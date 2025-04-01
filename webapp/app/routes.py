from flask import Blueprint, render_template, jsonify
from .database import get_random_entries, get_entries_by_source
from .logger import logger

routes = Blueprint("routes", __name__)


@routes.route("/")
def index():
    logger.info("Processing request for index route")

    # Get entries for each source - updating to match actual database source names
    # For Hacker News, we'll combine both hackernews sources
    hackernews_new = get_entries_by_source("hackernews-new", 5)
    hackernews_show = get_entries_by_source("hackernews-show", 5)
    hackernews_entries = hackernews_new + hackernews_show

    # These match your actual source names
    indieblog_entries = get_entries_by_source("indieblog.page", 10)
    kb512_entries = get_entries_by_source("512kb.club", 10)

    return render_template(
        "index.html",
        hackernews_entries=hackernews_entries,
        indieblog_entries=indieblog_entries,
        kb512_entries=kb512_entries,
    )


@routes.route("/api/random-entries")
def api_random_entries():
    try:
        logger.info("API request for random entries")

        # Get entries for each source - using actual database source names
        hackernews_new = get_entries_by_source("hackernews-new", 3)
        hackernews_show = get_entries_by_source("hackernews-show", 3)
        indieblog_entries = get_entries_by_source("indieblog.page", 5)
        kb512_entries = get_entries_by_source("512kb.club", 5)

        all_entries = (
            hackernews_new + hackernews_show + indieblog_entries + kb512_entries
        )

        entries_list = []
        for entry in all_entries:
            entry_dict = entry.copy()
            entry_dict["description"] = entry["source"]
            entry_dict[
                "image_url"
            ] = f"https://via.placeholder.com/300x200?text={entry['title']}"
            entries_list.append(entry_dict)

        return jsonify({"entries": entries_list})
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}")
        return jsonify({"entries": [], "error": str(e)})
