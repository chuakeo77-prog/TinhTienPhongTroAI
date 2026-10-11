import streamlit as st

# Cấu hình trang web (Tên hiển thị trên tab trình duyệt)
st.set_page_config(page_title="App Tính Tiền Phòng Trọ ", page_icon="🏠", layout="centered")

# Tiêu đề ứng dụng
st.title("🏠 Hệ Thống Tính Tiền Phòng Trọ Tự Động. Đề tài 1  ")
st.write("Ứng dụng hỗ trợ chủ trọ tính toán và xuất hóa đơn nhanh chóng.")

st.divider() # Thanh chia cắt giao diện

# --- PHẦN 1: CÀI ĐẶT ĐỊNH MỨC GIÁ (Bên thanh menu cánh trái - Sidebar) ---
st.sidebar.header("⚙️ Cấu Hình Bảng Giá")
gia_phong = st.sidebar.number_input("Tiền phòng cố định (VNĐ):", min_value=0, value=2500000, step=100000)
gia_dien = st.sidebar.number_input("Giá điện (VNĐ/kWh):", min_value=0, value=3500, step=100)
gia_nuoc = st.sidebar.number_input("Giá nước (VNĐ/khối):", min_value=0, value=15000, step=500)
gia_wifi = st.sidebar.number_input("Tiền Wifi/Phòng (VNĐ):", min_value=0, value=100000, step=10000)
gia_rac = st.sidebar.number_input("Tiền rác & dịch vụ (VNĐ):", min_value=0, value=50000, step=5000)

# --- PHẦN 2: NHẬP SỐ LIỆU THÁNG NÀY (Giao diện chính) ---
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

# --- PHẦN 3: TÍNH TOÁN LOGIC ---
so_dien_tieu_thu = dien_moi - dien_cu
so_nuoc_tieu_thu = nuoc_moi - nuoc_cu

if so_dien_tieu_thu < 0 or so_nuoc_tieu_thu < 0:
    st.error("❌ Lỗi: Số mới không được nhỏ hơn số cũ! Vui lòng kiểm tra lại.")
else:
    tien_dien = so_dien_tieu_thu * gia_dien
    tien_nuoc = so_nuoc_tieu_thu * gia_nuoc
    tong_tien = gia_phong + tien_dien + tien_nuoc + gia_wifi + gia_rac

    st.divider()

    # --- PHẦN 4: HIỂN THỊ HÓA ĐƠN CHI TIẾT ---
    st.header("📊 Hóa Đơn Tiền Phòng Chi Tiết")
    
    # Hiển thị tổng tiền lớn, nổi bật
    st.metric(label="💰 TỔNG SỐ TIỀN CẦN THANH TOÁN", value=f"{tong_tien:,.0f} VNĐ")

    # Tạo bảng chi tiết cấu thành tiền
    st.markdown(f"""
    | Khoản mục | Chi tiết chỉ số | Thành tiền (VNĐ) |
    | :--- | :--- | :--- |
    | **🏠 Tiền phòng cố định** | | {gia_phong:,.0f} |
    | **⚡ Tiền điện** | {so_dien_tieu_thu} kWh x {gia_dien:,.0f}đ | {tien_dien:,.0f} |
    | **💧 Tiền nước** | {so_nuoc_tieu_thu} khối x {gia_nuoc:,.0f}đ | {tien_nuoc:,.0f} |
    | **🌐 Tiền Wifi** | Gói cố định | {gia_wifi:,.0f} |
| **🗑️ Tiền rác & dịch vụ**| Gói cố định | {gia_rac:,.0f} |
""")

    # Tính năng phụ: Chia đều tiền theo đầu người
    st.subheader("👥 Tính năng chia đều (Tùy chọn)")
    so_nguoi = st.slider("Số lượng thành viên trong phòng:", min_value=1, max_value=6, value=3)
    tien_moi_nguoi = tong_tien / so_nguoi
    st.info(f"👉 Mỗi người cần đóng: **{tien_moi_nguoi:,.0f} VNĐ**")

    # Tạo nội dung văn bản để copy gửi Zalo nhanh
    st.subheader("📱 Tin nhắn gửi nhanh")
    tin_nhan = f"Thông báo tiền phòng tháng này:\n- Tiền phòng: {gia_phong:,.0f}đ\n- Điện: {so_dien_tieu_thu}kWh ({tien_dien:,.0f}đ)\n- Nước: {so_nuoc_tieu_thu} khối ({tien_nuoc:,.0f}đ)\n- Wifi + Rác: {(gia_wifi+gia_rac):,.0f}đ\n=> TỔNG: {tong_tien:,.0f}đ (Mỗi người: {tien_moi_nguoi:,.0f}đ). Các bạn chuyển khoản sớm nhé!"
    st.text_area("Copy đoạn văn bản này để gửi cho phòng trọ:", value=tin_nhan, height=150)
