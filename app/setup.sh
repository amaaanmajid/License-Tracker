#!/bin/bash

# ========================================
# LICENSE TRACKER - UNIX/LINUX/MAC SETUP
# ========================================

set -e  # Exit on error

echo ""
echo "========================================"
echo "   LICENSE TRACKER - SETUP"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Python 3 is not installed"
    echo "Please install Python 3.9+ from https://python.org"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Node.js is not installed"
    echo "Please install Node.js 16+ from https://nodejs.org"
    exit 1
fi

# Check if MySQL is accessible
if ! command -v mysql &> /dev/null; then
    echo -e "${YELLOW}[WARNING]${NC} MySQL client not found in PATH"
    echo "Please ensure MySQL server is installed and running"
fi

echo -e "${GREEN}[1/6]${NC} Setting up Backend..."
echo ""

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}[ACTION REQUIRED]${NC} Please edit backend/.env with your database credentials!"
    echo ""
fi

echo ""
echo -e "${GREEN}[2/6]${NC} Initializing Database..."
echo ""

# Initialize database
python init_db.py

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}[ERROR]${NC} Database initialization failed!"
    echo "Please check:"
    echo "  1. MySQL is running"
    echo "  2. Database 'license_tracker' exists"
    echo "  3. Credentials in .env are correct"
    exit 1
fi

cd ..

echo ""
echo -e "${GREEN}[3/6]${NC} Setting up Frontend..."
echo ""

cd frontend

# Install Node dependencies
echo "Installing Node.js dependencies..."
npm install

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

cd ..

echo ""
echo "========================================"
echo "   SETUP COMPLETE!"
echo "========================================"
echo ""
echo -e "${GREEN}Default Admin Credentials:${NC}"
echo "  Email: admin@licensetracker.com"
echo "  Password: Admin@123"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC} Change the password after first login!"
echo ""
echo "To start the application:"
echo ""
echo "  1. Backend:"
echo "     cd backend"
echo "     source venv/bin/activate"
echo "     uvicorn server:app --reload"
echo ""
echo "  2. Frontend (in new terminal):"
echo "     cd frontend"
echo "     npm start"
echo ""
echo "Access the application at: http://localhost:3000"
echo ""