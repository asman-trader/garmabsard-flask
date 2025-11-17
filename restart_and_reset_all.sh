#!/bin/bash

echo "❗ FULL RESET MODE — ALL DATA WILL BE REMOVED ❗"

echo "🔄 Stopping all Python & server processes..."
pkill -u $USER -f python 2>/dev/null
pkill -u $USER -f passenger 2>/dev/null
pkill -u $USER -f gunicorn 2>/dev/null

echo "🧹 Removing __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "🧹 Clearing pip cache..."
pip cache purge -q 2>/dev/null
rm -rf ~/.cache/pip 2>/dev/null

echo "🗄 Removing application data & temp..."
rm -rf tmp/* 2>/dev/null
mkdir -p tmp

echo "🗑 Removing SQLite databases..."
rm -f *.db 2>/dev/null
rm -f database.db 2>/dev/null
rm -f app.db 2>/dev/null

echo "🗑 Removing data folders (uploads, json data)..."
rm -rf app/data/* 2>/dev/null
rm -rf data/* 2>/dev/null

echo "🗑 Removing migrations..."
rm -rf migrations 2>/dev/null

echo "📦 Recreating clean folder structure..."
mkdir -p app/data/uploads
mkdir -p data

echo "🚀 Forcing full Passenger restart..."
touch tmp/restart.txt

echo "📌 Reloading virtual environment..."
deactivate 2>/dev/null
source /home/garmabs2/virtualenv/myapp/3.11/bin/activate

echo "🎉 FULL RESET COMPLETE — PROJECT IS NOW FRESH & CLEAN!"
