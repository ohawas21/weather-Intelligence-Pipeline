import os
import sqlite3
import pyodbc
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def get_azure_sql_connection():
    """Connect to Azure SQL Database."""
    server   = os.environ.get("AZURE_SQL_SERVER")
    database = os.environ.get("AZURE_SQL_DATABASE")
    username = os.environ.get("AZURE_SQL_USERNAME")
    password = os.environ.get("AZURE_SQL_PASSWORD")

    connection_string = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
    )
    return pyodbc.connect(connection_string)


def create_table_if_not_exists(conn):
    """Create the hourly_weather table in Azure SQL if it does not exist."""
    cursor = conn.cursor()
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sysobjects
            WHERE name='hourly_weather' AND xtype='U'
        )
        CREATE TABLE hourly_weather (
            id            INT IDENTITY(1,1) PRIMARY KEY,
            city          NVARCHAR(50),
            date          DATE,
            hour          INT,
            temperature   FLOAT,
            windspeed     FLOAT,
            precipitation FLOAT,
            loaded_at     DATETIME DEFAULT GETDATE()
        )
    """)
    conn.commit()
    print("  ✓ Table ready in Azure SQL")


def load_to_azure_sql():
    """Read from SQLite and load into Azure SQL Database."""
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Read from SQLite
    sqlite_conn = sqlite3.connect("weather.db")
    rows = sqlite_conn.execute("""
        SELECT city, date, hour, temperature, windspeed, precipitation
        FROM hourly_weather
        WHERE date = ?
    """, (today,)).fetchall()
    sqlite_conn.close()

    if not rows:
        print("  No data found in SQLite for today")
        return

    print(f"  Read {len(rows)} rows from SQLite")

    # 2. Connect to Azure SQL — fail gracefully if blocked
    try:
        conn = get_azure_sql_connection()
    except Exception as e:
        print(f"  ⚠ Could not connect to Azure SQL: {e}")
        print("  Skipping Azure SQL load — pipeline continues")
        return

    create_table_if_not_exists(conn)

    # 3. Delete today's rows first (safe to re-run)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM hourly_weather WHERE date = ?",
        (today,)
    )
    conn.commit()

    # 4. Insert all rows using cursor
    cursor.executemany("""
        INSERT INTO hourly_weather
            (city, date, hour, temperature, windspeed, precipitation)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()

    print(f"  ✓ Loaded {len(rows)} rows into Azure SQL")


if __name__ == "__main__":
    print("Loading data into Azure SQL...")
    load_to_azure_sql()
    print("Done.")