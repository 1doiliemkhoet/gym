from database import get_connection
from database import decrypt_cccd

def get_checkin_suggestions(query):
    """Tìm hội viên và hiển thị kèm SĐT để phân biệt trùng tên [cite: 2026-03-04]"""
    if not query or len(query) < 1:
        return []
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Lấy ho_ten để hiện, so_dien_thoai để phân biệt, cccd để làm giá trị check-in [cite: 2026-03-05]
        sql = "SELECT ho_ten, so_dien_thoai, cccd FROM members WHERE ho_ten LIKE ? LIMIT 5"
        cursor.execute(sql, (f"%{query}%",))
        results = cursor.fetchall()
        suggestions = []
        for row in results:
            name = row['ho_ten']
            phone = row['so_dien_thoai']
            # Chỉ hiện 4 số cuối SĐT để phân biệt
            masked_phone = f"****{phone[-4:]}" if phone and len(phone) >= 4 else "N/A"
            real_cccd = decrypt_cccd(row['cccd'])
            suggestions.append({
                "display": f"{name} ({masked_phone})",
                "real_value": real_cccd
            })
        return suggestions
    except Exception as e:
        print(f"Lỗi gợi ý: {e}")
        return []
    finally:
        if conn: conn.close()