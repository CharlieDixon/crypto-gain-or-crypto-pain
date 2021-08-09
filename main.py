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
from resources.currency_info import currency_codes, coin_list
from forex_python.converter import CurrencyRates

coin_list = coin_list()
cfg = configparser.ConfigParser()
cfg.read("binance_api_key.cfg")  # access api credentials

client = Client(cfg.get("KEYS", "api_key"), cfg.get("KEYS", "api_secret_key"))

templates = Jinja2Templates(directory="templates")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

models.Base.metadata.create_all(bind=engine)


class TradeRequest(BaseModel):
    base_asset: str
    quote_asset: str
    user_amount: float


def get_db():
    """Creates local database session - necessary for all API calls that require reading/writing to database"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_base_and_quote_assets():
    exchange_info = client.get_exchange_info()
    assets = {}
    for pair in exchange_info["symbols"]:
        assets[pair["symbol"]] = pair["baseAsset"], pair["quoteAsset"]
    return assets





def convert_to_dollars(gecko_id):
    """Uses gecko_id to get current price of a given coin (quote asset) in dollars from coingecko's public API and returns it"""
    params = {"ids": f"{gecko_id}", "vs_currencies": "usd"}
    response = httpx.get("https://api.coingecko.com/api/v3/simple/price", params=params)
    dollars = response.json()[f"{gecko_id}"]["usd"]
    return dollars


def get_all_coins():
    """At initiation of API fetches information on all trading pairs and adds to database."""
    db = SessionLocal()
    pair_tickers = client.get_ticker()
    assets = get_base_and_quote_assets()

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
            crypto.price = float(pair["weightedAvgPrice"])
            crypto.change = float(pair["priceChange"])
            crypto.percentage_change = float(pair["priceChangePercent"])
            crypto.gain = True if crypto.percentage_change > 5 else False
            crypto.pain = True if crypto.percentage_change < -5 else False
            db.add(crypto)
    db.commit()


get_all_coins()


def fetch_crypto_data(id: int, user_amount: float, symbol: str):
    """Connects to local database and returns data from binance API for the currency pair the user has inputted before committing to database."""
    conn = engine.connect()
    # implicitly joins on foreign key defined in models.py
    selection = (
        select(Cryptocurrency, Trades.user_amount)
        .filter(Cryptocurrency.symbol == symbol)
        .join(Trades)
    )
    result = conn.execute(selection)
    row = result.fetchone()
    conn.close()

    db = SessionLocal()

    trade = db.query(Trades).filter(Trades.id == id).first()

    percentage_change_for_selected_pair = float(row._mapping["percentage_change"])
    before_trade = float(user_amount)
    after_trade = before_trade + (float(row._mapping["percentage_change"])/100 * before_trade)
    gecko_coin_list = coin_list
    if row._mapping["quote_asset"].upper() in currency_codes:
        exchange = CurrencyRates()
        value_of_coin_in_dollars = exchange.get_rate(
            row._mapping["quote_asset"].upper(), "USD"
        )
    else:
        gecko_id, symb, name = [
            coin
            for coin in gecko_coin_list
            if coin["symbol"] == row._mapping["quote_asset"].lower()
        ][0].values()
        value_of_coin_in_dollars = convert_to_dollars(gecko_id)
    before_trade_in_dollars = before_trade * value_of_coin_in_dollars
    after_trade_in_dollars = after_trade * value_of_coin_in_dollars
    gain_or_pain_in_dollars = after_trade_in_dollars - before_trade_in_dollars
    trade.gain_or_pain_in_dollars = gain_or_pain_in_dollars

    db.add(trade)
    db.commit()


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
        },
    )


@app.post("/gain_or_pain")
async def user_gain_or_pain(
    trade_request: TradeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Adds a user-defined cryptocurrency to "trades" database and runs background task to find relevant info on success of trade."""
    trade = Trades()
    trade.base_asset = trade_request.base_asset
    trade.quote_asset = trade_request.quote_asset
    symbol = trade_request.base_asset + trade_request.quote_asset
    trade.symbol = symbol
    trade.user_amount = trade_request.user_amount
    db.add(trade)
    db.commit()

    background_tasks.add_task(
        fetch_crypto_data, trade.id, trade.user_amount, trade.symbol
    )

    return {f"{trade.symbol}": "Added"}
