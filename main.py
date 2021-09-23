from json.decoder import JSONDecodeError
from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.util.langhelpers import _symbol
from starlette.requests import Request
from sql_database import models
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.sql import select
from sql_database.database import SessionLocal, engine
from pydantic import BaseModel
from sql_database.models import Cryptocurrency, Trades
import configparser
from binance import Client
import uuid
import httpx
from resources.currency_info import (
    currency_codes,
    svg_icon_codes,
    alt_colours_for_graphs,
)
from forex_python.converter import CurrencyRates
from starlette.responses import FileResponse
from collections import defaultdict
from loguru import logger
import sys
import json
import backoff
import difflib
import random
from utils.data_cleaning import remove_html_tags, create_description_for_search_results, determine_colour

logger.remove()
logger.add(
    sys.stderr,
    colorize=True,
    format="<c>{time:HH:MM:SS}</c> | {level} | <level><blue>{message}</blue></level>",
    level="DEBUG",
)

cfg = configparser.ConfigParser()

cfg.read("binance_api_key.cfg")  # access api credentials

client = Client(cfg.get("KEYS", "api_key"), cfg.get("KEYS", "api_secret_key"))

templates = Jinja2Templates(directory="templates")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


models.Base.metadata.create_all(bind=engine)

assets = {}
set_of_base_coins = set()
gecko_coin_list = []


class TradeRequest(BaseModel):
    base_asset: str
    quote_asset: str
    user_amount: float


class DropdownRequest(BaseModel):
    coin: str


def get_db():
    """Creates local database session - necessary for all API calls that require reading/writing to database"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def get_base_and_quote_assets():
    """Returns a dictionary of assets from binance API and a set containing the base assets"""
    exchange_info = client.get_exchange_info()
    for pair in exchange_info["symbols"]:
        if pair["status"] == "TRADING":
            assets[pair["symbol"]] = pair["baseAsset"], pair["quoteAsset"]
            set_of_base_coins.add(pair["baseAsset"])


@app.on_event("startup")
async def get_all_coins():
    """At initiation of API fetches information on all binance trading pairs and adds to database."""
    db = SessionLocal()
    pair_tickers = client.get_ticker()
    assets, set_of_base_coins = await get_assets()

    for pair in pair_tickers:
        exists = (
            db.query(Cryptocurrency)
            .filter(Cryptocurrency.symbol == pair["symbol"])
            .first()
        )
        # check that pair exists as live trading pair
        if not exists and assets.get(pair["symbol"]):
            crypto = Cryptocurrency()
            crypto.id = str(uuid.uuid4())
            crypto.symbol = pair["symbol"]
            crypto.base_asset = assets.get(pair["symbol"])[0]
            crypto.quote_asset = assets.get(pair["symbol"])[1]
            crypto.price = pair["weightedAvgPrice"]
            crypto.change = pair["priceChange"]
            crypto.percentage_change = pair["priceChangePercent"]
            crypto.gain = True if float(pair["priceChangePercent"]) > 5 else False
            crypto.pain = True if float(pair["priceChangePercent"]) < -5 else False
            db.add(crypto)
    db.commit()


@app.on_event("startup")
@backoff.on_predicate(backoff.constant, interval=5, max_tries=8)
def get_gecko_coin_list():
    global gecko_coin_list
    try:
        res = httpx.get("https://api.coingecko.com/api/v3/coins/list", timeout=10)
    except httpx.RequestError as exc:
        print(f"An error occurred while requesting {exc.request.url!r}.")
    except httpx.HTTPStatusError as exc:
        print(
            f"Error response {exc.response.status_code} while requesting {exc.request.url!r}."
        )
    try:
        gecko_coin_list = res.json()
        logger.info(gecko_coin_list[0])
    except JSONDecodeError:
        logger.opt(exception=True).error("Exception logged with error level:")
        logger.info("Couldn't get gecko coin list")
    return gecko_coin_list


def get_first_sentence_from_string(sentence):
    if isinstance(sentence, str):
        index = sentence.find(".")
        if index != -1:
            index += 1  # add 1 to include the fullstop itself.
            return sentence[:index]
    else:
        return None


@app.get("/base-and-quote-assets")
async def get_assets():
    return assets, set_of_base_coins


@logger.catch
def convert_to_dollars(gecko_id):
    """Uses gecko_id to get current price of a given coin (quote asset) in dollars from coingecko's public API and returns it"""
    params = {"ids": f"{gecko_id}", "vs_currencies": "usd"}
    try:
        response = httpx.get(
            "https://api.coingecko.com/api/v3/simple/price", params=params, timeout=None
        )
    except JSONDecodeError as exc:
        logger.info(exc)

    dollars = response.json()[f"{gecko_id}"]["usd"]
    return dollars


