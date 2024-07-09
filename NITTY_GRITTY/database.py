import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env file
load_dotenv()

# Get database credentials from environment variables
DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_PORT = os.getenv('DATABASE_PORT')
DATABASE_NAME = os.getenv('DATABASE_NAME')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')

# Connect to PostgreSQL database
try:
    connection = psycopg2.connect(
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        dbname=DATABASE_NAME,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD
    )
    cursor = connection.cursor()
    print("Connected to the database successfully")
    
    # Execute a test query
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print(f"PostgreSQL Database Version: {db_version}")

    # Close the cursor and connection
    cursor.close()
    connection.close()
except Exception as e:
    print(f"Error connecting to the database: {e}")
