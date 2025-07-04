# app_tests/conftest.py

import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock
from playwright.sync_api import sync_playwright
import logging

# ==================== CONFIGURE LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== PATH SETUP ====================
# ✅ Add root path to sys.path so `streamlit_pages` is importable
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ==================== UNIT TEST FIXTURES ====================

# ✅ Autouse fixture to mock Streamlit globally (for unit tests)
@pytest.fixture(autouse=True)
def mock_streamlit(request):
    # Only apply mocks for unit tests (not e2e tests)
    if "e2e" not in request.keywords:
        import streamlit as st
        st.columns = MagicMock()
        st.checkbox = MagicMock(return_value=False)
        st.image = MagicMock()
        st.query_params = MagicMock()
        yield

# ==================== E2E TEST FIXTURES ====================

@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Configure browser launch arguments"""
    return {
        "headless": False,  # Set to True in CI
        "slow_mo": 500,     # Slow down for visual debugging
        "timeout": 30000    # Increase default timeout
    }

@pytest.fixture(scope="session")
def browser_context_args(pytestconfig, browser_context_args):
    """Configure browser context"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        "record_video_dir": "videos/" if pytestconfig.getoption("--record-video") else None
    }

@pytest.fixture(scope="session")
def playwright():
    """Playwright instance"""
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def browser(playwright, browser_type_launch_args):
    """Browser instance"""
    browser = playwright.chromium.launch(**browser_type_launch_args)
    yield browser
    browser.close()

@pytest.fixture
def context(browser, browser_context_args):
    """Browser context"""
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()

@pytest.fixture
def page(context):
    """New page for each test"""
    page = context.new_page()
    page.set_default_timeout(15000)  # Increase default timeout
    yield page
    page.close()

@pytest.fixture(scope="session")
def base_url(pytestconfig):
    """Base URL for the application"""
    url = pytestconfig.getoption("--base-url") or "http://localhost:8501"
    logger.info(f"Using base URL: {url}")
    return url

# ==================== HOOKS ====================

def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--record-video",
        action="store_true",
        default=False,
        help="Record test execution videos"
    )

def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )

def pytest_runtest_setup(item):
    """Skip unit test mocks for e2e tests"""
    if "e2e" in item.keywords:
        # Don't apply unit test mocks to e2e tests
        item.fixturenames = [f for f in item.fixturenames if f != "mock_streamlit"]
