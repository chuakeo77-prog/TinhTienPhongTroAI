import os
import streamlit as st

# =========================================================
# APP TÍNH TIỀN PHÒNG TRỌ - CHATBOT Ở TRANG CHÍNH, ADMIN RIÊNG
# Chạy: streamlit run app.py
# Chatbot AI tùy chọn: cài requests và cấu hình OPENAI_API_KEY
# trong .streamlit/secrets.toml. Không có API key thì chatbot
# vẫn trả lời các câu hỏi thường gặp theo dữ liệu ứng dụng.
# =========================================================

st.set_page_config(
    page_title="Hệ Thống Quản Lý Phòng Trọ",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Khởi tạo dữ liệu phiên ----------
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
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": (
                "Xin chào! Tôi là chatbot hỗ trợ quản lý phòng trọ. "
                "Bạn có thể hỏi cách tính tiền phòng, tiền điện/nước, "
                "tổng hóa đơn hoặc số tiền mỗi người cần đóng."
            ),
        }
    ]


def vnd(value):
    """Định dạng tiền Việt Nam."""
    return f"{value:,.0f} VNĐ"


def calculate_bill():
    dien_tieu_thu = st.session_state.dien_moi - st.session_state.dien_cu
    nuoc_tieu_thu = st.session_state.nuoc_moi - st.session_state.nuoc_cu
    if dien_tieu_thu < 0 or nuoc_tieu_thu < 0:
        return {"error": "Chỉ số mới không được nhỏ hơn chỉ số cũ."}
    tien_dien = dien_tieu_thu * st.session_state.gia_dien
    tien_nuoc = nuoc_tieu_thu * st.session_state.gia_nuoc
    tong = (
        st.session_state.gia_phong
        + tien_dien
        + tien_nuoc
        + st.session_state.gia_wifi
        + st.session_state.gia_rac
    )
    so_nguoi = max(1, int(st.session_state.so_nguoi))
    return {
        "dien_tieu_thu": dien_tieu_thu,
        "nuoc_tieu_thu": nuoc_tieu_thu,
        "tien_dien": tien_dien,
        "tien_nuoc": tien_nuoc,
        "tong": tong,
        "moi_nguoi": tong / so_nguoi,
    }


def bill_context():
    b = calculate_bill()
    if "error" in b:
        return b["error"]
    return (
        f"Thông tin hóa đơn hiện tại của {st.session_state.ten_phong}: "
        f"tiền phòng {vnd(st.session_state.gia_phong)}; điện dùng "
        f"{b['dien_tieu_thu']} kWh, thành tiền {vnd(b['tien_dien'])}; "
        f"nước dùng {b['nuoc_tieu_thu']} khối, thành tiền {vnd(b['tien_nuoc'])}; "
        f"Wi-Fi {vnd(st.session_state.gia_wifi)}; phí rác và dịch vụ "
        f"{vnd(st.session_state.gia_rac)}; tổng cộng {vnd(b['tong'])}; "
        f"chia {st.session_state.so_nguoi} người là khoảng {vnd(b['moi_nguoi'])}/người. "
        f"Đơn giá điện {vnd(st.session_state.gia_dien)}/kWh, "
        f"đơn giá nước {vnd(st.session_state.gia_nuoc)}/khối."
    )


def local_chat_reply(question):
    """Trả lời cơ bản khi chưa cấu hình API chatbot AI."""
    q = question.lower().strip()
    b = calculate_bill()
    if "error" in b:
        return "Chưa thể tính hóa đơn vì chỉ số mới đang nhỏ hơn chỉ số cũ. Hãy kiểm tra lại chỉ số điện và nước."
    if any(k in q for k in ["tổng tiền", "tổng hóa đơn", "bao nhiêu tiền", "phải đóng", "thanh toán", "hóa đơn hiện tại"]):
        return bill_context()
    if "điện" in q:
        return (
            f"Tiền điện được tính bằng (chỉ số mới − chỉ số cũ) × đơn giá. "
            f"Phòng hiện dùng {b['dien_tieu_thu']} kWh × {vnd(st.session_state.gia_dien)}/kWh "
            f"= {vnd(b['tien_dien'])}."
        )
    if "nước" in q:
        return (
            f"Tiền nước được tính bằng (chỉ số mới − chỉ số cũ) × đơn giá. "
            f"Phòng hiện dùng {b['nuoc_tieu_thu']} khối × {vnd(st.session_state.gia_nuoc)}/khối "
            f"= {vnd(b['tien_nuoc'])}."
        )
    if any(k in q for k in ["mỗi người", "chia tiền", "chia đều", "đầu người"]):
        return (
            f"Tổng hóa đơn hiện tại là {vnd(b['tong'])}. "
            f"Chia cho {st.session_state.so_nguoi} người thì mỗi người đóng khoảng {vnd(b['moi_nguoi'])}."
        )
    if any(k in q for k in ["giá", "đơn giá", "wifi", "rác", "dịch vụ", "tiền phòng"]):
        return bill_context()
    if any(k in q for k in ["xin chào", "chào", "hello", "hi "]):
        return "Xin chào! Bạn muốn xem tổng hóa đơn, cách tính tiền điện/nước hay số tiền mỗi người cần đóng?"
    return (
        "Tôi có thể hỗ trợ các câu hỏi về tổng hóa đơn, tiền điện, tiền nước, "
        "tiền phòng, Wi-Fi, phí rác và chia tiền theo đầu người. "
        "Ví dụ: “Tổng tiền phòng hiện tại là bao nhiêu?”"
    )


