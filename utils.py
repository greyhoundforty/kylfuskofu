#!/usr/bin/env python3
import os
import time
import random
import httpx
from tamga import Tamga
from playwright.sync_api import sync_playwright
from datetime import datetime, date

# Configure tamga logger
logger = Tamga(logToJSON=True, logToConsole=True)

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
        story_type: Either "new" or "show" to specify which endpoint to use
    
    Returns:
        List of story IDs
    """
    logger.debug(f"Fetching story IDs from Hacker News {story_type}")
    
    if story_type == "new":
        url = "https://hacker-news.firebaseio.com/v0/newstories.json"
    elif story_type == "show":
        url = "https://hacker-news.firebaseio.com/v0/showstories.json"
    else:
        raise ValueError(f"Invalid story type: {story_type}")
    
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
            if not story or 'url' not in story or 'title' not in story:
                logger.warning(f"Story {story_id} is missing URL or title")
                return None
                
            return story
    except Exception as e:
        logger.error(f"Error fetching story {story_id} details: {e}")
        return None


def get_random_hackernews_stories(story_type, count=10, url_exists_func=None):
    """
    Get random Hacker News stories.
    
    Args:
        story_type: Either "new" or "show"
        count: Number of stories to retrieve (default: 10)
        url_exists_func: Function to check if URL exists in database
        
    Returns:
        List of (url, title, source) tuples
    """
    logger.debug(f"Getting {count} random stories from Hacker News {story_type}")
    
    source = f"hackernews-{story_type}"
    story_ids = get_hackernews_story_ids(story_type)
    
    if not story_ids:
        logger.error(f"No story IDs retrieved from {story_type}")
        return []
    
    # Shuffle the IDs to get random stories
    random.shuffle(story_ids)
    
    stories = []
    processed_ids = 0
    
    # Process IDs until we have enough stories or run out
    while len(stories) < count and processed_ids < len(story_ids):
        story_id = story_ids[processed_ids]
        processed_ids += 1
        
        # Get story details
        story_details = get_hackernews_story_details(story_id)
        
        if not story_details:
            continue
            
        url = story_details.get('url')
        title = story_details.get('title')
        
        # Some HN posts don't have external URLs, create an HN link
        if not url:
            url = f"https://news.ycombinator.com/item?id={story_id}"
            
        # Check if this URL already exists in our database
        if url_exists_func is None or not url_exists_func(url):
            stories.append((url, title, source))
        else:
            logger.debug(f"Story URL already in database: {url}")
        
        # Avoid hitting the API too quickly
        time.sleep(0.5)
    
    logger.info(f"Retrieved {len(stories)} unique random stories from Hacker News {story_type}")
    return stories