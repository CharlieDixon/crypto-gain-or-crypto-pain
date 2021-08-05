from sqlalchemy import Numeric, Column, Integer, String, Boolean
from .database import Base


class Cryptocurrency(Base):
    __tablename__ = "cryptocurrencies"

    id = Column(String, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True) 
    base_asset = Column(String, unique=False, index=True)
    quote_asset = Column(String, unique=False, index=True)
    price = Column(Numeric(30, 6))
    change = Column(Numeric(10, 6))
    percentage_change = Column(Numeric(10, 2))
    gain = Column(Boolean, default=None)
    pain = Column(Boolean, default=None)


