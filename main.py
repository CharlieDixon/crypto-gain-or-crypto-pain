from fastapi import FastAPI, Path, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from sql_database import models
from sqlalchemy.orm import Session
from sql_database.database import SessionLocal, engine
from pydantic import BaseModel
from sql_database.models import Cryptocurrency
import configparser
from binance import Client
import uuid

cfg = configparser.ConfigParser()
cfg.read("binance_api_key.cfg")  # access api credentials

client = Client(cfg.get("KEYS", "api_key"), cfg.get("KEYS", "api_secret_key"))

templates = Jinja2Templates(directory="templates")

app = FastAPI()

models.Base.metadata.create_all(bind=engine)


class CryptoRequest(BaseModel):
    symbol: str

def get_db():
    """Creates local database session - necessary for all API calls that require reading/writing to database"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_list_of_pairs():
    pairs = client.get_all_tickers()
    return [pair['symbol'] for pair in pairs]
    

def get_all_coins():
    """At initiation of API fetches information on all trading pairs and adds to database."""
    db = SessionLocal()
    pair_tickers = client.get_ticker()
    for pair in pair_tickers:
        exists = db.query(Cryptocurrency).filter(Cryptocurrency.symbol == pair["symbol"]).first()
        if not exists:
            crypto = Cryptocurrency()
            crypto.id = uuid.uuid4()
            crypto.symbol = pair["symbol"]
            crypto.price = float(pair["weightedAvgPrice"])
            print(crypto.price)
            print(type(crypto.price))
            crypto.change = str(pair["priceChange"])
            crypto.percentage_change = str(pair["priceChangePercent"])
            crypto.gain = True if float(crypto.percentage_change) > 5 else False
            crypto.pain = True if float(crypto.percentage_change) < -5 else False
            db.add(crypto)
    db.commit()

get_all_coins()


def fetch_crypto_data(id: int):
    """Connects to local database and returns data from binance API for the currency pair the user has inputted before committing to database."""
    db = SessionLocal()
    crypto = db.query(Cryptocurrency).filter(Cryptocurrency.id == id).first()

    binance_info = client.get_ticker(symbol=crypto.symbol)
    crypto.price = str(binance_info["weightedAvgPrice"])
    crypto.change = str(binance_info["priceChange"])
    crypto.percentage_change = str(binance_info["priceChangePercent"])
    crypto.gain = True if float(crypto.percentage_change) > 5 else False
    crypto.pain = True if float(crypto.percentage_change) < -5 else False

    db.add(crypto)
    db.commit()


@app.get("/")
def home(request: Request, search=None, gain=None, pain=None, db: Session = Depends(get_db)):
    cryptos = db.query(Cryptocurrency)

    if search:
        cryptos = cryptos.filter(Cryptocurrency.symbol == search)
    
    return templates.TemplateResponse("homepage.html", {"request": request, "cryptos": cryptos})


@app.post("/new_currency")
async def add_new_currency_to_db(
    crypto_request: CryptoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Adds a user-defined cryptocurrency to the database."""
    crypto = Cryptocurrency()
    crypto.symbol = crypto_request.symbol

    db.add(crypto)
    db.commit()

    background_tasks.add_task(fetch_crypto_data, crypto.id)

    return {f"{crypto.symbol}": "Added"}

