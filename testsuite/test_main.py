import json
import unittest
from unittest.mock import patch, AsyncMock, Mock
from main import get_base_and_quote_assets, convert_to_dollars, get_gecko_coin_list, gecko_coin_api_get_coins
from sql_database.models import Cryptocurrency
import respx
import httpx
from httpx import Response, HTTPError, HTTPStatusError, RequestError
import asynctest
import asyncio
import pytest


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

    # @respx.mock
    # def test_gecko_coin_api_get_coins(self):
    #     json_response = [
    #         {"id": "aave", "symbol": "aave", "name": "Aave"},
    #         {"id": "solana", "symbol": "sol", "name": "Solana"},
    #     ]
    #     route = respx.get("https://api.coingecko.com/api/v3/coins/list").mock(return_value=Response(200, json=json_response))
    #     actual = gecko_coin_api_get_coins()
    #     actual_json = actual.json()
    #     expected = json_response
    #     assert route.called
    #     assert respx.calls.call_count == 1
    #     assert actual.status_code == 200
    #     self.assertEqual(actual_json, expected)
        
    @respx.mock
    def test_gecko_coin_api_get_coins_bad_response(self):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.url = "https://api.coingecko.com/api/v3/coins/list"
        respx.get("https://api.coingecko.com/api/v3/coins/list").mock(side_effect=HTTPStatusError(message="test run", request=mock_response, response=mock_response))        
        with self.assertRaises(HTTPStatusError):
            actual = gecko_coin_api_get_coins()
            # httpx.get("https://api.coingecko.com/api/v3/coins/list")
        # with self.assertRaises(httpx.HTTPStatusError):
        #     gecko_coin_api_get_coins()
        # assert route.called
        assert respx.calls.call_count == 1
        # assert actual.status_code == 400

        
if __name__ == "__main__":
    unittest.main()