def select_trade_row(symbol: str):
    with SessionLocal() as session:
        row = (
            session.query(Cryptocurrency, Trades.user_amount)
            .where(Cryptocurrency.symbol == symbol)
            .join(Trades)
            .first()
        )
    return row


def fetch_crypto_data(id: int, user_amount: float, symbol: str):
    """Connects to local database and returns data from binance API for the currency pair the user has inputted before committing to database."""
    row = select_trade_row(symbol)
    percentage_change_for_pair = float(row._mapping[Cryptocurrency].percentage_change)
    before_trade = float(user_amount)
    if percentage_change_for_pair == 0:
        after_trade = before_trade
    else:
        after_trade = before_trade + (percentage_change_for_pair / 100 * before_trade)
    global gecko_coin_list
    if row._mapping[Cryptocurrency].quote_asset.upper() in currency_codes:
        exchange = CurrencyRates()
        value_of_coin_in_dollars = exchange.get_rate(
            row._mapping[Cryptocurrency].quote_asset.upper(), "USD"
        )
    else:
        gecko_id, symb, name = [
            coin
            for coin in gecko_coin_list
            if coin["symbol"] == row._mapping[Cryptocurrency].quote_asset.lower()
        ][0].values()
        value_of_coin_in_dollars = convert_to_dollars(gecko_id)

    before_trade_in_dollars = before_trade * value_of_coin_in_dollars
    after_trade_in_dollars = after_trade * value_of_coin_in_dollars
    gain_or_pain_in_dollars = after_trade_in_dollars - before_trade_in_dollars
    with SessionLocal() as session:
        trade = session.query(Trades).filter(Trades.id == id).first()
        trade.before_trade_in_dollars = str(before_trade_in_dollars)
        trade.gain_or_pain_in_dollars = str(gain_or_pain_in_dollars)
        trade.percentage_change_for_selected_pair = str(percentage_change_for_pair)
        session.add(trade)
        session.commit()


@app.get("/favicon.ico")
async def get_favicon():
    return FileResponse("static/favicon.ico")


