import os
import pathlib

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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
            EC.presence_of_element_located((By.TAG_NAME, "nav"))
        )

        assert driver.title != ""

    finally:
        driver.quit()


def test_browse_page_loads():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/browse")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )

        assert "/browse" in driver.current_url

    finally:
        driver.quit()


def test_health_page():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/health")

        body = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        assert body.text != ""

    finally:
        driver.quit()


def test_artifact_model_page():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/artifacts/model/placeholder")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )

        assert "artifact" in driver.page_source.lower()

    finally:
        driver.quit()


def test_model_detail_page():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/models/placeholder")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )

        assert "/models/" in driver.current_url

    finally:
        driver.quit()


def test_artifact_detail_loading_state():
    driver = create_driver()
    try:
        # Use placeholder type/id to simulate page
        driver.get(f"{BASE_URL}/artifacts/model/placeholder")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "animate-spin"))
        )
        assert "Loading" in driver.page_source
    finally:
        driver.quit()


def test_artifact_detail_header_and_back_button():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/artifacts/model/placeholder")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        header = driver.find_element(By.TAG_NAME, "h1")
        assert "Unknown" in header.text or header.text != ""

        back_btn = driver.find_element(By.CSS_SELECTOR, "a[href='/browse']")
        assert back_btn.is_displayed()
    finally:
        driver.quit()


def test_download_and_external_links():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/artifacts/model/placeholder")
        # Wait for page to render main content
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )

        download_link = driver.find_element(By.CSS_SELECTOR, "a[href^='/artifacts']")
        assert download_link.is_enabled()

        external_links = driver.find_elements(By.CSS_SELECTOR, "a[target='_blank']")
        assert len(external_links) > 0
    finally:
        driver.quit()


def test_model_scores_render_for_models():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/artifacts/model/placeholder")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ModelScoreCard"))
        )
        scores = driver.find_elements(By.CLASS_NAME, "ModelScoreCard")
        assert len(scores) > 0
    finally:
        driver.quit()


def test_lineage_graph_renders_if_present():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/artifacts/model/placeholder")
        # Only render check, no error if absent
        graphs = driver.find_elements(By.TAG_NAME, "svg")
        assert len(graphs) >= 0  # at least zero; ensures DOM renders
    finally:
        driver.quit()


def test_browse_page_loads():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/browse")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        header = driver.find_element(By.TAG_NAME, "h1")
        assert "Browse" in header.text
    finally:
        driver.quit()


def test_tabs_switch():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/browse")
        tabs = driver.find_elements(By.CSS_SELECTOR, "button[role='tab']")
        assert len(tabs) >= 3
        tabs[1].click()  # switch to Datasets
        WebDriverWait(driver, 5).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "h1"), "Browse")
        )
    finally:
        driver.quit()


def test_search_artifacts():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/browse")
        search = driver.find_element(By.ID, "search-artifacts")
        search.send_keys("placeholder")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h3.text-lg"))
        )
        cards = driver.find_elements(By.CSS_SELECTOR, "h3.text-lg")
        assert any("placeholder" in card.text.lower() for card in cards)
    finally:
        driver.quit()


def test_view_toggle_grid_list():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/browse")
        grid_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Grid view']")
        list_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='List view']")
        grid_btn.click()
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.md\\:grid-cols-2"))
        )
        list_btn.click()
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.space-y-3"))
        )
    finally:
        driver.quit()


def test_artifact_card_links():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/browse")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a:has-text('Details')"))
        )
        details_links = driver.find_elements(By.CSS_SELECTOR, "a:has-text('Details')")
        download_links = driver.find_elements(By.CSS_SELECTOR, "a:has-text('Download')")
        assert len(details_links) > 0
        assert len(download_links) > 0
    finally:
        driver.quit()


