from database import get_connection
from datetime import datetime

def get_revenue_summary():
    """
    Hàm phụ (để tránh lỗi Import trong main.py nếu trước đó ông có gọi hàm này).
    Nếu ông chỉ dùng get_detailed_revenue_stats thì hàm này cứ để trống hoặc return tạm.
    """
    return True, {}

def get_detailed_revenue_stats():
    """
    Hàm chính xử lý tính toán doanh thu và thống kê trạng thái hội viên.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

    # ==========================================
        # PHẦN 1: THỐNG KÊ DOANH THU TIỀN BẠC
        # ==========================================
        
        # Doanh thu hôm nay
        cursor.execute("SELECT SUM(amount) FROM payments WHERE date(payment_date) = date('now', 'localtime')")
        daily = cursor.fetchone()[0] or 0

        # Doanh thu tuần này
        cursor.execute("""
            SELECT SUM(amount) FROM payments 
            WHERE strftime('%W', payment_date) = strftime('%W', 'now', 'localtime') 
              AND strftime('%Y', payment_date) = strftime('%Y', 'now', 'localtime')
        """)
        weekly = cursor.fetchone()[0] or 0

        # Doanh thu tháng này
        cursor.execute("""
            SELECT SUM(amount) FROM payments 
            WHERE strftime('%m', payment_date) = strftime('%m', 'now', 'localtime') 
              AND strftime('%Y', payment_date) = strftime('%Y', 'now', 'localtime')
        """)
        monthly = cursor.fetchone()[0] or 0

        # Tổng doanh thu từ trước đến nay (Không bị ảnh hưởng bởi ngày giờ)
        cursor.execute("SELECT SUM(amount) FROM payments")
        total_all = cursor.fetchone()[0] or 0


        # ==========================================
        # PHẦN 2: THỐNG KÊ TRẠNG THÁI HỘI VIÊN (ĐÃ FIX)
        # ==========================================
        
        # 1. Tổng số khách hàng từng đăng ký
        cursor.execute("SELECT COUNT(*) FROM members")
        total_members = cursor.fetchone()[0] or 0

        # 2. Đang hoạt động (Ngày hết hạn >= hôm nay)
        cursor.execute("SELECT COUNT(*) FROM members WHERE ngay_het_han >= date('now', 'localtime')")
        active_members = cursor.fetchone()[0] or 0

        # 3. Đã hết hạn (Ngày hết hạn < hôm nay)
        cursor.execute("SELECT COUNT(*) FROM members WHERE ngay_het_han < date('now', 'localtime')")
        expired_members = cursor.fetchone()[0] or 0

        # 4. Sắp hết hạn (Còn <= 7 ngày tính từ hôm nay)
        cursor.execute("""
            SELECT COUNT(*) FROM members 
            WHERE ngay_het_han BETWEEN date('now', 'localtime') AND date('now', '+7 days', 'localtime')
        """)
        expiring_soon = cursor.fetchone()[0] or 0
        
        # 5. Khách mới tham gia trong tháng này
        cursor.execute("""
            SELECT COUNT(*) FROM members 
            WHERE strftime('%m', ngay_dang_ky) = strftime('%m', 'now', 'localtime')
              AND strftime('%Y', ngay_dang_ky) = strftime('%Y', 'now', 'localtime')
        """)
        new_members_month = cursor.fetchone()[0] or 0

        # 6. Lượt gia hạn trong tháng này
        cursor.execute("""
            SELECT COUNT(*) FROM payments 
            WHERE strftime('%m', payment_date) = strftime('%m', 'now', 'localtime')
              AND strftime('%Y', payment_date) = strftime('%Y', 'now', 'localtime')
              AND LOWER(content) LIKE '%gia hạn%'
        """)
        renewals_month = cursor.fetchone()[0] or 0

        # ==========================================
        # PHẦN 3: THỐNG KÊ GÓI TẬP BÁN CHẠY
        # ==========================================
        cursor.execute("""
            SELECT m.goi_tap, SUM(p.amount) as total 
            FROM payments p
            JOIN members m ON p.member_id = m.id
            WHERE m.goi_tap IS NOT NULL
            GROUP BY m.goi_tap
            ORDER BY total DESC
        """)
        package_data = cursor.fetchall()
        
        package_stats = [{"goi_tap": row['goi_tap'], "total": row['total'] or 0} for row in package_data]

        # Đóng gói toàn bộ data vào 1 cuốn từ điển (dictionary)
        stats = {
            'daily': daily,
            'weekly': weekly,
            'monthly': monthly,
            'total_all': total_all,
            'total_members': total_members,
            'active_members': active_members,
            'expired_members': expired_members,
            'expiring_soon': expiring_soon,
            'new_members_month': new_members_month,
            'new_members_month': new_members_month, 
            'renewals_month': renewals_month,
            'package_stats': package_stats
        }
        
        return True, stats
        
    except Exception as e:
        print(f"Lỗi truy vấn hệ thống Dashboard: {e}")
        return False, {}
    finally:
        if conn:
            conn.close()