def get_chat_reply(question):
    """Dùng OpenAI API nếu đã cấu hình; nếu không, dùng trả lời cục bộ."""
    api_key = None
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return local_chat_reply(question)

    try:
        import requests

        context = bill_context()
        messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là chatbot hỗ trợ quản lý nhà trọ, trả lời bằng tiếng Việt "
                    "ngắn gọn, dễ hiểu. Chỉ sử dụng dữ liệu hóa đơn được cung cấp khi "
                    "trả lời về số tiền; không tự bịa số liệu. Nếu câu hỏi ngoài phạm vi, "
                    "hãy nói rõ giới hạn. Dữ liệu hóa đơn hiện tại: " + context
                ),
            }
        ]
        # Chỉ gửi một số lượt gần nhất để hạn chế lượng dữ liệu gửi đi.
        for item in st.session_state.chat_history[-8:]:
            messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": question})

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.3,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return (
            "Hiện chatbot AI chưa kết nối được. Tôi sẽ trả lời theo chức năng cơ bản: "
            + local_chat_reply(question)
        )


# ---------- Điều hướng ----------
st.sidebar.title("🏠 Quản lý phòng trọ")
page = st.sidebar.radio(
    "Điều hướng",
    ["💬 Chatbot quản lý", "🛠️ Admin quản lý"],
    index=0,
)
st.sidebar.caption("Chatbot nằm ở trang chính. Cấu hình giá được chuyển sang trang Admin.")

# ---------- Trang chính: chatbot ở đầu trang ----------
if page == "💬 Chatbot quản lý":
    st.title("💬 Chatbot hỗ trợ quản lý phòng trọ")
    st.write(
        "Hỏi nhanh về hóa đơn, tiền điện, tiền nước và số tiền mỗi người cần đóng. "
        "Phần tính hóa đơn vẫn nằm bên dưới."
    )

    with st.expander("📌 Thông tin hóa đơn hiện tại", expanded=False):
        st.write(bill_context())

    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    prompt = st.chat_input("Nhập câu hỏi, ví dụ: Tổng tiền phòng tháng này là bao nhiêu?")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        reply = get_chat_reply(prompt)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

    chat_col1, chat_col2 = st.columns([1, 5])
    with chat_col1:
        if st.button("🧹 Xóa hội thoại", use_container_width=True):
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": "Đã xóa hội thoại. Bạn có thể bắt đầu hỏi câu mới.",
                }
            ]
            st.rerun()

    st.divider()
    st.header("📝 Nhập số liệu tiêu thụ")
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

    b = calculate_bill()
    if "error" in b:
        st.error("❌ " + b["error"] + " Vui lòng kiểm tra lại các chỉ số.")
    else:
        st.divider()
        st.header("📊 Hóa đơn tiền phòng chi tiết")
        st.metric("💰 Tổng số tiền cần thanh toán", vnd(b["tong"]))

        details = [
            {"Khoản mục": "🏠 Tiền phòng cố định", "Chi tiết chỉ số": "Gói cố định", "Thành tiền (VNĐ)": f"{st.session_state.gia_phong:,.0f}"},
            {"Khoản mục": "⚡ Tiền điện", "Chi tiết chỉ số": f"{b['dien_tieu_thu']} kWh × {st.session_state.gia_dien:,.0f}đ", "Thành tiền (VNĐ)": f"{b['tien_dien']:,.0f}"},
            {"Khoản mục": "💧 Tiền nước", "Chi tiết chỉ số": f"{b['nuoc_tieu_thu']} khối × {st.session_state.gia_nuoc:,.0f}đ", "Thành tiền (VNĐ)": f"{b['tien_nuoc']:,.0f}"},
            {"Khoản mục": "🌐 Tiền Wi-Fi", "Chi tiết chỉ số": "Gói cố định", "Thành tiền (VNĐ)": f"{st.session_state.gia_wifi:,.0f}"},
            {"Khoản mục": "🗑️ Tiền rác & dịch vụ", "Chi tiết chỉ số": "Gói cố định", "Thành tiền (VNĐ)": f"{st.session_state.gia_rac:,.0f}"},
        ]
        st.table(details)

        st.subheader("👥 Chia đều tiền theo đầu người")
        st.info(f"Mỗi người cần đóng: **{vnd(b['moi_nguoi'])}**")

        thang = st.session_state.thang_tinh.strip() or "tháng này"
        ten_khach = f" - Khách thuê: {st.session_state.ten_khach}" if st.session_state.ten_khach.strip() else ""
        tin_nhan = (
            f"THÔNG BÁO TIỀN PHÒNG {st.session_state.ten_phong} ({thang}){ten_khach}\n"
            f"- Tiền phòng: {vnd(st.session_state.gia_phong)}\n"
            f"- Điện: {b['dien_tieu_thu']} kWh ({vnd(b['tien_dien'])})\n"
            f"- Nước: {b['nuoc_tieu_thu']} khối ({vnd(b['tien_nuoc'])})\n"
            f"- Wi-Fi: {vnd(st.session_state.gia_wifi)}\n"
            f"- Rác & dịch vụ: {vnd(st.session_state.gia_rac)}\n"
            f"=> TỔNG: {vnd(b['tong'])}\n"
            f"=> Mỗi người ({st.session_state.so_nguoi} người): {vnd(b['moi_nguoi'])}\n"
            "Vui lòng thanh toán đúng hạn. Cảm ơn mọi người!"
        )
        st.subheader("📱 Tin nhắn gửi nhanh qua Zalo")
        st.text_area("Sao chép nội dung tin nhắn", value=tin_nhan, height=220)
        st.download_button(
            "⬇️ Tải hóa đơn dạng TXT",
            data=tin_nhan,
            file_name=f"hoa_don_{st.session_state.ten_phong.replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=False,
        )

