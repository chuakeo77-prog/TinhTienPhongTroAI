import os
import json
import sqlite3
import hashlib
import hmac
import secrets
from pathlib import Path
from datetime import datetime
from io import BytesIO

import streamlit as st

# ============================================================
# QUẢN LÝ PHÒNG TRỌ - GIAO DIỆN SÁNG, ADMIN, HÓA ĐƠN, HÌNH ẢNH
# Chạy: streamlit run app.py
#
# Có thể đặt mật khẩu Admin qua biến môi trường ADMIN_PASSWORD.
# Nếu chưa đặt, mật khẩu mặc định là: admin123 (hãy đổi trước khi dùng thật).
# Chatbot AI tùy chọn: OPENAI_API_KEY trong biến môi trường hoặc secrets.toml.
# ============================================================

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "quan_ly_phong_tro.db"
UPLOAD_DIR = APP_DIR / "uploaded_images"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="Hệ Thống Quản Lý Phòng Trọ",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- Giao diện sáng --------------------
st.markdown(
    """
    <style>
    :root { color-scheme: light; }
    .stApp { background: #ffffff; color: #111827; }
    [data-testid="stHeader"] { background: rgba(255,255,255,.96); }
    [data-testid="stSidebar"] { background: #f7f8fa; border-right: 1px solid #e5e7eb; }
    [data-testid="stSidebar"] * { color: #111827 !important; }
    h1, h2, h3, h4, p, label, span, div { }
    h1, h2, h3, h4 { color: #111827; }
    p, label, [data-testid="stMarkdownContainer"] { color: #1f2937; }
    [data-testid="stMetric"] {
        background: #f8fafc; border: 1px solid #e5e7eb;
        border-radius: 12px; padding: 14px;
    }
    [data-testid="stMetricValue"] { color: #111827 !important; }
    input, textarea, [data-baseweb="select"] > div, [data-baseweb="popover"] {
        background: #ffffff !important; color: #111827 !important;
        border-color: #d1d5db !important;
    }
    [data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"] p,
    [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
        color: #1f2937 !important;
    }
    [data-testid="stChatMessage"] { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 12px; }
    [data-testid="stExpander"] { border: 1px solid #e5e7eb; border-radius: 10px; }
    .stAlert p { color: #111827 !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;
    }
    .stButton > button, .stDownloadButton > button, button[kind="primary"] {
        border-radius: 8px; font-weight: 600;
    }
    .stButton > button { border: 1px solid #d1d5db; background: #ffffff; color: #111827; }
    .stButton > button:hover { border-color: #64748b; color: #111827; background: #f3f4f6; }
    [data-testid="stAlert"] { border-radius: 10px; }
    hr { border-color: #e5e7eb; }
    </style>
    """,
    unsafe_allow_html=True,
)

DEFAULTS = {
    "gia_phong": 2_500_000,
    "gia_dien": 3_500,
    "gia_nuoc": 15_000,
    "gia_wifi": 100_000,
    "gia_rac": 50_000,
    "dien_cu": 1200,
    "dien_moi": 1350,
    "nuoc_cu": 450,
    "nuoc_moi": 462,
    "so_nguoi": 3,
    "ten_phong": "Phòng 01",
    "ten_khach": "",
    "thang_tinh": "",
}

# -------------------- SQLite: cấu hình và hóa đơn --------------------
def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_name TEXT NOT NULL,
                tenant_name TEXT DEFAULT '',
                billing_month TEXT DEFAULT '',
                total INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                data_json TEXT NOT NULL,
                image_path TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        for key, value in DEFAULTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                (key, json.dumps(value, ensure_ascii=False)),
            )


def load_settings():
    values = DEFAULTS.copy()
    with db_connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    for row in rows:
        try:
            values[row["key"]] = json.loads(row["value"])
        except (TypeError, json.JSONDecodeError):
            pass
    return values


