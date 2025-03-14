# YAM Online Scraper

Automated solution for scraping content from the YAM Online customer portal.

## Project Structure

```
app/
├── data/             # Scraped data and cookies storage
├── scrapers/         # Scraping modules
│   ├── cookie_scraper.py
│   └── scheduled_scraper.py
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

### Automated Scraping
```
python -m app.main scrape
```

The scraper will:
- Attempt to log in automatically using your credentials
- Save authentication cookies for future use
- Scrape all configured pages
- If automatic login fails, it will open a browser for one-time manual login
- On subsequent runs, it will use saved cookies without any manual intervention

### Calendar Slot Scraping
```
python -m app.main calendar [days]
```

Scrapes available appointment slots from the calendar page for the specified number of days (default: 14):
- Navigates through each day in the calendar
- Extracts date, time, service type, and availability status for each slot
- Saves data in JSON format for analysis
- Example: `python -m app.main calendar 30` to scrape the next 30 days

### Data Extraction
```
python -m app.main extract
```
Processes scraped HTML files and extracts structured data into JSON format.

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

## Customization

To customize which pages are scraped, edit the `get_urls_to_scrape()` function in `app/utils/config.py`.

## Output Files

Scraped files are saved in the `app/data/` directory with the following naming convention:
- `page_name_YYYYMMDD_HHMMSS.html` - HTML content of scraped pages
- `calendar_slots_DATE_YYYYMMDD_HHMMSS.html` - HTML content for each calendar day
- `all_slots_YYYYMMDD_HHMMSS.json` - Extracted calendar slot data for all days
- `extracted_slots_YYYYMMDD_HHMMSS.json` - Extracted data from calendar slots
- `yam_cookies.json` - Saved authentication cookies
