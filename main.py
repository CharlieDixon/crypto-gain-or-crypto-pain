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
from resources.currency_info import currency_codes, svg_icon_codes
from forex_python.converter import CurrencyRates
from starlette.responses import FileResponse
from collections import defaultdict

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
        if not exists:
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
    except JSONDecodeError as exc:
        print(exc)
        print(exc.msg)


@app.get("/base-and-quote-assets")
async def get_assets():
    return assets, set_of_base_coins


def convert_to_dollars(gecko_id):
    """Uses gecko_id to get current price of a given coin (quote asset) in dollars from coingecko's public API and returns it"""
    params = {"ids": f"{gecko_id}", "vs_currencies": "usd"}
    try:
        response = httpx.get(
            "https://api.coingecko.com/api/v3/simple/price", params=params, timeout=None
        )
    except JSONDecodeError as exc:
        print(exc)
        print(exc.message)

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
