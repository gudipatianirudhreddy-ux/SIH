import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

load_dotenv()
DATABASE_URL=os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not in your environment file")

engine=create_engine(DATABASE_URL,pool_pre_ping=True)
sessionLocal=sessionmaker(bind=engine,autocommit=False,autoflush=False)

Base=declarative_base()

def get_db():
    db=sessionLocal()
    try:
        yield db
    finally:
        db.close()
