

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL database URI (example: "postgresql://username:password@localhost/db_name")
DATABASE_URL = os.getenv('DATABASE_URL')

# Create database engine
engine = create_engine("postgresql://postgres:postgreselectric117@localhost:5432/FAST_API_TEST")


# Session and Base for SQLAlchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_database()



# TO CREATE SQLITE DATABASE

# import os
# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # SQLite database URI (example: "sqlite:///./.db")
# DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./power.db')  # Use default SQLite URL if not set in .env

# # Create database engine (SQLite will automatically create the database file if it doesn't exist)
# engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})  # Required for SQLite

# # Session and Base for SQLAlchemy
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# # Dependency to get the database session
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # Create the tables automatically (this should be run once to initialize the database)
# def create_database():
#     Base.metadata.create_all(bind=engine)

# # Optionally, call the create_database function to initialize the database
# if __name__ == "__main__":
#     create_database()
