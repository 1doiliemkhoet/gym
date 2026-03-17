import pandas as pd
from database import get_connection, log_system_action
from datetime import datetime, timedelta

def get_detailed_revenue_stats():
    """Lấy báo cáo doanh thu chi tiết [cite: 2026-03-04]"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total FROM payments 
            WHERE DATE(payment_date) = DATE('now')
        """)
        daily = cursor.fetchone()[0] or 0
        
        # 2. Doanh thu tuần này (7 ngày gần nhất)
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total FROM payments 
            WHERE payment_date >= date('now', '-7 days')
        """)
        weekly = cursor.fetchone()[0] or 0
        
        # 3. Doanh thu tháng này
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total FROM payments 
            WHERE strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')
        """)
        monthly = cursor.fetchone()[0] or 0
        
        # 4. Tổng doanh thu toàn bộ
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM payments")
        total_all = cursor.fetchone()[0] or 0
        
        # 5. Hội viên đang hoạt động
        cursor.execute("SELECT COUNT(*) as count FROM members WHERE trang_thai = 'Active'")
        active_members = cursor.fetchone()[0] or 0
        
        # 6. Hội viên mới trong tháng này
        cursor.execute("""
            SELECT COUNT(*) as count FROM members 
            WHERE strftime('%Y-%m', ngay_dang_ky) = strftime('%Y-%m', 'now')
        """)
        new_members_month = cursor.fetchone()[0] or 0
        
        # 7. Hội viên hết hạn trong 7 ngày tới
        cursor.execute("""
            SELECT COUNT(*) as count FROM members 
            WHERE ngay_het_han BETWEEN DATE('now') AND DATE('now', '+7 days')
            AND trang_thai = 'Active'
        """)
        expiring_soon = cursor.fetchone()[0] or 0
        
        # 8. Doanh thu theo gói tập
        cursor.execute("""
            SELECT m.goi_tap, COALESCE(SUM(p.amount), 0) as total, COUNT(DISTINCT p.member_id) as count
            FROM payments p
            JOIN members m ON p.member_id = m.id
            GROUP BY m.goi_tap
            ORDER BY total DESC
        """)
        package_stats = cursor.fetchall()
        
        log_system_action("Xem bao cao chi tiet doanh thu", "payments/members", None)
        
        return True, {
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly,
            "total_all": total_all,
            "active_members": active_members,
            "new_members_month": new_members_month,
            "expiring_soon": expiring_soon,
            "package_stats": package_stats
        }
    except Exception as e:
        print(f"Lỗi lấy báo cáo chi tiết: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

def get_revenue_by_package():
    """Thống kê doanh thu theo từng loại gói tập bằng cách kết hợp hai bảng [cite: 2026-01-28]"""
    try:
        conn = get_connection()
        # Sử dụng JOIN để biết khoản thanh toán đó thuộc về gói tập nào của hội viên [cite: 2026-01-28]
        query = """
            SELECT m.goi_tap, COALESCE(SUM(p.amount), 0) as total 
            FROM payments p
            JOIN members m ON p.member_id = m.id
            GROUP BY m.goi_tap
        """
        df = pd.read_sql(query, conn)
        
        log_system_action("Truy cap bao cao doanh thu theo goi tap", "payments/members", None)
        return df
    except Exception as e:
        print(f"Lỗi thống kê: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals():
            conn.close()

def get_revenue_summary():
    """Lấy số liệu doanh thu và đếm hội viên đang hoạt động [cite: 2026-01-28]"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Tính doanh thu tháng này [cite: 2026-01-28]
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total FROM payments 
            WHERE strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')
        """)
        monthly_data = cursor.fetchone()
        monthly = float(monthly_data[0]) if monthly_data[0] else 0.0

        # 2. ĐẾM TỔNG HỘI VIÊN ACTIVE (Đây là phần bị thiếu gây lỗi KeyError) [cite: 2026-01-28]
        cursor.execute("SELECT COUNT(*) as active_count FROM members WHERE trang_thai = 'Active'")
        active_data = cursor.fetchone()
        active_members = active_data[0] if active_data else 0

        # Trả về dictionary với đầy đủ các key mà main.py cần [cite: 2026-01-28]
        return True, {
            "monthly": monthly,
            "active_members": active_members, # Key quan trọng nhất để fix lỗi [cite: 2026-01-28]
            "growth": 0 # Tạm để 0 nếu bạn chưa cần tính tăng trưởng phức tạp [cite: 2026-02-20]
        }
    except Exception as e:
        return False, str(e)
    finally:
        if conn:
            conn.close()