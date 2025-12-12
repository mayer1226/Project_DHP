import streamlit as st
import pandas as pd
from datetime import datetime, date
import os
import time
from database import init_db
from db_operations import (
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
    get_latest_handovers_for_display,
    get_combined_handover_receive_data,
    # Hàm mới cho edit/delete
    get_handover_by_id,
    update_handover,
    delete_handover,
    get_receive_by_handover_id,
    delete_receive,
    search_handovers
)

# Cấu hình trang
st.set_page_config(page_title="Hệ thống Bàn Giao Ca", page_icon="🔄", layout="wide")

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

.success-box {
    background-color: #d4edda;
    border: 2px solid #28a745;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}

/* Highlight row in dataframe */
.dataframe tbody tr:hover {
    background-color: #f5f5f5;
}

/* Admin badge */
.admin-badge {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 5px 15px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    display: inline-block;
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


# Main app
def main():
    # Khởi tạo database
    if not initialize_database():
        st.error("❌ Không thể kết nối database. Vui lòng kiểm tra cấu hình DATABASE_URL")
        st.stop()
        return
    
    st.title("🔄 Hệ Thống Bàn Giao Ca Làm Việc Trên Line")
    
    # Hiển thị badge admin nếu đã đăng nhập
    if 'admin_logged_in' in st.session_state and st.session_state.admin_logged_in:
        st.markdown(f"""
        <div style="text-align: right; margin-bottom: 10px;">
            <span class="admin-badge">👑 ADMIN: {st.session_state.admin_name}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Tabs cho các chức năng - THÊM TAB QUẢN LÝ
    tabs = ["📊 Dashboard", "📤 Giao Ca", "📥 Nhận Ca", "📈 Xem Dữ Liệu", "⚙️ Cài Đặt"]
    
    # Thêm tab Quản Lý nếu là admin
    if 'admin_logged_in' in st.session_state and st.session_state.admin_logged_in:
        tabs.insert(4, "🔧 Quản Lý")
    
    selected_tabs = st.tabs(tabs)
    
    # Mapping tabs
    tab_dashboard = selected_tabs[0]
    tab_handover = selected_tabs[1]
    tab_receive = selected_tabs[2]
    tab_view_data = selected_tabs[3]
    
    if len(selected_tabs) == 6:  # Có tab Quản Lý
        tab_manage = selected_tabs[4]
        tab_settings = selected_tabs[5]
    else:
        tab_manage = None
        tab_settings = selected_tabs[4]
    
    # TAB 0: DASHBOARD
    with tab_dashboard:
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
                ["Tất cả"] + get_active_lines(),
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
    with tab_handover:
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
                active_lines = get_active_lines()
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
                    st.caption("⚠️ **Lưu ý:** Chỉ bắt buộc nhập ghi chú cho các mục NOK và NA")
                    
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
                        placeholder_text = f"Ghi chú cho {category} (không bắt buộc)"
                    elif status == "NOK":
                        border_color = "#EF4444"
                        placeholder_text = f"⚠️ BẮT BUỘC: Mô tả vấn đề {category}"
                    else:
                        border_color = "#9CA3AF"
                        placeholder_text = f"⚠️ BẮT BUỘC: Lý do không áp dụng {category}"
                    
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
                        placeholder=placeholder_text,
                        label_visibility="collapsed",
                        value=""
                    )
                    handover_data[f"{category} - Comments"] = comment
            
            st.markdown("---")
            
            # Kiểm tra validation - CẬP NHẬT: CHỈ BẮT BUỘC COMMENT CHO NOK VÀ NA
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
                    else:
                        status = handover_data[status_key]
                        comment = handover_data.get(comment_key, "").strip()
                        
                        # CHỈ BẮT BUỘC COMMENT CHO NOK VÀ NA
                        if status == "NOK" and not comment:
                            errors.append(f"❌ **{category}** có trạng thái NOK - BẮT BUỘC nhập ghi chú mô tả vấn đề")
                        elif status == "NA" and not comment:
                            errors.append(f"❌ **{category}** có trạng thái NA - BẮT BUỘC nhập lý do không áp dụng")
                        # OK không cần comment
                
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
                        
                        # Lưu dữ liệu vào database (ID sẽ được tạo bên trong hàm save_handover_safe)
                        data = {
                            'ma_nv': ma_nv_giao,
                            'ten_nv': ten_nv_giao,
                            'line': line_giao,
                            'ca': ca_giao,
                            'chu_ky': chu_ky_giao,
                            'ngay': ngay_bc.strftime('%Y-%m-%d'),
                            **handover_data
                        }
                        
                        # Hiển thị loading
                        with st.spinner('⏳ Đang lưu dữ liệu...'):
                            success, result = save_handover_safe(data, max_retries=10)
                        
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
                            # Hiển thị lỗi chi tiết
                            st.error(f"""
### ❌ Không thể lưu dữ liệu giao ca

**Lỗi:** {result}

**Hành động khuyến nghị:**
1. Đợi 2-3 giây và nhấn lại nút "XÁC NHẬN GIAO CA"
2. Nếu vẫn lỗi, chụp màn hình và liên hệ IT
3. Kiểm tra kết nối internet

**Thông tin debug:**
- Thời gian: {datetime.now().strftime('%H:%M:%S')}
- Line: {line_giao}
- Ca: {ca_giao}
- Nhân viên: {ma_nv_giao} - {ten_nv_giao}
                            """)

    
    # TAB 2: NHẬN CA
    with tab_receive:
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
                active_lines = get_active_lines()
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
                
                ngay_nhan = st.date_input("Ngày Làm Việc *", 
                                          value=datetime.now(),
                                          key="ngay_nhan",
                                          help="Chọn ngày làm việc")
            
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
                                
                                with st.spinner('⏳ Đang lưu dữ liệu nhận ca...'):
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
                                    st.error(f"""
### ❌ Không thể lưu dữ liệu nhận ca

**Lỗi:** {message}

**Hành động khuyến nghị:**
1. Đợi 2-3 giây và thử lại
2. Nếu vẫn lỗi, liên hệ IT
3. Kiểm tra kết nối internet
                                    """)
    
    # TAB 3: XEM DỮ LIỆU
    with tab_view_data:
        st.header("📈 Xem Dữ Liệu Bàn Giao Ca")
        
        # Sub-tabs cho các loại dữ liệu
        data_tab1, data_tab2, data_tab3, data_tab4 = st.tabs([
            "📊 Tổng Hợp Giao-Nhận", 
            "📤 Dữ Liệu Giao Ca",
            "📥 Dữ Liệu Nhận Ca",
            "🔥 Giao Ca Mới Nhất"
        ])
        
        # SUB-TAB 1: TỔNG HỢP GIAO-NHẬN
        with data_tab1:
            st.subheader("📊 Bảng Tổng Hợp Giao-Nhận Ca")
            st.caption("Bảng này hiển thị đầy đủ thông tin giao ca và nhận ca để dễ tra cứu")
            
            # Bộ lọc
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            
            with col_f1:
                filter_from_date = st.date_input(
                    "Từ ngày",
                    value=datetime.now().date() - pd.Timedelta(days=7),
                    key="combined_from_date"
                )
            
            with col_f2:
                filter_to_date = st.date_input(
                    "Đến ngày",
                    value=datetime.now().date(),
                    key="combined_to_date"
                )
            
            with col_f3:
                filter_line_combined = st.selectbox(
                    "Lọc Line",
                    ["Tất cả"] + get_active_lines(),
                    key="combined_filter_line"
                )
            
            with col_f4:
                filter_status = st.selectbox(
                    "Trạng thái",
                    ["Tất cả", "Đã nhận", "Chưa nhận"],
                    key="combined_filter_status"
                )
            
            # Nút tải dữ liệu
            if st.button("🔍 Tải Dữ Liệu", type="primary", key="load_combined_data"):
                with st.spinner("⏳ Đang tải dữ liệu..."):
                    try:
                        combined_data = get_combined_handover_receive_data(
                            from_date=filter_from_date.strftime('%Y-%m-%d'),
                            to_date=filter_to_date.strftime('%Y-%m-%d'),
                            line_filter=filter_line_combined if filter_line_combined != "Tất cả" else None,
                            status_filter=filter_status if filter_status != "Tất cả" else None
                        )
                        
                        if combined_data:
                            df_combined = pd.DataFrame(combined_data)
                            
                            # Hiển thị thống kê
                            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                            with col_s1:
                                st.metric("Tổng số bàn giao", len(df_combined))
                            with col_s2:
                                received_count = len(df_combined[df_combined['Trạng Thái Nhận'] == 'Đã nhận'])
                                st.metric("Đã nhận", received_count)
                            with col_s3:
                                pending_count = len(df_combined[df_combined['Trạng Thái Nhận'] == 'Chưa nhận'])
                                st.metric("Chưa nhận", pending_count)
                            with col_s4:
                                nok_count = df_combined['Số NOK'].sum()
                                st.metric("Tổng NOK", int(nok_count))
                            
                            st.markdown("---")
                            
                            # Hiển thị bảng với styling
                            st.dataframe(
                                df_combined,
                                use_container_width=True,
                                height=600,
                                column_config={
                                    "ID Giao Ca": st.column_config.TextColumn("ID Giao Ca", width="medium"),
                                    "Ngày Giao": st.column_config.DateColumn("Ngày Giao", format="DD/MM/YYYY"),
                                    "Thời Gian Giao": st.column_config.DatetimeColumn("Thời Gian Giao", format="DD/MM/YYYY HH:mm:ss"),
                                    "Thời Gian Nhận": st.column_config.DatetimeColumn("Thời Gian Nhận", format="DD/MM/YYYY HH:mm:ss"),
                                    "Trạng Thái Nhận": st.column_config.TextColumn("Trạng Thái", width="small"),
                                }
                            )
                            
                            # Nút download
                            st.markdown("---")
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                csv = df_combined.to_csv(index=False).encode('utf-8-sig')
                                st.download_button(
                                    "📥 Tải xuống dữ liệu tổng hợp (CSV)",
                                    csv,
                                    f"tong_hop_giao_nhan_{filter_from_date}_{filter_to_date}.csv",
                                    "text/csv",
                                    use_container_width=True
                                )
                        else:
                            st.info("Không có dữ liệu trong khoảng thời gian đã chọn")
                    except Exception as e:
                        st.error(f"Lỗi khi tải dữ liệu: {e}")
        
        # SUB-TAB 2: DỮ LIỆU GIAO CA
        with data_tab2:
            st.subheader("📤 Dữ Liệu Giao Ca")
            
            try:
                data = get_handover_data_for_export()
                if data:
                    df = pd.DataFrame(data)
                    
                    # Thống kê
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Tổng số giao ca", len(df))
                    with col2:
                        received = len(df[df['Trạng Thái Nhận'] == 'Đã nhận'])
                        st.metric("Đã nhận", received)
                    with col3:
                        pending = len(df[df['Trạng Thái Nhận'] == 'Chưa nhận'])
                        st.metric("Chưa nhận", pending)
                    
                    st.markdown("---")
                    st.dataframe(df, use_container_width=True, height=500)
                    
                    # Nút download
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.download_button(
                            "📥 Tải xuống dữ liệu Giao Ca (CSV)",
                            df.to_csv(index=False).encode('utf-8-sig'),
                            "handover_data.csv",
                            "text/csv",
                            use_container_width=True
                        )
                else:
                    st.info("Chưa có dữ liệu giao ca")
            except Exception as e:
                st.error(f"Lỗi khi đọc dữ liệu: {e}")
        
        # SUB-TAB 3: DỮ LIỆU NHẬN CA
        with data_tab3:
            st.subheader("📥 Dữ Liệu Nhận Ca")
            
            try:
                data = get_receive_data_for_export()
                if data:
                    df = pd.DataFrame(data)
                    
                    # Thống kê
                    st.metric("Tổng số nhận ca", len(df))
                    
                    st.markdown("---")
                    st.dataframe(df, use_container_width=True, height=500)
                    
                    # Nút download
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.download_button(
                            "📥 Tải xuống dữ liệu Nhận Ca (CSV)",
                            df.to_csv(index=False).encode('utf-8-sig'),
                            "receive_data.csv",
                            "text/csv",
                            use_container_width=True
                        )
                else:
                    st.info("Chưa có dữ liệu nhận ca")
            except Exception as e:
                st.error(f"Lỗi khi đọc dữ liệu: {e}")
        
        # SUB-TAB 4: GIAO CA MỚI NHẤT
        with data_tab4:
            st.subheader("🔥 Giao Ca Mới Nhất")
            
            try:
                latest_handovers = get_latest_handovers_for_display(limit=10)
                if latest_handovers:
                    for idx, row in enumerate(latest_handovers):
                        # Xác định trạng thái
                        status_badge = ""
                        if row['Trạng Thái Nhận'] == "Đã nhận":
                            status_badge = "✅ Đã nhận"
                        else:
                            status_badge = "⏳ Chưa nhận"
                        
                        with st.expander(f"📋 {row['ID Giao Ca']} - {row['Line']} - {row['Ca']} - {status_badge}", expanded=(idx == 0)):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**ID Giao Ca:** {row['ID Giao Ca']}")
                                st.write(f"**Mã NV:** {row['Mã NV Giao Ca']}")
                                st.write(f"**Tên NV:** {row['Tên NV Giao Ca']}")
                                st.write(f"**Nhân viên thuộc ca:** {row['Nhân viên thuộc ca']}")
                            with col2:
                                st.write(f"**Line:** {row['Line']}")
                                st.write(f"**Ca:** {row['Ca']}")
                                st.write(f"**Ngày:** {row['Ngày Báo Cáo']}")
                                st.write(f"**Trạng thái:** {status_badge}")
                            
                            st.markdown("---")
                            st.markdown("**Thông tin các hạng mục:**")
                            
                            for cat in CATEGORIES:
                                status = row.get(f"{cat} - Tình Trạng", "N/A")
                                comment = row.get(f"{cat} - Comments", "")
                                
                                # Color badge cho status
                                if status == "OK":
                                    badge_color = "green"
                                elif status == "NOK":
                                    badge_color = "red"
                                else:
                                    badge_color = "gray"
                                
                                st.markdown(f"**{cat}:** :{badge_color}[{status}]")
                                if comment:
                                    st.caption(f"📝 {comment}")
                else:
                    st.info("Chưa có dữ liệu giao ca")
            except Exception as e:
                st.error(f"Lỗi khi đọc dữ liệu: {e}")
    
    # TAB 4: QUẢN LÝ (CHỈ HIỂN THỊ KHI LÀ ADMIN)
    if tab_manage is not None:
        with tab_manage:
            # Phần này sẽ được tiếp tục trong phần 2 do giới hạn độ dài
            pass
    
    # TAB 5: CÀI ĐẶT
    with tab_settings:
        # Phần này sẽ được tiếp tục trong phần 2
        pass

if __name__ == "__main__":
    main()

    # TAB 4: QUẢN LÝ (CHỈ HIỂN THỊ KHI LÀ ADMIN)
    if tab_manage is not None:
        with tab_manage:
            st.header("🔧 Quản Lý Bàn Giao Ca")
            st.caption("⚠️ **Chức năng này chỉ dành cho Admin** - Cho phép tìm kiếm, sửa và xóa bàn giao ca")
            
            st.markdown("---")
            
            # Phần tìm kiếm
            st.subheader("🔍 Tìm Kiếm Bàn Giao Ca")
            
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            
            with col_s1:
                search_term = st.text_input(
                    "Tìm kiếm",
                    placeholder="ID, Mã NV, Tên NV...",
                    key="manage_search_term"
                )
            
            with col_s2:
                search_from_date = st.date_input(
                    "Từ ngày",
                    value=datetime.now().date() - pd.Timedelta(days=7),
                    key="manage_from_date"
                )
            
            with col_s3:
                search_to_date = st.date_input(
                    "Đến ngày",
                    value=datetime.now().date(),
                    key="manage_to_date"
                )
            
            with col_s4:
                search_line = st.selectbox(
                    "Line",
                    ["Tất cả"] + get_active_lines(),
                    key="manage_search_line"
                )
            
            col_s5, col_s6 = st.columns(2)
            
            with col_s5:
                search_status = st.selectbox(
                    "Trạng thái",
                    ["Tất cả", "Đã nhận", "Chưa nhận"],
                    key="manage_search_status"
                )
            
            with col_s6:
                st.markdown("<br>", unsafe_allow_html=True)
                search_button = st.button("🔍 Tìm Kiếm", type="primary", use_container_width=True, key="do_search")
            
            st.markdown("---")
            
            # Thực hiện tìm kiếm
            if search_button or 'search_results' in st.session_state:
                if search_button:
                    with st.spinner("⏳ Đang tìm kiếm..."):
                        results = search_handovers(
                            search_term=search_term if search_term else None,
                            from_date=search_from_date.strftime('%Y-%m-%d'),
                            to_date=search_to_date.strftime('%Y-%m-%d'),
                            line=search_line,
                            status=search_status,
                            limit=100
                        )
                        st.session_state.search_results = results
                
                results = st.session_state.get('search_results', [])
                
                if results:
                    st.success(f"✅ Tìm thấy **{len(results)}** kết quả")
                    
                    # Hiển thị kết quả dưới dạng bảng
                    df_results = pd.DataFrame(results)
                    
                    # Thêm cột Actions
                    st.markdown("### 📋 Kết Quả Tìm Kiếm")
                    
                    for idx, row in df_results.iterrows():
                        # Xác định màu dựa trên trạng thái
                        if row['Trạng Thái'] == 'Đã nhận':
                            status_color = "🟢"
                        else:
                            status_color = "🟡"
                        
                        if row['NOK'] > 0:
                            priority_icon = "🔴"
                        else:
                            priority_icon = ""
                        
                        with st.expander(f"{priority_icon} {status_color} **{row['ID Giao Ca']}** - {row['Line']} - {row['Ca']} - {row['Mã NV']} - {row['Tên NV']}", expanded=False):
                            
                            # Thông tin tóm tắt
                            col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                            
                            with col_info1:
                                st.metric("Ngày", row['Ngày'].strftime('%d/%m/%Y') if isinstance(row['Ngày'], (date, datetime)) else row['Ngày'])
                            
                            with col_info2:
                                st.metric("Nhóm", row['Nhóm'])
                            
                            with col_info3:
                                st.write("**Trạng thái hạng mục:**")
                                st.write(f"🟢 OK: {row['OK']} | 🔴 NOK: {row['NOK']} | ⚪ NA: {row['NA']}")
                            
                            with col_info4:
                                st.metric("Trạng thái nhận", row['Trạng Thái'])
                            
                            st.markdown("---")
                            
                            # Nút hành động
                            col_act1, col_act2, col_act3 = st.columns(3)
                            
                            with col_act1:
                                if st.button("📝 Sửa", key=f"edit_{row['ID Giao Ca']}", use_container_width=True):
                                    st.session_state.editing_handover_id = row['ID Giao Ca']
                                    st.rerun()
                            
                            with col_act2:
                                if row['Trạng Thái'] == 'Đã nhận':
                                    if st.button("🗑️ Xóa Phiếu Nhận", key=f"del_receive_{row['ID Giao Ca']}", use_container_width=True, type="secondary"):
                                        st.session_state.deleting_receive_id = row['ID Giao Ca']
                                        st.rerun()
                                else:
                                    st.button("🗑️ Xóa Phiếu Nhận", key=f"del_receive_{row['ID Giao Ca']}", use_container_width=True, disabled=True)
                            
                            with col_act3:
                                if st.button("❌ Xóa Bàn Giao", key=f"del_{row['ID Giao Ca']}", use_container_width=True, type="secondary"):
                                    st.session_state.deleting_handover_id = row['ID Giao Ca']
                                    st.rerun()
                    
                else:
                    st.info("Không tìm thấy kết quả nào")
            
            st.markdown("---")
            
            # XỬ LÝ EDIT HANDOVER
            if 'editing_handover_id' in st.session_state:
                handover_id = st.session_state.editing_handover_id
                
                st.markdown("---")
                st.subheader(f"📝 Chỉnh Sửa Bàn Giao: {handover_id}")
                
                # Lấy thông tin handover
                handover_info = get_handover_by_id(handover_id)
                
                if handover_info:
                    # Kiểm tra trạng thái
                    if handover_info['trang_thai'] == 'Đã nhận':
                        st.error("⚠️ **Cảnh báo:** Bàn giao này đã được nhận. Vui lòng xóa phiếu nhận ca trước khi chỉnh sửa.")
                        
                        col_cancel = st.columns([1, 2, 1])[1]
                        with col_cancel:
                            if st.button("❌ Hủy Chỉnh Sửa", use_container_width=True):
                                del st.session_state.editing_handover_id
                                st.rerun()
                    else:
                        # Form chỉnh sửa
                        with st.form(key="edit_handover_form"):
                            st.markdown("### 👤 Thông Tin Nhân Viên")
                            
                            col_e1, col_e2, col_e3 = st.columns(3)
                            
                            with col_e1:
                                edit_ma_nv = st.text_input("Mã Nhân Viên *", value=handover_info['ma_nv'], max_chars=6)
                                edit_line = st.selectbox("Line *", get_active_lines(), index=get_active_lines().index(handover_info['line']) if handover_info['line'] in get_active_lines() else 0)
                            
                            with col_e2:
                                edit_ten_nv = st.text_input("Tên Nhân Viên *", value=handover_info['ten_nv'])
                                edit_ca = st.selectbox("Ca *", ["Ca Sáng (7h-19h)", "Ca Tối (19h-7h)"], index=0 if handover_info['ca'] == "Ca Sáng (7h-19h)" else 1)
                            
                            with col_e3:
                                edit_chu_ky = st.selectbox("Nhóm *", ["A", "B", "C", "D"], index=["A", "B", "C", "D"].index(handover_info['chu_ky']) if handover_info['chu_ky'] in ["A", "B", "C", "D"] else 0)
                                edit_ngay = st.date_input("Ngày *", value=handover_info['ngay'] if isinstance(handover_info['ngay'], date) else datetime.strptime(str(handover_info['ngay']), '%Y-%m-%d').date())
                            
                            st.markdown("---")
                            st.markdown("### 📋 Các Hạng Mục")
                            
                            edit_data = {}
                            
                            for idx, category in enumerate(CATEGORIES):
                                if idx % 2 == 0:
                                    col1, col2 = st.columns(2)
                                
                                with col1 if idx % 2 == 0 else col2:
                                    st.markdown(f"**{category}**")
                                    
                                    current_status = handover_info.get(f"{category} - Tình Trạng", "OK")
                                    status_index = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
                                    
                                    status = st.selectbox(
                                        "Tình trạng",
                                        options=STATUS_OPTIONS,
                                        index=status_index,
                                        key=f"edit_status_{category}",
                                        label_visibility="collapsed"
                                    )
                                    edit_data[f"{category} - Tình Trạng"] = status
                                    
                                    current_comment = handover_info.get(f"{category} - Comments", "")
                                    comment = st.text_area(
                                        "Ghi chú",
                                        value=current_comment,
                                        key=f"edit_comment_{category}",
                                        height=100,
                                        label_visibility="collapsed"
                                    )
                                    edit_data[f"{category} - Comments"] = comment
                            
                            st.markdown("---")
                            
                            # Nút submit
                            col_submit1, col_submit2, col_submit3 = st.columns([1, 1, 1])
                            
                            with col_submit1:
                                submit_edit = st.form_submit_button("💾 Lưu Thay Đổi", type="primary", use_container_width=True)
                            
                            with col_submit2:
                                cancel_edit = st.form_submit_button("❌ Hủy", use_container_width=True)
                            
                            if submit_edit:
                                # Validate
                                is_valid, error_msg = validate_employee_id(edit_ma_nv)
                                
                                if not is_valid:
                                    st.error(f"⚠️ {error_msg}")
                                else:
                                    # Chuẩn bị dữ liệu update
                                    update_data = {
                                        'ma_nv': edit_ma_nv,
                                        'ten_nv': edit_ten_nv,
                                        'line': edit_line,
                                        'ca': edit_ca,
                                        'chu_ky': edit_chu_ky,
                                        'ngay': edit_ngay.strftime('%Y-%m-%d'),
                                        **edit_data
                                    }
                                    
                                    with st.spinner("⏳ Đang lưu thay đổi..."):
                                        success, message = update_handover(handover_id, update_data)
                                    
                                    if success:
                                        st.success(f"✅ {message}")
                                        time.sleep(1)
                                        del st.session_state.editing_handover_id
                                        if 'search_results' in st.session_state:
                                            del st.session_state.search_results
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {message}")
                            
                            if cancel_edit:
                                del st.session_state.editing_handover_id
                                st.rerun()
                else:
                    st.error("❌ Không tìm thấy thông tin bàn giao")
                    del st.session_state.editing_handover_id
            
            # XỬ LÝ XÓA PHIẾU NHẬN
            if 'deleting_receive_id' in st.session_state:
                handover_id = st.session_state.deleting_receive_id
                
                st.markdown("---")
                st.warning(f"⚠️ **Xác nhận xóa phiếu nhận ca cho bàn giao: {handover_id}**")
                
                receive_info = get_receive_by_handover_id(handover_id)
                
                if receive_info:
                    st.info(f"""
**Thông tin phiếu nhận:**
- Người nhận: {receive_info['ma_nv']} - {receive_info['ten_nv']}
- Thời gian nhận: {receive_info['thoi_gian']}

⚠️ **Lưu ý:** Sau khi xóa, trạng thái bàn giao sẽ chuyển về "Chưa nhận"
                    """)
                    
                    col_del1, col_del2, col_del3 = st.columns([1, 1, 1])
                    
                    with col_del1:
                        if st.button("✅ Xác Nhận Xóa", type="primary", use_container_width=True, key="confirm_del_receive"):
                            with st.spinner("⏳ Đang xóa..."):
                                success, message = delete_receive(handover_id)
                            
                            if success:
                                st.success(f"✅ {message}")
                                time.sleep(1)
                                del st.session_state.deleting_receive_id
                                if 'search_results' in st.session_state:
                                    del st.session_state.search_results
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                    
                    with col_del2:
                        if st.button("❌ Hủy", use_container_width=True, key="cancel_del_receive"):
                            del st.session_state.deleting_receive_id
                            st.rerun()
                else:
                    st.error("❌ Không tìm thấy phiếu nhận ca")
                    del st.session_state.deleting_receive_id
            
            # XỬ LÝ XÓA BÀN GIAO
            if 'deleting_handover_id' in st.session_state:
                handover_id = st.session_state.deleting_handover_id
                
                st.markdown("---")
                st.error(f"🚨 **Xác nhận xóa bàn giao: {handover_id}**")
                
                handover_info = get_handover_by_id(handover_id)
                
                if handover_info:
                    st.warning(f"""
**Thông tin bàn giao:**
- Người giao: {handover_info['ma_nv']} - {handover_info['ten_nv']}
- Line: {handover_info['line']} - Ca: {handover_info['ca']}
- Ngày: {handover_info['ngay']}
- Trạng thái: {handover_info['trang_thai']}

⚠️ **CẢNH BÁO:** 
- Hành động này sẽ xóa vĩnh viễn bàn giao và phiếu nhận ca (nếu có)
- Không thể khôi phục sau khi xóa!
                    """)
                    
                    col_del1, col_del2, col_del3 = st.columns([1, 1, 1])
                    
                    with col_del1:
                        if st.button("🗑️ XÁC NHẬN XÓA", type="primary", use_container_width=True, key="confirm_del_handover"):
                            with st.spinner("⏳ Đang xóa..."):
                                success, message = delete_handover(handover_id)
                            
                            if success:
                                st.success(f"✅ {message}")
                                time.sleep(1)
                                del st.session_state.deleting_handover_id
                                if 'search_results' in st.session_state:
                                    del st.session_state.search_results
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                    
                    with col_del2:
                        if st.button("❌ Hủy", use_container_width=True, key="cancel_del_handover"):
                            del st.session_state.deleting_handover_id
                            st.rerun()
                else:
                    st.error("❌ Không tìm thấy bàn giao")
                    del st.session_state.deleting_handover_id
    
    # TAB 5: CÀI ĐẶT
    with tab_settings:
        st.header("⚙️ Cài Đặt Hệ Thống")
        
        # Kiểm tra đăng nhập cho trang cài đặt
        if 'admin_logged_in' not in st.session_state:
            st.session_state.admin_logged_in = False
        
        if not st.session_state.admin_logged_in:
            st.warning("🔒 Trang này yêu cầu đăng nhập Admin")
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
                                st.session_state.admin_logged_in = True
                                st.session_state.admin_name = full_name
                                st.success(f"Chào mừng {full_name}!")
                                time.sleep(1)
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
                    st.session_state.admin_logged_in = False
                    if 'admin_name' in st.session_state:
                        del st.session_state.admin_name
                    st.rerun()
            
            st.markdown("---")
            
            # Quản lý Lines
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
            
            st.markdown("---")
            st.markdown("---")
            
            # Thông tin hệ thống
            st.subheader("ℹ️ Thông Tin Hệ Thống")
            
            col_sys1, col_sys2, col_sys3 = st.columns(3)
            
            with col_sys1:
                st.info("""
**Phiên bản:** 2.0.0
**Ngày cập nhật:** 2024-01-15
**Tính năng mới:**
- ✅ Edit/Xóa bàn giao ca
- ✅ Quản lý quyền Admin
- ✅ Tìm kiếm nâng cao
                """)
            
            with col_sys2:
                try:
                    total_handovers = len(get_handover_data_for_export())
                    total_receives = len(get_receive_data_for_export())
                    
                    st.metric("Tổng Giao Ca", total_handovers)
                    st.metric("Tổng Nhận Ca", total_receives)
                except:
                    st.warning("Không thể tải thống kê")
            
            with col_sys3:
                st.success("""
**Hỗ trợ:**
- 📧 Email: it@company.com
- 📞 Hotline: 0123-456-789
- 🌐 Website: company.com
                """)

if __name__ == "__main__":
    main()
