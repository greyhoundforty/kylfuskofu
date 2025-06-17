#!/usr/bin/env python3
import os
import time
import random
import httpx
import re
import sqlite3
from tamga import Tamga
from playwright.sync_api import sync_playwright
from datetime import datetime, date
from urllib.parse import urljoin, urlparse
from typing import List, Tuple, Optional, Dict

# Configure tamga logger
logger = Tamga(logToJSON=True, logToConsole=True)

# =============================================================================
# EXISTING FUNCTIONS (UNCHANGED)
# =============================================================================


def get_random_site():
    """Get a random site from 512kb.club and return its URL and title."""
    logger.debug("Getting random site from 512kb.club")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://512kb.club")

        # Set up event listener for new pages before clicking
        with context.expect_page() as new_page_info:
            # Click the random button
            page.click("a.button.random")

        # Get the new page that was opened
        new_page = new_page_info.value
        new_page.wait_for_load_state("networkidle")

        # Grab the URL and title of the new page
        random_url = new_page.url
        title = new_page.title()

        browser.close()
        logger.debug(f"Retrieved random site: {random_url}")
        return random_url, title


def get_random_indieblog():
    """Get a random site from indieblog.page and return its URL and title."""
    logger.debug("Getting random site from indieblog.page")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://indieblog.page/")

        # Set up event listener for new pages before clicking
        with context.expect_page() as new_page_info:
            # Click the random button using the correct selector from HTML
            page.click("a#stumble")

        # Get the new page that was opened
        new_page = new_page_info.value
        new_page.wait_for_load_state("networkidle")

        # Grab the URL and title of the new page
        random_url = new_page.url
        title = new_page.title()

        browser.close()
        logger.debug(f"Retrieved random site: {random_url}")
        return random_url, title


def get_hackernews_story_ids(story_type):
    """
    Fetch story IDs from Hacker News API.

    Args:
        story_type: Must be "show" to specify the endpoint to use

    Returns:
        List of story IDs
    """
    logger.debug(f"Fetching story IDs from Hacker News {story_type}")

    if story_type == "show":
        url = "https://hacker-news.firebaseio.com/v0/showstories.json"
    else:
        raise ValueError(f"Invalid story type: {story_type}, only 'show' is supported")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            story_ids = response.json()
            logger.debug(f"Retrieved {len(story_ids)} {story_type} story IDs")
            return story_ids
    except Exception as e:
        logger.error(f"Error fetching Hacker News {story_type} story IDs: {e}")
        return []


def get_hackernews_story_details(story_id):
    """
    Fetch details for a specific Hacker News story.

    Args:
        story_id: The ID of the story to fetch

    Returns:
        Dictionary containing story details, or None if an error occurred
    """
    logger.debug(f"Fetching details for story {story_id}")
    url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            story = response.json()

            # Check if it's a valid story with a URL and title
            if not story or "url" not in story or "title" not in story:
                logger.warning(f"Story {story_id} is missing URL or title")
                return None

            return story
    except Exception as e:
        logger.error(f"Error fetching story {story_id} details: {e}")
        return None


def get_random_linkwarden_links(api_url, api_key, count=10, url_exists_func=None):
    """
    Get random links from a Linkwarden account.

    Args:
        api_url: The base URL for the Linkwarden API (e.g., "https://linkwarden.example.com")
        api_key: API key or token for authentication
        count: Number of links to retrieve (default: 10)
        url_exists_func: Function to check if URL exists in database

    Returns:
        List of (url, title, source) tuples
    """
    logger.debug(f"Getting {count} random links from Linkwarden")

    # Set up headers with authentication following the docs
    headers = {"Accept": "application/json", "Authorization": f"Bearer {api_key}"}

    # Ensure we're using the correct endpoint path
    endpoint = "/api/v1/links"
    full_url = api_url.rstrip("/") + endpoint

    try:
        # Fetch all bookmarks from Linkwarden
        with httpx.Client(timeout=30.0) as client:
            logger.debug(f"Making request to Linkwarden API: {full_url}")
            response = client.get(full_url, headers=headers)

            # Debug information on response
            logger.debug(f"Linkwarden API response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Linkwarden API error: {response.text}")

            response.raise_for_status()
            all_links = response.json()

            logger.debug(f"Retrieved {len(all_links)} total links from Linkwarden")

            # Filter out links that don't have URLs or titles
            valid_links = [
                link for link in all_links if link.get("url") and link.get("title")
            ]

            # If we don't have enough links, return all we have
            if len(valid_links) <= count:
                selected_links = valid_links
            else:
                # Otherwise, get a random sample
                selected_links = random.sample(valid_links, count)

            results = []
            for link in selected_links:
                url = link.get("url")
                title = link.get("title")

                # Check if this URL already exists in our database
                if url_exists_func is None or not url_exists_func(url):
                    results.append((url, title, "linkwarden"))
                else:
                    logger.debug(f"Link URL already in database: {url}")

            logger.info(f"Retrieved {len(results)} unique random links from Linkwarden")
            return results

    except Exception as e:
        logger.error(f"Error fetching links from Linkwarden: {e}")
        return []


