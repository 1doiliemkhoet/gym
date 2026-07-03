import tkinter.messagebox as messagebox
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from database import get_connection

# Bảng màu đồng bộ với main.py
CHART_COLORS = {
    "bg_card": "#181C24",
    "bg_inner": "#202530",
    "border": "#2A303C",
    "accent": "#E11D48",       # Đỏ Crimson chủ đạo
    "peak": "#F59E0B",         # Vàng cam đánh dấu đỉnh cao điểm
    "info": "#3B82F6",         # Xanh dương
    "success": "#10B981",      # Xanh lá
    "text": "#F8FAFC",         # Chữ trắng sáng
    "subtext": "#94A3B8",      # Chữ xám phụ
}


def fetch_peak_hours_data():
    """Truy vấn dữ liệu khung giờ check-in trong 7 ngày gần nhất từ SQLite."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT strftime('%H', check_in_time, 'localtime') AS khung_gio, COUNT(*) AS so_luong
            FROM check_ins 
            WHERE check_in_time IS NOT NULL 
              AND DATE(check_in_time, 'localtime') >= date('now', '-7 days', 'localtime')
            GROUP BY khung_gio
            ORDER BY khung_gio ASC
        """
        cursor.execute(sql)
        data = cursor.fetchall()

        hours = [f"{i:02d}:00" for i in range(24)]
        counts = [0] * 24

        for row in data:
            gio_str = row["khung_gio"]
            so_luong = row["so_luong"]
            if gio_str is not None:
                counts[int(gio_str)] = so_luong

        return hours, counts
    finally:
        if conn:
            conn.close()


