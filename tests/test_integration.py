import pytest
from unittest.mock import patch, MagicMock
import random_site
from random_site import collect_five_unique_sites


def test_collect_sites_integration():
    """Test the full collection process with mocked browser."""
    # Mock get_random_site to return predetermined values
    with patch(
        "random_site.get_random_site",
        side_effect=[
            ("https://example1.com", "Example 1"),
            ("https://example2.com", "Example 2"),
            ("https://example3.com", "Example 3"),
            ("https://example4.com", "Example 4"),
            ("https://example5.com", "Example 5"),
            ("https://example6.com", "Example 6"),
            ("https://example7.com", "Example 7"),
            ("https://example8.com", "Example 8"),
            ("https://example9.com", "Example 9"),
            ("https://example10.com", "Example 10"),
        ],
    ), patch("random_site.url_exists", return_value=False), patch(
        "random_site.add_url_to_db"
    ) as mock_add_url, patch(
        "random_site.init_database"
    ):
        collect_five_unique_sites()
        # Verify add_url_to_db was called 10 times
        assert mock_add_url.call_count == 10