# =============================================================================
# NEW ENHANCED FUNCTIONS
# Updated 2025-06-16: Simplified 512kb to check for English sites instead of blog detection
# =============================================================================


def check_512kb_site_is_english(
    url: str, title: str
) -> Tuple[bool, Optional[str], str]:
    """
    Check if a 512kb site is in English and return basic site info.
    Updated 2025-06-16: Simplified approach focusing on English detection instead of blog analysis.
    """
    logger.info(f"🔍 Checking if site is English: {url}")

    try:
        with sync_playwright() as p:
            logger.info("🌐 Launching browser...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (compatible; SiteChecker/1.0)"
            )
            page = context.new_page()

            # Set timeout and load page
            page.set_default_timeout(10000)
            logger.info(f"📄 Loading page: {url}")
            page.goto(url, wait_until="networkidle")
            logger.info("✅ Page loaded successfully")

            # Check if site is in English
            is_english = detect_english_content(page, title)

            if is_english:
                logger.info("✅ Site appears to be in English")
                # Generate simple markdown entry for English site
                markdown = f"## {title}\n\n- [{title}]({url})\n\n"
                browser.close()
                return True, markdown, "english_site"
            else:
                logger.info("❌ Site does not appear to be in English")
                browser.close()
                return False, None, "non_english"

    except Exception as e:
        logger.error(f"💥 Error checking {url}: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False, None, "error"


def detect_english_content(page, title: str) -> bool:
    """
    Detect if a webpage content is primarily in English.
    Updated 2025-06-16: New function for English detection.
    """
    logger.info("🔍 Starting English content detection...")

    try:
        # Check 1: HTML lang attribute
        html_element = page.query_selector("html")
        if html_element:
            lang_attr = html_element.get_attribute("lang")
            if lang_attr and lang_attr.lower().startswith("en"):
                logger.info(f"✅ Found English lang attribute: {lang_attr}")
                return True

        # Check 2: Common English words in title
        english_title_words = [
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "about",
            "home",
            "page",
            "blog",
            "site",
            "web",
            "news",
            "contact",
            "portfolio",
            "work",
            "project",
            "code",
            "tech",
            "development",
            "design",
            "digital",
        ]

        title_lower = title.lower()
        title_english_words = sum(
            1 for word in english_title_words if word in title_lower
        )

        if title_english_words >= 2:
            logger.info(f"✅ Found {title_english_words} English words in title")
            return True

        # Check 3: Page content sample
        # Get some text content from the page
        content_selectors = ["p", "h1", "h2", "h3", "nav", "main", "article"]
        sample_text = ""

        for selector in content_selectors:
            elements = page.query_selector_all(selector)
            for element in elements[:3]:  # Limit to first 3 of each type
                text = element.text_content()
                if text:
                    sample_text += text + " "
                if len(sample_text) > 500:  # Get enough sample text
                    break
            if len(sample_text) > 500:
                break

        # Check for English words in content
        common_english_words = [
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "this",
            "that",
            "are",
            "is",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "will",
            "would",
            "could",
            "should",
            "can",
            "may",
            "might",
            "must",
            "shall",
            "about",
            "after",
            "before",
            "during",
            "through",
            "over",
            "under",
            "above",
            "home",
            "page",
            "site",
            "website",
            "blog",
            "post",
            "article",
            "content",
        ]

        if sample_text:
            sample_lower = sample_text.lower()
            english_word_count = sum(
                1 for word in common_english_words if f" {word} " in f" {sample_lower} "
            )

            # Calculate rough percentage
            total_words = len(sample_text.split())
            if total_words > 0:
                english_percentage = (
                    english_word_count / min(total_words, 50)
                ) * 100  # Cap at 50 words for percentage calc
                logger.info(
                    f"English word analysis: {english_word_count} common English words, ~{english_percentage:.1f}% English"
                )

                if english_percentage >= 20:  # If at least 20% common English words
                    logger.info(
                        "✅ Content appears to be English based on word analysis"
                    )
                    return True

        # Check 4: Navigation and common page elements
        nav_elements = page.query_selector_all("nav a, .nav a, .menu a, header a")
        nav_text = ""
        for element in nav_elements[:10]:  # Check first 10 nav links
            text = element.text_content()
            if text:
                nav_text += text.lower() + " "

        english_nav_words = [
            "home",
            "about",
            "contact",
            "blog",
            "work",
            "portfolio",
            "projects",
            "services",
        ]
        nav_english_count = sum(1 for word in english_nav_words if word in nav_text)

        if nav_english_count >= 2:
            logger.info(f"✅ Found {nav_english_count} English navigation words")
            return True

        logger.info("❌ Site does not appear to be primarily English")
        return False

    except Exception as e:
        logger.warning(f"Error detecting English content: {e}")
        # Default to True if we can't determine (benefit of the doubt)
        return True


def generate_simple_512kb_markdown(sites: List[Tuple[str, str, str]]) -> str:
    """
    Generate markdown for 512kb sites.
    Updated 2025-06-16: Simplified to show just the sites without blog post extraction.
    """
    if not sites:
        return "## 512KB Club Sites\n\n*No English sites found*\n"

    markdown = "## 512KB Club Sites\n\n"
    for url, title, _ in sites:
        markdown += f"- [{title}]({url})\n"
    markdown += "\n"

    return markdown


def generate_markdown_for_site(site_name: str, posts: List[Dict[str, str]]) -> str:
    """Generate markdown for a site's blog posts. (Legacy function - kept for compatibility)"""
    if not posts:
        return f"## {site_name}\n\n*No recent posts found*\n"

    markdown = f"## {site_name}\n\n"
    for post in posts:
        markdown += f"- [{post['title']}]({post['url']})\n"
    markdown += "\n"

    return markdown


def get_hackernews_stories_by_type(
    story_type: str, count: int = 10, url_exists_func=None
) -> List[Tuple[str, str, str]]:
    """Get Hacker News stories by type (show, new, top, etc.)."""
    logger.debug(f"Fetching {count} stories from Hacker News {story_type}")

    # Map story types to API endpoints
    endpoints = {
        "show": "https://hacker-news.firebaseio.com/v0/showstories.json",
        "new": "https://hacker-news.firebaseio.com/v0/newstories.json",
        "top": "https://hacker-news.firebaseio.com/v0/topstories.json",
    }

    if story_type not in endpoints:
        logger.error(f"Unknown story type: {story_type}")
        return []

    try:
        # Get story IDs
        with httpx.Client(timeout=10.0) as client:
            response = client.get(endpoints[story_type])
            response.raise_for_status()
            story_ids = response.json()[: count * 2]  # Get more IDs than needed

        stories = []
        source = f"hackernews-{story_type}"

        for story_id in story_ids:
            if len(stories) >= count:
                break

            story_details = get_hackernews_story_details(story_id)
            if not story_details:
                continue

            url = story_details.get("url")
            title = story_details.get("title")

            # Create HN link if no external URL
            if not url:
                url = f"https://news.ycombinator.com/item?id={story_id}"

            if title:
                # Check if this URL already exists in our database
                if url_exists_func is None or not url_exists_func(url):
                    stories.append((url, title, source))
                else:
                    logger.debug(f"Story URL already in database: {url}")

            time.sleep(0.2)  # Rate limiting

        logger.info(f"Retrieved {len(stories)} {story_type} stories")
        return stories

    except Exception as e:
        logger.error(f"Error fetching {story_type} stories: {e}")
        return []


def generate_hackernews_markdown(
    show_stories: List[Tuple[str, str, str]], new_stories: List[Tuple[str, str, str]]
) -> str:
    """Generate combined markdown for Hacker News show and new stories."""
    markdown = ""

    if show_stories:
        markdown += "## Hacker News - Show HN\n\n"
        for url, title, _ in show_stories:
            markdown += f"- [{title}]({url})\n"
        markdown += "\n"

    if new_stories:
        markdown += "## Hacker News - New Stories\n\n"
        for url, title, _ in new_stories:
            markdown += f"- [{title}]({url})\n"
        markdown += "\n"

    return markdown


def get_reduced_indieblog_posts(
    count: int = 5, url_exists_func=None
) -> List[Tuple[str, str, str]]:
    """Get reduced number of random indie blog posts."""
    logger.debug(f"Getting {count} random indie blog posts")

    posts = []
    attempts = 0
    max_attempts = count * 3  # Try more than needed to account for duplicates

    while len(posts) < count and attempts < max_attempts:
        try:
            url, title = get_random_indieblog()

            # Check if this URL already exists in our database
            if url_exists_func is None or not url_exists_func(url):
                posts.append((url, title, "indieblog.page"))
            else:
                logger.debug(f"Indie blog URL already in database: {url}")

            time.sleep(1)  # Rate limiting

        except Exception as e:
            logger.warning(f"Failed to get indie blog post: {e}")

        attempts += 1

    return posts[:count]


def generate_indieblog_markdown(posts: List[Tuple[str, str, str]]) -> str:
    """Generate markdown for indie blog posts."""
    if not posts:
        return "## IndieWeb Blogs\n\n*No posts found*\n"

    markdown = "## IndieWeb Blogs\n\n"
    for url, title, _ in posts:
        markdown += f"- [{title}]({url})\n"
    markdown += "\n"

    return markdown


def save_markdown_report(markdown_content: str):
    """Save markdown report to file with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scraped_sites_{timestamp}.md"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        logger.info(f"Saved markdown report to {filename}")
    except Exception as e:
        logger.error(f"Failed to save markdown report: {e}")


# =============================================================================
# DATABASE HELPER FUNCTIONS
# =============================================================================


def update_site_english_status(
    url: str, is_english: bool, status: str, posts_md: str = None
):
    """Update a site's English language status in the database.
    Updated 2025-06-16: Changed from blog analysis to English detection.
    """
    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    now = datetime.now()
    cursor.execute(
        """
        UPDATE sites
        SET has_blog = ?, blog_status = ?, blog_posts_md = ?, last_blog_check = ?
        WHERE url = ?
    """,
        (is_english, status, posts_md, now, url),
    )

    conn.commit()
    conn.close()
    logger.debug(f"Updated English status for {url}: {status}")


def get_sites_needing_english_check(limit: int = 10) -> List[Tuple[str, str]]:
    """Get sites that need English language check (512kb sites without language status).
    Updated 2025-06-16: Changed from blog analysis to English detection.
    """
    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT url, title FROM sites
        WHERE source = '512kb.club'
        AND (has_blog IS NULL OR last_blog_check IS NULL)
        LIMIT ?
    """,
        (limit,),
    )

    results = cursor.fetchall()
    conn.close()
    return results


