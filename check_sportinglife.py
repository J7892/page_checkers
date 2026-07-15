import os
import sys
import json
import time
import cloudscraper
from bs4 import BeautifulSoup

URL = "https://www.sportinglife.ca/en-CA/equipment/cycle/road-bikes/diverge-e5-bike/25930239-00271735.html"
STATUS_FILE = "status_sportinglife.json"

def write_github_output(name, value):
    output_file = os.environ.get('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"{name}={value}\n")

def fetch_price():
    max_retries = 3
    backoff = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            scraper = cloudscraper.create_scraper(delay=10)
            response = scraper.get(URL, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            product_data_input = soup.find("input", id="product-data")
            if not product_data_input:
                raise ValueError("Could not find element <input id=\"product-data\">")
                
            value_str = product_data_input.get("value")
            if not value_str:
                raise ValueError("Empty value attribute on product-data input")
                
            data = json.loads(value_str)
            price_str = data.get("price")
            if price_str is None:
                raise ValueError("Price field missing in product data JSON")
                
            # Convert to float for numeric comparison
            price = float(price_str)
            name = data.get("name", "Diverge E5 Bike")
            availability = data.get("availability", "Unknown")
            return price, name, availability
            
        except Exception as e:
            print(f"Warning: Attempt {attempt} to fetch price failed: {e}", file=sys.stderr)
            if attempt == max_retries:
                print(f"Error: Failed to retrieve price after {max_retries} attempts.", file=sys.stderr)
                sys.exit(2)
            sleep_time = backoff ** attempt
            print(f"Retrying in {sleep_time} seconds...", file=sys.stderr)
            time.sleep(sleep_time)

def main():
    # 1. Load last known state
    is_initial_run = not os.path.exists(STATUS_FILE)
    old_price = None
    old_availability = None
    
    if not is_initial_run:
        try:
            with open(STATUS_FILE, 'r') as f:
                state_data = json.load(f)
                old_price = state_data.get("price")
                old_availability = state_data.get("availability")
        except Exception as e:
            print(f"Warning: Failed to load status_sportinglife.json: {e}", file=sys.stderr)
            is_initial_run = True

    # 2. Fetch current price and info
    print("Fetching current product info...")
    price, name, availability = fetch_price()
    print(f"Current price: ${price:.2f} | Status: {availability}")

    # 3. Handle initial baseline run
    if is_initial_run:
        print("Initial run: saving baseline price and availability.")
        new_state = {
            "price": price,
            "availability": availability,
            "name": name,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(STATUS_FILE, 'w') as f:
            json.dump(new_state, f, indent=2)
        write_github_output("changed", "false")
        return

    # 4. Compare states
    price_changed = old_price != price
    availability_changed = old_availability != availability
    
    if price_changed or availability_changed:
        print("CHANGE DETECTED!")
        change_desc_lines = []
        if price_changed:
            change_desc_lines.append(f"Price changed from ${old_price:.2f} to ${price:.2f}")
        if availability_changed:
            change_desc_lines.append(f"Availability changed from '{old_availability}' to '{availability}'")
            
        summary_text = " & ".join(change_desc_lines)
        print(summary_text)

        # Save new state
        new_state = {
            "price": price,
            "availability": availability,
            "name": name,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(STATUS_FILE, 'w') as f:
            json.dump(new_state, f, indent=2)

        write_github_output("changed", "true")
        write_github_output("change_summary", summary_text)
        write_github_output("old_price", f"{old_price:.2f}")
        write_github_output("new_price", f"{price:.2f}")
        write_github_output("old_availability", old_availability)
        write_github_output("new_availability", availability)
    else:
        print("No changes detected.")
        write_github_output("changed", "false")

if __name__ == "__main__":
    main()
