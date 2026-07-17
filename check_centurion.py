import os
import sys
import time
import requests
import difflib
import html
from bs4 import BeautifulSoup

URL = "https://www.thecenturionproject.ca/"
STATUS_FILE = "status_centurion.txt"

def write_github_output(name, value):
    output_file = os.environ.get('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"{name}={value}\n")

def write_github_output_multiline(name, value):
    output_file = os.environ.get('GITHUB_OUTPUT')
    if output_file:
        import uuid
        delimiter = f"DELIMITER_{uuid.uuid4().hex}"
        with open(output_file, 'a') as f:
            f.write(f"{name}<<{delimiter}\n")
            f.write(f"{value}\n")
            f.write(f"{delimiter}\n")

def fetch_page_text():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    max_retries = 3
    backoff = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(URL, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract plain text content and normalize whitespace
            text = soup.get_text()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return lines
            
        except Exception as e:
            print(f"Warning: Attempt {attempt} to fetch page failed: {e}", file=sys.stderr)
            if attempt == max_retries:
                print(f"Error: Failed to retrieve page after {max_retries} attempts.", file=sys.stderr)
                sys.exit(2)
            sleep_time = backoff ** attempt
            print(f"Retrying in {sleep_time} seconds...", file=sys.stderr)
            time.sleep(sleep_time)

def get_html_diff(old_lines, new_lines):
    diff = difflib.unified_diff(old_lines, new_lines, lineterm="")
    html_lines = []
    
    diff_list = list(diff)
    if len(diff_list) > 2:
        diff_list = diff_list[2:]
        
    for line in diff_list:
        if line.startswith('+'):
            escaped = html.escape(line[1:])
            html_lines.append(f'<div style="color: #2e7d32; background-color: #e8f5e9; padding: 2px 5px; font-family: monospace;">+ {escaped}</div>')
        elif line.startswith('-'):
            escaped = html.escape(line[1:])
            html_lines.append(f'<div style="color: #c62828; background-color: #ffebee; padding: 2px 5px; font-family: monospace;">- {escaped}</div>')
        elif line.startswith('@@'):
            escaped = html.escape(line)
            html_lines.append(f'<div style="color: #1565c0; font-style: italic; margin-top: 10px; font-family: monospace;">{escaped}</div>')
        else:
            escaped = html.escape(line)
            html_lines.append(f'<div style="color: #555555; padding: 2px 5px; font-family: monospace;">&nbsp;&nbsp;{escaped}</div>')
            
    return "\n".join(html_lines)

def main():
    # 1. Fetch current text lines
    print("Fetching current webpage content...")
    new_lines = fetch_page_text()
    
    # 2. Check if baseline exists
    is_initial_run = not os.path.exists(STATUS_FILE)
    
    if is_initial_run:
        print("Initial run: saving baseline text content.")
        with open(STATUS_FILE, 'w') as f:
            f.write("\n".join(new_lines) + "\n")
        write_github_output("changed", "false")
        return

    # 3. Read baseline
    try:
        with open(STATUS_FILE, 'r') as f:
            old_lines = [line.strip() for line in f.read().splitlines() if line.strip()]
    except Exception as e:
        print(f"Warning: Failed to load baseline status_centurion.txt: {e}", file=sys.stderr)
        old_lines = []

    # 4. Compare
    if old_lines != new_lines:
        print("CHANGE DETECTED!")
        
        # Generate diffs
        diff_html = get_html_diff(old_lines, new_lines)
        
        # Save new state
        with open(STATUS_FILE, 'w') as f:
            f.write("\n".join(new_lines) + "\n")
            
        write_github_output("changed", "true")
        write_github_output("change_summary", "Centurion Project Website Content Updated")
        write_github_output_multiline("change_details", diff_html)
    else:
        print("No changes detected.")
        write_github_output("changed", "false")

if __name__ == "__main__":
    main()