def analyze_existing_sites_for_english(limit=50):
    """Analyze existing 512kb sites to check if they are English.
    Updated 2025-06-16: Changed from blog analysis to English detection.
    """
    logger.info("Checking existing 512kb sites for English language")

    sites_to_analyze = get_sites_needing_english_check(limit)
    logger.info(f"Found {len(sites_to_analyze)} sites to check")

    for i, (url, title) in enumerate(sites_to_analyze, 1):
        logger.info(f"Checking {i}/{len(sites_to_analyze)}: {url}")

        try:
            is_english, posts_md, status = check_512kb_site_is_english(url, title)
            update_site_english_status(url, is_english, status, posts_md)

            # Rate limiting
            time.sleep(2)

        except Exception as e:
            logger.error(f"Failed to check {url}: {e}")
            update_site_english_status(url, False, "error")
            continue

    logger.info("English language check complete")


def generate_markdown_from_existing_data():
    """Generate markdown report from existing analyzed data.
    Updated 2025-06-16: Now includes English 512kb sites instead of blog sites.
    """
    logger.info("Generating markdown from existing data")

    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # Get English 512kb sites
    cursor.execute(
        """
        SELECT url, title FROM sites
        WHERE has_blog = TRUE
        AND source = '512kb.club'
        ORDER BY last_blog_check DESC
        LIMIT 20
    """
    )

    english_sites = cursor.fetchall()

    # Get recent HN stories
    cursor.execute(
        """
        SELECT url, title FROM sites
        WHERE source LIKE 'hackernews-%'
        ORDER BY capture_date DESC
        LIMIT 20
    """
    )

    hn_stories = cursor.fetchall()

    # Get recent indie blogs
    cursor.execute(
        """
        SELECT url, title FROM sites
        WHERE source = 'indieblog.page'
        ORDER BY capture_date DESC
        LIMIT 10
    """
    )

    indie_blogs = cursor.fetchall()
    conn.close()

    # Generate markdown
    markdown_sections = []

    if english_sites:
        sites_markdown = "## 512KB Club Sites (English)\n\n"
        for url, title in english_sites:
            sites_markdown += f"- [{title}]({url})\n"
        markdown_sections.append(sites_markdown.rstrip())

    if hn_stories:
        hn_markdown = "## Recent Hacker News Stories\n\n"
        for url, title in hn_stories:
            hn_markdown += f"- [{title}]({url})\n"
        markdown_sections.append(hn_markdown.rstrip())

    if indie_blogs:
        indie_markdown = "## Recent IndieWeb Blogs\n\n"
        for url, title in indie_blogs:
            indie_markdown += f"- [{title}]({url})\n"
        markdown_sections.append(indie_markdown.rstrip())

    final_markdown = "\n\n".join(markdown_sections)
    save_markdown_report(final_markdown)

    return final_markdown


