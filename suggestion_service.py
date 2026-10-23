import unicodedata

from database import get_connection, decrypt_cccd


def _normalize_name(value):
    """Chuẩn hóa tên để xếp hạng kết quả nhất quán với chữ tiếng Việt."""
    value = unicodedata.normalize("NFD", str(value or "")).casefold()
    value = "".join(
        char for char in value if unicodedata.category(char) != "Mn"
    )
    return value.replace("đ", "d")


def _match_rank(name, query):
    """Ưu tiên họ tên bắt đầu bằng cụm tìm kiếm và khớp ở tên gọi cuối."""
    normalized_name = _normalize_name(name).strip()
    normalized_query = _normalize_name(query).strip()
    if not normalized_query or normalized_query not in normalized_name:
        return None

    tokens = normalized_name.split()
    if normalized_name == normalized_query:
        return 0
    if normalized_name.startswith(normalized_query + " "):
        return 1
    if tokens and tokens[-1] == normalized_query:
        return 2
    if tokens and tokens[-1].startswith(normalized_query):
        return 3
    if normalized_query in tokens:
        return 4
    if any(token.startswith(normalized_query) for token in tokens):
        return 5
    return 6


def get_checkin_suggestions(query):
    """Gợi ý tối đa 10 hội viên; ưu tiên tên gọi khi tìm bằng tên riêng."""
    query = str(query or "").strip()
    if not query:
        return []

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Không giới hạn ngay trong SQL: LIMIT 10 không có ORDER BY có thể
        # loại mất hội viên cần tìm khi nhiều tên khác cũng chứa từ khóa.
        cursor.execute(
            "SELECT ho_ten, so_dien_thoai, cccd FROM members WHERE ho_ten LIKE ?",
            (f"%{query}%",),
        )
        rows = cursor.fetchall()

        ranked_rows = []
        for position, row in enumerate(rows):
            name = row["ho_ten"] or ""
            rank = _match_rank(name, query)
            if rank is not None:
                ranked_rows.append((rank, position, row))

        ranked_rows.sort(key=lambda item: (item[0], item[1]))

        suggestions = []
        for _, _, row in ranked_rows[:10]:
            name = row["ho_ten"] or ""
            phone = row["so_dien_thoai"] or ""
            suggestions.append({
                "display": f"{name} - SĐT: {phone}",
                "real_value": decrypt_cccd(row["cccd"]),
            })
        return suggestions
    except Exception as e:
        print(f"Lỗi gợi ý: {e}")
        return []
    finally:
        if conn:
            conn.close()
