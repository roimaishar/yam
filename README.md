# YAM Online Calendar Scraper
## Club Activity Monitoring

Monitor YAM club activities (e.g., workshops, certifications, guided sails) and get notified only when activities become newly available (i.e., when the "הרשמה" button appears) or when a new activity appears with registration open.

### Commands

```
# Scrape club activities for N days (no notifications)
python -m app.main club scrape [days]

# Start continuous monitoring for N days ahead (checks every 30m by default)
python -m app.main club monitor [days] [--interval <minutes>]

# Run a one-time check (useful in CI)
python -m app.main club check [days]
```

Examples:
```bash
# Scrape next 14 days of club activities
python -m app.main club scrape 14

# Monitor club activities every 15 minutes
python -m app.main club monitor 14 --interval 15

# One-time check for the next 7 days
python -m app.main club check 7
```

### Slack channels

- Boat slot notifications use `SLACK_WEBHOOK_URL` (and optionally category-specific webhooks).
- Club activity notifications use `SLACK_WEBHOOK_URL_CLUB` to route to a dedicated channel (e.g., `#activities`). If `SLACK_WEBHOOK_URL_CLUB` is not set, the generic `SLACK_WEBHOOK_URL` is used as a fallback.

### First run behavior (important)

- On the first ever run (local or CI), the monitor establishes a baseline of club activities and does not send notifications.
- From the second run onward, notifications are sent only when an existing activity becomes available or a new activity appears with registration available.
- State is persisted in `app/data/club_previous_slots.json` and `app/data/club_notified_slots.json`.


Automated solution for scraping calendar slots from the YAM Online customer portal.

## Project Overview

This scraper automates the process of extracting available boats slots from the YAM Online calendar system. It navigates through the calendar interface, collects slot data for specified dates, and saves the information in a structured JSON format for further analysis or integration with other systems.

## Project Structure

```
yam/
├── app/
│   ├── data/             # Scraped data and cookies storage
│   ├── forecasts/        # Weather and marine forecast modules
│   │   └── swell_forecast.py # Handles wave and wind forecasts
│   ├── monitors/         # Monitoring modules
│   │   ├── slot_monitor.py    # Monitors for new available boat slots
│   │   ├── club_monitor.py    # Monitors for newly available club activities
│   │   └── slack_notifier.py  # Handles Slack notifications
│   ├── scrapers/         # Scraping modules
│   │   ├── cookie_scraper.py  # Handles authentication and calendar scraping
│   │   └── club_scraper.py    # Scrapes club activities from the club calendar
│   ├── utils/            # Utility modules
│   │   ├── config.py     # Configuration constants and URL definitions
│   │   └── filter_slots.py    # Filters slots based on criteria
│   └── main.py           # Main entry point for running the scraper
├── requirements.txt      # Python dependencies
├── run_scraper.sh        # Shell script for easy execution
└── .env                  # Environment variables (credentials)
```

## Key Files

- `cookie_scraper.py`: Core scraping functionality using Playwright
- `slot_monitor.py`: Monitors for new available boat slots and sends notifications to Slack
- `club_monitor.py`: Monitors for newly available club activities and sends notifications to Slack
- `slack_notifier.py`: Handles sending notifications to Slack with mobile-friendly format
- `swell_forecast.py`: Fetches and processes marine forecast data (waves, wind, UV index, visibility, moon phase)
- `config.py`: Configuration settings and file paths
- `main.py`: Command-line interface for running the scraper and monitor
- `all_slots.json`: Output file containing all scraped calendar slots
- `previous_slots.json`: Tracking file for slot monitoring
- `club_previous_slots.json`: Tracking file for club activity monitoring
- `club_notified_slots.json`: Tracking file to avoid duplicate club notifications

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your credentials:
   ```
   YAM_USERNAME=your_username
   YAM_PASSWORD=your_password
   SLACK_WEBHOOK_URL=your_slack_webhook_url  # Optional, for monitoring notifications
   SLACK_WEBHOOK_URL_CLUB=your_activities_channel_webhook_url  # Optional, for club activity notifications to #activities
   STORM_GLASS_KEY=your_stormglass_api_key  # Required for accurate weather forecasts
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

### Slot Monitoring with Slack Notifications

The application includes a monitoring service that checks for new available boat slots and sends notifications to a Slack channel when they appear:

```
python -m app.main monitor [days] [options]
```

Options:
- `days`: Number of days to monitor (default: 14)
- `--interval`: Check interval in minutes (default: 30)
- `--time-range`: Filter slots within a specific time range (e.g., "9:00-17:00")
- `--service-type`: Filter slots for a specific boat type
- `--setup`: Show Slack webhook setup instructions
- `--once`: Run the monitor once and exit (useful for scheduled tasks)

Examples:
```bash
# Monitor for 7 days with default settings
python -m app.main monitor 7

