from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import get_connection, encrypt_cccd, generate_blind_index, log_system_action
from mail_service import send_welcome_email_html 

def save_member_to_db(name, cccd, phone, email, package, gender, dob, price):
    """Lưu hội viên mới kèm chương trình KHUYẾN MÃI TẶNG THÁNG [cite: 2026-03-12]"""
    conn = None
    try:
        try:
            dob_dt = datetime.strptime(dob, "%d-%m-%Y").date()
        except ValueError:
            return False, "[ERROR] Ngày sinh phải nhập theo dạng DD-MM-YYYY"

        start_date = datetime.now().date()
        

        months_map = {"1 tháng": 1, "3 tháng": 3, "6 tháng": 6, "12 tháng": 12}
        base_months = months_map.get(package, 1)
        
        extra_months = 0
        payment_content = f"Đăng ký mới gói {package}"

        if base_months == 3:
            extra_months = 1  # Tặng 1 tháng
        elif base_months == 6:
            extra_months = 1  # Tặng 1 tháng
            payment_content += " + 🎁 TẶNG COMBO ĐI TẬP" 
        elif base_months == 12:
            extra_months = 2  # Tặng 2 tháng
        
        total_months = base_months + extra_months

        end_date = start_date + relativedelta(months=total_months)
        expire_date_str = end_date.strftime('%d-%m-%Y')


        cccd_hash = generate_blind_index(cccd) 
        encrypted_cccd = encrypt_cccd(cccd) 

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM members WHERE cccd_hash = ?", (cccd_hash,))
        if cursor.fetchone():
            return False, "[ERROR] Số CCCD này đã được đăng ký rồi!"
        
        cursor.execute("SELECT id FROM members WHERE email = ?", (email,))
        if cursor.fetchone():
            return False, "[ERROR] Email này đã được đăng ký rồi!"

        sql_member = """
            INSERT INTO members 
            (ho_ten, cccd, cccd_hash, so_dien_thoai, email, gioi_tinh, ngay_sinh, goi_tap, ngay_dang_ky, ngay_het_han, trang_thai) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active')
        """
        val_member = (name, encrypted_cccd, cccd_hash, phone, email, gender, dob_dt, package, start_date, end_date)
        
        cursor.execute(sql_member, val_member)
        member_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO payments (member_id, amount, content, payment_date) 
            VALUES (?, ?, ?, datetime('now', 'localtime'))
        """, (member_id, price, payment_content))
        
        conn.commit()

        log_system_action(f"Đăng ký: {name} (Tặng {extra_months} tháng)", "members", member_id)
        
        try:
            send_welcome_email_html(email, name, package, expire_date_str)
        except:
            print("[Lỗi] Không gửi được mail chào mừng nhưng dữ liệu đã lưu thành công.")
        
        return True, expire_date_str

    except Exception as e:
        if conn: conn.rollback()
        return False, f"[ERROR] Hệ thống: {str(e)}"
    finally:
        if conn: conn.close()

def check_cccd_match(cccd, gender, dob):
    """Bóc tách và đối chiếu CCCD với Giới tính và Năm sinh"""
    cccd = cccd.strip()
    if not cccd:
        return True, ""  # Bỏ qua nếu khách không nhập CCCD
        
    if len(cccd) != 12 or not cccd.isdigit():
        return False, "CCCD phải bao gồm đúng 12 chữ số."

    try:
        # Lấy năm sinh từ chuỗi ngày sinh (DD-MM-YYYY)
        birth_year = int(dob.split('-')[2])
        short_year = str(birth_year)[-2:]
    except:
        return False, "Ngày sinh bị sai định dạng (Cần DD-MM-YYYY)."

    # 1. Kiểm tra 2 số mã năm sinh (Vị trí số 5 và 6 trên CCCD)
    cccd_year = cccd[4:6]
    if cccd_year != short_year:
        return False, f"2 số năm sinh trên CCCD ({cccd_year}) không khớp với năm sinh khai báo ({birth_year})."

    # 2. Kiểm tra mã thế kỷ & giới tính (Vị trí số 4 trên CCCD)
    gender_code = cccd[3]
    century = birth_year // 100 + 1
    
    expected_codes = []
    if century == 20:   # Sinh 1900-1999
        expected_codes = ['0'] if gender == 'Nam' else ['1']
    elif century == 21: # Sinh 2000-2099
        expected_codes = ['2'] if gender == 'Nam' else ['3']
    elif century == 22: # Sinh 2100-2199
        expected_codes = ['4'] if gender == 'Nam' else ['5']

    if gender_code not in expected_codes:
        return False, f"Mã giới tính trên CCCD ({gender_code}) không khớp với giới tính '{gender}' và năm sinh '{birth_year}'."

    return True, "Hợp lệ"