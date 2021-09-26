from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert str(response.template) == "<Template 'homepage.html'>"
    
def test_limit_dropdown():
    response = client.get("/limit-dropdown")
    assert response.status_code == 200