# Monitor with 15-minute intervals for a specific boat type
python -m app.main monitor --interval 15 --service-type "נאווה"

# Monitor for slots between 9:00 and 17:00
python -m app.main monitor --time-range "9:00-17:00"

# Show Slack setup instructions
python -m app.main monitor --setup

# Run the monitor once and exit
python -m app.main monitor --once
```

#### Setting up Slack Notifications

To receive notifications in Slack:

1. Go to https://api.slack.com/apps and click "Create New App"
2. Choose "From scratch" and give your app a name (e.g., "YAM Slot Monitor")
3. Select the workspace where you want to receive notifications
4. In the left sidebar, click on "Incoming Webhooks"
5. Toggle "Activate Incoming Webhooks" to On
6. Click "Add New Webhook to Workspace"
7. Choose the channel where you want to receive notifications
8. Copy the Webhook URL that is generated
9. Add this URL to your .env file:
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX
```

If you also want a dedicated channel for club activity notifications (e.g., `#activities`), create another webhook and add it to your `.env`:
```
SLACK_WEBHOOK_URL_CLUB=https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/YYYYYYYYYYYYYYYYYYYYYYYY
```

For detailed setup instructions:
```
python -m app.main monitor --setup
```

### Feature: Enhanced Mobile-Friendly Notifications

The Slack notifications sent by this application are designed for optimal mobile viewing and include comprehensive weather data:

- **Mobile-Optimized Format**: Compact, English-only notifications optimized for mobile devices
- **Accurate Location**: Weather data from exact Herzliya Marina coordinates (32.164°N, 34.791°E)
- **Wave Height Indicators**: 🏝️ (calm), 🌊 (moderate), 🌊🌊 (large)
- **Wind Speed Indicators**: 🍃 (light), 💨 (moderate), 🌪️ (strong)
- **Visibility Indicators**: 🌫️ (poor visibility), 👁️ (good visibility), 🔭 (excellent visibility)
- **Moon Phase**: Shown for evening/night slots using standard moon phase emojis (🌑, 🌒, 🌓, etc.)
- **Direct Booking Links**: Each slot has a clickable link for immediate booking
- **Streamlined Design**: Focused on individual slot details without redundant general forecasts

Example notification:
```
🚣 2 New Boat Slots Available! 🚣

Monday, 7 April 2025:
- 10:00 - 13:00: Nava 450 UV7🏝️🌪️🌫️
- 20:00 - 23:00: Roni UV7🏝️🌪️🌫️🌓
```

For detailed information about marine weather features, see the [Forecasts Documentation](app/forecasts/README.md).

## Running with GitHub Actions

This project includes a GitHub Actions workflow that automatically runs the monitor at regular intervals:

1. **Setup steps**:
   - Fork this repository or create your own from the source code
   - Go to your repository's "Settings" → "Secrets and variables" → "Actions"
   - Add the following repository secrets:
     - `YAM_USERNAME` - Your YAM Online username
     - `YAM_PASSWORD` - Your YAM Online password
     - `SLACK_WEBHOOK_URL` - Slack webhook for boat slot notifications (e.g., `#yam_monitor`)
     - `SLACK_WEBHOOK_URL_CLUB` - Slack webhook for club activity notifications (e.g., `#activities`)
     - `STORM_GLASS_KEY` - StormGlass API key for accurate weather forecasts

2. **Workflow file**:
   - The workflow file is located at `.github/workflows/scraper.yml`
   - It runs the monitor every 15 minutes
   - It also commits any changes to the slot data back to the repository

3. **GitHub Actions workflow file**:
   - The workflow file is already included at `.github/workflows/scraper.yml`
   - This configures the scraper to run every 15 minutes
   - It also commits any changes to the slot data back to the repository

### Adjusting the monitoring frequency

You can adjust how often the GitHub Actions workflow runs by editing the cron schedule in `.github/workflows/scraper.yml`:

```yaml
schedule:
  - cron: '*/15 * * * *'  # Run every 15 minutes
```

For example, to run every hour instead:
```yaml
schedule:
  - cron: '0 * * * *'  # Run every hour at minute 0
```

### Resource Usage Considerations

When running with the 15-minute frequency:

