# LinkedIn Job Scrapper 🚀

Automatically scrape LinkedIn for new internship opportunities in software, data, analytics, BI, and related fields, and get instant email notifications for new matches!

---

## Features

-  **Automated LinkedIn Scraping:** Checks for new jobs every 10 minutes.
-  **Email Notifications:** Get notified instantly when a new relevant internship is posted.
-  **Duplicate Detection:** Never receive the same job twice-tracks all seen jobs.
-  **Customizable Filters:** Easily change keywords and locations to match your interests.
-  **Secure Email Sending:** Uses SSL and supports Gmail App Passwords.

---

## Prerequisites

- Python 3.7 or higher
- Gmail account with [App Passwords enabled](https://support.google.com/accounts/answer/185833?hl=en) (for sending emails)
- The following Python packages:
  - `requests`
  - `beautifulsoup4`
  - `dotend`

---

## Installation

1. **Clone this repository:**
Clone this repository:
   ```sh
   git clone https://github.com/jelb30/Linkedin-Job-Scrapper.git
   cd Linkedin-Job-Scrapper
   ```

## Usage

Simply run the script:

- The script will run continuously, checking for new jobs every 10 minutes.
- When a new matching job is found, you’ll receive an email notification with the job title, location, and link.

---

## Customization

- **Keywords:**  
  Edit the `KEYWORDS` list in the script to match your preferred roles (e.g., "Backend Developer Intern", "Data Analyst Internship", etc.).

- **Location Filtering:**  
  Update the `US_LOCATIONS` list to focus on specific states, cities, or "Remote" jobs.

- **Scraping Frequency:**  
  Change the `time.sleep(300)` value at the end of the script for a different interval (e.g., `600` for 10 minutes).

---

## Example Output
💼 Software Engineer Intern | New York City Metropolitan Area
🌐 https://www.linkedin.com/jobs/view/software-engineer-intern-at-somecompany-1234567890
✅✅ Description Matched!!

## Legal & Disclaimer

This script is for educational and personal use only.  
- Do not use it for commercial purposes.
- Respect LinkedIn’s [Terms of Service](https://www.linkedin.com/legal/user-agreement).
- Excessive scraping may result in your IP/account being blocked.

## Future Improvments

We can different keyword matching algorithms for better performance and efficient job filtering. Like Regex, Fuzzy Matching, Token Matching and Semantic Matching.
