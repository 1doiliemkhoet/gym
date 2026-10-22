import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
try:
    import winsound
except ImportError:  # Cho phép import ứng dụng trên nền tảng không có winsound
    winsound = None

import customtkinter as ctk

from add_member import save_member_to_db, check_cccd_match
from check_in_member import check_in_by_cccd_logic, get_today_checkin_history
from renew_member import renew_membership_logic
from revenue_stats import get_revenue_summary, get_detailed_revenue_stats
from export_excel import export_to_excel_logic
from search_service import (
    get_all_members_summary_logic,
    search_member_logic,
    update_member_status_logic,
    update_member_info_logic,
    delete_member_logic,
)
from mail_service import auto_check_and_send_reminders
from suggestion_service import get_checkin_suggestions
from body_metrics_service import (
    save_body_metrics,
    get_metrics_history,
    get_metrics_history_detailed,
    calculate_bmi_status,
)
from chart import show_peak_hours_chart


def resource_path(relative_path):
    """Lấy đường dẫn tuyệt đối đến tài nguyên, dùng được cả khi chạy dev và EXE"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ================= BẢNG MÀU MODERN CRIMSON DARK =================
COLORS = {
    "bg": "#0B0D11",           # Nền chính sâu
    "sidebar": "#12151C",      # Nền thanh điều hướng
    "card": "#181C24",         # Nền khung thẻ chính
    "card_inner": "#202530",   # Nền thẻ con / dòng dữ liệu
    "input_bg": "#11141A",     # Nền ô nhập liệu
    "border": "#2A303C",       # Viền mảnh tinh tế
    "accent": "#E11D48",       # Đỏ Crimson chủ đạo (TH Gym)
    "accent_hover": "#BE123C", # Đỏ khi di chuột
    "success": "#10B981",      # Xanh lá (Hoạt động / Lưu)
    "success_hover": "#059669",
    "warning": "#F59E0B",      # Cam vàng (Sắp hết hạn / Sửa)
    "warning_hover": "#D97706",
    "danger": "#EF4444",       # Đỏ cảnh báo (Hết hạn / Xóa)
    "danger_hover": "#DC2626",
    "info": "#3B82F6",         # Xanh dương (Thông tin / Lưu TT)
    "info_hover": "#2563EB",
    "purple": "#8B5CF6",       # Tím thống kê
    "text": "#F8FAFC",         # Chữ chính trắng sáng
    "subtext": "#94A3B8",      # Chữ phụ xám xanh
    "muted": "#64748B",        # Chữ mờ
}

# Mức mặc định được suy ra từ ví dụ hiện có trên giao diện (500.000đ đăng ký,
# 450.000đ gia hạn cho 1 tháng). Hãy chỉnh các mức này theo bảng giá thực tế của phòng gym.
# Người dùng vẫn có thể sửa trực tiếp số tiền trước khi lưu giao dịch.
REGISTRATION_PACKAGE_PRICES = {
    "1 tháng": 500_000,
    "3 tháng": 1_500_000,
    "6 tháng": 3_000_000,
    "12 tháng": 6_000_000,
}
RENEWAL_PACKAGE_PRICES = {
    "1 tháng": 450_000,
    "3 tháng": 1_350_000,
    "6 tháng": 2_700_000,
    "12 tháng": 5_400_000,
}

ctk.set_appearance_mode("dark")


class GymManagementApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.selected_cccd = None
        self.checkin_listbox = None
        self.current_suggestions_data = []
        self._suggestion_target_entry = None
        self._toast_frame = None
        self._toast_after_id = None
        self.quick_metrics_member_id = None
        self.member_list_members = []
        self.member_list_load_error = None
        self.nav_buttons = {}
        self.active_nav_key = None

        self.title("TH GYM — Hệ Thống Quản Lý Phòng Tập")
        self.geometry("1240x760")
        self.minsize(1080, 680)
        self.configure(fg_color=COLORS["bg"])

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

        # Đóng listbox gợi ý khi click ra ngoài
        self.bind("<Button-1>", self._on_global_click, add="+")

        # Chạy quét mail tự động (bỏ comment nếu cần bật lại)
        # threading.Thread(target=self.run_auto_mail_scan, daemon=True).start()

        self.navigate("register", self.show_registration)

    # ================= KHỞI TẠO KHUNG GIAO DIỆN =================

    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=255,
            corner_radius=0,
            fg_color=COLORS["sidebar"],
            border_width=1,
            border_color=COLORS["border"],
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # Brand Header
        brand_box = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_box.pack(fill="x", padx=22, pady=(28, 20))

        logo_row = ctk.CTkFrame(brand_box, fg_color="transparent")
        logo_row.pack(anchor="w")

        badge_icon = ctk.CTkFrame(
            logo_row, width=36, height=36, corner_radius=8, fg_color=COLORS["accent"]
        )
        badge_icon.pack(side="left", padx=(0, 10))
        badge_icon.pack_propagate(False)
        ctk.CTkLabel(
            badge_icon,
            text="TH",
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            text_color="#FFFFFF",
        ).place(relx=0.5, rely=0.5, anchor="center")

        title_col = ctk.CTkFrame(logo_row, fg_color="transparent")
        title_col.pack(side="left")
        self.logo_label = ctk.CTkLabel(
            title_col,
            text="TH GYM",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=COLORS["text"],
        )
        self.logo_label.pack(anchor="w")
        ctk.CTkLabel(
            title_col,
            text="MANAGEMENT PRO",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w")

        # Đường kẻ phân cách
        ctk.CTkFrame(self.sidebar_frame, height=1, fg_color=COLORS["border"]).pack(
            fill="x", padx=18, pady=(0, 12)
        )

        # Nhóm 1: Vận hành
        self._create_sidebar_section("VẬN HÀNH QUẦY")
        self.create_menu_button("➕  Đăng ký Hội viên", self.show_registration, key="register")
        self.create_menu_button("✅  Check-in CCCD", self.show_checkin, key="checkin")
        self.create_menu_button("💳  Gia hạn Gói tập", self.show_renew, key="renew")

        # Nhóm 2: Hội viên & Sức khỏe
        self._create_sidebar_section("HỘI VIÊN & HỒ SƠ")
        self.create_menu_button("🔍  Tìm kiếm Hội viên", self.show_search_screen, key="search")
        self.create_menu_button("⚖️  Theo dõi Sức khỏe", self.show_metrics_screen, key="metrics")
        self.create_menu_button("👥  Danh sách Hội viên", self.show_member_list, key="list")

        # Nhóm 3: Quản trị
        self._create_sidebar_section("PHÂN TÍCH & BÁO CÁO")
        self.create_menu_button("📊  Báo cáo Doanh thu", self.show_dashboard, key="dashboard")
        self.create_menu_button("📈  Biểu đồ Giờ khách", show_peak_hours_chart, key="chart")

    def _create_sidebar_section(self, title):
        ctk.CTkLabel(
            self.sidebar_frame,
            text=title,
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            text_color=COLORS["muted"],
        ).pack(anchor="w", padx=24, pady=(10, 4))

    def create_menu_button(self, text, command, key=None):
        def on_click():
            if key and key != "chart":
                self.navigate(key, command)
            else:
                command()

        btn = ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            fg_color="transparent",
            text_color=COLORS["subtext"],
            hover_color=COLORS["card_inner"],
            anchor="w",
            height=42,
            corner_radius=10,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=on_click,
        )
        btn.pack(pady=3, padx=14, fill="x")
        if key:
            self.nav_buttons[key] = btn
        return btn

    def navigate(self, key, callback):
        self.active_nav_key = key
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=COLORS["accent"], text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["subtext"])
        callback()

    def _build_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=28, pady=24)

    # ================= HELPER & LOGIC HỆ THỐNG =================

    def run_auto_mail_scan(self):
        try:
            result = auto_check_and_send_reminders()
            print(f"[Hệ thống] {result}")
        except Exception as e:
            print(f"[Lỗi Auto Mail] {e}")

    def clear_main_frame(self):
        self.hide_checkin_suggestions()
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def render_title(self, text, subtitle=None):
        header_box = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_box.pack(fill="x", pady=(0, 18))

        ctk.CTkLabel(
            header_box,
            text=text,
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                header_box,
                text=subtitle,
                font=ctk.CTkFont(family="Inter", size=12),
                text_color=COLORS["subtext"],
            ).pack(anchor="w", pady=(2, 0))

    def create_input(self, parent, placeholder, width=360, height=42):
        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            width=width,
            height=height,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["muted"],
            font=ctk.CTkFont(family="Inter", size=13),
        )
        entry.pack(pady=8)
        return entry

    def _create_labeled_field(self, parent, row, col, label_text, placeholder, width=320):
        """Tạo trường nhập liệu có nhãn phía trên cho bố cục Grid 2 cột"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.grid(row=row, column=col, padx=16, pady=8, sticky="ew")

        ctk.CTkLabel(
            field_frame,
            text=label_text,
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", pady=(0, 5))

        entry = ctk.CTkEntry(
            field_frame,
            placeholder_text=placeholder,
            width=width,
            height=42,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["muted"],
            font=ctk.CTkFont(family="Inter", size=13),
        )
        entry.pack(fill="x")
        return entry

    def _bind_suggestion_keys(self, widget):
        """Cho phép chọn gợi ý bằng bàn phím trên mọi ô tìm hội viên."""
        widget.bind("<Down>", self.focus_checkin_suggestion)
        widget.bind("<Return>", self.handle_suggestion_entry_return)

    def focus_checkin_suggestion(self, event):
        """Chuyển focus vào listbox gợi ý khi người dùng nhấn mũi tên xuống."""
        if self.checkin_listbox and self._suggestion_target_entry is event.widget:
            if not self.checkin_listbox.curselection() and self.current_suggestions_data:
                self.checkin_listbox.selection_set(0)
                self.checkin_listbox.activate(0)
                self.checkin_listbox.see(0)
            self.checkin_listbox.focus_set()
            return "break"
        return None

    def handle_suggestion_entry_return(self, event):
        """Enter chọn gợi ý đang mở; nếu không có gợi ý thì thực hiện hành động của màn hình."""
        if self.checkin_listbox and self._suggestion_target_entry is event.widget:
            return self.commit_checkin_suggestion()
        if event.widget is getattr(self, "entry_cccd_check", None):
            self.handle_checkin()
        elif event.widget is getattr(self, "entry_search", None):
            self.handle_search()
        elif event.widget is getattr(self, "entry_cccd_renew", None):
            self.entry_renew_price.focus_set()
        elif event.widget is getattr(self, "entry_member_search", None):
            self.entry_h.focus_set()
        return "break"

    def commit_checkin_suggestion(self, event=None):
        """Chốt mục đang chọn; nếu chưa chọn thì dùng mục đầu tiên."""
        if not self.checkin_listbox or not self.current_suggestions_data:
            return "break"
        selection = self.checkin_listbox.curselection()
        if selection:
            index = selection[0]
        else:
            try:
                index = int(self.checkin_listbox.index(tk.ACTIVE))
            except (tk.TclError, ValueError):
                index = 0
            if index < 0 or index >= len(self.current_suggestions_data):
                index = 0
            self.checkin_listbox.selection_set(index)
        target_entry = self._suggestion_target_entry
        if target_entry is not None:
            self.select_checkin_suggestion(target_entry)
        return "break"

    def dismiss_checkin_suggestions(self, event=None):
        target_entry = self._suggestion_target_entry
        self.hide_checkin_suggestions()
        if target_entry is not None and target_entry.winfo_exists():
            target_entry.focus_set()
        return "break"

    def _bind_currency_format(self, entry):
        entry.bind("<KeyRelease>", lambda event: self.format_currency_entry(event.widget), add="+")
        entry.bind("<FocusOut>", lambda event: self.format_currency_entry(event.widget), add="+")

    def format_currency_entry(self, widget):
        """Format số tiền bằng dấu phẩy và giữ vị trí con trỏ tương đối theo chữ số."""
        raw = widget.get()
        try:
            cursor = widget.index(tk.INSERT)
        except Exception:
            cursor = len(raw)
        digits_before_cursor = sum(char.isdigit() for char in raw[:cursor])
        digits = "".join(char for char in raw if char.isdigit())
        formatted = f"{int(digits):,}" if digits else ""
        if formatted == raw:
            return
        widget.delete(0, tk.END)
        if formatted:
            widget.insert(0, formatted)
        cursor_target = 0
        digits_seen = 0
        while cursor_target < len(formatted) and digits_seen < digits_before_cursor:
            if formatted[cursor_target].isdigit():
                digits_seen += 1
            cursor_target += 1
        widget.icursor(cursor_target)

    def _set_currency_entry(self, widget, amount):
        widget.delete(0, tk.END)
        widget.insert(0, f"{int(amount):,}")

    def update_registration_price(self, package):
        if hasattr(self, "entry_price") and self.entry_price.winfo_exists():
            amount = REGISTRATION_PACKAGE_PRICES.get(package)
            if amount is not None:
                self._set_currency_entry(self.entry_price, amount)

    def update_renewal_price(self, package):
        if hasattr(self, "entry_renew_price") and self.entry_renew_price.winfo_exists():
            amount = RENEWAL_PACKAGE_PRICES.get(package)
            if amount is not None:
                self._set_currency_entry(self.entry_renew_price, amount)

    def show_toast(self, message, success=True, beep=False):
        """Banner không chặn luồng thao tác, tự đóng sau 2,5 giây."""
        if self._toast_after_id is not None:
            try:
                self.after_cancel(self._toast_after_id)
            except Exception:
                pass
            self._toast_after_id = None
        if self._toast_frame is not None:
            try:
                self._toast_frame.destroy()
            except Exception:
                pass
            self._toast_frame = None

        background = COLORS["success"] if success else COLORS["danger"]
        icon = "✓" if success else "!"
        toast = ctk.CTkFrame(self, fg_color=background, corner_radius=10)
        ctk.CTkLabel(
            toast,
            text=f"{icon}  {message}",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            wraplength=430,
            justify="left",
        ).pack(padx=18, pady=12)
        toast.place(relx=0.985, y=18, anchor="ne")
        toast.lift()
        self._toast_frame = toast

        if beep and winsound is not None:
            try:
                sound_type = getattr(winsound, "MB_OK", 0) if success else getattr(winsound, "MB_ICONHAND", 0x10)
                winsound.MessageBeep(sound_type)
            except Exception:
                pass
        self._toast_after_id = self.after(2500, self._dismiss_toast)

    def _dismiss_toast(self):
        if self._toast_frame is not None:
            try:
                self._toast_frame.destroy()
            except Exception:
                pass
        self._toast_frame = None
        self._toast_after_id = None

    def _on_global_click(self, event):
        if self.checkin_listbox and event.widget != self.checkin_listbox:
            self.hide_checkin_suggestions()

    def on_checkin_typing(self, event):
        """Xử lý gợi ý linh hoạt (Tên + SĐT)"""
        widget = event.widget
        typed = widget.get().strip()

        self.current_suggestions_data = get_checkin_suggestions(typed)
        self.selected_cccd = None  # Reset khi gõ mới
        if widget is getattr(self, "entry_member_search", None):
            self.quick_metrics_member_id = None

        if not self.current_suggestions_data:
            self.hide_checkin_suggestions()
            return

        self.hide_checkin_suggestions()
        self._suggestion_target_entry = widget
        self.checkin_listbox = tk.Listbox(
            self,
            font=("Inter", 11),
            bg=COLORS["card_inner"],
            fg=COLORS["text"],
            selectbackground=COLORS["accent"],
            selectforeground="#FFFFFF",
            activestyle="none",
            borderwidth=1,
            relief="solid",
            highlightthickness=0,
        )

        for item in self.current_suggestions_data:
            self.checkin_listbox.insert(tk.END, f"  {item['display']}")

        x_pos = widget.winfo_rootx() - self.winfo_rootx()
        y_pos = widget.winfo_rooty() - self.winfo_rooty() + widget.winfo_height() + 2

        row_count = min(len(self.current_suggestions_data), 5)
        box_height = max(row_count * 26 + 8, 60)

        self.checkin_listbox.place(
            x=x_pos, y=y_pos, width=widget.winfo_width(), height=box_height
        )
        self.checkin_listbox.lift()
        self.checkin_listbox.bind(
            "<ButtonRelease-1>",
            lambda e, target=widget: self.after_idle(lambda: self.select_checkin_suggestion(target)),
        )
        self.checkin_listbox.bind("<Return>", self.commit_checkin_suggestion)
        self.checkin_listbox.bind("<Escape>", self.dismiss_checkin_suggestions)

    def select_checkin_suggestion(self, target_entry):
        """Tách tên chuẩn xác sau khi thay đổi định dạng hiển thị"""
        if not target_entry.winfo_exists() or not self.checkin_listbox:
            self.hide_checkin_suggestions()
            return

        selection = self.checkin_listbox.curselection()
        if selection:
            idx = selection[0]
            selected_item = self.current_suggestions_data[idx]

            display_text = selected_item["display"]
            clean_name = (
                display_text.split(" - SĐT:")[0].strip()
                if " - SĐT:" in display_text
                else display_text
            )

            target_entry.delete(0, tk.END)
            target_entry.insert(0, clean_name)

            self.selected_cccd = selected_item["real_value"]
            self.hide_checkin_suggestions()

            if (
                hasattr(self, "metrics_history_frame")
                and self.metrics_history_frame.winfo_exists()
            ):
                success, data = search_member_logic(clean_name, "name")
                if success and data:
                    self.refresh_metrics_history(data[0]["id"])

    def hide_checkin_suggestions(self):
        if self.checkin_listbox:
            try:
                self.checkin_listbox.place_forget()
                self.checkin_listbox.destroy()
            except Exception:
                pass
            self.checkin_listbox = None
        self._suggestion_target_entry = None

    # ================= 1. MÀN HÌNH ĐĂNG KÝ HỘI VIÊN =================

    def show_registration(self):
        self.clear_main_frame()
        self.render_title(
            "ĐĂNG KÝ HỘI VIÊN MỚI",
            "Nhập thông tin cá nhân và gói tập để khởi tạo hồ sơ hội viên",
        )

        card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(fill="both", expand=True)

        form_grid = ctk.CTkFrame(card, fg_color="transparent")
        form_grid.pack(fill="x", padx=24, pady=(24, 10))
        form_grid.grid_columnconfigure((0, 1), weight=1)

        # Hàng 0: Họ tên & CCCD
        self.entry_name = self._create_labeled_field(
            form_grid, 0, 0, "👤 Họ và tên khách hàng *", "Ví dụ: Nguyễn Văn An"
        )
        self.entry_cccd = self._create_labeled_field(
            form_grid, 0, 1, "🪪 Số CCCD (12 chữ số) *", "Nhập 12 số căn cước công dân"
        )

        # Hàng 1: Giới tính & Ngày sinh
        gender_box = ctk.CTkFrame(form_grid, fg_color="transparent")
        gender_box.grid(row=1, column=0, padx=16, pady=8, sticky="ew")
        ctk.CTkLabel(
            gender_box,
            text="⚧ Giới tính",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", pady=(0, 5))
        self.gender_var = ctk.StringVar(value="Nam")
        ctk.CTkComboBox(
            gender_box,
            values=["Nam", "Nữ", "Khác"],
            variable=self.gender_var,
            height=42,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
            button_color=COLORS["border"],
            dropdown_fg_color=COLORS["card_inner"],
        ).pack(fill="x")

        self.entry_dob = self._create_labeled_field(
            form_grid, 1, 1, "🎂 Ngày sinh (DD-MM-YYYY) *", "Ví dụ: 25-01-2000"
        )

        # Hàng 2: SĐT & Email
        self.entry_phone = self._create_labeled_field(
            form_grid, 2, 0, "📞 Số điện thoại *", "Ví dụ: 0912345678"
        )
        self.entry_email = self._create_labeled_field(
            form_grid, 2, 1, "📧 Địa chỉ Gmail", "Ví dụ: example@gmail.com"
        )

        # Hàng 3: Gói tập & Giá tiền
        pkg_box = ctk.CTkFrame(form_grid, fg_color="transparent")
        pkg_box.grid(row=3, column=0, padx=16, pady=8, sticky="ew")
        ctk.CTkLabel(
            pkg_box,
            text="📦 Thời hạn gói tập *",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", pady=(0, 5))
        self.package_var = ctk.StringVar(value="1 tháng")
        ctk.CTkComboBox(
            pkg_box,
            values=["1 tháng", "3 tháng", "6 tháng", "12 tháng"],
            variable=self.package_var,
            height=42,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
            button_color=COLORS["border"],
            dropdown_fg_color=COLORS["card_inner"],
            command=self.update_registration_price,
        ).pack(fill="x")

        self.entry_price = self._create_labeled_field(
            form_grid, 3, 1, "💰 Giá tiền thanh toán (VNĐ) *", "Ví dụ: 500000"
        )
        self._bind_currency_format(self.entry_price)
        self.update_registration_price(self.package_var.get())

        # Nút xác nhận
        action_bar = ctk.CTkFrame(card, fg_color="transparent")
        action_bar.pack(fill="x", padx=40, pady=(20, 28))

        ctk.CTkButton(
            action_bar,
            text="✓  XÁC NHẬN & LƯU HỘI VIÊN",
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            height=46,
            corner_radius=10,
            command=self.handle_registration,
        ).pack(fill="x")

    def handle_registration(self):
        name = self.entry_name.get()
        cccd = self.entry_cccd.get()
        phone = self.entry_phone.get()
        email = self.entry_email.get()
        package = self.package_var.get()
        gender = self.gender_var.get()
        dob = self.entry_dob.get()
        price_str = self.entry_price.get()

        is_valid, warning_msg = check_cccd_match(cccd, gender, dob)

        if not is_valid:
            confirm = messagebox.askyesno(
                "Phát hiện nghi vấn",
                f"⚠️ NGHI NGỜ CCCD GIẢ HOẶC SAI THÔNG TIN:\n\n{warning_msg}\n\nBạn vẫn muốn bỏ qua cảnh báo và tiếp tục lưu?",
            )
            if not confirm:
                return

        try:
            price = float(price_str.replace(",", "").strip())
            success, msg = save_member_to_db(
                name, cccd, phone, email, package, gender, dob, price
            )

            if success:
                messagebox.showinfo(
                    "Thành công", f"Hội viên đã được lưu!\nHạn dùng: {msg}"
                )
            else:
                messagebox.showerror("Lỗi", msg)
        except ValueError:
            messagebox.showerror("Lỗi", "Giá tiền không hợp lệ!")

    # ================= 2. MÀN HÌNH CHECK-IN CCCD =================

    def show_checkin(self):
        self.clear_main_frame()
        self.render_title(
            "XÁC THỰC RA VÀO (CHECK-IN)",
            "Tra cứu nhanh bằng tên, SĐT hoặc quét mã CCCD để ghi nhận lượt tập",
        )

        input_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        input_card.pack(fill="x", pady=(0, 18))

        search_row = ctk.CTkFrame(input_card, fg_color="transparent")
        search_row.pack(fill="x", padx=24, pady=20)

        self.entry_cccd_check = ctk.CTkEntry(
            search_row,
            placeholder_text="🔍 Nhập tên hội viên, SĐT hoặc quét mã CCCD...",
            height=46,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Inter", size=14),
        )
        self.entry_cccd_check.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.entry_cccd_check.bind("<KeyRelease>", self.on_checkin_typing)
        self._bind_suggestion_keys(self.entry_cccd_check)

        ctk.CTkButton(
            search_row,
            text="XÁC NHẬN VÀO TẬP",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            width=200,
            height=46,
            corner_radius=10,
            command=self.handle_checkin,
        ).pack(side="right")

        # Tiêu đề lịch sử trong ngày
        hist_header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        hist_header.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            hist_header,
            text="🕒 LỊCH SỬ CHECK-IN HÔM NAY",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(side="left")

        self.history_frame = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.history_frame.pack(fill="both", expand=True)
        self.refresh_checkin_history()

    def handle_checkin(self):
        """Chỉ chạy một lần duy nhất trong Thread"""
        cccd_input = (
            self.selected_cccd
            if self.selected_cccd
            else self.entry_cccd_check.get().strip()
        )
        if not cccd_input:
            return

        def task():
            success, msg = check_in_by_cccd_logic(cccd_input)
            self.selected_cccd = None
            self.after(0, lambda: self.finish_checkin(success, msg))

        threading.Thread(target=task, daemon=True).start()

    def finish_checkin(self, success, msg):
        self.show_toast(msg, success=success, beep=True)
        if success:
            self.entry_cccd_check.delete(0, "end")
            self.entry_cccd_check.focus_set()
            self.refresh_checkin_history()

    def refresh_checkin_history(self):
        for widget in self.history_frame.winfo_children():
            widget.destroy()

        history = get_today_checkin_history()

        if not history:
            ctk.CTkLabel(
                self.history_frame,
                text="Chưa có hội viên nào check-in hôm nay",
                text_color=COLORS["muted"],
                font=ctk.CTkFont(family="Inter", size=13, slant="italic"),
            ).pack(pady=40)
            return

        for entry in history:
            row = ctk.CTkFrame(
                self.history_frame,
                fg_color=COLORS["card_inner"],
                corner_radius=10,
                height=48,
            )
            row.pack(fill="x", pady=4, padx=10)
            row.pack_propagate(False)

            time_frame = ctk.CTkFrame(row, fg_color="transparent", width=95)
            time_frame.pack(side="left", fill="y")
            time_frame.pack_propagate(False)

            short_time = entry["time"][:5] if entry["time"] else ""
            ctk.CTkLabel(
                time_frame,
                text=f"🕒 {short_time}",
                text_color=COLORS["info"],
                font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            ).pack(side="left", padx=12, pady=10)

            ctk.CTkLabel(
                row,
                text=f"👤  {entry['name']}",
                text_color=COLORS["text"],
                font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            ).pack(side="left", padx=8, pady=10)

            days = entry["days_left"]
            if days < 0:
                text_days = "Hết hạn"
                color_bg = COLORS["danger"]
                color_text = "#FFFFFF"
            elif days <= 7:
                text_days = f"Còn {days} ngày"
                color_bg = COLORS["warning"]
                color_text = "#000000"
            else:
                text_days = f"Còn {days} ngày"
                color_bg = COLORS["success"]
                color_text = "#FFFFFF"

            badge = ctk.CTkFrame(
                row, fg_color=color_bg, corner_radius=14, height=28, width=105
            )
            badge.pack(side="right", padx=12, pady=10)
            badge.pack_propagate(False)

            ctk.CTkLabel(
                badge,
                text=text_days,
                text_color=color_text,
                font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            ).place(relx=0.5, rely=0.5, anchor="center")

    # ================= 3. MÀN HÌNH GIA HẠN GÓI TẬP =================

    def show_renew(self):
        self.clear_main_frame()
        self.render_title(
            "GIA HẠN GÓI TẬP",
            "Tìm kiếm hội viên hiện tại và cộng thêm thời hạn gói tập mới",
        )

        card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(fill="x", pady=6)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=32, pady=28)

        ctk.CTkLabel(
            inner,
            text="🔍 Tìm hội viên cần gia hạn (Tên, SĐT hoặc CCCD) *",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", pady=(0, 6))

        self.entry_cccd_renew = ctk.CTkEntry(
            inner,
            placeholder_text="Gõ tên/SĐT để chọn gợi ý hoặc dùng CCCD từ hồ sơ...",
            height=44,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
            font=ctk.CTkFont(family="Inter", size=13),
        )
        self.entry_cccd_renew.pack(fill="x", pady=(0, 16))
        self.entry_cccd_renew.bind("<KeyRelease>", self.on_checkin_typing)
        self._bind_suggestion_keys(self.entry_cccd_renew)

        row_split = ctk.CTkFrame(inner, fg_color="transparent")
        row_split.pack(fill="x", pady=(0, 20))
        row_split.grid_columnconfigure((0, 1), weight=1)

        # Cột trái: Số tháng
        col_left = ctk.CTkFrame(row_split, fg_color="transparent")
        col_left.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkLabel(
            col_left,
            text="📅 Gói thời gian gia hạn *",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", pady=(0, 6))
        self.renew_month_var = ctk.StringVar(value="1 tháng")
        ctk.CTkComboBox(
            col_left,
            values=["1 tháng", "3 tháng", "6 tháng", "12 tháng"],
            variable=self.renew_month_var,
            height=44,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
            button_color=COLORS["border"],
            dropdown_fg_color=COLORS["card_inner"],
            command=self.update_renewal_price,
        ).pack(fill="x")

        # Cột phải: Số tiền
        col_right = ctk.CTkFrame(row_split, fg_color="transparent")
        col_right.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        ctk.CTkLabel(
            col_right,
            text="💰 Phí gia hạn thanh toán (VNĐ) *",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", pady=(0, 6))
        self.entry_renew_price = ctk.CTkEntry(
            col_right,
            placeholder_text="Ví dụ: 450000",
            height=44,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
            font=ctk.CTkFont(family="Inter", size=13),
        )
        self.entry_renew_price.pack(fill="x")
        self._bind_currency_format(self.entry_renew_price)
        self.update_renewal_price(self.renew_month_var.get())

        ctk.CTkButton(
            inner,
            text="💳  XÁC NHẬN GIA HẠN",
            fg_color=COLORS["warning"],
            hover_color=COLORS["warning_hover"],
            text_color="#000000",
            height=46,
            corner_radius=10,
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            command=self.handle_renew,
        ).pack(fill="x", pady=(6, 0))

    def handle_renew(self):
        cccd = (
            self.selected_cccd
            if self.selected_cccd
            else self.entry_cccd_renew.get().strip()
        )
        price_str = self.entry_renew_price.get().strip()

        if not cccd or not price_str:
            messagebox.showwarning(
                "Chú ý", "Vui lòng chọn hội viên và nhập giá tiền!"
            )
            return

        def task():
            try:
                months = int(self.renew_month_var.get().split()[0])
                amount = float(price_str.replace(",", "").strip())

                success, msg = renew_membership_logic(cccd, months, amount)

                self.after(0, lambda: messagebox.showinfo("Kết quả", msg))
                if success:
                    self.after(0, lambda: self.entry_cccd_renew.delete(0, "end"))
                    self.after(0, lambda: self.update_renewal_price(self.renew_month_var.get()))
                    self.selected_cccd = None
            except ValueError:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Lỗi", "Số tiền không hợp lệ. Chỉ nhập chữ số; dấu phẩy phân tách hàng nghìn được hỗ trợ."
                    ),
                )
            except Exception as e:
                loi_thuc_te = str(e)
                self.after(0, lambda msg=loi_thuc_te: messagebox.showerror("Lỗi", msg))

        threading.Thread(target=task, daemon=True).start()

    # ================= 4. MÀN HÌNH TÌM KIẾM & HỒ SƠ HỘI VIÊN =================

    def show_search_screen(self):
        self.clear_main_frame()
        self.render_title(
            "TÌM KIẾM & HỒ SƠ HỘI VIÊN",
            "Tra cứu toàn bộ lịch sử tập luyện, chỉ số BMI, thanh toán và chỉnh sửa thông tin",
        )

        search_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        search_card.pack(fill="x", pady=(0, 16))

        bar = ctk.CTkFrame(search_card, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=16)

        self.entry_search = ctk.CTkEntry(
            bar,
            placeholder_text="🔍 Nhập tên hội viên, số điện thoại hoặc CCCD 12 số...",
            height=44,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
            font=ctk.CTkFont(family="Inter", size=13),
        )
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.entry_search.bind("<KeyRelease>", self.on_checkin_typing)
        self._bind_suggestion_keys(self.entry_search)

        ctk.CTkButton(
            bar,
            text="TRA CỨU HỒ SƠ",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            width=160,
            height=44,
            corner_radius=10,
            command=self.handle_search,
        ).pack(side="right")

        self.detail_container = ctk.CTkScrollableFrame(
            self.main_frame, fg_color="transparent", height=520
        )
        self.detail_container.pack(fill="both", expand=True)

    def handle_search(self):
        if self.selected_cccd:
            query = self.selected_cccd
            search_type = "cccd"
        else:
            query = self.entry_search.get().strip()
            search_type = "cccd" if query.isdigit() and len(query) == 12 else "name"

        if not query:
            messagebox.showwarning("Chú ý", "Vui lòng nhập thông tin tìm kiếm!")
            return

        success, results = search_member_logic(query, search_type)

        if success and results:
            self.display_member_full_profile(results[0])
            self.selected_cccd = None
        else:
            messagebox.showinfo("Thông báo", "Không tìm thấy hội viên nào!")

    def handle_update_status(self, member_id):
        new_status = self.status_var.get()
        if messagebox.askyesno(
            "Xác nhận", f"Bạn có chắc muốn đổi trạng thái sang {new_status}?"
        ):
            success, msg = update_member_status_logic(member_id, new_status)
            if success:
                messagebox.showinfo("Thành công", msg)
            else:
                messagebox.showerror("Lỗi", msg)

    def display_member_full_profile(self, member_data):
        """Hiển thị hồ sơ hội viên đầy đủ kèm các nút thao tác"""
        for widget in self.detail_container.winfo_children():
            widget.destroy()

        # Header Card của Hội viên
        header = ctk.CTkFrame(
            self.detail_container,
            fg_color=COLORS["card"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
        )
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header,
            text=f"👤  {member_data['ho_ten']}",
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color=COLORS["text"],
        ).pack(side="left", padx=20, pady=18)

        ctk.CTkButton(
            header,
            text="🗑 XÓA",
            width=80,
            height=34,
            corner_radius=8,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            command=lambda: self.handle_delete_member(member_data["id"]),
        ).pack(side="right", padx=(6, 16))

        ctk.CTkButton(
            header,
            text="✏️ SỬA THÔNG TIN",
            width=125,
            height=34,
            corner_radius=8,
            fg_color=COLORS["warning"],
            hover_color=COLORS["warning_hover"],
            text_color="#000000",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            command=lambda: self.open_edit_dialog(member_data),
        ).pack(side="right", padx=6)

        ctk.CTkButton(
            header,
            text="💾 LƯU TRẠNG THÁI",
            width=125,
            height=34,
            corner_radius=8,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            command=lambda: self.handle_update_status(member_data["id"]),
        ).pack(side="right", padx=6)

        self.status_var = ctk.StringVar(value=member_data["trang_thai"])
        status_cb = ctk.CTkComboBox(
            header,
            values=["Active", "Inactive", "Locked"],
            variable=self.status_var,
            width=115,
            height=34,
            corner_radius=8,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
        )
        status_cb.pack(side="right", padx=6)

        quick_actions = ctk.CTkFrame(self.detail_container, fg_color="transparent")
        quick_actions.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(
            quick_actions,
            text="💳 GIA HẠN NHANH",
            width=155,
            height=38,
            corner_radius=9,
            fg_color=COLORS["warning"],
            hover_color=COLORS["warning_hover"],
            text_color="#000000",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=lambda data=member_data: self.quick_renew_member(data),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            quick_actions,
            text="⚖️ ĐO BMI",
            width=125,
            height=38,
            corner_radius=9,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=lambda data=member_data: self.quick_measure_bmi(data),
        ).pack(side="left")

        # Tabview chi tiết
        tabview = ctk.CTkTabview(
            self.detail_container,
            height=420,
            fg_color=COLORS["card"],
            segmented_button_fg_color=COLORS["input_bg"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["input_bg"],
            corner_radius=14,
        )
        tabview.pack(fill="both", expand=True)

        t_info = tabview.add("ℹ️ Thông tin")
        t_checkin = tabview.add("🕒 Check-in")
        t_health = tabview.add("⚖️ Sức khỏe")
        t_payment = tabview.add("💰 Thanh toán")

        # Tab 1: Thông tin dạng lưới thẻ 2x2
        info_grid = ctk.CTkFrame(t_info, fg_color="transparent")
        info_grid.pack(fill="x", padx=16, pady=16)
        info_grid.grid_columnconfigure((0, 1), weight=1)

        info_fields = [
            ("🆔 Số CCCD", member_data.get("cccd", "N/A")),
            ("📞 Số điện thoại", member_data.get("so_dien_thoai", "N/A")),
            ("📧 Địa chỉ Email", member_data.get("email", "Chưa cập nhật")),
            ("📅 Ngày hết hạn", member_data.get("ngay_het_han", "N/A")),
        ]
        for idx, (lbl, val) in enumerate(info_fields):
            r_idx, c_idx = divmod(idx, 2)
            box = ctk.CTkFrame(
                info_grid, fg_color=COLORS["card_inner"], corner_radius=10
            )
            box.grid(row=r_idx, column=c_idx, padx=8, pady=8, sticky="ew")
            ctk.CTkLabel(
                box,
                text=lbl,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=COLORS["subtext"],
            ).pack(anchor="w", padx=16, pady=(12, 2))
            ctk.CTkLabel(
                box,
                text=str(val),
                font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                text_color=COLORS["text"],
            ).pack(anchor="w", padx=16, pady=(0, 12))

        # Tab 2: Lịch sử Check-in
        for time_str in member_data.get("all_checkins", [])[:10]:
            r = ctk.CTkFrame(
                t_checkin, fg_color=COLORS["card_inner"], corner_radius=8
            )
            r.pack(fill="x", pady=3, padx=12)
            ctk.CTkLabel(
                r,
                text=f"✅  Vào tập lúc: {time_str}",
                font=ctk.CTkFont(family="Inter", size=13),
            ).pack(side="left", padx=14, pady=8)

        # Tab 3: Lịch sử Sức khỏe
        for m in member_data.get("all_metrics", []):
            r = ctk.CTkFrame(
                t_health, fg_color=COLORS["card_inner"], corner_radius=8
            )
            r.pack(fill="x", pady=3, padx=12)
            date_lbl = m.get("local_date") or m.get("ngay_ghi_nhan", "")
            ctk.CTkLabel(
                r,
                text=f"📅 {date_lbl}   |   Cao: {m.get('chieu_cao', '--')}cm   •   Nặng: {m['can_nang']}kg   •   BMI: {m['bmi']}",
                font=ctk.CTkFont(family="Inter", size=13),
            ).pack(side="left", padx=14, pady=8)

        # Tab 4: Lịch sử Thanh toán
        for p in member_data.get("all_payments", []):
            r = ctk.CTkFrame(
                t_payment, fg_color=COLORS["card_inner"], corner_radius=8
            )
            r.pack(fill="x", pady=3, padx=12)
            pay_date = p.get("local_payment_date") or p.get("payment_date", "")
            ctk.CTkLabel(
                r,
                text=f"💵 {pay_date}: {p['amount']:,.0f}đ — {p['content']}",
                font=ctk.CTkFont(family="Inter", size=13),
                text_color=COLORS["success"],
            ).pack(side="left", padx=14, pady=8)

    def quick_renew_member(self, member_data):
        """Mở màn gia hạn và điền sẵn CCCD của hội viên đang xem."""
        cccd = str(member_data.get("cccd") or "").strip()
        if not cccd or cccd == "N/A":
            messagebox.showwarning("Thiếu CCCD", "Hồ sơ này chưa có CCCD để tự điền gia hạn.")
            return
        self.navigate("renew", self.show_renew)
        self.entry_cccd_renew.delete(0, tk.END)
        self.entry_cccd_renew.insert(0, cccd)
        self.selected_cccd = cccd
        self.entry_renew_price.focus_set()

    def quick_measure_bmi(self, member_data):
        """Mở màn BMI, chọn sẵn đúng member_id để tránh trùng tên."""
        self.navigate("metrics", self.show_metrics_screen)
        self.entry_member_search.delete(0, tk.END)
        self.entry_member_search.insert(0, member_data.get("ho_ten", ""))
        self.quick_metrics_member_id = member_data.get("id")
        self.refresh_metrics_history(self.quick_metrics_member_id)
        self.entry_h.focus_set()

    def open_edit_dialog(self, member_data):
        """Mở cửa sổ popup để sửa đổi thông tin cơ bản"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Chỉnh sửa Hội viên")
        dialog.geometry("460x400")
        dialog.configure(fg_color=COLORS["card"])
        dialog.attributes("-topmost", True)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="✏️ CHỈNH SỬA HỒ SƠ",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            dialog,
            text="Họ và tên khách hàng:",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(pady=(10, 4), anchor="w", padx=40)
        entry_name = ctk.CTkEntry(
            dialog, width=380, height=38, fg_color=COLORS["input_bg"]
        )
        entry_name.insert(0, member_data["ho_ten"])
        entry_name.pack()

        ctk.CTkLabel(
            dialog,
            text="Số điện thoại:",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(pady=(12, 4), anchor="w", padx=40)
        entry_phone = ctk.CTkEntry(
            dialog, width=380, height=38, fg_color=COLORS["input_bg"]
        )
        entry_phone.insert(0, member_data["so_dien_thoai"])
        entry_phone.pack()

        ctk.CTkLabel(
            dialog,
            text="Ngày hết hạn (YYYY-MM-DD):",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(pady=(12, 4), anchor="w", padx=40)
        entry_expiry = ctk.CTkEntry(
            dialog, width=380, height=38, fg_color=COLORS["input_bg"]
        )
        entry_expiry.insert(0, member_data["ngay_het_han"])
        entry_expiry.pack()

        def save_changes():
            new_name = entry_name.get().strip()
            new_phone = entry_phone.get().strip()
            new_expiry = entry_expiry.get().strip()

            if not new_name or not new_phone or not new_expiry:
                messagebox.showwarning("Lỗi", "Không được để trống thông tin!")
                return

            success, msg = update_member_info_logic(
                member_data["id"], new_name, new_phone, new_expiry
            )
            if success:
                messagebox.showinfo("Thành công", msg)
                dialog.destroy()
                self.selected_cccd = member_data["cccd"]
                self.handle_search()
            else:
                messagebox.showerror("Lỗi", msg)

        ctk.CTkButton(
            dialog,
            text="✓ LƯU THAY ĐỔI",
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            height=42,
            width=380,
            corner_radius=10,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=save_changes,
        ).pack(pady=24)

    def handle_delete_member(self, member_id):
        if messagebox.askyesno(
            "Xác nhận",
            "Bạn có chắc chắn muốn xóa vĩnh viễn hội viên này và mọi lịch sử liên quan không?",
        ):
            success, msg = delete_member_logic(member_id)
            if success:
                messagebox.showinfo("Thành công", msg)
                for widget in self.detail_container.winfo_children():
                    widget.destroy()
                self.entry_search.delete(0, "end")
                self.selected_cccd = None
            else:
                messagebox.showerror("Lỗi", msg)

    # ================= 5. MÀN HÌNH THEO DÕI SỨC KHỎE =================

    def show_metrics_screen(self):
        self.quick_metrics_member_id = None
        self.clear_main_frame()
        self.render_title(
            "THEO DÕI CHỈ SỐ SỨC KHỎE (BMI)",
            "Cập nhật chiều cao, cân nặng định kỳ và theo dõi lịch sử thể trạng hội viên",
        )

        input_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        input_card.pack(fill="x", pady=(0, 16))

        top_grid = ctk.CTkFrame(input_card, fg_color="transparent")
        top_grid.pack(fill="x", padx=20, pady=16)
        top_grid.grid_columnconfigure(0, weight=2)
        top_grid.grid_columnconfigure(1, weight=3)

        # Cột tìm hội viên
        col_member = ctk.CTkFrame(top_grid, fg_color="transparent")
        col_member.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(
            col_member,
            text="🔍 Chọn hội viên",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", pady=(0, 6))
        self.entry_member_search = ctk.CTkEntry(
            col_member,
            placeholder_text="Nhập tên hội viên...",
            height=40,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
        )
        self.entry_member_search.pack(fill="x")
        self.entry_member_search.bind("<KeyRelease>", self.on_checkin_typing)
        self._bind_suggestion_keys(self.entry_member_search)

        # Cột nhập chiều cao / cân nặng
        col_stats = ctk.CTkFrame(top_grid, fg_color="transparent")
        col_stats.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        ctk.CTkLabel(
            col_stats,
            text="📊 Chỉ số cơ thể & Dự tính BMI",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", pady=(0, 6))

        input_inner = ctk.CTkFrame(col_stats, fg_color="transparent")
        input_inner.pack(fill="x")

        self.entry_h = ctk.CTkEntry(
            input_inner,
            placeholder_text="Cao (cm)",
            width=120,
            height=40,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
        )
        self.entry_h.pack(side="left", padx=(0, 8))
        self.entry_h.bind("<KeyRelease>", self.preview_bmi)

        self.entry_w = ctk.CTkEntry(
            input_inner,
            placeholder_text="Nặng (kg)",
            width=120,
            height=40,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
        )
        self.entry_w.pack(side="left", padx=(0, 12))
        self.entry_w.bind("<KeyRelease>", self.preview_bmi)

        self.bmi_preview_label = ctk.CTkLabel(
            input_inner,
            text="BMI: --",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color=COLORS["subtext"],
        )
        self.bmi_preview_label.pack(side="left", padx=8)

        # Hàng ghi chú + nút bấm
        bottom_bar = ctk.CTkFrame(input_card, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=20, pady=(0, 16))

        self.entry_note = ctk.CTkEntry(
            bottom_bar,
            placeholder_text="📝 Ghi chú thêm (tùy chọn)...",
            height=40,
            corner_radius=10,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
        )
        self.entry_note.pack(side="left", fill="x", expand=True, padx=(0, 12))

        ctk.CTkButton(
            bottom_bar,
            text="💾 LƯU CHỈ SỐ",
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            height=40,
            width=150,
            corner_radius=10,
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=self.handle_save_metrics,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            bottom_bar,
            text="🔄 LÀM MỚI",
            fg_color=COLORS["card_inner"],
            hover_color=COLORS["border"],
            height=40,
            width=100,
            corner_radius=10,
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=self.reset_metrics_input,
        ).pack(side="left")

        ctk.CTkLabel(
            self.main_frame,
            text="📈 LỊCH SỬ ĐO LƯỜNG (10 LẦN GẦN NHẤT)",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", pady=(4, 8))

        self.metrics_history_frame = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.metrics_history_frame.pack(fill="both", expand=True)

        self.refresh_metrics_history(None)

    def preview_bmi(self, event=None):
        try:
            h, w = self.entry_h.get().strip(), self.entry_w.get().strip()
            if h and w:
                bmi = round(float(w) / ((float(h) / 100) ** 2), 2)
                status, color, _ = calculate_bmi_status(bmi)
                self.bmi_preview_label.configure(
                    text=f"BMI: {bmi} ({status})", text_color=color
                )
        except Exception:
            pass

    def reset_metrics_input(self):
        self.quick_metrics_member_id = None
        self.entry_member_search.delete(0, "end")
        self.entry_h.delete(0, "end")
        self.entry_w.delete(0, "end")
        self.entry_note.delete(0, "end")
        self.bmi_preview_label.configure(text="BMI: --", text_color=COLORS["subtext"])
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
            m_id = self.quick_metrics_member_id
            if m_id is None:
                success_s, data = search_member_logic(name, "name")
                if not success_s or not data:
                    messagebox.showerror("❌ Lỗi", f"Không tìm thấy hội viên: {name}")
                    return
                m_id = data[0]["id"]

            success_save, msg = save_body_metrics(
                m_id, h, w, self.entry_note.get()
            )
            if success_save:
                messagebox.showinfo("✅ Thành công", msg)
                self.refresh_metrics_history(m_id)
                self.reset_metrics_input()
            else:
                messagebox.showerror("❌ Lỗi", msg)
        except ValueError:
            messagebox.showerror("❌ Lỗi", "Chiều cao/Cân nặng phải là số!")

    def refresh_metrics_history(self, member_id):
        for widget in self.metrics_history_frame.winfo_children():
            widget.destroy()

        header_frame = ctk.CTkFrame(
            self.metrics_history_frame,
            fg_color=COLORS["input_bg"],
            corner_radius=8,
            height=40,
        )
        header_frame.pack(fill="x", pady=6, padx=8)

        cols = [
            ("📅 Ngày đo", 160),
            ("📏 Chiều Cao", 130),
            ("⚖️ Cân Nặng", 130),
            ("BMI", 110),
            ("Đánh giá", 160),
        ]
        for label, width in cols:
            ctk.CTkLabel(
                header_frame,
                text=label,
                font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                text_color=COLORS["subtext"],
                width=width,
                anchor="w",
            ).pack(side="left", padx=10, pady=8)

        if member_id is None:
            ctk.CTkLabel(
                self.metrics_history_frame,
                text="Vui lòng chọn hội viên ở ô tìm kiếm để xem lịch sử đo.",
                text_color=COLORS["muted"],
            ).pack(pady=30)
            return

        history = get_metrics_history_detailed(member_id, limit=10)

        if not history:
            ctk.CTkLabel(
                self.metrics_history_frame,
                text="Hội viên này chưa có dữ liệu đo lường.",
                text_color=COLORS["muted"],
            ).pack(pady=30)
            return

        for entry in history:
            row = ctk.CTkFrame(
                self.metrics_history_frame,
                fg_color=COLORS["card_inner"],
                corner_radius=8,
            )
            row.pack(fill="x", pady=3, padx=8)

            ctk.CTkLabel(
                row,
                text=entry["ngay_ghi_nhan"],
                font=ctk.CTkFont(family="Inter", size=12),
                width=160,
                anchor="w",
            ).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(
                row,
                text=f"{entry['chieu_cao']} cm",
                font=ctk.CTkFont(family="Inter", size=12),
                width=130,
                anchor="w",
            ).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(
                row,
                text=f"{entry['can_nang']} kg",
                font=ctk.CTkFont(family="Inter", size=12),
                width=130,
                anchor="w",
            ).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(
                row,
                text=str(entry["bmi"]),
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                text_color=entry["status_color"],
                width=110,
                anchor="w",
            ).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(
                row,
                text=entry["status"],
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                text_color=entry["status_color"],
                width=160,
                anchor="w",
            ).pack(side="left", padx=10, pady=8)

    # ================= 6. MÀN HÌNH DANH SÁCH HỘI VIÊN =================

    def show_member_list(self):
        self.clear_main_frame()
        self.render_title(
            "DANH SÁCH HỘI VIÊN",
            "Tìm nhanh theo tên/SĐT, lọc hạn tập và nhấp đúp một dòng để mở hồ sơ",
        )

        table_wrapper = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        table_wrapper.pack(fill="both", expand=True)

        toolbar = ctk.CTkFrame(table_wrapper, fg_color="transparent")
        toolbar.pack(fill="x", padx=14, pady=(14, 6))
        self.member_list_search = ctk.CTkEntry(
            toolbar,
            placeholder_text="🔎 Lọc nhanh theo tên hoặc số điện thoại...",
            height=38,
            corner_radius=9,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"],
        )
        self.member_list_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.member_list_search.bind("<KeyRelease>", lambda event: self._render_member_list_rows())

        self.member_list_filter_var = ctk.StringVar(value="Tất cả")
        ctk.CTkSegmentedButton(
            toolbar,
            values=["Tất cả", "Đang tập", "Sắp hết hạn", "Quá hạn"],
            variable=self.member_list_filter_var,
            command=self._render_member_list_rows,
            height=36,
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
        ).pack(side="right")

        headers = [
            ("Họ và Tên Hội Viên", 220),
            ("Số Điện Thoại", 140),
            ("Ngày Hết Hạn", 140),
            ("Thời Hạn Còn", 120),
            ("Trạng Thái", 110),
        ]
        header_frame = ctk.CTkFrame(table_wrapper, fg_color=COLORS["input_bg"], corner_radius=10)
        header_frame.pack(fill="x", padx=14, pady=(0, 6))
        for text, width in headers:
            ctk.CTkLabel(
                header_frame,
                text=text,
                width=width,
                anchor="w",
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                text_color=COLORS["subtext"],
            ).pack(side="left", padx=12, pady=10)

        self.member_list_container = ctk.CTkScrollableFrame(table_wrapper, fg_color="transparent")
        self.member_list_container.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        success, members = get_all_members_summary_logic()
        self.member_list_load_error = None if success else str(members)
        self.member_list_members = [dict(member) for member in members] if success and members else []
        self._render_member_list_rows()

    def _render_member_list_rows(self, selected_filter=None):
        """Vẽ lại các dòng theo bộ lọc và từ khóa, không truy vấn lại DB mỗi lần gõ."""
        if not hasattr(self, "member_list_container") or not self.member_list_container.winfo_exists():
            return
        for widget in self.member_list_container.winfo_children():
            widget.destroy()

        if self.member_list_load_error:
            ctk.CTkLabel(
                self.member_list_container,
                text=f"Không tải được danh sách hội viên: {self.member_list_load_error}",
                text_color=COLORS["danger"],
                wraplength=700,
            ).pack(pady=40)
            return

        query = self.member_list_search.get().strip().casefold() if hasattr(self, "member_list_search") else ""
        chosen_filter = self.member_list_filter_var.get() if hasattr(self, "member_list_filter_var") else "Tất cả"
        visible_members = []
        for member in self.member_list_members:
            name_and_phone = f"{member.get('ho_ten', '')} {member.get('so_dien_thoai', '')}".casefold()
            if query and query not in name_and_phone:
                continue

            days_left = member.get("so_ngay_con_lai")
            status = member.get("trang_thai", "Active")
            if chosen_filter == "Đang tập":
                if not (status == "Active" and days_left is not None and days_left > 7):
                    continue
            elif chosen_filter == "Sắp hết hạn":
                if not (status == "Active" and days_left is not None and 0 <= days_left <= 7):
                    continue
            elif chosen_filter == "Quá hạn":
                if days_left is None or days_left >= 0:
                    continue
            visible_members.append(member)

        if not visible_members:
            ctk.CTkLabel(
                self.member_list_container,
                text="Không có hội viên phù hợp với bộ lọc hiện tại.",
                text_color=COLORS["muted"],
            ).pack(pady=40)
            return

        for idx, member in enumerate(visible_members):
            row_bg = COLORS["card_inner"] if idx % 2 == 0 else "transparent"
            row = ctk.CTkFrame(self.member_list_container, fg_color=row_bg, corner_radius=8)
            row.pack(fill="x", pady=2, padx=4)

            ctk.CTkLabel(
                row,
                text=member.get("ho_ten", ""),
                width=220,
                anchor="w",
                font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            ).pack(side="left", padx=12, pady=9)
            ctk.CTkLabel(
                row,
                text=member.get("so_dien_thoai", ""),
                width=140,
                anchor="w",
                text_color=COLORS["subtext"],
            ).pack(side="left", padx=12, pady=9)
            ctk.CTkLabel(
                row,
                text=member.get("ngay_het_han", ""),
                width=140,
                anchor="w",
            ).pack(side="left", padx=12, pady=9)

            days_left = member.get("so_ngay_con_lai")
            text_days = f"{days_left} ngày" if days_left is not None else "N/A"
            if days_left is not None and days_left < 0:
                color_days = COLORS["danger"]
            elif days_left is not None and days_left <= 7:
                color_days = COLORS["warning"]
            else:
                color_days = COLORS["success"]
            ctk.CTkLabel(
                row,
                text=text_days,
                width=120,
                anchor="w",
                text_color=color_days,
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            ).pack(side="left", padx=12, pady=9)

            status = member.get("trang_thai", "Active")
            status_color = (
                COLORS["success"] if status == "Active"
                else (COLORS["danger"] if status == "Locked" else COLORS["muted"])
            )
            ctk.CTkLabel(
                row,
                text=status,
                width=110,
                anchor="w",
                text_color=status_color,
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            ).pack(side="left", padx=12, pady=9)

            callback = lambda event, member_id=member["id"], member_name=member.get("ho_ten", ""): self.open_member_profile_from_list(member_id, member_name)
            row.bind("<Double-Button-1>", callback)
            for child in row.winfo_children():
                child.bind("<Double-Button-1>", callback)

    def open_member_profile_from_list(self, member_id, member_name):
        """Mở hồ sơ đúng ID kể cả khi có nhiều hội viên trùng tên."""
        self.navigate("search", self.show_search_screen)
        success, results = search_member_logic(member_name, "name")
        if not success:
            self.show_toast(f"Không tải được hồ sơ hội viên: {results}", success=False)
            return
        profile = next((item for item in results if item.get("id") == member_id), None)
        if profile is None:
            self.show_toast("Không tìm thấy hồ sơ hội viên đã chọn.", success=False)
            return
        self.entry_search.delete(0, tk.END)
        self.entry_search.insert(0, member_name)
        self.display_member_full_profile(profile)

    # ================= 7. MÀN HÌNH BÁO CÁO DOANH THU =================

    def show_dashboard(self):
        self.clear_main_frame()
        self.render_title(
            "BÁO CÁO DOANH THU & THỐNG KÊ",
            "Tổng hợp doanh thu theo kỳ, biến động hội viên và tỷ trọng gói tập",
        )

        success, stats = get_detailed_revenue_stats()
        if not success:
            ctk.CTkLabel(
                self.main_frame,
                text="❌ Lỗi tải dữ liệu thống kê",
                text_color=COLORS["danger"],
            ).pack(pady=50)
            return

        scroll_container = ctk.CTkScrollableFrame(
            self.main_frame, fg_color="transparent"
        )
        scroll_container.pack(fill="both", expand=True)

        # --- 1. KHỐI DOANH THU ---
        revenue_card = ctk.CTkFrame(
            scroll_container,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        revenue_card.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            revenue_card,
            text="💰 TỔNG HỢP DOANH THU",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", padx=20, pady=(16, 6))

        revenue_grid = ctk.CTkFrame(revenue_card, fg_color="transparent")
        revenue_grid.pack(fill="x", padx=16, pady=(0, 16))
        revenue_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        rev_items = [
            ("Doanh thu Hôm nay", f"{stats['daily']:,.0f} đ", COLORS["info"]),
            ("Doanh thu Tuần này", f"{stats['weekly']:,.0f} đ", COLORS["purple"]),
            ("Doanh thu Tháng này", f"{stats['monthly']:,.0f} đ", COLORS["accent"]),
            ("Tổng Doanh thu", f"{stats['total_all']:,.0f} đ", COLORS["success"]),
        ]

        for i, (label, value, color) in enumerate(rev_items):
            item = ctk.CTkFrame(
                revenue_grid, fg_color=COLORS["card_inner"], corner_radius=12
            )
            item.grid(row=0, column=i, padx=6, pady=4, sticky="ew")
            ctk.CTkLabel(
                item,
                text=label,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=COLORS["subtext"],
            ).pack(anchor="w", pady=(12, 2), padx=14)
            ctk.CTkLabel(
                item,
                text=value,
                font=ctk.CTkFont(family="Inter", size=17, weight="bold"),
                text_color=color,
            ).pack(anchor="w", pady=(0, 12), padx=14)

        # --- 2. KHỐI CHỈ SỐ HỘI VIÊN ---
        member_card = ctk.CTkFrame(
            scroll_container,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        member_card.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            member_card,
            text="👥 CHỈ SỐ HỘI VIÊN",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=COLORS["subtext"],
        ).pack(anchor="w", padx=20, pady=(16, 6))

        member_grid = ctk.CTkFrame(member_card, fg_color="transparent")
        member_grid.pack(fill="x", padx=16, pady=(0, 16))
        member_grid.grid_columnconfigure((0, 1, 2), weight=1)

        member_items = [
            ("Tổng đăng ký", str(stats.get("total_members", 0)), COLORS["text"]),
            ("Đang hoạt động", str(stats.get("active_members", 0)), COLORS["success"]),
            ("Sắp hết hạn", str(stats.get("expiring_soon", 0)), COLORS["warning"]),
            ("Đã hết hạn", str(stats.get("expired_members", 0)), COLORS["danger"]),
            ("Mới tháng này", str(stats.get("new_members_month", 0)), COLORS["info"]),
            ("Gia hạn tháng này", str(stats.get("renewals_month", 0)), COLORS["purple"]),
        ]

        for i, (label, value, color) in enumerate(member_items):
            hang_ngang = i // 3
            cot_doc = i % 3
            item = ctk.CTkFrame(
                member_grid, fg_color=COLORS["card_inner"], corner_radius=12
            )
            item.grid(row=hang_ngang, column=cot_doc, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(
                item,
                text=label,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=COLORS["subtext"],
            ).pack(anchor="w", pady=(10, 2), padx=14)
            ctk.CTkLabel(
                item,
                text=value,
                font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
                text_color=color,
            ).pack(anchor="w", pady=(0, 10), padx=14)

        # --- 3. BẢNG DOANH THU THEO GÓI ---
        if stats.get("package_stats"):
            package_card = ctk.CTkFrame(
                scroll_container,
                fg_color=COLORS["card"],
                corner_radius=16,
                border_width=1,
                border_color=COLORS["border"],
            )
            package_card.pack(fill="x", pady=(0, 14))

            ctk.CTkLabel(
                package_card,
                text="📊 DOANH THU THEO GÓI TẬP",
                font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                text_color=COLORS["subtext"],
            ).pack(anchor="w", padx=20, pady=(16, 10))

            for pkg in stats["package_stats"]:
                row = ctk.CTkFrame(
                    package_card, fg_color=COLORS["card_inner"], corner_radius=10
                )
                row.pack(fill="x", pady=3, padx=20)
                ctk.CTkLabel(
                    row,
                    text=f"📦  Gói {pkg['goi_tap']}",
                    width=200,
                    anchor="w",
                    font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
                ).pack(side="left", padx=14, pady=10)
                ctk.CTkLabel(
                    row,
                    text=f"{pkg['total']:,.0f} đ",
                    text_color=COLORS["success"],
                    font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
                ).pack(side="right", padx=16, pady=10)

            ctk.CTkFrame(package_card, height=8, fg_color="transparent").pack()

        ctk.CTkButton(
            scroll_container,
            text="📥  XUẤT BÁO CÁO EXCEL CHI TIẾT",
            height=46,
            corner_radius=10,
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#FFFFFF",
            command=self.handle_export,
        ).pack(pady=(6, 20), fill="x")

    def handle_export(self):
        success, path = export_to_excel_logic()
        if success:
            messagebox.showinfo("Thành công", f"Lưu tại: {path}")
            os.startfile(path)
        else:
            messagebox.showerror("Lỗi", path)


if __name__ == "__main__":
    app = GymManagementApp()
    app.mainloop()