def _create_dark_figure(hours, counts, figsize=(10, 4.8)):
    """Khởi tạo đối tượng Figure Matplotlib chuẩn giao diện tối."""
    fig = Figure(figsize=figsize, dpi=100, facecolor=CHART_COLORS["bg_card"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(CHART_COLORS["bg_card"])

    x_indices = list(range(len(hours)))

    # 1. Tô vùng chuyển sắc dưới đường biểu đồ (Area Fill)
    ax.fill_between(
        x_indices, counts, color=CHART_COLORS["accent"], alpha=0.18, zorder=2
    )

    # 2. Vẽ đường chính (Line Plot)
    ax.plot(
        x_indices,
        counts,
        marker="o",
        linestyle="-",
        color=CHART_COLORS["accent"],
        linewidth=2.5,
        markersize=6,
        markerfacecolor=CHART_COLORS["bg_card"],
        markeredgewidth=2,
        markeredgecolor=CHART_COLORS["accent"],
        zorder=3,
    )

    # 3. Đánh dấu điểm cao nhất & hiển thị số lượng trên các mốc có khách
    max_count = max(counts) if counts else 0
    peak_idx = counts.index(max_count) if max_count > 0 else None

    for idx, val in enumerate(counts):
        if val > 0:
            is_peak = idx == peak_idx
            dot_color = CHART_COLORS["peak"] if is_peak else CHART_COLORS["text"]
            if is_peak:
                ax.scatter(
                    [idx],
                    [val],
                    color=CHART_COLORS["peak"],
                    s=90,
                    zorder=4,
                )
            ax.annotate(
                f"{val}",
                xy=(idx, val),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                fontweight="bold",
                color=dot_color,
            )

    # 4. Tinh chỉnh trục, lưới và khung viền
    ax.set_xticks(x_indices)
    ax.set_xticklabels(hours, rotation=45, ha="right")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    upper_limit = max(max_count * 1.25, 5)
    ax.set_ylim(0, upper_limit)
    ax.set_xlim(-0.5, 23.5)

    ax.set_xlabel(
        "Khung giờ trong ngày (00:00 - 23:00)",
        fontsize=10,
        color=CHART_COLORS["subtext"],
        labelpad=10,
    )
    ax.set_ylabel(
        "Tổng số lượt Check-in",
        fontsize=10,
        color=CHART_COLORS["subtext"],
        labelpad=10,
    )

    ax.tick_params(axis="x", colors=CHART_COLORS["subtext"], labelsize=9)
    ax.tick_params(axis="y", colors=CHART_COLORS["subtext"], labelsize=9)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(CHART_COLORS["border"])
    ax.spines["bottom"].set_color(CHART_COLORS["border"])

    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.35,
        color=CHART_COLORS["border"],
        zorder=1,
    )

    fig.tight_layout(pad=1.8)
    return fig


def show_peak_hours_chart(parent_frame=None):
    """
    Hiển thị biểu đồ khung giờ cao điểm:
    - Nếu truyền `parent_frame` (ví dụ `self.main_frame`), nhúng trực tiếp vào giao diện CustomTkinter.
    - Nếu không truyền tham số, mở cửa sổ biểu đồ Dark Mode độc lập.
    """
    try:
        hours, counts = fetch_peak_hours_data()
        total_checkins = sum(counts)
        max_checkin = max(counts) if counts else 0
        peak_hour = (
            hours[counts.index(max_checkin)] if max_checkin > 0 else "Chưa có dữ liệu"
        )

        # TRƯỜNG HỢP 1: Nhúng trực tiếp vào main_frame của ứng dụng
        if parent_frame is not None:
            for widget in parent_frame.winfo_children():
                widget.destroy()

            # Tiêu đề trang
            header_box = ctk.CTkFrame(parent_frame, fg_color="transparent")
            header_box.pack(fill="x", pady=(0, 16))
            ctk.CTkLabel(
                header_box,
                text="BIỂU ĐỒ KHUNG GIỜ ĐÔNG KHÁCH (7 NGÀY QUA)",
                font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
                text_color=CHART_COLORS["text"],
            ).pack(anchor="w")
            ctk.CTkLabel(
                header_box,
                text="Phân tích mật độ hội viên ra vào theo từng khung giờ trong ngày",
                font=ctk.CTkFont(family="Inter", size=12),
                text_color=CHART_COLORS["subtext"],
            ).pack(anchor="w", pady=(2, 0))

            # Hàng 3 thẻ KPI tóm tắt
            kpi_row = ctk.CTkFrame(parent_frame, fg_color="transparent")
            kpi_row.pack(fill="x", pady=(0, 14))
            kpi_row.grid_columnconfigure((0, 1, 2), weight=1)

            kpis = [
                ("⚡ Tổng Check-in (7 ngày)", f"{total_checkins} lượt", CHART_COLORS["info"]),
                ("🔥 Khung Giờ Cao Điểm Nhất", peak_hour, CHART_COLORS["peak"]),
                ("📈 Mật Độ Đỉnh Điểm", f"{max_checkin} lượt / giờ", CHART_COLORS["success"]),
            ]

            for idx, (label, val, color) in enumerate(kpis):
                card = ctk.CTkFrame(
                    kpi_row,
                    fg_color=CHART_COLORS["bg_card"],
                    corner_radius=12,
                    border_width=1,
                    border_color=CHART_COLORS["border"],
                )
                padx = (0, 6) if idx == 0 else ((6, 0) if idx == 2 else 6)
                card.grid(row=0, column=idx, sticky="ew", padx=padx)

                ctk.CTkLabel(
                    card,
                    text=label,
                    font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                    text_color=CHART_COLORS["subtext"],
                ).pack(anchor="w", padx=16, pady=(12, 2))
                ctk.CTkLabel(
                    card,
                    text=val,
                    font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
                    text_color=color,
                ).pack(anchor="w", padx=16, pady=(0, 12))

            # Khung chứa Canvas Biểu đồ
            chart_card = ctk.CTkFrame(
                parent_frame,
                fg_color=CHART_COLORS["bg_card"],
                corner_radius=16,
                border_width=1,
                border_color=CHART_COLORS["border"],
            )
            chart_card.pack(fill="both", expand=True)

            fig = _create_dark_figure(hours, counts)
            canvas = FigureCanvasTkAgg(fig, master=chart_card)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=12)
            return

        # TRƯỜNG HỢP 2: Chạy cửa sổ rời (Fallback khi gọi không tham số)
        plt.close("all")
        fig = _create_dark_figure(hours, counts, figsize=(10.5, 5.2))
        fig.axes[0].set_title(
            "THỐNG KÊ KHUNG GIỜ ĐÔNG KHÁCH NHẤT (7 NGÀY QUA)",
            fontsize=13,
            fontweight="bold",
            color=CHART_COLORS["text"],
            pad=15,
        )

        # Hiển thị bằng CTkToplevel đồng bộ giao diện tối
        win = ctk.CTkToplevel()
        win.title("TH GYM — Biểu đồ Giờ khách")
        win.geometry("980x560")
        win.configure(fg_color=CHART_COLORS["bg_card"])
        win.attributes("-topmost", True)

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=16, pady=16)

    except Exception as e:
        messagebox.showerror("Lỗi Thống Kê", f"Không thể vẽ biểu đồ:\n{e}")