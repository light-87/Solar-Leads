# PM Surya Ghar Vendor Scraper

Extract registered vendor information (Name, Phone, Email) from all states and districts from the [PM Surya Ghar Portal](https://pmsuryaghar.gov.in/#/registered-vendors) using Selenium browser automation.

## Quick Start

```powershell
# Install dependencies
pip install -r requirements.txt

# Run scraper (visible browser)
python scraper.py

# Run in headless mode
python scraper.py --headless

# Test mode (1 state, 1 district)
python scraper.py --test-mode

# Resume from specific state
python scraper.py --start-state "Madhya Pradesh"
```

## Output

Files are saved in the `output/` directory:
- `vendors.csv` - All vendor data
- `vendors.xlsx` - Excel with state-wise sheets

### Data Fields
| Field | Description |
|-------|-------------|
| state | State name |
| district | District name |
| name | Vendor name |
| phone | Phone number |
| email | Email address |
| scraped_at | Timestamp |

## Configuration

Edit `config.py` to adjust:
- `HEADLESS_MODE` - Run without browser window
- `DELAY_BETWEEN_STATES` - Delay between states (default: 2s)
- `DELAY_BETWEEN_DISTRICTS` - Delay between districts (default: 1.5s)

## Troubleshooting

**ChromeDriver issues**: The scraper uses `webdriver-manager` to auto-download the correct ChromeDriver.

**Page not loading**: Check the screenshots in `output/` folder for debugging.

**Timeout errors**: Increase `PAGE_LOAD_TIMEOUT` in `config.py`.
