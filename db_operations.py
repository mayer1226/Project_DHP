from database import get_db, Handover, Receive, User, Line
from sqlalchemy import and_, func, or_, text, Date, desc
from sqlalchemy.orm import joinedload
from datetime import datetime, date
import time
import uuid

# ===== HANDOVER OPERATIONS =====

def generate_handover_id():
    """
    Tạo ID giao ca unique với PostgreSQL Advisory Lock
    Format: HO-YYYYMMDD-XXXX (production) hoặc HO-timestamp-XXXX (fallback)
    
    Advisory Lock đảm bảo chỉ 1 process được generate ID tại 1 thời điểm
    Tránh race condition khi nhiều user submit đồng thời
    """
    LOCK_ID = 789456  # Unique lock ID cho function này
    
    try:
        with get_db() as db:
            # Kiểm tra xem có phải PostgreSQL không
            db_url = str(db.bind.url)
            is_postgresql = 'postgresql' in db_url
            
            if is_postgresql:
                # PostgreSQL: Dùng Advisory Lock
                try:
                    # Acquire lock (blocking - chỉ 1 thread chạy tại 1 thời điểm)
                    db.execute(text(f"SELECT pg_advisory_lock({LOCK_ID})"))
                    
                    today = datetime.now().strftime('%Y%m%d')
                    
                    # Đếm số handover trong ngày (an toàn vì có lock)
                    count = db.query(func.count(Handover.id)).filter(
                        Handover.handover_id.like(f'HO-{today}-%')
                    ).scalar()
                    
                    new_id = f"HO-{today}-{(count + 1):04d}"
                    
                    # Release lock
                    db.execute(text(f"SELECT pg_advisory_unlock({LOCK_ID})"))
                    
                    return new_id
                    
                except Exception as lock_error:
                    # Nếu lỗi lock, fallback sang UUID
                    print(f"Advisory lock failed: {lock_error}")
                    # Release lock nếu có
                    try:
                        db.execute(text(f"SELECT pg_advisory_unlock({LOCK_ID})"))
                    except:
                        pass
            
            # Fallback: SQLite hoặc PostgreSQL lock failed
            # Dùng timestamp + UUID để đảm bảo unique tuyệt đối
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            random_suffix = uuid.uuid4().hex[:4].upper()
            return f"HO-{timestamp}-{random_suffix}"
            
    except Exception as e:
        print(f"Error generating handover ID: {e}")
        # Ultimate fallback: microsecond timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        return f"HO-{timestamp}"

def save_handover_safe(data):
    """
    Lưu handover với retry mechanism để xử lý concurrent access
    Returns: (success: bool, result: str/id, error_detail: str)
    """
    max_retries = 5
    base_delay = 0.1  # 100ms
    
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
                
                return True, handover.handover_id, None
                
        except Exception as e:
            error_str = str(e).lower()
            
            # Kiểm tra loại lỗi
            is_duplicate = 'duplicate' in error_str or 'unique' in error_str
            is_lock_timeout = 'lock' in error_str or 'timeout' in error_str
            
            if attempt < max_retries - 1:
                if is_duplicate:
                    # Duplicate key: generate new ID và retry
                    print(f"Attempt {attempt + 1}: Duplicate ID detected, regenerating...")
                    data['handover_id'] = generate_handover_id()
                    time.sleep(base_delay * (attempt + 1))
                    continue
                elif is_lock_timeout:
                    # Lock timeout: wait và retry
                    print(f"Attempt {attempt + 1}: Lock timeout, retrying...")
                    time.sleep(base_delay * (attempt + 2))  # Longer wait
                    continue
                else:
                    # Lỗi khác: retry với delay ngắn
                    print(f"Attempt {attempt + 1}: Error {e}, retrying...")
                    time.sleep(base_delay)
                    continue
            else:
                # Hết retry: return detailed error
                if is_duplicate:
                    return False, None, "ID đã tồn tại sau nhiều lần thử. Vui lòng liên hệ IT."
                elif is_lock_timeout:
                    return False, None, "Hệ thống đang bận. Vui lòng thử lại sau vài giây."
                else:
                    return False, None, f"Lỗi lưu dữ liệu: {str(e)}"
    
    return False, None, "Vượt quá số lần thử. Vui lòng thử lại."

def get_latest_handover(line, work_date):
    """
    Lấy thông tin bàn giao gần nhất chưa được nhận
    Args:
        line: Tên line
        work_date: Ngày báo cáo (date object hoặc string YYYY-MM-DD)
    Returns: Handover object hoặc None
    """
    try:
        with get_db() as db:
            # Chuyển đổi work_date sang date object nếu là string
            if isinstance(work_date, str):
                work_date = datetime.strptime(work_date, '%Y-%m-%d').date()
            elif isinstance(work_date, datetime):
                work_date = work_date.date()
            
            query = db.query(Handover).filter(
                and_(
                    Handover.line == line,
                    func.cast(Handover.ngay_bao_cao, Date) == work_date,
                    Handover.trang_thai_nhan == 'Chưa nhận'
                )
            ).order_by(Handover.thoi_gian_giao_ca.desc())
            
            return query.first()
    except Exception as e:
        print(f"Error getting latest handover: {e}")
        return None

