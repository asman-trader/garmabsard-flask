#!/bin/bash

echo "🔄 Stopping Python processes..."
pkill -u $USER -f python

echo "🧹 Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "🧹 Clearing pip cache..."
rm -rf ~/.cache/pip 2>/dev/null

echo "🚀 Restarting application..."
touch passenger_wsgi.py

echo "✅ Done! Application restarted successfully."
