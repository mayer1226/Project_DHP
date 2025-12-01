# 🔄 Hệ Thống Bàn Giao Ca Làm Việc Trên Line

Ứng dụng quản lý bàn giao ca làm việc, hỗ trợ giao ca và nhận ca với khả năng xử lý đồng thời nhiều người dùng.

## 🌟 Tính Năng

- **📊 Dashboard**: Tổng quan trạng thái bàn giao ca với metrics và pending handovers
- **📤 Giao Ca**: Tạo bàn giao mới với 6 hạng mục kiểm tra
- **📥 Nhận Ca**: Nhận và xác nhận bàn giao từ ca trước
- **⚙️ Cài Đặt**: Quản lý lines sản xuất và xem dữ liệu

## 🛠️ Công Nghệ

- **Frontend**: Streamlit 1.29.0
- **Backend**: Python 3.11
- **Database**: PostgreSQL với SQLAlchemy ORM
- **Deployment**: Render Cloud Platform

## 🚀 Triển Khai Trên Render

### Bước 1: Tạo PostgreSQL Database

1. Đăng nhập vào [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **PostgreSQL**
3. Điền thông tin:
   - **Name**: `shift-handover-db`
   - **Database**: `shift_handover`
   - **User**: `shift_handover_user`
   - **Region**: Singapore (hoặc gần Việt Nam nhất)
   - **Plan**: Free
4. Click **Create Database**
5. Sau khi tạo xong, copy **Internal Database URL** (dạng: `postgresql://user:pass@host/db`)

### Bước 2: Tạo Web Service

1. Push code lên GitHub repository
2. Trong Render Dashboard, click **New +** → **Web Service**
3. Connect GitHub repository
4. Điền thông tin:
   - **Name**: `shift-handover-app`
   - **Environment**: Python 3
   - **Region**: Singapore
   - **Branch**: main
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: Tự động phát hiện từ Procfile
   - **Plan**: Free
5. Thêm Environment Variable:
   - Key: `DATABASE_URL`
   - Value: Paste Internal Database URL từ bước 1
6. Click **Create Web Service**

### Bước 3: Kiểm Tra Deployment

1. Đợi build hoàn tất (3-5 phút)
2. Truy cập URL được cung cấp (dạng: `https://shift-handover-app.onrender.com`)
3. Đăng nhập với tài khoản admin:
   - Username: `admin`
   - Password: `admin123`

## 🔧 Chạy Local

### Yêu Cầu

- Python 3.11+
- PostgreSQL 12+

### Cài Đặt

```bash
# Clone repository
git clone <repository-url>
cd App

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Cài đặt dependencies
pip install -r requirements.txt

# Tạo file .env
cp .env.example .env

# Sửa DATABASE_URL trong .env
# DATABASE_URL=postgresql://username:password@localhost:5432/shift_handover

# Chạy app
streamlit run app.py
```

## 📝 Hướng Dẫn Sử Dụng

### Giao Ca

1. Nhập Mã NV (6 chữ số) và Tên đầy đủ
2. Chọn Line, Ca làm việc, và Nhóm ca (A/B/C/D)
3. Điền trạng thái (OK/NOK/NA) và comment cho 5 hạng mục bắt buộc:
   - 5S
   - An Toàn
   - Chất Lượng
   - Thiết Bị
   - Kế Hoạch
4. Mục "Khác" là tùy chọn
5. Click **Xác Nhận Giao Ca**

### Nhận Ca

1. Nhập thông tin nhân viên nhận ca
2. Chọn Line và Ngày làm việc
3. Click **Xem Thông Tin Bàn Giao**
4. Xác nhận từng hạng mục bằng checkbox
5. Thêm ghi chú nếu cần
6. Click **Xác Nhận Nhận Ca**

### Quản Lý Lines

1. Truy cập tab **Cài Đặt**
2. Đăng nhập bằng tài khoản admin
3. Chỉnh sửa Lines trong data editor
4. Click **Lưu Cấu Hình**

## 🔒 Bảo Mật

- Row-level locking để tránh double-receive
- Transaction-based operations với retry mechanism
- Connection pooling với timeout và pre-ping
- Authentication cho admin settings
- Validation cho mã nhân viên (6 chữ số)

## 🐛 Xử Lý Lỗi

### Database Connection Error

```
❌ Không thể kết nối database. Vui lòng kiểm tra cấu hình DATABASE_URL
```

**Giải pháp**: Kiểm tra DATABASE_URL trong environment variables

### Double Receive Error

```
❌ Không thể nhận ca! Bàn giao này đã được nhận bởi...
```

**Giải pháp**: Bàn giao đã được xử lý, chọn bàn giao khác hoặc liên hệ người đã nhận

### Validation Errors

- Mã nhân viên phải là 6 chữ số
- Tất cả hạng mục bắt buộc phải có trạng thái và comment
- Mục "Khác" bắt buộc xác nhận nếu có thông tin

## 📊 Database Schema

### Tables

- **users**: Tài khoản người dùng
- **lines**: Cấu hình Lines sản xuất
- **handovers**: Dữ liệu bàn giao ca
- **receives**: Dữ liệu nhận ca

### Relationships

- `receives.handover_id` → `handovers.handover_id` (Foreign Key)

## 🔄 Concurrent Access Protection

Ứng dụng sử dụng pessimistic locking (row-level locks) để đảm bảo an toàn khi nhiều người submit đồng thời:

1. **Lock handover row** khi nhận ca (`with_for_update()`)
2. **Check status** trong transaction
3. **Create receive record** và **update handover status** atomically
4. **Retry mechanism** với exponential backoff nếu conflict

## 📞 Hỗ Trợ

- Liên hệ IT Support để reset mật khẩu admin
- Check logs trong Render Dashboard nếu có lỗi deployment
- Review database connection nếu app không load được

## 📄 License

Internal LEGO Manufacturing Tool - Not for public distribution

