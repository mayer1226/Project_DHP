# 📤 Hướng Dẫn Upload Lên GitHub

## Bước 1: Cài Đặt Git

### Tải Git cho Windows:
1. Truy cập: https://git-scm.com/download/win
2. Tải bản **64-bit Git for Windows Setup**
3. Chạy file cài đặt
4. Giữ tất cả thiết lập mặc định, click **Next** → **Install**
5. Sau khi cài xong, click **Finish**

### Kiểm tra Git đã cài:
Mở PowerShell mới và chạy:
```powershell
git --version
```
Kết quả mong đợi: `git version 2.x.x`

## Bước 2: Cấu Hình Git (Lần đầu tiên)

```powershell
# Thiết lập tên và email
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Kiểm tra
git config --list
```

## Bước 3: Upload Code Lên GitHub

### 3.1. Di chuyển vào thư mục dự án
```powershell
cd "c:\Users\vnPhuDuo\OneDrive - LEGO\App"
```

### 3.2. Khởi tạo Git repository
```powershell
git init
```

### 3.3. Thêm tất cả file vào staging
```powershell
git add .
```

### 3.4. Commit code
```powershell
git commit -m "Initial commit - PostgreSQL migration for Render deployment"
```

### 3.5. Kết nối với GitHub repository
```powershell
git remote add origin https://github.com/mayer1226/Shift_Handover.git
```

### 3.6. Đổi tên branch thành main
```powershell
git branch -M main
```

### 3.7. Push code lên GitHub
```powershell
git push -u origin main
```

**Lưu ý**: Bạn sẽ được yêu cầu đăng nhập GitHub:
- Username: `mayer1226`
- Password: Sử dụng **Personal Access Token** (không phải mật khẩu thông thường)

## Bước 4: Tạo Personal Access Token (Nếu Cần)

Nếu GitHub yêu cầu token thay vì password:

1. Truy cập: https://github.com/settings/tokens
2. Click **Generate new token** → **Generate new token (classic)**
3. Đặt tên: `Shift_Handover_Deploy`
4. Chọn quyền: ✅ **repo** (full control)
5. Click **Generate token**
6. **QUAN TRỌNG**: Copy token ngay (chỉ hiển thị 1 lần!)
7. Sử dụng token này làm password khi push

## Bước 5: Kiểm Tra Upload Thành Công

1. Truy cập: https://github.com/mayer1226/Shift_Handover
2. Kiểm tra các file đã xuất hiện:
   - app.py
   - database.py
   - db_operations.py
   - requirements.txt
   - Procfile
   - README.md
   - v.v.

## 🎉 Hoàn Thành!

Sau khi upload thành công, bạn có thể tiếp tục với deployment lên Render theo hướng dẫn trong `DEPLOYMENT_GUIDE.md`.

---

## ⚠️ Xử Lý Lỗi Thường Gặp

### Lỗi: "git is not recognized"
**Giải pháp**: Cài đặt Git từ https://git-scm.com/download/win và khởi động lại PowerShell

### Lỗi: "fatal: remote origin already exists"
**Giải pháp**: 
```powershell
git remote remove origin
git remote add origin https://github.com/mayer1226/Shift_Handover.git
```

### Lỗi: "failed to push some refs"
**Giải pháp**:
```powershell
# Pull trước khi push
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### Lỗi: "Authentication failed"
**Giải pháp**: Tạo Personal Access Token (xem Bước 4) và sử dụng làm password

---

## 📝 Các Lệnh Git Hữu Ích

```powershell
# Kiểm tra trạng thái
git status

# Xem lịch sử commit
git log --oneline

# Thêm file mới
git add filename.py

# Commit thay đổi
git commit -m "Description of changes"

# Push lên GitHub
git push

# Pull từ GitHub
git pull

# Xem remote URL
git remote -v
```

---

## 🔄 Update Code Sau Này

Khi bạn thay đổi code và muốn upload lại:

```powershell
# Di chuyển vào thư mục
cd "c:\Users\vnPhuDuo\OneDrive - LEGO\App"

# Xem file đã thay đổi
git status

# Thêm tất cả thay đổi
git add .

# Commit với mô tả
git commit -m "Update: mô tả thay đổi của bạn"

# Push lên GitHub
git push
```

Render sẽ tự động detect và redeploy!

---

**Repository**: https://github.com/mayer1226/Shift_Handover
**Ngày tạo**: December 1, 2025
