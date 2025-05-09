#!/usr/bin/env python
"""
Conda Environment Manager for CRISPResso2 AI Research Assistant

This utility handles detection, creation, and management of Conda environments
for CRISPResso2 to ensure the assistant can properly execute CRISPResso2 commands.
"""

import os
import sys
import subprocess
import platform
import json
from typing import Dict, List, Optional, Tuple, Union


class CondaManager:
    """Manages Conda environments for CRISPResso2."""
    
    def __init__(self):
        """Initialize the Conda manager."""
        self.is_conda_installed = self._check_conda_installed()
        self.detected_environments = {}
        self.crispresso_env = None
        if self.is_conda_installed:
            self.detected_environments = self._get_conda_environments()
            self.crispresso_env = self._find_crispresso_environment()
    
    def _check_conda_installed(self) -> bool:
        """Check if Conda is installed on the system."""
        try:
            subprocess.run(
                ["conda", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _get_conda_environments(self) -> Dict[str, Dict]:
        """Get all available Conda environments."""
        try:
            result = subprocess.run(
                ["conda", "env", "list", "--json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )
            # Parse the JSON output
            environments_data = json.loads(result.stdout)
            
            # Convert to more usable format with name as keys
            parsed_environments = {}
            for env_path in environments_data.get("envs", []):
                env_name = os.path.basename(env_path)
                # If the base environment, name it 'base'
                if env_path == environments_data.get("base_prefix", ""):
                    env_name = "base"
                parsed_environments[env_name] = {
                    "path": env_path,
                    "has_crispresso": self._check_env_has_crispresso(env_path)
                }
            return parsed_environments
        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
            print(f"Error getting Conda environments: {e}")
            return {}
    
    def _check_env_has_crispresso(self, env_path: str) -> bool:
        """Check if an environment has CRISPResso2 installed."""
        try:
            # Construct the path to the CRISPResso executable
            if platform.system() == "Windows":
                crispresso_path = os.path.join(env_path, "Scripts", "CRISPResso")
            else:
                crispresso_path = os.path.join(env_path, "bin", "CRISPResso")
            
            return os.path.exists(crispresso_path)
        except Exception as e:
            print(f"Error checking for CRISPResso in environment: {e}")
            return False
    
    def _find_crispresso_environment(self) -> Optional[str]:
        """Find an environment with CRISPResso2 installed."""
        for env_name, env_data in self.detected_environments.items():
            if env_data.get("has_crispresso", False):
                return env_name
        return None
    
    def create_crispresso_environment(self, env_name: str = "crispresso2_env") -> bool:
        """Create a new Conda environment with CRISPResso2."""
        if not self.is_conda_installed:
            print("Error: Conda is not installed on this system.")
            return False
        
        # Handle platform-specific considerations
        platform_specific_cmd = []
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            # macOS with Apple Silicon (M1/M2)
            platform_specific_cmd = [
                "conda", "config", "--add", "subdirs", "osx-64"
            ]
            try:
                subprocess.run(
                    platform_specific_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
                print("Configured Conda for Apple Silicon (using Rosetta).")
            except subprocess.SubprocessError as e:
                print(f"Warning: Failed to configure Conda for Apple Silicon: {e}")
        
        # Create the environment
        create_cmd = [
            "conda", "create", "-n", env_name, 
            "-c", "bioconda", "-c", "conda-forge",
            "crispresso2", "-y"
        ]
        
        try:
            print(f"Creating Conda environment '{env_name}' with CRISPResso2...")
            subprocess.run(
                create_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            # Refresh the environments
            self.detected_environments = self._get_conda_environments()
            self.crispresso_env = self._find_crispresso_environment()
            return True
        except subprocess.SubprocessError as e:
            print(f"Error creating CRISPResso2 environment: {e}")
            return False
    
    def get_activation_command(self, env_name: Optional[str] = None) -> List[str]:
        """Get the command to activate a Conda environment."""
        if env_name is None:
            env_name = self.crispresso_env
        
        if not env_name:
            raise ValueError("No CRISPResso2 environment specified or detected.")
        
        if platform.system() == "Windows":
            return ["conda", "activate", env_name]
        else:
            # For macOS and Linux, we need source which isn't directly 
            # callable via subprocess, so we return a shell command
            return ["source", "activate", env_name]
    
    def run_crispresso_command(
        self, 
        command_args: List[str], 
        env_name: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Run a CRISPResso2 command in the specified environment.
        
        Args:
            command_args: Command line arguments for CRISPResso
            env_name: Optional environment name to use
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        if env_name is None:
            env_name = self.crispresso_env
        
        if not env_name:
            return (False, "", "No CRISPResso2 environment specified or detected.")
        
        env_path = self.detected_environments.get(env_name, {}).get("path")
        if not env_path:
            return (False, "", f"Environment '{env_name}' not found.")
        
        # Determine the path to the CRISPResso executable
        if platform.system() == "Windows":
            crispresso_path = os.path.join(env_path, "Scripts", "CRISPResso")
        else:
            crispresso_path = os.path.join(env_path, "bin", "CRISPResso")
        
        if not os.path.exists(crispresso_path):
            return (False, "", f"CRISPResso executable not found in environment '{env_name}'.")
        
        # Create the full command
        full_command = [crispresso_path] + command_args
        
        try:
            # Execute the command with the conda environment's python
            result = subprocess.run(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False  # Don't raise an exception on non-zero exit
            )
            return (result.returncode == 0, result.stdout, result.stderr)
        except Exception as e:
            return (False, "", f"Error executing CRISPResso2 command: {str(e)}")
    
    def get_installation_guide(self) -> str:
        """Generate installation instructions for CRISPResso2."""
        if self.is_conda_installed:
            if self.crispresso_env:
                return (
                    f"CRISPResso2 is already installed in the '{self.crispresso_env}' "
                    f"Conda environment. You can activate it with:\n"
                    f"conda activate {self.crispresso_env}"
                )
            else:
                instructions = (
                    "CRISPResso2 is not installed, but Conda is detected. "
                    "You can install CRISPResso2 using Bioconda with:\n\n"
                    "conda create -n crispresso2_env -c bioconda -c conda-forge crispresso2\n"
                    "conda activate crispresso2_env"
                )
                
                # Add Apple Silicon-specific instructions
                if platform.system() == "Darwin" and platform.machine() == "arm64":
                    instructions += (
                        "\n\nNote: Since you're using an Apple Silicon Mac (M1/M2), "
                        "you'll need to install Rosetta 2 and configure Conda to use Intel packages:\n\n"
                        "conda config --add subdirs osx-64\n"
                        "conda create -n crispresso2_env -c bioconda -c conda-forge crispresso2"
                    )
                
                return instructions
        else:
            return (
                "Conda is not installed. To use CRISPResso2, you need to install Conda first:\n\n"
                "1. Download Miniconda from https://docs.conda.io/en/latest/miniconda.html\n"
                "2. Install Miniconda by following the instructions for your platform\n"
                "3. After installation, install CRISPResso2 with:\n"
                "   conda create -n crispresso2_env -c bioconda -c conda-forge crispresso2\n"
                "   conda activate crispresso2_env"
            )


# Example usage
if __name__ == "__main__":
    manager = CondaManager()
    
    print(f"Conda installed: {manager.is_conda_installed}")
    if manager.is_conda_installed:
        print(f"Detected environments: {list(manager.detected_environments.keys())}")
        print(f"CRISPResso environment: {manager.crispresso_env}")
        
        if manager.crispresso_env:
            print(f"CRISPResso is installed in '{manager.crispresso_env}'")
        else:
            print("CRISPResso is not installed in any detected environment.")
            print(manager.get_installation_guide()) 