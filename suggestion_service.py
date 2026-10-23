import unicodedata

from database import get_connection
from database import decrypt_cccd


def _normalize_search_text(value):
    """Chuẩn hóa chuỗi để tìm tên không phân biệt hoa/thường và dấu tiếng Việt."""
    text = unicodedata.normalize("NFD", str(value or "")).casefold()
    text = "".join(
        character
        for character in text
        if unicodedata.category(character) != "Mn"
    )
    return text.replace("đ", "d")


def get_checkin_suggestions(query):
    """Tìm hội viên theo bất kỳ phần nào của họ tên, không phân biệt dấu."""
    normalized_query = _normalize_search_text(query).strip()
    if not normalized_query:
        return []

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # SQLite LIKE không xử lý đầy đủ chữ hoa/thường Unicode tiếng Việt
        # (ví dụ Đ/đ, Á/á), nên lọc tên bằng chuẩn hóa Unicode trong Python.
        cursor.execute(
            "SELECT ho_ten, so_dien_thoai, cccd FROM members"
        )
        results = cursor.fetchall()

        suggestions = []
        for row in results:
            name = row["ho_ten"] or ""
            if normalized_query not in _normalize_search_text(name):
                continue

            phone = row["so_dien_thoai"]
            real_cccd = decrypt_cccd(row["cccd"])

            suggestions.append({
                "display": f"{name} - SĐT: {phone}",
                "real_value": real_cccd,
            })
            if len(suggestions) >= 10:
                break

        return suggestions
    except Exception as e:
        print(f"Lỗi gợi ý: {e}")
        return []
    finally:
        if conn:
            conn.close()
