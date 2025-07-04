import pytest
from playwright.sync_api import Page, expect
import time
import re
import logging
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("test_sidebar_filters.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "http://localhost:8501"
WAIT_TIMEOUT = 45000  # 45 seconds
NAV_DELAY = 3  # Page transition delay
FILTER_DELAY = 4  # Filter application delay
RETRY_ATTEMPTS = 3  # Retry attempts for flaky operations

class SidebarLocators:
    """Advanced locator strategies with multiple fallbacks"""
    
    @staticmethod
    def get_element_with_retry(page: Page, *locators, timeout=10000) -> Optional[Page.locator]:
        """Try multiple locators with retries and timeout"""
        for attempt in range(RETRY_ATTEMPTS):
            for locator in locators:
                try:
                    element = locator(page) if callable(locator) else page.locator(locator)
                    if element.is_visible(timeout=timeout):
                        return element
                except Exception as e:
                    logger.debug(f"Locator attempt {attempt+1} failed: {str(e)}")
                    continue
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(1)
        return None
    
    @classmethod
    def get_genre_section(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.locator('div', has_text=re.compile(r"🎭\s*Genres")).first,
            lambda p: p.locator('div', has_text=re.compile("Genres")).first,
            '[data-testid="stExpander"]:has-text("Genres")',
            timeout=15000
        )
    
    @classmethod
    def get_genre_selector(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.get_by_label("Select genres"),
            lambda p: p.locator('[data-baseweb="select"]').first,
            'input[aria-label*="genre"]',
            'input[aria-label*="select"]',
            timeout=15000
        )
    
    @classmethod
    def get_year_section(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.locator('div', has_text=re.compile(r"📅\s*Release Year")).first,
            lambda p: p.locator('div', has_text=re.compile("Release Year")).first,
            '[data-testid="stExpander"]:has-text("Year")',
            timeout=15000
        )
    
    @classmethod
    def get_year_input(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.get_by_label("Select exact year"),
            lambda p: p.locator('input[aria-label*="year"]'),
            '[data-testid="stNumberInput"] >> nth=0',
            timeout=15000
        )
    
    @classmethod
    def get_rating_section(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.locator('div', has_text=re.compile(r"⭐\s*Rating")).first,
            lambda p: p.locator('div', has_text=re.compile("Rating")).first,
            '[data-testid="stExpander"]:has-text("Rating")',
            timeout=15000
        )
    
    @classmethod
    def get_reset_button(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.get_by_role("button", name=re.compile(r"♻️\s*Reset All Filters", re.IGNORECASE)),
            lambda p: p.get_by_role("button", name=re.compile("Reset All Filters", re.IGNORECASE)),
            'button:has-text("Reset") >> nth=0',
            timeout=15000
        )
    
    @classmethod
    def get_active_filters_badge(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.locator('div', has_text=re.compile(r"\d+\s*active")),
            '[data-testid="stMarkdownContainer"]:has-text("active")',
            timeout=5000
        )

@pytest.fixture(scope="function")
def setup_page(page: Page):
    """Enhanced page setup with robust initialization"""
    page.set_default_timeout(WAIT_TIMEOUT)
    
    def is_app_ready():
        try:
            page.goto(BASE_URL)
            page.wait_for_selector(
                '.sidebar-header, [data-testid="stAppViewContainer"]',
                state="visible",
                timeout=10000
            )
            return True
        except Exception as e:
            logger.warning(f"App not ready yet: {str(e)}")
            return False
    
    # Retry app loading
    for attempt in range(3):
        if is_app_ready():
            break
        if attempt == 2:
            raise Exception("Failed to load app after 3 attempts")
        time.sleep(5)
    
    # Ensure sidebar is ready
    sidebar = page.locator('[data-testid="stSidebar"]')
    if not sidebar.is_visible():
        page.wait_for_selector('[data-testid="stSidebar"]', state="visible", timeout=10000)
    
    yield page
    
    # Test cleanup
    try:
        reset_btn = SidebarLocators.get_reset_button(page)
        if reset_btn and reset_btn.is_visible():
            safe_click(reset_btn, "reset button in cleanup")
            time.sleep(FILTER_DELAY)
    except Exception as e:
        logger.warning(f"Cleanup failed: {str(e)}")

def safe_click(element, description="element", timeout=10000):
    """Robust click with multiple strategies and error handling"""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            element.scroll_into_view_if_needed()
            element.hover()
            element.click(timeout=timeout)
            time.sleep(0.3)  # Small delay for UI updates
            return
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                logger.error(f"Failed to click {description} after {RETRY_ATTEMPTS} attempts")
                raise
            logger.warning(f"Click failed on {description} (attempt {attempt+1}), retrying...")
            try:
                element.dispatch_event('click')
                time.sleep(0.5)
                return
            except Exception as e:
                logger.debug(f"Dispatch click also failed: {str(e)}")
                time.sleep(1)

def verify_filter_state(page: Page, filter_type: str, expected_value: str) -> Tuple[bool, str]:
    """Comprehensive filter verification with multiple fallbacks"""
    verification_methods = []
    
    # Method 1: Visual confirmation
    try:
        if filter_type == "genre":
            if page.get_by_text(expected_value).first.is_visible(timeout=5000):
                return True, "Visual confirmation"
        elif filter_type == "year":
            year_display = SidebarLocators.get_element_with_retry(
                page,
                lambda p: p.locator('div', has_text=re.compile(f"📅\\s*{expected_value}")).first,
                lambda p: p.locator('div', has_text=re.compile(expected_value)).first,
                timeout=5000
            )
            if year_display and year_display.is_visible():
                return True, "Visual confirmation"
    except Exception as e:
        verification_methods.append(f"Visual failed: {str(e)}")
    
    # Method 2: URL parameters
    try:
        current_url = page.url
        if filter_type == "genre":
            if f"genres={expected_value}" in current_url:
                return True, "URL parameter confirmation"
        elif filter_type == "year":
            if f"exact_year={expected_value}" in current_url:
                return True, "URL parameter confirmation"
    except Exception as e:
        verification_methods.append(f"URL check failed: {str(e)}")
    
    # Method 3: DOM attributes
    try:
        if filter_type == "genre":
            selected_indicator = page.locator(f'[data-testid*="{expected_value.lower()}"]').first
            if selected_indicator.is_visible(timeout=5000):
                return True, "DOM attribute confirmation"
    except Exception as e:
        verification_methods.append(f"DOM check failed: {str(e)}")
    
    # Method 4: Active filters badge
    try:
        badge = SidebarLocators.get_active_filters_badge(page)
        if badge and badge.is_visible():
            badge_text = badge.text_content()
            if badge_text and int(badge_text.split()[0]) > 0:
                return True, "Active filters badge confirmation"
    except Exception as e:
        verification_methods.append(f"Badge check failed: {str(e)}")
    
    return False, f"All verification failed: {', '.join(verification_methods)}"

def test_genre_filter_persistence(setup_page: Page):
    """Comprehensive genre filter persistence test"""
    page = setup_page
    
    # Open genre section
    genre_section = SidebarLocators.get_genre_section(page)
    assert genre_section, "Could not find genre section"
    safe_click(genre_section, "genre section")
    
    # Find and interact with genre selector
    genre_selector = SidebarLocators.get_genre_selector(page)
    assert genre_selector, "Could not find genre selector"
    safe_click(genre_selector, "genre selector")
    
    # Select genres with robust retry logic
    genres_to_select = ["Action", "Adventure"]
    for genre in genres_to_select:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                page.get_by_text(genre, exact=True).click()
                logger.info(f"Selected genre: {genre}")
                break
            except Exception as e:
                if attempt == RETRY_ATTEMPTS - 1:
                    logger.error(f"Failed to select genre {genre} after {RETRY_ATTEMPTS} attempts")
                    raise
                logger.warning(f"Genre selection failed for {genre} (attempt {attempt+1}), retrying...")
                safe_click(genre_selector, "genre selector retry")
                time.sleep(1)
    
    page.keyboard.press("Escape")
    time.sleep(FILTER_DELAY)
    
    # Verify genre filters
    for genre in genres_to_select:
        is_set, verification_method = verify_filter_state(page, "genre", genre)
        assert is_set, f"Failed to verify {genre} filter is set ({verification_method})"
        logger.info(f"Verified {genre} filter via {verification_method}")

def test_year_filter_persistence(setup_page: Page):
    """Comprehensive year filter persistence test"""
    page = setup_page
    
    # Open year section
    year_section = SidebarLocators.get_year_section(page)
    assert year_section, "Could not find year section"
    safe_click(year_section, "year section")
    
    # Switch to exact year mode
    exact_year_btn = page.get_by_text("Exact Year").first
    if not exact_year_btn.is_visible(timeout=5000):
        exact_year_btn = page.get_by_text("Exact Year").first
    safe_click(exact_year_btn, "exact year button")
    
    # Set year value with robust input handling
    year_input = SidebarLocators.get_year_input(page)
    assert year_input, "Could not find year input"
    
    for attempt in range(RETRY_ATTEMPTS):
        try:
            year_input.fill("")
            year_input.fill("2010")
            year_input.press("Enter")
            logger.info("Set year filter to 2010")
            break
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                logger.error("Failed to set year filter after multiple attempts")
                raise
            logger.warning(f"Year input failed (attempt {attempt+1}), retrying...")
            time.sleep(1)
    
    time.sleep(FILTER_DELAY)
    
    # Verify year filter
    is_set, verification_method = verify_filter_state(page, "year", "2010")
    assert is_set, f"Failed to verify year filter is set ({verification_method})"
    logger.info(f"Verified year filter via {verification_method}")

def test_rating_filter_persistence(setup_page: Page):
    """Comprehensive rating filter persistence test"""
    page = setup_page
    
    # Open rating section
    rating_section = SidebarLocators.get_rating_section(page)
    assert rating_section, "Could not find rating section"
    safe_click(rating_section, "rating section")
    
    # Switch to exact rating mode
    exact_rating_btn = page.get_by_text("Exact Rating").first
    if not exact_rating_btn.is_visible(timeout=5000):
        exact_rating_btn = page.get_by_text("Exact Rating").first
    safe_click(exact_rating_btn, "exact rating button")
    
    # Set rating value
    rating_input = SidebarLocators.get_year_input(page)  # Reusing similar locator
    assert rating_input, "Could not find rating input"
    
    for attempt in range(RETRY_ATTEMPTS):
        try:
            rating_input.fill("")
            rating_input.fill("8.5")
            rating_input.press("Enter")
            logger.info("Set rating filter to 8.5")
            break
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                logger.error("Failed to set rating filter after multiple attempts")
                raise
            logger.warning(f"Rating input failed (attempt {attempt+1}), retrying...")
            time.sleep(1)
    
    time.sleep(FILTER_DELAY)
    
    # Verify rating filter
    is_set, verification_method = verify_filter_state(page, "year", "8.5")
    assert is_set, f"Failed to verify rating filter is set ({verification_method})"
    logger.info(f"Verified rating filter via {verification_method}")

def test_reset_filters(setup_page: Page):
    """Comprehensive test of reset functionality"""
    page = setup_page
    
    # Set initial filters
    genre_section = SidebarLocators.get_genre_section(page)
    safe_click(genre_section, "genre section")
    
    genre_selector = SidebarLocators.get_genre_selector(page)
    safe_click(genre_selector, "genre selector")
    page.get_by_text("Comedy", exact=True).click()
    page.keyboard.press("Escape")
    time.sleep(FILTER_DELAY)
    
    # Verify filters were set
    is_set, _ = verify_filter_state(page, "genre", "Comedy")
    assert is_set, "Failed to set initial filters for reset test"
    
    # Find and click reset button
    reset_button = SidebarLocators.get_reset_button(page)
    assert reset_button, "Could not find reset button"
    safe_click(reset_button, "reset button")
    time.sleep(FILTER_DELAY)
    
    # Verify reset with multiple checks
    try:
        expect(page.get_by_text("Comedy")).not_to_be_visible()
    except Exception as e:
        # Fallback check URL parameters
        expect(page).not_to_have_url(re.compile(r".*genres=Comedy.*"))
    
    # Verify default year range is visible
    year_section = SidebarLocators.get_year_section(page)
    safe_click(year_section, "year section in reset test")
    expect(page.get_by_text("2000")).to_be_visible()
    
    # Verify active filters badge shows zero
    badge = SidebarLocators.get_active_filters_badge(page)
    if badge and badge.is_visible():
        badge_text = badge.text_content()
        assert "0 active" in badge_text, "Active filters badge not reset"

def test_url_parameter_persistence(setup_page: Page):
    """Comprehensive test of URL parameter persistence"""
    page = setup_page
    
    # Load with specific URL parameters
    test_url = f"{BASE_URL}/?genres=Action&exact_year=2010"
    page.goto(test_url)
    page.wait_for_selector('.sidebar-header, [data-testid="stAppViewContainer"]', state="visible")
    time.sleep(NAV_DELAY)
    
    # Verify filters applied from URL
    genre_section = SidebarLocators.get_genre_section(page)
    safe_click(genre_section, "genre section in URL test")
    
    # Check for active genre
    action_visible = page.get_by_text("Action").is_visible()
    if not action_visible:
        # Check if genre is selected but not visible (collapsed state)
        selected_genres = page.locator('[data-testid="stMarkdownContainer"]', has_text="Action")
        expect(selected_genres).to_be_visible()
    else:
        expect(page.get_by_text("Action")).to_be_visible()
    
    # Verify year
    year_section = SidebarLocators.get_year_section(page)
    safe_click(year_section, "year section in URL test")
    expect(page.get_by_text("2010")).to_be_visible()
    
    # Verify URL parameters are maintained after interaction
    page.get_by_role("link", name=re.compile("Search", re.IGNORECASE)).click()
    time.sleep(NAV_DELAY)
    expect(page).to_have_url(re.compile(r".*genres=Action.*"))
    expect(page).to_have_url(re.compile(r".*exact_year=2010.*"))

def test_filter_persistence_across_navigation(setup_page: Page):
    """Test filter persistence across page navigation"""
    page = setup_page
    
    # Set genre filter
    genre_section = SidebarLocators.get_genre_section(page)
    safe_click(genre_section, "genre section in nav test")
    
    genre_selector = SidebarLocators.get_genre_selector(page)
    safe_click(genre_selector, "genre selector in nav test")
    page.get_by_text("Drama", exact=True).click()
    page.keyboard.press("Escape")
    time.sleep(FILTER_DELAY)
    
    # Navigate to movie details
    first_movie = page.locator('[data-testid="movie-tile"]').first
    movie_title = first_movie.text_content()
    first_movie.click()
    expect(page.get_by_text(movie_title)).to_be_visible()
    time.sleep(NAV_DELAY)
    
    # Navigate back
    page.get_by_role("button", name=re.compile("Back", re.IGNORECASE)).first.click()
    time.sleep(NAV_DELAY)
    
    # Verify filters persisted
    is_set, verification_method = verify_filter_state(page, "genre", "Drama")
    assert is_set, f"Genre filter not persisted after navigation ({verification_method})"
    logger.info(f"Verified genre persistence via {verification_method}")

if __name__ == "__main__":
    # This allows running the tests directly during development

    import pytest
from playwright.sync_api import Page, expect
import time
import re
import logging
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("test_sidebar_filters.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "http://localhost:8501"
WAIT_TIMEOUT = 60000  # 60 seconds
NAV_DELAY = 5  # Page transition delay
FILTER_DELAY = 5  # Filter application delay
RETRY_ATTEMPTS = 5  # Retry attempts for flaky operations

class SidebarLocators:
    """Enhanced locator strategies with multiple fallbacks"""
    
    @staticmethod
    def get_element_with_retry(page: Page, *locators, timeout=15000):
        """Robust element location with retries and timeout"""
        for attempt in range(RETRY_ATTEMPTS):
            for locator in locators:
                try:
                    element = locator(page) if callable(locator) else page.locator(locator)
                    element.wait_for(state="visible", timeout=timeout)
                    return element
                except Exception as e:
                    logger.debug(f"Locator attempt {attempt+1} failed: {str(e)}")
                    if attempt == RETRY_ATTEMPTS - 1:
                        continue
                    time.sleep(1)
        raise Exception(f"Could not locate element after {RETRY_ATTEMPTS} attempts")
    
    @classmethod
    def get_genre_section(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.locator('div', has_text=re.compile(r"🎭\s*Genres")).first,
            lambda p: p.locator('div', has_text=re.compile("Genres")).first,
            '[data-testid="stExpander"]:has-text("Genres")',
            timeout=20000
        )
    
    @classmethod
    def get_genre_selector(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.get_by_label("Select genres"),
            lambda p: p.locator('[data-baseweb="select"]').first,
            'input[aria-label*="genre"]',
            'input[aria-label*="select"]',
            timeout=20000
        )
    
    @classmethod
    def get_year_section(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.locator('div', has_text=re.compile(r"📅\s*Release Year")).first,
            lambda p: p.locator('div', has_text=re.compile("Release Year")).first,
            '[data-testid="stExpander"]:has-text("Year")',
            timeout=20000
        )
    
    @classmethod
    def get_year_input(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.get_by_label("Select exact year"),
            lambda p: p.locator('input[aria-label*="year"]'),
            '[data-testid="stNumberInput"] >> nth=0',
            timeout=20000
        )
    
    @classmethod
    def get_rating_section(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.locator('div', has_text=re.compile(r"⭐\s*Rating")).first,
            lambda p: p.locator('div', has_text=re.compile("Rating")).first,
            '[data-testid="stExpander"]:has-text("Rating")',
            timeout=20000
        )
    
    @classmethod
    def get_rating_input(cls, page: Page):
        """Specific locator for rating input"""
        return cls.get_element_with_retry(
            page,
            lambda p: p.get_by_label("Select exact rating"),
            lambda p: p.locator('input[aria-label*="rating"]'),
            '[data-testid="stNumberInput"] >> nth=1',
            timeout=20000
        )
    
    @classmethod
    def get_reset_button(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.get_by_role("button", name=re.compile(r"♻️\s*Reset All Filters", re.IGNORECASE)),
            lambda p: p.get_by_role("button", name=re.compile("Reset All Filters", re.IGNORECASE)),
            'button:has-text("Reset") >> nth=0',
            timeout=20000
        )
    
    @classmethod
    def get_active_filters_badge(cls, page: Page):
        return cls.get_element_with_retry(
            page,
            lambda p: p.locator('div', has_text=re.compile(r"\d+\s*active")),
            '[data-testid="stMarkdownContainer"]:has-text("active")',
            timeout=10000
        )
    
    @classmethod
    def get_year_display(cls, page: Page, year: str):
        """Specific locator for year display"""
        return cls.get_element_with_retry(
            page,
            lambda p: p.locator('div', has_text=re.compile(f"📅\\s*{year}")).first,
            lambda p: p.locator('div', has_text=re.compile(year)).first,
            f'[data-testid*="{year}"]',
            timeout=15000
        )

@pytest.fixture(scope="function")
def setup_page(page: Page):
    """Enhanced page setup with robust initialization"""
    page.set_default_timeout(WAIT_TIMEOUT)
    
    def is_app_ready():
        try:
            page.goto(BASE_URL)
            page.wait_for_selector(
                '.sidebar-header, [data-testid="stAppViewContainer"]',
                state="visible",
                timeout=20000
            )
            return True
        except Exception as e:
            logger.warning(f"App not ready yet: {str(e)}")
            return False
    
    # Retry app loading with more attempts
    for attempt in range(5):
        if is_app_ready():
            break
        if attempt == 4:
            raise Exception("Failed to load app after 5 attempts")
        logger.warning(f"App loading failed (attempt {attempt+1}), retrying...")
        time.sleep(5)
    
    # Ensure sidebar is ready
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.wait_for(state="visible", timeout=20000)
    
    yield page
    
    # Test cleanup with better error handling
    try:
        reset_btn = SidebarLocators.get_reset_button(page)
        if reset_btn and reset_btn.is_visible():
            safe_click(reset_btn, "reset button in cleanup")
            time.sleep(FILTER_DELAY)
    except Exception as e:
        logger.warning(f"Cleanup failed: {str(e)}")

def safe_click(element, description="element", timeout=15000):
    """Robust click with multiple strategies and error handling"""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            element.scroll_into_view_if_needed()
            element.hover()
            box = element.bounding_box()
            page = element.page
            page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            time.sleep(0.5)
            return
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                logger.error(f"Failed to click {description} after {RETRY_ATTEMPTS} attempts")
                raise
            logger.warning(f"Click failed on {description} (attempt {attempt+1}), retrying...")
            try:
                element.dispatch_event('click')
                time.sleep(1)
            except Exception as e:
                logger.debug(f"Dispatch click also failed: {str(e)}")
                time.sleep(2)

def verify_filter_state(page: Page, filter_type: str, expected_value: str) -> Tuple[bool, str]:
    """Comprehensive filter verification with multiple fallbacks"""
    verification_methods = []
    
    # Method 1: Visual confirmation
    try:
        if filter_type == "genre":
            if page.get_by_text(expected_value).first.is_visible(timeout=5000):
                return True, "Visual confirmation"
        elif filter_type == "year":
            year_display = SidebarLocators.get_year_display(page, expected_value)
            if year_display and year_display.is_visible():
                return True, "Visual confirmation"
        elif filter_type == "rating":
            rating_display = SidebarLocators.get_element_with_retry(
                page,
                lambda p: p.locator('div', has_text=re.compile(f"🌟\\s*{expected_value}")).first,
                timeout=5000
            )
            if rating_display and rating_display.is_visible():
                return True, "Visual confirmation"
    except Exception as e:
        verification_methods.append(f"Visual failed: {str(e)}")
    
    # Method 2: URL parameters
    try:
        current_url = page.url
        if filter_type == "genre":
            if f"genres={expected_value}" in current_url:
                return True, "URL parameter confirmation"
        elif filter_type in ["year", "rating"]:
            if f"exact_{filter_type}={expected_value}" in current_url:
                return True, "URL parameter confirmation"
    except Exception as e:
        verification_methods.append(f"URL check failed: {str(e)}")
    
    # Method 3: DOM attributes
    try:
        if filter_type == "genre":
            selected_indicator = page.locator(f'[data-testid*="{expected_value.lower()}"]').first
            if selected_indicator.is_visible(timeout=5000):
                return True, "DOM attribute confirmation"
        elif filter_type in ["year", "rating"]:
            value_indicator = page.locator(f'[data-testid*="{expected_value}"]').first
            if value_indicator and value_indicator.is_visible(timeout=5000):
                return True, "DOM attribute confirmation"
    except Exception as e:
        verification_methods.append(f"DOM check failed: {str(e)}")
    
    # Method 4: Active filters badge
    try:
        badge = SidebarLocators.get_active_filters_badge(page)
        if badge and badge.is_visible():
            badge_text = badge.text_content()
            if badge_text and int(badge_text.split()[0]) > 0:
                return True, "Active filters badge confirmation"
    except Exception as e:
        verification_methods.append(f"Badge check failed: {str(e)}")
    
    return False, f"All verification failed: {', '.join(verification_methods)}"

def test_genre_filter_persistence(setup_page: Page):
    """Test genre filter persistence with resilient locators"""
    page = setup_page
    
    # Open genre section
    genre_section = SidebarLocators.get_genre_section(page)
    assert genre_section, "Could not find genre section"
    safe_click(genre_section, "genre section")
    
    # Find and interact with genre selector
    genre_selector = SidebarLocators.get_genre_selector(page)
    assert genre_selector, "Could not find genre selector"
    safe_click(genre_selector, "genre selector")
    
    # Select genres with comprehensive retry logic
    genres_to_select = ["Action", "Adventure"]
    for genre in genres_to_select:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                page.get_by_text(genre, exact=True).click()
                logger.info(f"Selected genre: {genre}")
                break
            except Exception as e:
                if attempt == RETRY_ATTEMPTS - 1:
                    logger.error(f"Failed to select genre {genre} after {RETRY_ATTEMPTS} attempts")
                    raise
                logger.warning(f"Genre selection failed for {genre} (attempt {attempt+1}), retrying...")
                safe_click(genre_selector, "genre selector retry")
                time.sleep(1)
    
    page.keyboard.press("Escape")
    time.sleep(FILTER_DELAY)
    
    # Enhanced verification
    for genre in genres_to_select:
        is_set, verification_method = verify_filter_state(page, "genre", genre)
        assert is_set, f"Failed to verify {genre} filter is set ({verification_method})"
        logger.info(f"Verified {genre} filter via {verification_method}")

def test_year_filter_persistence(setup_page: Page):
    """Test year filter persistence with resilient locators"""
    page = setup_page
    
    # Open year section
    year_section = SidebarLocators.get_year_section(page)
    assert year_section, "Could not find year section"
    safe_click(year_section, "year section")
    
    # Switch to exact year mode
    exact_year_btn = page.get_by_text("Exact Year").first
    if not exact_year_btn.is_visible(timeout=5000):
        exact_year_btn = page.get_by_text("Exact Year").first
    safe_click(exact_year_btn, "exact year button")
    
    # Set year value
    year_input = SidebarLocators.get_year_input(page)
    assert year_input, "Could not find year input"
    
    for attempt in range(RETRY_ATTEMPTS):
        try:
            year_input.fill("")
            year_input.fill("2010")
            year_input.press("Enter")
            logger.info("Set year filter to 2010")
            break
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                logger.error("Failed to set year filter after multiple attempts")
                raise
            logger.warning(f"Year input failed (attempt {attempt+1}), retrying...")
            time.sleep(1)
    
    time.sleep(FILTER_DELAY)
    
    # Enhanced verification
    is_set, verification_method = verify_filter_state(page, "year", "2010")
    assert is_set, f"Failed to verify year filter is set ({verification_method})"
    logger.info(f"Verified year filter via {verification_method}")

def test_rating_filter_persistence(setup_page: Page):
    """Test rating filter persistence with dedicated locator"""
    page = setup_page
    
    # Open rating section
    rating_section = SidebarLocators.get_rating_section(page)
    assert rating_section, "Could not find rating section"
    safe_click(rating_section, "rating section")
    
    # Switch to exact rating mode
    exact_rating_btn = page.get_by_text("Exact Rating").first
    if not exact_rating_btn.is_visible(timeout=5000):
        exact_rating_btn = page.get_by_text("Exact Rating").first
    safe_click(exact_rating_btn, "exact rating button")
    
    # Set rating value with dedicated input locator
    rating_input = SidebarLocators.get_rating_input(page)
    assert rating_input, "Could not find rating input"
    
    for attempt in range(RETRY_ATTEMPTS):
        try:
            rating_input.fill("")
            rating_input.type("8.5", delay=100)  # Slower typing for reliability
            rating_input.press("Enter")
            logger.info("Set rating filter to 8.5")
            break
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                logger.error("Failed to set rating filter after multiple attempts")
                raise
            logger.warning(f"Rating input failed (attempt {attempt+1}), retrying...")
            time.sleep(2)
    
    time.sleep(FILTER_DELAY)
    
    # Enhanced verification
    is_set, verification_method = verify_filter_state(page, "rating", "8.5")
    assert is_set, f"Failed to verify rating filter is set ({verification_method})"
    logger.info(f"Verified rating filter via {verification_method}")

def test_reset_filters(setup_page: Page):
    """Test reset functionality with robust verification"""
    page = setup_page
    
    # Set initial filters
    genre_section = SidebarLocators.get_genre_section(page)
    safe_click(genre_section, "genre section")
    
    genre_selector = SidebarLocators.get_genre_selector(page)
    safe_click(genre_selector, "genre selector")
    page.get_by_text("Comedy", exact=True).click()
    page.keyboard.press("Escape")
    time.sleep(FILTER_DELAY)
    
    # Verify filters were set
    is_set, _ = verify_filter_state(page, "genre", "Comedy")
    assert is_set, "Failed to set initial filters for reset test"
    
    # Find and click reset button
    reset_button = SidebarLocators.get_reset_button(page)
    assert reset_button, "Could not find reset button"
    safe_click(reset_button, "reset button")
    time.sleep(FILTER_DELAY)
    
    # Verify reset with multiple checks
    try:
        expect(page.get_by_text("Comedy")).not_to_be_visible()
    except Exception as e:
        # Fallback check URL parameters
        expect(page).not_to_have_url(re.compile(r".*genres=Comedy.*"))
    
    # Verify default year range is visible
    year_section = SidebarLocators.get_year_section(page)
    safe_click(year_section, "year section in reset test")
    
    year_display = SidebarLocators.get_year_display(page, "2000")
    expect(year_display).to_be_visible()
    
    # Verify active filters badge shows zero
    badge = SidebarLocators.get_active_filters_badge(page)
    if badge and badge.is_visible():
        badge_text = badge.text_content()
        assert "0 active" in badge_text, "Active filters badge not reset"

def test_url_parameter_persistence(setup_page: Page):
    """Test URL parameter persistence with reliable navigation"""
    page = setup_page
    
    # Load with specific URL parameters
    test_url = f"{BASE_URL}/?genres=Action&exact_year=2010"
    for attempt in range(3):
        try:
            page.goto(test_url)
            page.wait_for_selector('.sidebar-header', state="visible", timeout=30000)
            break
        except Exception as e:
            if attempt == 2:
                raise Exception(f"Failed to load URL after 3 attempts: {str(e)}")
            logger.warning(f"URL load failed (attempt {attempt+1}), retrying...")
            time.sleep(5)
    
    # Verify filters applied from URL
    genre_section = SidebarLocators.get_genre_section(page)
    safe_click(genre_section, "genre section in URL test")
    
    # Check for active genre with multiple strategies
    action_visible = page.get_by_text("Action").is_visible()
    if not action_visible:
        # Check if genre is selected but not visible (collapsed state)
        selected_genres = SidebarLocators.get_element_with_retry(
            page,
            lambda p: p.locator('[data-testid="stMarkdownContainer"]', has_text="Action"),
            timeout=10000
        )
        expect(selected_genres).to_be_visible()
    else:
        expect(page.get_by_text("Action")).to_be_visible()
    
    # Verify year
    year_section = SidebarLocators.get_year_section(page)
    safe_click(year_section, "year section in URL test")
    
    year_display = SidebarLocators.get_year_display(page, "2010")
    expect(year_display).to_be_visible()
    
    # Verify URL parameters are maintained after interaction
    search_link = SidebarLocators.get_element_with_retry(
        page,
        lambda p: p.get_by_role("link", name=re.compile("Search", re.IGNORECASE)),
        timeout=20000
    )
    safe_click(search_link, "search link")
    time.sleep(NAV_DELAY)
    
    expect(page).to_have_url(re.compile(r".*genres=Action.*"))
    expect(page).to_have_url(re.compile(r".*exact_year=2010.*"))

def test_filter_persistence_across_navigation(setup_page: Page):
    """Test filter persistence across page navigation"""
    page = setup_page
    
    # Set genre filter
    genre_section = SidebarLocators.get_genre_section(page)
    safe_click(genre_section, "genre section in nav test")
    
    genre_selector = SidebarLocators.get_genre_selector(page)
    safe_click(genre_selector, "genre selector in nav test")
    page.get_by_text("Drama", exact=True).click()
    page.keyboard.press("Escape")
    time.sleep(FILTER_DELAY)
    
    # Navigate to movie details
    movie_tile = SidebarLocators.get_element_with_retry(
        page,
        lambda p: p.locator('[data-testid="movie-tile"]').first,
        timeout=30000
    )
    movie_title = movie_tile.text_content()
    safe_click(movie_tile, "movie tile")
    
    # Wait for details page
    SidebarLocators.get_element_with_retry(
        page,
        lambda p: p.get_by_text(movie_title),
        timeout=30000
    )
    time.sleep(NAV_DELAY)
    
    # Navigate back
    back_button = SidebarLocators.get_element_with_retry(
        page,
        lambda p: p.get_by_role("button", name=re.compile("Back", re.IGNORECASE)).first,
        timeout=20000
    )
    safe_click(back_button, "back button")
    time.sleep(NAV_DELAY)
    
    # Verify filters persisted
    is_set, verification_method = verify_filter_state(page, "genre", "Drama")
    assert is_set, f"Genre filter not persisted after navigation ({verification_method})"
    logger.info(f"Verified genre persistence via {verification_method}")

if __name__ == "__main__":
    # Allow running tests directly during development
    pytest.main(["-v", "--headed", "--slowmo", "100", __file__])