import subprocess
import json
import os
import requests # For PubMed API calls
import time
import xml.etree.ElementTree as ET # For parsing PubMed XML
import re
from dotenv import load_dotenv # Add this import

# Assuming llm_api.py is in the same directory or accessible in PYTHONPATH
from .llm_api import query_llm # Relative import

# Load environment variables from .env file
load_dotenv() # Add this call

# Constants for PubMed API
PUBMED_API_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
PUBMED_ESEARCH_URL = PUBMED_API_BASE_URL + "esearch.fcgi"
PUBMED_EFETCH_URL = PUBMED_API_BASE_URL + "efetch.fcgi"
# It's good practice to include an email for NCBI to contact if there are issues
# However, for a client-side app, this might not be directly set by the user.
# For now, we'll omit it, but for a server-side app, it would be important.
# NCBI_TOOL_EMAIL = {'tool': 'crispr_ai_assistant', 'email': 'user@example.com'} 

# Diffbot API Configuration
DIFFBOT_ANALYZE_API_URL = "https://api.diffbot.com/v3/analyze"
# Load Diffbot token from environment variable for security
DIFFBOT_TOKEN = os.getenv("DIFFBOT_TOKEN") # Now this should work if .env is loaded

# Constants for PubMed URL construction (still useful for targeting Diffbot)
PUBMED_SEARCH_BASE_URL = "https://pubmed.ncbi.nlm.nih.gov/"

