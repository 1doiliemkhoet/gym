import pandas as pd
from datetime import datetime
from database import get_connection, decrypt_cccd

def export_to_excel_logic():
    """
    Xuất dữ liệu hội viên ra file Excel với định dạng chuyên nghiệp và bảo mật
    """
    conn = None
    try:
        # 1. Kết nối và lấy dữ liệu thủ công để tránh lỗi UserWarning của Pandas
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT ho_ten, cccd, so_dien_thoai, email, gioi_tinh, 
                   ngay_sinh, goi_tap, ngay_dang_ky, ngay_het_han 
            FROM members
        """
        cursor.execute(query)
        rows = cursor.fetchall() # Tải toàn bộ dữ liệu về bộ nhớ
        
        # 2. Tạo DataFrame từ danh sách kết quả
        df = pd.DataFrame(rows, columns=['ho_ten', 'cccd', 'so_dien_thoai', 'email', 'gioi_tinh',
                                         'ngay_sinh', 'goi_tap', 'ngay_dang_ky', 'ngay_het_han'])
        
        if df.empty:
            return False, "Hệ thống th gym hiện chưa có dữ liệu hội viên để xuất!"

        # 3. GIẢI MÃ PII (Thông tin cá nhân nhạy cảm)
        # Giải mã CCCD để hiển thị trong báo cáo nội bộ
        df['cccd'] = df['cccd'].apply(lambda x: decrypt_cccd(x) if x else "N/A")

        # 4. CHUẨN HÓA ĐỊNH DẠNG NGÀY THÁNG
        # Chuyển đổi các cột ngày sang định dạng Ngày-Tháng-Năm (DD-MM-YYYY)
        date_columns = ['ngay_sinh', 'ngay_dang_ky', 'ngay_het_han']
        for col in date_columns:
            df[col] = pd.to_datetime(df[col]).dt.strftime('%d-%m-%Y')

        # 5. ĐỔI TÊN CỘT SANG TIẾNG VIỆT (Như Excel chuyên nghiệp)
        df.columns = [
            'Họ Tên', 'Số CCCD', 'Số Điện Thoại', 'Email', 
            'Giới Tính', 'Ngày Sinh', 'Gói Tập', 'Ngày Đăng Ký', 'Ngày Hết Hạn'
        ]

        # 6. XUẤT FILE VÀ TỰ ĐỘNG CĂN CHỈNH ĐỘ RỘNG CỘT
        file_name = f"Bao_cao_th_gym_{datetime.now().strftime('%d%m%Y_%H%M%S')}.xlsx"
        
        # Sử dụng engine 'xlsxwriter' để can thiệp sâu vào định dạng file
        with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='DanhSachHoiVien')
            
            # Lấy đối tượng workbook và worksheet để định dạng
            workbook  = writer.book
            worksheet = writer.sheets['DanhSachHoiVien']
            
            # Tự động tính toán và đặt độ rộng cột dựa trên nội dung dài nhất
            for i, col in enumerate(df.columns):
                column_len = max(df[col].astype(str).map(len).max(), len(col)) + 5
                worksheet.set_column(i, i, column_len)
                
        return True, file_name

    except Exception as e:
        return False, f"Lỗi xuất báo cáo: {str(e)}"
    
    finally:
        # Đảm bảo đóng kết nối để tránh rò rỉ tài nguyên hệ thống
        if conn:
            conn.close()