def check_handover_received(handover_id):
    """
    Kiểm tra xem handover đã được nhận hay chưa
    Returns: (is_received: bool, receive_data: dict or None)
    """
    try:
        with get_db() as db:
            handover = db.query(Handover).filter(
                Handover.handover_id == handover_id
            ).first()
            
            if not handover:
                return False, None
            
            if handover.trang_thai_nhan == 'Đã nhận':
                # Lấy thông tin nhận ca
                receive = db.query(Receive).filter(
                    Receive.handover_id == handover_id
                ).first()
                
                if receive:
                    return True, {
                        'ma_nv_nhan_ca': receive.ma_nv_nhan_ca,
                        'ten_nv_nhan_ca': receive.ten_nv_nhan_ca,
                        'thoi_gian_nhan_ca': receive.thoi_gian_nhan_ca
                    }
                else:
                    return True, None
            
            return False, None
    except Exception as e:
        print(f"Error checking handover received: {e}")
        return False, None

def get_handover_by_id(handover_id):
    """
    Lấy thông tin handover theo ID
    """
    try:
        with get_db() as db:
            return db.query(Handover).filter(
                Handover.handover_id == handover_id
            ).first()
    except Exception as e:
        print(f"Error getting handover by ID: {e}")
        return None

def get_all_handovers(line=None, start_date=None, end_date=None, status=None):
    """
    Lấy tất cả handover với filters
    """
    try:
        with get_db() as db:
            query = db.query(Handover)
            
            if line:
                query = query.filter(Handover.line == line)
            
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) >= start_date)
            
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) <= end_date)
            
            if status:
                query = query.filter(Handover.trang_thai_nhan == status)
            
            return query.order_by(Handover.thoi_gian_giao_ca.desc()).all()
    except Exception as e:
        print(f"Error getting all handovers: {e}")
        return []

def get_all_handovers_for_admin(line=None, start_date=None, end_date=None):
    """
    Lấy tất cả handover cho admin panel
    Bao gồm cả đã nhận và chưa nhận
    """
    try:
        with get_db() as db:
            query = db.query(Handover)
            
            if line:
                query = query.filter(Handover.line == line)
            
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) >= start_date)
            
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) <= end_date)
            
            return query.order_by(Handover.thoi_gian_giao_ca.desc()).all()
    except Exception as e:
        print(f"Error getting handovers for admin: {e}")
        return []

def delete_handover_by_id(handover_id):
    """
    Xóa handover theo ID (admin function)
    Returns: (success: bool, message: str)
    """
    try:
        with get_db() as db:
            # Kiểm tra handover tồn tại
            handover = db.query(Handover).filter(
                Handover.handover_id == handover_id
            ).first()
            
            if not handover:
                return False, "Không tìm thấy handover"
            
            # Kiểm tra xem đã có receive chưa
            receive = db.query(Receive).filter(
                Receive.handover_id == handover_id
            ).first()
            
            if receive:
                # Xóa receive trước
                db.delete(receive)
            
            # Xóa handover
            db.delete(handover)
            db.commit()
            
            return True, f"Đã xóa handover {handover_id}"
            
    except Exception as e:
        print(f"Error deleting handover: {e}")
        return False, f"Lỗi xóa handover: {str(e)}"

# ===== RECEIVE OPERATIONS =====

