import os
import pathlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
SCREENSHOT_DIR = pathlib.Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def test_homepage_loads():
    driver = create_driver()

    try:
        driver.get(BASE_URL)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Replace this with something meaningful in your app
        assert "html" in driver.page_source.lower()

    except Exception:
        driver.save_screenshot(str(SCREENSHOT_DIR / "homepage_failure.png"))
        raise

    finally:
        driver.quit()
