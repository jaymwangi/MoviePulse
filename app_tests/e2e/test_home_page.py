import pytest
from playwright.sync_api import Page, expect
import time
import urllib.parse
import logging

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def locate_movie_titles(page: Page):
    strategies = [
        lambda: page.locator('[data-testid^="movie-title"]'),
        lambda: page.locator('.movie-title'),
        lambda: page.locator("h1, h2, h3, h4").filter(has_text=""),
    ]
    for i, strategy in enumerate(strategies, start=1):
        try:
            locator = strategy()
            count = locator.count()
            if count > 0:
                logger.info(f"✅ Found movie titles using strategy {i} (count={count})")
                return locator
        except Exception as e:
            logger.warning(f"⚠️ Strategy {i} failed: {str(e)}")
    raise Exception("❌ Could not locate movie titles using any strategy")

@pytest.mark.parametrize("search_query", ["Inception", "The Matrix"])
def test_url_param_sync(page: Page, base_url, search_query):
    page.set_default_timeout(10000)

    try:
        logger.info(f"🌐 Navigating to {base_url}")
        page.goto(base_url, timeout=20000)

        logger.info("⏳ Waiting for Streamlit app to connect...")
        page.wait_for_selector(
            '[data-testid="stApp"][data-test-connection-state="CONNECTED"]',
            state="attached",
            timeout=20000
        )
        logger.info("✅ Streamlit app is connected.")

        def locate_search_input():
            try:
                input_locator = page.locator('input[type="text"][aria-label*="Search movies"]')
                if input_locator.count() > 0:
                    logger.info("✔️ Found search input by aria-label")
                    return input_locator

                label_locator = page.get_by_text("🔍 Search movies, actors, or moods...", exact=True)
                if label_locator.count() > 0:
                    input_field = label_locator.locator('.. >> input[type="text"]')
                    if input_field.count() > 0:
                        logger.info("✔️ Found search input via label")
                        return input_field

                placeholder_locator = page.get_by_placeholder("Search movies, actors, or moods...")
                if placeholder_locator.count() > 0:
                    logger.info("✔️ Found search input by placeholder")
                    return placeholder_locator

                st_text_input = page.locator('.stTextInput input[type="text"]')
                if st_text_input.count() > 0:
                    logger.info("✔️ Found search input via Streamlit component")
                    return st_text_input

                raise Exception("No visible search input found")
            except Exception as e:
                logger.error(f"❌ Search input location failed: {str(e)}")
                raise

        search_input = None
        for attempt in range(1, 6):
            try:
                logger.info(f"🧭 Attempt {attempt}/5 to locate search input")
                search_input = locate_search_input()
                search_input.wait_for(state="visible", timeout=5000)
                if not search_input.is_editable():
                    raise Exception("Search input is not editable")
                logger.info("✅ Search input located and ready")
                break
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt} failed: {str(e)}")
                if attempt == 5:
                    logger.error("❌ Max attempts reached. Dumping partial page content:")
                    logger.error(page.content()[:1000])
                    raise
                time.sleep(2)

        for attempt in range(1, 4):
            try:
                logger.info(f"⌨️ Attempt {attempt}/3 to interact with search input")
                search_input.click()
                search_input.fill(search_query)
                search_input.press("Enter")
                logger.info("✅ Search query submitted")
                break
            except Exception as e:
                logger.warning(f"⚠️ Interaction attempt {attempt} failed: {str(e)}")
                if attempt == 3:
                    raise AssertionError(f"Failed to interact with search input: {str(e)}")
                time.sleep(1)

        expected_param = f"q={urllib.parse.quote_plus(search_query)}"
        try:
            logger.info(f"⏳ Waiting for URL to update with '{expected_param}'")
            page.wait_for_url(f"**/*{expected_param}*", timeout=10000, wait_until="networkidle")
            logger.info(f"✅ URL updated: {page.url}")
        except Exception as e:
            logger.error(f"❌ URL not updated. Current: {page.url}")
            raise AssertionError(f"Expected URL to contain '{expected_param}': {str(e)}")

        results_header_text = f"Results for: {search_query}"
        try:
            logger.info(f"🔍 Looking for results header: '{results_header_text}'")
            results_header = page.get_by_role("heading", name=results_header_text, exact=False)
            results_header.wait_for(state="visible", timeout=10000)
            logger.info("✅ Results header found")
        except Exception as e:
            raise AssertionError(f"❌ Results header not found: {str(e)}")

        try:
            logger.info("⏱️ Waiting briefly for tiles to render")
            time.sleep(1.5)

            movie_tiles = page.locator('[data-testid="movie-tile"]')
            count = movie_tiles.count()
            logger.info(f"🎞️ Found {count} movie tiles in the DOM")

            visible_count = 0
            for i in range(count):
                tile = movie_tiles.nth(i)
                try:
                    tile.scroll_into_view_if_needed(timeout=3000)
                    expect(tile).to_be_visible(timeout=2000)
                    visible_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ Tile {i} visibility check failed: {str(e)}")

            assert count > 0, "No movie tiles found in the DOM"
            logger.info(f"✅ {visible_count} of {count} movie tiles are visible")

            logger.info("🔍 Verifying movie titles match search")
            movie_titles = locate_movie_titles(page)
            if movie_titles.count() == 0:
                raise AssertionError("❌ No movie titles found")

            all_titles = movie_titles.all_inner_texts()
            logger.info(f"🎬 Found titles: {all_titles}")

            match_found = any(search_query.lower() in title.lower() for title in all_titles)
            assert match_found, f"No movie title matched search query '{search_query}'"
            logger.info("✅ Movie title match verified")

        except Exception as e:
            logger.error("❌ Movie tile or title verification failed")
            logger.error(f"DOM snapshot: {page.content()[:1000]}")
            raise AssertionError(f"❌ Verification failed: {str(e)}")

        logger.info("🎉 Test completed successfully")

    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        raise
