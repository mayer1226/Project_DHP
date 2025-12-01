# 🚀 Quick Deployment Reference

## Pre-Deployment Checklist ✅

```bash
# 1. Check all files exist
ls -la
# Should see: app.py, database.py, db_operations.py, requirements.txt, 
#             Procfile, runtime.txt, .env.example, .gitignore, README.md

# 2. Initialize Git (if not already)
git init
git add .
git commit -m "PostgreSQL migration for Render deployment"

# 3. Create GitHub repo and push
git remote add origin https://github.com/<username>/shift-handover-system.git
git branch -M main
git push -u origin main
```

## Render Setup (5 Minutes) ⚡

### Step 1: Create PostgreSQL Database
1. Go to: https://dashboard.render.com/
2. New + → PostgreSQL
3. Config:
   - Name: `shift-handover-db`
   - Region: **Singapore**
   - Plan: **Free**
4. Create → Copy **Internal Database URL**

### Step 2: Create Web Service
1. New + → Web Service
2. Connect GitHub repo
3. Config:
   - Name: `shift-handover-app`
   - Region: **Singapore**
   - Plan: **Free**
4. Add Environment Variable:
   - Key: `DATABASE_URL`
   - Value: [Paste Internal DB URL from Step 1]
5. Create Web Service

### Step 3: Wait & Access
- Wait 3-5 mins for build
- Access: `https://shift-handover-app.onrender.com`

## Quick Test 🧪

```
1. Tab "Cài Đặt" → Login (admin/admin123)
2. Tab "Giao Ca" → Create handover (Mã NV: 123456)
3. Tab "Nhận Ca" → Receive handover
4. Tab "Dashboard" → Verify data
```

## Common Issues 🔧

| Error | Solution |
|-------|----------|
| Cannot connect database | Check DATABASE_URL in Environment Variables |
| Module not found | Verify requirements.txt, git push again |
| App sleeping | Free tier sleeps after 15 mins idle (normal) |

## Important URLs 🔗

- Render Dashboard: https://dashboard.render.com/
- App URL: https://shift-handover-app.onrender.com
- Documentation: README.md
- Full Guide: DEPLOYMENT_GUIDE.md

## Default Credentials 🔑

```
Username: admin
Password: admin123
```

⚠️ **CHANGE PASSWORD AFTER FIRST LOGIN!**

## File Structure 📁

```
App/
├── app.py              ← Main Streamlit app (PostgreSQL version)
├── database.py         ← SQLAlchemy models + connection
├── db_operations.py    ← Concurrent-safe CRUD operations
├── requirements.txt    ← Python dependencies
├── Procfile           ← Render start command
├── runtime.txt        ← Python 3.11.7
├── .env.example       ← Environment template
├── .gitignore         ← Git ignore rules
├── .streamlit/
│   └── config.toml    ← Production Streamlit config
├── README.md          ← Main documentation
├── DEPLOYMENT_GUIDE.md ← Detailed deployment steps
└── QUICK_REFERENCE.md  ← This file
```

## Environment Variables 🔐

```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

Copy from Render Database → **Internal Database URL**

## Update App 🔄

```bash
# Make changes
git add .
git commit -m "Update: description"
git push

# Render auto-deploys from main branch
```

## Key Features 🌟

- ✅ Concurrent access protection (row-level locks)
- ✅ Transaction-based operations
- ✅ Retry mechanism with exponential backoff
- ✅ Connection pooling (10 connections, 20 overflow)
- ✅ 2-shift system with cycle tracking (A/B/C/D)
- ✅ Dashboard with metrics and pending handovers
- ✅ Real-time validation and error handling

## Performance Notes 📊

**Free Tier**:
- 750 hours/month (enough for 24/7)
- 512 MB RAM
- Sleeps after 15 mins idle
- First request after sleep: 30-60s

**Database**:
- 1 GB storage
- 97 connections max
- Auto-backup

## Security 🔒

- HTTPS by default (Render certificate)
- PostgreSQL with password auth
- Row-level locking prevents race conditions
- Environment variables for sensitive data
- .gitignore prevents credential leaks

## Monitoring 📈

Check in Render Dashboard:
- Web Service Logs → Real-time application logs
- Web Service Metrics → CPU, Memory, Requests
- Database Metrics → Connections, Size, Performance

## Support 💬

- Render Docs: https://render.com/docs
- Render Support: support@render.com
- PostgreSQL Docs: https://www.postgresql.org/docs/

---

**Last Updated**: December 1, 2025
**Version**: 1.0 (PostgreSQL Migration)