def save_receive_safe(data):
    """
    Lưu thông tin nhận ca với locking để tránh duplicate receive
    Returns: (success: bool, message: str)
    """
    max_retries = 3
    base_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            with get_db() as db:
                # Lock handover record để tránh duplicate receive
                handover = db.query(Handover).filter(
                    Handover.handover_id == data['handover_id']
                ).with_for_update().first()
                
                if not handover:
                    return False, "Không tìm thấy thông tin giao ca"
                
                # Kiểm tra đã nhận chưa
                if handover.trang_thai_nhan == 'Đã nhận':
                    return False, "Ca này đã được nhận bởi người khác"
                
                # Tạo receive record
                receive = Receive(
                    handover_id=data['handover_id'],
                    ma_nv_nhan_ca=data['ma_nv'],
                    ten_nv_nhan_ca=data['ten_nv'],
                    thoi_gian_nhan_ca=datetime.now(),
                    xac_nhan_5s=data.get('5S - Xác Nhận'),
                    comment_5s=data.get('5S - Comments'),
                    xac_nhan_an_toan=data.get('An Toàn - Xác Nhận'),
                    comment_an_toan=data.get('An Toàn - Comments'),
                    xac_nhan_chat_luong=data.get('Chất Lượng - Xác Nhận'),
                    comment_chat_luong=data.get('Chất Lượng - Comments'),
                    xac_nhan_thiet_bi=data.get('Thiết Bị - Xác Nhận'),
                    comment_thiet_bi=data.get('Thiết Bị - Comments'),
                    xac_nhan_ke_hoach=data.get('Kế Hoạch - Xác Nhận'),
                    comment_ke_hoach=data.get('Kế Hoạch - Comments'),
                    xac_nhan_khac=data.get('Khác - Xác Nhận'),
                    comment_khac=data.get('Khác - Comments')
                )
                
                db.add(receive)
                
                # Cập nhật trạng thái handover
                handover.trang_thai_nhan = 'Đã nhận'
                
                db.commit()
                return True, "Đã xác nhận nhận ca thành công"
                
        except Exception as e:
            error_str = str(e).lower()
            
            if 'lock' in error_str or 'timeout' in error_str:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1}: Lock conflict, retrying...")
                    time.sleep(base_delay * (attempt + 2))
                    continue
                else:
                    return False, "Hệ thống đang bận. Vui lòng thử lại sau vài giây."
            else:
                if attempt < max_retries - 1:
                    time.sleep(base_delay)
                    continue
                else:
                    return False, f"Lỗi lưu dữ liệu: {str(e)}"
    
    return False, "Vượt quá số lần thử. Vui lòng thử lại."

def get_all_receives(line=None, start_date=None, end_date=None):
    """
    Lấy tất cả receive với filters
    """
    try:
        with get_db() as db:
            query = db.query(Receive).join(Handover)
            
            if line:
                query = query.filter(Handover.line == line)
            
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) >= start_date)
            
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) <= end_date)
            
            return query.order_by(Receive.thoi_gian_nhan_ca.desc()).all()
    except Exception as e:
        print(f"Error getting all receives: {e}")
        return []

def get_combined_handover_receive_data(line=None, start_date=None, end_date=None):
    """
    Lấy dữ liệu kết hợp handover và receive (LEFT JOIN)
    Returns: List of tuples (handover, receive or None)
    """
    try:
        with get_db() as db:
            query = db.query(Handover, Receive).outerjoin(
                Receive, Handover.handover_id == Receive.handover_id
            )
            
            if line:
                query = query.filter(Handover.line == line)
            
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) >= start_date)
            
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) <= end_date)
            
            return query.order_by(Handover.thoi_gian_giao_ca.desc()).all()
    except Exception as e:
        print(f"Error getting combined data: {e}")
        return []

# ===== USER OPERATIONS =====

def verify_user(username, password):
    """
    Xác thực user
    Returns: (success: bool, user_data: dict or None)
    """
    try:
        with get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            
            if user and user.password == password:
                return True, {
                    'username': user.username,
                    'full_name': user.full_name
                }
            return False, None
    except Exception as e:
        print(f"Error verifying user: {e}")
        return False, None

def get_all_users():
    """
    Lấy tất cả users
    """
    try:
        with get_db() as db:
            return db.query(User).all()
    except Exception as e:
        print(f"Error getting users: {e}")
        return []

def create_user(username, password, full_name):
    """
    Tạo user mới
    Returns: (success: bool, message: str)
    """
    try:
        with get_db() as db:
            # Kiểm tra username đã tồn tại chưa
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                return False, "Username đã tồn tại"
            
            user = User(
                username=username,
                password=password,
                full_name=full_name
            )
            db.add(user)
            db.commit()
            return True, "Tạo user thành công"
    except Exception as e:
        print(f"Error creating user: {e}")
        return False, f"Lỗi tạo user: {str(e)}"

def update_user_password(username, new_password):
    """
    Cập nhật password user
    Returns: (success: bool, message: str)
    """
    try:
        with get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return False, "Không tìm thấy user"
            
            user.password = new_password
            db.commit()
            return True, "Cập nhật password thành công"
    except Exception as e:
        print(f"Error updating password: {e}")
        return False, f"Lỗi cập nhật password: {str(e)}"

def delete_user(username):
    """
    Xóa user
    Returns: (success: bool, message: str)
    """
    try:
        with get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return False, "Không tìm thấy user"
            
            db.delete(user)
            db.commit()
            return True, "Xóa user thành công"
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False, f"Lỗi xóa user: {str(e)}"

# ===== LINE OPERATIONS =====

def get_active_lines():
    """
    Lấy danh sách các line đang active
    Returns: List of line names
    """
    try:
        with get_db() as db:
            lines = db.query(Line).filter(Line.is_active == True).all()
            return [line.line_name for line in lines]
    except Exception as e:
        print(f"Error getting active lines: {e}")
        return []