@app.get("/coin-market-cap")
async def get_coin_market_cap(symbol):
    # ! Split into several functions
    # todo Docstring
    # workaround to account for mismatches between gecko and binance api symbols
    binance_gecko_mismatch = {
        "agi": "agix",
        "arn": "arnv",
        "strat": "stratx",
        "bchabc": "bcha",
        "iota": "miota",
        "yoyo": "yoyow",
    }
    coin_gecko_names = [
        value[1]
        for elem in gecko_coin_list
        for value in elem.items()
        if value[0] == "symbol"
    ]
    symbol = symbol.lower().rstrip('"')
    if symbol not in coin_gecko_names:
        if symbol in binance_gecko_mismatch:
            symbol = binance_gecko_mismatch.get(symbol)
        else:
            pass
    logger.debug(symbol)

    matches = [
        {"id": coin["id"], "symbol": coin["symbol"], "name": coin["name"]}
        for coin in gecko_coin_list
        if symbol in coin["symbol"]
    ]
    match_symbols = [match.get("symbol") for match in matches]
    closest = difflib.get_close_matches(symbol, match_symbols, n=8)

    items = []
    with httpx.Client() as client:
        for match in matches:
            if match.get("symbol") in closest:
                gecko_id = match.get("id")
                gecko_name = match.get("name")
                gecko_symbol = match.get("symbol")
                params = {
                    "id": f"{gecko_id}",
                    "localization": "false",
                    "developer_data": "false",
                    "community_data": "false",
                }
                try:
                    response = client.get(
                        f"https://api.coingecko.com/api/v3/coins/{gecko_id}",
                        params=params,
                        timeout=None,
                    )
                except:
                    logger.error("Exception occurred while fetching request")
                res = response.json()
                homepage = res["links"]["homepage"][0]
                logger.debug(res["name"])
                logger.debug(homepage)
                price_change_percentage_1y = res["market_data"][
                    "price_change_percentage_1y"
                ]
                # rounds up to two decimal places before converting back to string
                price_change_percentage_1y = str(
                    round(float(price_change_percentage_1y), 2)
                )
                market_cap_rank = (
                    str(res["market_cap_rank"])
                    if res["market_cap_rank"] != None
                    else None
                )
                coingecko_rank = (
                    str(res["coingecko_rank"])
                    if res["coingecko_rank"] != None
                    else None
                )
                price_change_percentage_1y = (
                    price_change_percentage_1y
                    if price_change_percentage_1y != "0.0"
                    else None
                )
                categories = ", ".join(res["categories"])
                coin_description = res["description"]["en"]
                coin_description = remove_html_tags(coin_description)
                coin_description = get_first_sentence_from_string(coin_description)

                logger.debug(f"categories: {categories}")
                logger.debug(f"market_cap_rank: {market_cap_rank}")
                logger.debug(
                    f"price_change_percentage_1y: {price_change_percentage_1y}"
                )
                market_cap_description = (
                    f"<b>Market cap rank:</b> {market_cap_rank}"
                    if market_cap_rank
                    else ""
                )
                coin_gecko_rank_description = (
                    (f"<b>Coingecko rank:</b> {coingecko_rank}")
                    if coingecko_rank
                    else ""
                )
                price_change_description = (
                    (f"<b>1 year price change:</b> {price_change_percentage_1y}%")
                    if price_change_percentage_1y is not None
                    else ""
                )
                categories_description = (
                    (f"<b>Categories:</b> {categories}") if len(categories) != 0 else ""
                )
                coin_description = (
                    (f"<i>{coin_description}</i>") if coin_description else ""
                )
                list_of_descriptions = [
                    coin_description,
                    market_cap_description,
                    coin_gecko_rank_description,
                    price_change_description,
                    categories_description,
                ]
                description = create_description_for_search_results(
                    list_of_descriptions
                )
                logger.debug(description)
                items.append(
                    {
                        "name": gecko_name,
                        "symbol": gecko_symbol.upper(),
                        "html_url": homepage,
                        "description": description,
                    }
                )
    return {"items": items}


@app.get("/")
def home(
    request: Request, search=None, gain=None, pain=None, db: Session = Depends(get_db)
):
    cryptos = db.query(Cryptocurrency)

    if search:
        cryptos = cryptos.filter(Cryptocurrency.symbol.ilike(f"%{search}%"))

    if gain and pain:
        cryptos = cryptos.filter(
            or_(Cryptocurrency.gain == 1, Cryptocurrency.pain == 1)
        )

    elif gain:
        cryptos = cryptos.filter(Cryptocurrency.gain == 1)

    elif pain:
        cryptos = cryptos.filter(Cryptocurrency.pain == 1)

    with open("./resources/binance_urls.json") as json_urls:
        binance_urls = json.load(json_urls)

    return templates.TemplateResponse(
        "homepage.html",
        {
            "request": request,
            "cryptos": cryptos,
            "search": search,
            "gain": gain,
            "pain": pain,
            "set_of_base_coins": sorted(set_of_base_coins),
            "svg_icons": svg_icon_codes,
            "binance_urls": binance_urls,
        },
    )


@app.post("/gain-or-pain")
def user_gain_or_pain(
    trade_request: TradeRequest,
):
    """Adds a user-defined cryptocurrency to "trades" database and runs background task to find relevant info on success of trade."""
    trade = Trades()
    trade.base_asset = trade_request.base_asset
    trade.quote_asset = trade_request.quote_asset
    symbol = trade_request.base_asset + trade_request.quote_asset
    trade.symbol = symbol
    trade.user_amount = str(trade_request.user_amount)
    with SessionLocal() as session:
        session.add(trade)
        session.commit()

    fetch_crypto_data(trade.id, trade.user_amount, trade.symbol)


