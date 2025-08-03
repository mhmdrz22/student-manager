from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# The database URL for PostgreSQL.
# IMPORTANT: Replace the placeholder values with your actual database credentials.
# Format: "postgresql://<user>:<password>@<host>/<dbname>"
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/scientific_db"

# The SQLAlchemy engine is the entry point to the database.
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Each instance of the SessionLocal class will be a new database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models.
# The models will inherit from this class to be registered with SQLAlchemy.
Base = declarative_base()

def create_db_and_tables():
    # This function will be called on application startup
    # to create the database tables.
    Base.metadata.create_all(bind=engine)

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
