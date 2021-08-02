from sqlalchemy import Numeric, Column, Integer, String, Boolean
from .database import Base


class Cryptocurrency(Base):
    __tablename__ = "cryptocurrencies"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    price = Column(Numeric(10, 2))
    change = Column(Numeric(10, 2))
    percentage_change = Column(Numeric(10, 2))
    gain = Column(Boolean, default=None)
    pain = Column(Boolean, default=None)