def get_all_lines():
    """
    Lấy tất cả lines
    """
    try:
        with get_db() as db:
            return db.query(Line).all()
    except Exception as e:
        print(f"Error getting all lines: {e}")
        return []

def create_line(line_code, line_name, is_active=True):
    """
    Tạo line mới
    Returns: (success: bool, message: str)
    """
    try:
        with get_db() as db:
            # Kiểm tra line_code đã tồn tại chưa
            existing = db.query(Line).filter(Line.line_code == line_code).first()
            if existing:
                return False, "Line code đã tồn tại"
            
            line = Line(
                line_code=line_code,
                line_name=line_name,
                is_active=is_active
            )
            db.add(line)
            db.commit()
            return True, "Tạo line thành công"
    except Exception as e:
        print(f"Error creating line: {e}")
        return False, f"Lỗi tạo line: {str(e)}"

def update_line(line_code, line_name=None, is_active=None):
    """
    Cập nhật thông tin line
    Returns: (success: bool, message: str)
    """
    try:
        with get_db() as db:
            line = db.query(Line).filter(Line.line_code == line_code).first()
            if not line:
                return False, "Không tìm thấy line"
            
            if line_name is not None:
                line.line_name = line_name
            if is_active is not None:
                line.is_active = is_active
            
            db.commit()
            return True, "Cập nhật line thành công"
    except Exception as e:
        print(f"Error updating line: {e}")
        return False, f"Lỗi cập nhật line: {str(e)}"

def delete_line(line_code):
    """
    Xóa line
    Returns: (success: bool, message: str)
    """
    try:
        with get_db() as db:
            line = db.query(Line).filter(Line.line_code == line_code).first()
            if not line:
                return False, "Không tìm thấy line"
            
            # Kiểm tra xem có handover nào dùng line này không
            handover_count = db.query(func.count(Handover.id)).filter(
                Handover.line == line.line_name
            ).scalar()
            
            if handover_count > 0:
                return False, f"Không thể xóa. Line này có {handover_count} handover"
            
            db.delete(line)
            db.commit()
            return True, "Xóa line thành công"
    except Exception as e:
        print(f"Error deleting line: {e}")
        return False, f"Lỗi xóa line: {str(e)}"

# ===== DASHBOARD/STATISTICS OPERATIONS =====

def get_dashboard_stats(line=None, start_date=None, end_date=None):
    """
    Lấy thống kê cho dashboard
    Returns: dict với các metrics
    """
    try:
        with get_db() as db:
            query = db.query(Handover)
            
            if line:
                query = query.filter(Handover.line == line)
            
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) >= start_date)
            
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(func.cast(Handover.ngay_bao_cao, Date) <= end_date)
            
            total_handovers = query.count()
            
            received = query.filter(Handover.trang_thai_nhan == 'Đã nhận').count()
            pending = query.filter(Handover.trang_thai_nhan == 'Chưa nhận').count()
            
            # Tính % nhận ca đúng hạn (receive trong vòng 1h từ handover)
            on_time_count = 0
            if received > 0:
                receives = db.query(Receive).join(Handover).filter(
                    Handover.trang_thai_nhan == 'Đã nhận'
                )
                if line:
                    receives = receives.filter(Handover.line == line)
                if start_date:
                    receives = receives.filter(func.cast(Handover.ngay_bao_cao, Date) >= start_date)
                if end_date:
                    receives = receives.filter(func.cast(Handover.ngay_bao_cao, Date) <= end_date)
                
                for receive, handover in receives.join(Handover).with_entities(Receive, Handover).all():
                    time_diff = (receive.thoi_gian_nhan_ca - handover.thoi_gian_giao_ca).total_seconds()
                    if time_diff <= 3600:  # 1 hour
                        on_time_count += 1
            
            on_time_rate = (on_time_count / received * 100) if received > 0 else 0
            
            return {
                'total_handovers': total_handovers,
                'received': received,
                'pending': pending,
                'on_time_count': on_time_count,
                'on_time_rate': round(on_time_rate, 1)
            }
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return {
            'total_handovers': 0,
            'received': 0,
            'pending': 0,
            'on_time_count': 0,
            'on_time_rate': 0
        }

def get_pending_handovers(line=None, limit=10):
    """
    Lấy các handover chưa nhận (gần nhất)
    """
    try:
        with get_db() as db:
            query = db.query(Handover).filter(
                Handover.trang_thai_nhan == 'Chưa nhận'
            )
            
            if line:
                query = query.filter(Handover.line == line)
            
            query = query.order_by(Handover.thoi_gian_giao_ca.desc())
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
    except Exception as e:
        print(f"Error getting pending handovers: {e}")
        return []
