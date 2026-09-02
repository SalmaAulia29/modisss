import mysql.connector


def get_connection():
  try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  
        database="db_modis_pvmbg", 
    )
    return db
  except mysql.connector.Error as err:
    print(f"[ERROR] Gagal konek ke database: {err}")
    return None