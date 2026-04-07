from database import get_connection
from database import decrypt_cccd

def get_checkin_suggestions(query):
    """Tìm hội viên bằng tên và hiển thị SĐT đầy đủ"""
    if not query or len(query) < 1:
        return []
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        sql = "SELECT ho_ten, so_dien_thoai, cccd FROM members WHERE ho_ten LIKE ? LIMIT 10"
        cursor.execute(sql, (f"%{query}%",))
        results = cursor.fetchall()
        
        suggestions = []
        for row in results:
            name = row['ho_ten']
            phone = row['so_dien_thoai']
            real_cccd = decrypt_cccd(row['cccd'])
            
            suggestions.append({
                "display": f"{name} - SĐT: {phone}",
                "real_value": real_cccd
            })
        return suggestions
    except Exception as e:
        print(f"Lỗi gợi ý: {e}")
        return []
    finally:
        if conn: conn.close()