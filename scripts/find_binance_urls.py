"""This script creates a dictionary of coins with their corresponding binance info page urls where available."""

from binance import Client
import httpx
import configparser
from unidecode import unidecode
import json

cfg = configparser.ConfigParser()
cfg.read("binance_api_key.cfg")

client = Client(cfg.get("KEYS", "api_key"), cfg.get("KEYS", "api_secret_key"))


def get_trading_assets():
    assets = {}
    set_of_base_coins = set()
    set_of_quote_coins = set()
    exchange_info = client.get_exchange_info()
    for pair in exchange_info["symbols"]:
        if pair["status"] == "TRADING":
            # assets[pair["symbol"]] = pair["baseAsset"], pair["quoteAsset"]
            set_of_base_coins.add(pair["baseAsset"])
            set_of_quote_coins.add(pair["quoteAsset"])
    return set_of_base_coins | set_of_quote_coins

def create_coin_full_name_dict():
    info = client.get_all_coins_info()
    coin_name_dict = {}
    unique_coins = get_trading_assets()
    for coin in unique_coins:
        for item in info:
            if coin == item['coin']:
                coin_name_dict[coin] = item.get("name")

    return coin_name_dict

def get_binance_urls():
    binance_pages = {}
    coin_name_dict = create_coin_full_name_dict()
    with httpx.Client() as client:
        for coin, name in coin_name_dict.items():
            res = client.get(f"https://research.binance.com/en/projects/{coin}")
            print('top', str(res.url))
            if res.status_code != 200:
                name = name.replace(" ", "-") # replace white space in names with dashes
                name = unidecode(name) # remove accents from characters e.g. Atlético -> Atletico
                res = client.get(f"https://research.binance.com/en/projects/{name}")
                print('middle', str(res.url))
                if res.status_code != 200:
                    continue
            binance_pages[coin] = (str(res.url))
    return binance_pages

get_trading_assets()
create_coin_full_name_dict()
binance_urls = get_binance_urls()
with open("./resources/binance_urls.txt", "w") as f:
    f.write(json.dumps(binance_urls))

# with open("./resources/binance_urls.txt") as json_file:
#     binance_urls = json.loads(json_file.read())
