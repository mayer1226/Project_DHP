import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from contextlib import contextmanager

# Lấy DATABASE_URL từ environment variable
DATABASE_URL = os.getenv('DATABASE_URL')

# Render sử dụng 'postgres://' nhưng SQLAlchemy cần 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Fallback cho local development
if not DATABASE_URL:
    DATABASE_URL = 'postgresql://localhost:5432/shift_handover'

# Tạo engine với connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # Số connection pool
    max_overflow=20,        # Số connection tối đa khi pool đầy
    pool_pre_ping=True,     # Kiểm tra connection trước khi dùng
    pool_recycle=3600,      # Recycle connection sau 1 giờ
    echo=False              # Set True để debug SQL queries
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Context manager để tự động close session
@contextmanager
def get_db():
    """
    Context manager để quản lý database session
    Tự động commit khi thành công, rollback khi lỗi
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# ===== DATABASE MODELS =====

class User(Base):
    """Model cho bảng users - quản lý tài khoản"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(100), nullable=False)
    full_name = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

class Line(Base):
    """Model cho bảng lines - quản lý các line sản xuất"""
    __tablename__ = 'lines'
    
    id = Column(Integer, primary_key=True, index=True)
    line_code = Column(String(50), unique=True, index=True, nullable=False)
    line_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class Handover(Base):
    """Model cho bảng handovers - lưu thông tin giao ca"""
    __tablename__ = 'handovers'
    
    id = Column(Integer, primary_key=True, index=True)
    handover_id = Column(String(50), unique=True, index=True, nullable=False)
    ma_nv_giao_ca = Column(String(6), nullable=False)
    ten_nv_giao_ca = Column(String(200), nullable=False)
    line = Column(String(100), index=True, nullable=False)
    ca = Column(String(50), nullable=False)
    nhan_vien_thuoc_ca = Column(String(10), nullable=False)
    ngay_bao_cao = Column(DateTime, index=True, nullable=False)
    thoi_gian_giao_ca = Column(DateTime, default=datetime.now, index=True)
    trang_thai_nhan = Column(String(20), default='Chưa nhận', index=True)
    
    # Trạng thái các hạng mục
    status_5s = Column(String(10))
    comment_5s = Column(Text)
    status_an_toan = Column(String(10))
    comment_an_toan = Column(Text)
    status_chat_luong = Column(String(10))
    comment_chat_luong = Column(Text)
    status_thiet_bi = Column(String(10))
    comment_thiet_bi = Column(Text)
    status_ke_hoach = Column(String(10))
    comment_ke_hoach = Column(Text)
    status_khac = Column(String(10))
    comment_khac = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now, index=True)

class Receive(Base):
    """Model cho bảng receives - lưu thông tin nhận ca"""
    __tablename__ = 'receives'
    
    id = Column(Integer, primary_key=True, index=True)
    ma_nv_nhan_ca = Column(String(6), nullable=False)
    ten_nv_nhan_ca = Column(String(200), nullable=False)
    line = Column(String(100), index=True)
    ca = Column(String(50))
    nhan_vien_thuoc_ca = Column(String(10))
    ngay_nhan_ca = Column(DateTime, index=True)
    thoi_gian_nhan_ca = Column(DateTime, default=datetime.now, index=True)
    handover_id = Column(String(50), index=True, nullable=False)
    
    # Xác nhận các hạng mục
    xac_nhan_5s = Column(String(20))
    comment_5s = Column(Text)
    xac_nhan_an_toan = Column(String(20))
    comment_an_toan = Column(Text)
    xac_nhan_chat_luong = Column(String(20))
    comment_chat_luong = Column(Text)
    xac_nhan_thiet_bi = Column(String(20))
    comment_thiet_bi = Column(Text)
    xac_nhan_ke_hoach = Column(String(20))
    comment_ke_hoach = Column(Text)
    xac_nhan_khac = Column(String(20))
    comment_khac = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now)

def init_db():
    """
    Khởi tạo database: tạo tables và dữ liệu mặc định
    Được gọi khi app khởi động lần đầu
    """
    try:
        # Tạo tất cả tables
        Base.metadata.create_all(bind=engine)
        
        # Tạo dữ liệu mặc định
        with get_db() as db:
            # Kiểm tra và tạo admin user
            admin = db.query(User).filter(User.username == 'admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    password='admin123',
                    full_name='Administrator'
                )
                db.add(admin)
            
            # Kiểm tra và tạo default lines
            if db.query(Line).count() == 0:
                default_lines = [
                    Line(line_code='LINE-01', line_name='Line 1', is_active=True),
                    Line(line_code='LINE-02', line_name='Line 2', is_active=True),
                    Line(line_code='LINE-03', line_name='Line 3', is_active=True),
                    Line(line_code='LINE-04', line_name='Line 4', is_active=True),
                    Line(line_code='LINE-05', line_name='Line 5', is_active=True),
                ]
                db.add_all(default_lines)
        
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False
