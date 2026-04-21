import sqlite3
import pandas as pd
import os

DB_PATH = "sales_data.db"

def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.close()

def save_to_db(df, table_name="sales"):
    """Save a pandas DataFrame to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

def load_from_db(table_name="sales"):
    """Load data from the SQLite database into a pandas DataFrame."""
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    except Exception:
        df = None
    conn.close()
    return df

def get_db_schema(table_name="sales"):
    """Get the schema of the specified table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    schema = cursor.fetchall()
    conn.close()
    return schema
