import streamlit as st
import pandas as pd
from datetime import datetime, date
import os
import time
from database import init_db
from db_operations import (
    generate_handover_id,
    save_handover_safe,
    save_receive_safe,
    get_latest_handover,
    check_handover_received,
    get_dashboard_data,
    check_login,
    get_active_lines,
    get_all_lines,
    save_lines_config,
    get_handover_data_for_export,
    get_receive_data_for_export,
    get_combined_handover_receive_data,
    delete_handover_by_id,
    get_all_handovers_for_admin
)

# Cấu hình trang
st.set_page_config(page_title="Hệ thống Bàn Giao Ca", page_icon="🔄", layout="wide")

# Cached function để tối ưu performance
@st.cache_data(ttl=300)  # Cache 5 phút
def get_active_lines_cached():
    """Cached version of get_active_lines() để tránh query DB nhiều lần"""
    return get_active_lines()

# Custom CSS cho status colors và styling
st.markdown("""
<style>
/* OK - Green */
[data-baseweb="select"] [data-value="OK"] {
    background-color: rgba(34, 197, 94, 0.1) !important;
    border-color: #22C55E !important;
}

/* NOK - Red */
[data-baseweb="select"] [data-value="NOK"] {
    background-color: rgba(239, 68, 68, 0.1) !important;
    border-color: #EF4444 !important;
}

/* NA - Gray */
[data-baseweb="select"] [data-value="NA"] {
    background-color: rgba(156, 163, 175, 0.1) !important;
    border-color: #9CA3AF !important;
}

/* Style cho select khi đã chọn */
select:has(option[value="OK"]:checked) {
    background-color: rgba(34, 197, 94, 0.1) !important;
    border: 2px solid #22C55E !important;
}

select:has(option[value="NOK"]:checked) {
    background-color: rgba(239, 68, 68, 0.1) !important;
    border: 2px solid #EF4444 !important;
}

select:has(option[value="NA"]:checked) {
    background-color: rgba(156, 163, 175, 0.1) !important;
    border: 2px solid #9CA3AF !important;
}

/* Custom styling cho receive section */
.receive-category-box {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
    border-left: 4px solid #6c757d;
}

.receive-category-box.ok {
    border-left-color: #22C55E;
    background-color: rgba(34, 197, 94, 0.05);
}

.receive-category-box.nok {
    border-left-color: #EF4444;
    background-color: rgba(239, 68, 68, 0.05);
}

.receive-category-box.na {
    border-left-color: #9CA3AF;
    background-color: rgba(156, 163, 175, 0.05);
}

/* Dashboard cards */
.dashboard-card {
    background: white;
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid #007bff;
    margin-bottom: 15px;
}

.dashboard-card.success {
    border-left-color: #22C55E;
}

.dashboard-card.warning {
    border-left-color: #FFA500;
}

.dashboard-card.danger {
    border-left-color: #EF4444;
}

.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}

.status-badge.completed {
    background-color: #d4edda;
    color: #155724;
}

.status-badge.pending {
    background-color: #fff3cd;
    color: #856404;
}

.status-badge.not-started {
    background-color: #f8d7da;
    color: #721c24;
}

/* Warning box style */
.warning-box {
    background-color: #fff3cd;
    border: 2px solid #ffc107;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}

.error-box {
    background-color: #f8d7da;
    border: 2px solid #dc3545;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

# Khởi tạo database khi app chạy
@st.cache_resource
def initialize_database():
    """Khởi tạo database và tạo tables (chạy 1 lần khi app start)"""
    try:
        init_db()
        return True
    except Exception as e:
        st.error(f"Lỗi khởi tạo database: {e}")
        return False

# Các hạng mục kiểm tra
CATEGORIES = ['5S', 'An Toàn', 'Chất Lượng', 'Thiết Bị', 'Kế Hoạch', 'Khác']
STATUS_OPTIONS = ['OK', 'NOK', 'NA']

# Hàm validate mã nhân viên
def validate_employee_id(emp_id):
    """
    Kiểm tra mã nhân viên phải là số và có đúng 6 chữ số
    """
    if not emp_id:
        return False, "Mã nhân viên không được để trống"
    
    if not emp_id.isdigit():
        return False, "Mã nhân viên phải là số"
    
    if len(emp_id) != 6:
        return False, "Mã nhân viên phải có đúng 6 chữ số"
    
    return True, ""

# Các hàm database operations được import từ db_operations.py


# Main app
def main():
    # Khởi tạo database
    if not initialize_database():
        st.error("❌ Không thể kết nối database. Vui lòng kiểm tra cấu hình DATABASE_URL")
        st.stop()
        return
    
    st.title("🔄 Hệ Thống Bàn Giao Ca Làm Việc Trên Line")
    st.markdown("---")
    
    # Tabs cho các chức năng
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "📤 Giao Ca", "📥 Nhận Ca", "📋 Xem Dữ Liệu", "⚙️ Cài Đặt"])
    
    # TAB 0: DASHBOARD
    with tab1:
        st.header("📊 Dashboard - Tổng Quan Bàn Giao Ca")
        
        # Thêm bộ lọc ngày
        col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 1])
        
        with col_filter1:
            filter_date = st.date_input(
                "📅 Chọn ngày xem",
                value=datetime.now(),
                key="dashboard_filter_date",
                help="Chọn ngày để xem dữ liệu bàn giao ca"
            )
        
        with col_filter2:
            filter_line = st.selectbox(
                "🏭 Lọc theo Line",
                ["Tất cả"] + get_active_lines_cached(),
                key="dashboard_filter_line"
            )
        
        with col_filter3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Làm Mới", use_container_width=True, key="dashboard_refresh"):
                st.rerun()
        
        st.markdown("---")
        
        # Lấy dữ liệu dashboard với bộ lọc
        dashboard_data = get_dashboard_data(filter_date=filter_date.strftime('%Y-%m-%d'), filter_line=filter_line)
        
        if dashboard_data is None or len(dashboard_data) == 0:
            st.info("📌 Chưa có dữ liệu giao ca trong ngày được chọn")
        else:
            # Thống kê tổng quan
            total_handovers = len(dashboard_data)
            total_received = sum(1 for item in dashboard_data if item['Trạng Thái Nhận'] == "Đã nhận")
            total_pending = total_handovers - total_received
            total_nok = sum(item['NOK'] for item in dashboard_data)
            
            # Hiển thị metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="📋 Tổng Số Giao Ca",
                    value=total_handovers,
                    delta=f"{filter_date.strftime('%d/%m/%Y')}"
                )
            
            with col2:
                st.metric(
                    label="✅ Đã Nhận Ca",
                    value=total_received,
                    delta=f"{round(total_received/total_handovers*100) if total_handovers > 0 else 0}%"
                )
            
            with col3:
                st.metric(
                    label="⏳ Chờ Nhận Ca",
                    value=total_pending,
                    delta=f"{round(total_pending/total_handovers*100) if total_handovers > 0 else 0}%"
                )
            
            with col4:
                st.metric(
                    label="🔴 Vấn Đề (NOK)",
                    value=total_nok,
                    delta="Cần xử lý" if total_nok > 0 else "Tốt"
                )
            
            st.markdown("---")
            
            # PHẦN MỚI: Hiển thị các bàn giao chưa nhận
            pending_handovers = [item for item in dashboard_data if item['Trạng Thái Nhận'] == "Chưa nhận"]
            
            if pending_handovers:
                st.subheader(f"⚠️ Bàn Giao Chưa Nhận ({len(pending_handovers)} ca)")
                
                for item in pending_handovers:
                    # Xác định mức độ ưu tiên dựa trên NOK
                    if item['NOK'] > 0:
                        priority_color = "🔴"
                        priority_text = "KHẨN CẤP"
                    else:
                        priority_color = "🟡"
                        priority_text = "CHỜ XỬ LÝ"
                    
                    with st.container():
                        st.markdown(f"""
                        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 5px solid #ffc107; margin-bottom: 10px;">
                            <h4 style="margin: 0 0 10px 0;">{priority_color} {priority_text} - {item['Line']} - {item['Ca']} - Nhóm {item['Nhân viên thuộc ca']}</h4>
                            <p style="margin: 5px 0;"><strong>ID Giao Ca:</strong> {item['ID Giao Ca']}</p>
                            <p style="margin: 5px 0;"><strong>Người giao:</strong> {item['Mã NV Giao']} - {item['Tên NV Giao']}</p>
                            <p style="margin: 5px 0;"><strong>Thời gian giao:</strong> {item['Thời Gian Giao']}</p>
                            <p style="margin: 5px 0;"><strong>Trạng thái:</strong> 🟢 {item['OK']} OK | 🔴 {item['NOK']} NOK | ⚪ {item['NA']} NA</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("---")
            else:
                st.success("✅ **Tất cả bàn giao đã được nhận!**")
                st.markdown("---")
            
            # Hiển thị chi tiết từng line
            st.subheader("📋 Chi Tiết Bàn Giao Ca Theo Line")
            
            # Khởi tạo session state cho số lượng hiển thị
            if 'dashboard_show_all' not in st.session_state:
                st.session_state.dashboard_show_all = False
            
            # Xác định số lượng hiển thị
            if st.session_state.dashboard_show_all:
                display_data = dashboard_data
                show_count = len(dashboard_data)
            else:
                display_data = dashboard_data[:5]
                show_count = min(5, len(dashboard_data))
            
            # Hiển thị thông tin số lượng
            st.caption(f"Đang hiển thị **{show_count}** / **{len(dashboard_data)}** bàn giao ca")
            
            for idx, item in enumerate(display_data):
                # Xác định màu card
                if item['NOK'] > 0:
                    card_class = "danger"
                    status_icon = "🔴"
                elif item['Trạng Thái Nhận'] == "Đã nhận":
                    card_class = "success"
                    status_icon = "✅"
                else:
                    card_class = "warning"
                    status_icon = "⏳"
                
                # Tạo expander cho mỗi line
                is_expanded = (idx == 0 and item['Trạng Thái Nhận'] == "Chưa nhận" and not st.session_state.dashboard_show_all)
                
                with st.expander(f"{status_icon} **{item['Line']}** - {item['Ca']} - Nhóm {item['Nhân viên thuộc ca']} | ID: {item['ID Giao Ca']} | {item['Trạng Thái Nhận']}", expanded=is_expanded):
                    
                    # Thông tin giao ca
                    st.markdown("#### 📤 Thông Tin Giao Ca")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.markdown(f"**👤 Người giao:**")
                        st.info(f"{item['Mã NV Giao']} - {item['Tên NV Giao']}")
                    
                    with col2:
                        st.markdown(f"**🕐 Thời gian giao:**")
                        st.info(f"{item['Thời Gian Giao']}")
                    
                    with col3:
                        st.markdown(f"**📊 Trạng thái hạng mục:**")
                        st.success(f"🟢 OK: {item['OK']}")
                        if item['NOK'] > 0:
                            st.error(f"🔴 NOK: {item['NOK']}")
                        if item['NA'] > 0:
                            st.warning(f"⚪ NA: {item['NA']}")
                    
                    with col4:
                        st.markdown(f"**📥 Trạng thái nhận ca:**")
                        if item['Trạng Thái Nhận'] == "Đã nhận":
                            st.success(f"✅ {item['Trạng Thái Nhận']}")
                        else:
                            st.warning(f"⏳ {item['Trạng Thái Nhận']}")
                    
                    # Thông tin nhận ca (nếu có)
                    if item['Trạng Thái Nhận'] == "Đã nhận":
                        st.markdown("---")
                        st.markdown("#### 📥 Thông Tin Nhận Ca")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"**👤 Người nhận:**")
                            st.info(f"{item['Người Nhận']}")
                        
                        with col2:
                            st.markdown(f"**🕐 Thời gian nhận:**")
                            st.info(f"{item['Thời Gian Nhận']}")
                    
                    st.markdown("---")
            
            # Nút Xem thêm / Thu gọn
            if len(dashboard_data) > 5:
                st.markdown("---")
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.session_state.dashboard_show_all:
                        if st.button("🔼 Thu Gọn", use_container_width=True, key="dashboard_collapse"):
                            st.session_state.dashboard_show_all = False
                            st.rerun()
                    else:
                        if st.button(f"🔽 Xem Thêm ({len(dashboard_data) - 5} bàn giao ca)", use_container_width=True, key="dashboard_expand"):
                            st.session_state.dashboard_show_all = True
                            st.rerun()
    
    # TAB 1: GIAO CA
    with tab2:
        st.header("📤 Thực Hiện Giao Ca")
        
        # Khởi tạo session state cho handover nếu chưa có
        if 'handover_success' not in st.session_state:
            st.session_state.handover_success = False
        
        # Kiểm tra xem có thông báo thành công cần hiển thị không
        if st.session_state.handover_success:
            success_data = st.session_state.handover_success_data
            
            # Phân tích trạng thái
            ok_count = success_data['ok_count']
            nok_count = success_data['nok_count']
            na_count = success_data['na_count']
            total_items = success_data['total_items']
            
            st.markdown("---")
            
            # Hiển thị thông báo theo trạng thái
            if nok_count > 0:
                st.warning(f"""
### ⚠️ CẢNH BÁO: Phát hiện {nok_count} hạng mục có vấn đề (NOK)

**Tổng quan:**
- 🟢 OK: {ok_count} mục
- 🔴 NOK: {nok_count} mục  
- ⚪ NA: {na_count} mục

**Các hạng mục NOK:**
{success_data['nok_details']}

⚠️ Vui lòng kiểm tra và xử lý các vấn đề trước khi kết thúc ca!
                """)
            elif ok_count == total_items:
                st.success(f"""
### ✅ TẤT CẢ HẠNG MỤC ĐẠT YÊU CẦU

**Tổng quan:**
- 🟢 OK: {ok_count}/{total_items} mục
- ✨ Ca làm việc diễn ra suôn sẻ, không có vấn đề!
                """)
            else:
                st.info(f"""
### ℹ️ TRẠNG THÁI CA LÀM VIỆC

**Tổng quan:**
- 🟢 OK: {ok_count} mục
- 🔴 NOK: {nok_count} mục
- ⚪ NA: {na_count} mục

**Lưu ý:** Có {na_count} mục được đánh dấu NA (Không áp dụng/Không có thông tin)
                """)
            
            st.markdown("---")
            
            st.success(f"""
### ✅ ĐÃ LƯU THÔNG TIN GIAO CA THÀNH CÔNG!

**Thông tin bàn giao:**
- 🆔 ID Giao Ca: **{success_data['id']}**
- 👤 Nhân viên: **{success_data['ma_nv']}** - **{success_data['ten_nv']}**
- 🏭 Line: **{success_data['line']}**
- ⏰ Ca: **{success_data['ca']}**
- 👥 Nhân viên thuộc ca: **{success_data['chu_ky']}**
- 📅 Ngày: **{success_data['ngay']}**
- 🕐 Thời gian: **{success_data['time']}**

---

✨ Dữ liệu đã được lưu vào hệ thống thành công!
            """)
            
            st.markdown("---")
            
            # Nút để reset form
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 GIAO CA MỚI", type="primary", use_container_width=True, key="new_handover"):
                    # Clear tất cả session state liên quan đến giao ca
                    st.session_state.handover_success = False
                    if 'handover_success_data' in st.session_state:
                        del st.session_state.handover_success_data
                    
                    # Clear tất cả các key liên quan đến form giao ca
                    keys_to_clear = [key for key in st.session_state.keys() if key.startswith(('ma_nv_giao', 'ten_nv_giao', 'line_giao', 'ca_giao', 'chu_ky_giao', 'ngay_bc', 'status_', 'comment_'))]
                    for key in keys_to_clear:
                        del st.session_state[key]
                    
                    st.rerun()
        
        else:
            # Hiển thị form giao ca
            col1, col2, col3 = st.columns(3)
            
            with col1:
                ma_nv_giao = st.text_input("Mã Nhân Viên * (6 chữ số)", key="ma_nv_giao", value="", max_chars=6, placeholder="Ví dụ: 123456")
                active_lines = get_active_lines_cached()
                line_giao = st.selectbox("Line Làm Việc *", 
                                         active_lines,
                                         key="line_giao",
                                         index=0)
            
            with col2:
                ten_nv_giao = st.text_input("Tên Đầy Đủ *", key="ten_nv_giao", value="")
                ca_giao = st.selectbox("Ca Làm Việc *", 
                                       ["Ca Sáng (7h-19h)", "Ca Tối (19h-7h)"],
                                       key="ca_giao",
                                       index=0)
            
            with col3:
                chu_ky_giao = st.selectbox("Nhân viên thuộc ca *",
                                           ["A", "B", "C", "D"],
                                           key="chu_ky_giao",
                                           index=0,
                                           help="Chọn ca làm việc của nhân viên")
                
                ngay_bc = st.date_input("Ngày Báo Cáo *", 
                                        value=datetime.now(),
                                        key="ngay_bc",
                                        help="Chọn ngày bắt đầu ca làm việc")
            
            # Validate mã nhân viên real-time
            if ma_nv_giao:
                is_valid, error_msg = validate_employee_id(ma_nv_giao)
                if not is_valid:
                    st.error(f"⚠️ {error_msg}")
            
            # Tự động xác định ca làm việc và ngày báo cáo
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # Xác định ca: 7h-19h là Ca Sáng, 19h-7h là Ca Tối
            if 7 <= current_hour < 19:
                default_shift = "Ca Sáng (7h-19h)"
                default_date = current_time.date()
            else:
                default_shift = "Ca Tối (19h-7h)"
                if current_hour >= 19:
                    default_date = current_time.date()
                else:
                    default_date = (current_time - pd.Timedelta(days=1)).date()
            
            # Cảnh báo nếu chọn sai ca hoặc ngày
            if ngay_bc != default_date or ca_giao != default_shift:
                st.warning(f"⚠️ **Lưu ý**: Hệ thống đề xuất **{default_shift}** - Ngày **{default_date.strftime('%d/%m/%Y')}** (Hiện tại: {current_time.strftime('%H:%M')})")
            
            # Kiểm tra thông tin nhân viên đã đủ chưa
            if not ma_nv_giao or not ten_nv_giao:
                st.info("👉 Vui lòng nhập đầy đủ **Mã Nhân Viên** và **Tên Đầy Đủ** để tiếp tục")
            else:
                # Validate mã nhân viên trước khi cho phép tiếp tục
                is_valid, error_msg = validate_employee_id(ma_nv_giao)
                if not is_valid:
                    st.error(f"⚠️ {error_msg}")
                else:
                    # CHỈ HIỂN THỊ FORM KHI THÔNG TIN HỢP LỆ
                    st.markdown("---")
                    st.success(f"✅ Thông tin nhân viên hợp lệ: **{ma_nv_giao}** - **{ten_nv_giao}**")
                    
                    st.markdown("### 📋 Thông Tin Các Hạng Mục")
                    st.caption("⚠️ Bắt buộc chọn trạng thái cho tất cả các mục (trừ mục 'Khác')")
                    st.caption("💡 Ghi chú bắt buộc khi trạng thái là NOK hoặc NA, tùy chọn khi OK")
                    
            handover_data = {}
            
            # Tạo layout 2 cột cho các hạng mục
            for idx, category in enumerate(CATEGORIES):
                if idx % 2 == 0:
                    col1, col2 = st.columns(2)
                
                with col1 if idx % 2 == 0 else col2:
                    st.markdown(f"**{category}**")
                    
                    # Selectbox với icons màu
                    status_display = {
                        "OK": "🟢 OK",
                        "NOK": "🔴 NOK", 
                        "NA": "⚪ NA"
                    }
                    
                    status = st.selectbox(
                        f"Tình trạng",
                        options=["OK", "NOK", "NA"],
                        format_func=lambda x: status_display[x],
                        key=f"status_{category}_giao",
                        label_visibility="collapsed",
                        index=2 if category == "Khác" else 0
                    )
                    handover_data[f"{category} - Tình Trạng"] = status
                    
                    # Style cho textarea dựa trên status
                    if status == "OK":
                        border_color = "#22C55E"
                    elif status == "NOK":
                        border_color = "#EF4444"
                    else:
                        border_color = "#9CA3AF"
                    
                    st.markdown(f"""
                    <style>
                    [data-testid="stTextArea"]:has(textarea[aria-label*="{category}"]) {{
                        border-left: 4px solid {border_color};
                        padding-left: 8px;
                    }}
                    </style>
                    """, unsafe_allow_html=True)
                    
                    comment = st.text_area(
                        f"Ghi chú chi tiết",
                        key=f"comment_{category}_giao",
                        height=100,
                        placeholder=f"Nhập ghi chú cho {category}...",
                        label_visibility="collapsed",
                        value=""
                    )
                    handover_data[f"{category} - Comments"] = comment
            
            st.markdown("---")
            
            # Kiểm tra validation
            def validate_handover():
                errors = []
                
                # Kiểm tra thông tin cơ bản
                if not ma_nv_giao or not ten_nv_giao:
                    errors.append("❌ Chưa nhập Mã NV và Tên NV")
                else:
                    # Validate mã nhân viên
                    is_valid, error_msg = validate_employee_id(ma_nv_giao)
                    if not is_valid:
                        errors.append(f"❌ {error_msg}")
                
                # Kiểm tra các hạng mục (trừ "Khác")
                required_categories = [cat for cat in CATEGORIES if cat != "Khác"]
                for category in required_categories:
                    status_key = f"{category} - Tình Trạng"
                    comment_key = f"{category} - Comments"
                    
                    # Kiểm tra trạng thái
                    if status_key not in handover_data or not handover_data[status_key]:
                        errors.append(f"❌ Chưa chọn trạng thái cho **{category}**")
                    
                    # Kiểm tra comment (chỉ bắt buộc nếu trạng thái là NOK hoặc NA, không bắt buộc nếu OK)
                    status = handover_data.get(status_key, "")
                    comment = handover_data.get(comment_key, "").strip()
                    
                    if status in ["NOK", "NA"] and not comment:
                        errors.append(f"❌ Chưa nhập ghi chú cho **{category}** (bắt buộc khi trạng thái {status})")
                
                return errors
            
            # Nút xác nhận với validation
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            
            with col_btn2:
                if st.button("✅ XÁC NHẬN GIAO CA", type="primary", use_container_width=True, key="confirm_handover"):
                    validation_errors = validate_handover()
                    
                    if validation_errors:
                        st.error("### ⚠️ Vui lòng hoàn thành các mục sau:\n\n" + "\n\n".join(validation_errors))
                    else:
                        # Phân tích trạng thái các hạng mục
                        ok_count = sum(1 for k, v in handover_data.items() if k.endswith("Tình Trạng") and v == "OK")
                        nok_count = sum(1 for k, v in handover_data.items() if k.endswith("Tình Trạng") and v == "NOK")
                        na_count = sum(1 for k, v in handover_data.items() if k.endswith("Tình Trạng") and v == "NA")
                        total_items = len(CATEGORIES)
                        
                        # Tạo chi tiết các mục NOK
                        nok_details = "\n".join([
                            f"- **{k.replace(' - Tình Trạng', '')}**: {handover_data.get(k.replace('Tình Trạng', 'Comments'), 'Không có ghi chú')}" 
                            for k, v in handover_data.items() 
                            if k.endswith('Tình Trạng') and v == 'NOK'
                        ])
                        
                        if not nok_details:
                            nok_details = "Không có"
                        
                        # Lưu dữ liệu vào database
                        try:
                            handover_id = generate_handover_id()
                        except Exception as e:
                            st.error(f"❌ Lỗi tạo ID giao ca: {str(e)}")
                            st.stop()
                        
                        data = {
                            'handover_id': handover_id,
                            'ma_nv': ma_nv_giao,
                            'ten_nv': ten_nv_giao,
                            'line': line_giao,
                            'ca': ca_giao,
                            'chu_ky': chu_ky_giao,
                            'ngay': ngay_bc.strftime('%Y-%m-%d'),
                            **handover_data
                        }
                        
                        with st.spinner('Đang lưu thông tin giao ca...'):
                            success, result, error_detail = save_handover_safe(data)
                        if success:
                            # Lưu thông tin vào session state để hiển thị sau khi rerun
                            st.session_state.handover_success = True
                            st.session_state.handover_success_data = {
                                'ma_nv': ma_nv_giao,
                                'ten_nv': ten_nv_giao,
                                'line': line_giao,
                                'ca': ca_giao,
                                'chu_ky': chu_ky_giao,
                                'ngay': ngay_bc.strftime('%d/%m/%Y'),
                                'id': result,
                                'time': datetime.now().strftime('%H:%M:%S'),
                                'ok_count': ok_count,
                                'nok_count': nok_count,
                                'na_count': na_count,
                                'total_items': total_items,
                                'nok_details': nok_details
                            }
                            st.rerun()
                        else:
                            # Hiển thị error message chi tiết từ save_handover_safe
                            error_msg = error_detail if error_detail else result
                            st.error(f"❌ {error_msg}")

    
    # TAB 2: NHẬN CA
    with tab3:
        st.header("📥 Nhận Ca Làm Việc")
        
        # Khởi tạo session state cho receive nếu chưa có
        if 'receive_success' not in st.session_state:
            st.session_state.receive_success = False
        
        # Kiểm tra xem có thông báo thành công cần hiển thị không
        if st.session_state.receive_success:
            receive_data = st.session_state.receive_success_data
            
            st.markdown("---")
            
            st.success(f"""
### ✅ ĐÃ XÁC NHẬN NHẬN CA THÀNH CÔNG!

**Thông tin nhận ca:**
- 🆔 ID Bàn Giao: **{receive_data['handover_id']}**
- 👤 Nhân viên: **{receive_data['ma_nv']}** - **{receive_data['ten_nv']}**
- 🏭 Line: **{receive_data['line']}**
- ⏰ Ca: **{receive_data['ca']}**
- 👥 Nhân viên thuộc ca: **{receive_data['chu_ky']}**
- 📅 Ngày: **{receive_data['ngay']}**
- 🕐 Thời gian: **{receive_data['time']}**

---

✨ Đã xác nhận nhận bàn giao từ ca trước!
            """)
            
            st.markdown("---")
            
            # Nút để reset form
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 NHẬN CA MỚI", type="primary", use_container_width=True, key="new_receive"):
                    # Clear session state
                    st.session_state.receive_success = False
                    if 'receive_success_data' in st.session_state:
                        del st.session_state.receive_success_data
                    if 'handover_info' in st.session_state:
                        del st.session_state['handover_info']
                    
                    # Clear tất cả các key liên quan đến form nhận ca
                    keys_to_clear = [key for key in st.session_state.keys() if key.startswith(('ma_nv_nhan', 'ten_nv_nhan', 'line_nhan', 'ca_nhan', 'chu_ky_nhan', 'ngay_nhan', 'confirm_', 'comment_', 'prev_'))]
                    for key in keys_to_clear:
                        del st.session_state[key]
                    
                    st.rerun()
        
        else:
            # Form nhập thông tin nhận ca
            col1, col2, col3 = st.columns(3)
            
            with col1:
                ma_nv_nhan = st.text_input("Mã Nhân Viên * (6 chữ số)", key="ma_nv_nhan", value="", max_chars=6, placeholder="Ví dụ: 123456")
                active_lines = get_active_lines_cached()
                line_nhan = st.selectbox("Line Làm Việc *", 
                                         active_lines,
                                         key="line_nhan",
                                         index=0)
            
            with col2:
                ten_nv_nhan = st.text_input("Tên Đầy Đủ *", key="ten_nv_nhan", value="")
                ca_nhan = st.selectbox("Ca Làm Việc *",
                                       ["Ca Sáng (7h-19h)", "Ca Tối (19h-7h)"],
                                       key="ca_nhan",
                                       index=0)
            
            with col3:
                chu_ky_nhan = st.selectbox("Nhân viên thuộc ca *",
                                           ["A", "B", "C", "D"],
                                           key="chu_ky_nhan",
                                           index=0,
                                           help="Chọn ca làm việc của nhân viên")
                
                ngay_nhan = st.date_input("Chọn ngày mà giao ca được thực hiện *", 
                                          value=datetime.now(),
                                          key="ngay_nhan",
                                          help="Chọn ngày cụ thể để lọc ra các giao ca đã bàn giao trong ngày hôm đó, giúp người nhận ca tìm ra giao ca thuận tiện hơn, áp dụng cho các trường hợp nhiều giao ca trong ngày.")
            
            # Kiểm tra thay đổi Line hoặc Ngày
            if 'prev_line_nhan' not in st.session_state:
                st.session_state.prev_line_nhan = line_nhan
            if 'prev_ngay_nhan' not in st.session_state:
                st.session_state.prev_ngay_nhan = ngay_nhan
            
            # Nếu Line hoặc Ngày thay đổi, clear thông tin bàn giao cũ
            if (st.session_state.prev_line_nhan != line_nhan or 
                st.session_state.prev_ngay_nhan != ngay_nhan):
                
                # Clear các session state liên quan
                if 'handover_info' in st.session_state:
                    del st.session_state['handover_info']
                if 'handover_already_received' in st.session_state:
                    del st.session_state['handover_already_received']
                if 'receive_info' in st.session_state:
                    del st.session_state['receive_info']
                
                # Cập nhật giá trị mới
                st.session_state.prev_line_nhan = line_nhan
                st.session_state.prev_ngay_nhan = ngay_nhan
                
                # Rerun để cập nhật UI
                st.rerun()
            
            # Validate mã nhân viên real-time
            if ma_nv_nhan:
                is_valid, error_msg = validate_employee_id(ma_nv_nhan)
                if not is_valid:
                    st.error(f"⚠️ {error_msg}")
            
            st.markdown("---")
            
            # Nút xem thông tin bàn giao
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                if st.button("🔍 XEM THÔNG TIN BÀN GIAO", use_container_width=True, type="primary"):
                    handover_info = get_latest_handover(line_nhan, ngay_nhan)
                    if handover_info:
                        # Kiểm tra xem bàn giao này đã được nhận chưa
                        is_received, receive_info = check_handover_received(handover_info['ID Giao Ca'])
                        
                        if is_received:
                            # Hiển thị cảnh báo đã nhận
                            st.session_state['handover_already_received'] = True
                            st.session_state['receive_info'] = receive_info
                            st.session_state['handover_info'] = handover_info
                        else:
                            # Bàn giao chưa được nhận, cho phép tiếp tục
                            st.session_state['handover_info'] = handover_info
                            if 'handover_already_received' in st.session_state:
                                del st.session_state['handover_already_received']
                        
                        st.rerun()
                    else:
                        st.warning(f"⚠️ Chưa có thông tin bàn giao chưa nhận cho **{line_nhan}** vào ngày **{ngay_nhan.strftime('%d/%m/%Y')}**!")
            
            # Kiểm tra xem có thông báo bàn giao đã được nhận không
            if 'handover_already_received' in st.session_state and st.session_state['handover_already_received']:
                st.markdown("---")
                
                receive_info = st.session_state['receive_info']
                handover_info = st.session_state['handover_info']
                
                # Hiển thị thông báo lỗi với styling
                st.markdown("""
                <div class="error-box">
                    <h3>🚫 BÀN GIAO NÀY ĐÃ ĐƯỢC NHẬN</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.error(f"""
### ❌ Không thể nhận ca này vì đã được xác nhận trước đó!

**Thông tin bàn giao:**
- 🆔 ID Giao Ca: **{handover_info['ID Giao Ca']}**
- 🏭 Line: **{handover_info['Line']}**
- ⏰ Ca: **{handover_info['Ca']}**
- 👤 Người giao: **{handover_info['Mã NV Giao Ca']}** - **{handover_info['Tên NV Giao Ca']}**
- 📅 Ngày giao: **{handover_info['Ngày Báo Cáo']}**

---

**Đã được nhận bởi:**
- 👤 Nhân viên: **{receive_info['ma_nv']}** - **{receive_info['ten_nv']}**
- 🕐 Thời gian nhận: **{receive_info['thoi_gian']}**

---

💡 **Gợi ý:** Vui lòng kiểm tra lại thông tin Line và Ngày, hoặc liên hệ với người đã nhận ca để xác nhận.
                """)
                
                st.markdown("---")
                
                # Nút để thử lại
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🔄 THỬ LẠI VỚI THÔNG TIN KHÁC", use_container_width=True, type="secondary"):
                        # Clear session state
                        if 'handover_info' in st.session_state:
                            del st.session_state['handover_info']
                        if 'handover_already_received' in st.session_state:
                            del st.session_state['handover_already_received']
                        if 'receive_info' in st.session_state:
                            del st.session_state['receive_info']
                        st.rerun()
            
            # Checklist nhận ca (chỉ hiển thị nếu chưa được nhận)
            elif 'handover_info' in st.session_state:
                st.markdown("---")
                st.success("✅ Đã tìm thấy thông tin bàn giao chưa nhận!")
                
                # Thông tin người giao ca
                st.markdown("### 📄 Thông Tin Người Giao Ca")
                info_col1, info_col2, info_col3, info_col4 = st.columns(4)
                with info_col1:
                    st.metric("ID Giao Ca", st.session_state['handover_info']['ID Giao Ca'])
                with info_col2:
                    st.metric("Mã NV", st.session_state['handover_info']['Mã NV Giao Ca'])
                with info_col3:
                    st.metric("Tên NV", st.session_state['handover_info']['Tên NV Giao Ca'])
                with info_col4:
                    # Xử lý hiển thị ngày
                    ngay_bc = st.session_state['handover_info']['Ngày Báo Cáo']
                    if isinstance(ngay_bc, date):
                        ngay_display = ngay_bc.strftime('%d/%m/%Y')
                    else:
                        ngay_display = str(ngay_bc)
                    st.metric("Ngày", ngay_display)
                
                st.markdown("---")
                st.markdown("### ✅ Checklist Nhận Ca")
                st.caption("📌 Xác nhận từng hạng mục và thêm ghi chú nếu cần làm rõ")
                
                receive_data = {}
                
                # Layout 2 cột cho các hạng mục
                for idx, category in enumerate(CATEGORIES):
                    # Lấy thông tin từ ca trước
                    handover_status = st.session_state['handover_info'].get(f"{category} - Tình Trạng", "N/A")
                    handover_comment = st.session_state['handover_info'].get(f"{category} - Comments", "")
                    
                    # Xác định class CSS dựa trên status
                    status_class = ""
                    if handover_status == "OK":
                        status_class = "ok"
                        status_icon = "🟢"
                    elif handover_status == "NOK":
                        status_class = "nok"
                        status_icon = "🔴"
                    else:
                        status_class = "na"
                        status_icon = "⚪"
                    
                    # Tạo 2 cột
                    if idx % 2 == 0:
                        col1, col2 = st.columns(2)
                    
                    with col1 if idx % 2 == 0 else col2:
                        # Container cho mỗi category
                        with st.container():
                            st.markdown(f"""
                            <div class="receive-category-box {status_class}">
                                <h4 style="margin: 0 0 10px 0;">{status_icon} {category}</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Hiển thị thông tin ca trước
                            st.caption(f"**Tình trạng ca trước:** {status_icon} {handover_status}")
                            if handover_comment:
                                st.caption(f"**Ghi chú ca trước:** {handover_comment}")
                            
                            # Checkbox xác nhận và comment
                            col_check, col_comment = st.columns([1, 3])
                            
                            with col_check:
                                xac_nhan = st.checkbox(
                                    "✓ Đã xác nhận",
                                    key=f"confirm_{category}_nhan",
                                    value=False
                                )
                                receive_data[f"{category} - Xác Nhận"] = "Đã xác nhận" if xac_nhan else "Chưa xác nhận"
                            
                            with col_comment:
                                comment_nhan = st.text_input(
                                    "Ghi chú (nếu cần)",
                                    key=f"comment_{category}_nhan",
                                    placeholder="Nhập ghi chú...",
                                    label_visibility="collapsed",
                                    value=""
                                )
                                receive_data[f"{category} - Comments Nhận"] = comment_nhan
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Validation cho nhận ca
                def validate_receive():
                    errors = []
                    
                    # Kiểm tra thông tin cơ bản
                    if not ma_nv_nhan or not ten_nv_nhan:
                        errors.append("❌ Chưa nhập Mã NV và Tên NV")
                    else:
                        # Validate mã nhân viên
                        is_valid, error_msg = validate_employee_id(ma_nv_nhan)
                        if not is_valid:
                            errors.append(f"❌ {error_msg}")
                    
                    # Kiểm tra các hạng mục (trừ "Khác")
                    required_categories = [cat for cat in CATEGORIES if cat != "Khác"]
                    for category in required_categories:
                        confirm_key = f"{category} - Xác Nhận"
                        if confirm_key not in receive_data or receive_data[confirm_key] != "Đã xác nhận":
                            errors.append(f"❌ Chưa xác nhận hạng mục **{category}**")
                    
                    # Kiểm tra mục "Khác" - bắt buộc xác nhận nếu có comment từ ca trước HOẶC có comment mới
                    khac_comment_old = str(st.session_state['handover_info'].get("Khác - Comments", "")).strip()
                    khac_comment_new = str(receive_data.get("Khác - Comments Nhận", "")).strip()
                    khac_confirm = receive_data.get("Khác - Xác Nhận", "")
                    
                    # Bỏ qua nếu comment là "nan" (từ pandas NaN)
                    if khac_comment_old.lower() == "nan":
                        khac_comment_old = ""
                    if khac_comment_new.lower() == "nan":
                        khac_comment_new = ""
                    
                    # Nếu có thông tin (từ ca trước hoặc comment mới) thì phải xác nhận
                    if (khac_comment_old or khac_comment_new) and khac_confirm != "Đã xác nhận":
                        errors.append(f"❌ Mục **Khác** có thông tin nhưng chưa được xác nhận")
                    
                    return errors
                
                # Nút xác nhận nhận ca
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    if st.button("✅ XÁC NHẬN NHẬN CA", type="primary", use_container_width=True, key="confirm_receive"):
                        validation_errors = validate_receive()
                        
                        if validation_errors:
                            st.error("### ⚠️ Vui lòng hoàn thành các mục sau:\n\n" + "\n\n".join(validation_errors))
                        else:
                            # Kiểm tra lại một lần nữa trước khi lưu
                            handover_id = st.session_state['handover_info']['ID Giao Ca']
                            is_received, receive_info = check_handover_received(handover_id)
                            
                            if is_received:
                                st.error(f"""
### ❌ Không thể nhận ca!

Bàn giao này đã được nhận bởi **{receive_info['ma_nv']}** - **{receive_info['ten_nv']}** 
vào lúc **{receive_info['thoi_gian']}**

Vui lòng làm mới trang và thử lại.
                                """)
                            else:
                                # Tiến hành lưu với row-level locking
                                data = {
                                    'ma_nv': ma_nv_nhan,
                                    'ten_nv': ten_nv_nhan,
                                    'line': line_nhan,
                                    'ca': ca_nhan,
                                    'chu_ky': chu_ky_nhan,
                                    'ngay': ngay_nhan.strftime('%Y-%m-%d'),
                                    **receive_data
                                }
                                
                                with st.spinner('Đang lưu thông tin nhận ca...'):
                                    success, message = save_receive_safe(data, handover_id)
                                if success:
                                    # Lưu thông tin vào session state
                                    st.session_state.receive_success = True
                                    st.session_state.receive_success_data = {
                                        'handover_id': handover_id,
                                        'ma_nv': ma_nv_nhan,
                                        'ten_nv': ten_nv_nhan,
                                        'line': line_nhan,
                                        'ca': ca_nhan,
                                        'chu_ky': chu_ky_nhan,
                                        'ngay': ngay_nhan.strftime('%d/%m/%Y'),
                                        'time': datetime.now().strftime('%H:%M:%S')
                                    }
                                    
                                    # Clear các session state không cần thiết
                                    if 'handover_info' in st.session_state:
                                        del st.session_state['handover_info']
                                    if 'prev_line_nhan' in st.session_state:
                                        del st.session_state['prev_line_nhan']
                                    if 'prev_ngay_nhan' in st.session_state:
                                        del st.session_state['prev_ngay_nhan']
                                    
                                    st.rerun()
                                else:
                                    st.error(f"❌ Lỗi khi lưu dữ liệu: {message}")
    
    # TAB 4: XEM DỮ LIỆU
    with tab4:
        st.header("📋 Xem Dữ Liệu Bàn Giao Ca")
        
        # Tạo sub-tabs cho Giao Ca, Nhận Ca và Kết Hợp
        view_tab1, view_tab2, view_tab3 = st.tabs(["📤 Dữ Liệu Giao Ca", "📥 Dữ Liệu Nhận Ca", "🔗 Kết Hợp Giao-Nhận"])
        
        # SUB-TAB 1: Dữ liệu Giao Ca
        with view_tab1:
            st.subheader("📤 Lịch Sử Giao Ca")
            
            try:
                data = get_handover_data_for_export()
                if data:
                    df = pd.DataFrame(data)
                    
                    # Bộ lọc
                    col_filter1, col_filter2, col_filter3 = st.columns(3)
                    
                    with col_filter1:
                        # Lọc theo Line
                        unique_lines = ['Tất cả'] + sorted(df['Line'].unique().tolist())
                        selected_line = st.selectbox("🏭 Lọc theo Line", unique_lines, key="view_handover_line")
                    
                    with col_filter2:
                        # Lọc theo Ca
                        unique_shifts = ['Tất cả'] + sorted(df['Ca'].unique().tolist())
                        selected_shift = st.selectbox("⏰ Lọc theo Ca", unique_shifts, key="view_handover_shift")
                    
                    with col_filter3:
                        # Lọc theo Trạng thái
                        status_options = ['Tất cả', 'Đã nhận', 'Chưa nhận']
                        selected_status = st.selectbox("📊 Lọc theo Trạng thái", status_options, key="view_handover_status")
                    
                    # Áp dụng bộ lọc
                    filtered_df = df.copy()
                    if selected_line != 'Tất cả':
                        filtered_df = filtered_df[filtered_df['Line'] == selected_line]
                    if selected_shift != 'Tất cả':
                        filtered_df = filtered_df[filtered_df['Ca'] == selected_shift]
                    if selected_status != 'Tất cả':
                        filtered_df = filtered_df[filtered_df['Trạng Thái Nhận'] == selected_status]
                    
                    # Hiển thị thống kê
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📋 Tổng số bàn giao", len(filtered_df))
                    with col2:
                        received_count = len(filtered_df[filtered_df['Trạng Thái Nhận'] == 'Đã nhận'])
                        st.metric("✅ Đã nhận", received_count)
                    with col3:
                        pending_count = len(filtered_df[filtered_df['Trạng Thái Nhận'] == 'Chưa nhận'])
                        st.metric("⏳ Chưa nhận", pending_count)
                    with col4:
                        # Đếm NOK trong các cột status
                        nok_count = 0
                        for cat in CATEGORIES:
                            col_name = f'{cat} - Tình Trạng'
                            if col_name in filtered_df.columns:
                                nok_count += (filtered_df[col_name] == 'NOK').sum()
                        st.metric("🔴 Tổng NOK", nok_count)
                    
                    st.markdown("---")
                    
                    # Hiển thị bảng dữ liệu
                    st.dataframe(
                        filtered_df,
                        use_container_width=True,
                        height=400
                    )
                    
                    st.caption(f"Hiển thị **{len(filtered_df)}** / **{len(df)}** bản ghi")
                    
                else:
                    st.info("📌 Chưa có dữ liệu giao ca")
            except Exception as e:
                st.error(f"❌ Lỗi khi đọc dữ liệu: {e}")
        
        # SUB-TAB 2: Dữ liệu Nhận Ca
        with view_tab2:
            st.subheader("📥 Lịch Sử Nhận Ca")
            
            try:
                data = get_receive_data_for_export()
                if data:
                    df = pd.DataFrame(data)
                    
                    # Bộ lọc
                    col_filter1, col_filter2 = st.columns(2)
                    
                    with col_filter1:
                        # Lọc theo Line
                        unique_lines = ['Tất cả'] + sorted(df['Line'].unique().tolist())
                        selected_line = st.selectbox("🏭 Lọc theo Line", unique_lines, key="view_receive_line")
                    
                    with col_filter2:
                        # Lọc theo Ca
                        unique_shifts = ['Tất cả'] + sorted(df['Ca'].unique().tolist())
                        selected_shift = st.selectbox("⏰ Lọc theo Ca", unique_shifts, key="view_receive_shift")
                    
                    # Áp dụng bộ lọc
                    filtered_df = df.copy()
                    if selected_line != 'Tất cả':
                        filtered_df = filtered_df[filtered_df['Line'] == selected_line]
                    if selected_shift != 'Tất cả':
                        filtered_df = filtered_df[filtered_df['Ca'] == selected_shift]
                    
                    # Hiển thị thống kê
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📋 Tổng số nhận ca", len(filtered_df))
                    with col2:
                        # Đếm số lượng xác nhận
                        confirmed_count = 0
                        for cat in CATEGORIES:
                            col_name = f'{cat} - Xác Nhận'
                            if col_name in filtered_df.columns:
                                confirmed_count += (filtered_df[col_name] == 'Đã xác nhận').sum()
                        st.metric("✅ Tổng xác nhận", confirmed_count)
                    with col3:
                        # Unique nhân viên
                        unique_employees = filtered_df['Mã NV Nhận Ca'].nunique()
                        st.metric("👥 Số nhân viên", unique_employees)
                    
                    st.markdown("---")
                    
                    # Hiển thị bảng dữ liệu
                    st.dataframe(
                        filtered_df,
                        use_container_width=True,
                        height=400
                    )
                    
                    st.caption(f"Hiển thị **{len(filtered_df)}** / **{len(df)}** bản ghi")
                    
                else:
                    st.info("📌 Chưa có dữ liệu nhận ca")
            except Exception as e:
                st.error(f"❌ Lỗi khi đọc dữ liệu: {e}")
        
        # SUB-TAB 3: Dữ liệu Kết Hợp
        with view_tab3:
            st.subheader("🔗 Dữ Liệu Kết Hợp Giao Ca - Nhận Ca")
            st.caption("Bảng này hiển thị thông tin đầy đủ từ giao ca đến nhận ca")
            
            try:
                # Bộ lọc
                col_filter1, col_filter2, col_filter3 = st.columns(3)
                
                with col_filter1:
                    # Lọc theo ngày
                    filter_date = st.date_input(
                        "📅 Chọn ngày",
                        value=datetime.now(),
                        key="combined_filter_date"
                    )
                
                with col_filter2:
                    # Lọc theo Line
                    all_lines = get_active_lines_cached()
                    selected_line = st.selectbox(
                        "🏭 Lọc theo Line",
                        ["Tất cả"] + all_lines,
                        key="combined_filter_line"
                    )
                
                with col_filter3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔄 Làm Mới", key="combined_refresh"):
                        st.rerun()
                
                st.markdown("---")
                
                # Lấy dữ liệu kết hợp
                combined_data = get_combined_handover_receive_data(
                    filter_date=filter_date,
                    filter_line=selected_line if selected_line != "Tất cả" else None
                )
                
                if combined_data:
                    df = pd.DataFrame(combined_data)
                    
                    # Thống kê
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("📋 Tổng bàn giao", len(df))
                    with col2:
                        received = len(df[df['Trạng Thái Nhận'] == 'Đã nhận'])
                        st.metric("✅ Đã nhận", received)
                    with col3:
                        pending = len(df[df['Trạng Thái Nhận'] == 'Chưa nhận'])
                        st.metric("⏳ Chưa nhận", pending)
                    with col4:
                        total_nok = df['NOK'].sum()
                        st.metric("🔴 Tổng NOK", int(total_nok))
                    with col5:
                        unique_employees_giao = df['Mã NV Giao'].nunique()
                        unique_employees_nhan = df['Mã NV Nhận'].nunique()
                        st.metric("👥 NV Giao/Nhận", f"{unique_employees_giao}/{unique_employees_nhan}")
                    
                    st.markdown("---")
                    
                    # Định dạng cột cho hiển thị đẹp
                    display_df = df.copy()
                    
                    # Format datetime columns
                    if 'Thời Gian Giao' in display_df.columns:
                        display_df['Thời Gian Giao'] = pd.to_datetime(display_df['Thời Gian Giao']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    if 'Thời Gian Nhận' in display_df.columns:
                        display_df['Thời Gian Nhận'] = display_df['Thời Gian Nhận'].apply(
                            lambda x: pd.to_datetime(x).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) else ''
                        )
                    
                    # Sắp xếp cột hiển thị
                    column_order = [
                        'ID Giao Ca', 'Line', 'Ca', 'Nhân viên thuộc ca', 'Ngày Báo Cáo',
                        'Mã NV Giao', 'Tên NV Giao', 'Thời Gian Giao',
                        'OK', 'NOK', 'NA', 'Trạng Thái Nhận',
                        'Mã NV Nhận', 'Tên NV Nhận', 'Thời Gian Nhận'
                    ]
                    
                    # Chỉ giữ các cột tồn tại
                    column_order = [col for col in column_order if col in display_df.columns]
                    display_df = display_df[column_order]
                    
                    # Hiển thị bảng với styling
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        height=500,
                        column_config={
                            "ID Giao Ca": st.column_config.TextColumn("ID Giao Ca", width="medium"),
                            "Line": st.column_config.TextColumn("Line", width="small"),
                            "Ca": st.column_config.TextColumn("Ca", width="medium"),
                            "OK": st.column_config.NumberColumn("OK", format="%d"),
                            "NOK": st.column_config.NumberColumn("NOK", format="%d"),
                            "NA": st.column_config.NumberColumn("NA", format="%d"),
                            "Trạng Thái Nhận": st.column_config.TextColumn("Trạng Thái", width="small"),
                        }
                    )
                    
                    st.caption(f"Hiển thị **{len(df)}** bản ghi")
                    
                    # Xuất dữ liệu kết hợp
                    st.markdown("---")
                    col_export1, col_export2, col_export3 = st.columns([1, 2, 1])
                    with col_export2:
                        st.download_button(
                            "📥 Tải Xuống Dữ Liệu Kết Hợp (CSV)",
                            df.to_csv(index=False).encode('utf-8-sig'),
                            f"combined_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            "text/csv",
                            use_container_width=True,
                            type="primary"
                        )
                else:
                    st.info("📌 Chưa có dữ liệu cho ngày đã chọn")
                    
            except Exception as e:
                st.error(f"❌ Lỗi khi đọc dữ liệu: {e}")
    
    # TAB 5: CÀI ĐẶT (Bao gồm cả Xuất Dữ Liệu)
    with tab5:
        st.header("⚙️ Cài Đặt Hệ Thống")
        
        # Kiểm tra đăng nhập cho trang cài đặt
        if 'settings_logged_in' not in st.session_state:
            st.session_state.settings_logged_in = False
        
        if not st.session_state.settings_logged_in:
            st.warning("🔒 Trang này yêu cầu đăng nhập")
            st.markdown("---")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                username = st.text_input("👤 Tên đăng nhập", key="settings_username")
                password = st.text_input("🔑 Mật khẩu", type="password", key="settings_password")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🚀 Đăng Nhập", type="primary", use_container_width=True):
                        if username and password:
                            success, full_name = check_login(username, password)
                            if success and username == 'admin':
                                st.session_state.settings_logged_in = True
                                st.session_state.admin_name = full_name
                                st.success(f"Chào mừng {full_name}!")
                                st.rerun()
                            else:
                                st.error("❌ Chỉ tài khoản admin mới có quyền truy cập!")
                        else:
                            st.warning("⚠️ Vui lòng nhập đầy đủ thông tin!")
        
        else:
            # Đã đăng nhập - hiển thị trang cài đặt
            col_info, col_logout = st.columns([3, 1])
            with col_info:
                st.success(f"✅ Đang đăng nhập với quyền Admin: **{st.session_state.admin_name}**")
            with col_logout:
                if st.button("🚪 Đăng xuất", type="secondary"):
                    st.session_state.settings_logged_in = False
                    st.rerun()
            
            st.markdown("---")
            
            # Tạo sub-tabs cho Cài đặt, Xuất dữ liệu và Quản trị
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🏭 Quản Lý Lines", "📥 Xuất Dữ Liệu", "🛠️ Quản Trị Dữ Liệu"])
            
            # SUB-TAB 1: Quản lý Lines
            with sub_tab1:
                st.subheader("🏭 Quản Lý Lines Sản Xuất")
                
                try:
                    lines_data = get_all_lines()
                    lines_df = pd.DataFrame(lines_data)
                    
                    # Hiển thị bảng lines hiện tại
                    st.markdown("### 📋 Danh Sách Lines Hiện Tại")
                    
                    # Sử dụng data_editor để chỉnh sửa trực tiếp
                    edited_df = st.data_editor(
                        lines_df,
                        use_container_width=True,
                        num_rows="dynamic",
                        column_config={
                            "line_code": st.column_config.TextColumn("Mã Line", help="Mã định danh duy nhất", required=True),
                            "line_name": st.column_config.TextColumn("Tên Line", help="Tên hiển thị", required=True),
                            "is_active": st.column_config.CheckboxColumn("Kích hoạt", help="Line có đang hoạt động?", default=True)
                        },
                        hide_index=True
                    )
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("💾 Lưu Cấu Hình", type="primary", use_container_width=True):
                            lines_list = edited_df.to_dict('records')
                            if save_lines_config(lines_list):
                                st.success("✅ Đã lưu cấu hình lines thành công!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Lỗi khi lưu cấu hình!")
                    
                    with col2:
                        if st.button("🔄 Làm Mới", use_container_width=True):
                            st.rerun()
                    
                    st.markdown("---")
                    st.info("💡 **Hướng dẫn**: Bạn có thể thêm/xóa/sửa lines bằng cách chỉnh sửa trực tiếp trong bảng trên, sau đó nhấn **Lưu Cấu Hình**")
                    
                except Exception as e:
                    st.error(f"❌ Lỗi khi tải cấu hình lines: {e}")
            
            # SUB-TAB 2: Xuất Dữ Liệu
            with sub_tab2:
                st.subheader("📥 Xuất Dữ Liệu Ra File")
                
                st.info("💡 Tải xuống dữ liệu dưới dạng file CSV để phân tích hoặc lưu trữ")
                
                col1, col2 = st.columns(2)
                
                # Xuất dữ liệu Giao Ca
                with col1:
                    st.markdown("### 📤 Dữ Liệu Giao Ca")
                    try:
                        data = get_handover_data_for_export()
                        if data:
                            df = pd.DataFrame(data)
                            st.success(f"✅ Sẵn sàng xuất **{len(df)}** bản ghi")
                            
                            # Hiển thị preview
                            with st.expander("👁️ Xem trước dữ liệu (5 dòng đầu)"):
                                st.dataframe(df.head(), use_container_width=True)
                            
                            # Nút download
                            st.download_button(
                                "📥 Tải Xuống Dữ Liệu Giao Ca (CSV)",
                                df.to_csv(index=False).encode('utf-8-sig'),
                                f"handover_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                "text/csv",
                                use_container_width=True,
                                type="primary"
                            )
                        else:
                            st.info("📌 Chưa có dữ liệu giao ca để xuất")
                    except Exception as e:
                        st.error(f"❌ Lỗi: {e}")
                
                # Xuất dữ liệu Nhận Ca
                with col2:
                    st.markdown("### 📥 Dữ Liệu Nhận Ca")
                    try:
                        data = get_receive_data_for_export()
                        if data:
                            df = pd.DataFrame(data)
                            st.success(f"✅ Sẵn sàng xuất **{len(df)}** bản ghi")
                            
                            # Hiển thị preview
                            with st.expander("👁️ Xem trước dữ liệu (5 dòng đầu)"):
                                st.dataframe(df.head(), use_container_width=True)
                            
                            # Nút download
                            st.download_button(
                                "📥 Tải Xuống Dữ Liệu Nhận Ca (CSV)",
                                df.to_csv(index=False).encode('utf-8-sig'),
                                f"receive_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                "text/csv",
                                use_container_width=True,
                                type="primary"
                            )
                        else:
                            st.info("📌 Chưa có dữ liệu nhận ca để xuất")
                    except Exception as e:
                        st.error(f"❌ Lỗi: {e}")
                
                st.markdown("---")
                
                # Hướng dẫn sử dụng
                with st.expander("ℹ️ Hướng Dẫn Sử Dụng File CSV"):
                    st.markdown("""
                    ### Cách Mở File CSV:
                    
                    1. **Microsoft Excel**:
                       - Mở Excel → File → Open
                       - Chọn file CSV đã tải
                       - Dữ liệu sẽ tự động hiển thị trong các cột
                    
                    2. **Google Sheets**:
                       - Truy cập Google Sheets
                       - File → Import → Upload
                       - Chọn file CSV
                    
                    3. **Python/Pandas**:
                       ```python
                       import pandas as pd
                       df = pd.read_csv('handover_data.csv', encoding='utf-8-sig')
                       ```
                    
                    ### Lưu Ý:
                    - File CSV sử dụng encoding UTF-8 với BOM để hiển thị tiếng Việt chính xác
                    - Tên file tự động thêm timestamp để tránh ghi đè
                    - Dữ liệu được xuất theo định dạng gốc từ database
                    """)
            
            # SUB-TAB 3: Quản Trị Dữ Liệu
            with sub_tab3:
                st.subheader("🛠️ Quản Trị Dữ Liệu Bàn Giao")
                
                st.warning("⚠️ **Cảnh báo**: Chức năng này chỉ dành cho Admin. Hãy cẩn thận khi xóa dữ liệu!")
                
                st.markdown("---")
                
                # Tìm kiếm và xóa bàn giao
                st.markdown("### 🔍 Tìm Kiếm và Xóa Bàn Giao Lỗi")
                
                # Bộ lọc
                col_filter1, col_filter2, col_filter3 = st.columns(3)
                
                with col_filter1:
                    search_line = st.selectbox(
                        "🏭 Lọc theo Line",
                        ["Tất cả"] + get_active_lines_cached(),
                        key="admin_search_line"
                    )
                
                with col_filter2:
                    search_status = st.selectbox(
                        "📊 Lọc theo Trạng thái",
                        ["Tất cả", "Đã nhận", "Chưa nhận"],
                        key="admin_search_status"
                    )
                
                with col_filter3:
                    search_date = st.date_input(
                        "📅 Lọc theo Ngày",
                        value=None,
                        key="admin_search_date"
                    )
                
                st.markdown("---")
                
                try:
                    # Lấy tất cả handovers
                    all_handovers = get_all_handovers_for_admin()
                    
                    if all_handovers:
                        df = pd.DataFrame(all_handovers)
                        
                        # Áp dụng bộ lọc
                        filtered_df = df.copy()
                        
                        if search_line != "Tất cả":
                            filtered_df = filtered_df[filtered_df['Line'] == search_line]
                        
                        if search_status != "Tất cả":
                            filtered_df = filtered_df[filtered_df['Trạng Thái Nhận'] == search_status]
                        
                        if search_date:
                            # Convert Ngày Báo Cáo to date for comparison
                            filtered_df['Ngày Báo Cáo'] = pd.to_datetime(filtered_df['Ngày Báo Cáo']).dt.date
                            filtered_df = filtered_df[filtered_df['Ngày Báo Cáo'] == search_date]
                        
                        # Hiển thị thống kê
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📋 Tổng số bàn giao", len(df))
                        with col2:
                            st.metric("🔍 Kết quả lọc", len(filtered_df))
                        with col3:
                            pending = len(filtered_df[filtered_df['Trạng Thái Nhận'] == 'Chưa nhận'])
                            st.metric("⏳ Chưa nhận (có thể xóa)", pending)
                        
                        st.markdown("---")
                        
                        # Hiển thị danh sách
                        if not filtered_df.empty:
                            st.markdown(f"### 📋 Danh Sách Bàn Giao ({len(filtered_df)} bản ghi)")
                            
                            # Khởi tạo session state cho việc xóa
                            if 'confirm_delete' not in st.session_state:
                                st.session_state.confirm_delete = {}
                            
                            # Hiển thị từng bản ghi
                            for idx, row in filtered_df.iterrows():
                                with st.expander(
                                    f"{'🔴' if row['Trạng Thái Nhận'] == 'Chưa nhận' else '✅'} "
                                    f"{row['ID Giao Ca']} - {row['Line']} - {row['Ca']} - "
                                    f"{row['Trạng Thái Nhận']}",
                                    expanded=False
                                ):
                                    col_info1, col_info2, col_info3 = st.columns(3)
                                    
                                    with col_info1:
                                        st.write(f"**ID**: {row['ID Giao Ca']}")
                                        st.write(f"**Line**: {row['Line']}")
                                        st.write(f"**Ca**: {row['Ca']}")
                                    
                                    with col_info2:
                                        st.write(f"**Nhân viên**: {row['Mã NV Giao']} - {row['Tên NV Giao']}")
                                        st.write(f"**Nhóm ca**: {row['Nhân viên thuộc ca']}")
                                        st.write(f"**Ngày**: {row['Ngày Báo Cáo']}")
                                    
                                    with col_info3:
                                        st.write(f"**Thời gian giao**: {row['Thời Gian Giao']}")
                                        st.write(f"**Trạng thái**: {row['Trạng Thái Nhận']}")
                                    
                                    st.markdown("---")
                                    
                                    # Nút xóa
                                    handover_id = row['ID Giao Ca']
                                    
                                    col_del1, col_del2, col_del3 = st.columns([2, 1, 1])
                                    
                                    with col_del2:
                                        if st.button(
                                            "🗑️ Xóa Bàn Giao",
                                            key=f"delete_{handover_id}",
                                            type="secondary",
                                            use_container_width=True
                                        ):
                                            st.session_state.confirm_delete[handover_id] = True
                                            st.rerun()
                                    
                                    # Hiển thị confirmation nếu đã click xóa
                                    if st.session_state.confirm_delete.get(handover_id, False):
                                        st.error(f"⚠️ **XÁC NHẬN XÓA**: Bạn có chắc chắn muốn xóa bàn giao **{handover_id}**?")
                                        
                                        col_confirm1, col_confirm2, col_confirm3 = st.columns(3)
                                        
                                        with col_confirm1:
                                            if st.button(
                                                "✅ Xác Nhận Xóa",
                                                key=f"confirm_{handover_id}",
                                                type="primary",
                                                use_container_width=True
                                            ):
                                                success, message = delete_handover_by_id(handover_id)
                                                if success:
                                                    st.success(f"✅ {message}")
                                                    st.session_state.confirm_delete[handover_id] = False
                                                    time.sleep(1)
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ Lỗi: {message}")
                                        
                                        with col_confirm2:
                                            if st.button(
                                                "❌ Hủy",
                                                key=f"cancel_{handover_id}",
                                                use_container_width=True
                                            ):
                                                st.session_state.confirm_delete[handover_id] = False
                                                st.rerun()
                            
                            st.markdown("---")
                            st.caption("💡 **Lưu ý**: Chỉ xóa các bàn giao lỗi hoặc test. Việc xóa sẽ xóa cả thông tin nhận ca liên quan (nếu có).")
                        
                        else:
                            st.info("📌 Không tìm thấy bàn giao nào với bộ lọc đã chọn")
                    
                    else:
                        st.info("📌 Chưa có dữ liệu bàn giao")
                        
                except Exception as e:
                    st.error(f"❌ Lỗi khi tải dữ liệu: {e}")
                
                st.markdown("---")
                
                # Thống kê tổng quan
                st.markdown("### 📊 Thống Kê Tổng Quan")
                try:
                    all_data = get_all_handovers_for_admin()
                    if all_data:
                        df_all = pd.DataFrame(all_data)
                        
                        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                        
                        with col_stat1:
                            st.metric("📋 Tổng bàn giao (toàn hệ thống)", len(df_all))
                        
                        with col_stat2:
                            received = len(df_all[df_all['Trạng Thái Nhận'] == 'Đã nhận'])
                            st.metric("✅ Đã nhận", received)
                        
                        with col_stat3:
                            pending = len(df_all[df_all['Trạng Thái Nhận'] == 'Chưa nhận'])
                            st.metric("⏳ Chưa nhận", pending)
                        
                        with col_stat4:
                            # Ngày cũ nhất
                            oldest_date = df_all['Ngày Báo Cáo'].min()
                            st.metric("📅 Dữ liệu từ ngày", str(oldest_date)[:10])
                        
                except Exception as e:
                    st.error(f"❌ Lỗi khi tải thống kê: {e}")

if __name__ == "__main__":
    main()

