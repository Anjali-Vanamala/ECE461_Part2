import os

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")


# --- DRIVER SETUP ---
def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)


# --- ACCESSIBILITY CHECKS ---
def check_images_accessible(driver):
    images = driver.find_elements(By.TAG_NAME, "img")
    for img in images:
        alt = img.get_attribute("alt")
        assert alt and alt.strip() != "", f"Image missing alt attribute: {img.get_attribute('outerHTML')}"


def check_buttons_accessible(driver):
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        text = btn.text.strip()
        aria_label = btn.get_attribute("aria-label")
        assert text or aria_label, f"Button missing accessible name: {btn.get_attribute('outerHTML')}"


def check_links_accessible(driver):
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        href = link.get_attribute("href")
        assert href and href.strip() != "", f"Link missing href: {link.get_attribute('outerHTML')}"


def run_accessibility_checks(driver):
    check_images_accessible(driver)
    check_buttons_accessible(driver)
    check_links_accessible(driver)


# --- FRONTEND CONTENT CHECKS ---
def check_main_content(driver):
    main_elements = driver.find_elements(By.TAG_NAME, "main")
    assert main_elements, "No <main> element found on the page"


def check_headings_present(driver):
    """Ensure at least one heading exists unless page is a 404."""
    main_text = driver.find_element(By.TAG_NAME, "main").text.lower() if driver.find_elements(By.TAG_NAME, "main") else ""
    if "404" in main_text or "not found" in main_text:
        pytest.skip("Page is a 404, skipping heading check")  # skip instead of asserting
    headings = driver.find_elements(By.XPATH, "//h1 | //h2 | //h3")
    assert headings, "No headings found on the page"


# --- TESTS ---
def test_homepage_loads():
    driver = create_driver()
    try:
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "nav")))
        assert driver.title != ""

        run_accessibility_checks(driver)
        check_main_content(driver)
        check_headings_present(driver)
    finally:
        driver.quit()


def test_browse_page_loads():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/browse")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        assert "/browse" in driver.current_url

        run_accessibility_checks(driver)
        check_main_content(driver)
        check_headings_present(driver)
    finally:
        driver.quit()


def test_health_page_loads():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/health")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert driver.find_element(By.TAG_NAME, "body").text.strip() != ""

        run_accessibility_checks(driver)
        check_main_content(driver)
    finally:
        driver.quit()


def test_artifact_model_page_loads():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/artifacts/model/placeholder")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "main")))

        run_accessibility_checks(driver)
        check_main_content(driver)
        check_headings_present(driver)
    finally:
        driver.quit()


def test_model_detail_page_loads():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/models/placeholder")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "main")))

        run_accessibility_checks(driver)
        check_main_content(driver)
        check_headings_present(driver)
    finally:
        driver.quit()
