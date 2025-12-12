from database import get_db, Handover, Receive, User, Line
from sqlalchemy import and_, func, or_
from datetime import datetime
import time
import random

# ===== HANDOVER OPERATIONS =====

def generate_handover_id():
    """
    Tạo ID giao ca unique theo format HYBRID:
    - Format cơ bản: HO-YYYYMMDD-XXXX (tương thích cũ)
    - Nếu trùng: HO-YYYYMMDD-XXXX-RRR (thêm random suffix)
    
    Thread-safe với database lock
    """
    try:
        with get_db() as db:
            today = datetime.now().strftime('%Y%m%d')
            
            # Đếm số handover trong ngày (với lock)
            count = db.query(func.count(Handover.id)).filter(
                Handover.handover_id.like(f'HO-{today}-%')
            ).scalar()
            
            base_id = f"HO-{today}-{(count + 1):04d}"
            
            # Kiểm tra xem ID đã tồn tại chưa
            exists = db.query(Handover).filter(
                Handover.handover_id == base_id
            ).first()
            
            if exists:
                # Nếu trùng, thêm random suffix
                random_suffix = random.randint(100, 999)
                return f"{base_id}-{random_suffix}"
            
            return base_id
            
    except Exception as e:
        # Fallback nếu lỗi database
        print(f"Error generating handover_id: {e}")
        today = datetime.now().strftime('%Y%m%d')
        timestamp = datetime.now().strftime('%H%M%S')
        random_num = random.randint(100, 999)
        return f"HO-{today}-{timestamp}-{random_num}"


