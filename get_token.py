"""
Launches a browser for EdStem login (supports SSO) and extracts the X-Token
from the /api/user network request, then saves it to .env.

Flow:
  1. EdStem login form  → select region, enter email, click start
  2. sso.gatech.edu     → auto-fill GT username/password, click submit
  3. Duo MFA            → user approves on phone
  4. Trust browser popup→ auto-click trust-browser-button
  5. EdStem loads       → capture X-Token from /api/user request header
"""
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv, set_key
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

ENV_PATH = Path(__file__).parent / ".env"
COUNTRY = os.environ.get("EDSTEM_COUNTRY", "us").lower()
LOGIN_URL = f"https://{COUNTRY}.edstem.org/login"
GT_SSO_HOST = os.environ.get("GT_SSO_HOST", "sso.gatech.edu")


def get_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--start-maximized")
    # Enable CDP performance logs so we can intercept network request headers
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=options)


def fill_edstem_login_form(driver: webdriver.Chrome, email: str, country: str):
    """Select region, enter email, and click the start button on the EdStem login page."""
    wait = WebDriverWait(driver, 10)

    dropdown_el = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "select.start-region-select"))
    )
    Select(dropdown_el).select_by_value(country)

    email_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']"))
    )
    email_input.clear()
    email_input.send_keys(email)

    driver.find_element(By.CSS_SELECTOR, ".start-btn").click()


def try_fill_gt_sso(driver: webdriver.Chrome) -> bool:
    """If on the GT SSO page, auto-fill credentials. Returns True if filled."""
    if GT_SSO_HOST not in driver.current_url:
        return False

    username = os.environ.get("GT_USERNAME", "")
    password = os.environ.get("GT_PASSWORD", "")
    if not username or not password:
        return False

    try:
        wait = WebDriverWait(driver, 5)
        wait.until(EC.presence_of_element_located((By.ID, "username")))
        driver.find_element(By.ID, "username").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, ".btn-submit").click()
        print("GT credentials submitted — approve Duo MFA on your phone.")
        return True
    except Exception:
        return False


def try_click_trust_browser(driver: webdriver.Chrome) -> bool:
    """Click the trust-browser-button if it is present. Returns True if clicked."""
    try:
        btn = driver.find_element(By.ID, "trust-browser-button")
        btn.click()
        print("Trusted browser — waiting for EdStem to load.")
        return True
    except Exception:
        return False


def get_token_from_network(driver: webdriver.Chrome) -> str | None:
    """Scan Chrome performance logs for the X-Token header in the /api/user request."""
    try:
        logs = driver.get_log("performance")
        for entry in logs:
            message = json.loads(entry["message"])["message"]
            if message.get("method") != "Network.requestWillBeSent":
                continue
            request = message["params"]["request"]
            if "/api/user" in request.get("url", ""):
                token = request["headers"].get("X-Token")
                if token:
                    return token
    except Exception:
        pass
    return None


def main():
    email = os.environ.get("EDSTEM_EMAIL", "")
    print(f"Opening browser for EdStem login ({COUNTRY.upper()} region).")
    if email:
        print(f"Account: {email}")

    driver = get_driver()
    driver.get(LOGIN_URL)

    # Step 1: fill EdStem login form
    try:
        fill_edstem_login_form(driver, email, COUNTRY)
        print("EdStem login form submitted.")
    except Exception as e:
        print(f"Could not auto-fill login form: {e}")
        print("Please complete the login manually in the browser.")

    gt_filled = False
    trust_clicked = False
    token = None

    print("Waiting for login... (up to 5 minutes)")
    for _ in range(300):
        # Step 2: auto-fill GT SSO once redirected
        if not gt_filled:
            gt_filled = try_fill_gt_sso(driver)

        # Step 3 (Duo): nothing to automate — user acts on phone

        # Step 4: click trust-browser popup after Duo approval
        if gt_filled and not trust_clicked:
            trust_clicked = try_click_trust_browser(driver)

        # Step 5: once back on EdStem, capture token from /api/user network request
        if "edstem.org" in driver.current_url and "login" not in driver.current_url:
            token = get_token_from_network(driver)
            if token:
                break

        time.sleep(1)

    driver.quit()

    if not token:
        print("Login timed out or token not found.")
        return

    set_key(str(ENV_PATH), "EDSTEM_TOKEN", token)
    print(f"Token saved to {ENV_PATH}")


if __name__ == "__main__":
    main()
