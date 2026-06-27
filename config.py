import pymysql

try:
    db = pymysql.connect(
        host="localhost",
        user="root",
        password="Yazhini@2006",
        database="cloud_backup"
    )
    print("Database Connected Successfully!")

except Exception as e:
    print("Error:", e)