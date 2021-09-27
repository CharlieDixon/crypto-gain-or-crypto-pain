from main import app, get_db, get_all_coins
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert str(response.template) == "<Template 'homepage.html'>"


def test_limit_dropdown():
    response = client.get("/limit-dropdown")
    assert response.status_code == 200
