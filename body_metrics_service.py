import math

from database import get_connection
from datetime import datetime

def calculate_bmi_status(bmi):
    """Phân loại BMI và trả về trạng thái """
    if bmi < 18.5:
        return "Gầy", "#3498db", "Cần tăng cân"
    elif 18.5 <= bmi < 25:
        return "Bình thường", "#2ecc71", "Duy trì tốt!"
    elif 25 <= bmi < 30:
        return "Thừa cân", "#f39c12", "Nên giảm cân"
    else:
        return "Béo phì", "#e74c3c", "Cần giảm cân ngay"

def save_body_metrics(member_id, height, weight, note=""):
    """Tính BMI và lưu chỉ số mới vào database."""
    conn = None
    try:
        height_cm = float(height)
        weight_kg = float(weight)
        if not math.isfinite(height_cm) or not math.isfinite(weight_kg):
            return False, "Chiều cao và cân nặng phải là số hữu hạn."
        if height_cm <= 0 or weight_kg <= 0:
            return False, "Chiều cao và cân nặng phải lớn hơn 0."

        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 2)

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO body_metrics (member_id, chieu_cao, can_nang, bmi, ngay_ghi_nhan, ghi_chu)
            VALUES (?, ?, ?, ?, CURRENT_DATE, ?)
        """
        cursor.execute(sql, (member_id, height_cm, weight_kg, bmi, note))
        conn.commit()

        status, _, suggestion = calculate_bmi_status(bmi)
        return True, f"Lưu thành công! BMI: {bmi} ({status}) - {suggestion}"
    except (TypeError, ValueError):
        return False, "Chiều cao và cân nặng phải là số hợp lệ."
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if conn:
            conn.close()
def get_metrics_history_detailed(member_id, limit=10):
    """Lấy lịch sử đo chi tiết với so sánh giữa các lần """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            SELECT id, ngay_ghi_nhan, chieu_cao, can_nang, bmi, ghi_chu 
            FROM body_metrics 
            WHERE member_id = ? 
            ORDER BY ngay_ghi_nhan DESC 
            LIMIT ?
        """
        cursor.execute(sql, (member_id, limit))
        history = cursor.fetchall()
        
        # Chuyển tuple thành list dict cho dễ xử lý
        history_dicts = []
        for row in history:
            history_dicts.append({
                'id': row[0],
                'ngay_ghi_nhan': row[1],
                'chieu_cao': row[2],
                'can_nang': row[3],
                'bmi': row[4],
                'ghi_chu': row[5]
            })
        
        # Đảo ngược để sắp xếp từ cũ đến mới (để so sánh)
        history_dicts = list(reversed(history_dicts))
        
        # Tính toán sự thay đổi
        detailed_history = []
        for i, entry in enumerate(history_dicts):
            # Format ngày
            if hasattr(entry['ngay_ghi_nhan'], 'strftime'):
                ngay_str = entry['ngay_ghi_nhan'].strftime('%d-%m-%Y')
            else:
                ngay_str = str(entry['ngay_ghi_nhan'])
            
            item = {
                "id": entry['id'],
                "ngay_ghi_nhan": ngay_str,
                "chieu_cao": entry['chieu_cao'],
                "can_nang": entry['can_nang'],
                "bmi": entry['bmi'],
                "ghi_chu": entry['ghi_chu'],
                "status": calculate_bmi_status(entry['bmi'])[0],
                "status_color": calculate_bmi_status(entry['bmi'])[1],
            }
            
            # So sánh với lần đo trước
            if i > 0:
                prev = history_dicts[i-1]
                weight_change = float(entry['can_nang']) - float(prev['can_nang'])
                bmi_change = entry['bmi'] - prev['bmi']
                
                item['weight_change'] = weight_change
                item['weight_change_pct'] = round((weight_change / float(prev['can_nang'])) * 100, 1) if prev['can_nang'] else 0
                item['bmi_change'] = round(bmi_change, 2)
            
            detailed_history.append(item)
        
        return detailed_history
    except Exception as e:
        print(f"Lỗi lấy lịch sử chi tiết: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_metrics_history(member_id):
    """Lấy lịch sử 5 lần đo gần nhất của hội viên [cite: 2026-01-28]"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = "SELECT ngay_ghi_nhan, chieu_cao, can_nang, bmi FROM body_metrics WHERE member_id = ? ORDER BY ngay_ghi_nhan DESC LIMIT 5"
        cursor.execute(sql, (member_id,))
        res = cursor.fetchall()
        return res
    except Exception as e:
        print(f"Lỗi: {e}")
        return []
    finally:
        if conn:
            conn.close()