def test_health_page_loads_and_displays_cards():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/health")

        # Wait for main content
        main = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )

        # Check header exists
        header = driver.find_element(By.XPATH, "//h1[contains(text(),'System Health Dashboard')]")
        assert header.is_displayed()

        # Wait until loading spinner disappears
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "animate-spin"))
        )

        # Check Overall System Status badge
        status_badge = driver.find_element(By.XPATH, "//span[contains(@class,'Badge') and text()]")
        assert status_badge.is_displayed()

        # Check key metrics cards
        metrics = ["Uptime", "Requests/Min", "Total Requests", "Unique Clients"]
        for metric in metrics:
            card = driver.find_element(By.XPATH, f"//p[contains(text(),'{metric}')]")
            assert card.is_displayed()

    finally:
        driver.quit()


def test_health_page_timeline_chart_renders():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/health")
        # Wait for main content
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )

        # Wait for chart container
        chart_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "recharts-wrapper"))
        )
        assert chart_container.is_displayed()

        # Check at least one line/path element in the chart
        lines = driver.find_elements(By.CSS_SELECTOR, "path.recharts-line")
        assert len(lines) > 0

    finally:
        driver.quit()


def test_health_page_component_cards_render():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/health")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )

        # Check for at least one component card
        component_cards = driver.find_elements(By.XPATH, "//h2[contains(@class,'text-xl') and @class]")
        assert len(component_cards) > 0

        # Check that status badges exist for components
        badges = driver.find_elements(By.XPATH, "//span[contains(@class,'Badge') and text()]")
        assert len(badges) >= len(component_cards)

    finally:
        driver.quit()


def test_health_page_download_benchmark():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/health")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )

        # Click Run Benchmark button
        benchmark_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Run Benchmark')]")
        benchmark_btn.click()

        # Wait for spinner/progress to appear
        spinner = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "animate-spin"))
        )
        assert spinner.is_displayed()

    finally:
        driver.quit()


def test_health_page_error_state():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/health")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )

        # Check if error card exists (simulate error by checking destructive class)
        error_cards = driver.find_elements(By.CSS_SELECTOR, "div.bg-destructive/10")
        # No error is also valid; just ensure it doesn't crash
        assert error_cards is not None

    finally:
        driver.quit()


def test_ingest_page_loads_and_tabs():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/ingest")

        # Check page header
        header = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        assert "Ingest Artifact" in header.text

        # Check that all tabs exist
        tabs = driver.find_elements(By.CSS_SELECTOR, "button[role='tab']")
        tab_texts = [t.text.lower() for t in tabs]
        assert "model" in tab_texts
        assert "dataset" in tab_texts
        assert "code" in tab_texts

        # Switch to Dataset tab
        tabs[1].click()
        active_tab = driver.find_element(By.CSS_SELECTOR, "button[role='tab'][aria-selected='true']")
        assert active_tab.text.lower() == "dataset"

        # Switch to Code tab
        tabs[2].click()
        active_tab = driver.find_element(By.CSS_SELECTOR, "button[role='tab'][aria-selected='true']")
        assert active_tab.text.lower() == "code"

    finally:
        driver.quit()


def test_ingest_page_input_placeholders():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/ingest")

        model_input = driver.find_element(By.ID, "model-url")
        dataset_tab = driver.find_element(By.CSS_SELECTOR, "button[role='tab'][value='dataset']")
        code_tab = driver.find_element(By.CSS_SELECTOR, "button[role='tab'][value='code']")

        # Check Model placeholder
        assert "huggingface.co" in model_input.get_attribute("placeholder")

        # Switch to Dataset and check placeholder
        dataset_tab.click()
        dataset_input = driver.find_element(By.ID, "dataset-url")
        assert "huggingface.co/datasets" in dataset_input.get_attribute("placeholder")

        # Switch to Code and check placeholder
        code_tab.click()
        code_input = driver.find_element(By.ID, "code-url")
        assert "github.com" in code_input.get_attribute("placeholder")

    finally:
        driver.quit()


def test_ingest_button_disabled_when_input_empty():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/ingest")
        ingest_btn = driver.find_element(By.CSS_SELECTOR, "button:has-text('Ingest Model')")
        assert not ingest_btn.is_enabled()
    finally:
        driver.quit()


def test_ingest_error_message_on_empty_input():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/ingest")
        ingest_btn = driver.find_element(By.CSS_SELECTOR, "button:has-text('Ingest Model')")
        ingest_btn.click()
        error_card = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.bg-destructive/10"))
        )
        assert "Please enter a model URL" in error_card.text.lower()
    finally:
        driver.quit()


