# YAM Online Calendar Scraper

Automated solution for scraping calendar slots from the YAM Online customer portal.

## Project Overview

This scraper automates the process of extracting available boats slots from the YAM Online calendar system. It navigates through the calendar interface, collects slot data for specified dates, and saves the information in a structured JSON format for further analysis or integration with other systems.

## Project Structure

```
yam/
├── app/
│   ├── data/             # Scraped data and cookies storage
│   ├── monitors/         # Monitoring modules
│   │   ├── slot_monitor.py    # Monitors for new available slots
│   │   └── slack_notifier.py  # Handles Slack notifications
│   ├── scrapers/         # Scraping modules
│   │   └── cookie_scraper.py  # Handles authentication and calendar scraping
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
- `slot_monitor.py`: Monitors for new available slots and sends notifications
- `slack_notifier.py`: Handles sending notifications to Slack
- `config.py`: Configuration settings and file paths
- `main.py`: Command-line interface for running the scraper and monitor
- `all_slots.json`: Output file containing all scraped calendar slots
- `previous_slots.json`: Tracking file for slot monitoring

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
7. Choose the channel where you want to post notifications
8. Copy the Webhook URL that is generated
9. Add this URL to your .env file:
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX
```

For detailed setup instructions:
```
python -m app.main monitor --setup
```

#### Running the Monitor Continuously

To keep the monitor running continuously:

1. **Using tmux (recommended for macOS/Linux)**:
   ```bash
   tmux new -s yam-monitor
   python -m app.main monitor
   # Press Ctrl+B then D to detach (monitor keeps running)
   # To reattach: tmux attach -t yam-monitor
   ```

2. **As a background process**:
   ```bash
   nohup python -m app.main monitor > monitor.log 2>&1 &
   ```

## Features

- **Automated Monitoring**: Checks for available boat slots at YAM Online
- **Customizable Filters**: Filter slots by date, time, and boat type
- **Slack Notifications**: Get notified when new slots become available
- **GitHub Actions Integration**: Run the monitor automatically on a schedule
- **Data Persistence**: Track which slots have been seen and notified

### Slack Notifications

The system sends beautiful, well-formatted notifications to Slack when new boat slots are available:

- **Organized by Date**: Slots are grouped by date for easy reading
- **Tabular Format**: Time and boat type displayed in a clean table layout
- **Limited Display**: Shows a maximum of 12 slots to keep notifications concise
- **Total Count**: Always shows the total number of available slots, even when limiting display

To set up Slack notifications:

1. Create a Slack app and webhook URL in your workspace
2. Add the webhook URL to your `.env` file as `SLACK_WEBHOOK_URL`
3. For GitHub Actions, add the webhook URL as a repository secret

Example notification format:
```
🚣 15 New Boat Slots Available! 🚣
Found at 2025-03-14 23:16:37 (showing 12 of 15)
-------------------------------------------
📅 שישי, 14 מרץ 2025
| Time          | Boat Type     |
|---------------|---------------|
| 09:00 - 12:00 | מישל          |
| 12:00 - 15:00 | קיאק זוגי      |
-------------------------------------------
```

## Running with GitHub Actions

You can use GitHub Actions to run the scraper automatically every 30 minutes without needing to keep your computer running. This is a free solution that leverages GitHub's CI/CD platform.

### Setup GitHub Actions

1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/yam-scraper.git
   git push -u origin main
   ```

2. **Add repository secrets**:
   - Go to your GitHub repository
   - Navigate to Settings > Secrets and variables > Actions
   - Add the following secrets:
     - `YAM_USERNAME`: Your YAM website username
     - `YAM_PASSWORD`: Your YAM website password
     - `SLACK_WEBHOOK_URL`: Your Slack webhook URL

3. **GitHub Actions workflow file**:
   - The workflow file is already included at `.github/workflows/scraper.yml`
   - This configures the scraper to run every 30 minutes
   - It also commits any changes to the slot data back to the repository

4. **Repository permissions**:
   - The workflow needs permission to push changes back to your repository
   - This is configured in the workflow file with `permissions: contents: write`
   - If you're using a fork or organization repository, you may need to:
     - Go to Settings > Actions > General
     - Under "Workflow permissions", select "Read and write permissions"
     - Click "Save"

### How it works

1. The workflow runs every 30 minutes based on the cron schedule
2. It checks out your code, installs dependencies, and runs the scraper
3. Any new slot data is committed back to the repository
4. Notifications are sent to your Slack channel when new slots are found

### Manual trigger

You can also trigger the workflow manually:
1. Go to the "Actions" tab in your GitHub repository
2. Select the "YAM Boat Slot Monitor" workflow
3. Click "Run workflow" and then "Run workflow" again

### Viewing logs

To see the results of each run:
1. Go to the "Actions" tab in your GitHub repository
2. Click on the most recent "YAM Boat Slot Monitor" workflow run
3. Expand the "Run slot monitor once" step to see the output

### Customizing the schedule

To change how often the scraper runs, edit the cron expression in `.github/workflows/scraper.yml`:
```yaml
schedule:
  - cron: '*/30 * * * *'  # Run every 30 minutes
```

For example, to run every hour instead:
```yaml
schedule:
  - cron: '0 * * * *'  # Run every hour at minute 0
```

### Running the monitor once

We've added a `--once` flag to the monitor command that runs the check once and then exits. This is particularly useful for GitHub Actions:

```bash
python -m app.main monitor 14 --once
```

This command:
- Checks for new slots once (no continuous monitoring)
- Looks ahead for the next 14 days
- Sends notifications for any new slots found
- Exits after completion

### Security considerations

When using GitHub Actions with a public repository:

1. **Never commit sensitive information**:
   - Keep your `.env` file in `.gitignore`
   - Use GitHub Secrets for credentials

2. **Secure your data**:
   - If you don't want slot data to be publicly visible, use a private repository
   - Alternatively, modify the workflow to use GitHub Artifacts instead of committing data files

3. **Dependency security**:
   - We've configured the requirements.txt to use secure versions of dependencies
   - GitHub's Dependabot will alert you about security vulnerabilities

### Troubleshooting GitHub Actions

If your GitHub Actions workflow isn't working as expected:

1. **Check workflow logs**:
   - Go to the Actions tab in your repository
   - Click on the failed workflow run
   - Examine the logs for error messages

2. **Verify secrets**:
   - Make sure all required secrets (YAM_USERNAME, YAM_PASSWORD, SLACK_WEBHOOK_URL) are set correctly
   - Secrets are case-sensitive

3. **Test locally first**:
   - Run `python -m app.main monitor 14 --once` locally to verify it works
   - Fix any issues before pushing to GitHub

4. **Common issues**:
   - "404 no_service" error with Slack: Check your webhook URL
   - "Unknown" boat types: Fixed in the latest version to display service_type
   - Workflow getting stuck: Fixed by using the `--once` flag
   - Permission denied errors: Make sure workflow has write permissions (see Setup step 4)

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

### Slot Monitoring

The slot monitoring system continuously checks for newly available boat slots:

1. **Monitoring Process**:
   - Runs at configurable intervals (default: 30 minutes)
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
