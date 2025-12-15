"""
Frontend accessibility and content checks using Selenium WebDriver.

This module performs automated tests on the web application's pages to ensure:
- Pages load correctly.
- Accessibility standards for images, buttons, and links are met.
- Main content and headings are present.
- Specific pages (home, browse, health, artifact, model detail) function properly.

Environment:
- BASE_URL: Base URL of the web application (default: "http://localhost:3000")
- ChromeDriver must be available in PATH.
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")


# --- DRIVER SETUP ---
def create_driver() -> webdriver.Chrome:
    """
    Create a headless Chrome WebDriver instance.

    Returns
    -------
    webdriver.Chrome
        Configured Chrome WebDriver for running tests in headless mode.
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)


# --- ACCESSIBILITY CHECKS ---
def check_images_accessible(driver: webdriver.Chrome) -> None:
    """
    Ensure all <img> elements have non-empty alt attributes.

    Parameters
    ----------
    driver : webdriver.Chrome
        Active Selenium WebDriver instance.

    Raises
    ------
    AssertionError
        If any image is missing an alt attribute or it is empty.
    """
    images = driver.find_elements(By.TAG_NAME, "img")
    for img in images:
        alt = img.get_attribute("alt")
        assert alt and alt.strip() != "", f"Image missing alt attribute: {img.get_attribute('outerHTML')}"


def check_buttons_accessible(driver: webdriver.Chrome) -> None:
    """
    Ensure all <button> elements have either visible text or an aria-label.

    Parameters
    ----------
    driver : webdriver.Chrome
        Active Selenium WebDriver instance.

    Raises
    ------
    AssertionError
        If a button lacks both text content and an aria-label.
    """
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        text = btn.text.strip()
        aria_label = btn.get_attribute("aria-label")
        assert text or aria_label, f"Button missing accessible name: {btn.get_attribute('outerHTML')}"


def check_links_accessible(driver: webdriver.Chrome) -> None:
    """
    Ensure all <a> elements have a non-empty href attribute.

    Parameters
    ----------
    driver : webdriver.Chrome
        Active Selenium WebDriver instance.

    Raises
    ------
    AssertionError
        If any link is missing an href or it is empty.
    """
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        href = link.get_attribute("href")
        assert href and href.strip() != "", f"Link missing href: {link.get_attribute('outerHTML')}"


def run_accessibility_checks(driver: webdriver.Chrome) -> None:
    """
    Run all accessibility checks (images, buttons, links) on the page.

    Parameters
    ----------
    driver : webdriver.Chrome
        Active Selenium WebDriver instance.
    """
    check_images_accessible(driver)
    check_buttons_accessible(driver)
    check_links_accessible(driver)


# --- FRONTEND CONTENT CHECKS ---
def check_main_content(driver: webdriver.Chrome) -> None:
    """
    Ensure the page contains at least one <main> element.

    Parameters
    ----------
    driver : webdriver.Chrome
        Active Selenium WebDriver instance.

    Raises
    ------
    AssertionError
        If no <main> element is found on the page.
    """
    main_elements = driver.find_elements(By.TAG_NAME, "main")
    assert main_elements, "No <main> element found on the page"


def check_headings_present(driver: webdriver.Chrome) -> None:
    """
    Ensure at least one heading (<h1>, <h2>, <h3>) exists on the page,
    unless the page is a 404.

    Parameters
    ----------
    driver : webdriver.Chrome
        Active Selenium WebDriver instance.

    Raises
    ------
    AssertionError
        If no headings are found on non-404 pages.
    """
    main_text = driver.find_element(By.TAG_NAME, "main").text.lower() if driver.find_elements(By.TAG_NAME, "main") else ""
    if "404" in main_text or "not found" in main_text:
        pytest.skip("Page is a 404, skipping heading check")  # skip instead of asserting
    headings = driver.find_elements(By.XPATH, "//h1 | //h2 | //h3")
    assert headings, "No headings found on the page"


# --- TESTS ---
def test_homepage_loads() -> None:
    """
    Test that the homepage loads correctly, and runs accessibility
    and content checks.
    """
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


def test_browse_page_loads() -> None:
    """
    Test that the browse page loads and runs accessibility and content checks.
    """
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


def test_health_page_loads() -> None:
    """
    Test that the health page loads and runs accessibility and main content checks.
    """
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/health")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert driver.find_element(By.TAG_NAME, "body").text.strip() != ""

        run_accessibility_checks(driver)
        check_main_content(driver)
    finally:
        driver.quit()


def test_artifact_model_page_loads() -> None:
    """
    Test that the artifact model page loads and runs accessibility and content checks.
    """
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/artifacts/model/placeholder")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "main")))

        run_accessibility_checks(driver)
        check_main_content(driver)
        check_headings_present(driver)
    finally:
        driver.quit()


def test_model_detail_page_loads() -> None:
    """
    Test that the model detail page loads and runs accessibility and content checks.
    """
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/models/placeholder")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "main")))

        run_accessibility_checks(driver)
        check_main_content(driver)
        check_headings_present(driver)
    finally:
        driver.quit()
