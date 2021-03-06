import unittest
from unittest.mock import patch
from main import get_base_and_quote_assets, convert_to_dollars
import respx
from httpx import Response


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


if __name__ == "__main__":
    unittest.main()
