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

@pytest.mark.asyncio
async def test_get_all_coins(mocker):
    mock_get_ticker_return_value = [
        {
            "symbol": "ETHBTC",
            "priceChange": "0.00010800",
            "priceChangePercent": "0.157",
            "weightedAvgPrice": "0.06800151",
        },
        {
            "symbol": "BNBETH",
            "priceChange": "-0.00480000",
            "priceChangePercent": "-3.983",
            "weightedAvgPrice": "0.11887713",
        },
    ]
    mocker.patch("main.client.get_ticker", return_value=mock_get_ticker_return_value)
    mocker.patch("main.get_assets", return_value=({"ETHBTC": ("ETH", "BTC")}, None))
    mocker.patch("main.SessionLocal", return_value="WHAT")
    result = await get_all_coins()
    assert result == "BAN"
    
# def override_get_db_dependency(mocker):
#     override = mocker.MagicMock()
#     override.query.return_value = "EXAMPLE"
#     override.return_value = "TWO"
#     return override


# @pytest.mark.asyncio
# async def test_get_all_coins(mocker):
#     app.dependency_overrides[get_db] = override_get_db_dependency
#     mock_get_ticker_return_value = [
#         {
#             "symbol": "ETHBTC",
#             "priceChange": "0.00010800",
#             "priceChangePercent": "0.157",
#             "weightedAvgPrice": "0.06800151",
#         },
#         {
#             "symbol": "BNBETH",
#             "priceChange": "-0.00480000",
#             "priceChangePercent": "-3.983",
#             "weightedAvgPrice": "0.11887713",
#         },
#     ]
#     # override get_db dependency
#     mocker.patch("main.client.get_ticker", return_value=mock_get_ticker_return_value)
#     mocker.patch("main.get_assets", return_value=({"ETHBTC": ("ETH", "BTC")}, None))
#     result = await get_all_coins()
#     assert result == "BAN"
#     # reset override of dependency
#     app.dependency_overrides = {}