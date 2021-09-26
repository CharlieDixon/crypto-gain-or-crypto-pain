import unittest
from unittest.mock import patch, AsyncMock, Mock
from main import get_base_and_quote_assets, convert_to_dollars, get_all_coins
from sql_database.models import Cryptocurrency
import respx
from httpx import Response
import asynctest
import asyncio


class TestMain(unittest.TestCase):
    def test_get_base_and_quote_assets(self):

        exchange_info_example = {
            "timezone": "UTC",
            "serverTime": 1565246363776,
            "symbols": [
                {
                    "symbol": "ETHBTC",
                    "status": "TRADING",
                    "baseAsset": "ETH",
                    "baseAssetPrecision": 8,
                    "quoteAsset": "BTC",
                    "quotePrecision": 8,
                    "quoteAssetPrecision": 8,
                    "orderTypes": [
                        "LIMIT",
                        "LIMIT_MAKER",
                        "MARKET",
                        "STOP_LOSS",
                        "STOP_LOSS_LIMIT",
                        "TAKE_PROFIT",
                        "TAKE_PROFIT_LIMIT",
                    ],
                }
            ],
        }
        expected_tuple = ({"ETHBTC": ("ETH", "BTC")}, {"ETH"})
        with patch("main.client.get_exchange_info") as mocked_binance:
            mocked_binance.return_value.ok = True
            mocked_binance.return_value = exchange_info_example
            response = get_base_and_quote_assets()
            self.assertEqual(response, expected_tuple)

    @respx.mock
    def test_convert_to_dollars(self):
        test_id = "ethereum"
        params = {"ids": test_id, "vs_currencies": "usd"}
        route = respx.get(
            "https://api.coingecko.com/api/v3/simple/price", params=params
        ).mock(return_value=Response(200, json={test_id: {"usd": 3000}}))
        actual = convert_to_dollars(test_id)
        expected = 3000
        assert route.called
        assert respx.calls.call_count == 1
        self.assertEqual(actual, expected)

    @patch("main.Cryptocurrency")
    @patch("main.get_assets", new_callable=AsyncMock)
    @patch("main.client.get_ticker")
    @patch("main.SessionLocal")
    def test_def_get_all_coins(self, mock_db, mock_get_ticker, mock_get_assets, mock_crypto):
        # ensure 'exists' condition in for loop is always False
        mock_db.return_value.query.return_value.filter.return_value.first.return_value = (
            False
        )
        mock_get_ticker.return_value = [
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
        mock_get_assets.return_value = {
            "ETHBC": ("ETH", "BTC"),
            "BNBETH": ("BNB", "ETH"),
        }, None
        mock_crypto = Mock()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(get_all_coins())
        loop.close()
        


# class TestAsyncFunctions(asynctest.TestCase):
#     @asynctest.patch("main.get_assets", scope="limited")
#     @patch("main.client.get_ticker")
#     @patch("main.SessionLocal", return_value="PLACEHOLDER")
#     async def test_def_get_all_coins(self, mock_db, get_ticker, get_assets):
#         get_ticker.return_value = [
#             {
#                 "symbol": "ETHBTC",
#                 "priceChange": "0.00010800",
#                 "priceChangePercent": "0.157",
#                 "weightedAvgPrice": "0.06800151",
#             },
#             {
#                 "symbol": "BNBETH",
#                 "priceChange": "-0.00480000",
#                 "priceChangePercent": "-3.983",
#                 "weightedAvgPrice": "0.11887713",
#             },
#         ]
#         get_assets.return_value = {"ETHBC": ("ETH", "BTC"), "BNBETH": ("BNB", "ETH")}
#         await get_all_coins()


if __name__ == "__main__":
    unittest.main()