def save_settings(values):
    with db_connect() as conn:
        for key, value in values.items():
            conn.execute(
                """INSERT INTO settings(key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (key, json.dumps(value, ensure_ascii=False)),
            )


init_db()
saved_settings = load_settings()
for key, value in saved_settings.items():
    if key not in st.session_state:
        st.session_state[key] = value

def load_chat_history():
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT 80"
        ).fetchall()
    rows = list(reversed(rows))
    if not rows:
        return [{
            "role": "assistant",
            "content": (
                "Xin chào! Tôi là chatbot hỗ trợ quản lý phòng trọ. "
                "Bạn có thể hỏi về hóa đơn, điện nước, hợp đồng thuê, cách quản lý phòng "
                "và số tiền mỗi người cần đóng. Khi có khóa API AI, tôi có thể trả lời linh hoạt hơn."
            ),
        }]
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def persist_chat_message(role, content):
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages(role, content, created_at) VALUES (?, ?, ?)",
            (role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "admin_login_attempts" not in st.session_state:
    st.session_state.admin_login_attempts = 0


def vnd(value):
    return f"{float(value):,.0f} VNĐ"


def current_values():
    return {key: st.session_state.get(key, default) for key, default in DEFAULTS.items()}


def calculate_bill(values=None):
    values = values or current_values()
    dien_tieu_thu = int(values["dien_moi"]) - int(values["dien_cu"])
    nuoc_tieu_thu = int(values["nuoc_moi"]) - int(values["nuoc_cu"])
    if dien_tieu_thu < 0 or nuoc_tieu_thu < 0:
        return {"error": "Chỉ số mới không được nhỏ hơn chỉ số cũ."}
    tien_dien = dien_tieu_thu * int(values["gia_dien"])
    tien_nuoc = nuoc_tieu_thu * int(values["gia_nuoc"])
    tong = (
        int(values["gia_phong"]) + tien_dien + tien_nuoc
        + int(values["gia_wifi"]) + int(values["gia_rac"])
    )
    so_nguoi = max(1, int(values["so_nguoi"]))
    return {
        "dien_tieu_thu": dien_tieu_thu,
        "nuoc_tieu_thu": nuoc_tieu_thu,
        "tien_dien": tien_dien,
        "tien_nuoc": tien_nuoc,
        "tong": tong,
        "moi_nguoi": tong / so_nguoi,
    }


def bill_context(values=None):
    values = values or current_values()
    b = calculate_bill(values)
    if "error" in b:
        return b["error"]
    return (
        f"Thông tin hóa đơn hiện tại của {values['ten_phong']}: "
        f"tiền phòng {vnd(values['gia_phong'])}; điện dùng "
        f"{b['dien_tieu_thu']} kWh, thành tiền {vnd(b['tien_dien'])}; "
        f"nước dùng {b['nuoc_tieu_thu']} khối, thành tiền {vnd(b['tien_nuoc'])}; "
        f"Wi-Fi {vnd(values['gia_wifi'])}; phí rác và dịch vụ "
        f"{vnd(values['gia_rac'])}; tổng cộng {vnd(b['tong'])}; "
        f"chia {values['so_nguoi']} người là khoảng {vnd(b['moi_nguoi'])}/người. "
        f"Đơn giá điện {vnd(values['gia_dien'])}/kWh, "
        f"đơn giá nước {vnd(values['gia_nuoc'])}/khối."
    )


def local_chat_reply(question):
    """Trả lời dự phòng khi chưa cấu hình khóa API AI."""
    q = question.lower().strip()
    b = calculate_bill()
    if any(k in q for k in ["xin chào", "chào", "hello", "hi "]):
        return (
            "Xin chào! Tôi có thể giúp bạn tính tiền phòng, giải thích cách tính điện/nước, "
            "chia tiền theo đầu người và hướng dẫn quản lý hóa đơn. Bạn muốn hỏi điều gì?"
        )
    if any(k in q for k in ["tổng tiền", "tổng hóa đơn", "bao nhiêu tiền", "phải đóng", "thanh toán", "hóa đơn hiện tại"]):
        return bill_context()
    if "error" in b:
        return "Chưa thể tính hóa đơn vì chỉ số mới nhỏ hơn chỉ số cũ. Hãy kiểm tra lại chỉ số điện và nước."
    if any(k in q for k in ["điện", "kwh"]):
        return (
            f"Tiền điện được tính bằng (chỉ số mới − chỉ số cũ) × đơn giá. "
            f"Phòng hiện dùng {b['dien_tieu_thu']} kWh × {vnd(st.session_state.gia_dien)}/kWh "
            f"= {vnd(b['tien_dien'])}. Bạn có thể vào mục “Tính hóa đơn” để sửa chỉ số."
        )
    if any(k in q for k in ["nước", "khối nước"]):
        return (
            f"Tiền nước được tính bằng (chỉ số mới − chỉ số cũ) × đơn giá. "
            f"Phòng hiện dùng {b['nuoc_tieu_thu']} khối × {vnd(st.session_state.gia_nuoc)}/khối "
            f"= {vnd(b['tien_nuoc'])}."
        )
    if any(k in q for k in ["mỗi người", "chia tiền", "chia đều", "đầu người"]):
        return (
            f"Tổng hóa đơn là {vnd(b['tong'])}. Chia đều cho {st.session_state.so_nguoi} người, "
            f"mỗi người đóng khoảng {vnd(b['moi_nguoi'])}."
        )
    if any(k in q for k in ["giá", "đơn giá", "wifi", "rác", "dịch vụ", "tiền phòng"]):
        return bill_context()
    if any(k in q for k in ["lưu hóa đơn", "xóa hóa đơn", "sửa hóa đơn", "admin", "đăng nhập"]):
        return (
            "Bạn vào mục “Admin quản lý” và đăng nhập để cấu hình giá, xem danh sách hóa đơn, "
            "chỉnh sửa hoặc xóa hóa đơn đã lưu. Vào “Tính hóa đơn” để tạo hóa đơn mới và bấm "
            "“Lưu hóa đơn vào hệ thống”. Dữ liệu được lưu trong cơ sở dữ liệu SQLite."
        )
    if any(k in q for k in ["ảnh", "hình", "hình ảnh"]):
        return (
            "Trong mục “Tính hóa đơn”, dùng ô “Hình ảnh đính kèm” để chọn ảnh JPG, PNG hoặc WEBP. "
            "Ảnh sẽ được lưu khi bạn bấm “Lưu hóa đơn vào hệ thống”."
        )
    return (
        "Tôi đang chạy ở chế độ trả lời cơ bản vì chưa có khóa API AI. Tôi có thể trả lời về "
        "hóa đơn, tiền điện/nước, đơn giá, chia tiền, lưu hóa đơn và hình ảnh. "
        "Để trò chuyện linh hoạt hơn với AI, hãy cấu hình OPENAI_API_KEY trong biến môi trường "
        "hoặc file .streamlit/secrets.toml."
    )


def get_chat_reply(question):
    """Dùng AI thật khi có OPENAI_API_KEY; nếu không, dùng bộ trả lời dự phòng."""
    api_key = os.getenv("OPENAI_API_KEY")
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", api_key)
    except Exception:
        pass
    if not api_key:
        return local_chat_reply(question)

    try:
        import requests

        context = bill_context()
        system_prompt = (
            "Bạn là trợ lý AI thông minh chuyên hỗ trợ quản lý nhà trọ tại Việt Nam. "
            "Luôn trả lời bằng tiếng Việt tự nhiên, rõ ràng, hữu ích; ưu tiên câu trả lời có cấu trúc "
            "và ví dụ khi phù hợp. Hỗ trợ các chủ đề: tính tiền phòng, điện nước, hóa đơn, chia phí, "
            "quản lý người thuê, quy trình lưu/sửa/xóa hóa đơn và hướng dẫn dùng ứng dụng. "
            "Với câu hỏi về số tiền hiện tại, chỉ dùng số liệu trong ngữ cảnh; không tự bịa số liệu. "
            "Nếu thiếu dữ liệu, hỏi lại ngắn gọn. Với vấn đề pháp lý/hợp đồng, đưa thông tin tổng quát "
            "và nhắc người dùng kiểm tra quy định địa phương khi cần. "
            "Dữ liệu hóa đơn hiện tại: " + context
        )
        messages = [{"role": "system", "content": system_prompt}]
        # The latest user prompt is already in history when this function is called;
        # exclude it here to avoid sending the same prompt twice.
        history = st.session_state.chat_history[-13:]
        if history and history[-1].get("role") == "user" and history[-1].get("content") == question:
            history = history[:-1]
        for item in history:
            if item.get("role") in {"user", "assistant"} and item.get("content"):
                messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": question})

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": messages,
                "temperature": 0.4,
            },
            timeout=45,
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"].strip()
        return answer or "Xin lỗi, tôi chưa tạo được câu trả lời. Bạn thử diễn đạt lại câu hỏi nhé."
    except Exception as exc:
        # Do not expose API keys or raw request details in the UI.
        return (
            "Tôi chưa kết nối được với dịch vụ AI nên đang trả lời ở chế độ dự phòng. "
            "Hãy kiểm tra OPENAI_API_KEY, kết nối Internet và hạn mức API.\\n\\n"
            + local_chat_reply(question)
        )


def expected_admin_password():
    try:
        return st.secrets.get("ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", "admin123"))
    except Exception:
        return os.getenv("ADMIN_PASSWORD", "admin123")


def save_uploaded_image(uploaded_file):
    if uploaded_file is None:
        return ""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    safe_name = f"bill_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}{suffix}"
    target = UPLOAD_DIR / safe_name
    target.write_bytes(uploaded_file.getbuffer())
    return str(target)


def make_bill_payload(values, b, image_path=""):
    return {
        "ten_phong": values["ten_phong"],
        "ten_khach": values["ten_khach"],
        "thang_tinh": values["thang_tinh"],
        "gia_phong": int(values["gia_phong"]),
        "gia_dien": int(values["gia_dien"]),
        "gia_nuoc": int(values["gia_nuoc"]),
        "gia_wifi": int(values["gia_wifi"]),
        "gia_rac": int(values["gia_rac"]),
        "dien_cu": int(values["dien_cu"]),
        "dien_moi": int(values["dien_moi"]),
        "nuoc_cu": int(values["nuoc_cu"]),
        "nuoc_moi": int(values["nuoc_moi"]),
        "so_nguoi": int(values["so_nguoi"]),
        "dien_tieu_thu": b["dien_tieu_thu"],
        "nuoc_tieu_thu": b["nuoc_tieu_thu"],
        "tien_dien": b["tien_dien"],
        "tien_nuoc": b["tien_nuoc"],
        "tong": b["tong"],
        "moi_nguoi": b["moi_nguoi"],
        "image_path": image_path,
    }


def insert_bill(payload, image_path=""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_connect() as conn:
        cur = conn.execute(
            """INSERT INTO bills(room_name, tenant_name, billing_month, total,
               created_at, updated_at, data_json, image_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payload["ten_phong"], payload["ten_khach"], payload["thang_tinh"],
                int(payload["tong"]), now, now,
                json.dumps(payload, ensure_ascii=False), image_path,
            ),
        )
        return cur.lastrowid