def get_pubmed_search_results_via_diffbot(query_string: str, diffbot_token: str, retmax: int = 5) -> list:
    """
    Uses Diffbot's Analyze API to get structured data from a PubMed search results page.

    Args:
        query_string (str): The raw search query for PubMed.
        diffbot_token (str): Your Diffbot API token.
        retmax (int): Number of results Diffbot attempts to extract (actual may vary).

    Returns:
        list: A list of article dictionaries, or an empty list if an error occurs.
    """
    if not diffbot_token:
        print("Error: DIFFBOT_TOKEN is not set. Please set it as an environment variable.")
        return []

    # Construct the PubMed search URL
    # We need to URL-encode the query_string for the `term` parameter of PubMed URL
    try:
        from urllib.parse import quote_plus
        encoded_query = quote_plus(query_string)
    except ImportError:
        # Fallback for older Python if needed, though quote_plus is standard
        import urllib
        encoded_query = urllib.parse.quote_plus(query_string)
        
    pubmed_url = f"{PUBMED_SEARCH_BASE_URL}?term={encoded_query}"
    print(f"Constructed PubMed URL for Diffbot: {pubmed_url}")

    params = {
        'url': pubmed_url,
        'token': diffbot_token,
        # 'fields': 'links,meta,querystring,items' # Optional: specify fields if needed
        # 'maxPages': '1' # Limit Diffbot to the first page of PubMed results
    }
    headers = {}
    
    articles_extracted = []
    try:
        response = requests.get(DIFFBOT_ANALYZE_API_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Diffbot's Analyze API returns a list of objects, one for each page analyzed.
        # For a PubMed search URL, we expect one primary object.
        if isinstance(data, list) and len(data) > 0:
            page_data = data[0] # Assuming the first object contains the relevant page analysis
        elif isinstance(data, dict) and data.get('type') == 'page':
            page_data = data
        else:
            page_data = data # If it's already the page object for some reason
        
        if page_data and page_data.get('type') == 'page' and 'items' in page_data:
            # 'items' usually contains the list of articles/results Diffbot found on the page
            items = page_data['items']
            print(f"Diffbot found {len(items)} items on the page.")
            
            for item in items[:retmax]: # Respect retmax
                # The structure of 'item' can vary based on Diffbot's analysis.
                # We need to flexibly extract title, summary (abstract), and link.
                title = item.get('title', 'No title available')
                # Diffbot's 'summary' is often the abstract snippet
                abstract_snippet = item.get('summary', item.get('text', 'No abstract available')) 
                link = item.get('link', item.get('resolvedPageUrl', item.get('pageUrl', 'No URL available')))
                pmid = None
                # Try to extract PMID from the link
                if link and "pubmed.ncbi.nlm.nih.gov/" in link:
                    match = re.search(r'/(\d+)/?', link)
                    if match:
                        pmid = match.group(1)
                
                articles_extracted.append({
                    'pmid': pmid,
                    'title': title,
                    'abstract': abstract_snippet, # Using Diffbot's summary as abstract
                    'url': link
                })
        else:
            print(f"Diffbot Analyze API did not return the expected 'items' array for PubMed URL: {pubmed_url}")
            print(f"Diffbot Response (or relevant part): {json.dumps(page_data, indent=2)[:1000]}...")

    except requests.exceptions.RequestException as e:
        print(f"Error during Diffbot API call for PubMed URL '{pubmed_url}': {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Diffbot API for PubMed URL '{pubmed_url}': {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
    
    return articles_extracted

def search_pubmed(query_string: str, retmax: int = 5) -> list:
    """
    Searches PubMed for a given query string and returns a list of PubMed IDs (PMIDs).

    Args:
        query_string (str): The search query.
        retmax (int): Maximum number of PMIDs to return.

    Returns:
        list: A list of PMIDs (as strings), or an empty list if an error occurs or no results.
    """
    params = {
        'db': 'pubmed',
        'term': query_string,
        'retmode': 'json',
        'retmax': str(retmax),
        # 'usehistory': 'y' # Useful if we were doing many related queries
    }
    # params.update(NCBI_TOOL_EMAIL) # If we were to add email/tool name

    pmids = []
    try:
        response = requests.get(PUBMED_ESEARCH_URL, params=params, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        
        if 'esearchresult' in data and 'idlist' in data['esearchresult']:
            pmids = data['esearchresult']['idlist']
        else:
            print(f"PubMed ESearch did not return the expected idlist for query: {query_string}")
            print(f"Response: {data}")

    except requests.exceptions.RequestException as e:
        print(f"Error during PubMed ESearch for query '{query_string}': {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from PubMed ESearch for query '{query_string}': {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
    
    return pmids

def fetch_pubmed_articles(pmids: list) -> list:
    """
    Fetches article details (title, abstract, URL) from PubMed for a list of PMIDs.
    Uses EFetch with retmode=xml to get abstracts.

    Args:
        pmids (list): A list of PubMed IDs (strings).

    Returns:
        list: A list of dictionaries, each containing pmid, title, abstract, and url.
              Returns an empty list if an error occurs or no articles found.
    """
    if not pmids:
        return []

    articles = []
    # Process PMIDs in batches if necessary, though for small numbers (e.g., < 200) one call is fine.
    # Max PMIDs per EFetch GET request is around 200.
    pmid_string = ",".join(pmids)
    
    params = {
        'db': 'pubmed',
        'id': pmid_string,
        'retmode': 'xml', # XML is often more complete for abstracts
        'rettype': 'abstract' # We want abstract, not full text
    }
    # params.update(NCBI_TOOL_EMAIL)

    try:
        response = requests.get(PUBMED_EFETCH_URL, params=params, timeout=20) # Longer timeout for fetch
        response.raise_for_status()
        
        # Parse the XML response
        root = ET.fromstring(response.content)
        
        for pubmed_article in root.findall('.//PubmedArticle'):
            article_data = {'pmid': '', 'title': '', 'abstract': '', 'url': ''}
            
            pmid_node = pubmed_article.find('.//PMID')
            if pmid_node is not None and pmid_node.text:
                article_data['pmid'] = pmid_node.text
                article_data['url'] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid_node.text}/"
            
            article_title_node = pubmed_article.find('.//ArticleTitle')
            if article_title_node is not None:
                 # Join all text parts of the ArticleTitle, handling any inline tags like <i>
                article_data['title'] = "".join(article_title_node.itertext()).strip()

            abstract_text_parts = []
            # Abstracts can be structured with multiple AbstractText nodes
            for abstract_node in pubmed_article.findall('.//Abstract/AbstractText'):
                label = abstract_node.get('Label')
                text_content = "".join(abstract_node.itertext()).strip()
                if label:
                    abstract_text_parts.append(f"{label}: {text_content}")
                else:
                    abstract_text_parts.append(text_content)
            
            if abstract_text_parts:
                article_data['abstract'] = "\n".join(abstract_text_parts)
            elif article_title_node is not None: # Fallback if no abstract, use title
                article_data['abstract'] = "Abstract not available. " + article_data['title']
            else:
                article_data['abstract'] = "Title and abstract not available."

            if article_data['pmid'] and article_data['title']:
                 articles.append(article_data)

    except requests.exceptions.RequestException as e:
        print(f"Error during PubMed EFetch for PMIDs '{pmid_string}': {e}")
    except ET.ParseError as e:
        print(f"Error parsing XML from PubMed EFetch for PMIDs '{pmid_string}': {e}")
        # print(f"Response text: {response.text if 'response' in locals() else 'N/A'}") # Be careful printing large XML

    return articles

def get_literature_summary_for_therapeutic_context(target_keyword, challenge_keyword, research_area="CRISPR gene editing", max_articles_to_summarize=3):
    """
    Performs a literature search using the PubMed E-utilities API and uses an LLM to summarize the findings.
    """
    # Construct a simplified PubMed search query for E-utilities
    query_parts = []
    if target_keyword:
        query_parts.append(f'"{target_keyword}"[Title/Abstract]')
    if challenge_keyword:
        query_parts.append(f'"{challenge_keyword}"[Title/Abstract]')
    # Optional: Include research area if it helps narrow down.
    # For now, keeping it simpler based on previous results.
    # if research_area:
    #     query_parts.append(f'"{research_area}"[Title/Abstract]')
    
    # Add therapeutic context terms, ensuring they are ANDed with the main query if other parts exist
    therapeutic_terms = "(therapeutic[Title/Abstract] OR therapy[Title/Abstract] OR clinical[Title/Abstract] OR preclinical[Title/Abstract])"
    if query_parts: # Only add AND if there are other terms
        query_parts.append(therapeutic_terms)
    else: # If no other terms, this becomes the main query
        query_parts.append(therapeutic_terms) # This case is unlikely if target_keyword is mandatory

    pubmed_search_term = " AND ".join(query_parts)
    print(f"Constructed Simplified PubMed search term for E-utilities: {pubmed_search_term}")

    # Use direct PubMed API
    pmids = search_pubmed(pubmed_search_term, retmax=max_articles_to_summarize) 

    if not pmids:
        return f"No relevant literature found via PubMed API for query: '{pubmed_search_term}'. Please check search terms or try broadening your query."
    
    print(f"Found PMIDs: {pmids}")
    
    # Fetch article details for the found PMIDs
    articles = fetch_pubmed_articles(pmids)

    if not articles:
        return f"Found PMIDs ({', '.join(pmids)}), but could not retrieve article details via PubMed API."

    # Filter for articles that have a meaningful abstract
    valid_articles_for_summary = []
    for article in articles:
        if article.get('abstract') and "not available" not in article.get('abstract', "").lower() and len(article.get('abstract', "")) > 20:
            valid_articles_for_summary.append(article)

    if not valid_articles_for_summary:
        return f"Retrieved article details for PMIDs ({', '.join(pmids)}), but could not find sufficient abstract details for LLM summarization."

    context_for_llm = "Based on the following article summaries obtained from PubMed:\n\n"
    for i, article in enumerate(valid_articles_for_summary):
        max_abstract_length = 1500 
        title = article.get('title', 'No title')
        abstract = article.get('abstract', 'No abstract available') 
        url = article.get('url', 'No URL')
        pmid = article.get('pmid', 'N/A')
        safe_abstract = abstract if abstract else ""
        context_for_llm += f"{i+1}. PMID: {pmid}\\n   Title: {title}\\n   Abstract: {safe_abstract[:max_abstract_length]}...\\n   URL: {url}\\n\\n"
    
    print("\\n" + "-"*20 + " DEBUG: Data sent to LLM for Summarization (PubMed API) " + "-"*20)
    print(f"Original PubMed Search Term: {pubmed_search_term}")
    print(f"Target Keyword: {target_keyword}, Challenge: {challenge_keyword}, Research Area: {research_area}")
    print(f"Number of valid articles for summary: {len(valid_articles_for_summary)}")
    print("Valid articles (titles and PMIDs from PubMed API):")
    for art in valid_articles_for_summary:
        print(f"  - PMID: {art.get('pmid')}, Title: {art.get('title')}")
    print("-"*60 + "\\n")

    summary_prompt = f\"\"\"
As an expert in CRISPR-based therapeutic development, please synthesize the key findings from the following article abstracts (obtained from PubMed).
Original search query aimed for: '{pubmed_search_term}'.

Focus your summary on how these findings relate to the challenge of '{challenge_keyword}' when developing '{target_keyword}' as a therapeutic using '{research_area}'. 

Highlight:
- Key insights or data points relevant to the challenge from the provided abstracts.
- Any novel approaches or solutions mentioned.
- Remaining gaps or future directions suggested by the abstracts.

Keep the summary concise (2-4 paragraphs) and directly relevant to the therapeutic development context. Cite PMIDs using (PMID: XXXXX) where appropriate.

Article Abstracts from PubMed:
{context_for_llm}

Synthesized Summary:
\"\"\"

    try:
        summary = query_llm(summary_prompt)
        source_info = []
        for art in valid_articles_for_summary:
            if art['pmid']:
                source_info.append(f"PMID: {art['pmid']}")
        if source_info:
            summary += f"\\n\\n_Summary based on insights from: { '; '.join(source_info) }._"
        return summary
    except Exception as e:
        print(f"Error during LLM summarization: {e}")
        return f"Error generating summary: {str(e)}"

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    # No longer need to check DIFFBOT_TOKEN here as we are using PubMed API directly.

    print("--- Test 1: PDCD1 Off-target Effects (PubMed API) ---")
    summary1 = get_literature_summary_for_therapeutic_context(
        target_keyword="PDCD1", 
        challenge_keyword="off-target effects",
        research_area="T-cell cancer immunotherapy",
        max_articles_to_summarize=3 # Changed max to 3
    )
    print(summary1)
    print("\\n")

    time.sleep(1) 
    print("--- Test 2: CRISPR Delivery to T-cells (PubMed API) ---")
    summary2 = get_literature_summary_for_therapeutic_context(
        target_keyword="CRISPR Cas9", 
        challenge_keyword="delivery methods",
        research_area="T-cell gene therapy",
        max_articles_to_summarize=3 # Changed max to 3
    )
    print(summary2)
    print("\\n")

    time.sleep(1)
    print("--- Test 3: BCL11A Editing Efficacy for Sickle Cell (PubMed API) ---")
    summary3 = get_literature_summary_for_therapeutic_context(
        target_keyword="BCL11A", 
        challenge_keyword="editing efficacy AND durability", 
        research_area="sickle cell disease gene therapy",
        max_articles_to_summarize=3 # Changed max to 3
    )
    print(summary3)
    print("\\n")
    
    time.sleep(1)
    print("--- Test 4: NonExistentGene BogusChallenge (PubMed API - expect no results) ---")
    summary4 = get_literature_summary_for_therapeutic_context(
        target_keyword="NonExistentGeneXYZ", 
        challenge_keyword="BogusChallengeABC",
        research_area="made up research",
        max_articles_to_summarize=3 # Changed max to 3
    )
    print(summary4)
    print("\\n")

    # Remove the old run_search_engine function as it's replaced by PubMed specific ones
    # Path to the search_engine.py script - adjust if necessary
    # SEARCH_ENGINE_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'search_engine.py')
    # VENV_PYTHON_PATH = 'venv/bin/python' # Adjust if your venv python is elsewhere or use sys.executable if run from same env

    # def run_search_engine(query_string):
    #     ... 