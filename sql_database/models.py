from sqlalchemy import Numeric, Integer, Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Cryptocurrency(Base):
    __tablename__ = "cryptocurrencies"

    id = Column(String, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    base_asset = Column(String, unique=False, index=True)
    quote_asset = Column(String, unique=False, index=True)
    price = Column(String, unique=False)
    change = Column(String, unique=False)
    percentage_change = Column(String, unique=False)
    gain = Column(Boolean, default=None)
    pain = Column(Boolean, default=None)
    trades = relationship("Trades", backref="cryptocurrencies")


class Trades(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    base_asset = Column(String, index=True)
    quote_asset = Column(String, index=True)
    symbol = Column(String, ForeignKey("cryptocurrencies.symbol"))
    user_amount = Column(String, unique=False)
    percentage_change_for_selected_pair = Column(String, unique=False)
    before_trade_in_dollars = Column(String, unique=False)
    gain_or_pain_in_dollars = Column(String, unique=False)
