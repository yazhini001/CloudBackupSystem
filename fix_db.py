import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

# Connects directly to your live Railway database using your env variables
connection = pymysql.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    autocommit=True
)

cursor = connection.cursor()

try:
    print("Adding missing columns to Railway database...")
    
    # Add file_url if missing
    try:
        cursor.execute("ALTER TABLE backups ADD COLUMN file_url VARCHAR(255);")
        print("✅ Added file_url column")
    except Exception as e:
        print(f"ℹ️ file_url: {e}")

    # Add public_id if missing
    try:
        cursor.execute("ALTER TABLE backups ADD COLUMN public_id VARCHAR(255);")
        print("✅ Added public_id column")
    except Exception as e:
        print(f"ℹ️ public_id: {e}")

    # Add is_favorite if missing
    try:
        cursor.execute("ALTER TABLE backups ADD COLUMN is_favorite INT DEFAULT 0;")
        print("✅ Added is_favorite column")
    except Exception as e:
        print(f"ℹ️ is_favorite: {e}")

    print("\n🎉 Database sync completed successfully!")

finally:
    cursor.close()
    connection.close()