# =============================================================================
# ENHANCED COLLECTION FUNCTION
# =============================================================================


def collect_unique_sites_enhanced(
    local=False, url_exists_func=None, add_url_to_db_func=None
):
    """
    Enhanced version of collect_unique_sites with new markdown generation.
    Updated 2025-06-16: Changed 512kb collection to focus on English sites instead of blog detection.

    Args:
        local: Whether to run in local mode
        url_exists_func: Function to check if URL exists in database
        add_url_to_db_func: Function to add URL to database

    Returns:
        Tuple of (collected_sites, markdown_content)
    """
    logger.info("Starting enhanced collection of unique sites")

    collected_sites = []
    markdown_sections = []

    # 1. Enhanced 512kb collection with English detection
    logger.info("=" * 60)
    logger.info("STARTING 512KB COLLECTION WITH ENGLISH DETECTION")
    logger.info("=" * 60)

    sites_512kb_english = []
    unique_sites_collected = 0
    attempts = 0
    max_attempts = 20

    while unique_sites_collected < 10 and attempts < max_attempts:
        attempts += 1
        logger.info(
            f"512kb attempt {attempts}/{max_attempts}, collected {unique_sites_collected}/10 sites"
        )

        try:
            logger.info(f"Getting random site from 512kb.club...")
            url, title = get_random_site()
            logger.info(f"Got site: {url} - {title}")

            if url_exists_func is None or not url_exists_func(url):
                logger.info(f"Site is new, checking if English...")

                # Check if site is English
                is_english, posts_md, status = check_512kb_site_is_english(url, title)
                logger.info(
                    f"English check result: is_english={is_english}, status={status}"
                )

                # Add to database with English status
                if add_url_to_db_func:
                    logger.info(f"Adding to database...")
                    add_url_to_db_func(url, title, "512kb.club")
                    update_site_english_status(url, is_english, status, posts_md)
                    logger.info(f"Added to database successfully")

                collected_sites.append((url, title, "512kb.club"))

                if is_english:
                    sites_512kb_english.append((url, title, "512kb.club"))
                    logger.info(
                        f"Added English site! Total English 512kb sites: {len(sites_512kb_english)}"
                    )
                else:
                    logger.info(f"Site is not English, not added to English list")

                unique_sites_collected += 1
                logger.info(f"Successfully processed site {unique_sites_collected}/10")
            else:
                logger.info(f"Site already in database, skipping: {url}")

            logger.info(f"Sleeping for 2 seconds...")
            time.sleep(2)

        except Exception as e:
            logger.error(f"Error processing 512kb site (attempt {attempts}): {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")

    logger.info(
        f"512kb collection complete. Processed {unique_sites_collected} sites, {len(sites_512kb_english)} are English"
    )

    # Generate 512kb markdown
    logger.info(
        f"Generating 512kb markdown from {len(sites_512kb_english)} English sites..."
    )
    if sites_512kb_english:
        kb_markdown = generate_simple_512kb_markdown(sites_512kb_english)

        if kb_markdown.strip():
            markdown_sections.append(kb_markdown.rstrip())
            logger.info(f"Added 512kb markdown section ({len(kb_markdown)} chars)")
        else:
            logger.warning("512kb markdown was empty after strip()")
    else:
        logger.warning("No English 512kb sites found - no markdown section generated")

    # 2. Enhanced Hacker News collection
    logger.info("=" * 60)
    logger.info("STARTING HACKER NEWS COLLECTION")
    logger.info("=" * 60)

    show_stories = get_hackernews_stories_by_type("show", 5, url_exists_func)
    new_stories = get_hackernews_stories_by_type("new", 5, url_exists_func)

    logger.info(f"Got {len(show_stories)} show stories, {len(new_stories)} new stories")

    # Add to database
    if add_url_to_db_func:
        for url, title, source in show_stories + new_stories:
            add_url_to_db_func(url, title, source)

    collected_sites.extend(show_stories + new_stories)

    # Generate HN markdown
    hn_markdown = generate_hackernews_markdown(show_stories, new_stories)
    if hn_markdown.strip():
        markdown_sections.append(hn_markdown.rstrip())
        logger.info(f"Added HN markdown section ({len(hn_markdown)} chars)")
    else:
        logger.warning("HN markdown was empty")

    # 3. Reduced indie blog collection
    logger.info("=" * 60)
    logger.info("STARTING INDIE BLOG COLLECTION")
    logger.info("=" * 60)

    indie_posts = get_reduced_indieblog_posts(5, url_exists_func)
    logger.info(f"Got {len(indie_posts)} indie blog posts")

    # Add to database
    if add_url_to_db_func:
        for url, title, source in indie_posts:
            add_url_to_db_func(url, title, source)

    collected_sites.extend(indie_posts)

    # Generate indie markdown
    indie_markdown = generate_indieblog_markdown(indie_posts)
    if indie_markdown.strip():
        markdown_sections.append(indie_markdown.rstrip())
        logger.info(f"Added indie markdown section ({len(indie_markdown)} chars)")
    else:
        logger.warning("Indie markdown was empty")

    # 4. Compile final markdown report
    logger.info("=" * 60)
    logger.info("COMPILING FINAL MARKDOWN REPORT")
    logger.info("=" * 60)

    logger.info(f"Total markdown sections: {len(markdown_sections)}")
    for i, section in enumerate(markdown_sections, 1):
        logger.info(f"Section {i} length: {len(section)} chars")
        logger.info(f"Section {i} preview: {section[:100]}...")

    final_markdown = ""
    if markdown_sections:
        final_markdown = "\n\n".join(markdown_sections)
        logger.info(f"Generated final markdown report ({len(final_markdown)} chars)")

        # Save markdown report
        save_markdown_report(final_markdown)
    else:
        logger.warning("No markdown sections generated!")

    logger.info(f"Enhanced collection complete. Added {len(collected_sites)} new sites")
    return collected_sites, final_markdown
