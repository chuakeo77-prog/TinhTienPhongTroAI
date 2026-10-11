import streamlit as st
import requests
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# ============================================================
# CẤU HÌNH TRANG
# ============================================================
st.set_page_config(
    page_title="App Tính Tiền Phòng Trọ",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# HÌNH ẢNH / LOGO
# Đặt file ảnh cạnh app.py, ví dụ: logo.jpg hoặc nha_tro.png
# Có thể đổi IMAGE_PATH bên dưới theo tên file của bạn.
# ============================================================
IMAGE_PATH = "logo.jpg"

# ============================================================
# GIAO DIỆN: NỀN SÁNG, CHỮ RÕ, THẺ NỘI DUNG DỄ ĐỌC
# ============================================================
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #f4f8ff 0%, #f8fbff 55%, #eef6ff 100%); color: #172033; }
[data-testid="stHeader"] { background: rgba(244,248,255,0.88); }
[data-testid="stSidebar"] { background: #eaf1fb; border-right: 1px solid #d7e3f4; }
[data-testid="stSidebar"] * { color: #172033; }
.stMarkdown, .stText, label, p, li { color: #172033; }
[data-testid="stMetric"] { background: #ffffff; border: 1px solid #dbe5f2; padding: 16px; border-radius: 14px; box-shadow: 0 3px 12px rgba(28,55,90,.06); }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
.stButton > button, .stDownloadButton > button { border-radius: 10px; font-weight: 600; min-height: 2.7rem; }
.stButton > button[kind="primary"] { background: #2563eb; border-color: #2563eb; }
input, textarea, [data-baseweb="select"] > div { background-color: #ffffff !important; }
hr { border-color: #d7e3f4; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CƠ SỞ DỮ LIỆU SQLITE: LƯU LỊCH SỬ HÓA ĐƠN
# ============================================================
DB_FILE = "phongtro_data.db"

def ket_noi_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            tenant_name TEXT,
            room_code TEXT,
            billing_period TEXT,
            total_amount REAL NOT NULL,
            invoice_text TEXT NOT NULL,
            invoice_data TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

def luu_hoa_don_db(tenant_name, room_code, billing_period, total_amount, invoice_text, invoice_data):
    conn = ket_noi_db()
    conn.execute(
        "INSERT INTO invoices (created_at, tenant_name, room_code, billing_period, total_amount, invoice_text, invoice_data) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tenant_name, room_code, billing_period,
         float(total_amount), invoice_text, json.dumps(invoice_data, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

def lay_hoa_don_db():
    conn = ket_noi_db()
    rows = conn.execute("SELECT * FROM invoices ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def xoa_hoa_don_db(invoice_id):
    conn = ket_noi_db()
    conn.execute("DELETE FROM invoices WHERE id = ?", (int(invoice_id),))
    conn.commit()
    conn.close()

def xoa_tat_ca_hoa_don_db():
    conn = ket_noi_db()
    conn.execute("DELETE FROM invoices")
    conn.commit()
    conn.close()

# ============================================================
# HÀM HỖ TRỢ
# ============================================================
def dinh_dang_tien(so_tien):
    return f"{so_tien:,.0f}".replace(",", ".") + " VNĐ"

def goi_openrouter(api_key, model, messages):
    """Gọi OpenRouter Chat Completions API."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-OpenRouter-Title": "App Tinh Tien Phong Tro"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 900
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"OpenRouter trả về lỗi {response.status_code}: {detail}")
    data = response.json()
    return data["choices"][0]["message"]["content"]

def tao_noi_dung_hoa_don(thang_nam, ten_khach, ma_phong, dien_cu, dien_moi,
                         nuoc_cu, nuoc_moi, so_dien, so_nuoc, gia_phong,
                         gia_dien, gia_nuoc, gia_wifi, gia_rac, tien_dien,
                         tien_nuoc, tong_tien, so_nguoi, tien_moi_nguoi):
    ngay_lap = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""HOA DON TIEN PHONG TRO
==================================================
Ma phong: {ma_phong or 'Chua nhap'}
Khach thue: {ten_khach or 'Chua nhap'}
Ky thanh toan: {thang_nam or 'Chua nhap'}
Ngay lap hoa don: {ngay_lap}
--------------------------------------------------
CHI SO TIEU THU
Dien cu: {dien_cu} kWh
Dien moi: {dien_moi} kWh
Dien tieu thu: {so_dien} kWh
Nuoc cu: {nuoc_cu} khoi
Nuoc moi: {nuoc_moi} khoi
Nuoc tieu thu: {so_nuoc} khoi
--------------------------------------------------
CHI TIET THANH TOAN
Tien phong: {dinh_dang_tien(gia_phong)}
Tien dien: {so_dien} x {dinh_dang_tien(gia_dien)} = {dinh_dang_tien(tien_dien)}
Tien nuoc: {so_nuoc} x {dinh_dang_tien(gia_nuoc)} = {dinh_dang_tien(tien_nuoc)}
Tien Wifi: {dinh_dang_tien(gia_wifi)}
Tien rac va dich vu: {dinh_dang_tien(gia_rac)}
==================================================
TONG CONG: {dinh_dang_tien(tong_tien)}
So thanh vien: {so_nguoi}
Tien moi nguoi (chia deu): {dinh_dang_tien(tien_moi_nguoi)}
==================================================
Cam on ban da thanh toan!
"""

# ============================================================
# TIÊU ĐỀ VÀ HÌNH ẢNH
# ============================================================
if IMAGE_PATH:
    try:
        st.image(IMAGE_PATH, use_container_width=True)
    except Exception:
        st.caption("📷 Muốn hiển thị ảnh, hãy đặt file logo.jpg cạnh app.py hoặc sửa IMAGE_PATH đúng tên file ảnh.")

st.title("🏠 Hệ Thống Tính Tiền Phòng Trọ Tự Động. Đề tài 1")
st.write("Ứng dụng hỗ trợ chủ trọ tính toán và xuất hóa đơn nhanh chóng.")
st.divider()

# ============================================================
# SIDEBAR: BẢNG GIÁ + API KEY
# ============================================================
st.sidebar.header("⚙️ Cấu Hình Bảng Giá")
gia_phong = st.sidebar.number_input("Tiền phòng cố định (VNĐ):", min_value=0, value=2500000, step=100000)
gia_dien = st.sidebar.number_input("Giá điện (VNĐ/kWh):", min_value=0, value=3500, step=100)
gia_nuoc = st.sidebar.number_input("Giá nước (VNĐ/khối):", min_value=0, value=15000, step=500)
gia_wifi = st.sidebar.number_input("Tiền Wifi/Phòng (VNĐ):", min_value=0, value=100000, step=10000)
gia_rac = st.sidebar.number_input("Tiền rác & dịch vụ (VNĐ):", min_value=0, value=50000, step=5000)

st.sidebar.divider()
st.sidebar.header("🤖 Cấu hình Chatbot AI")
secret_key = ""
try:
    secret_key = st.secrets.get("OPENROUTER_API_KEY", "")
except Exception:
    secret_key = ""
api_key_nhap = st.sidebar.text_input(
    "OpenRouter API Key",
    value="",
    type="password",
    help="Khuyến nghị lưu key trong Streamlit Secrets thay vì nhập công khai."
)
api_key = api_key_nhap.strip() or secret_key
model = st.sidebar.text_input(
    "Tên model OpenRouter",
    value="openai/gpt-4o-mini",
    help="Hãy chọn model còn hoạt động trong danh mục OpenRouter; chi phí phụ thuộc model."
)
if api_key:
    st.sidebar.success("Đã có API Key (được che trên giao diện).")
else:
    st.sidebar.info("Nhập API Key để bật chatbot AI.")

# ============================================================
# NHẬP THÔNG TIN KHÁCH THUÊ / KỲ THANH TOÁN
# ============================================================
st.header("🧾 Thông Tin Hóa Đơn")
col_a, col_b = st.columns(2)
with col_a:
    ten_khach = st.text_input("Tên khách thuê:", placeholder="Ví dụ: Nguyễn Văn A")
    ma_phong = st.text_input("Mã phòng:", placeholder="Ví dụ: P101")
with col_b:
    thang_nam = st.text_input("Kỳ thanh toán:", value=datetime.now().strftime("%m/%Y"), placeholder="Ví dụ: 10/2026")

# ============================================================
# NHẬP SỐ LIỆU TIÊU THỤ
# ============================================================
st.header("📝 Nhập Số Liệu Tiêu Thụ")
col1, col2 = st.columns(2)
with col1:
    st.subheader("⚡ Chỉ số Điện")
    dien_cu = st.number_input("Số điện CŨ (kWh):", min_value=0, value=1200)
    dien_moi = st.number_input("Số điện MỚI (kWh):", min_value=0, value=1350)
with col2:
    st.subheader("💧 Chỉ số Nước")
    nuoc_cu = st.number_input("Số nước CŨ (khối):", min_value=0, value=450)
    nuoc_moi = st.number_input("Số nước MỚI (khối):", min_value=0, value=462)

# ============================================================
# TÍNH TOÁN VÀ HÓA ĐƠN
# ============================================================
so_dien_tieu_thu = dien_moi - dien_cu
so_nuoc_tieu_thu = nuoc_moi - nuoc_cu

if so_dien_tieu_thu < 0 or so_nuoc_tieu_thu < 0:
    st.error("❌ Lỗi: Số mới không được nhỏ hơn số cũ! Vui lòng kiểm tra lại.")
else:
    tien_dien = so_dien_tieu_thu * gia_dien
    tien_nuoc = so_nuoc_tieu_thu * gia_nuoc
    tong_tien = gia_phong + tien_dien + tien_nuoc + gia_wifi + gia_rac

    st.divider()
    st.header("📊 Hóa Đơn Tiền Phòng Chi Tiết")
    st.metric(label="💰 TỔNG SỐ TIỀN CẦN THANH TOÁN", value=dinh_dang_tien(tong_tien))

    st.markdown(f"""
    | Khoản mục | Chi tiết chỉ số | Thành tiền (VNĐ) |
    | :--- | :--- | ---: |
    | **🏠 Tiền phòng cố định** | Gói cố định | {gia_phong:,.0f} |
    | **⚡ Tiền điện** | {so_dien_tieu_thu} kWh × {gia_dien:,.0f}đ | {tien_dien:,.0f} |
    | **💧 Tiền nước** | {so_nuoc_tieu_thu} khối × {gia_nuoc:,.0f}đ | {tien_nuoc:,.0f} |
    | **🌐 Tiền Wifi** | Gói cố định | {gia_wifi:,.0f} |
    | **🗑️ Tiền rác & dịch vụ** | Gói cố định | {gia_rac:,.0f} |
    | **💰 TỔNG CỘNG** | | **{tong_tien:,.0f}** |
    """)

    st.subheader("👥 Tính năng chia đều (Tùy chọn)")
    so_nguoi = st.slider("Số lượng thành viên trong phòng:", min_value=1, max_value=6, value=3)
    tien_moi_nguoi = tong_tien / so_nguoi
    st.info(f"👉 Mỗi người cần đóng: **{dinh_dang_tien(tien_moi_nguoi)}**")

    st.subheader("📱 Tin nhắn gửi nhanh")
    tin_nhan = (
        f"Thông báo tiền phòng tháng {thang_nam}:\n"
        f"- Khách thuê: {ten_khach or 'Chưa nhập'} | Phòng: {ma_phong or 'Chưa nhập'}\n"
        f"- Tiền phòng: {gia_phong:,.0f}đ\n"
        f"- Điện: {so_dien_tieu_thu} kWh ({tien_dien:,.0f}đ)\n"
        f"- Nước: {so_nuoc_tieu_thu} khối ({tien_nuoc:,.0f}đ)\n"
        f"- Wifi + Rác: {(gia_wifi + gia_rac):,.0f}đ\n"
        f"=> TỔNG: {tong_tien:,.0f}đ (Mỗi người: {tien_moi_nguoi:,.0f}đ). Các bạn chuyển khoản sớm nhé!"
    )
    st.text_area("Copy đoạn văn bản này để gửi cho phòng trọ:", value=tin_nhan, height=150)

    noi_dung_hoa_don = tao_noi_dung_hoa_don(
        thang_nam, ten_khach, ma_phong, dien_cu, dien_moi, nuoc_cu, nuoc_moi,
        so_dien_tieu_thu, so_nuoc_tieu_thu, gia_phong, gia_dien, gia_nuoc,
        gia_wifi, gia_rac, tien_dien, tien_nuoc, tong_tien, so_nguoi, tien_moi_nguoi
    )
    ten_file = f"hoa_don_{ma_phong or 'phong_tro'}_{thang_nam.replace('/', '-') or 'thang'}.txt"
    ten_file = "".join(c if c.isalnum() or c in "._-" else "_" for c in ten_file)
    st.download_button(
        "⬇️ Tải hóa đơn chi tiết (.txt)",
        data=noi_dung_hoa_don,
        file_name=ten_file,
        mime="text/plain",
        use_container_width=True
    )

    st.caption("Lưu hóa đơn vào lịch sử để Admin có thể xem, tải lại hoặc xóa sau này.")
    if st.button("💾 Lưu hóa đơn vào hệ thống", type="primary", use_container_width=True):
        invoice_data = {
            "tenant_name": ten_khach, "room_code": ma_phong, "billing_period": thang_nam,
            "electric_old": dien_cu, "electric_new": dien_moi, "electric_used": so_dien_tieu_thu,
            "water_old": nuoc_cu, "water_new": nuoc_moi, "water_used": so_nuoc_tieu_thu,
            "rent": gia_phong, "electric_price": gia_dien, "water_price": gia_nuoc,
            "wifi": gia_wifi, "trash": gia_rac, "electric_total": tien_dien,
            "water_total": tien_nuoc, "total": tong_tien, "members": so_nguoi,
            "per_person": tien_moi_nguoi
        }
        luu_hoa_don_db(ten_khach, ma_phong, thang_nam, tong_tien, noi_dung_hoa_don, invoice_data)
        st.success("Đã lưu hóa đơn vào hệ thống. Admin có thể quản lý trong mục Quản trị Admin bên dưới.")

# ============================================================
# CHATBOT AI
# ============================================================
st.divider()
st.header("🤖 Trợ Lý AI Phòng Trọ")
st.caption("Hỏi về cách tính tiền phòng, điện, nước, hóa đơn hoặc các chủ đề khác. Câu trả lời được tạo bởi model bạn chọn trên OpenRouter.")

if "chat_history_phongtro" not in st.session_state:
    st.session_state.chat_history_phongtro = [
        {"role": "assistant", "content": "Xin chào! Tôi là trợ lý AI. Tôi có thể giải thích cách tính hóa đơn phòng trọ hoặc trả lời câu hỏi của bạn. Bạn muốn hỏi gì?"}
    ]

for message in st.session_state.chat_history_phongtro:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

cau_hoi = st.chat_input("Nhập câu hỏi cho chatbot AI...")
if cau_hoi:
    st.session_state.chat_history_phongtro.append({"role": "user", "content": cau_hoi})
    with st.chat_message("user"):
        st.markdown(cau_hoi)

    if not api_key:
        phan_hoi = "Chatbot chưa được kết nối. Vui lòng nhập OpenRouter API Key ở thanh bên trái hoặc cấu hình OPENROUTER_API_KEY trong Streamlit Secrets."
        st.session_state.chat_history_phongtro.append({"role": "assistant", "content": phan_hoi})
        with st.chat_message("assistant"):
            st.markdown(phan_hoi)
    else:
        system_prompt = (
            "Bạn là trợ lý AI thân thiện cho ứng dụng tính tiền phòng trọ. "
            "Trả lời bằng tiếng Việt rõ ràng, hữu ích; có thể trả lời cả câu hỏi ngoài chủ đề phòng trọ. "
            "Khi giải thích hóa đơn, không tự bịa dữ liệu. Nếu cần số liệu thực tế, hãy yêu cầu người dùng cung cấp. "
            "Không khẳng định đã truy cập Internet trực tiếp nếu không có công cụ tìm kiếm."
        )
        messages = [{"role": "system", "content": system_prompt}]
        # Gửi một phần lịch sử gần nhất để giữ ngữ cảnh và hạn chế chi phí.
        messages.extend(st.session_state.chat_history_phongtro[-12:])
        with st.chat_message("assistant"):
            with st.spinner("AI đang suy nghĩ..."):
                try:
                    phan_hoi = goi_openrouter(api_key, model.strip(), messages)
                    st.markdown(phan_hoi)
                    st.session_state.chat_history_phongtro.append(
                        {"role": "assistant", "content": phan_hoi}
                    )
                except requests.exceptions.Timeout:
                    phan_hoi = "Yêu cầu bị quá thời gian chờ. Bạn hãy thử lại."
                    st.error(phan_hoi)
                    st.session_state.chat_history_phongtro.append({"role": "assistant", "content": phan_hoi})
                except requests.exceptions.RequestException as e:
                    phan_hoi = f"Không kết nối được OpenRouter: {e}"
                    st.error(phan_hoi)
                    st.session_state.chat_history_phongtro.append({"role": "assistant", "content": phan_hoi})
                except Exception as e:
                    phan_hoi = f"Không thể nhận phản hồi từ AI: {e}"
                    st.error(phan_hoi)
                    st.session_state.chat_history_phongtro.append({"role": "assistant", "content": phan_hoi})

if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
    st.session_state.chat_history_phongtro = [
        {"role": "assistant", "content": "Xin chào! Tôi là trợ lý AI. Bạn muốn hỏi gì?"}
    ]
    st.rerun()


# ============================================================
# KHU VỰC QUẢN TRỊ ADMIN: XEM / TẢI / XÓA HÓA ĐƠN
# ============================================================
st.divider()
st.header("🔐 Quản trị Admin")
st.write("Đăng nhập để xem lịch sử hóa đơn đã lưu, tải lại hóa đơn hoặc xóa các bản ghi.")

admin_password_from_secrets = ""
try:
    admin_password_from_secrets = st.secrets.get("ADMIN_PASSWORD", "")
except Exception:
    admin_password_from_secrets = ""
ADMIN_PASSWORD = admin_password_from_secrets or "admin123"

if "admin_logged_in_phongtro" not in st.session_state:
    st.session_state.admin_logged_in_phongtro = False

if not st.session_state.admin_logged_in_phongtro:
    with st.form("admin_login_form"):
        admin_password_input = st.text_input("Mật khẩu Admin", type="password", placeholder="Nhập mật khẩu quản trị")
        login_clicked = st.form_submit_button("🔓 Đăng nhập Admin", use_container_width=True)
    if login_clicked:
        if admin_password_input == ADMIN_PASSWORD:
            st.session_state.admin_logged_in_phongtro = True
            st.success("Đăng nhập Admin thành công.")
            st.rerun()
        else:
            st.error("Mật khẩu chưa đúng. Vui lòng thử lại.")
    if not admin_password_from_secrets:
        st.warning("Mật khẩu mặc định hiện tại là admin123. Hãy đặt ADMIN_PASSWORD trong Streamlit Secrets trước khi triển khai công khai.")
else:
    head_col1, head_col2 = st.columns([4, 1])
    with head_col1:
        st.success("Bạn đang đăng nhập với quyền quản trị.")
    with head_col2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.admin_logged_in_phongtro = False
            st.rerun()

    tab_tongquan, tab_hoadon, tab_caidat = st.tabs(["📊 Tổng quan", "🧾 Quản lý hóa đơn", "⚙️ Cấu hình hiện tại"])
    invoices = lay_hoa_don_db()
    with tab_tongquan:
        tong_so_hoa_don = len(invoices)
        tong_doanh_thu = sum(float(row["total_amount"]) for row in invoices)
        phong_da_luu = len({row["room_code"] for row in invoices if row["room_code"]})
        k1, k2, k3 = st.columns(3)
        k1.metric("Tổng hóa đơn đã lưu", f"{tong_so_hoa_don}")
        k2.metric("Tổng tiền hóa đơn đã lưu", dinh_dang_tien(tong_doanh_thu))
        k3.metric("Số phòng có hóa đơn", f"{phong_da_luu}")
        st.caption("Thống kê chỉ tính các hóa đơn đã bấm nút Lưu hóa đơn vào hệ thống.")
    with tab_hoadon:
        st.subheader("📚 Danh sách hóa đơn")
        if not invoices:
            st.info("Chưa có hóa đơn nào được lưu. Hãy tính hóa đơn ở phía trên và bấm ‘Lưu hóa đơn vào hệ thống’.")
        else:
            search_text = st.text_input("🔎 Tìm theo tên khách, mã phòng hoặc kỳ thanh toán", key="admin_invoice_search")
            filtered_invoices = [
                row for row in invoices
                if search_text.strip().lower() in " ".join([
                    str(row["tenant_name"] or ""), str(row["room_code"] or ""), str(row["billing_period"] or "")
                ]).lower()
            ]
            st.caption(f"Đang hiển thị {len(filtered_invoices)} / {len(invoices)} hóa đơn")
            for row in filtered_invoices:
                with st.expander(
                    f"#{row['id']} · Phòng {row['room_code'] or 'Chưa nhập'} · {row['tenant_name'] or 'Chưa nhập tên'} · {row['billing_period'] or 'Chưa có kỳ'} · {dinh_dang_tien(row['total_amount'])}"
                ):
                    st.write(f"**Ngày lưu:** {row['created_at']}")
                    st.text(row["invoice_text"])
                    safe_room = "".join(c if c.isalnum() or c in "_-." else "_" for c in (row["room_code"] or "phong_tro"))
                    safe_period = "".join(c if c.isalnum() or c in "_-." else "_" for c in (row["billing_period"] or "ky_thanh_toan").replace("/", "-"))
                    dcol, xcol = st.columns([2, 1])
                    with dcol:
                        st.download_button(
                            "⬇️ Tải hóa đơn này",
                            data=row["invoice_text"],
                            file_name=f"hoa_don_{safe_room}_{safe_period}_{row['id']}.txt",
                            mime="text/plain",
                            key=f"download_invoice_{row['id']}",
                            use_container_width=True
                        )
                    with xcol:
                        if st.button("🗑️ Xóa hóa đơn", key=f"delete_invoice_{row['id']}", use_container_width=True):
                            xoa_hoa_don_db(row["id"])
                            st.success(f"Đã xóa hóa đơn #{row['id']}.")
                            st.rerun()
            if invoices:
                with st.expander("⚠️ Xóa toàn bộ lịch sử hóa đơn"):
                    st.warning("Thao tác này xóa tất cả hóa đơn đã lưu trong cơ sở dữ liệu và không thể hoàn tác.")
                    xac_nhan_xoa = st.checkbox("Tôi xác nhận muốn xóa toàn bộ hóa đơn", key="confirm_delete_all_invoices")
                    if st.button("Xóa toàn bộ hóa đơn", type="primary", disabled=not xac_nhan_xoa, key="delete_all_invoices"):
                        xoa_tat_ca_hoa_don_db()
                        st.success("Đã xóa toàn bộ lịch sử hóa đơn.")
                        st.rerun()
    with tab_caidat:
        st.subheader("Bảng giá đang áp dụng trên phiên hiện tại")
        st.dataframe([
            {"Khoản mục": "Tiền phòng", "Đơn giá (VNĐ)": gia_phong},
            {"Khoản mục": "Điện / kWh", "Đơn giá (VNĐ)": gia_dien},
            {"Khoản mục": "Nước / khối", "Đơn giá (VNĐ)": gia_nuoc},
            {"Khoản mục": "Wifi / phòng", "Đơn giá (VNĐ)": gia_wifi},
            {"Khoản mục": "Rác & dịch vụ", "Đơn giá (VNĐ)": gia_rac},
        ], use_container_width=True, hide_index=True)
        st.info("Điều chỉnh bảng giá ở thanh bên trái. Bảng giá hiện tại không tự lưu sau khi khởi động lại ứng dụng; hóa đơn đã lưu giữ nguyên số liệu tại thời điểm tạo.")
