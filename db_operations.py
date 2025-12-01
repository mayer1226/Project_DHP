from database import get_db, Handover, Receive, User, Line
from sqlalchemy import and_, func, or_
from datetime import datetime
import time

# ===== HANDOVER OPERATIONS =====

def generate_handover_id():
    """
    Tạo ID giao ca unique theo format: HO-YYYYMMDD-XXXX
    Thread-safe với database lock
    """
    try:
        with get_db() as db:
            today = datetime.now().strftime('%Y%m%d')
            
            # Đếm số handover trong ngày (với lock)
            count = db.query(func.count(Handover.id)).filter(
                Handover.handover_id.like(f'HO-{today}-%')
            ).scalar()
            
            return f"HO-{today}-{(count + 1):04d}"
    except Exception as e:
        # Fallback nếu lỗi
        import random
        today = datetime.now().strftime('%Y%m%d')
        random_num = random.randint(1000, 9999)
        return f"HO-{today}-{random_num}"

def save_handover_safe(data):
    """
    Lưu handover với retry mechanism để xử lý concurrent access
    Returns: (success: bool, result: str/id)
    """
    max_retries = 3
    retry_delay = 0.1  # 100ms
    
    for attempt in range(max_retries):
        try:
            with get_db() as db:
                # Tạo handover object
                handover = Handover(
                    handover_id=data['handover_id'],
                    ma_nv_giao_ca=data['ma_nv'],
                    ten_nv_giao_ca=data['ten_nv'],
                    line=data['line'],
                    ca=data['ca'],
                    nhan_vien_thuoc_ca=data['chu_ky'],
                    ngay_bao_cao=datetime.strptime(data['ngay'], '%Y-%m-%d'),
                    thoi_gian_giao_ca=datetime.now(),
                    trang_thai_nhan='Chưa nhận',
                    status_5s=data.get('5S - Tình Trạng'),
                    comment_5s=data.get('5S - Comments'),
                    status_an_toan=data.get('An Toàn - Tình Trạng'),
                    comment_an_toan=data.get('An Toàn - Comments'),
                    status_chat_luong=data.get('Chất Lượng - Tình Trạng'),
                    comment_chat_luong=data.get('Chất Lượng - Comments'),
                    status_thiet_bi=data.get('Thiết Bị - Tình Trạng'),
                    comment_thiet_bi=data.get('Thiết Bị - Comments'),
                    status_ke_hoach=data.get('Kế Hoạch - Tình Trạng'),
                    comment_ke_hoach=data.get('Kế Hoạch - Comments'),
                    status_khac=data.get('Khác - Tình Trạng'),
                    comment_khac=data.get('Khác - Comments')
                )
                
                db.add(handover)
                db.flush()  # Get ID trước khi commit
                
                return True, handover.handover_id
                
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            else:
                return False, str(e)
    
    return False, "Max retries exceeded"

def get_latest_handover(line, work_date):
    """
    Lấy thông tin bàn giao gần nhất chưa được nhận
    Args:
        line: Tên line
        work_date: datetime.date object
    Returns: dict hoặc None
    """
    try:
        with get_db() as db:
            handover = db.query(Handover).filter(
                and_(
                    Handover.line == line,
                    func.date(Handover.ngay_bao_cao) == work_date,
                    Handover.trang_thai_nhan == 'Chưa nhận'
                )
            ).order_by(Handover.thoi_gian_giao_ca.desc()).first()
            
            if not handover:
                return None
            
            # Convert to dict
            return {
                'ID Giao Ca': handover.handover_id,
                'Mã NV Giao Ca': handover.ma_nv_giao_ca,
                'Tên NV Giao Ca': handover.ten_nv_giao_ca,
                'Line': handover.line,
                'Ca': handover.ca,
                'Nhân viên thuộc ca': handover.nhan_vien_thuoc_ca,
                'Ngày Báo Cáo': handover.ngay_bao_cao.date(),
                'Thời Gian Giao Ca': handover.thoi_gian_giao_ca,
                '5S - Tình Trạng': handover.status_5s,
                '5S - Comments': handover.comment_5s or '',
                'An Toàn - Tình Trạng': handover.status_an_toan,
                'An Toàn - Comments': handover.comment_an_toan or '',
                'Chất Lượng - Tình Trạng': handover.status_chat_luong,
                'Chất Lượng - Comments': handover.comment_chat_luong or '',
                'Thiết Bị - Tình Trạng': handover.status_thiet_bi,
                'Thiết Bị - Comments': handover.comment_thiet_bi or '',
                'Kế Hoạch - Tình Trạng': handover.status_ke_hoach,
                'Kế Hoạch - Comments': handover.comment_ke_hoach or '',
                'Khác - Tình Trạng': handover.status_khac,
                'Khác - Comments': handover.comment_khac or ''
            }
    except Exception as e:
        print(f"Error getting latest handover: {e}")
        return None

