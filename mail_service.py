import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from database import get_connection

load_dotenv()
SMTP_USER = os.getenv("SMTP_USER", "dt01636879200@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
if not SMTP_PASSWORD:
    raise Exception("Thiếu SMTP_PASSWORD trong .env. Vui lòng cấu hình và khởi động lại.")

GYM_NAME = "TH GYM"
GYM_ADDRESS = "238 Đường Thương Cát, Phường Thương Cát, Hà Nội"
GYM_PHONE_1 = "0962 133 126"
GYM_PHONE_2 = "037 8995 698"

def get_email_footer():
    """Tạo footer chuyên nghiệp cho email """
    return f"""
    <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%); padding: 25px; text-align: center; border-top: 3px solid #00d4ff;">
        <div style="margin-bottom: 12px;">
            <h3 style="margin: 5px 0; color: #00d4ff; font-size: 16px; font-weight: bold;">{GYM_NAME}</h3>
        </div>
        
        <table style="width: 100%; max-width: 500px; margin: 0 auto; color: #ccc; font-size: 13px; border-collapse: collapse;">
            <tr>
                <td style="padding: 5px;">
                    <strong style="color: #fff;">📍 Địa chỉ:</strong><br/>
                    {GYM_ADDRESS}
                </td>
            </tr>
            <tr>
                <td style="padding: 5px;">
                    <strong style="color: #fff;">📞 Hotline:</strong><br/>
                    <a href="tel:{GYM_PHONE_1.replace(chr(32), '')}" style="color: #00d4ff; text-decoration: none;">{GYM_PHONE_1}</a> | 
                    <a href="tel:{GYM_PHONE_2.replace(chr(32), '')}" style="color: #00d4ff; text-decoration: none;">{GYM_PHONE_2}</a>
                </td>
            </tr>
        </table>
        
        <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #444; color: #888; font-size: 11px;">
            <p style="margin: 0;">© 2026 TH GYM - Nơi bạn thể hiện đúng sức mình</p>
        </div>
    </div>
    """

def send_welcome_email_html(receiver_email, member_name, package_name, expire_date):
    """Gửi thư chào mừng hội viên kèm thông tin QUÀ TẶNG KHUYẾN MÃI """
    server = None
    try:
        base_months = int(package_name.split()[0])
        promo_info = ""
        
        if base_months == 3:
            promo_info = "🎁 <strong>Tặng thêm:</strong> 01 tháng tập miễn phí"
        elif base_months == 6:
            promo_info = "🎁 <strong>Tặng thêm:</strong> 01 tháng tập + 🎒 Bộ Combo đi tập "
        elif base_months == 12:
            promo_info = "🎁 <strong>Tặng thêm:</strong> 02 tháng tập miễn phí"

        user_mail = SMTP_USER
        pass_mail = SMTP_PASSWORD
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(user_mail, pass_mail)

        msg = MIMEMultipart("alternative")
        msg['Subject'] = f"[TH Gym] - Xác nhận hội viên: {member_name}"
        msg['From'] = f"TH Gym Management <{user_mail}>"
        msg['To'] = receiver_email

        promo_section = f"""
            <div style="margin-top: 20px; padding: 15px; background-color: #fff4f2; border: 1px dashed #e74c3c; border-radius: 8px; text-align: center; color: #e74c3c;">
                <p style="margin: 0; font-size: 14px;">{promo_info}</p>
            </div>
        """ if promo_info else ""

        html = f"""
        <html>
        <body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: Arial, sans-serif;">
            <div style="background-color: #f0f2f5; padding: 50px 0; width: 100%;">
                <div style="max-width: 550px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; border: 1px solid #e1e4e8;">
                    
                    <div style="background-color: #1a1a1a; padding: 30px; text-align: center;">
                        <h1 style="color: #00d4ff; margin: 0; font-family: 'Segoe UI', Arial, sans-serif; letter-spacing: 2px;">TH GYM</h1>
                        <p style="color: #ccc; margin: 5px 0 0 0; font-size: 12px;">Nơi bạn thể hiện đúng sức mình</p>
                    </div>

                    <div style="padding: 40px; font-family: 'Segoe UI', Arial, sans-serif; color: #333; line-height: 1.6;">
                        <p style="font-size: 18px;">Chào <strong>{member_name}</strong>,</p>
                        <p>Chào mừng gia nhập cộng đồng tập luyện tại <strong>TH Gym</strong>! Thông tin đăng ký của bạn đã được cập nhật thành công.</p>
                        
                        <div style="margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #00d4ff;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 10px 0; color: #666; border-bottom: 1px solid #eee;">Gói tập đã chọn:</td>
                                    <td style="text-align: right; border-bottom: 1px solid #eee; font-weight: bold;">{package_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px 0; color: #666;">Ngày hết hạn (đã cộng KM):</td>
                                    <td style="text-align: right; color: #e74c3c; font-weight: bold;">{expire_date}</td>
                                </tr>
                            </table>
                            {promo_section}
                        </div>
                        
                        <p style="margin-top: 30px; color: #555;">Hãy mang theo CCCD khi đến phòng tập để check-in bạn nhé! </p>
                    </div>
                    {get_email_footer()}
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))
        server.sendmail(user_mail, [receiver_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Lỗi gửi mail: {e}")
        return False
    finally:
        if server: server.quit()

def auto_check_and_send_reminders():
    """Quét và gửi mail nhắc hạn, đảm bảo không gửi trùng """
    conn = None
    server = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT m.id, m.ho_ten, m.email, m.ngay_het_han, m.goi_tap 
            FROM members m
            LEFT JOIN email_logs e ON m.id = e.member_id 
                AND e.sent_date = DATE('now') 
                AND e.log_type = 'expiry_7d'
            WHERE CAST((julianday(m.ngay_het_han) - julianday(DATE('now'))) AS INTEGER) = 7 
                AND e.id IS NULL
        """
        cursor.execute(query)
        members = cursor.fetchall()

        if not members:
            return "Không có hội viên nào cần nhắc hạn mới."

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)

        sent_count = 0
        for m in members:
            expire_date_str = m['ngay_het_han'].strftime('%d-%m-%Y') if hasattr(m['ngay_het_han'], 'strftime') else str(m['ngay_het_han'])
            
            msg = MIMEMultipart("alternative")
            msg['Subject'] = f"[TH Gym] - Thông báo hết hạn gói tập"
            msg['From'] = f"TH Gym Management <{SMTP_USER}>"
            msg['To'] = m['email']

            html = f"""
            <html>
            <body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: Arial, sans-serif;">
                <div style="background-color: #f0f2f5; padding: 50px 0; width: 100%;">
                    <div style="max-width: 550px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; border: 1px solid #e1e4e8;">
                        <div style="background-color: #c0392b; padding: 30px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-family: 'Segoe UI', Arial, sans-serif; letter-spacing: 2px;">⏰ NHẮC HẠN GIA CHI</h1>
                            <p style="color: #ffcccb; margin: 5px 0 0 0; font-size: 12px;">Không nên bỏ lỡ cơ hội tập luyện</p>
                        </div>
                        <div style="padding: 40px; color: #333; line-height: 1.6;">
                            <p style="font-size: 16px;">Chào <strong>{m['ho_ten']}</strong>,</p>
                            <p>Gói tập <strong style="color: #c0392b;">{m['goi_tap']}</strong> của bạn sẽ hết hạn vào ngày <strong style="color: #c0392b;">{expire_date_str}</strong>.</p>
                            <p>Hãy ghé qua phòng tập để gia hạn gói tập và tiếp tục hành trình rèn luyện sức khỏe cùng chúng tôi! 💪</p>
                        </div>
                        {get_email_footer()}
                    </div>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(html, "html"))
            server.sendmail(SMTP_USER, [m['email']], msg.as_string())
            
            cursor.execute(
                "INSERT INTO email_logs (member_id, log_type, sent_date) VALUES (?, 'expiry_7d', DATE('now'))",
                (m['id'],)
            )
            sent_count += 1
            
        conn.commit()
        return f"Đã gửi {sent_count} mail nhắc hạn thành công."

    except Exception as e:
        if conn:
            conn.rollback()
        return f"Lỗi hệ thống mail: {e}"
    finally:
        if server:
            server.quit()
        if conn:
            conn.close()

def send_renewal_email(receiver_email, member_name, months_renewed, new_expire_date):
    """Gửi mail thông báo gia hạn thành công """
    server = None
    try:
        user_mail = SMTP_USER
        pass_mail = SMTP_PASSWORD

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(user_mail, pass_mail)

        msg = MIMEMultipart("alternative")
        msg['Subject'] = f"[TH Gym] - Gia hạn thành công: {months_renewed} tháng"
        msg['From'] = f"TH Gym Management <{user_mail}>"
        msg['To'] = receiver_email

        html = f"""
        <html>
        <body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: Arial, sans-serif;">
            <div style="background-color: #f0f2f5; padding: 50px 0; width: 100%;">
                <div style="max-width: 550px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; border: 1px solid #e1e4e8;">
                    
                    <div style="background-color: #27ae60; padding: 30px; text-align: center;">
                        <h1 style="color: #ffffff; margin: 0; font-family: 'Segoe UI', Arial, sans-serif; letter-spacing: 2px;">✓ GIA HẠN THÀNH CÔNG</h1>
                        <p style="color: #e8f5e9; margin: 5px 0 0 0; font-size: 12px;">Cảm ơn bạn đã tin tưởng TH Gym</p>
                    </div>

                    <div style="padding: 40px; font-family: 'Segoe UI', Arial, sans-serif; color: #333; line-height: 1.6;">
                        <p style="font-size: 18px;">Chào <strong>{member_name}</strong>,</p>
                        <p>Cảm ơn bạn đã gia hạn gói tập tại <strong>TH Gym</strong>! Tài khoản của bạn đã được cập nhật thành công.</p>
                        
                        <div style="margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #27ae60;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 12px 0; color: #666; font-weight: bold;">Thời hạn gia hạn:</td>
                                    <td style="text-align: right; color: #27ae60; font-weight: bold;">{months_renewed} tháng</td>
                                </tr>
                                <tr style="border-top: 1px solid #eee;">
                                    <td style="padding: 12px 0; color: #666; font-weight: bold;">Ngày hết hạn mới:</td>
                                    <td style="text-align: right; color: #e74c3c; font-weight: bold; font-size: 16px;">{new_expire_date}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <div style="margin: 25px 0; padding: 15px; background-color: #e8f5e9; border-radius: 8px;">
                            <p style="margin: 0; color: #2e7d32;"><strong>💪 Tiếp tục tập luyện và duy trì sức khỏe!</strong></p>
                        </div>
                        
                        <p style="margin-top: 30px; font-size: 14px; color: #666;">Nếu bạn có bất kỳ câu hỏi nào, vui lòng liên hệ với chúng tôi.</p>
                    </div>

                    {get_email_footer()}
                </div>
                <div style="height: 50px;"></div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))
        server.sendmail(user_mail, [receiver_email], msg.as_string())
        return True
    except Exception as e:
        print(f"❌ Lỗi gửi mail gia hạn: {e}")
        return False
    finally:
        if server: server.quit()