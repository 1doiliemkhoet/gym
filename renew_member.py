from database import get_connection, log_system_action, generate_blind_index
from datetime import datetime
from dateutil.relativedelta import relativedelta
from mail_service import send_renewal_email

def renew_membership_logic(cccd_number, months_to_add):
    """Gia hạn với bảng giá cố định 1-3-6 tháng [cite: 2026-03-07]"""
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


        price_mapping = {1: 300000, 3: 900000, 6: 1800000}
        amount = price_mapping.get(months_to_add, 0)


        cursor.execute("UPDATE members SET ngay_het_han = ?, trang_thai = 'Active' WHERE id = ?", 
                       (new_expiry, member_id))

        cursor.execute(
            "INSERT INTO payments (member_id, amount, content, payment_date) VALUES (?, ?, ?, ?)", 
            (member_id, amount, f"Gia hạn {months_to_add} tháng", today)
        )

        conn.commit()
        log_system_action(f"Gia han {months_to_add} thang cho: {name}", "members", member_id)
        send_renewal_email(email, name, months_to_add, new_expiry.strftime('%d-%m-%Y'))
        
        return True, f"Gia hạn thành công! Hạn mới của {name}: {new_expiry.strftime('%d/%m/%Y')}"

    except Exception as e:
        if conn: conn.rollback()
        return False, f"Lỗi: {e}"
    finally:
        if conn: conn.close()