def get_bills():
    with db_connect() as conn:
        return conn.execute("SELECT * FROM bills ORDER BY id DESC").fetchall()


def get_bill(bill_id):
    with db_connect() as conn:
        return conn.execute("SELECT * FROM bills WHERE id=?", (bill_id,)).fetchone()


def update_bill(bill_id, payload, image_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload["image_path"] = image_path
    with db_connect() as conn:
        conn.execute(
            """UPDATE bills SET room_name=?, tenant_name=?, billing_month=?,
               total=?, updated_at=?, data_json=?, image_path=? WHERE id=?""",
            (
                payload["ten_phong"], payload["ten_khach"], payload["thang_tinh"],
                int(payload["tong"]), now, json.dumps(payload, ensure_ascii=False),
                image_path, bill_id,
            ),
        )


def delete_bill(bill_id):
    row = get_bill(bill_id)
    if row and row["image_path"]:
        try:
            Path(row["image_path"]).unlink(missing_ok=True)
        except OSError:
            pass
    with db_connect() as conn:
        conn.execute("DELETE FROM bills WHERE id=?", (bill_id,))


def bill_text(payload):
    return (
        f"THÔNG BÁO TIỀN PHÒNG {payload['ten_phong']} ({payload.get('thang_tinh') or 'tháng này'})\n"
        + (f"- Khách thuê: {payload['ten_khach']}\n" if payload.get("ten_khach") else "")
        + f"- Tiền phòng: {vnd(payload['gia_phong'])}\n"
        + f"- Điện: {payload['dien_tieu_thu']} kWh ({vnd(payload['tien_dien'])})\n"
        + f"- Nước: {payload['nuoc_tieu_thu']} khối ({vnd(payload['tien_nuoc'])})\n"
        + f"- Wi-Fi: {vnd(payload['gia_wifi'])}\n"
        + f"- Rác & dịch vụ: {vnd(payload['gia_rac'])}\n"
        + f"=> TỔNG: {vnd(payload['tong'])}\n"
        + f"=> Mỗi người ({payload['so_nguoi']} người): {vnd(payload['moi_nguoi'])}\n"
        + "Vui lòng thanh toán đúng hạn. Cảm ơn mọi người!"
    )


# -------------------- Điều hướng --------------------
st.sidebar.title("🏠 Quản lý phòng trọ")
page = st.sidebar.radio(
    "Điều hướng",
    ["💬 Chatbot quản lý", "🧮 Tính hóa đơn", "🛠️ Admin quản lý"],
    index=0,
)
st.sidebar.caption("Giao diện nền trắng, chữ đen. Dữ liệu được lưu trong SQLite.")
if os.getenv("OPENAI_API_KEY"):
    st.sidebar.success("Chatbot AI: đã cấu hình khóa API")
else:
    try:
        _api_ready = bool(st.secrets.get("OPENAI_API_KEY", ""))
    except Exception:
        _api_ready = False
    if _api_ready:
        st.sidebar.success("Chatbot AI: đã cấu hình khóa API")
    else:
        st.sidebar.info("Chatbot đang ở chế độ cơ bản. Cấu hình OPENAI_API_KEY để bật AI.")

# -------------------- Chatbot --------------------
if page == "💬 Chatbot quản lý":
    st.title("💬 Chatbot hỗ trợ quản lý phòng trọ")
    st.write("Hỏi nhanh về hóa đơn, tiền điện, tiền nước và số tiền mỗi người cần đóng.")
    with st.expander("📌 Thông tin hóa đơn hiện tại"):
        st.write(bill_context())
    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
    prompt = st.chat_input("Nhập câu hỏi, ví dụ: Tổng tiền phòng tháng này là bao nhiêu?")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        persist_chat_message("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)
        reply = get_chat_reply(prompt)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        persist_chat_message("assistant", reply)
        with st.chat_message("assistant"):
            st.markdown(reply)
    if st.button("🧹 Xóa hội thoại"):
        with db_connect() as conn:
            conn.execute("DELETE FROM chat_messages")
        st.session_state.chat_history = [{
            "role": "assistant",
            "content": "Đã xóa hội thoại. Bạn có thể bắt đầu hỏi câu mới.",
        }]
        persist_chat_message("assistant", st.session_state.chat_history[0]["content"])
        st.rerun()

# -------------------- Tính hóa đơn (giữ chức năng cũ) --------------------
elif page == "🧮 Tính hóa đơn":
    st.title("🧮 Tính tiền phòng")
    st.write("Nhập chỉ số điện, nước và thông tin người thuê. Đơn giá được Admin thiết lập.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("⚡ Chỉ số điện")
        st.number_input("Số điện CŨ (kWh)", min_value=0, step=1, key="dien_cu")
        st.number_input("Số điện MỚI (kWh)", min_value=0, step=1, key="dien_moi")
    with c2:
        st.subheader("💧 Chỉ số nước")
        st.number_input("Số nước CŨ (khối)", min_value=0, step=1, key="nuoc_cu")
        st.number_input("Số nước MỚI (khối)", min_value=0, step=1, key="nuoc_moi")
    st.subheader("👤 Thông tin phòng")
    c3, c4, c5 = st.columns([2, 2, 1])
    with c3:
        st.text_input("Tên phòng", key="ten_phong")
    with c4:
        st.text_input("Tên khách thuê (tùy chọn)", key="ten_khach")
    with c5:
        st.number_input("Số người", min_value=1, max_value=20, step=1, key="so_nguoi")
    st.text_input("Tháng tính hóa đơn (ví dụ: 10/2026)", key="thang_tinh")
    st.subheader("🖼️ Hình ảnh đính kèm (tùy chọn)")
    uploaded = st.file_uploader("Chọn ảnh phòng, đồng hồ điện/nước hoặc chứng từ", type=["jpg", "jpeg", "png", "webp"], key="new_bill_image")
    if uploaded:
        st.image(uploaded, caption="Ảnh xem trước", width=320)
    b = calculate_bill()
    if "error" in b:
        st.error(b["error"] + " Vui lòng kiểm tra lại các chỉ số.")
    else:
        st.metric("💰 Tổng số tiền cần thanh toán", vnd(b["tong"]))
        details = [
            {"Khoản mục": "Tiền phòng cố định", "Chi tiết": "Gói cố định", "Thành tiền": vnd(st.session_state.gia_phong)},
            {"Khoản mục": "Tiền điện", "Chi tiết": f"{b['dien_tieu_thu']} kWh × {vnd(st.session_state.gia_dien)}", "Thành tiền": vnd(b["tien_dien"])},
            {"Khoản mục": "Tiền nước", "Chi tiết": f"{b['nuoc_tieu_thu']} khối × {vnd(st.session_state.gia_nuoc)}", "Thành tiền": vnd(b["tien_nuoc"])},
            {"Khoản mục": "Tiền Wi-Fi", "Chi tiết": "Gói cố định", "Thành tiền": vnd(st.session_state.gia_wifi)},
            {"Khoản mục": "Rác & dịch vụ", "Chi tiết": "Gói cố định", "Thành tiền": vnd(st.session_state.gia_rac)},
        ]
        st.dataframe(details, use_container_width=True, hide_index=True)
        st.info(f"👥 Mỗi người cần đóng: **{vnd(b['moi_nguoi'])}**")
        payload = make_bill_payload(current_values(), b)
        tin_nhan = bill_text(payload)
        st.subheader("📱 Tin nhắn gửi nhanh qua Zalo")
        st.text_area("Sao chép nội dung tin nhắn", value=tin_nhan, height=220)
        st.download_button(
            "⬇️ Tải hóa đơn dạng TXT",
            data=tin_nhan,
            file_name=f"hoa_don_{st.session_state.ten_phong.replace(' ', '_')}.txt",
            mime="text/plain",
        )
        if st.button("💾 Lưu hóa đơn vào hệ thống", type="primary", use_container_width=True):
            image_path = save_uploaded_image(uploaded) if uploaded else ""
            payload = make_bill_payload(current_values(), b, image_path)
            new_id = insert_bill(payload, image_path)
            st.success(f"Đã lưu hóa đơn #{new_id}. Bạn có thể xem, sửa hoặc xóa trong mục Admin.")
            st.rerun()

# -------------------- Admin --------------------
else:
    st.title("🛠️ Admin quản lý")
    if not st.session_state.admin_logged_in:
        st.write("Đăng nhập để chỉnh sửa bảng giá và quản lý các hóa đơn đã lưu.")
        with st.form("admin_login_form", clear_on_submit=False):
            password = st.text_input("Mật khẩu Admin", type="password")
            login = st.form_submit_button("🔐 Đăng nhập", type="primary", use_container_width=True)
        if login:
            correct = expected_admin_password()
            if hmac.compare_digest(password, str(correct)):
                st.session_state.admin_logged_in = True
                st.session_state.admin_login_attempts = 0
                st.success("Đăng nhập thành công.")
                st.rerun()
            else:
                st.session_state.admin_login_attempts += 1
                st.error("Mật khẩu không đúng.")
        st.caption("Lần chạy đầu: mật khẩu mặc định admin123. Hãy đổi bằng biến môi trường ADMIN_PASSWORD hoặc secrets.toml.")
        st.stop()

    top1, top2 = st.columns([5, 1])
    with top1:
        st.success("Bạn đang đăng nhập với quyền Admin.")
    with top2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.rerun()

    tab_settings, tab_bills = st.tabs(["⚙️ Cấu hình giá", "🧾 Quản lý hóa đơn"])

    with tab_settings:
        st.write("Thay đổi đơn giá tại đây. Cấu hình được lưu vào SQLite và vẫn còn sau khi khởi động lại.")
        with st.form("admin_price_form"):
            a1, a2 = st.columns(2)
            with a1:
                gia_phong = st.number_input("Tiền phòng cố định (VNĐ)", min_value=0, step=100000, value=int(st.session_state.gia_phong))
                gia_dien = st.number_input("Giá điện (VNĐ/kWh)", min_value=0, step=100, value=int(st.session_state.gia_dien))
                gia_nuoc = st.number_input("Giá nước (VNĐ/khối)", min_value=0, step=500, value=int(st.session_state.gia_nuoc))
            with a2:
                gia_wifi = st.number_input("Tiền Wi-Fi/phòng (VNĐ)", min_value=0, step=10000, value=int(st.session_state.gia_wifi))
                gia_rac = st.number_input("Tiền rác & dịch vụ (VNĐ)", min_value=0, step=5000, value=int(st.session_state.gia_rac))
                thang_tinh = st.text_input("Tháng tính hóa đơn mặc định", value=str(st.session_state.thang_tinh))
            submitted = st.form_submit_button("💾 Lưu cấu hình", type="primary", use_container_width=True)
        if submitted:
            updates = {
                "gia_phong": gia_phong, "gia_dien": gia_dien, "gia_nuoc": gia_nuoc,
                "gia_wifi": gia_wifi, "gia_rac": gia_rac, "thang_tinh": thang_tinh,
            }
            for key, value in updates.items():
                st.session_state[key] = value
            save_settings(current_values())
            st.success("Đã lưu cấu hình thành công.")
            st.rerun()
        st.subheader("📋 Bảng giá đang áp dụng")
        st.dataframe([
            {"Khoản mục": "Tiền phòng", "Đơn giá": vnd(st.session_state.gia_phong)},
            {"Khoản mục": "Điện", "Đơn giá": f"{vnd(st.session_state.gia_dien)}/kWh"},
            {"Khoản mục": "Nước", "Đơn giá": f"{vnd(st.session_state.gia_nuoc)}/khối"},
            {"Khoản mục": "Wi-Fi", "Đơn giá": vnd(st.session_state.gia_wifi)},
            {"Khoản mục": "Rác & dịch vụ", "Đơn giá": vnd(st.session_state.gia_rac)},
        ], use_container_width=True, hide_index=True)

    with tab_bills:
        st.write("Hóa đơn được lưu độc lập với phiên làm việc. Chọn một hóa đơn để xem, chỉnh sửa hoặc xóa.")
        bills = get_bills()
        if not bills:
            st.info("Chưa có hóa đơn nào. Hãy vào mục “Tính hóa đơn” để tạo và lưu hóa đơn đầu tiên.")
        else:
            rows = [{
                "Mã": row["id"],
                "Phòng": row["room_name"],
                "Khách thuê": row["tenant_name"],
                "Tháng": row["billing_month"],
                "Tổng tiền": vnd(row["total"]),
                "Ngày tạo": row["created_at"],
                "Cập nhật": row["updated_at"],
            } for row in bills]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            selected_id = st.selectbox("Chọn mã hóa đơn", options=[int(row["id"]) for row in bills], format_func=lambda x: f"#{x} — {next((r['room_name'] for r in bills if r['id'] == x), '')}")
            row = get_bill(selected_id)
            payload = json.loads(row["data_json"]) if row else {}
            if row:
                st.divider()
                st.subheader(f"🧾 Chi tiết hóa đơn #{selected_id}")
                if row["image_path"] and Path(row["image_path"]).is_file():
                    st.image(row["image_path"], caption="Ảnh đính kèm hóa đơn", width=360)
                st.write(bill_text(payload))
                with st.expander("✏️ Chỉnh sửa hóa đơn", expanded=False):
                    with st.form(f"edit_bill_{selected_id}"):
                        e1, e2 = st.columns(2)
                        with e1:
                            e_room = st.text_input("Tên phòng", value=payload.get("ten_phong", "Phòng 01"))
                            e_tenant = st.text_input("Tên khách thuê", value=payload.get("ten_khach", ""))
                            e_month = st.text_input("Tháng tính", value=payload.get("thang_tinh", ""))
                            e_people = st.number_input("Số người", min_value=1, max_value=20, value=int(payload.get("so_nguoi", 1)))
                        with e2:
                            e_rent = st.number_input("Tiền phòng", min_value=0, step=100000, value=int(payload.get("gia_phong", 0)))
                            e_eprice = st.number_input("Đơn giá điện", min_value=0, step=100, value=int(payload.get("gia_dien", 0)))
                            e_wprice = st.number_input("Đơn giá nước", min_value=0, step=500, value=int(payload.get("gia_nuoc", 0)))
                            e_wifi = st.number_input("Tiền Wi-Fi", min_value=0, step=10000, value=int(payload.get("gia_wifi", 0)))
                            e_trash = st.number_input("Rác & dịch vụ", min_value=0, step=5000, value=int(payload.get("gia_rac", 0)))
                        e3, e4 = st.columns(2)
                        with e3:
                            e_ec = st.number_input("Số điện cũ", min_value=0, value=int(payload.get("dien_cu", 0)))
                            e_en = st.number_input("Số điện mới", min_value=0, value=int(payload.get("dien_moi", 0)))
                        with e4:
                            e_wc = st.number_input("Số nước cũ", min_value=0, value=int(payload.get("nuoc_cu", 0)))
                            e_wn = st.number_input("Số nước mới", min_value=0, value=int(payload.get("nuoc_moi", 0)))
                        replace_image = st.file_uploader("Thay ảnh đính kèm (không chọn nếu giữ ảnh cũ)", type=["jpg", "jpeg", "png", "webp"], key=f"edit_image_{selected_id}")
                        remove_image = st.checkbox("Xóa ảnh đính kèm hiện tại")
                        save_edit = st.form_submit_button("💾 Lưu chỉnh sửa", type="primary", use_container_width=True)
                    if save_edit:
                        edit_values = {
                            "ten_phong": e_room, "ten_khach": e_tenant, "thang_tinh": e_month,
                            "so_nguoi": e_people, "gia_phong": e_rent, "gia_dien": e_eprice,
                            "gia_nuoc": e_wprice, "gia_wifi": e_wifi, "gia_rac": e_trash,
                            "dien_cu": e_ec, "dien_moi": e_en, "nuoc_cu": e_wc, "nuoc_moi": e_wn,
                        }
                        edit_calc = calculate_bill(edit_values)
                        if "error" in edit_calc:
                            st.error(edit_calc["error"])
                        else:
                            old_image = row["image_path"] or ""
                            new_image = old_image
                            if remove_image:
                                new_image = ""
                            if replace_image is not None:
                                new_image = save_uploaded_image(replace_image)
                            edit_payload = make_bill_payload(edit_values, edit_calc, new_image)
                            update_bill(selected_id, edit_payload, new_image)
                            if new_image != old_image and old_image:
                                try:
                                    Path(old_image).unlink(missing_ok=True)
                                except OSError:
                                    pass
                            st.success("Đã cập nhật hóa đơn.")
                            st.rerun()
                with st.expander("🗑️ Xóa hóa đơn", expanded=False):
                    st.warning("Xóa hóa đơn là thao tác không thể hoàn tác.")
                    confirm_delete = st.checkbox("Tôi xác nhận muốn xóa hóa đơn này", key=f"confirm_delete_{selected_id}")
                    if st.button("Xóa hóa đơn đã chọn", type="primary", disabled=not confirm_delete, key=f"delete_bill_{selected_id}"):
                        delete_bill(selected_id)
                        st.success(f"Đã xóa hóa đơn #{selected_id}.")
                        st.rerun()

    st.divider()
    st.caption("Bảo mật: đặt ADMIN_PASSWORD riêng trước khi đưa ứng dụng lên Internet. Mật khẩu mặc định chỉ phù hợp để chạy thử cục bộ.")


# Tự động lưu các thông tin nhập hiện tại vào SQLite sau mỗi lần Streamlit chạy lại.
# Hóa đơn đã lưu vẫn được giữ riêng trong bảng bills.
try:
    save_settings(current_values())
except Exception:
    pass
