import streamlit as st
import requests
from datetime import datetime

# ============================================================
# CẤU HÌNH TRANG
# ============================================================
st.set_page_config(
    page_title="App Tính Tiền Phòng Trọ",
    page_icon="🏠",
    layout="centered"
)

# ============================================================
# HÌNH ẢNH / LOGO
# Đặt file ảnh cạnh app.py, ví dụ: logo.jpg hoặc nha_tro.png
# Có thể đổi IMAGE_PATH bên dưới theo tên file của bạn.
# ============================================================
IMAGE_PATH = "logo.jpg"

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
