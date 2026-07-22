import os
import sys
import time
import urllib.request
import difflib
import html
import json
from bs4 import BeautifulSoup

URL = "https://www.canada.ca/en/foreign-influence-commissioner.html"
STATUS_FILE = "status_foreign_influence.json"

USER_AGENTS = [
    "Mozilla/5.0 (compatible; ForeignInfluenceMonitor/1.0; +https://github.com/J7892/page_checkers)",
    "Wget/1.21.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

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
    max_retries = 3
    backoff = 2
    
    for attempt in range(1, max_retries + 1):
        for ua in USER_AGENTS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": ua})
                with urllib.request.urlopen(req, timeout=30) as response:
                    html_content = response.read().decode("utf-8", errors="replace")
                    
                soup = BeautifulSoup(html_content, "html.parser")
                main = soup.find("main") or soup.find("body")
                if not main:
                    raise ValueError("No main or body tag found in HTML")
                    
                # Remove unwanted structural/script tags
                for elem in main.find_all(["script", "style", "nav", "header", "footer", "noscript"]):
                    elem.decompose()
                    
                lines = [line.strip() for line in main.get_text().splitlines() if line.strip()]
                if lines:
                    return lines
            except Exception as e:
                print(f"Warning: Attempt {attempt} with User-Agent '{ua[:30]}...' failed: {e}", file=sys.stderr)
                
        if attempt < max_retries:
            sleep_time = backoff ** attempt
            print(f"Retrying in {sleep_time} seconds...", file=sys.stderr)
            time.sleep(sleep_time)
            
    print(f"Error: Failed to retrieve content from {url} after {max_retries} attempts.", file=sys.stderr)
    sys.exit(2)

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
    print(f"Fetching current content for Foreign Influence Commissioner page ({URL})...")
    current_lines = fetch_page_text(URL)
    print(f"Extracted {len(current_lines)} lines of text.")
    
    # 2. Check if baseline state file exists
    is_initial_run = not os.path.exists(STATUS_FILE)
    
    if is_initial_run:
        print(f"Initial run: saving baseline text content to {STATUS_FILE}.")
        with open(STATUS_FILE, 'w') as f:
            json.dump({"lines": current_lines}, f, indent=2)
        write_github_output("changed", "false")
        return

    # 3. Read baseline
    try:
        with open(STATUS_FILE, 'r') as f:
            old_data = json.load(f)
            old_lines = old_data.get("lines", [])
    except Exception as e:
        print(f"Warning: Failed to load baseline {STATUS_FILE}: {e}", file=sys.stderr)
        old_lines = []

    # 4. Compare baseline with current lines
    if old_lines != current_lines:
        print("CHANGE DETECTED on Foreign Influence Commissioner page!")
        diff_html = get_html_diff(old_lines, current_lines)
        
        change_details_html = (
            "<h4>Changes Detected on Foreign Influence Commissioner Page:</h4>"
            f'<div style="background-color: #fafafa; border: 1px solid #ddd; padding: 10px; border-radius: 4px; overflow-x: auto; margin-bottom: 20px;">{diff_html}</div>'
        )
        summary = "Foreign Influence Commissioner Page Updated"
        
        # Save new state
        with open(STATUS_FILE, 'w') as f:
            json.dump({"lines": current_lines}, f, indent=2)
            
        write_github_output("changed", "true")
        write_github_output("change_summary", summary)
        write_github_output_multiline("change_details", change_details_html)
    else:
        print("No changes detected on the Foreign Influence Commissioner page.")
        write_github_output("changed", "false")

if __name__ == "__main__":
    main()
