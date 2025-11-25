#!/bin/bash
echo "❗ ULTIMATE DEPLOY — FULL RESET & REDEPLOY FROM GIT ❗"

PROJECT_DIR="/home/garmabs2/myapp"
VENV_DIR="/home/garmabs2/virtualenv/myapp/3.11"
PYTHON_BIN="/home/garmabs2/virtualenv/myapp/3.11/bin/python"
PIP_BIN="/home/garmabs2/virtualenv/myapp/3.11/bin/pip"

echo "🔄 Stopping previous processes..."
pkill -f myapp || true

echo "🗑 Cleaning Python caches..."
find $PROJECT_DIR -type d -name "__pycache__" -exec rm -rf {} +
find $PROJECT_DIR -type f -name "*.pyc" -delete
find $PROJECT_DIR -type f -name "*.pyo" -delete

echo "🗑 Removing local data (SQLite, JSON, uploads)..."
rm -rf $PROJECT_DIR/app.db
rm -rf $PROJECT_DIR/app/data/*.json
rm -rf $PROJECT_DIR/app/data/uploads/*

echo "🗑 Removing migration folders..."
rm -rf $PROJECT_DIR/migrations

echo "🗑 Removing logs..."
rm -rf $PROJECT_DIR/logs/*

echo "🧨 Removing old Virtualenv..."
rm -rf $VENV_DIR

echo "📌 Creating NEW Virtualenv (Python 3.11)..."
python3.11 -m venv $VENV_DIR

echo "📌 Activating Virtualenv..."
source $VENV_DIR/bin/activate

echo "📦 Pulling NEW VERSION from GitHub..."
cd $PROJECT_DIR
git reset --hard
git pull origin main

echo "📦 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🚀 Restarting Passenger..."
touch $PROJECT_DIR/tmp/restart.txt

echo "🎉 DEPLOY FINISHED — PROJECT IS LIVE!"
