import os
import re
import sys
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SEARCH_URL = "https://www.consumerbewarelist.mgs.gov.on.ca/en/CBL/searchresult?product=Ticket%20Sales&isSearchAll=False"
BASE_URL = "https://www.consumerbewarelist.mgs.gov.on.ca"
STATUS_FILE = "status_ontario.json"

def write_github_output(name, value):
    output_file = os.environ.get('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"{name}={value}\n")

def write_github_output_multiline(name, value):
    output_file = os.environ.get('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"{name}<<EOF\n{value}\nEOF\n")

def fetch_company_details(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching details from {url}: {e}", file=sys.stderr)
        return None
        
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', class_='table')
    details = {}
    if table:
        for row in table.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if th and td:
                key = th.get_text(strip=True)
                # Clean up nested html and extra whitespace
                val = ' '.join(td.get_text().split()).strip()
                details[key] = val
    return details

def main():
    # 1. Load last known state
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r') as f:
                old_state = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load status_ontario.json: {e}", file=sys.stderr)
            old_state = {"companies": {}}
    else:
        old_state = {"companies": {}}
        
    old_companies = old_state.get("companies", {})
    
    # 2. Fetch main search results
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(SEARCH_URL, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching search results: {e}", file=sys.stderr)
        sys.exit(2)
        
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        print("Error: Could not find results table on the page.", file=sys.stderr)
        sys.exit(3)
        
    # 3. Find all company links
    links = table.find_all('a', href=re.compile(r'/en/CBL/businessdetail/', re.I))
    
    current_companies = {}
    print(f"Found {len(links)} company entries in Ticket Sales.")
    
    for a in links:
        name = a.get_text(strip=True)
        path = a['href']
        detail_url = urljoin(BASE_URL, path)
        
        print(f"Fetching details for '{name}'...")
        details = fetch_company_details(detail_url)
        if details is None:
            # Fall back to empty details if subpage fetch fails, to prevent entire script failing
            details = {}
            
        current_companies[name] = {
            "url": detail_url,
            "details": details
        }
        
    # 4. Compare states
    added = []
    removed = []
    modified = []
    
    for name, info in current_companies.items():
        if name not in old_companies:
            added.append((name, info))
        else:
            old_info = old_companies[name]
            if info["details"] != old_info.get("details"):
                diffs = []
                for k, v in info["details"].items():
                    old_v = old_info.get("details", {}).get(k, "")
                    if v != old_v:
                        diffs.append(f"  * **{k}**: changed from '{old_v}' to '{v}'")
                modified.append((name, info, diffs))
                
    for name, info in old_companies.items():
        if name not in current_companies:
            removed.append((name, info))
            
    has_changes = len(added) > 0 or len(removed) > 0 or len(modified) > 0
    
    if has_changes:
        summary_lines = []
        email_lines = []
        
        if added:
            summary_lines.append(f"Added {len(added)} new company/companies.")
            email_lines.append("<h3>New Companies Added:</h3>")
            for name, info in added:
                email_lines.append(f"<p><strong>{name}</strong> - <a href='{info['url']}'>View Details</a></p>")
                email_lines.append("<ul>")
                for k, v in info["details"].items():
                    if v:
                        email_lines.append(f"  <li><strong>{k}</strong>: {v}</li>")
                email_lines.append("</ul>")
                
        if removed:
            summary_lines.append(f"Removed {len(removed)} company/companies.")
            email_lines.append("<h3>Companies Removed:</h3>")
            for name, info in removed:
                email_lines.append(f"<p><strong>{name}</strong> (no longer on list)</p>")
                
        if modified:
            summary_lines.append(f"Updated details for {len(modified)} company/companies.")
            email_lines.append("<h3>Company Details Updated:</h3>")
            for name, info, diffs in modified:
                email_lines.append(f"<p><strong>{name}</strong> - <a href='{info['url']}'>View Details</a></p>")
                email_lines.append("<ul>")
                for diff in diffs:
                    # Clean markdown tags for html email
                    clean_diff = diff.replace('**', '').replace('  * ', '<li>').strip() + '</li>'
                    email_lines.append(f"  {clean_diff}")
                email_lines.append("</ul>")
                
        summary_text = " / ".join(summary_lines)
        email_text = "\n".join(email_lines)
        
        print(f"CHANGES DETECTED: {summary_text}")
        
        # Save updated state
        new_state = {"companies": current_companies}
        with open(STATUS_FILE, 'w') as f:
            json.dump(new_state, f, indent=2)
            
        write_github_output("changed", "true")
        write_github_output("change_summary", summary_text)
        write_github_output_multiline("change_details", email_text)
    else:
        print("No changes detected on Ontario Consumer Beware List (Ticket Sales).")
        write_github_output("changed", "false")

if __name__ == "__main__":
    main()