1. **GitHub Actions Minutes**: 
   - For public repositories: No impact (unlimited minutes)
   - For private repositories: Approximately 2,880 minutes per month (may exceed the free tier's 2,000 minutes)

2. **API Usage**:
   - Weather data is cached for 6 hours regardless of run frequency
   - No additional impact on external APIs

3. **Website Impact**:
   - More frequent scraping means more requests to the YAM Online website
   - Consider adjusting frequency if you notice any issues with access

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

### Browser Automation

The scraper uses Playwright for browser automation. In CI environments (GitHub Actions), browsers are launched in headless mode automatically. This ensures compatibility with environments that don't have a display server.

### Slot Monitoring

The slot monitoring system continuously checks for newly available boat slots:

1. **Monitoring Process**:
   - Runs at configurable intervals (default: 15 minutes)
   - Scrapes the calendar for available slots
   - Compares current slots with previously recorded slots
   - Identifies newly available slots
   - Sends notifications only for new slots

2. **Filtering Capabilities**:
   - Time range filtering (e.g., only slots between 9:00-17:00)
   - Boat type filtering (e.g., only specific boat models)
   - Combines multiple filters for precise monitoring

3. **State Management**:
   - Stores previously seen slots in `previous_slots.json`
   - Tracks already notified slots to prevent duplicate notifications
   - Persists state between monitoring runs

### Slack Integration

The monitoring system integrates with Slack for real-time notifications:

1. **Notification System**:
   - Uses Slack's incoming webhooks for reliable delivery
   - Formats messages with clear, readable slot information
   - Includes direct booking link for quick action

2. **Message Format**:
   - Highlights date, time, and boat type for each available slot
   - Groups multiple slots in a single notification when appropriate
   - Uses emoji and formatting for improved readability

### Cookie Management

The scraper implements a sophisticated cookie-based authentication system with security best practices:

1. **Initial Authentication**:
   - On first run, attempts to log in using credentials from `.env`
   - If auto-login succeeds, saves cookies to the configured location
   - If auto-login fails, opens a visible browser window for manual login
   - After manual login, saves the authenticated session cookies

2. **Cookie Reuse**:
   - On subsequent runs, loads cookies from the configured location
   - Applies cookies to the browser context before navigating to protected pages
   - Avoids the need for repeated logins, making the scraper more efficient

3. **Session Expiry Handling**:
   - Detects when cookies are expired by checking if redirected to login page
   - Automatically initiates re-authentication when expired cookies are detected
   - After successful re-authentication, updates the cookie file with fresh cookies
   - Resumes the scraping process from where it left off

4. **Secure Cookie Storage**:
   - **Security**: Cookie files are never committed to the repository (`.gitignore`)
   - **Local Development**: Cookies stored in `cookies/yam_cookies.json` by default
   - **CI/GitHub Actions**: Uses temporary directory via `YAM_COOKIES_PATH` environment variable
   - **Custom Location**: Set `YAM_COOKIES_PATH` environment variable to override default location
   - Contains session data including authentication tokens in Playwright-compatible JSON format

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
       "service_type": "נאווה 450",
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
- `previous_slots.json` - Tracks previously seen slots for monitoring
- `notified_slots.json` - Tracks slots that have already been notified
- `yam_cookies.json` - Saved authentication cookies

## Dependencies

- Python 3.8+
- Playwright (for browser automation)
- Requests (for Slack notifications)
- python-dotenv (for environment variable management)

## Development Workflow

This project utilizes GitHub Actions to run the scraper automatically on a schedule. The data files (all_slots.json, previous_slots.json, notified_slots.json) are tracked in the repository to maintain persistent data between automated runs. To avoid conflicts between local development and automated runs, follow this workflow:

### Git Workflow for Local Development

1. **Before starting work**:
   ```bash
   git pull origin master
   ```

2. **After making code changes, but before committing**:
   ```bash
   # Discard any local data changes
   git checkout -- app/data/*.json
   
   # Add only code files
   git add your-code-files.py
   
   # Commit your changes
   git commit -m "Your meaningful commit message"
   ```

3. **Before pushing**:
   ```bash
   git pull --rebase origin master
   git push origin master
   ```

This workflow ensures that local development doesn't interfere with the data files managed by GitHub Actions.

### Handling Merge Conflicts

If you encounter merge conflicts with data files:

1. Discard local data changes:
   ```bash
   git checkout -- app/data/*.json
   ```

2. Remove any untracked data files:
   ```bash
   git clean -f app/data/new_slots_*.json
   ```

3. Pull with rebase:
   ```bash
   git pull --rebase origin master
   ```

4. Push your changes:
   ```bash
   git push origin master
   ```

Following this workflow will help maintain a clean repository with both your code changes and the latest data from the automated scraper runs.
