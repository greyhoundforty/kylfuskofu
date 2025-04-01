from app import app
import pytest


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_random_entries(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Catalog" in response.data  # Check if the catalog title is in the response
    assert (
        len(response.data.split(b"catalog_tile")) >= 10
    )  # Ensure at least 10 catalog tiles are present


def test_catalog_tile_structure(client):
    response = client.get("/")
    assert response.status_code == 200
    assert (
        b'<div class="catalog-tile">' in response.data
    )  # Check for catalog tile structure
    assert b"<h3>" in response.data  # Check for title in catalog tile
    assert b"<p>" in response.data  # Check for description in catalog tile
