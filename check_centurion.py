import os
import sys
import time
import requests
import difflib
import html
import json
from bs4 import BeautifulSoup

URLS = {
    "home": "https://www.thecenturionproject.ca/",
    "events": "https://www.thecenturionproject.ca/event-list"
}
STATUS_FILE = "status_centurion.json"

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

def fetch_page_text(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    max_retries = 3
    backoff = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract plain text content and normalize whitespace
            text = soup.get_text()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return lines
            
        except Exception as e:
            print(f"Warning: Attempt {attempt} to fetch {url} failed: {e}", file=sys.stderr)
            if attempt == max_retries:
                print(f"Error: Failed to retrieve {url} after {max_retries} attempts.", file=sys.stderr)
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
    # 1. Fetch current text lines for both pages
    current_state = {}
    for key, url in URLS.items():
        print(f"Fetching current content for {key} ({url})...")
        current_state[key] = fetch_page_text(url)
        
    # 2. Check if baseline exists
    is_initial_run = not os.path.exists(STATUS_FILE)
    
    if is_initial_run:
        print("Initial run: saving baseline text content for both pages.")
        with open(STATUS_FILE, 'w') as f:
            json.dump(current_state, f, indent=2)
        write_github_output("changed", "false")
        return

    # 3. Read baseline
    try:
        with open(STATUS_FILE, 'r') as f:
            old_state = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load baseline status_centurion.json: {e}", file=sys.stderr)
        old_state = {}

    # 4. Compare both pages
    changes = []
    change_summaries = []
    
    for key in URLS:
        old_lines = old_state.get(key, [])
        new_lines = current_state.get(key, [])
        
        if old_lines != new_lines:
            print(f"CHANGE DETECTED on {key} page!")
            diff_html = get_html_diff(old_lines, new_lines)
            
            changes.append(f"<h4>Changes on {key.capitalize()} Page:</h4>")
            changes.append(f'<div style="background-color: #fafafa; border: 1px solid #ddd; padding: 10px; border-radius: 4px; overflow-x: auto; margin-bottom: 20px;">{diff_html}</div>')
            change_summaries.append(f"{key.capitalize()} page updated")

    # 5. Output results
    if changes:
        combined_diff_html = "\n".join(changes)
        combined_summary = " & ".join(change_summaries)
        
        # Save new state
        with open(STATUS_FILE, 'w') as f:
            json.dump(current_state, f, indent=2)
            
        write_github_output("changed", "true")
        write_github_output("change_summary", combined_summary)
        write_github_output_multiline("change_details", combined_diff_html)
    else:
        print("No changes detected on either page.")
        write_github_output("changed", "false")

if __name__ == "__main__":
    main()
