
import sqlite3
import os

# Xây dựng đường dẫn đến tệp cơ sở dữ liệu trong thư mục data
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'rpg.db')

def init_db():
    """Khởi tạo cơ sở dữ liệu và tạo các bảng nếu chúng chưa tồn tại."""
    # Đảm bảo thư mục data tồn tại
    os.makedirs(DB_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tạo bảng người chơi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY,      -- ID người dùng Discord
        name TEXT NOT NULL,
        class TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        hp INTEGER DEFAULT 100,
        mp INTEGER DEFAULT 50,
        atk INTEGER DEFAULT 10,
        def INTEGER DEFAULT 5,
        gold INTEGER DEFAULT 0,
        weapon_equipped_id INTEGER DEFAULT NULL,
        armor_equipped_id INTEGER DEFAULT NULL
    )
    """)

    # Tạo bảng kho đồ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        item_name TEXT NOT NULL,
        item_type TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY (player_id) REFERENCES players (id)
    )
    """)

    # Cập nhật bảng inventory để thêm cột is_equipped nếu chưa có
    try:
        cursor.execute("ALTER TABLE inventory ADD COLUMN is_equipped BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        # Cột đã tồn tại, bỏ qua lỗi
        pass

    conn.commit()
    conn.close()

def get_db_connection():
    """Trả về một đối tượng kết nối cơ sở dữ liệu."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

