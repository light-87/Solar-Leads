"""
Configuration settings for PM Surya Ghar Vendor Scraper
"""

# Base URL
BASE_URL = "https://pmsuryaghar.gov.in/#/registered-vendors"

# Timing settings (in seconds)
PAGE_LOAD_TIMEOUT = 60
ELEMENT_WAIT_TIMEOUT = 20
INITIAL_PAGE_WAIT = 30  # Wait for Angular to fully bootstrap
ANGULAR_RENDER_WAIT = 10  # Additional wait for content rendering
DELAY_BETWEEN_STATES = 2
DELAY_BETWEEN_DISTRICTS = 1.5
DELAY_AFTER_SELECTION = 3
DELAY_BETWEEN_PAGES = 1.5

# Browser settings
HEADLESS_MODE = False  # Set to True to run without browser window
WINDOW_SIZE = (1920, 1080)

# Output settings
OUTPUT_DIR = "output"
CSV_FILENAME = "vendors.csv"
EXCEL_FILENAME = "vendors.xlsx"

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5

# Progress save interval (save every N states)
SAVE_INTERVAL = 1
