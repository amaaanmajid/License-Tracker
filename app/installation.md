🚀 Installation Guide - License Tracker

Complete step-by-step installation guide for all platforms.

---

## 📋 Prerequisites

Before starting, ensure you have:

- **Python 3.9+** ([Download](https://www.python.org/downloads/))
- **Node.js 16+** ([Download](https://nodejs.org/))
- **MySQL 8.0+** or **MariaDB 10.5+** ([MySQL Download](https://dev.mysql.com/downloads/) | [MariaDB Download](https://mariadb.org/download/))
- **Git** ([Download](https://git-scm.com/downloads))
- **Text Editor** (VS Code, Sublime Text, etc.)

---

## 🖥️ Platform-Specific Setup

### Windows Installation

#### 1. Install Prerequisites

**Python:**
```powershell
# Download from https://www.python.org/downloads/
# ✅ Check "Add Python to PATH" during installation
python --version
```

**Node.js:**
```powershell
# Download from https://nodejs.org/
# Install LTS version
node --version
npm --version
```

**MySQL:**
```powershell
# Download MySQL Installer from https://dev.mysql.com/downloads/installer/
# Choose "Developer Default" installation
# Set root password during installation
```

#### 2. Clone Repository

```powershell
git clone https://github.com/yourusername/license-tracker.git
cd license-tracker
```

#### 3. Run Setup Script

```powershell
setup.bat
```

The script will:
- Create Python virtual environment
- Install all dependencies
- Create database tables
- Setup default admin user

---

### macOS Installation

#### 1. Install Prerequisites

**Homebrew (if not installed):**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Python:**
```bash
brew install python@3.11
python3 --version
```

**Node.js:**
```bash
brew install node
node --version
npm --version
```

**MySQL:**
```bash
brew install mysql
brew services start mysql
mysql_secure_installation
```

#### 2. Clone Repository

```bash
git clone https://github.com/yourusername/license-tracker.git
cd license-tracker
```

#### 3. Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

---

### Linux Installation (Ubuntu/Debian)

#### 1. Install Prerequisites

```bash
# Update package list
sudo apt update

# Install Python
sudo apt install python3 python3-pip python3-venv

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install MySQL
sudo apt install mysql-server
sudo mysql_secure_installation
```

#### 2. Clone Repository

```bash
git clone https://github.com/yourusername/license-tracker.git
cd license-tracker
```

#### 3. Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

---

## 🗄️ Database Setup (All Platforms)

### Create Database

**Using MySQL Client:**
```bash
mysql -u root -p
```

**Run these SQL commands:**
```sql
-- Create database
CREATE DATABASE license_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'license_user'@'localhost' IDENTIFIED BY 'YourSecurePassword123!';

-- Grant privileges
GRANT ALL PRIVILEGES ON license_tracker.* TO 'license_user'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Exit
EXIT;
```

### Alternative: Using MySQL Workbench

1. Open MySQL Workbench
2. Connect to your MySQL server
3. Click "Create new schema" (database icon)
4. Name: `license_tracker`
5. Charset: `utf8mb4`
6. Collation: `utf8mb4_unicode_ci`
7. Click "Apply"

---
## sample data
run the sample_data.py file for loading sample data
## ⚙️ Manual Installation (If Scripts Fail)

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env file with your settings
# Update DATABASE_URL with your MySQL credentials

# Initialize database
python init_db.py

# Start server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Open new terminal
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Start development server
npm start
```

---

## 🔐 Environment Configuration

### Backend (.env)

Create `backend/.env` from template:

```env
DATABASE_URL=mysql+pymysql://license_user:YourPassword@localhost:3306/license_tracker
JWT_SECRET_KEY=your-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
OPENAI_API_KEY=sk-your-key-here  # Optional
ENVIRONMENT=development
```

**Generate secure JWT secret:**
```bash
# Unix/macOS:
openssl rand -hex 32

# Windows (PowerShell):
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

### Frontend (.env)

Create `frontend/.env` from template:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_ENV=development
```

---

## 🌱 Load Sample Data (Optional)

```bash
cd scripts
python sample_data.py
```

This creates:
- 3 test users (Admin, Engineer, Auditor)
- 5 vendors
- 10 devices
- 5 licenses
- Sample assignments
- Software version tracking data

**Test credentials:**
- Admin: `admin@licensetracker.com` / `Admin@123`
- Engineer: `engineer@licensetracker.com` / `Engineer@123`
- Auditor: `auditor@licensetracker.com` / `Auditor@123`

---

## 🚀 Starting the Application

### Start Backend

```bash
cd backend

# Activate virtual environment first
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Start server
uvicorn server:app --reload
```

**Backend will be available at:** `http://localhost:8000`

**API Docs:** `http://localhost:8000/docs`

### Start Frontend

```bash
# In new terminal
cd frontend

npm start
```

**Frontend will be available at:** `http://localhost:3000`

---

## ✅ Verification

### Check Backend

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Check Frontend

Open browser: `http://localhost:3000`

You should see the login page.

---

## 🔧 Troubleshooting

### Backend Issues

**Problem:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
cd backend
pip install -r requirements.txt
```

---

**Problem:** `Can't connect to MySQL server`

**Solution:**
1. Check MySQL is running:
   ```bash
   # Windows
   net start MySQL80
   
   # macOS
   brew services start mysql
   
   # Linux
   sudo systemctl start mysql
   ```

2. Verify credentials in `backend/.env`

3. Test connection:
   ```bash
   mysql -u license_user -p license_tracker
   ```

---

**Problem:** `Database 'license_tracker' doesn't exist`

**Solution:**
```bash
mysql -u root -p -e "CREATE DATABASE license_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

---

### Frontend Issues

**Problem:** `npm ERR! code ENOENT`

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

**Problem:** `Network Error` when logging in

**Solution:**
1. Check backend is running on port 8000
2. Verify `REACT_APP_BACKEND_URL` in `frontend/.env`
3. Check browser console for CORS errors

---

**Problem:** CORS error in browser

**Solution:**
Update `backend/.env`:
```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Restart backend server.

---

### Database Issues

**Problem:** `Access denied for user`

**Solution:**
```sql
-- Reset user permissions
DROP USER IF EXISTS 'license_user'@'localhost';
CREATE USER 'license_user'@'localhost' IDENTIFIED BY 'NewPassword123!';
GRANT ALL PRIVILEGES ON license_tracker.* TO 'license_user'@'localhost';
FLUSH PRIVILEGES;
```

Update `DATABASE_URL` in `backend/.env`.

---

**Problem:** Tables not created

**Solution:**
```bash
cd backend
python init_db.py
```

---

## 🐳 Docker Installation (Alternative)

### Using Docker Compose

```bash
# Make sure Docker is installed
docker --version
docker-compose --version

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

**Containers:**
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- MySQL: `localhost:3306`

---

## 📱 Production Deployment

### Build Frontend

```bash
cd frontend
npm run build
```

### Configure Production Backend

Update `backend/.env`:
```env
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://yourdomain.com
```

### Use Production Server

```bash
cd backend
pip install gunicorn
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

## 🔒 Security Checklist

Before deploying to production:

- [ ] Change default admin password
- [ ] Generate new JWT secret key
- [ ] Update CORS_ORIGINS with actual domain
- [ ] Use strong database password
- [ ] Enable HTTPS/SSL
- [ ] Set ENVIRONMENT=production
- [ ] Review all .env files
- [ ] Never commit .env to Git

---

## 📞 Getting Help

If you encounter issues:

1. Check this guide's Troubleshooting section
2. Review backend logs
3. Check browser console (F12)
4. Search existing GitHub issues
5. Create new GitHub issue with:
   - Error message
   - Platform (Windows/Mac/Linux)
   - Python/Node versions
   - Steps to reproduce

---

## ✅ Installation Complete!

You should now have:
- ✅ MySQL database created and configured
- ✅ Backend API running on port 8000
- ✅ Frontend application running on port 3000
- ✅ Default admin user created
- ✅ Ready to start using License Tracker!

**Next Steps:**
1. Login with admin credentials
2. Change default password
3. Add your first device
4. Create your first license
5. Explore the features!

---

**Happy Tracking! 🎉**