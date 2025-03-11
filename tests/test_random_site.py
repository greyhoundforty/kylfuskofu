import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from random_site import init_database, url_exists, add_url_to_db, get_random_site


def test_database_initialization():
    """Test that the database can be initialized."""
    with patch("sqlite3.connect"):
        init_database()
        sqlite3.connect.assert_called_once()


def test_url_exists():
    """Test that we can check if URL exists in database."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("sqlite3.connect", return_value=mock_conn):
        url_exists("https://example.com")
        mock_cursor.execute.assert_called_once()


def test_add_url():
    """Test that we can add URL to database."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("sqlite3.connect", return_value=mock_conn):
        add_url_to_db("https://example.com", "Example Site")
        mock_cursor.execute.assert_called_once()
