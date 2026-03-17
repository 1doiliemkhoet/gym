import threading
import customtkinter as ctk
from tkinter import messagebox
import os
import tkinter as tk
import sys

from add_member import save_member_to_db 
from check_in_member import check_in_by_cccd_logic, get_today_checkin_history
from renew_member import renew_membership_logic
from revenue_stats import get_revenue_summary, get_detailed_revenue_stats
from export_excel import export_to_excel_logic 
from search_service import search_member_logic, update_member_status_logic
from mail_service import auto_check_and_send_reminders
from suggestion_service import get_checkin_suggestions
from body_metrics_service import save_body_metrics, get_metrics_history, get_metrics_history_detailed


def resource_path(relative_path):
    """Lấy đường dẫn tuyệt đối đến tài nguyên, dùng được cả khi chạy dev và EXE [cite: 2026-01-28]"""
    try:
        base_path = sys._MEIPASS 
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

COLORS = {
    "bg": "#0f0f0f",
    "sidebar": "#161616",
    "accent": "#b41f0e",
    "card": "#1e1e1e",
    "text": "#ffffff",
    "subtext": "#aaaaaa"
}

ctk.set_appearance_mode("dark")

class GymManagementApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.selected_cccd = None
        self.checkin_listbox = None
        self.current_suggestions_data = []

        self.title("TH gym")
        self.geometry("1100x680")
        self.configure(fg_color=COLORS["bg"])

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR MENU ---
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=COLORS["sidebar"])
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="TH gym ", 
                                     font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
                                     text_color=COLORS["accent"])
        self.logo_label.pack(pady=40)

        self.create_menu_button("Đăng ký Hội viên", self.show_registration)
        self.create_menu_button("Check-in CCCD", self.show_checkin)
        self.create_menu_button("Gia hạn Gói tập", self.show_renew)
        self.create_menu_button("Tìm kiếm Hội viên", self.show_search_screen)
        self.create_menu_button("Theo dõi sức khỏe", self.show_metrics_screen)
        self.create_menu_button("Báo cáo Doanh thu", self.show_dashboard)

        # --- MAIN CONTENT AREA ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

        # Chạy quét mail tự động 
        threading.Thread(target=self.run_auto_mail_scan, daemon=True).start()
        
        self.show_registration() 

    # ================= LOGIC HỆ THỐNG =================

    def run_auto_mail_scan(self):
        try:
            result = auto_check_and_send_reminders()
            print(f"[Hệ thống] {result}")
        except Exception as e:
            print(f"[Lỗi Auto Mail] {e}")

    def create_menu_button(self, text, command):
        btn = ctk.CTkButton(self.sidebar_frame, text=text, fg_color="transparent", 
                           text_color=COLORS["text"], hover_color=COLORS["card"],
                           anchor="w", height=45, font=("Inter", 14), command=command)
        btn.pack(pady=5, padx=20, fill="x")

    def clear_main_frame(self):
        self.hide_checkin_suggestions()
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def render_title(self, text):
        ctk.CTkLabel(self.main_frame, text=text, font=("Inter", 26, "bold"), 
                     text_color=COLORS["accent"]).pack(anchor="w", pady=(0, 25))

    def create_input(self, parent, placeholder):
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder, width=350, height=40,
                            fg_color="#121212", border_color="#333333")
        entry.pack(pady=10)
        return entry

    def on_checkin_typing(self, event):
        """Xử lý gợi ý linh hoạt (Tên + SĐT) [cite: 2026-03-04]"""
        widget = event.widget
        typed = widget.get().strip()
        
        self.current_suggestions_data = get_checkin_suggestions(typed)
        self.selected_cccd = None # Reset khi gõ mới

        if not self.current_suggestions_data:
            self.hide_checkin_suggestions()
            return

        self.hide_checkin_suggestions()
        self.checkin_listbox = tk.Listbox(self, font=("Inter", 11), bg="#222", fg="white", 
                                          borderwidth=0, highlightthickness=0)
        
        for item in self.current_suggestions_data:
            self.checkin_listbox.insert(tk.END, item["display"])

        x_pos = widget.winfo_rootx() - self.winfo_rootx()
        y_pos = widget.winfo_rooty() - self.winfo_rooty() + widget.winfo_height()
        
        self.checkin_listbox.place(x=x_pos, y=y_pos, width=widget.winfo_width(), height=100)
        self.checkin_listbox.lift()
        self.checkin_listbox.bind("<<ListboxSelect>>", lambda e: self.select_checkin_suggestion(widget))

    def select_checkin_suggestion(self, target_entry):
        """Làm sạch tên khi chọn để tránh lỗi tìm kiếm [cite: 2026-03-04]"""
        if not target_entry.winfo_exists() or not self.checkin_listbox:
            self.hide_checkin_suggestions()
            return

        selection = self.checkin_listbox.curselection()
        if selection:
            idx = selection[0]
            selected_item = self.current_suggestions_data[idx]
            
            display_text = selected_item["display"]
            clean_name = display_text.split("(")[0].strip() if "(" in display_text else display_text
            
            target_entry.delete(0, tk.END)
            target_entry.insert(0, clean_name)

            self.selected_cccd = selected_item["real_value"]
            self.hide_checkin_suggestions()

            if hasattr(self, 'metrics_history_frame') and self.metrics_history_frame.winfo_exists():
                success, data = search_member_logic(clean_name, "name")
                if success and data:
                    self.refresh_metrics_history(data[0]['id'])

    def hide_checkin_suggestions(self):
        if self.checkin_listbox:
            try:
                self.checkin_listbox.place_forget()
                self.checkin_listbox.destroy()
            except: pass
            self.checkin_listbox = None

    # ================= MÀN HÌNH CHÍNH =================

    def show_registration(self):
        self.clear_main_frame()
        self.render_title("QUẢN LÝ ĐĂNG KÝ")
        card = ctk.CTkFrame(self.main_frame, fg_color=COLORS["card"], corner_radius=15)
        card.pack(fill="both", expand=True, padx=5, pady=5)

        self.entry_name = self.create_input(card, "Họ và tên khách hàng")
        self.entry_cccd = self.create_input(card, "Số CCCD (12 số)")

        gender_frame = ctk.CTkFrame(card, fg_color="transparent")
        gender_frame.pack(pady=5)
        self.gender_var = ctk.StringVar(value="Nam")
        ctk.CTkLabel(gender_frame, text="Giới tính: ").pack(side="left", padx=10)
        ctk.CTkComboBox(gender_frame, values=["Nam", "Nữ", "Khác"], variable=self.gender_var, width=280).pack(side="left")

        self.entry_dob = self.create_input(card, "Ngày sinh (25-01-2000)")
        self.entry_phone = self.create_input(card, "Số điện thoại")
        self.entry_email = self.create_input(card, "Địa chỉ Gmail")

        self.package_var = ctk.StringVar(value="1 tháng")
        ctk.CTkComboBox(card, 
                values=["1 tháng", "3 tháng", "6 tháng", "12 tháng"],
                variable=self.package_var, # Thêm chữ 'v' vào đây [cite: 2026-03-04]
                width=350, 
                height=40).pack(pady=10)

        self.entry_price = self.create_input(card, "Giá tiền thanh toán (VNĐ)")

        ctk.CTkButton(card, text="XÁC NHẬN & LƯU", fg_color="#2ecc71", height=45, command=self.handle_registration).pack(pady=20)

    def handle_registration(self):
        try:
            success, msg = save_member_to_db(
                self.entry_name.get(), self.entry_cccd.get(), self.entry_phone.get(), 
                self.entry_email.get(), self.package_var.get(), 
                self.gender_var.get(), self.entry_dob.get(), float(self.entry_price.get())
            )
            if success: messagebox.showinfo("Thành công", f"Hội viên đã được lưu!\nHạn dùng: {msg}")
            else: messagebox.showerror("Lỗi", msg)
        except ValueError: messagebox.showerror("Lỗi", "Giá tiền không hợp lệ!")

    def show_checkin(self):
        self.clear_main_frame()
        self.render_title("XÁC THỰC RA VÀO")
        input_card = ctk.CTkFrame(self.main_frame, fg_color=COLORS["card"], corner_radius=15)
        input_card.pack(fill="x", pady=(0, 20))
        
        self.entry_cccd_check = self.create_input(input_card, "Nhập tên hoặc quét mã...")
        self.entry_cccd_check.bind("<KeyRelease>", self.on_checkin_typing)

        ctk.CTkButton(input_card, text="XÁC NHẬN VÀO TẬP", fg_color=COLORS["accent"], text_color="#000000",
                     font=("Inter", 14, "bold"), height=40, command=self.handle_checkin).pack(pady=20)

        self.history_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color=COLORS["card"], height=300)
        self.history_frame.pack(fill="both", expand=True)
        self.refresh_checkin_history()

    def handle_update_status(self, member_id):
        """Xử lý nút bấm cập nhật trạng thái [cite: 2026-03-04]"""
        new_status = self.status_var.get()
        
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn đổi trạng thái sang {new_status}?"):
            
            success, msg = update_member_status_logic(member_id, new_status)
        
            if success:
                messagebox.showinfo("Thành công", msg)
            else:
                messagebox.showerror("Lỗi", msg)

    def display_member_full_profile(self, member_data):
        """Vẽ giao diện hiển thị TẤT CẢ thông tin hội viên [cite: 2026-03-04]"""

        for widget in self.detail_container.winfo_children():
            widget.destroy()

        status_card = ctk.CTkFrame(self.detail_container, fg_color=COLORS["card"])
        status_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(status_card, text=f"👤 {member_data['ho_ten']}", font=("Inter", 16, "bold")).pack(side="left", padx=20, pady=15)
        
        self.status_var = ctk.StringVar(value=member_data['trang_thai'])
        status_cb = ctk.CTkComboBox(status_card, values=["Active", "Inactive", "Locked"], variable=self.status_var, width=120)
        status_cb.pack(side="right", padx=10)
        
        ctk.CTkButton(status_card, text="Lưu trạng thái", width=100, fg_color="#3498db", 
                       command=lambda: self.handle_update_status(member_data['id'])).pack(side="right", padx=10)

        tabview = ctk.CTkTabview(self.detail_container, height=400)
        tabview.pack(fill="both", expand=True)
        
        tab_info = tabview.add("ℹ️ Thông tin")
        tab_checkin = tabview.add("🕒 Check-in")
        tab_health = tabview.add("⚖️ Sức khỏe")
        tab_payment = tabview.add("💰 Thanh toán")

        info_text = f"CCCD: {member_data['cccd']}\nSĐT: {member_data['so_dien_thoai']}\nHạn dùng: {member_data['ngay_het_han']}"
        ctk.CTkLabel(tab_info, text=info_text, justify="left", anchor="w").pack(padx=20, pady=20)

        for time in member_data['all_checkins'][:10]: # Hiện 10 lần gần nhất [cite: 2026-03-05]
            row = ctk.CTkFrame(tab_checkin, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"✅ Đã vào tập lúc: {time}").pack(side="left", padx=10)

        for m in member_data['all_metrics'][:5]:
            row = ctk.CTkFrame(tab_health, fg_color="#1e1e1e")
            row.pack(fill="x", pady=2, padx=10)
            ctk.CTkLabel(row, text=f"{m['ngay_ghi_nhan']}: {m['can_nang']}kg - BMI: {m['bmi']}").pack(pady=5)

        for p in member_data['all_payments'][:5]:
            row = ctk.CTkFrame(tab_payment, fg_color="#1e1e1e")
            row.pack(fill="x", pady=2, padx=10)
            ctk.CTkLabel(row, text=f"{p['payment_date']}: {p['amount']:,.0f}đ - {p['content']}").pack(pady=5)

    def handle_checkin(self):
        """Chỉ chạy một lần duy nhất trong Thread [cite: 2026-03-04]"""
        cccd_input = self.selected_cccd if self.selected_cccd else self.entry_cccd_check.get().strip()
        if not cccd_input: return

        def task():
            success, msg = check_in_by_cccd_logic(cccd_input)
            self.selected_cccd = None 
            
            self.after(0, lambda: self.finish_checkin(success, msg))

        threading.Thread(target=task, daemon=True).start()

    def finish_checkin(self, success, msg):
        """Hàm bổ trợ để hiển thị kết quả [cite: 2026-03-04]"""
        if success:
            messagebox.showinfo("Thành công", msg)
            self.entry_cccd_check.delete(0, 'end')
            self.refresh_checkin_history() 
        else:
            messagebox.showerror("Lỗi", msg)

    def show_metrics_screen(self):
        """Hiển thị đầy đủ ô nhập liệu và bảng lịch sử [cite: 2026-03-04]"""
        self.clear_main_frame()
        self.render_title("THEO DÕI SỨC KHỎE ")

        input_card = ctk.CTkFrame(self.main_frame, fg_color=COLORS["card"], corner_radius=15)
        input_card.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(input_card, text="🔍 Tìm hội viên", font=("Inter", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 5))
        self.entry_member_search = self.create_input(input_card, "Nhập tên hội viên...")
        self.entry_member_search.bind("<KeyRelease>", self.on_checkin_typing)

        metrics_row = ctk.CTkFrame(input_card, fg_color="transparent")
        metrics_row.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(metrics_row, text="📊 Chỉ số cơ thể", font=("Inter", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", pady=(0, 5))
        
        input_inner = ctk.CTkFrame(metrics_row, fg_color="transparent")
        input_inner.pack(fill="x")
        
        self.entry_h = ctk.CTkEntry(input_inner, placeholder_text="Cao (cm)", width=120)
        self.entry_h.pack(side="left", padx=5)
        self.entry_h.bind("<KeyRelease>", self.preview_bmi)
        
        self.entry_w = ctk.CTkEntry(input_inner, placeholder_text="Nặng (kg)", width=120)
        self.entry_w.pack(side="left", padx=5)
        self.entry_w.bind("<KeyRelease>", self.preview_bmi)
        
        self.bmi_preview_label = ctk.CTkLabel(input_inner, text="BMI: --", font=("Inter", 12, "bold"), text_color="#aaa")
        self.bmi_preview_label.pack(side="left", padx=15)

        self.entry_note = self.create_input(input_card, "Ghi chú (tùy chọn)")
        
        btn_row = ctk.CTkFrame(input_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(10, 15))
        
        ctk.CTkButton(btn_row, text="💾 LƯU CHỈ SỐ", fg_color="#3498db", height=40, width=180, 
                       font=("Inter", 12, "bold"), command=self.handle_save_metrics).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="🔄 RESET", fg_color="#95a5a6", height=40, width=90, 
                       command=self.reset_metrics_input).pack(side="left", padx=5)
        ctk.CTkLabel(self.main_frame, text="📈 LỊCH SỬ ĐO LƯỜNG (10 LẦN GẦN NHẤT)", 
                     font=("Inter", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", pady=(20, 10), padx=5)
        
        self.metrics_history_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color=COLORS["card"], corner_radius=10)
        self.metrics_history_frame.pack(fill="both", expand=True, padx=5)
        
        self.refresh_metrics_history(None)

    def reset_metrics_input(self):
        """Xóa sạch các ô nhập liệu về trạng thái ban đầu [cite: 2026-03-04]"""
        self.entry_member_search.delete(0, 'end')
        self.entry_h.delete(0, 'end')
        self.entry_w.delete(0, 'end')
        self.entry_note.delete(0, 'end')
        self.bmi_preview_label.configure(text="BMI: --", text_color="#aaa")
        self.selected_cccd = None
        self.refresh_metrics_history(None)

    def handle_save_metrics(self):
        raw_name = self.entry_member_search.get().strip()
        name = raw_name.split("(")[0].strip() if "(" in raw_name else raw_name
        
        h, w = self.entry_h.get().strip(), self.entry_w.get().strip()
        if not name or not h or not w:
            messagebox.showwarning("Chú ý", "Nhập đủ Tên, Cao, Nặng!")
            return
        try:
            success_s, data = search_member_logic(name, "name")
            if success_s and data:
                m_id = data[0]['id']
                success_save, msg = save_body_metrics(m_id, h, w, self.entry_note.get())
                if success_save:
                    messagebox.showinfo("✅ Thành công", msg)
                    self.refresh_metrics_history(m_id)
                    self.reset_metrics_input()
                else: messagebox.showerror("❌ Lỗi", msg)
            else: messagebox.showerror("❌ Lỗi", f"Không tìm thấy hội viên: {name}")
        except ValueError: messagebox.showerror("❌ Lỗi", "Chiều cao/Cân nặng phải là số!")

    def refresh_metrics_history(self, member_id):
        for widget in self.metrics_history_frame.winfo_children():
            widget.destroy()

        header_frame = ctk.CTkFrame(self.metrics_history_frame, fg_color="#252525", height=40)
        header_frame.pack(fill="x", pady=5, padx=10)
        
        cols = [("📅 Ngày", 150), ("📏 Chiều Cao", 120), ("⚖️ Cân Nặng", 120), ("BMI", 100), ("Trạng thái", 150)]
        for label, width in cols:
            ctk.CTkLabel(header_frame, text=label, font=("Inter", 11, "bold"), 
                         width=width, anchor="w").pack(side="left", padx=10, pady=10)
        
        if member_id is None:
            ctk.CTkLabel(self.metrics_history_frame, text="Vui lòng tìm hội viên để xem lịch sử.", 
                         text_color="#666666").pack(pady=20)
            return

        history = get_metrics_history_detailed(member_id, limit=10)
        
        if not history:
            ctk.CTkLabel(self.metrics_history_frame, text="Hội viên này chưa có dữ liệu đo lường.", 
                         text_color="#666666").pack(pady=20)
            return
        
        for entry in history:
            row = ctk.CTkFrame(self.metrics_history_frame, fg_color="#1e1e1e", corner_radius=8)
            row.pack(fill="x", pady=3, padx=10)
            
            ctk.CTkLabel(row, text=entry['ngay_ghi_nhan'], font=("Inter", 11), width=150, anchor="w").pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"{entry['chieu_cao']} cm", font=("Inter", 11), width=120, anchor="w").pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"{entry['can_nang']} kg", font=("Inter", 11), width=120, anchor="w").pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=str(entry['bmi']), font=("Inter", 11, "bold"), 
                         text_color=entry['status_color'], width=100, anchor="w").pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=entry['status'], font=("Inter", 10), 
                         text_color=entry['status_color'], width=150, anchor="w").pack(side="left", padx=10, pady=8)

    def show_dashboard(self):
        """Khắc phục lỗi mất nút Xuất Excel bằng cách thêm Scrollable Container [cite: 2026-03-04]"""
        self.clear_main_frame()
        self.render_title("BÁO CÁO DOANH THU CHI TIẾT")
        
        success, stats = get_detailed_revenue_stats()
        if not success:
            ctk.CTkLabel(self.main_frame, text="❌ Lỗi tải dữ liệu", text_color="#e74c3c").pack(pady=50)
            return

        scroll_container = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=5, pady=5)

        revenue_card = ctk.CTkFrame(scroll_container, fg_color=COLORS["card"], corner_radius=15)
        revenue_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(revenue_card, text="💰 DOANH THU", font=("Inter", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 5))
        
        revenue_grid = ctk.CTkFrame(revenue_card, fg_color="transparent")
        revenue_grid.pack(fill="x", padx=20, pady=10)
        
        rev_items = [
            ("Hôm nay", f"{stats['daily']:,.0f}đ", "#3498db"),
            ("Tuần này", f"{stats['weekly']:,.0f}đ", "#9b59b6"),
            ("Tháng này", f"{stats['monthly']:,.0f}đ", "#e74c3c"),
            ("Tổng toàn bộ", f"{stats['total_all']:,.0f}đ", "#2ecc71"),
        ]
        
        for i, (label, value, color) in enumerate(rev_items):
            item = ctk.CTkFrame(revenue_grid, fg_color="#1e1e1e", corner_radius=8)
            item.grid(row=0, column=i, padx=5, sticky="ew")
            ctk.CTkLabel(item, text=label, font=("Inter", 11), text_color="#aaa").pack(pady=(10, 2), padx=10)
            ctk.CTkLabel(item, text=value, font=("Inter", 14, "bold"), text_color=color).pack(pady=(2, 10), padx=10)
        
        revenue_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # --- 2. KHỐI HỘI VIÊN --- 
        member_card = ctk.CTkFrame(scroll_container, fg_color=COLORS["card"], corner_radius=15)
        member_card.pack(fill="x", pady=10)
        
        member_grid = ctk.CTkFrame(member_card, fg_color="transparent")
        member_grid.pack(fill="x", padx=20, pady=20)
        
        member_items = [
            ("Đang hoạt động", str(stats['active_members']), "#2ecc71"),
            ("Mới tháng này", str(stats['new_members_month']), "#3498db"),
            ("Sắp hết hạn", str(stats['expiring_soon']), "#f39c12"),
        ]
        
        for i, (label, value, color) in enumerate(member_items):
            item = ctk.CTkFrame(member_grid, fg_color="#1e1e1e", corner_radius=8)
            item.grid(row=0, column=i, padx=5, sticky="ew")
            ctk.CTkLabel(item, text=label, font=("Inter", 11), text_color="#aaa").pack(pady=(10, 2), padx=10)
            ctk.CTkLabel(item, text=value, font=("Inter", 16, "bold"), text_color=color).pack(pady=(2, 10), padx=10)
        
        member_grid.grid_columnconfigure((0, 1, 2), weight=1)
        
        # --- 3. BẢNG DOANH THU THEO GÓI --- 
        if stats.get('package_stats'):
            package_card = ctk.CTkFrame(scroll_container, fg_color=COLORS["card"], corner_radius=15)
            package_card.pack(fill="x", pady=10)
            
            ctk.CTkLabel(package_card, text="📊 DOANH THU THEO GÓI TẬP", font=("Inter", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=15)
            
            for pkg in stats['package_stats']:
                row = ctk.CTkFrame(package_card, fg_color="#1e1e1e", corner_radius=8)
                row.pack(fill="x", pady=2, padx=20)
                ctk.CTkLabel(row, text=pkg['goi_tap'], width=200, anchor="w").pack(side="left", padx=10, pady=5)
                ctk.CTkLabel(row, text=f"{pkg['total']:,.0f}đ", text_color="#2ecc71", font=("Inter", 12, "bold")).pack(side="left", padx=10)

        ctk.CTkButton(scroll_container, text="📥 XUẤT BÁO CÁO EXCEL", height=45, 
                       font=("Inter", 14, "bold"), fg_color=COLORS["accent"], 
                       command=self.handle_export).pack(pady=20, fill="x", padx=100)

    def preview_bmi(self, event=None):
        try:
            h, w = self.entry_h.get().strip(), self.entry_w.get().strip()
            if h and w:
                bmi = round(float(w) / ((float(h)/100)**2), 2)
                from body_metrics_service import calculate_bmi_status
                status, color, _ = calculate_bmi_status(bmi)
                self.bmi_preview_label.configure(text=f"BMI: {bmi} ({status})", text_color=color)
        except: pass

    def refresh_checkin_history(self):
        for widget in self.history_frame.winfo_children(): widget.destroy()
        history = get_today_checkin_history()
        for entry in history:
            row = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"[{entry['time']}]", text_color=COLORS["accent"], width=80).pack(side="left")
            ctk.CTkLabel(row, text=entry['name'], text_color="white").pack(side="left", padx=10)

    def handle_export(self):
        success, path = export_to_excel_logic()
        if success:
            messagebox.showinfo("Thành công", f"Lưu tại: {path}")
            os.startfile(path)
        else: messagebox.showerror("Lỗi", path)

    def show_renew(self):
        """Màn hình gia hạn rút gọn (Không có ô nhập giá) [cite: 2026-03-04]"""
        self.clear_main_frame()
        self.render_title("GIA HẠN GÓI TẬP")
        
        card = ctk.CTkFrame(self.main_frame, fg_color=COLORS["card"], corner_radius=15)
        card.pack(fill="x", pady=10, padx=5)
        
        self.entry_cccd_renew = self.create_input(card, "Số CCCD hội viên...")
        
        self.renew_month_var = ctk.StringVar(value="1 tháng")
        ctk.CTkComboBox(card, values=["1 tháng", "3 tháng", "6 tháng"], 
                        variable=self.renew_month_var, width=350, height=40).pack(pady=10)
        
        ctk.CTkButton(card, text="XÁC NHẬN GIA HẠN", fg_color="#e67e22", height=45, width=200,
                       font=("Inter", 14, "bold"), command=self.handle_renew).pack(pady=20)

    def handle_renew(self):
        """Chỉ gửi CCCD và Số tháng xuống logic [cite: 2026-03-04]"""
        cccd = self.entry_cccd_renew.get().strip()
        if not cccd:
            messagebox.showwarning("Chú ý", "Vui lòng nhập số CCCD!")
            return

        def task():
            try:
                months = int(self.renew_month_var.get().split()[0])
                success, msg = renew_membership_logic(cccd, months)
                
                self.after(0, lambda: messagebox.showinfo("Kết quả", msg))
                if success:
                    self.after(0, lambda: self.entry_cccd_renew.delete(0, 'end'))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Lỗi", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def show_search_screen(self):
        """Màn hình tìm kiếm hội viên [cite: 2026-03-04]"""
        self.clear_main_frame()
        self.render_title("TÌM KIẾM HỘI VIÊN")
        search_card = ctk.CTkFrame(self.main_frame, fg_color=COLORS["card"], corner_radius=15)
        search_card.pack(fill="x", pady=(0, 20))
        self.entry_search = self.create_input(search_card, "Nhập tên hoặc số CCCD...")
        ctk.CTkButton(search_card, text="TRA CỨU", fg_color=COLORS["accent"], text_color="#000000",
                       font=("Inter", 14, "bold"), height=40, command=self.handle_search).pack(pady=20)

        self.detail_container = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent", height=550)
        self.detail_container.pack(fill="both", expand=True)

    def display_member_full_profile(self, member_data):
        """Vẽ Tabview hiển thị mọi thông tin và các nút chức năng [cite: 2026-03-04]"""
        for widget in self.detail_container.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(self.detail_container, fg_color=COLORS["card"], corner_radius=15)
        header.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(header, text=f"👤 {member_data['ho_ten']}", 
                     font=("Inter", 18, "bold"), text_color=COLORS["accent"]).pack(side="left", padx=20, pady=20)
        
        
        ctk.CTkButton(header, text="XÓA HỘI VIÊN", width=110, height=32, 
                       fg_color="#c0392b", hover_color="#a93226", font=("Inter", 11, "bold"),
                       command=lambda: self.handle_delete_member(member_data['id'])).pack(side="right", padx=10)

        ctk.CTkButton(header, text="LƯU", width=60, height=32, 
                       fg_color="#3498db", font=("Inter", 11, "bold"),
                       command=lambda: self.handle_update_status(member_data['id'])).pack(side="right", padx=5)

        self.status_var = ctk.StringVar(value=member_data['trang_thai'])
        status_cb = ctk.CTkComboBox(header, values=["Active", "Inactive", "Locked"], 
                                    variable=self.status_var, width=110, height=32)
        status_cb.pack(side="right", padx=5)

        tabview = ctk.CTkTabview(self.detail_container, height=450, segmented_button_selected_color=COLORS["accent"])
        tabview.pack(fill="both", expand=True)
        
        t_info = tabview.add("ℹ️ Thông tin")
        t_checkin = tabview.add("🕒 Check-in")
        t_health = tabview.add("⚖️ Sức khỏe")
        t_payment = tabview.add("💰 Thanh toán")

        info_str = f"🆔 CCCD: {member_data['cccd']}\n📞 SĐT: {member_data['so_dien_thoai']}\n📧 Email: {member_data['email']}\n📅 Hạn dùng: {member_data['ngay_het_han']}"
        ctk.CTkLabel(t_info, text=info_str, justify="left", font=("Inter", 13), padx=20).pack(pady=20, anchor="w")

        for time in member_data.get('all_checkins', [])[:10]:
            r = ctk.CTkFrame(t_checkin, fg_color="#1e1e1e", corner_radius=5)
            r.pack(fill="x", pady=2, padx=10)
            ctk.CTkLabel(r, text=f"✅ Vào tập: {time}").pack(padx=10, pady=5)

        for m in member_data.get('all_metrics', []):
            r = ctk.CTkFrame(t_health, fg_color="#1e1e1e")
            r.pack(fill="x", pady=2, padx=10)
            ctk.CTkLabel(r, text=f"📅 {m['local_date']}: {m['chieu_cao']}cm - {m['can_nang']}kg - BMI: {m['bmi']}").pack(pady=5)

        for p in member_data.get('all_payments', []):
            r = ctk.CTkFrame(t_payment, fg_color="#1e1e1e")
            r.pack(fill="x", pady=2, padx=10)
            ctk.CTkLabel(r, text=f"💵 {p['local_payment_date']}: {p['amount']:,.0f}đ - {p['content']}").pack(pady=5)
    def handle_delete_member(self, member_id):
        """Xử lý khi bấm nút Xóa [cite: 2026-03-14]"""
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa vĩnh viễn hội viên này và mọi lịch sử liên quan không?"):
            from search_service import delete_member_logic
            success, msg = delete_member_logic(member_id)
            if success:
                messagebox.showinfo("Thành công", msg)
                for widget in self.detail_container.winfo_children():
                    widget.destroy()
                self.entry_search.delete(0, 'end')
            else:
                messagebox.showerror("Lỗi", msg)
                
                        
    def handle_search(self):
        """Xử lý nút bấm tìm kiếm [cite: 2026-03-04]"""
        query = self.entry_search.get().strip()
        if not query:
            messagebox.showwarning("Chú ý", "Vui lòng nhập thông tin tìm kiếm!")
            return

        search_type = "cccd" if query.isdigit() and len(query) == 12 else "name"
        success, results = search_member_logic(query, search_type)

        if success and results:
            self.display_member_full_profile(results[0])
        else:
            messagebox.showinfo("Thông báo", "Không tìm thấy hội viên nào!")

if __name__ == "__main__":
    app = GymManagementApp()
    app.mainloop()