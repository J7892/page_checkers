import os
import re
import sys
import time
import requests

URL = "https://efpublic.elections.ab.ca/efCIPs.cfm?MID=CIP"
STATUS_FILE = "status.txt"
DEFAULT_STATUS = "Due: July 3, 2026"
TARGET_PETITION = "2026 A Referendum Relating to Alberta Independence"

def write_github_output(name, value):
    output_file = os.environ.get('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"{name}={value}\n")

def main():
    # 1. Read last known status
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'r') as f:
            old_status = f.read().strip()
    else:
        old_status = DEFAULT_STATUS
    
    print(f"Last known status: '{old_status}'")
    
    # 2. Fetch the page
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    max_retries = 3
    backoff = 2
    response = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(URL, headers=headers, timeout=30)
            response.raise_for_status()
            break
        except Exception as e:
            print(f"Warning: Attempt {attempt} to fetch URL failed with error: {e}", file=sys.stderr)
            if attempt == max_retries:
                print(f"Error fetching the URL: {e}", file=sys.stderr)
                sys.exit(2)  # Use exit code 2 for network/fetch errors
            sleep_time = backoff ** attempt
            print(f"Retrying in {sleep_time} seconds...", file=sys.stderr)
            time.sleep(sleep_time)

    html = response.text
    
    # 3. Parse page using regex split (highly robust for this ColdFusion table)
    rows = re.split(r'<tr[^>]*>', html, flags=re.I)
    
    target_row_html = None
    for row in rows:
        if TARGET_PETITION in row:
            target_row_html = row
            break
            
    if not target_row_html:
        print(f"Error: Target petition '{TARGET_PETITION}' not found in page content.", file=sys.stderr)
        sys.exit(3)  # Use exit code 3 for parsing/structure errors
        
    cols = re.split(r'<td[^>]*>', target_row_html, flags=re.I)
    if len(cols) < 6:
        print(f"Error: Unexpected row structure. Expected at least 6 cells, found {len(cols)}.", file=sys.stderr)
        sys.exit(3)
        
    col5_raw = cols[5]
    
    # Strip HTML tags and normalize whitespace
    col5_clean = re.sub(r'<[^<]+?>', ' ', col5_raw)
    new_status = re.sub(r'\s+', ' ', col5_clean).strip()
    
    print(f"Current scraped status: '{new_status}'")
    
    if new_status != old_status:
        print(f"CHANGE DETECTED!")
        print(f"Old status: '{old_status}'")
        print(f"New status: '{new_status}'")
        
        # Save new status
        with open(STATUS_FILE, 'w') as f:
            f.write(new_status + '\n')
            
        write_github_output("changed", "true")
        write_github_output("old_status", old_status)
        write_github_output("new_status", new_status)
    else:
        print("No change detected.")
        write_github_output("changed", "false")

if __name__ == "__main__":
    main()
