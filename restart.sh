#!/bin/bash

echo "🔄 Stopping all Python & server processes..."
pkill -u $USER -f python 2>/dev/null
pkill -u $USER -f passenger 2>/dev/null
pkill -u $USER -f gunicorn 2>/dev/null

echo "🧹 Removing __pycache__ folders..."
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "🧹 Clearing pip cache..."
pip cache purge -q 2>/dev/null
rm -rf ~/.cache/pip 2>/dev/null

echo "🧹 Clearing temp files..."
rm -rf tmp/* 2>/dev/null

echo "🚀 Forcing full Passenger restart..."
mkdir -p tmp
touch tmp/restart.txt

echo "⚙️ Reloading virtual environment..."
deactivate 2>/dev/null
source /home/garmabs2/virtualenv/myapp/3.11/bin/activate

echo "✅ Full Reset Complete — Application will restart fresh!"