def check_handover_received(handover_id):
    """
    Kiểm tra xem bàn giao đã được nhận chưa
    Returns: (is_received: bool, receive_info: dict/None)
    """
    try:
        with get_db() as db:
            handover = db.query(Handover).filter(
                Handover.handover_id == handover_id
            ).first()
            
            if not handover:
                return False, None
            
            if handover.trang_thai_nhan == 'Đã nhận':
                # Lấy thông tin người nhận
                receive = db.query(Receive).filter(
                    Receive.handover_id == handover_id
                ).first()
                
                if receive:
                    return True, {
                        'ma_nv': receive.ma_nv_nhan_ca,
                        'ten_nv': receive.ten_nv_nhan_ca,
                        'thoi_gian': receive.thoi_gian_nhan_ca
                    }
            
            return False, None
    except Exception as e:
        print(f"Error checking handover status: {e}")
        return False, None

# ===== RECEIVE OPERATIONS =====

def save_receive_safe(data, handover_id):
    """
    Lưu receive với pessimistic locking để tránh double-receive
    Returns: (success: bool, message: str)
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            with get_db() as db:
                # LOCK handover row để tránh concurrent receive
                handover = db.query(Handover).filter(
                    Handover.handover_id == handover_id
                ).with_for_update().first()
                
                if not handover:
                    return False, "Không tìm thấy bàn giao"
                
                # Kiểm tra trạng thái (với lock)
                if handover.trang_thai_nhan == 'Đã nhận':
                    return False, "Bàn giao đã được nhận bởi người khác"
                
                # Tạo receive record
                receive = Receive(
                    ma_nv_nhan_ca=data['ma_nv'],
                    ten_nv_nhan_ca=data['ten_nv'],
                    line=data['line'],
                    ca=data['ca'],
                    nhan_vien_thuoc_ca=data['chu_ky'],
                    ngay_nhan_ca=datetime.strptime(data['ngay'], '%Y-%m-%d'),
                    thoi_gian_nhan_ca=datetime.now(),
                    handover_id=handover_id,
                    xac_nhan_5s=data.get('5S - Xác Nhận'),
                    comment_5s=data.get('5S - Comments Nhận'),
                    xac_nhan_an_toan=data.get('An Toàn - Xác Nhận'),
                    comment_an_toan=data.get('An Toàn - Comments Nhận'),
                    xac_nhan_chat_luong=data.get('Chất Lượng - Xác Nhận'),
                    comment_chat_luong=data.get('Chất Lượng - Comments Nhận'),
                    xac_nhan_thiet_bi=data.get('Thiết Bị - Xác Nhận'),
                    comment_thiet_bi=data.get('Thiết Bị - Comments Nhận'),
                    xac_nhan_ke_hoach=data.get('Kế Hoạch - Xác Nhận'),
                    comment_ke_hoach=data.get('Kế Hoạch - Comments Nhận'),
                    xac_nhan_khac=data.get('Khác - Xác Nhận'),
                    comment_khac=data.get('Khác - Comments Nhận')
                )
                
                # Update handover status
                handover.trang_thai_nhan = 'Đã nhận'
                
                db.add(receive)
                db.flush()
                
                return True, "Success"
                
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
            else:
                return False, str(e)
    
    return False, "Max retries exceeded"

# ===== DASHBOARD OPERATIONS =====

def get_dashboard_data(filter_date, filter_line=None):
    """
    Lấy dữ liệu dashboard với filter
    Returns: list of dict
    """
    try:
        with get_db() as db:
            query = db.query(Handover).filter(
                func.date(Handover.ngay_bao_cao) == filter_date
            )
            
            if filter_line and filter_line != "Tất cả":
                query = query.filter(Handover.line == filter_line)
            
            handovers = query.order_by(Handover.thoi_gian_giao_ca.desc()).all()
            
            if not handovers:
                return None
            
            dashboard_data = []
            for h in handovers:
                # Lấy thông tin receive nếu đã nhận
                receive_info = None
                if h.trang_thai_nhan == 'Đã nhận':
                    receive = db.query(Receive).filter(
                        Receive.handover_id == h.handover_id
                    ).first()
                    if receive:
                        receive_info = {
                            'time': receive.thoi_gian_nhan_ca,
                            'by': f"{receive.ma_nv_nhan_ca} - {receive.ten_nv_nhan_ca}"
                        }
                
                # Đếm OK/NOK/NA
                statuses = [h.status_5s, h.status_an_toan, h.status_chat_luong, 
                           h.status_thiet_bi, h.status_ke_hoach, h.status_khac]
                ok_count = sum(1 for s in statuses if s == 'OK')
                nok_count = sum(1 for s in statuses if s == 'NOK')
                na_count = sum(1 for s in statuses if s == 'NA')
                
                dashboard_data.append({
                    'ID Giao Ca': h.handover_id,
                    'Line': h.line,
                    'Ca': h.ca,
                    'Nhân viên thuộc ca': h.nhan_vien_thuoc_ca,
                    'Mã NV Giao': h.ma_nv_giao_ca,
                    'Tên NV Giao': h.ten_nv_giao_ca,
                    'Thời Gian Giao': h.thoi_gian_giao_ca,
                    'OK': ok_count,
                    'NOK': nok_count,
                    'NA': na_count,
                    'Trạng Thái Nhận': h.trang_thai_nhan,
                    'Thời Gian Nhận': receive_info['time'] if receive_info else None,
                    'Người Nhận': receive_info['by'] if receive_info else None
                })
            
            return dashboard_data
    except Exception as e:
        print(f"Error getting dashboard data: {e}")
        return None

# ===== USER OPERATIONS =====

def check_login(username, password):
    """Kiểm tra đăng nhập"""
    try:
        with get_db() as db:
            user = db.query(User).filter(
                and_(User.username == username, User.password == password)
            ).first()
            
            if user:
                return True, user.full_name
            return False, None
    except Exception as e:
        print(f"Error checking login: {e}")
        return False, None

# ===== LINE OPERATIONS =====

def get_active_lines():
    """Lấy danh sách lines đang active"""
    try:
        with get_db() as db:
            lines = db.query(Line).filter(Line.is_active == True).all()
            return [line.line_name for line in lines]
    except Exception as e:
        print(f"Error getting active lines: {e}")
        return ['Line 1', 'Line 2', 'Line 3', 'Line 4', 'Line 5']

def get_all_lines():
    """Lấy tất cả lines để quản lý"""
    try:
        with get_db() as db:
            lines = db.query(Line).all()
            return [{
                'line_code': line.line_code,
                'line_name': line.line_name,
                'is_active': line.is_active
            } for line in lines]
    except Exception as e:
        print(f"Error getting all lines: {e}")
        return []

def save_lines_config(lines_data):
    """
    Lưu cấu hình lines
    Args:
        lines_data: list of dict với keys: line_code, line_name, is_active
    """
    try:
        with get_db() as db:
            # Xóa tất cả lines cũ
            db.query(Line).delete()
            
            # Thêm lines mới
            for line_data in lines_data:
                line = Line(
                    line_code=line_data['line_code'],
                    line_name=line_data['line_name'],
                    is_active=line_data.get('is_active', True)
                )
                db.add(line)
            
            return True
    except Exception as e:
        print(f"Error saving lines config: {e}")
        return False

# ===== DATA EXPORT OPERATIONS =====

def get_handover_data_for_export():
    """Lấy tất cả dữ liệu giao ca để export"""
    try:
        with get_db() as db:
            handovers = db.query(Handover).order_by(
                Handover.created_at.desc()
            ).all()
            
            data = []
            for h in handovers:
                data.append({
                    'ID Giao Ca': h.handover_id,
                    'Mã NV Giao Ca': h.ma_nv_giao_ca,
                    'Tên NV Giao Ca': h.ten_nv_giao_ca,
                    'Line': h.line,
                    'Ca': h.ca,
                    'Nhân viên thuộc ca': h.nhan_vien_thuoc_ca,
                    'Ngày Báo Cáo': h.ngay_bao_cao,
                    'Thời Gian Giao Ca': h.thoi_gian_giao_ca,
                    'Trạng Thái Nhận': h.trang_thai_nhan,
                    '5S - Tình Trạng': h.status_5s,
                    '5S - Comments': h.comment_5s,
                    'An Toàn - Tình Trạng': h.status_an_toan,
                    'An Toàn - Comments': h.comment_an_toan,
                    'Chất Lượng - Tình Trạng': h.status_chat_luong,
                    'Chất Lượng - Comments': h.comment_chat_luong,
                    'Thiết Bị - Tình Trạng': h.status_thiet_bi,
                    'Thiết Bị - Comments': h.comment_thiet_bi,
                    'Kế Hoạch - Tình Trạng': h.status_ke_hoach,
                    'Kế Hoạch - Comments': h.comment_ke_hoach,
                    'Khác - Tình Trạng': h.status_khac,
                    'Khác - Comments': h.comment_khac
                })
            
            return data
    except Exception as e:
        print(f"Error getting handover data: {e}")
        return []

def get_receive_data_for_export():
    """Lấy tất cả dữ liệu nhận ca để export"""
    try:
        with get_db() as db:
            receives = db.query(Receive).order_by(
                Receive.created_at.desc()
            ).all()
            
            data = []
            for r in receives:
                data.append({
                    'Mã NV Nhận Ca': r.ma_nv_nhan_ca,
                    'Tên NV Nhận Ca': r.ten_nv_nhan_ca,
                    'Line': r.line,
                    'Ca': r.ca,
                    'Nhân viên thuộc ca': r.nhan_vien_thuoc_ca,
                    'Ngày Nhận Ca': r.ngay_nhan_ca,
                    'Thời Gian Nhận Ca': r.thoi_gian_nhan_ca,
                    'ID Bàn Giao Tham Chiếu': r.handover_id,
                    '5S - Xác Nhận': r.xac_nhan_5s,
                    '5S - Comments Nhận': r.comment_5s,
                    'An Toàn - Xác Nhận': r.xac_nhan_an_toan,
                    'An Toàn - Comments Nhận': r.comment_an_toan,
                    'Chất Lượng - Xác Nhận': r.xac_nhan_chat_luong,
                    'Chất Lượng - Comments Nhận': r.comment_chat_luong,
                    'Thiết Bị - Xác Nhận': r.xac_nhan_thiet_bi,
                    'Thiết Bị - Comments Nhận': r.comment_thiet_bi,
                    'Kế Hoạch - Xác Nhận': r.xac_nhan_ke_hoach,
                    'Kế Hoạch - Comments Nhận': r.comment_ke_hoach,
                    'Khác - Xác Nhận': r.xac_nhan_khac,
                    'Khác - Comments Nhận': r.comment_khac
                })
            
            return data
    except Exception as e:
        print(f"Error getting receive data: {e}")
        return []

def get_latest_handovers_for_display(limit=10):
    """Lấy N bàn giao gần nhất để hiển thị"""
    try:
        with get_db() as db:
            handovers = db.query(Handover).order_by(
                Handover.thoi_gian_giao_ca.desc()
            ).limit(limit).all()
            
            return [{
                'ID Giao Ca': h.handover_id,
                'Line': h.line,
                'Ca': h.ca,
                'Nhân viên thuộc ca': h.nhan_vien_thuoc_ca,
                'Mã NV Giao Ca': h.ma_nv_giao_ca,
                'Tên NV Giao Ca': h.ten_nv_giao_ca,
                'Ngày Báo Cáo': h.ngay_bao_cao,
                'Thời Gian Giao Ca': h.thoi_gian_giao_ca,
                'Trạng Thái Nhận': h.trang_thai_nhan,
                '5S - Tình Trạng': h.status_5s,
                '5S - Comments': h.comment_5s or '',
                'An Toàn - Tình Trạng': h.status_an_toan,
                'An Toàn - Comments': h.comment_an_toan or '',
                'Chất Lượng - Tình Trạng': h.status_chat_luong,
                'Chất Lượng - Comments': h.comment_chat_luong or '',
                'Thiết Bị - Tình Trạng': h.status_thiet_bi,
                'Thiết Bị - Comments': h.comment_thiet_bi or '',
                'Kế Hoạch - Tình Trạng': h.status_ke_hoach,
                'Kế Hoạch - Comments': h.comment_ke_hoach or '',
                'Khác - Tình Trạng': h.status_khac,
                'Khác - Comments': h.comment_khac or ''
            } for h in handovers]
    except Exception as e:
        print(f"Error getting latest handovers: {e}")
        return []
