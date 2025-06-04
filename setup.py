"""
Setup script for Job Scraper Agent
"""
import os
import subprocess
import sys
import time
import platform

def run_command(command):
    """Run a command and display output"""
    print(f"Running: {command}")
    process = subprocess.Popen(
        command, 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        universal_newlines=True
    )
    
    for line in process.stdout:
        print(line.strip())
    
    process.wait()
    return process.returncode

def main():
    """Main setup function"""
    print("===== Job Scraper Agent Setup =====")
    print("This script will help you set up the Job Scraper Agent.")
    print("It will install the required dependencies and configure the environment.")
    print()
    
    # Check if Python is installed
    print("Checking Python installation...")
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8 or higher is required.")
        return 1
    
    print(f"Found Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Install requirements
    print("\nInstalling requirements...")
    if run_command("pip install -r requirements.txt") != 0:
        print("ERROR: Failed to install requirements.")
        return 1
    
    # Install Playwright
    print("\nInstalling Playwright...")
    if run_command("pip install playwright") != 0:
        print("ERROR: Failed to install Playwright.")
        return 1
    
    # Install Playwright browsers using our compatibility module
    print("\nInstalling Playwright browsers...")
    print("Using compatibility module for Python 3.13...")
    
    # Import our compatibility module
    try:
        from playwright_compat import ensure_browsers_installed
        
        # Try to install browsers using our module
        if ensure_browsers_installed():
            print("Successfully installed Playwright browsers!")
        else:
            print("WARNING: Failed to install Playwright browsers.")
            print("You may need to install them manually later.")
    except ImportError:
        # Fallback to standard method
        if run_command("playwright install chromium") != 0:
            print("WARNING: Failed to install Playwright browsers automatically.")
            print("You may need to install them manually later with 'playwright install'.")
    
    # Create .env file if it doesn't exist
    if not os.path.exists(".env"):
        print("\nCreating .env file...")
        with open(".env", "w") as f:
            f.write("# OpenAI API key\nOPENAI_API_KEY=")
        print("Please edit the .env file and add your OpenAI API key.")
    
    print("\n===== Setup Complete =====")
    print("To run the Job Scraper Agent, use the following command:")
    print("streamlit run app.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
