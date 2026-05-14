# Brenus Governance Sync Policy

**Canonical location (upstream):** `docs/GOVERNANCE_SYNC_POLICY.md` in `fjkiani/Brenus`
**Consumer-repo location:** `external/Brenus/docs/GOVERNANCE_SYNC_POLICY.md`
**Last updated:** 2026-05-14
**Controlling authority:** This file. The handoff receipt(s) in this directory are historical context only.

---

## Agent preamble (verbatim — paste into every agent that touches Brenus content)

> Read `external/Brenus/docs/GOVERNANCE_SYNC_POLICY.md` before making any Brenus-related change. That file is the controlling policy. The handoff receipt is historical context, not the primary rule set.
>
> Brenus content has one upstream source of truth. Do not invent or maintain a second canonical version through prose summaries, partial local rewrites, or ad hoc copied snippets.
>
> Preferred sync method is a submodule with CI configured to fetch submodules. If submodules are blocked, use a documented vendor snapshot with manifest, pinned SHA, synced paths, and sync-only commits from SHA to SHA.
>
> Long-term validation must target machine artifacts, not Python scraping of raw TypeScript. Export from Node/TypeScript to generated JSON, then validate the JSON with schema and linkage checks in CI.
>
> If local consumer-repo content differs from upstream Brenus, sync first, then validate. No local drift patches before provenance is re-established.

**One-liner for task tickets:**
`Policy → external/Brenus/docs/GOVERNANCE_SYNC_POLICY.md first; receipt is history only; submodule preferred, vendor only with manifest + pin; validation targets generated JSON, not long-term TS scraping.`

---

## 1. Source of truth

`fjkiani/Brenus` is the single upstream source of truth for all Brenus content.

Consumer repos (`crispro-backend-v2`, `crispr-assistant`, and any future consumers) hold Brenus content under `external/Brenus/` — either as a git submodule checkout or a documented vendor snapshot. They do not own or originate Brenus content.

---

## 2. Sync method

### Preferred: git submodule

```
git submodule add https://github.com/fjkiani/Brenus.git external/Brenus
git submodule update --init --recursive
```

CI must run `git submodule update --init --recursive` before any Brenus-dependent step. Pin the submodule to a specific SHA; do not float on `main`.

### Fallback: vendor snapshot

Use only when submodules are blocked by the deployment environment. Requirements:

- `external/Brenus/VENDOR_MANIFEST.json` must exist and contain:
  - `upstream_repo`: `https://github.com/fjkiani/Brenus`
  - `pinned_sha`: exact 40-character commit SHA
  - `synced_paths`: list of paths copied from upstream
  - `sync_date`: ISO 8601 date
  - `synced_by`: agent or human identifier
- Commits that update the vendor snapshot must be labeled `chore(brenus-vendor): sync to <SHA>` and must contain only the snapshot update — no mixed changes.
- No local edits to vendored files. If a fix is needed, make it upstream in `fjkiani/Brenus` first, then re-sync.

---

## 3. Validation

Long-term validation must target **machine artifacts**, not Python scraping of raw TypeScript source.

Correct pattern:
1. Upstream `fjkiani/Brenus` exports a generated JSON artifact (e.g., `generated/registry_export.json`) via a Node/TypeScript build step.
2. Consumer CI downloads or submodule-fetches that JSON.
3. Consumer CI validates the JSON with schema checks and linkage checks (e.g., artifact IDs referenced in STATUS.md exist in REGISTRY.yaml).

Prohibited pattern: parsing `.ts`, `.tsx`, or `.md` files with ad hoc Python regex/string scraping as the primary validation mechanism. This is acceptable for one-off diagnostics but must not be the CI gate.

---

## 4. Drift policy

If consumer-repo content under `external/Brenus/` differs from upstream `fjkiani/Brenus` at the pinned SHA:

1. **Sync first.** Update the submodule or vendor snapshot to the correct SHA.
2. **Then validate.** Run schema and linkage checks against the freshly synced content.
3. **No drift patches.** Do not apply local edits to `external/Brenus/` files to paper over a divergence. Fix upstream, then re-sync.

---

## 5. EscapeMap artifact governance

`escape_map/`, `REGISTRY.yaml`, and `STATUS.md` are governed artifacts that live exclusively in `fjkiani/Brenus`. They are owned and updated upstream only.

Consumer repos:
- **May carry:** submodule SHA pins, vendor manifest paths, or generated JSON artifacts emitted by upstream tooling (e.g., a CI-exported `escape_map_summary.json`).
- **Must not carry:** forked canonical escape narratives, partial YAML rewrites, ad hoc "war board summaries" in prose form, or any local copy of `REGISTRY.yaml` / `STATUS.md` maintained as a truth source.

If a consumer needs to reference EscapeMap findings (e.g., in a prompt or UI), it must read from the synced `external/Brenus/` tree at the pinned SHA — not from a hand-copied snippet.

---

## 6. This file

This file is the single controlling policy document. Do not create parallel "how we sync Brenus" documents in any repo. If a rule changes, make a scoped edit to this file only, in both locations simultaneously:

- `docs/GOVERNANCE_SYNC_POLICY.md` in `fjkiani/Brenus` (authoritative)
- `external/Brenus/docs/GOVERNANCE_SYNC_POLICY.md` in each consumer repo (identical copy)

The two copies must remain byte-for-byte identical. If they diverge, the `fjkiani/Brenus` copy wins.
