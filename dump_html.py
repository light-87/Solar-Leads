"""
Dump HTML after loading vendors to inspect structure.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

def dump_vendor_html():
    print("🚀 Setting up Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
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
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    # Remove webdriver flag
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """
    })
    
    try:
        print("🌐 Opening page...")
        driver.get("https://pmsuryaghar.gov.in/#/registered-vendors")
        
        print("⏳ Waiting 30s for full load...")
        time.sleep(30)
        
        # Select first state
        print("📍 Selecting state...")
        state_dropdown = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "p-dropdown[formcontrolname='state']")))
        driver.execute_script("arguments[0].click();", state_dropdown)
        time.sleep(2)
        
        # Type and select first state
        search = driver.find_element(By.XPATH, "//div[contains(@class, 'p-dropdown-panel')]//input")
        search.send_keys("ANDAMAN")
        time.sleep(1)
        search.send_keys(Keys.ENTER)
        time.sleep(3)
        
        # Select district
        print("📍 Selecting district...")
        district_dropdown = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "p-dropdown[formcontrolname='district']")))
        driver.execute_script("arguments[0].click();", district_dropdown)
        time.sleep(2)
        
        search = driver.find_element(By.XPATH, "//div[contains(@class, 'p-dropdown-panel')]//input")
        search.send_keys("NORTH")
        time.sleep(1)
        search.send_keys(Keys.ENTER)
        time.sleep(2)
        
        # Click Apply
        print("🖱️ Clicking Apply...")
        apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Apply')]")))
        apply_btn.click()
        
        print("⏳ Waiting for vendors to load...")
        time.sleep(10)
        
        # Now dump the full HTML
        print("💾 Saving full HTML...")
        os.makedirs("output", exist_ok=True)
        with open("output/vendor_page_full.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        
        # Find and describe vendor cards
        print("\n🔍 Looking for vendor cards...")
        
        # Try various selectors
        selectors_to_try = [
            ("p-accordiontab", "PrimeNG Accordion Tab"),
            (".p-accordion-tab", "Accordion Tab Class"),
            ("[class*='vendor']", "Vendor class"),
            ("[class*='card']", "Card class"),
            ("[class*='accordion']", "Accordion class"),
            ("mat-expansion-panel", "Material Expansion Panel"),
            (".mat-expansion-panel", "Material Expansion Panel Class"),
        ]
        
        for selector, name in selectors_to_try:
            try:
                if selector.startswith("//"):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"  ✅ Found {len(elements)} elements with selector: {selector} ({name})")
                    # Dump first element's HTML
                    with open(f"output/element_{name.replace(' ', '_')}.html", "w", encoding="utf-8") as f:
                        f.write(elements[0].get_attribute('outerHTML'))
            except Exception as e:
                print(f"  ❌ {selector}: {e}")
        
        # Look for blue headers specifically
        print("\n🔍 Looking for blue vendor headers...")
        blue_headers = driver.find_elements(By.XPATH, "//*[contains(text(), 'RMC AKSHAY')]/ancestor::*[1]")
        if blue_headers:
            print(f"  Found parent of RMC AKSHAY: {blue_headers[0].tag_name}")
            with open("output/vendor_header_parent.html", "w", encoding="utf-8") as f:
                # Get the larger ancestor
                ancestor = blue_headers[0]
                for _ in range(5):
                    try:
                        ancestor = ancestor.find_element(By.XPATH, "..")
                    except:
                        break
                f.write(ancestor.get_attribute('outerHTML'))
            print("  Saved to output/vendor_header_parent.html")
        
        # Click first vendor to expand and dump again
        print("\n🖱️ Trying to click first vendor to expand...")
        try:
            first_vendor_header = driver.find_element(By.XPATH, "//*[contains(text(), 'RMC AKSHAY')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_vendor_header)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", first_vendor_header)
            time.sleep(3)
            
            with open("output/vendor_page_after_click.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("  Saved after-click HTML")
        except Exception as e:
            print(f"  Click failed: {e}")
        
        driver.save_screenshot("output/final_state.png")
        print("\n✅ Done! Check output/ folder for HTML dumps.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    dump_vendor_html()