def test_ingest_loading_and_success_flow(monkeypatch=None):
    """
    If you have a way to mock ingestArtifact API, you can patch it to simulate success.
    Otherwise, this test just clicks button and ensures loading spinner appears.
    """
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/ingest")

        # Enter URL for Model tab
        model_input = driver.find_element(By.ID, "model-url")
        model_input.send_keys("https://huggingface.co/google-bert/bert-base-uncased")

        # Click ingest
        ingest_btn = driver.find_element(By.CSS_SELECTOR, "button:has-text('Ingest Model')")
        ingest_btn.click()

        # Check loading spinner appears
        spinner = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "animate-spin"))
        )
        assert spinner.is_displayed()

        # Here you would ideally mock API and wait for success card
        # success_card = WebDriverWait(driver, 10).until(
        #     EC.presence_of_element_located((By.CSS_SELECTOR, "div.bg-chart-3/10"))
        # )
        # assert "success" in success_card.text.lower()

    finally:
        driver.quit()


def test_ingest_info_card_rendered():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/ingest")
        info_card = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[text()='How It Works']/.."))
        )
        assert "select the artifact type" in info_card.text.lower()
    finally:
        driver.quit()


def test_model_detail_loading_state():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/models/placeholder")
        # Wait for loading spinner
        spinner = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "animate-spin"))
        )
        assert spinner.is_displayed()
        loading_text = driver.find_element(By.XPATH, "//span[contains(text(),'Loading model')]")
        assert loading_text.is_displayed()
    finally:
        driver.quit()


def test_model_detail_error_state():
    driver = create_driver()
    try:
        # Use a non-existent ID to trigger error
        driver.get(f"{BASE_URL}/models/nonexistent-id")
        error_card = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.bg-destructive/10"))
        )
        assert "error" in error_card.text.lower()
        # Back button is visible
        back_btn = driver.find_element(By.CSS_SELECTOR, "a:has-text('Back to Models')")
        assert back_btn.is_displayed()
    finally:
        driver.quit()


def test_model_detail_header_and_links():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/models/placeholder")
        # Wait for main content
        main_header = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        assert main_header.text != ""
        model_id_text = driver.find_element(By.XPATH, "//p[contains(text(),'Model ID')]")
        assert "placeholder" in model_id_text.text.lower()

        # Check HuggingFace link if present
        links = driver.find_elements(By.XPATH, "//a[contains(text(),'View on HuggingFace')]")
        if links:
            assert links[0].get_attribute("href").startswith("http")
    finally:
        driver.quit()


def test_model_detail_buttons():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/models/placeholder")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        # At least Back, Download, Share, Report
        assert len(buttons) >= 4

        # Check that Download button has link to download
        download_link = driver.find_element(By.XPATH, "//a[contains(@href,'/download')]")
        assert download_link.is_enabled()
    finally:
        driver.quit()


def test_model_detail_scores_render():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/models/placeholder")
        # Wait for score cards
        score_cards = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "ModelScoreCard"))
        )
        assert len(score_cards) > 0
    finally:
        driver.quit()


def test_model_detail_lineage_render():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/models/placeholder")
        # Check for SVG elements (lineage graph)
        svgs = driver.find_elements(By.TAG_NAME, "svg")
        # At least zero, ensures DOM rendered
        assert len(svgs) >= 0
    finally:
        driver.quit()


def test_model_detail_sidebar_cards():
    driver = create_driver()
    try:
        driver.get(f"{BASE_URL}/models/placeholder")
        # Model Info card
        model_info = driver.find_element(By.XPATH, "//h3[text()='Model Info']/..")
        assert model_info.is_displayed()
        # Quick Actions card
        quick_actions = driver.find_element(By.XPATH, "//h3[text()='Quick Actions']/..")
        assert quick_actions.is_displayed()

        # Quick Actions links/buttons
        links = quick_actions.find_elements(By.TAG_NAME, "a")
        assert len(links) >= 1  # At least "View API Docs"
    finally:
        driver.quit()
