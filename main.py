from fastapi import FastAPI, Path, Depends, BackgroundTasks
from sql_database import models
from sqlalchemy.orm import Session
from sql_database.database import SessionLocal, engine
from pydantic import BaseModel
from sql_database.models import Cryptocurrency

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

class CryptoRequest(BaseModel):
    symbol: str

def get_db():
    """Creates database session - necessary for all API calls that require reading/writing to database"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def fetch_crypto_data(id: int):
    db = SessionLocal
    crypto = db.query(Cryptocurrency).filter(Cryptocurrency.id == id)

@app.get("/")
def home():
    return {"Home": "Page"}

@app.post("/new_currency")
def add_new_currency_to_db(crypto_request: CryptoRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Adds a user-defined cryptocurrency to the database."""
    crypto = Cryptocurrency()
    crypto.symbol = crypto_request.symbol

    db.add(crypto)
    db.commit()

    return {f"{crypto.symbol}" : "Added"}