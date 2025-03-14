# YAM Online Calendar Scraper

Automated solution for scraping calendar slots from the YAM Online customer portal.

## Project Overview

This scraper automates the process of extracting available boats slots from the YAM Online calendar system. It navigates through the calendar interface, collects slot data for specified dates, and saves the information in a structured JSON format for further analysis or integration with other systems.

## Project Structure

```
yam/
├── app/
│   ├── data/             # Scraped data and cookies storage
│   ├── scrapers/         # Scraping modules
│   │   └── cookie_scraper.py  # Handles authentication and calendar scraping
│   ├── utils/            # Utility modules
│   │   └── config.py     # Configuration constants and URL definitions
│   └── main.py           # Main entry point for running the scraper
├── requirements.txt      # Python dependencies
├── run_scraper.sh        # Shell script for easy execution
└── .env                  # Environment variables (credentials)
```

## Key Files

- `cookie_scraper.py`: Core scraping functionality using Playwright
- `config.py`: Configuration settings and file paths
- `main.py`: Command-line interface for running the scraper
- `all_slots.json`: Output file containing all scraped calendar slots

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your credentials:
   ```
   YAM_USERNAME=your_username
   YAM_PASSWORD=your_password
   ```

## Usage

### Calendar Slot Scraping

```
python -m app.main calendar [days]
```

Scrapes available appointment slots from the calendar page for the specified number of days (default: 14).

Example:
```
python -m app.main calendar 7  # Scrape the next 7 days
```

Or use the shorthand command:
```
python -m app.main scrape  # Uses default 14 days
```

You can also use the provided shell script:
```
./run_scraper.sh
```

## Technical Implementation

### Scraping Process

The scraper uses Playwright, a browser automation library, to interact with the YAM Online website:

1. **Browser Automation**:
   - Uses headless Chromium browser for efficient scraping
   - Simulates user interactions like clicking, navigating, and waiting for page loads
   - Handles JavaScript-rendered content that traditional HTTP requests can't access

2. **Calendar Navigation**:
   - Locates and clicks the calendar's "next day" button to navigate through dates
   - Waits for the calendar to update between navigations
   - Extracts the current date from the page header

3. **Slot Extraction**:
   - Identifies calendar slots using CSS selectors (`.dhx_cal_event` elements)
   - Extracts data attributes and text content from each slot
   - Determines availability status by checking for the presence of order buttons

### Cookie Management

The scraper implements a sophisticated cookie-based authentication system:

1. **Initial Authentication**:
   - On first run, attempts to log in using credentials from `.env`
   - If auto-login succeeds, saves cookies to `yam_cookies.json`
   - If auto-login fails, opens a visible browser window for manual login
   - After manual login, saves the authenticated session cookies

2. **Cookie Reuse**:
   - On subsequent runs, loads cookies from `yam_cookies.json`
   - Applies cookies to the browser context before navigating to protected pages
   - Avoids the need for repeated logins, making the scraper more efficient

3. **Session Expiry Handling**:
   - Detects when cookies are expired by checking if redirected to login page
   - Automatically initiates re-authentication when expired cookies are detected
   - After successful re-authentication, updates the cookie file with fresh cookies
   - Resumes the scraping process from where it left off

4. **Cookie Storage**:
   - Cookies are stored in JSON format in the `app/data` directory
   - Contains all necessary session data including authentication tokens
   - Format is compatible with Playwright's cookie handling system

### Error Handling

The scraper includes robust error handling mechanisms:

1. **Authentication Failures**:
   - Detects login form errors and provides feedback
   - Falls back to manual authentication when automated login fails
   - Provides clear instructions for manual intervention when needed

2. **Navigation Errors**:
   - Implements timeouts and retries for page loading
   - Handles cases where calendar elements are not found
   - Gracefully exits if critical navigation actions fail

3. **Data Extraction Fallbacks**:
   - Uses multiple methods to extract date information
   - Falls back to system date calculation if page elements are not found
   - Validates extracted data before saving

### How It Works

1. **Authentication**:
   - First run: Attempts to log in automatically using credentials from `.env`
   - If automatic login fails, opens a browser for manual login
   - Saves authentication cookies for future use
   - Subsequent runs: Uses saved cookies without manual intervention

2. **Data Collection**:
   - Navigates through each day in the calendar
   - Extracts date, time, service type, and availability status for each slot
   - Saves all data in a single JSON file (`all_slots.json`)

3. **Output Format**:
   The `all_slots.json` file contains an array of slot objects with the following structure:
   ```json
   [
     {
       "date": "שישי, 14 מרץ 2025",
       "event_id": "123456",
       "time": "10:00 - 11:00",
       "service_type": "Boat Name",
       "is_available": true
     },
     ...
   ]
   ```

## Scheduling Automated Scraping

To schedule the scraper to run periodically:

### On macOS/Linux (using cron):
```bash
# Edit crontab
crontab -e

# Add this line to run daily at 8 AM
0 8 * * * cd /path/to/yam && python -m app.main scrape
```

### On Windows (using Task Scheduler):
Create a batch file `run_scraper.bat`:
```batch
cd /d C:\path\to\yam
python -m app.main scrape
```
Then add it to Task Scheduler.

## Troubleshooting

- **Authentication Issues**: If you encounter login problems, delete the `yam_cookies.json` file to force a new login session.
- **Scraping Failures**: Check that the YAM Online website structure hasn't changed. The scraper relies on specific HTML elements.
- **Browser Issues**: The scraper uses Playwright's Chromium browser. Ensure you have proper permissions and dependencies installed.
- **Session Timeouts**: If the scraper frequently needs to re-authenticate, the YAM Online site may have shortened their session timeout period.

## Output Files

All scraped data is saved in the `app/data/` directory:
- `all_slots.json` - All extracted calendar slot data in structured JSON format
- `yam_cookies.json` - Saved authentication cookies

## Dependencies

- Python 3.8+
- Playwright (for browser automation)
- BeautifulSoup4 (for HTML parsing)
- python-dotenv (for environment variable management)
