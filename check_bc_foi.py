import os
import sys
import json
import requests
from bs4 import BeautifulSoup

URL_TEMPLATE = "https://www2.gov.bc.ca/gov/search?q=foi+request%2Binmeta%3Ahigh_level_subject%3DFOI+Request&id=9199E7BC9682482EB9EA0B6D6B8D386C&tab=1&page={page}"
STATUS_FILE = "status_bc_foi.json"

def write_github_output(name, value):
    output_file = os.environ.get('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"{name}={value}\n")

def fetch_page_results(page_num):
    url = URL_TEMPLATE.format(page=page_num)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www2.gov.bc.ca/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page {page_num}: {e}", file=sys.stderr)
        sys.exit(2)
        
    soup = BeautifulSoup(response.text, 'html.parser')
    next_data_script = soup.find('script', id='__NEXT_DATA__')
    if not next_data_script:
        print(f"Error: __NEXT_DATA__ script not found on page {page_num}.", file=sys.stderr)
        sys.exit(3)
        
    try:
        next_data = json.loads(next_data_script.string)
    except Exception as e:
        print(f"Error parsing JSON from page {page_num}: {e}", file=sys.stderr)
        sys.exit(3)
        
    results_list = []
    try:
        page_component = next_data['props']['pageProps']['data']['results'][0]
        comps = page_component.get('components', [])
        # Find the SEARCH_INSTANCE component
        search_comp = next(c for c in comps if c.get('type') == 'SEARCH_INSTANCE')
        # Find search_body
        search_body = next(c for c in search_comp.get('children', []) if c.get('name') == 'search_body')
        # Find search_results
        search_results = next(c for c in search_body.get('children', []) if c.get('name') == 'search_results')
        # Get all children under search_results
        result_items = search_results.get('children', [])
        
        for item in result_items:
            if item.get('name') == 'result':
                fields = {f.get('name'): f.get('value') for f in item.get('fields', [])}
                results_list.append(fields)
    except Exception as e:
        print(f"Error traversing Next.js component tree on page {page_num}: {e}", file=sys.stderr)
        sys.exit(3)
        
    return results_list

def main():
    # 1. Load last known state
    is_initial_run = not os.path.exists(STATUS_FILE)
    old_uids = {}
    
    if not is_initial_run:
        try:
            with open(STATUS_FILE, 'r') as f:
                state_data = json.load(f)
                old_uids = state_data.get("uids", {})
        except Exception as e:
            print(f"Warning: Failed to load status_bc_foi.json: {e}", file=sys.stderr)
            # Proceed with empty set if corrupted, to avoid getting stuck
            old_uids = {}
            is_initial_run = True

    # 2. Fetch page 1 and page 2 results (top 20)
    print("Fetching Page 1...")
    p1_results = fetch_page_results(1)
    print(f"Found {len(p1_results)} results on Page 1.")
    
    print("Fetching Page 2...")
    p2_results = fetch_page_results(2)
    print(f"Found {len(p2_results)} results on Page 2.")
    
    all_results = p1_results + p2_results
    
    # 3. Detect new items
    new_items = []
    current_uids = {}
    
    for item in all_results:
        uid = item.get('recordUid')
        if not uid:
            continue
        
        pub_date = item.get('Publication Date', '')
        current_uids[uid] = pub_date
        
        # If it's a new UID and we're not in the initial baseline run
        if uid not in old_uids and not is_initial_run:
            new_items.append(item)

    # 4. Handle initial baseline run
    if is_initial_run:
        print("Initial run: saving baseline records without alerting.")
        # Store current UIDs
        new_state = {"uids": current_uids}
        with open(STATUS_FILE, 'w') as f:
            json.dump(new_state, f, indent=2)
        write_github_output("changed", "false")
        return

    # 5. Output results
    if new_items:
        print(f"Detected {len(new_items)} new FOI releases!")
        
        # Sort new items chronologically (oldest of the new first, to read forward)
        new_items.reverse()
        
        # Prepare HTML body details
        html_details = []
        for item in new_items:
            uid = item.get('recordUid', 'N/A')
            title = item.get('title', f"FOI Request - {uid}")
            url = item.get('url', '#')
            desc = item.get('description', 'No description provided.')
            ministry = item.get('Ministry', 'Unknown Ministry')
            pub_date = item.get('Publication Date', 'Unknown Date')
            app_type = item.get('Applicant Type', 'N/A')
            fees = item.get('Fees paid by applicant', 'N/A')
            
            html_details.append(f"""
            <div style="margin-bottom: 20px; border-left: 4px solid #003366; padding-left: 15px;">
                <h4 style="margin: 0 0 5px 0; color: #003366;">
                    <a href="{url}" style="text-decoration: underline; color: #003366;">{title}</a>
                </h4>
                <p style="margin: 0 0 5px 0; font-size: 0.9em; color: #555;">
                    <strong>Published:</strong> {pub_date} | 
                    <strong>Ministry:</strong> {ministry} | 
                    <strong>Applicant:</strong> {app_type} | 
                    <strong>Fees:</strong> {fees}
                </p>
                <p style="margin: 5px 0 0 0; line-height: 1.4; color: #222;">{desc}</p>
            </div>
            """)
            
        change_details_html = "\n".join(html_details)
        
        # Update baseline status file to include the new UIDs plus keep the old ones
        updated_uids = old_uids.copy()
        updated_uids.update(current_uids)
        
        # Clean up very old UIDs if necessary to keep state file size reasonable
        # Since we only keep keys, even 5000 records is tiny, but let's keep it clean
        if len(updated_uids) > 1000:
            # Sort by date and keep newest 1000
            sorted_keys = sorted(updated_uids.keys(), key=lambda k: updated_uids[k], reverse=True)
            updated_uids = {k: updated_uids[k] for k in sorted_keys[:1000]}

        new_state = {"uids": updated_uids}
        with open(STATUS_FILE, 'w') as f:
            json.dump(new_state, f, indent=2)
            
        write_github_output("changed", "true")
        write_github_output("change_summary", f"{len(new_items)} New FOI Release(s)")
        
        # Sanitize HTML for GitHub output by replacing newlines or escaping if necessary,
        # but modern actions read multi-line outputs using delimiter patterns.
        # However, to be completely safe, we can write it to a file or output it directly.
        # Let's write the HTML body block to an environment file or handle it in GitHub Actions.
        # Wait! To avoid multiline string encoding issues in GITHUB_OUTPUT, 
        # we can write it to a temporary file and read it in the workflow or use the heredoc format!
        # Heredoc in GITHUB_OUTPUT:
        # EOF=$(dd if=/dev/urandom bs=15 count=1 2>/dev/null | base64)
        # echo "change_details<<$EOF" >> "$GITHUB_OUTPUT"
        # echo "..." >> "$GITHUB_OUTPUT"
        # echo "$EOF" >> "$GITHUB_OUTPUT"
        # Let's write it in Python using heredoc!
        output_file = os.environ.get('GITHUB_OUTPUT')
        if output_file:
            import uuid
            delimiter = f"DELIMITER_{uuid.uuid4().hex}"
            with open(output_file, 'a') as f:
                f.write(f"change_details<<{delimiter}\n")
                f.write(f"{change_details_html}\n")
                f.write(f"{delimiter}\n")
    else:
        print("No changes detected.")
        write_github_output("changed", "false")

if __name__ == "__main__":
    main()
