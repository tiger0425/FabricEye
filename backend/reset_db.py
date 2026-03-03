import sqlite3
import os

db_path = "E:/myProject/FabricEye/backend/fabriceye.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE rolls SET status = 'PENDING' WHERE id = 1;")
    conn.commit()
    print("Reset roll 1 to PENDING (uppercase)")
    conn.close()
else:
    print("DB not found")
