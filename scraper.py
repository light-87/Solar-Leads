"""
PM Surya Ghar Vendor Data Scraper
Extracts registered vendor information (Name, Phone, Email) from all states and districts.

Based on actual page structure:
- State dropdown with search input
- District dropdown 
- Vendor accordion cards that expand to show contact details
- Email format: name[at]domain[dot]com

Usage:
    python scraper.py              # Run full scrape
    python scraper.py --headless   # Headless mode
    python scraper.py --test-mode  # Test with 1 state/district
    python scraper.py --start-state "MAHARASHTRA"
"""

import argparse
import os
import sys
import time
import json
import random
import re
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

import config


class VendorScraper:
    """Scraper for PM Surya Ghar registered vendors."""
    
    def __init__(self, headless: bool = False, test_mode: bool = False, start_state: str = None, district: str = None, min_installations: int = 1):
        self.headless = headless
        self.test_mode = test_mode
        self.start_state = start_state
        self.target_district = district
        self.min_installations = min_installations
        self.driver = None
        self.wait = None
        self.all_vendors: List[Dict] = []
        self.current_state = ""
        self.current_district = ""
        self.stats = {
            "states_processed": 0,
            "districts_processed": 0,
            "vendors_found": 0,
            "errors": 0
        }
        
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    def setup_driver(self):
        """Initialize Chrome WebDriver."""
        print("🚀 Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument(f"--window-size={config.WINDOW_SIZE[0]},{config.WINDOW_SIZE[1]}")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Remove webdriver flag
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """
        })
        
        self.driver.set_window_size(1920, 1080)
        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        self.wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)
        
        print("✅ WebDriver ready!")
    
    def delay(self, min_sec: float = 0.5, max_sec: float = 1.0):
        """Random delay."""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def navigate_to_vendor_page(self):
        """Navigate to the vendor page."""
        print(f"🌐 Opening {config.BASE_URL}...")
        self.driver.get(config.BASE_URL)
        
        print(f"  ⏳ Waiting for page load ({config.INITIAL_PAGE_WAIT}s)...")
        time.sleep(config.INITIAL_PAGE_WAIT)
        
        # Wait for State dropdown to appear
        try:
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Select State')]"))
            )
            print("✅ Page loaded - State dropdown visible!")
            self.take_screenshot("page_loaded")
            return True
        except:
            print("  ⚠️ State dropdown not found, refreshing page...")
            self.driver.refresh()
            time.sleep(config.INITIAL_PAGE_WAIT)
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Select State')]")))
                print("✅ Page loaded after refresh!")
                return True
            except:
                print("  ❌ Failed to load page properly.")
                self.take_screenshot("page_error_final")
                return False

    def click_dropdown(self, dropdown_element):
        """Helper to click a dropdown safely."""
        try:
            # Try clicking the label or chevron specifically
            try:
                trigger = dropdown_element.find_element(By.CSS_SELECTOR, ".p-dropdown-label, .p-dropdown-trigger")
                self.driver.execute_script("arguments[0].click();", trigger)
            except:
                self.driver.execute_script("arguments[0].click();", dropdown_element)
            return True
        except Exception as e:
            print(f"      ⚠️ Error clicking dropdown: {e}")
            return False
    
    def get_all_states(self) -> List[str]:
        """Get list of all states from dropdown."""
        print("\n📍 Getting all states...")
        states = []
        
        try:
            # Click anywhere outside first to ensure clean state
            self.driver.find_element(By.TAG_NAME, "body").click()
            self.delay(0.5, 0.8)
            
            # Find and click the State dropdown
            selectors = [
                "p-dropdown[formcontrolname='state']",
                "//p-dropdown[@formcontrolname='state']",
                "//*[contains(text(), 'Select State')]/ancestor::p-dropdown",
                "//span[contains(text(), 'Select State')]/ancestor::div[contains(@class, 'p-dropdown')]",
                "//p-dropdown"  # Last resort
            ]
            
            state_dropdown = None
            for sel in selectors:
                try:
                    if sel.startswith("//"):
                        state_dropdown = self.driver.find_element(By.XPATH, sel)
                    else:
                        state_dropdown = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if state_dropdown.is_displayed():
                        print(f"    🔍 Found dropdown with selector: {sel}")
                        break
                except:
                    continue

            if not state_dropdown:
                print("    ⚠️ Could not find State dropdown")
                self.take_screenshot("no_state_dropdown")
                return []
                
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", state_dropdown)
            self.delay(0.5, 1.0)
            
            self.click_dropdown(state_dropdown)
            self.delay(2, 3)
            
            self.take_screenshot("state_dropdown_open")
            
            # Get all state options
            options = []
            try:
                # Wait for panel to appear
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".p-dropdown-panel, .p-dropdown-items-wrapper")))
                self.delay(0.5, 1)
                
                # Find all li elements that look like options
                options = self.driver.find_elements(By.XPATH, "//li[contains(@class, 'p-dropdown-item')] | //li[@role='option'] | //p-dropdown-item//li")
                
                if not options:
                    # Very broad search
                    options = self.driver.find_elements(By.TAG_NAME, "li")
            except Exception as e:
                print(f"      ⚠️ Error waiting for state options: {e}")
                options = self.driver.find_elements(By.TAG_NAME, "li")
            
            for opt in options:
                try:
                    text = opt.text.strip()
                    if not text:
                        text = opt.get_attribute("innerText").strip()
                    
                    if text and text.upper() not in ['SELECT STATE', 'SELECT', ''] and len(text) > 1:
                        # Exclude common noise
                        if any(k in text.upper() for k in ['HOME', 'CONSUMER', 'VENDOR', 'DISCOM', 'ACHIEVEMENT']):
                            continue
                        states.append(text)
                except:
                    continue
            
            # Remove possible duplicates from noise
            states = list(dict.fromkeys(states))
            print(f"  ✅ Found {len(states)} states")
            
            # Close dropdown by pressing Escape
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            self.delay(0.5, 0.8)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            self.take_screenshot("error_states")
        
        return states
    
    def select_state(self, state_name: str) -> bool:
        """Select a state by clicking it directly from dropdown."""
        print(f"\n🏛️ Selecting state: {state_name}")
        
        try:
            # First, click body to reset any open dropdowns
            self.driver.find_element(By.TAG_NAME, "body").click()
            self.delay(0.5, 0.8)
            
            # Find state dropdown
            selectors = [
                "p-dropdown[formcontrolname='state']",
                "//p-dropdown[@formcontrolname='state']",
                "//*[contains(text(), 'Select State')]/ancestor::p-dropdown",
                "//span[contains(text(), 'Select State')]/ancestor::div[contains(@class, 'p-dropdown')]",
                "//p-dropdown"
            ]
            state_dropdown = None
            for sel in selectors:
                try:
                    if sel.startswith("//"):
                        state_dropdown = self.driver.find_element(By.XPATH, sel)
                    else:
                        state_dropdown = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if state_dropdown.is_displayed():
                        break
                except:
                    continue

            if not state_dropdown:
                 print(f"    ⚠️ Could not find State dropdown for selection")
                 return False

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", state_dropdown)
            self.delay(0.5, 1.0)
            self.click_dropdown(state_dropdown)
            self.delay(1, 1.5)
            
            # Look for search input and type to filter
            try:
                search_input = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'p-dropdown-panel')]//input"
                                                           " | //input[contains(@class, 'p-dropdown-filter')]"))
                )
                search_input.clear()
                # Type character by character to trigger search
                for char in state_name:
                    search_input.send_keys(char)
                    time.sleep(0.05)
                self.delay(1, 1.5)
                
                # Find and click the state option
                option = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, 
                        f"//li[contains(@class, 'p-dropdown-item')]//span[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{state_name.upper()}')]"
                        f" | //li[contains(@class, 'p-dropdown-item')][contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{state_name.upper()}')]"
                        f" | //li[contains(@role, 'option')][contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{state_name.upper()}')]"
                    ))
                )
                self.driver.execute_script("arguments[0].click();", option)
                
                # Wait for dropdown to close
                self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".p-dropdown-panel")))
            except Exception as e:
                print(f"    ⚠️ Filter selection failed, trying ENTER: {e}")
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                self.delay(0.5, 1)
                # Press ESC to be sure it's closed
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            
            self.current_state = state_name
            print(f"  ✅ Selected: {state_name}")
            self.delay(1.5, 2)  # Wait for district dropdown to populate
            self.take_screenshot(f"state_selected_{state_name[:8]}")
            return True
            
        except Exception as e:
            print(f"  ❌ Error selecting state: {e}")
            self.take_screenshot("error_select_state")
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            except:
                pass
            return False
    
    def get_all_districts(self) -> List[str]:
        """Get list of all districts for current state."""
        print("  📍 Getting districts...")
        districts = []
        
        try:
            self.delay(1.5, 2)  # Wait for district dropdown to be populated
            
            # Find and click district dropdown
            district_dropdown = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "p-dropdown[formcontrolname='district']"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", district_dropdown)
            self.delay(0.5, 1.0)
            
            try:
                district_dropdown.click()
            except:
                self.driver.execute_script("arguments[0].click();", district_dropdown)
            
            self.delay(2, 3)
            
            # Get all district options
            options = []
            try:
                # Wait for panel
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".p-dropdown-panel, .p-dropdown-items-wrapper")))
                self.delay(0.5, 1)
                
                options = self.driver.find_elements(By.XPATH, "//li[contains(@class, 'p-dropdown-item')] | //li[@role='option'] | //p-dropdown-item//li")
                
                if not options:
                    options = self.driver.find_elements(By.TAG_NAME, "li")
            except Exception as e:
                print(f"      ⚠️ Error waiting for district options: {e}")
                options = self.driver.find_elements(By.TAG_NAME, "li")
            
            for opt in options:
                try:
                    text = opt.text.strip()
                    if not text:
                        text = opt.get_attribute("innerText").strip()
                        
                    if text and text.upper() not in ['SELECT DISTRICT', 'SELECT', ''] and len(text) > 1:
                        # Exclude noise
                        if any(k in text.upper() for k in ['HOME', 'CONSUMER', 'VENDOR', 'DISCOM', 'ACHIEVEMENT']):
                            continue
                        districts.append(text)
                except:
                    continue
            
            # Deduplicate
            districts = list(dict.fromkeys(districts))
            print(f"  ✅ Found {len(districts)} districts")
            
            # Close dropdown
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            self.delay(0.3, 0.5)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        return districts
    
    def select_district(self, district_name: str) -> bool:
        """Select a district."""
        print(f"  🏘️ Selecting district: {district_name}")
        
        try:
            # First, click body to reset
            self.driver.find_element(By.TAG_NAME, "body").click()
            self.delay(0.5, 0.8)
            
            # Find district dropdown
            selectors = [
                "p-dropdown[formcontrolname='district']",
                "//p-dropdown[@formcontrolname='district']",
                "//*[contains(text(), 'Select District')]/ancestor::p-dropdown",
                "//span[contains(text(), 'Select District')]/ancestor::div[1]"
            ]
            district_dropdown = None
            for sel in selectors:
                try:
                    if sel.startswith("//"):
                        district_dropdown = self.driver.find_element(By.XPATH, sel)
                    else:
                        district_dropdown = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if district_dropdown.is_displayed():
                        break
                except:
                    continue

            if not district_dropdown:
                 print("    ⚠️ Could not find District dropdown")
                 return False

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", district_dropdown)
            self.delay(0.5, 1.0)
            
            try:
                district_dropdown.click()
            except:
                self.driver.execute_script("arguments[0].click();", district_dropdown)
                
            self.delay(1.5, 2)
            
            # Filter and select
            try:
                search_input = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'p-dropdown-panel')]//input"))
                )
                search_input.clear()
                for char in district_name:
                    search_input.send_keys(char)
                    time.sleep(0.05)
                self.delay(1, 1.5)
                
                option = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, 
                        f"//li[contains(@class, 'p-dropdown-item')]//span[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{district_name.upper()}')]"
                        f" | //li[contains(@class, 'p-dropdown-item')][contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{district_name.upper()}')]"
                    ))
                )
                self.driver.execute_script("arguments[0].click();", option)
            except:
                print(f"    ⚠️ Filter district failed, trying ENTER")
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            
            self.current_district = district_name
            print(f"    ✅ Selected: {district_name}")
            self.take_screenshot(f"district_selected_{district_name[:8]}")
            return True
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            except:
                pass
            return False
    
    def click_apply_button(self):
        """Click the Apply button to load vendors."""
        try:
            apply_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//button[contains(., 'Apply')] | //button[contains(text(), 'Apply')]"
                ))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", apply_btn)
            self.delay(0.5, 0.8)
            apply_btn.click()
            print("    ✅ Clicked Apply")
            time.sleep(5)  # Wait for vendors to load
            return True
        except Exception as e:
            print(f"    ⚠️ Apply button error: {e}")
            return False
    
    def convert_email_format(self, email_text: str) -> str:
        """Convert email from [at][dot] format to standard format."""
        if not email_text:
            return ""
        email = email_text.replace('[at]', '@').replace('[dot]', '.')
        email = email.replace('(at)', '@').replace('(dot)', '.')
        return email.strip()
    
    def extract_vendors(self, start_from: int = 0) -> List[Dict]:
        """Extract vendors by expanding each card and reading content.
        
        CRITICAL: Extract data IMMEDIATELY after expansion, before moving to next card.
        PrimeNG accordion collapses previous cards when a new one is clicked.
        """
        vendors = []
        
        try:
            # Wait for any loaders to disappear
            try:
                self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading-overlay, .p-progress-spinner, .p-blockui")))
            except:
                pass
                
            self.delay(2, 3)  
            
            # Find vendor cards using p-accordion structure
            tabs = self.driver.find_elements(By.TAG_NAME, "p-accordiontab")
            
            if not tabs:
                tabs = self.driver.find_elements(By.CSS_SELECTOR, ".p-accordion-tab, [class*='accordion']")
            
            if not tabs:
                print("    ⚠️ No p-accordiontab found, trying XPath fallback...")
                headers = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'NO. OF INSTALLATIONS')]/ancestor::*[5]")
                if headers:
                    print(f"    📊 Found {len(headers)} vendor headers via XPath")
                    tabs = headers
                else:
                    print("    ❌ Could not find any vendor cards!")
                    self.take_screenshot("no_vendor_cards_found")
                    with open(os.path.join(config.OUTPUT_DIR, "debug_page_source.html"), "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    return []
            
            target_tabs = tabs[start_from:]
            print(f"    📊 Processing {len(target_tabs)} vendor cards (from index {start_from})...")
            
            # Clear debug file at start
            try:
                with open(os.path.join(config.OUTPUT_DIR, "debug_vendors.txt"), "w", encoding="utf-8") as f:
                    f.write(f"Extraction started at {datetime.now().isoformat()}\n")
            except:
                pass
            
            for i, tab in enumerate(target_tabs):
                try:
                    # Re-find tabs to avoid stale element issues after clicking
                    if i > 0:
                        try:
                            current_tabs = self.driver.find_elements(By.TAG_NAME, "p-accordiontab")
                            if not current_tabs:
                                current_tabs = self.driver.find_elements(By.CSS_SELECTOR, ".p-accordion-tab")
                            if current_tabs and len(current_tabs) > start_from + i:
                                tab = current_tabs[start_from + i]
                        except:
                            pass
                    
                    # Scroll card into view
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
                    self.delay(0.5, 0.8)
                    
                    # Get company name from header
                    company_name = ""
                    header_lines = tab.text.strip().split('\n')
                    if header_lines and len(header_lines[0]) > 2:
                        company_name = header_lines[0].strip()
                    
                    print(f"      [{i+1}/{len(target_tabs)}] Processing: {company_name[:30]}...")
                    
                    # Check if already expanded
                    current_text = tab.text.strip().upper()
                    is_expanded = "EMAIL" in current_text or "CONTACT NUMBER" in current_text
                    
                    if not is_expanded:
                        # Click to expand - try multiple selectors
                        click_selectors = [
                            ".p-accordion-header-link",
                            ".p-accordion-header a",
                            ".p-accordion-header",
                            "a[role='button']",
                            "a",
                        ]
                        
                        clicked = False
                        for selector in click_selectors:
                            try:
                                click_elem = tab.find_element(By.CSS_SELECTOR, selector)
                                self.driver.execute_script("arguments[0].click();", click_elem)
                                clicked = True
                                self.delay(0.3, 0.5)
                                break
                            except:
                                continue
                        
                        if not clicked:
                            try:
                                self.driver.execute_script("arguments[0].click();", tab)
                                clicked = True
                            except:
                                print(f"        ⚠️ Could not click card {company_name[:20]}")
                                continue
                        
                        # WAIT for content to load with better detection
                        max_wait_time = 8  # seconds
                        poll_interval = 0.3
                        start_time = time.time()
                        expansion_successful = False
                        
                        while time.time() - start_time < max_wait_time:
                            try:
                                # Re-read the tab text
                                current_text = tab.text.strip().upper()
                                if "EMAIL" in current_text or "CONTACT NUMBER" in current_text:
                                    expansion_successful = True
                                    break
                                    
                                # Also check for content div visibility
                                try:
                                    content_div = tab.find_element(By.CSS_SELECTOR, ".p-accordion-content, .p-toggleable-content")
                                    if content_div.is_displayed():
                                        content_text = content_div.text.strip().upper()
                                        if "EMAIL" in content_text or "CONTACT" in content_text:
                                            expansion_successful = True
                                            break
                                except:
                                    pass
                            except StaleElementReferenceException:
                                # Re-fetch the tab
                                try:
                                    current_tabs = self.driver.find_elements(By.TAG_NAME, "p-accordiontab")
                                    if current_tabs and len(current_tabs) > start_from + i:
                                        tab = current_tabs[start_from + i]
                                except:
                                    break
                            except:
                                pass
                            time.sleep(poll_interval)
                        
                        if not expansion_successful:
                            print(f"        ⚠️ Expansion timeout for {company_name[:20]}, trying retry...")
                            # One more click attempt
                            try:
                                header = tab.find_element(By.CSS_SELECTOR, ".p-accordion-header-link, .p-accordion-header a, a")
                                self.driver.execute_script("arguments[0].click();", header)
                                time.sleep(2)
                            except:
                                pass
                    
                    # IMMEDIATELY extract data while card is still expanded
                    full_text = ""
                    try:
                        full_text = tab.text.strip()
                    except StaleElementReferenceException:
                        try:
                            current_tabs = self.driver.find_elements(By.TAG_NAME, "p-accordiontab")
                            if current_tabs and len(current_tabs) > start_from + i:
                                tab = current_tabs[start_from + i]
                                full_text = tab.text.strip()
                        except:
                            pass
                    
                    # Debug output
                    try:
                        with open(os.path.join(config.OUTPUT_DIR, "debug_vendors.txt"), "a", encoding="utf-8") as f:
                            is_expanded_now = "EMAIL" in full_text.upper() or "CONTACT NUMBER" in full_text.upper()
                            f.write(f"\n{'='*50}\n")
                            f.write(f"CARD #{i+1}: {company_name}\n")
                            f.write(f"EXPANDED: {is_expanded_now}\n")
                            f.write(f"FULL TEXT:\n{full_text}\n")
                            f.write(f"{'='*50}\n")
                    except:
                        pass
                    
                    if not full_text:
                        print(f"        ⚠️ Empty text for {company_name[:20]}")
                        continue
                    
                    # Parse vendor data
                    vendor = self.parse_vendor_from_text(full_text)
                    if vendor:
                        if not vendor["company_name"] and company_name:
                            vendor["company_name"] = company_name
                        
                        # Log extraction result
                        has_contact = vendor.get("phone") or vendor.get("email")
                        if vendor.get("phone") and vendor.get("email"):
                            print(f"        ✅ {vendor['company_name'][:25]}: ☎️{vendor['phone']} 📧{vendor['email'][:15]}...")
                        elif vendor.get("phone"):
                            print(f"        ✅ {vendor['company_name'][:25]}: ☎️{vendor['phone']}")
                        elif vendor.get("email"):
                            print(f"        📧 {vendor['company_name'][:25]}: {vendor['email']}")
                        else:
                            print(f"        ⚠️ {vendor['company_name'][:25]}: No contact info")
                        
                        vendors.append(vendor)
                    
                    # Small delay before next card to let UI settle
                    self.delay(0.3, 0.5)
                    
                except Exception as e:
                    print(f"      ⚠️ Error processing card {start_from + i}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"    ✅ Extracted {len(vendors)} vendors from this batch")
            
            # Summary stats
            vendors_with_phone = sum(1 for v in vendors if v.get("phone"))
            vendors_with_email = sum(1 for v in vendors if v.get("email"))
            print(f"    📊 Stats: {vendors_with_phone} with phone, {vendors_with_email} with email")
            
            if not vendors and start_from == 0:
                print("    ⚠️ No vendors extracted. Dumping debug info...")
                self.take_screenshot("no_vendors_extracted")
                try:
                    with open(os.path.join(config.OUTPUT_DIR, "no_vendors_page_dump.html"), "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                except Exception as e:
                    print(f"    ⚠️ Failed to dump HTML: {e}")
            
        except Exception as e:
            print(f"    ❌ Error during extraction: {e}")
            import traceback
            traceback.print_exc()
        
        return vendors
    
    def parse_vendor_from_text(self, text: str) -> Optional[Dict]:
        """Parse vendor info from text block."""
        try:
            vendor = {
                "state": self.current_state,
                "district": self.current_district,
                "company_name": "",
                "brand_name": "",
                "contact_person": "",
                "email": "",
                "phone": "",
                "installations": "",
                "capacity_kwp": "",
                "scraped_at": datetime.now().isoformat()
            }
            
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            for i, line in enumerate(lines):
                line_upper = line.upper()
                
                # Company name parsing
                if i == 0:
                    # Ignore if the first line is just a label or common generic header
                    if len(line) < 3 or any(k in line_upper for k in ['CONTACT', 'EMAIL', 'INSTALLATIONS', 'CAPACITY', 'VENDOR', 'DETAILS']):
                        continue
                    vendor["company_name"] = line
                
                # If we still haven't found a company name, try the second line
                if not vendor["company_name"] and i == 1:
                     if not any(k in line_upper for k in ['CONTACT', 'EMAIL', 'INSTALLATIONS', 'CAPACITY']):
                        vendor["company_name"] = line
                if 'BRAND NAME' in line_upper:
                    brand_match = re.search(r'BRAND NAME[:\s]*(.+)', line, re.I)
                    if brand_match:
                        vendor["brand_name"] = brand_match.group(1).strip()
                
                # Contact person - usually after "CONTACT PERSON" or similar
                if 'CONTACT PERSON' in line_upper:
                    match = re.search(r'CONTACT PERSON[:\s]*(.+)', line, re.I)
                    if match:
                        vendor["contact_person"] = match.group(1).strip()
                    elif i + 1 < len(lines):
                        vendor["contact_person"] = lines[i+1]
                
                # Email with [at][dot] format or standard
                email_match = re.search(r'[\w\.-]+(?:\[at\]|@)[\w\.-]+(?:\[dot\]|\.)\w+', line, re.I)
                if email_match:
                    vendor["email"] = self.convert_email_format(email_match.group())
                
                # Phone number - look for "CONTACT NUMBER" or 10-digit patterns
                # Look for patterns like +91 12345 67890, 01234567890, 1234567890
                # Using a very permissive regex for 10-digit numbers starting with 6-9
                clean_line = line.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                phone_match = re.search(r'(?<!\d)([6-9]\d{9})(?!\d)', clean_line)
                
                if 'CONTACT NUMBER' in line_upper or 'MOBILE' in line_upper or 'PHONE' in line_upper:
                    if phone_match:
                        vendor["phone"] = phone_match.group(1)
                    elif i + 1 < len(lines):
                        next_line = lines[i+1].replace(' ', '').replace('-', '')
                        next_phone = re.search(r'([6-9]\d{9})', next_line)
                        if next_phone:
                            vendor["phone"] = next_phone.group(1)
                
                # Generic fallback if not found yet
                if not vendor["phone"] and phone_match:
                    vendor["phone"] = phone_match.group(1)
                
                # installations
                if 'INSTALLATIONS' in line_upper:
                    num_match = re.search(r'(\d+)', line)
                    if num_match:
                        vendor["installations"] = num_match.group(1)
                    elif i + 1 < len(lines):
                         next_line_num = re.search(r'(\d+)', lines[i+1])
                         if next_line_num:
                             vendor["installations"] = next_line_num.group(1)
                
                # Capacity
                if 'CAPACITY' in line_upper:
                    cap_match = re.search(r'(\d+(?:\.\d+)?)', line)
                    if cap_match:
                        vendor["capacity_kwp"] = cap_match.group(1)
                    elif i + 1 < len(lines):
                        next_line_cap = re.search(r'(\d+(?:\.\d+)?)', lines[i+1])
                        if next_line_cap:
                            vendor["capacity_kwp"] = next_line_cap.group(1)
            
            # Additional cleanup for company name if it's still empty
            if not vendor["company_name"] and len(lines) > 0:
                 vendor["company_name"] = lines[0]

            # Only return if we have meaningful data (at least company name)
            if vendor["company_name"]:
                return vendor
            
        except Exception:
            pass
        
        return None
    
    def parse_vendors_from_page_text(self, text: str) -> List[Dict]:
        """Parse multiple vendors from full page text."""
        vendors = []
        
        # Split by company patterns
        # Companies often end with PVT LTD, LLP, SOLUTIONS, ENERGY, SOLAR, etc.
        
        # Find all email patterns
        email_pattern = r'[\w\.-]+\[at\][\w\.-]+\[dot\]\w+|[\w\.-]+@[\w\.-]+\.\w+'
        phone_pattern = r'(?<!\d)([6-9]\d{9})(?!\d)'
        
        emails = re.findall(email_pattern, text, re.I)
        phones = re.findall(phone_pattern, text)
        
        # Create vendors from found contact info
        for i, email in enumerate(emails):
            vendor = {
                "state": self.current_state,
                "district": self.current_district,
                "company_name": "",
                "contact_person": "",
                "email": self.convert_email_format(email),
                "phone": phones[i] if i < len(phones) else "",
                "scraped_at": datetime.now().isoformat()
            }
            vendors.append(vendor)
        
        return vendors
    
    def expand_all_vendor_cards(self, start_from: int = 0):
        """Expand all vendor accordion cards one by one starting from an index."""
        try:
            # Find all accordion tabs
            tabs = self.driver.find_elements(By.TAG_NAME, "p-accordiontab")
            
            if not tabs:
                return
                
            limit = 200 if not self.test_mode else 50
            print(f"    📂 Expanding vendor cards starting from index {start_from}...")
            
            for tab in tabs[start_from:limit]:
                try:
                    # Check if already expanded
                    header = tab.find_element(By.CSS_SELECTOR, ".p-accordion-header")
                    is_expanded = "p-highlight" in header.get_attribute("class")
                    
                    if not is_expanded:
                        # Scroll into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", header)
                        self.delay(0.2, 0.4)
                        
                        header_text = tab.text.split('\n')[0][:20]
                        print(f"      📂 Clicking header {header_text}...")
                        # Robust expansion loop
                        start_wait = time.time()
                        max_retries = 3
                        retry_count = 0
                        
                        # Find content element once
                        content_elem = None
                        try:
                            content_elem = tab.find_element(By.CSS_SELECTOR, ".p-accordion-content")
                        except:
                            print(f"      ⚠️ Could not find content element for {header_text}")
                            continue # Skip this tab if content element is not found
                        
                        while time.time() - start_wait < 10 and retry_count < max_retries:
                             # Check if content is already visible
                             try:
                                 content_text = content_elem.text.strip()
                                 if content_text and ("CONTACT" in content_text.upper() or "EMAIL" in content_text.upper()):
                                     print(f"        ✅ Content loaded for {header_text}...")
                                     break
                             except:
                                 pass
                                 
                             # Not visible yet, try clicking specifically the anchor/link inside
                             print(f"      🖱️ Clicking header {header_text} (Attempt {retry_count+1})...")
                             try:
                                 # Try to find the link inside the header first
                                 try:
                                     link = header.find_element(By.TAG_NAME, "a")
                                     self.driver.execute_script("arguments[0].click();", link)
                                 except:
                                     self.driver.execute_script("arguments[0].click();", header)
                                     
                                 # Double check if we expanded
                                 self.delay(0.5, 1.0)
                                 is_expanded_now = "p-highlight" in header.get_attribute("class") or header.get_attribute("aria-expanded") == "true"
                                 if is_expanded_now:
                                     pass # Good, wait for content
                                 else:
                                     print("        ⚠️ Header did not toggle highlight/expanded state")
                                     
                             except Exception as e:
                                 print(f"      ⚠️ Click failed: {e}")
                             
                             # Wait a bit before checking/clicking again
                             self.delay(1.5, 2.5)
                             retry_count += 1
                        
                        # If still no content, dump the header HTML for debugging the selector
                        try:
                             content_text = content_elem.text.strip()
                             if not (content_text and ("CONTACT" in content_text.upper() or "EMAIL" in content_text.upper())):
                                 print(f"      ❌ Failed to expand {header_text} after retries. Dumping HTML...")
                                 with open(os.path.join(config.OUTPUT_DIR, "debug_failed_card.html"), "w", encoding="utf-8") as f:
                                     f.write(header.get_attribute('outerHTML'))
                        except:
                            pass
                        
                except Exception as e:
                    print(f"      ⚠️ Expansion error for tab: {e}")
                    continue
                    
        except Exception as e:
            print(f"    ⚠️ Error expanding cards: {e}")
    
    def scroll_and_extract_all(self) -> List[Dict]:
        """Scroll through page and extract all vendors with pagination support."""
        all_vendors = []
        
        max_pages = 50 if not self.test_mode else 2
        page_num = 1
        last_item_index = 0
        
        while page_num <= max_pages:
            print(f"    📄 Processing page {page_num}...")
            
            # Extract vendors (expansion now happens inline)
            current_page_vendors = self.extract_vendors(start_from=last_item_index)
            
            # Check for 0 installations to stop
            stop_scraping = False
            filtered_vendors = []
            for v in current_page_vendors:
                try:
                    inst_str = v.get("installations", "")
                    inst = int(inst_str) if inst_str and inst_str.isdigit() else 0
                    
                    
                    if inst >= self.min_installations:
                        filtered_vendors.append(v)
                        # Debug: Screenshot valid vendors to see why phone might be missing
                        if not v.get("phone"):
                            print(f"    📸 Taking debug screenshot for {v.get('company_name')} (Missing Phone)...")
                            safe_name = "".join(x for x in v.get("company_name", "vendor") if x.isalnum())[:20]
                            self.take_screenshot(f"debug_vendor_{safe_name}")
                    else:
                        print(f"    🛑 Vendor '{v.get('company_name')[:25]}' has {inst} installations (< {self.min_installations}). Stopping.")
                        stop_scraping = True
                        break  # Stop processing more vendors from this page
                        
                except:
                    filtered_vendors.append(v) # Keep if parsing fails but technically valid?
            
            # Dump intermediate vendors to verify extraction
            try:
                debug_csv_path = os.path.join(config.OUTPUT_DIR, "debug_page_vendors.csv")
                # Write header if file doesn't exist OR if file is empty
                write_header = not os.path.exists(debug_csv_path) or os.path.getsize(debug_csv_path) == 0
                pd.DataFrame(current_page_vendors).to_csv(debug_csv_path, mode='a', header=write_header, index=False)
            except:
                pass

            
            if stop_scraping:
                print("    🛑 Found vendor with 0 installations. Stopping pagination for this district.")
                current_page_vendors = filtered_vendors
            
            
            # Track count for next expansion
            try:
                tabs = self.driver.find_elements(By.TAG_NAME, "p-accordiontab")
                if not tabs:
                    tabs = self.driver.find_elements(By.CSS_SELECTOR, ".p-accordion-tab")
                last_item_index = len(tabs)
                print(f"    📈 Tracked {last_item_index} total vendor items")
            except:
                pass
            
            # Add unique vendors
            new_added = 0
            for v in current_page_vendors:
                # Deduplicate against all_vendors
                if not any(av["company_name"] == v["company_name"] and av["phone"] == v["phone"] for av in all_vendors):
                    all_vendors.append(v)
                    new_added += 1
            
            print(f"    ✨ Added {new_added} new vendors from page {page_num}")
            
            # Look for and click "Load More" button
            try:
                # PrimeNG might use a paginator or a 'Load More' button
                load_more_selectors = [
                    "//button[contains(., 'Load More')]",
                    "//button[contains(., 'Show More')]",
                    "//button[contains(@class, 'p-button')][.//*[contains(text(), 'More')]]",
                    "//a[contains(@class, 'p-paginator-next')]:not(.p-disabled)"
                ]
                
                load_more_btn = None
                for selector in load_more_selectors:
                    btns = self.driver.find_elements(By.XPATH, selector)
                    if btns and btns[0].is_displayed():
                        load_more_btn = btns[0]
                        break
                
                if load_more_btn:
                    print("    ⏬ Clicking 'Load More'...")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more_btn)
                    self.delay(0.5, 0.8)
                    self.driver.execute_script("arguments[0].click();", load_more_btn)
                    
                    # Wait for loading to complete
                    self.delay(3, 5)
                    page_num += 1
                else:
                    print("    🏁 No more pages found.")
                    break
            except Exception as e:
                print(f"    ⚠️ Pagination error: {e}")
                break
            
            if stop_scraping:
                break
                
        return all_vendors
    
    def save_progress(self):
        """Save collected data."""
        if not self.all_vendors:
            return
        
        df = pd.DataFrame(self.all_vendors)
        
        # CSV
        csv_path = os.path.join(config.OUTPUT_DIR, config.CSV_FILENAME)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # Excel
        try:
            excel_path = os.path.join(config.OUTPUT_DIR, config.EXCEL_FILENAME)
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='All Vendors', index=False)
        except:
            pass
        
        print(f"\n💾 Saved {len(self.all_vendors)} vendors to {csv_path}")
    
    def take_screenshot(self, name: str):
        """Take screenshot."""
        try:
            clean = "".join(c for c in name if c.isalnum() or c in ['_', '-'])
            path = os.path.join(config.OUTPUT_DIR, f"{clean}_{datetime.now().strftime('%H%M%S')}.png")
            self.driver.save_screenshot(path)
        except:
            pass
    
    def save_page_source(self, name: str):
        """Save HTML source."""
        try:
            path = os.path.join(config.OUTPUT_DIR, f"{name}.html")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
        except:
            pass
    
    def run(self):
        """Main scraping workflow."""
        print("\n" + "="*60)
        print("🌞 PM Surya Ghar Vendor Scraper")
        print("="*60)
        
        try:
            self.setup_driver()
            self.navigate_to_vendor_page()
            
            # Get all states
            states = self.get_all_states()
            
            if not states:
                print("\n❌ No states found!")
                return
            
            print(f"\n📋 States to process: {len(states)}")
            
            # Filter if starting from specific state (Fuzzy match)
            if self.start_state:
                # Try exact match first
                idx = next((i for i, s in enumerate(states) if s.upper() == self.start_state.upper()), -1)
                
                # If not found, try partial match
                if idx == -1:
                    print(f"  🔍 '{self.start_state}' not found exactly. Searching for partial match...")
                    idx = next((i for i, s in enumerate(states) if self.start_state.upper() in s.upper()), -1)
                
                if idx != -1:
                    print(f"  ✅ Starting from: {states[idx]}")
                    if self.target_district:
                        print(f"  🔒 Restricting to single state '{states[idx]}' because --district is specified.")
                        states = [states[idx]]
                    else:
                        states = states[idx:]
                else:
                    print(f"  ❌ State '{self.start_state}' not found!")
                    return
            
            if self.test_mode:
                states = states[:1]
                print("🧪 TEST MODE: 1 state only")
            
            for state_idx, state_name in enumerate(states):
                print(f"\n{'='*50}")
                print(f"📍 State {state_idx + 1}/{len(states)}: {state_name}")
                print('='*50)
                
                if not self.select_state(state_name):
                    continue
                
                districts = self.get_all_districts()
                
                if not districts:
                    print(f"  ⚠️ No districts for {state_name}")
                    continue
                
                if self.test_mode and not self.target_district:
                    districts = districts[:1]
                
                # Filter by district if specified
                if self.target_district:
                    # Fuzzy match district
                    d_idx = next((i for i, d in enumerate(districts) if self.target_district.upper() in d.upper()), -1)
                    if d_idx != -1:
                        print(f"  🎯 Target District Found: {districts[d_idx]}")
                        districts = [districts[d_idx]]
                    else:
                        print(f"  ⚠️ Target district '{self.target_district}' not found in {state_name}")
                        continue
                
                for dist_idx, district_name in enumerate(districts):
                    print(f"\n  District {dist_idx + 1}/{len(districts)}: {district_name}")
                    
                    if not self.select_district(district_name):
                        continue
                    
                    # Click Apply to load vendors
                    print("    🖱️ Clicking Apply button...")
                    self.take_screenshot(f"before_apply_{district_name[:10]}")
                    self.click_apply_button()
                    self.delay(2, 3)
                    self.take_screenshot(f"after_apply_{district_name[:10]}")
                    
                    # Extract vendors
                    
                    # Extract vendors
                    vendors = self.scroll_and_extract_all()
                    self.all_vendors.extend(vendors)
                    
                    self.stats["districts_processed"] += 1
                    self.stats["vendors_found"] += len(vendors)
                    
                    print(f"    ✅ {len(vendors)} vendors extracted")
                    
                    # Save per-district CSV file
                    if vendors:
                        try:
                            districts_dir = os.path.join(config.OUTPUT_DIR, "districts")
                            os.makedirs(districts_dir, exist_ok=True)
                            safe_state = "".join(c for c in state_name if c.isalnum() or c in [' ', '-', '_']).strip().replace(' ', '_')
                            safe_district = "".join(c for c in district_name if c.isalnum() or c in [' ', '-', '_']).strip().replace(' ', '_')
                            district_csv = os.path.join(districts_dir, f"{safe_state}_{safe_district}.csv")
                            pd.DataFrame(vendors).to_csv(district_csv, index=False, encoding='utf-8-sig')
                            print(f"    💾 Saved to: {safe_district}.csv ({len(vendors)} vendors)")
                        except Exception as e:
                            print(f"    ⚠️ Failed to save district file: {e}")
                    
                    time.sleep(config.DELAY_BETWEEN_DISTRICTS)
                
                self.stats["states_processed"] += 1
                self.save_progress()
                time.sleep(config.DELAY_BETWEEN_STATES)
            
            self.save_progress()
            
            print("\n" + "="*60)
            print("📊 SCRAPING COMPLETE!")
            print("="*60)
            print(f"  States: {self.stats['states_processed']}")
            print(f"  Districts: {self.stats['districts_processed']}")
            print(f"  Vendors: {self.stats['vendors_found']}")
            print(f"\n📁 Output: {os.path.abspath(config.OUTPUT_DIR)}")
            
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted - saving progress...")
            self.save_progress()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            self.save_progress()
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔒 Browser closed.")


def main():
    parser = argparse.ArgumentParser(description='PM Surya Ghar Vendor Scraper')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--test-mode', action='store_true')
    parser.add_argument('--start-state', type=str, help="Start from this state (fuzzy match)")
    parser.add_argument('--district', type=str, help="Filter for this district (fuzzy match)")
    
    parser.add_argument('--min-installations', type=int, default=1, help="Minimum installations to include (default: 1)")
    
    args = parser.parse_args()
    
    VendorScraper(
        headless=args.headless,
        test_mode=args.test_mode,
        start_state=args.start_state,
        district=args.district,
        min_installations=args.min_installations
    ).run()


if __name__ == "__main__":
    main()
