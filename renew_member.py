from database import get_connection, log_system_action, generate_blind_index
from datetime import datetime
from dateutil.relativedelta import relativedelta
from mail_service import send_renewal_email

# Sửa lại hàm trong file renew_member.py
def renew_membership_logic(cccd_number, months_to_add, amount):
    """Gia hạn với giá tiền nhập thủ công từ giao diện"""
    conn = None
    try:
        cccd_hash = generate_blind_index(cccd_number)
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, ho_ten, email, ngay_het_han FROM members WHERE cccd_hash = ?", (cccd_hash,))
        result = cursor.fetchone()

        if not result:
            return False, "Không tìm thấy hội viên!"

        member_id, name, email = result['id'], result['ho_ten'], result['email']
        current_expiry = result['ngay_het_han']
        today = datetime.now().date()

        if isinstance(current_expiry, str):
            current_expiry = datetime.strptime(current_expiry, '%Y-%m-%d').date()

        base_date = max(today, current_expiry)
        new_expiry = base_date + relativedelta(months=months_to_add)

        # Cập nhật ngày hết hạn mới
        cursor.execute("UPDATE members SET ngay_het_han = ?, trang_thai = 'Active' WHERE id = ?", 
                       (new_expiry, member_id))

        # Lưu lịch sử thanh toán với số tiền truyền vào từ giao diện
        cursor.execute(
            "INSERT INTO payments (member_id, amount, content, payment_date) VALUES (?, ?, ?, ?)", 
            (member_id, amount, f"Gia hạn {months_to_add} tháng", today)
        )

        conn.commit()
        log_system_action(f"Gia han {months_to_add} thang cho: {name} - So tien: {amount}", "members", member_id)
        
        # Gửi mail thông báo (vẫn giữ luồng gửi mail nếu ông không tắt)
        send_renewal_email(email, name, months_to_add, new_expiry.strftime('%d-%m-%Y'))
        
        return True, f"Gia hạn thành công! Hạn mới của {name}: {new_expiry.strftime('%d/%m/%Y')}"
    except Exception as e:
        if conn: conn.rollback()
        return False, f"Lỗi: {e}"
    finally:
        if conn: conn.close()