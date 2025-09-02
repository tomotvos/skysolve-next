import pytest
from playwright.sync_api import sync_playwright
import time

# This test assumes the FastAPI server is running locally on port 5001
BASE_URL = "http://localhost:5001"

@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()

@pytest.fixture(scope="function")
def page(browser):
    page = browser.new_page()
    yield page
    page.close()

def test_solve_button_and_history(page):
    page.goto(f"{BASE_URL}/")
    # Click Demo button to ensure image is loaded
    page.click("#demo-btn")
    page.wait_for_timeout(1000)
    # Click Solve button
    page.click("#solve-btn")
    page.wait_for_timeout(2000)
    # Check that log history is updated and line feeds are rendered
    history_items = page.query_selector_all("#history li")
    assert len(history_items) > 0
    log_text = history_items[-1].inner_text()
    assert "solve-field command" in log_text
    assert "Image solved." in log_text or "Demo image solved." in log_text
    # Check that Last Solve data is updated
    last_solve = page.inner_text("#last-solve")
    assert "solved" in last_solve.lower() or "ra" in last_solve.lower()
    # Check that log lines are not mashed together
    assert "\n" in log_text or "RA,Dec" in log_text
