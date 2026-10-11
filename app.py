st.divider()
    st.subheader("📚 Ảnh đã lưu")
    image_files = sorted(
        [f for f in GALLERY_DIR.iterdir()
         if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not image_files:
        st.info("Thư viện chưa có ảnh. Chọn ảnh ở phía trên để bắt đầu.")
    else:
        st.caption(f"Tổng số ảnh: {len(image_files)}")
        columns_per_row = 3
        for start in range(0, len(image_files), columns_per_row):
            cols = st.columns(columns_per_row)
            for col, image_path in zip(cols, image_files[start:start + columns_per_row]):
                with col:
                    st.image(str(image_path), use_container_width=True)
                    caption_path = image_path.with_suffix(image_path.suffix + ".txt")
                    caption_text = ""
                    if caption_path.is_file():
                        try:
                            caption_text = caption_path.read_text(encoding="utf-8").strip()
                        except OSError:
                            caption_text = ""
                    st.caption(caption_text or image_path.name)
                    st.caption(f"Dung lượng: {image_path.stat().st_size / (1024 * 1024):.2f} MB")
                    with st.expander("🗑️ Tùy chọn ảnh", expanded=False):
                        if st.button("Xóa ảnh này", key=f"delete_gallery_{image_path.name}"):
                            try:
                                image_path.unlink(missing_ok=True)
                                caption_path.unlink(missing_ok=True)
                                st.success("Đã xóa ảnh khỏi thư viện.")
                                st.rerun()
                            except OSError as exc:
                                st.error(f"Không thể xóa ảnh: {exc}")

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
                            
