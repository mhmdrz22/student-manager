from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# The database URL.
# For simplicity, we'll start with SQLite.
# To use PostgreSQL, you would change this line to something like:
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

# The SQLAlchemy engine is the entry point to the database.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # The connect_args are only needed for SQLite.
    connect_args={"check_same_thread": False}
)

# Each instance of the SessionLocal class will be a new database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models.
# The models will inherit from this class to be registered with SQLAlchemy.
Base = declarative_base()

def create_db_and_tables():
    # This function will be called on application startup
    # to create the database tables.
    Base.metadata.create_all(bind=engine)
