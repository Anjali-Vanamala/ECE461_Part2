import os

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")


@pytest.fixture
def driver():
    """Create and yield a Chrome driver instance."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


def test_homepage_loads(driver):
    """Test that homepage loads and has basic structure."""
    driver.get(BASE_URL)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "nav")))
    assert driver.title != ""
    assert driver.find_elements(By.TAG_NAME, "main"), "No <main> element found"


def test_browse_page_loads(driver):
    """Test that browse page loads correctly."""
    driver.get(f"{BASE_URL}/browse")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "main")))
    assert "/browse" in driver.current_url


def test_health_page_loads(driver):
    """Test that health page loads and displays content."""
    driver.get(f"{BASE_URL}/health")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    assert driver.find_element(By.TAG_NAME, "body").text.strip() != ""


def test_backend_selection_works(driver):
    """Test that backend selection buttons are present and functional."""
    driver.get(f"{BASE_URL}/health")
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//button[contains(., 'ECS') or contains(., 'Lambda')]"))
    )
    
    # Verify both buttons exist
    ecs_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'ECS')]")
    lambda_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Lambda')]")
    assert len(ecs_buttons) > 0, "ECS button not found"
    assert len(lambda_buttons) > 0, "Lambda button not found"
    
    # Test switching to Lambda
    lambda_buttons[0].click()
    WebDriverWait(driver, 2).until(
        lambda d: "Serverless" in d.find_element(By.TAG_NAME, "body").text or 
                  "Lambda" in d.find_element(By.TAG_NAME, "body").text
    )


def test_benchmark_section_present(driver):
    """Test that benchmark section is present on health page."""
    driver.get(f"{BASE_URL}/health")
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Benchmark')]"))
    )
    
    # Verify benchmark button exists
    benchmark_buttons = driver.find_elements(
        By.XPATH, 
        "//button[contains(., 'Run') or contains(., 'Benchmark') or contains(., 'Start')]"
    )
    assert len(benchmark_buttons) > 0, "Benchmark button not found"