# ---------- Trang riêng: Admin ----------
else:
    st.title("🛠️ Trang Admin quản lý")
    st.write("Thiết lập đơn giá và thông tin mặc định. Các thay đổi áp dụng ngay trong phiên sử dụng hiện tại.")
    st.warning(
        "Lưu ý: phiên bản này lưu cấu hình trong session của Streamlit; "
        "chưa có đăng nhập/phân quyền hoặc cơ sở dữ liệu lưu bền vững."
    )

    with st.form("admin_price_form"):
        st.subheader("⚙️ Cấu hình bảng giá")
        a1, a2 = st.columns(2)
        with a1:
            gia_phong = st.number_input("Tiền phòng cố định (VNĐ)", min_value=0, step=100000, value=int(st.session_state.gia_phong))
            gia_dien = st.number_input("Giá điện (VNĐ/kWh)", min_value=0, step=100, value=int(st.session_state.gia_dien))
            gia_nuoc = st.number_input("Giá nước (VNĐ/khối)", min_value=0, step=500, value=int(st.session_state.gia_nuoc))
        with a2:
            gia_wifi = st.number_input("Tiền Wi-Fi/phòng (VNĐ)", min_value=0, step=10000, value=int(st.session_state.gia_wifi))
            gia_rac = st.number_input("Tiền rác & dịch vụ (VNĐ)", min_value=0, step=5000, value=int(st.session_state.gia_rac))
            thang_tinh = st.text_input("Tháng tính hóa đơn (ví dụ: 10/2026)", value=st.session_state.thang_tinh)
        submitted = st.form_submit_button("💾 Lưu cấu hình", use_container_width=True)

    if submitted:
        st.session_state.gia_phong = gia_phong
        st.session_state.gia_dien = gia_dien
        st.session_state.gia_nuoc = gia_nuoc
        st.session_state.gia_wifi = gia_wifi
        st.session_state.gia_rac = gia_rac
        st.session_state.thang_tinh = thang_tinh
        st.success("Đã cập nhật cấu hình giá cho phiên sử dụng hiện tại.")
        st.rerun()

    st.divider()
    st.subheader("📋 Xem nhanh bảng giá đang áp dụng")
    st.table([
        {"Khoản mục": "Tiền phòng", "Đơn giá": vnd(st.session_state.gia_phong)},
        {"Khoản mục": "Điện", "Đơn giá": f"{vnd(st.session_state.gia_dien)}/kWh"},
        {"Khoản mục": "Nước", "Đơn giá": f"{vnd(st.session_state.gia_nuoc)}/khối"},
        {"Khoản mục": "Wi-Fi", "Đơn giá": vnd(st.session_state.gia_wifi)},
        {"Khoản mục": "Rác & dịch vụ", "Đơn giá": vnd(st.session_state.gia_rac)},
    ])

    st.subheader("🧾 Hóa đơn hiện tại")
    st.write(bill_context())
