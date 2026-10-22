import sqlite3
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import hashlib
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "gym.db")
# Nạp cấu hình cạnh file database/script, kể cả khi mở EXE từ shortcut khác thư mục.
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Không dùng pepper hard-code. Với database cũ, phải giữ DB_PEPPER đã dùng để tạo index
# cho tới khi có quy trình re-index dữ liệu và thay pepper an toàn.
PEPPER = os.getenv("DB_PEPPER")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

cipher_suite = None
if ENCRYPTION_KEY:
    try:
        cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    except (TypeError, ValueError):
        print("[ERROR] ENCRYPTION_KEY khong hop le; tu choi ma hoa CCCD.")
else:
    print("[WARNING] Chua cau hinh ENCRYPTION_KEY trong .env.")

def get_connection():
    """Kết nối SQLite - Tự động tạo gym.db nếu chưa có """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)  
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous = NORMAL")  
    return conn

def init_db():
    """Tự động tạo tất cả các bảng lần đầu tiên """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ho_ten TEXT NOT NULL,
                cccd TEXT UNIQUE,
                cccd_hash TEXT UNIQUE,
                so_dien_thoai TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                goi_tap TEXT,
                gioi_tinh TEXT,
                ngay_sinh DATE,
                gia_tien REAL DEFAULT 0,
                ngay_dang_ky DATE DEFAULT CURRENT_DATE,
                ngay_het_han DATE,
                trang_thai TEXT DEFAULT 'Active',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                amount REAL NOT NULL,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_method TEXT DEFAULT 'Cash',
                content TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS body_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                chieu_cao REAL,
                can_nang REAL,
                bmi REAL,
                ngay_ghi_nhan DATE DEFAULT CURRENT_DATE,
                ghi_chu TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS check_ins (
                check_in_id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_text TEXT,
                table_affected TEXT,
                record_id INTEGER,
                action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT
            );

            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                log_type TEXT,
                sent_date DATE,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_members_cccd_hash ON members(cccd_hash);
            CREATE INDEX IF NOT EXISTS idx_members_email ON members(email);
            CREATE INDEX IF NOT EXISTS idx_payments_member ON payments(member_id);
            CREATE INDEX IF NOT EXISTS idx_metrics_member ON body_metrics(member_id);
        ''')
        conn.commit()
        print("[OK] Database initialized successfully!")
    except Exception as e:
        print(f"[ERROR] Error initializing database: {e}")
    finally:
        conn.close()

def generate_blind_index(data):
    """Tạo mã băm tìm kiếm từ CCCD đã chuẩn hóa."""
    if data is None:
        return None
    if not isinstance(data, str):
        raise TypeError("Du lieu tao chi muc CCCD phai la chuoi.")
    normalized = data.strip()
    if not normalized:
        return None
    if not PEPPER:
        raise RuntimeError("Thieu DB_PEPPER trong .env; tu choi tao chi muc CCCD.")
    combined = normalized + PEPPER
    return hashlib.sha256(combined.encode()).hexdigest()

def encrypt_cccd(plain_text):
    """Mã hóa CCCD; tuyệt đối không lưu plaintext khi thiếu khóa."""
    if plain_text is None:
        return None
    if not isinstance(plain_text, str):
        raise TypeError("CCCD phai la chuoi.")
    normalized = plain_text.strip()
    if not normalized:
        return None
    if not cipher_suite:
        raise RuntimeError("ENCRYPTION_KEY chua duoc cau hinh hop le; tu choi luu CCCD dang plaintext.")
    return cipher_suite.encrypt(normalized.encode()).decode()

def decrypt_cccd(cipher_text):
    """Giải mã CCCD với cơ chế phòng lỗi kiểu dữ liệu"""
    if not isinstance(cipher_text, str) or not cipher_suite:
        return cipher_text
    
    try:
        return cipher_suite.decrypt(cipher_text.encode()).decode()
    except Exception:
        return cipher_text

def log_system_action(action_text, table_affected=None, record_id=None):
    """Ghi nhật ký hệ thống [cite: 2026-01-28]"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO audit_logs (action_text, table_affected, record_id, action_time) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """
        cursor.execute(sql, (action_text, table_affected, record_id))
        conn.commit()
        print(f"[LOG] Da ghi nhat ky: {action_text}")
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print(f"[LOG] Khong ghi duoc log (database dang busy): {action_text}")
        else:
            print(f"[ERROR] Loi ghi log: {e}")
    except Exception as e:
        print(f"[ERROR] Loi ghi log: {e}")
    finally:
        if conn:
            conn.close()

# CREATE TABLE/INDEX IF NOT EXISTS giúp bổ sung bảng còn thiếu cho database cũ.
# Không thay đổi dữ liệu hiện có; thay đổi cột/khóa cần migration riêng.
init_db()
