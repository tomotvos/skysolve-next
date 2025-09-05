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
