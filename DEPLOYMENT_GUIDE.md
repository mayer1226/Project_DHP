# 🚀 Hướng Dẫn Triển Khai Chi Tiết

## ✅ Checklist Trước Khi Deploy

- [ ] Code đã được push lên GitHub
- [ ] File `.env` KHÔNG được commit (đã có trong .gitignore)
- [ ] Đã tạo tài khoản Render (https://render.com)
- [ ] Đã review lại tất cả code changes

## 📋 Các File Cần Thiết

```
App/
├── app.py                 # Main application (đã convert sang PostgreSQL)
├── database.py            # Database models và connection
├── db_operations.py       # Concurrent-safe CRUD operations
├── requirements.txt       # Python dependencies
├── Procfile              # Render deployment command
├── runtime.txt           # Python version
├── .env.example          # Environment variable template
├── .gitignore           # Git ignore rules
├── .streamlit/
│   └── config.toml      # Streamlit production config
└── README.md            # Documentation
```

## 🎯 Bước 1: Chuẩn Bị GitHub Repository

### 1.1. Khởi tạo Git (nếu chưa có)

```bash
cd "c:\Users\vnPhuDuo\OneDrive - LEGO\App"
git init
git add .
git commit -m "Initial commit - PostgreSQL migration for Render deployment"
```

### 1.2. Tạo Repository Trên GitHub

1. Truy cập https://github.com/new
2. Repository name: `shift-handover-system`
3. Description: `LEGO Manufacturing Shift Handover Management System`
4. Visibility: Private (recommended)
5. Click **Create repository**

### 1.3. Push Code Lên GitHub

```bash
git remote add origin https://github.com/<your-username>/shift-handover-system.git
git branch -M main
git push -u origin main
```

## 🗄️ Bước 2: Tạo PostgreSQL Database Trên Render

### 2.1. Tạo Database

1. Đăng nhập: https://dashboard.render.com/
2. Click **New +** (góc trên bên phải)
3. Chọn **PostgreSQL**

### 2.2. Cấu Hình Database

Điền thông tin sau:

| Field | Value | Ghi Chú |
|-------|-------|---------|
| Name | `shift-handover-db` | Tên database trên Render |
| Database | `shift_handover` | Tên database thực tế |
| User | `shift_handover_user` | Username |
| Region | **Singapore** | Gần Việt Nam nhất |
| PostgreSQL Version | 15 | Mặc định |
| Plan | **Free** | 0$ - đủ cho production nhỏ |

### 2.3. Tạo Database

1. Click **Create Database**
2. Đợi 1-2 phút database khởi tạo
3. Sau khi status = **Available**, scroll xuống phần **Connections**

### 2.4. Copy Database URL

⚠️ **QUAN TRỌNG**: Copy **Internal Database URL** (KHÔNG phải External)

Format: `postgresql://shift_handover_user:PASSWORD@dpg-xxxxx-singapore/shift_handover`

Lưu URL này để dùng ở bước tiếp theo!

## 🌐 Bước 3: Tạo Web Service Trên Render

### 3.1. Tạo Web Service

1. Quay lại Dashboard: https://dashboard.render.com/
2. Click **New +** → **Web Service**
3. Click **Connect a repository**

### 3.2. Connect GitHub

1. Click **GitHub** → Authorize Render
2. Chọn repository: `shift-handover-system`
3. Click **Connect**

### 3.3. Cấu Hình Web Service

Điền thông tin sau:

| Field | Value | Ghi Chú |
|-------|-------|---------|
| Name | `shift-handover-app` | URL sẽ là: shift-handover-app.onrender.com |
| Region | **Singapore** | Cùng region với database |
| Branch | `main` | Branch chính |
| Root Directory | (để trống) | |
| Runtime | **Python 3** | Tự động detect |
| Build Command | `pip install -r requirements.txt` | Tự động detect từ requirements.txt |
| Start Command | `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0` | Tự động detect từ Procfile |
| Plan | **Free** | 0$ - 750 hours/month |

### 3.4. Thêm Environment Variables

Scroll xuống **Environment Variables** → Click **Add Environment Variable**

| Key | Value | Ghi Chú |
|-----|-------|---------|
| `DATABASE_URL` | Paste Internal Database URL từ Bước 2.4 | ⚠️ SỬ DỤNG INTERNAL URL |
| `PYTHON_VERSION` | `3.11.7` | (Optional - đã có runtime.txt) |

⚠️ **LƯU Ý**: Đảm bảo DATABASE_URL bắt đầu bằng `postgresql://` (KHÔNG phải `postgres://`)

### 3.5. Deploy

1. Click **Create Web Service**
2. Render sẽ bắt đầu build và deploy
3. Theo dõi logs trong phần **Logs**

## ⏱️ Bước 4: Theo Dõi Deployment

### 4.1. Build Process (3-5 phút)

Logs sẽ hiển thị:

```
==> Cloning from https://github.com/...
==> Downloading cache...
==> Running build command 'pip install -r requirements.txt'...
    Collecting streamlit==1.29.0
    Collecting pandas==2.1.3
    Collecting psycopg2-binary==2.9.9
    Collecting SQLAlchemy==2.0.23
    Collecting python-dotenv==1.0.0
    Successfully installed...
==> Build completed successfully
```

### 4.2. Start Process

```
==> Running start command 'streamlit run app.py...'
You can now view your Streamlit app in your browser.
URL: http://0.0.0.0:10000
```

### 4.3. Database Initialization

Logs sẽ hiển thị:

```
Database initialization successful
Creating tables...
Tables created successfully
Inserting default data...
Default data inserted successfully
```

### 4.4. Kiểm Tra Status

1. Đợi status chuyển sang **Live** (màu xanh)
2. URL của app: `https://shift-handover-app.onrender.com`

## 🧪 Bước 5: Test Application

### 5.1. Truy Cập App

1. Click vào URL: `https://shift-handover-app.onrender.com`
2. Đợi app load (lần đầu có thể mất 30-60 giây)

### 5.2. Test Login

1. Vào tab **Cài Đặt**
2. Đăng nhập:
   - Username: `admin`
   - Password: `admin123`
3. Kiểm tra danh sách Lines

### 5.3. Test Giao Ca

1. Vào tab **Giao Ca**
2. Nhập thông tin:
   - Mã NV: `123456`
   - Tên: `Test User`
   - Line: `Line 1`
   - Ca: `Ca Sáng (7h-19h)`
   - Nhóm: `A`
3. Điền trạng thái và comment cho các hạng mục
4. Click **Xác Nhận Giao Ca**
5. Kiểm tra thông báo thành công

### 5.4. Test Nhận Ca

1. Vào tab **Nhận Ca**
2. Nhập thông tin người nhận khác
3. Chọn cùng Line và Ngày
4. Click **Xem Thông Tin Bàn Giao**
5. Xác nhận các hạng mục
6. Click **Xác Nhận Nhận Ca**
7. Kiểm tra thông báo thành công

### 5.5. Test Dashboard

1. Vào tab **Dashboard**
2. Kiểm tra metrics hiển thị đúng
3. Kiểm tra bàn giao đã nhận hiển thị trong danh sách

### 5.6. Test Concurrent Access

1. Mở 2 browser tabs khác nhau
2. Tab 1: Tạo giao ca mới
3. Tab 2: Đợi giao ca hiển thị
4. Cả 2 tabs: Cùng lúc click **Xem Thông Tin Bàn Giao**
5. Cả 2 tabs: Điền form và click **Xác Nhận Nhận Ca** gần như đồng thời
6. **Kết quả mong đợi**: 1 tab thành công, 1 tab báo lỗi "đã được nhận"

## 🔧 Bước 6: Troubleshooting

### ❌ Lỗi: "Cannot connect to database"

**Nguyên nhân**: DATABASE_URL sai hoặc database chưa ready

**Giải pháp**:
1. Kiểm tra DATABASE_URL trong Environment Variables
2. Đảm bảo sử dụng **Internal Database URL**
3. Đảm bảo database status = **Available**
4. Restart web service: **Manual Deploy** → **Deploy latest commit**

### ❌ Lỗi: "Module not found"

**Nguyên nhân**: requirements.txt thiếu hoặc sai

**Giải pháp**:
1. Kiểm tra file requirements.txt
2. Commit và push lại:
   ```bash
   git add requirements.txt
   git commit -m "Fix requirements"
   git push
   ```
3. Render sẽ tự động redeploy

### ❌ Lỗi: "Address already in use"

**Nguyên nhân**: Port conflict

**Giải pháp**:
1. Kiểm tra Procfile có đúng: `--server.port=$PORT`
2. Không hardcode port 8501
3. Restart web service

### ⚠️ App chạy chậm sau khi idle

**Nguyên nhân**: Free tier sleep sau 15 phút không hoạt động

**Giải pháp**:
- Lần đầu truy cập sau khi sleep mất 30-60 giây
- Upgrade lên paid plan nếu cần always-on
- Hoặc sử dụng uptime monitoring service để ping định kỳ

## 📊 Bước 7: Monitoring

### 7.1. Logs

1. Truy cập: https://dashboard.render.com/
2. Chọn web service `shift-handover-app`
3. Tab **Logs** → Xem real-time logs

### 7.2. Metrics

1. Tab **Metrics** → Xem:
   - CPU usage
   - Memory usage
   - Request count
   - Response time

### 7.3. Database Metrics

1. Chọn database `shift-handover-db`
2. Tab **Metrics** → Xem:
   - Connection count
   - Database size
   - Query performance

## 🔒 Bước 8: Bảo Mật

### 8.1. Đổi Admin Password

⚠️ **QUAN TRỌNG**: Đổi password mặc định ngay sau khi deploy!

1. Connect vào database qua psql hoặc pgAdmin:
   ```bash
   psql <External-Database-URL>
   ```

2. Đổi password:
   ```sql
   UPDATE users SET password = 'new_secure_password' WHERE username = 'admin';
   ```

### 8.2. Environment Variables

- KHÔNG commit file `.env` vào Git
- KHÔNG share DATABASE_URL publicly
- Thay đổi DATABASE_URL nếu bị leak

### 8.3. HTTPS

- Render tự động cung cấp HTTPS
- URL: `https://shift-handover-app.onrender.com`
- Certificate tự động renew

## 🎉 Hoàn Thành!

App đã sẵn sàng sử dụng tại: `https://shift-handover-app.onrender.com`

## 📞 Support

Nếu gặp vấn đề:

1. Check logs trong Render Dashboard
2. Review database connection status
3. Test locally với PostgreSQL trước
4. Contact Render Support: https://render.com/docs

## 🔄 Update App

Để update app sau này:

```bash
# Make changes to code
git add .
git commit -m "Update: description of changes"
git push

# Render sẽ tự động detect và redeploy
```

## 💰 Cost Estimate

**Free Tier Limits**:
- Web Service: 750 hours/month (đủ cho 1 instance 24/7)
- PostgreSQL: 90 days free trial, sau đó $7/month
- Bandwidth: 100GB/month

**Khi nào nên upgrade**:
- App cần always-on (không sleep)
- Database size > 1GB
- Nhiều concurrent users (> 10)
- Cần faster performance
