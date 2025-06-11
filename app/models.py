from sqlalchemy import Column, String, BigInteger, Text, Float, Boolean, Numeric
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"

    hash = Column(String, primary_key=True, unique=True, index=True)
    status = Column(String) 
    block = Column(BigInteger, index=True)
    timestamp = Column(BigInteger) 
    transaction_action = Column(Text)
    _from = Column(String) 
    to = Column(String)
    value = Column(Numeric(38, 18))
    transaction_fee = Column(Numeric(38, 18))
    gas_price = Column(Numeric(38, 18))
    gas_used = Column(BigInteger) 
    cumulative_gas_used = Column(BigInteger) 
    input_data = Column(Text) 

    def __repr__(self):
        return (
            f"<Transaction(hash='{self.hash}', block={self.block}, "
            f"value={self.value}, status='{self.status}')>"
        )