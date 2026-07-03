from database import get_connection, generate_blind_index, log_system_action
from datetime import datetime

def check_in_by_cccd_logic(cccd_input):
    conn = None
    try:
        cccd_clean = cccd_input.strip()
        if not cccd_clean: return False, "Vui lòng nhập thông tin!"
        
        search_hash = generate_blind_index(cccd_clean)
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, ho_ten, ngay_het_han, trang_thai FROM members WHERE cccd_hash = ?", (search_hash,))
        member = cursor.fetchone()
        
        if not member: return False, "Hội viên không tồn tại!"
        if member['trang_thai'] != 'Active': return False, f"Tài khoản đang bị {member['trang_thai']}!"


        today = datetime.now().date()
        expiry = datetime.strptime(member['ngay_het_han'], '%Y-%m-%d').date() if isinstance(member['ngay_het_han'], str) else member['ngay_het_han']
        if expiry < today: return False, "Gói tập đã hết hạn!"

        cursor.execute("INSERT INTO check_ins (member_id) VALUES (?)", (member['id'],))
        cursor.execute("INSERT INTO audit_logs (action_text, record_id) VALUES (?, ?)", 
                       (f"Check-in: {member['ho_ten']}", member['id']))
        
        conn.commit()
        return True, f"Chào mừng {member['ho_ten']}!"
    except Exception as e:
        return False, str(e)
    finally:
        if conn: conn.close()

def get_today_checkin_history():
    """Truy vấn từ bảng check_ins  """
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT m.ho_ten, m.so_dien_thoai, strftime('%H:%M:%S', c.check_in_time, 'localtime') as t
        FROM check_ins c
        JOIN members m ON c.member_id = m.id
        WHERE DATE(c.check_in_time, 'localtime') = DATE('now', 'localtime')
        ORDER BY c.check_in_time DESC LIMIT 20
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    return [{"name": f"{r['ho_ten']} (****{r['so_dien_thoai'][-4:]})", "time": r['t']} for r in rows]

def get_today_checkin_history():
    """Truy vấn lịch sử check-in hôm nay kèm số ngày còn hạn"""
    from database import get_connection
    from datetime import datetime

    conn = get_connection()
    cursor = conn.cursor()
    # Bổ sung lấy m.ngay_het_han
    query = """
        SELECT m.ho_ten, m.so_dien_thoai, m.ngay_het_han, 
               strftime('%H:%M:%S', c.check_in_time, 'localtime') as t
        FROM check_ins c
        JOIN members m ON c.member_id = m.id
        WHERE DATE(c.check_in_time, 'localtime') = DATE('now', 'localtime')
        ORDER BY c.check_in_time DESC LIMIT 20
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    today = datetime.now().date()
    
    for r in rows:
        # Tính toán số ngày còn hạn
        days_left = 0
        if r['ngay_het_han']:
            try:
                expiry = datetime.strptime(r['ngay_het_han'], '%Y-%m-%d').date()
                days_left = (expiry - today).days
            except:
                pass
        
        # Đóng gói thêm biến days_left để gửi lên giao diện
        history.append({
            "name": f"{r['ho_ten']} (****{r['so_dien_thoai'][-4:]})", 
            "time": r['t'],
            "days_left": days_left
        })
        
    return history