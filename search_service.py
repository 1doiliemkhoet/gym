from datetime import datetime

from database import get_connection, generate_blind_index, decrypt_cccd, log_system_action

def search_member_logic(query, search_type="name"):
    """
    Tìm kiếm và lấy TẤT CẢ dữ liệu liên quan đến hội viên
    """
    conn = None
    try:
        clean_query = query.split("(")[0].strip() if "(" in query else query.strip()
        conn = get_connection()
        cursor = conn.cursor()
        if search_type == "name":
            sql = "SELECT * FROM members WHERE ho_ten LIKE ?"
            cursor.execute(sql, (f"%{clean_query}%",))
        else:
            cccd_hash = generate_blind_index(clean_query)
            sql = "SELECT * FROM members WHERE cccd_hash = ?"
            cursor.execute(sql, (cccd_hash,))
            
        results = cursor.fetchall()
        final_results = []

        for row in results:
            m = dict(row) 
            m_id = m['id']

            m['cccd'] = decrypt_cccd(m['cccd'])
            
            cursor.execute("""
                SELECT datetime(check_in_time, 'localtime') as local_time 
                FROM check_ins 
                WHERE member_id = ? 
                ORDER BY check_in_time DESC
            """, (m_id,))
            m['all_checkins'] = [r['local_time'] for r in cursor.fetchall()]

            cursor.execute("""
                SELECT amount, content, datetime(payment_date, 'localtime') as local_payment_date 
                FROM payments 
                WHERE member_id = ? 
                ORDER BY payment_date DESC
            """, (m_id,))
            m['all_payments'] = [dict(r) for r in cursor.fetchall()]
            
            cursor.execute("""
                SELECT chieu_cao, can_nang, bmi, date(ngay_ghi_nhan, 'localtime') as local_date 
                FROM body_metrics 
                WHERE member_id = ? 
                ORDER BY ngay_ghi_nhan DESC
            """, (m_id,))
            m['all_metrics'] = [dict(r) for r in cursor.fetchall()]
            
            final_results.append(m)
        
        # Không ghi query thô vào audit log: query có thể chứa CCCD hoặc dữ liệu cá nhân.
        query_kind = "name" if search_type == "name" else "cccd"
        log_system_action(f"Truy xuat ho so (loai tim kiem: {query_kind})", "members", None)
        return True, final_results

    except Exception as e:
        return False, str(e)
    finally:
        if conn: conn.close()

def update_member_status_logic(member_id, new_status):

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = "UPDATE members SET trang_thai = ? WHERE id = ?"
        cursor.execute(sql, (new_status, member_id))
        
        conn.commit()
        
        log_system_action(f"Thay doi trang thai sang {new_status}", "members", member_id)
        
        return True, f"Đã chuyển trạng thái hội viên sang {new_status}."
    except Exception as e:
        if conn: conn.rollback()
        return False, f"Lỗi cập nhật: {str(e)}"
    finally:
        if conn: conn.close()

def delete_member_logic(member_id):
    """Xóa vĩnh viễn hội viên và các dữ liệu liên quan """
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM check_ins WHERE member_id = ?", (member_id,))
        cursor.execute("DELETE FROM payments WHERE member_id = ?", (member_id,))
        cursor.execute("DELETE FROM body_metrics WHERE member_id = ?", (member_id,))
        
        cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
        
        conn.commit()
        return True, "Đã xóa hội viên thành công!"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()
def get_all_members_summary_logic():
    from database import get_connection
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Thêm CASE WHEN vào ORDER BY để đẩy số âm xuống cuối
        sql = """
            SELECT id, ho_ten, so_dien_thoai, ngay_het_han, trang_thai,
                   CAST((julianday(ngay_het_han) - julianday(DATE('now'))) AS INTEGER) AS so_ngay_con_lai
            FROM members 
            ORDER BY 
                CASE 
                    WHEN CAST((julianday(ngay_het_han) - julianday(DATE('now'))) AS INTEGER) < 0 THEN 1 
                    ELSE 0 
                END ASC,
                so_ngay_con_lai ASC
        """
        cursor.execute(sql)
        return True, cursor.fetchall()
    except Exception as e:
        return False, str(e)
    finally:
        if conn: conn.close()

def update_member_info_logic(member_id, new_name, new_phone, new_expiry):
    """Cập nhật tên, số điện thoại và ngày hết hạn của hội viên."""
    if not str(new_name or "").strip():
        return False, "Họ tên không được để trống."
    if not str(new_phone or "").strip():
        return False, "Số điện thoại không được để trống."

    try:
        expiry_date = datetime.strptime(str(new_expiry).strip(), "%Y-%m-%d").date()
        expiry_iso = expiry_date.isoformat()
    except (TypeError, ValueError):
        return False, "Ngày hết hạn không hợp lệ. Nhập theo định dạng YYYY-MM-DD."

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE members
            SET ho_ten = ?, so_dien_thoai = ?, ngay_het_han = ?
            WHERE id = ?
        """, (str(new_name).strip(), str(new_phone).strip(), expiry_iso, member_id))

        if cursor.rowcount == 0:
            conn.rollback()
            return False, "Không tìm thấy hội viên cần cập nhật."

        conn.commit()
        log_system_action("Cap nhat ho so hoi vien", "members", member_id)
        return True, "Cập nhật thông tin hội viên thành công!"
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Lỗi cập nhật: {e}"
    finally:
        if conn:
            conn.close()
