from fastapi import FastAPI, Path, Depends
from sql_database import models
from sqlalchemy.orm import Session
from sql_database.database import SessionLocal, engine
from pydantic import BaseModel

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

class CryptoRequest(BaseModel):
    symbol: str

@app.get("/")
def home():
    return {"Home": "Page"}