@app.get("/trade-db")
def trade_db():
    # gets last db entry i.e. last trade submitted: change to use IDs
    with SessionLocal() as session:
        last_trade = session.query(Trades).order_by(Trades.id.desc()).first()
        logger.debug(last_trade.before_trade_in_dollars)
        logger.debug(last_trade.gain_or_pain_in_dollars)
    total_user_dollars = float(last_trade.before_trade_in_dollars) + float(
        last_trade.gain_or_pain_in_dollars
    )
    before_dollars = float(last_trade.before_trade_in_dollars)
    return {
        "total_user_dollars": total_user_dollars,
        "before_dollars": before_dollars,
        "gain_or_pain_in_dollars": last_trade.gain_or_pain_in_dollars,
        "percentage_change": last_trade.percentage_change_for_selected_pair,
    }


@app.get("/limit-dropdown")
def limit_dropdown(
    c2b=None,
):
    coin_dict = defaultdict(list)
    for base, quote in assets.values():
        coin_dict[base].append(quote)
    if c2b:
        return coin_dict.get(c2b)


@app.get("/results")
def overlay_svgs(request: Request, db: Session = Depends(get_db)):

    return templates.TemplateResponse(
        "image-overlay.html",
        {
            "request": request,
            "svg_base": "btc",
            "svg_quote": "doge",
        },
    )
    # pseudocode
    # get last trade
    # assign base and quote assets of that trade
    # fetch relevant svgs
    # return via jinja template
    # separate page for worst_trade?


@app.get("/analysis")
def analysis(request: Request, db: Session = Depends(get_db)):
    profit_on_coin = {}
    trades = db.query(Trades.base_asset, Trades.gain_or_pain_in_dollars)
    # add up values where base asset is the same
    for coin, profit in trades:
        if coin in profit_on_coin:
            profit_on_coin[coin] += float(profit)
        else:
            profit_on_coin[coin] = float(profit)
    ordered_by_profit = {
        k: v
        for k, v in sorted(
            profit_on_coin.items(), key=lambda item: item[1], reverse=True
        )
    }
    profit_coins = {k: v for k, v in ordered_by_profit.items() if v >= 0}
    loss_coins = {k: v for k, v in ordered_by_profit.items() if v < 0}

    profitable_coins_ordered = [coin for coin in profit_coins.keys()]
    profits_ordered = [round(value, 2) for value in profit_coins.values()]
    loss_coins_ordered = [coin for coin in loss_coins.keys()]
    losses_ordered = [round(value, 2) for value in loss_coins.values()]

    total_gained = "$" + str(round(sum(profits_ordered),2))
    total_lost = str(round(sum(losses_ordered),2)).replace("-", "$")
    total = "$" + str(round(sum(profits_ordered + losses_ordered)))
    highest_earner_coin, highest_earner_amount = profitable_coins_ordered[0], "$" + str(profits_ordered[0])
    biggest_burner_coin, biggest_burner_amount = loss_coins_ordered[-1], str(losses_ordered[-1]).replace("-","$")
    
    with open("./resources/crypto-colours.json") as colours:
        colour_dict = json.load(colours)

    profitable_colour_order = determine_colour(profitable_coins_ordered, colour_dict, alt_colours_for_graphs)
    loss_colour_order = determine_colour(loss_coins_ordered, colour_dict, alt_colours_for_graphs)

    return templates.TemplateResponse(
        "analysis.html",
        {
            "request": request,
            "profitable_coins": json.dumps(profitable_coins_ordered),
            "profits_ordered": json.dumps(profits_ordered),
            "profitable_colour_order": json.dumps(profitable_colour_order),
            "loss_coins": json.dumps(loss_coins_ordered),
            "losses_ordered": json.dumps(losses_ordered),
            "loss_colour_order": json.dumps(loss_colour_order),
            "total_gained": total_gained,
            "total_lost": total_lost,
            "total": total,
            "highest_earner_coin": highest_earner_coin,
            "highest_earner_amount": highest_earner_amount,
            "biggest_burner_coin": biggest_burner_coin,
            "biggest_burner_amount": biggest_burner_amount,

        },
    )
