import math
from database import get_connection, log_system_action, generate_blind_index
from datetime import datetime
from dateutil.relativedelta import relativedelta
from mail_service import send_renewal_email

# Sửa lại hàm trong file renew_member.py
def renew_membership_logic(cccd_number, months_to_add, amount):
    """Gia hạn hội viên sau khi kiểm tra dữ liệu đầu vào."""
    conn = None
    try:
        try:
            months_float = float(months_to_add)
            months = int(months_float)
            amount_value = float(amount)
        except (TypeError, ValueError, OverflowError):
            return False, "Số tháng và số tiền phải là số hợp lệ."

        if not math.isfinite(months_float) or months_float != months or months < 1 or months > 120:
            return False, "Số tháng gia hạn phải là số nguyên từ 1 đến 120."
        if not math.isfinite(amount_value) or amount_value < 0:
            return False, "Số tiền gia hạn phải là số hữu hạn và không âm."
        cccd_value = str(cccd_number or "").strip()
        if not cccd_value:
            return False, "Vui lòng nhập CCCD hội viên."

        cccd_hash = generate_blind_index(cccd_value)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, ho_ten, email, ngay_het_han FROM members WHERE cccd_hash = ?",
            (cccd_hash,),
        )
        result = cursor.fetchone()
        if not result:
            return False, "Không tìm thấy hội viên!"

        member_id, name, email = result["id"], result["ho_ten"], result["email"]
        current_expiry = result["ngay_het_han"]
        if not current_expiry:
            return False, "Hội viên chưa có ngày hết hạn hợp lệ; chưa thể gia hạn."
        if isinstance(current_expiry, datetime):
            current_expiry = current_expiry.date()
        elif isinstance(current_expiry, str):
            try:
                current_expiry = datetime.strptime(current_expiry, "%Y-%m-%d").date()
            except ValueError:
                return False, "Ngày hết hạn hiện tại trong database không hợp lệ."
        today = datetime.now().date()
        base_date = max(today, current_expiry)
        new_expiry = base_date + relativedelta(months=months)

        cursor.execute(
            "UPDATE members SET ngay_het_han = ?, trang_thai = 'Active' WHERE id = ?",
            (new_expiry, member_id),
        )
        cursor.execute(
            "INSERT INTO payments (member_id, amount, content, payment_date) VALUES (?, ?, ?, ?)",
            (member_id, amount_value, f"Gia hạn {months} tháng", today),
        )
        conn.commit()
        log_system_action(
            f"Gia han {months} thang cho hoi vien", "members", member_id
        )
        # Lỗi gửi email không được đảo ngược một giao dịch đã commit thành công.
        if email and not send_renewal_email(email, name, months, new_expiry.strftime("%d-%m-%Y")):
            print("[WARN] Gia hạn đã lưu nhưng không gửi được email thông báo.")
        return True, f"Gia hạn thành công! Hạn mới của {name}: {new_expiry.strftime('%d/%m/%Y')}"
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Lỗi: {e}"
    finally:
        if conn:
            conn.close()
