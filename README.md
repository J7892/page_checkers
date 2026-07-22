# Multi-Site Compliance and Petition Monitor

This repository monitors multiple public government websites for updates, including Elections Alberta petitions and Ontario's Consumer Beware List.

---

## Monitors

### 1. Alberta Petition Tracker
* **Goal**: Monitor the financial statement status of the **"2026 A Referendum Relating to Alberta Independence"** citizen initiative petition.
* **Target URL**: [Elections Alberta Financial Disclosure](https://efpublic.elections.ab.ca/efCIPs.cfm?MID=CIP)
* **Scraper**: `check_status.py`
* **State File**: `status.txt`
* **Workflow**: `.github/workflows/monitor.yml` (Runs hourly from 7 AM to 7 PM MT).

### 2. Ontario Consumer Beware List (Ticket Sales)
* **Goal**: Monitor for new company listings and any updates to compliance orders/actions in the **Ticket Sales** category.
* **Target URL**: [Ontario Consumer Beware List - Ticket Sales](https://www.consumerbewarelist.mgs.gov.on.ca/en/CBL/searchresult?product=Ticket%20Sales&isSearchAll=False)
* **Scraper**: `check_ontario.py` (performs deep-scrapes on company detail pages)
* **State File**: `status_ontario.json`
* **Workflow**: `.github/workflows/monitor_ontario.yml` (Runs weekdays at 10 AM, 1 PM, and 5 PM ET).

### 3. Foreign Influence Commissioner Monitor
* **Goal**: Monitor updates on the **Office of the Foreign Influence Commissioner of Canada** landing page.
* **Target URL**: [Office of the Foreign Influence Commissioner of Canada](https://www.canada.ca/en/foreign-influence-commissioner.html)
* **Scraper**: `check_foreign_influence.py`
* **State File**: `status_foreign_influence.json`
* **Workflow**: `.github/workflows/monitor_foreign_influence.yml` (Runs daily at 12:00 PM UTC).

---

## Configuration

To receive email notifications when a change is detected, add the following secrets to your GitHub repository under **Settings** -> **Secrets and variables** -> **Actions**:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `MAIL_TO` | The recipient email address for alerts | `user@example.com` |
| `MAIL_SERVER` | SMTP Server | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP Port | `587` or `465` |
| `MAIL_USERNAME` | SMTP Username | `your-email@gmail.com` |
| `MAIL_PASSWORD` | SMTP Password / App Password | `your-app-password` |

### Fallback Alert

If you do **not** configure these SMTP secrets, the workflows will still commit updates to your repository but will intentionally fail at the end of the run. This triggers GitHub's default email notification system to email you about the failed workflow, ensuring you are notified of the change without having to set up SMTP.

---

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the Alberta check:
   ```bash
   python check_status.py
   ```
3. Run the Ontario check:
   ```bash
   python check_ontario.py
   ```
4. Run the Foreign Influence Commissioner check:
   ```bash
   python check_foreign_influence.py
   ```
