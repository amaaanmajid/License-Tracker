@echo off
REM ========================================
REM LICENSE TRACKER - WINDOWS SETUP SCRIPT
REM ========================================

echo.
echo ========================================
echo    LICENSE TRACKER - SETUP
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 16+ from https://nodejs.org
    pause
    exit /b 1
)

REM Check if MySQL is accessible
mysql --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] MySQL client not found in PATH
    echo Please ensure MySQL server is installed and running
)

echo [1/6] Setting up Backend...
echo.

cd backend

REM Create virtual environment
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo [ACTION REQUIRED] Please edit backend\.env with your database credentials!
    echo.
)

echo.
echo [2/6] Initializing Database...
echo.

REM Initialize database
python init_db.py

if errorlevel 1 (
    echo.
    echo [ERROR] Database initialization failed!
    echo Please check:
    echo   1. MySQL is running
    echo   2. Database 'license_tracker' exists
    echo   3. Credentials in .env are correct
    pause
    exit /b 1
)

cd ..

echo.
echo [3/6] Setting up Frontend...
echo.

cd frontend

REM Install Node dependencies
echo Installing Node.js dependencies...
call npm install

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
)

cd ..

echo.
echo ========================================
echo    SETUP COMPLETE!
echo ========================================
echo.
echo Default Admin Credentials:
echo   Email: admin@licensetracker.com
echo   Password: Admin@123
echo.
echo IMPORTANT: Change the password after first login!
echo.
echo To start the application:
echo   1. Backend:  cd backend ^&^& venv\Scripts\activate ^&^& uvicorn server:app --reload
echo   2. Frontend: cd frontend ^&^& npm start
echo.
echo Access the application at: http://localhost:3000
echo.
pause