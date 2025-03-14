# YAM Online Calendar Scraper

Automated solution for scraping calendar slots from the YAM Online customer portal.

## Project Structure

```
app/
├── data/             # Scraped data and cookies storage
├── scrapers/         # Scraping modules
│   └── cookie_scraper.py
└── utils/            # Utility modules
    ├── config.py
    └── extract_data.py
```

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
python -m app.main scrape
```
or
```
python -m app.main calendar [days]
```

Scrapes available appointment slots from the calendar page for the specified number of days (default: 14):
- Attempts to log in automatically using your credentials
- Saves authentication cookies for future use
- If automatic login fails, it opens a browser for one-time manual login
- On subsequent runs, it uses saved cookies without manual intervention
- Navigates through each day in the calendar
- Extracts date, time, service type, and availability status for each slot
- Saves all data in a single JSON file for analysis
- Example: `python -m app.main calendar 30` to scrape the next 30 days

### Data Extraction
```
python -m app.main extract
```
Processes scraped HTML files and extracts structured data into a single JSON file.

### Scheduling Automated Scraping

To schedule the scraper to run periodically:

#### On macOS/Linux (using cron):
```bash
# Edit crontab
crontab -e

# Add this line to run daily at 8 AM
0 8 * * * cd /path/to/yam && python -m app.main scrape
```

#### On Windows (using Task Scheduler):
Create a batch file `run_scraper.bat`:
```batch
cd /d C:\path\to\yam
python -m app.main scrape
```
Then add it to Task Scheduler.

## Output Files

All scraped data is saved in the `app/data/` directory with the following fixed filenames:
- `calendar_slots_DATE.html` - HTML content for each calendar day
- `all_slots.json` - All extracted calendar slot data
- `all_calendar_html.json` - All HTML content
- `all_extracted_data.json` - All extracted data
- `yam_cookies.json` - Saved authentication cookies