def save_handover_safe(data, max_retries=10):
    """
    Lưu handover với retry mechanism để xử lý concurrent access
    
    Args:
        data: dict chứa thông tin handover (KHÔNG bao gồm handover_id)
        max_retries: số lần thử lại tối đa
    
    Returns: 
        (success: bool, result: str)
        - Nếu thành công: (True, handover_id)
        - Nếu thất bại: (False, error_message)
    """
    retry_delay = 0.05  # 50ms
    
    for attempt in range(max_retries):
        try:
            with get_db() as db:
                # Tạo ID MỚI cho mỗi lần thử
                handover_id = generate_handover_id()
                
                # Kiểm tra ID đã tồn tại chưa (double-check)
                exists = db.query(Handover).filter(
                    Handover.handover_id == handover_id
                ).first()
                
                if exists:
                    # ID đã tồn tại, thử lại
                    print(f"Attempt {attempt + 1}: ID {handover_id} already exists, retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                
                # Tạo handover object
                handover = Handover(
                    handover_id=handover_id,
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
                
                print(f"✅ Successfully saved handover with ID: {handover_id}")
                return True, handover.handover_id
                
        except Exception as e:
            error_str = str(e).lower()
            
            # Kiểm tra lỗi duplicate key
            if 'duplicate' in error_str or 'unique constraint' in error_str:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1}: Duplicate key error, retrying...")
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    return False, "ID đã tồn tại sau nhiều lần thử. Vui lòng thử lại sau vài giây."
            else:
                # Lỗi khác (không phải duplicate)
                print(f"Error saving handover: {e}")
                return False, f"Lỗi database: {str(e)}"
    
    return False, "Không thể tạo ID duy nhất sau nhiều lần thử. Vui lòng thử lại."


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
        
def get_combined_handover_receive_data(from_date, to_date, line_filter=None, status_filter=None):
    """
    Lấy dữ liệu tổng hợp giao ca và nhận ca
    
    Args:
        from_date: Ngày bắt đầu (YYYY-MM-DD)
        to_date: Ngày kết thúc (YYYY-MM-DD)
        line_filter: Lọc theo line (None = tất cả)
        status_filter: Lọc theo trạng thái (None = tất cả, "Đã nhận", "Chưa nhận")
    
    Returns:
        List of dict chứa thông tin tổng hợp
    """
    try:
        with get_db() as db:
            # Query handovers với LEFT JOIN receives
            query = db.query(
                Handover.handover_id,
                Handover.ngay_bao_cao,
                Handover.thoi_gian_giao_ca,
                Handover.line,
                Handover.ca,
                Handover.nhan_vien_thuoc_ca,
                Handover.ma_nv_giao_ca,
                Handover.ten_nv_giao_ca,
                Handover.trang_thai_nhan,
                Handover.status_5s,
                Handover.status_an_toan,
                Handover.status_chat_luong,
                Handover.status_thiet_bi,
                Handover.status_ke_hoach,
                Handover.status_khac,
                Receive.ma_nv_nhan_ca,
                Receive.ten_nv_nhan_ca,
                Receive.thoi_gian_nhan_ca
            ).outerjoin(
                Receive, Handover.handover_id == Receive.handover_id
            ).filter(
                and_(
                    func.date(Handover.ngay_bao_cao) >= from_date,
                    func.date(Handover.ngay_bao_cao) <= to_date
                )
            )
            
            # Áp dụng filter
            if line_filter:
                query = query.filter(Handover.line == line_filter)
            
            if status_filter:
                query = query.filter(Handover.trang_thai_nhan == status_filter)
            
            # Sắp xếp theo thời gian giao ca giảm dần
            query = query.order_by(Handover.thoi_gian_giao_ca.desc())
            
            results = query.all()
            
            # Convert to list of dict
            combined_data = []
            for row in results:
                # Đếm OK/NOK/NA
                statuses = [row.status_5s, row.status_an_toan, row.status_chat_luong,
                           row.status_thiet_bi, row.status_ke_hoach, row.status_khac]
                ok_count = sum(1 for s in statuses if s == 'OK')
                nok_count = sum(1 for s in statuses if s == 'NOK')
                na_count = sum(1 for s in statuses if s == 'NA')
                
                combined_data.append({
                    'ID Giao Ca': row.handover_id,
                    'Ngày Giao': row.ngay_bao_cao,
                    'Thời Gian Giao': row.thoi_gian_giao_ca,
                    'Line': row.line,
                    'Ca': row.ca,
                    'Nhóm': row.nhan_vien_thuoc_ca,
                    'Mã NV Giao': row.ma_nv_giao_ca,
                    'Tên NV Giao': row.ten_nv_giao_ca,
                    'Số OK': ok_count,
                    'Số NOK': nok_count,
                    'Số NA': na_count,
                    'Trạng Thái Nhận': row.trang_thai_nhan,
                    'Mã NV Nhận': row.ma_nv_nhan_ca if row.ma_nv_nhan_ca else '',
                    'Tên NV Nhận': row.ten_nv_nhan_ca if row.ten_nv_nhan_ca else '',
                    'Thời Gian Nhận': row.thoi_gian_nhan_ca if row.thoi_gian_nhan_ca else None
                })
            
            return combined_data
            
    except Exception as e:
        print(f"Error getting combined data: {e}")
        return []
# ===== ADMIN OPERATIONS - EDIT/DELETE =====

def get_handover_by_id(handover_id):
    """
    Lấy thông tin chi tiết handover theo ID
    Returns: dict hoặc None
    """
    try:
        with get_db() as db:
            handover = db.query(Handover).filter(
                Handover.handover_id == handover_id
            ).first()
            
            if not handover:
                return None
            
            return {
                'handover_id': handover.handover_id,
                'ma_nv': handover.ma_nv_giao_ca,
                'ten_nv': handover.ten_nv_giao_ca,
                'line': handover.line,
                'ca': handover.ca,
                'chu_ky': handover.nhan_vien_thuoc_ca,
                'ngay': handover.ngay_bao_cao,
                'thoi_gian': handover.thoi_gian_giao_ca,
                'trang_thai': handover.trang_thai_nhan,
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
        print(f"Error getting handover by ID: {e}")
        return None


def update_handover(handover_id, data):
    """
    Cập nhật thông tin handover
    
    Args:
        handover_id: ID của handover cần update
        data: dict chứa thông tin cần update
    
    Returns:
        (success: bool, message: str)
    """
    try:
        with get_db() as db:
            # Tìm handover
            handover = db.query(Handover).filter(
                Handover.handover_id == handover_id
            ).first()
            
            if not handover:
                return False, "Không tìm thấy bàn giao"
            
            # Kiểm tra xem đã được nhận chưa
            if handover.trang_thai_nhan == 'Đã nhận':
                return False, "Không thể sửa bàn giao đã được nhận. Vui lòng xóa phiếu nhận ca trước."
            
            # Update thông tin
            handover.ma_nv_giao_ca = data.get('ma_nv', handover.ma_nv_giao_ca)
            handover.ten_nv_giao_ca = data.get('ten_nv', handover.ten_nv_giao_ca)
            handover.line = data.get('line', handover.line)
            handover.ca = data.get('ca', handover.ca)
            handover.nhan_vien_thuoc_ca = data.get('chu_ky', handover.nhan_vien_thuoc_ca)
            
            if 'ngay' in data:
                handover.ngay_bao_cao = datetime.strptime(data['ngay'], '%Y-%m-%d')
            
            # Update các hạng mục
            handover.status_5s = data.get('5S - Tình Trạng', handover.status_5s)
            handover.comment_5s = data.get('5S - Comments', handover.comment_5s)
            handover.status_an_toan = data.get('An Toàn - Tình Trạng', handover.status_an_toan)
            handover.comment_an_toan = data.get('An Toàn - Comments', handover.comment_an_toan)
            handover.status_chat_luong = data.get('Chất Lượng - Tình Trạng', handover.status_chat_luong)
            handover.comment_chat_luong = data.get('Chất Lượng - Comments', handover.comment_chat_luong)
            handover.status_thiet_bi = data.get('Thiết Bị - Tình Trạng', handover.status_thiet_bi)
            handover.comment_thiet_bi = data.get('Thiết Bị - Comments', handover.comment_thiet_bi)
            handover.status_ke_hoach = data.get('Kế Hoạch - Tình Trạng', handover.status_ke_hoach)
            handover.comment_ke_hoach = data.get('Kế Hoạch - Comments', handover.comment_ke_hoach)
            handover.status_khac = data.get('Khác - Tình Trạng', handover.status_khac)
            handover.comment_khac = data.get('Khác - Comments', handover.comment_khac)
            
            db.flush()
            
            return True, "Cập nhật thành công"
            
    except Exception as e:
        print(f"Error updating handover: {e}")
        return False, f"Lỗi: {str(e)}"


def delete_handover(handover_id):
    """
    Xóa handover và receive liên quan
    
    Args:
        handover_id: ID của handover cần xóa
    
    Returns:
        (success: bool, message: str)
    """
    try:
        with get_db() as db:
            # Tìm handover
            handover = db.query(Handover).filter(
                Handover.handover_id == handover_id
            ).first()
            
            if not handover:
                return False, "Không tìm thấy bàn giao"
            
            # Xóa receive liên quan (nếu có)
            db.query(Receive).filter(
                Receive.handover_id == handover_id
            ).delete()
            
            # Xóa handover
            db.delete(handover)
            db.flush()
            
            return True, "Đã xóa bàn giao thành công"
            
    except Exception as e:
        print(f"Error deleting handover: {e}")
        return False, f"Lỗi: {str(e)}"


def get_receive_by_handover_id(handover_id):
    """
    Lấy thông tin receive theo handover_id
    Returns: dict hoặc None
    """
    try:
        with get_db() as db:
            receive = db.query(Receive).filter(
                Receive.handover_id == handover_id
            ).first()
            
            if not receive:
                return None
            
            return {
                'id': receive.id,
                'ma_nv': receive.ma_nv_nhan_ca,
                'ten_nv': receive.ten_nv_nhan_ca,
                'line': receive.line,
                'ca': receive.ca,
                'chu_ky': receive.nhan_vien_thuoc_ca,
                'ngay': receive.ngay_nhan_ca,
                'thoi_gian': receive.thoi_gian_nhan_ca,
                'handover_id': receive.handover_id,
                '5S - Xác Nhận': receive.xac_nhan_5s,
                '5S - Comments': receive.comment_5s or '',
                'An Toàn - Xác Nhận': receive.xac_nhan_an_toan,
                'An Toàn - Comments': receive.comment_an_toan or '',
                'Chất Lượng - Xác Nhận': receive.xac_nhan_chat_luong,
                'Chất Lượng - Comments': receive.comment_chat_luong or '',
                'Thiết Bị - Xác Nhận': receive.xac_nhan_thiet_bi,
                'Thiết Bị - Comments': receive.comment_thiet_bi or '',
                'Kế Hoạch - Xác Nhận': receive.xac_nhan_ke_hoach,
                'Kế Hoạch - Comments': receive.comment_ke_hoach or '',
                'Khác - Xác Nhận': receive.xac_nhan_khac,
                'Khác - Comments': receive.comment_khac or ''
            }
    except Exception as e:
        print(f"Error getting receive by handover_id: {e}")
        return None


def delete_receive(handover_id):
    """
    Xóa phiếu nhận ca và cập nhật trạng thái handover
    
    Args:
        handover_id: ID của handover
    
    Returns:
        (success: bool, message: str)
    """
    try:
        with get_db() as db:
            # Xóa receive
            deleted = db.query(Receive).filter(
                Receive.handover_id == handover_id
            ).delete()
            
            if deleted == 0:
                return False, "Không tìm thấy phiếu nhận ca"
            
            # Cập nhật trạng thái handover về "Chưa nhận"
            handover = db.query(Handover).filter(
                Handover.handover_id == handover_id
            ).first()
            
            if handover:
                handover.trang_thai_nhan = 'Chưa nhận'
            
            db.flush()
            
            return True, "Đã xóa phiếu nhận ca thành công"
            
    except Exception as e:
        print(f"Error deleting receive: {e}")
        return False, f"Lỗi: {str(e)}"


def search_handovers(search_term=None, from_date=None, to_date=None, line=None, status=None, limit=50):
    """
    Tìm kiếm handovers với nhiều tiêu chí
    
    Args:
        search_term: Tìm theo ID, mã NV, tên NV
        from_date: Từ ngày (YYYY-MM-DD)
        to_date: Đến ngày (YYYY-MM-DD)
        line: Lọc theo line
        status: Lọc theo trạng thái nhận
        limit: Giới hạn số kết quả
    
    Returns:
        List of dict
    """
    try:
        with get_db() as db:
            query = db.query(Handover)
            
            # Tìm kiếm theo search_term
            if search_term:
                query = query.filter(
                    or_(
                        Handover.handover_id.like(f'%{search_term}%'),
                        Handover.ma_nv_giao_ca.like(f'%{search_term}%'),
                        Handover.ten_nv_giao_ca.like(f'%{search_term}%')
                    )
                )
            
            # Lọc theo ngày
            if from_date:
                query = query.filter(func.date(Handover.ngay_bao_cao) >= from_date)
            if to_date:
                query = query.filter(func.date(Handover.ngay_bao_cao) <= to_date)
            
            # Lọc theo line
            if line and line != "Tất cả":
                query = query.filter(Handover.line == line)
            
            # Lọc theo trạng thái
            if status and status != "Tất cả":
                query = query.filter(Handover.trang_thai_nhan == status)
            
            # Sắp xếp và giới hạn
            handovers = query.order_by(Handover.thoi_gian_giao_ca.desc()).limit(limit).all()
            
            # Convert to list of dict
            results = []
            for h in handovers:
                # Đếm OK/NOK/NA
                statuses = [h.status_5s, h.status_an_toan, h.status_chat_luong,
                           h.status_thiet_bi, h.status_ke_hoach, h.status_khac]
                ok_count = sum(1 for s in statuses if s == 'OK')
                nok_count = sum(1 for s in statuses if s == 'NOK')
                na_count = sum(1 for s in statuses if s == 'NA')
                
                results.append({
                    'ID Giao Ca': h.handover_id,
                    'Ngày': h.ngay_bao_cao,
                    'Thời Gian': h.thoi_gian_giao_ca,
                    'Line': h.line,
                    'Ca': h.ca,
                    'Nhóm': h.nhan_vien_thuoc_ca,
                    'Mã NV': h.ma_nv_giao_ca,
                    'Tên NV': h.ten_nv_giao_ca,
                    'OK': ok_count,
                    'NOK': nok_count,
                    'NA': na_count,
                    'Trạng Thái': h.trang_thai_nhan
                })
            
            return results
            
    except Exception as e:
        print(f"Error searching handovers: {e}")
        return []
