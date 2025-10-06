import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Load the database URL from the environment variables (set in docker-compose)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./test.db") 

# If using PostgreSQL (which we are), adjust the driver name for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# The engine handles the connection to the database
engine = create_engine(
    DATABASE_URL, 
    # echo=True # Uncomment to see all SQL queries in the console
)

# Each instance of the SessionLocal class will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class which our models will inherit from
Base = declarative_base()

# Dependency function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()