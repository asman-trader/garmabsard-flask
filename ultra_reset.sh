#!/bin/bash

echo "❗ ULTRA RESET MODE — EVERYTHING WILL BE DESTROYED ❗"

PROJECT_PATH="/home/garmabs2/myapp"
VENV_PATH="/home/garmabs2/virtualenv/myapp/3.11"

echo "🔄 Killing all related processes..."
pkill -u $USER -f python 2>/dev/null
pkill -u $USER -f passenger 2>/dev/null
pkill -u $USER -f gunicorn 2>/dev/null

echo "🗑 Removing ALL Python caches..."
find $PROJECT_PATH -type d -name "__pycache__" -exec rm -rf {} +

echo "🗑 Removing all hidden cache files..."
find $PROJECT_PATH -type f -name "*.pyc" -delete

echo "🗑 Removing pip cache..."
rm -rf ~/.cache/pip 2>/dev/null

echo "🗑 Removing SQLite and JSON data..."
rm -f $PROJECT_PATH/*.db
rm -rf $PROJECT_PATH/app/data/*
rm -rf $PROJECT_PATH/data/*

echo "🗑 Removing uploads..."
rm -rf $PROJECT_PATH/app/data/uploads/*

echo "🗑 Removing all migration folders..."
rm -rf $PROJECT_PATH/migrations

echo "🗑 Removing tmp folders..."
rm -rf $PROJECT_PATH/tmp
mkdir -p $PROJECT_PATH/tmp

echo "🗑 Removing log files..."
find $PROJECT_PATH -type f -name "*.log" -delete

echo "🧨 Removing and recreating VIRTUALENV..."
rm -rf $VENV_PATH
python3.11 -m venv $VENV_PATH

echo "📌 Activating fresh virtualenv..."
source $VENV_PATH/bin/activate

echo "📦 Reinstalling requirements if exists..."
if [ -f "$PROJECT_PATH/requirements.txt" ]; then
    pip install -r $PROJECT_PATH/requirements.txt
else
    echo "⚠️ No requirements.txt found."
fi

echo "🚀 Forcing HARD Passenger reload..."
mkdir -p $PROJECT_PATH/tmp
touch $PROJECT_PATH/tmp/restart.txt

echo "🎉 ULTRA RESET COMPLETE — PROJECT IS NOW 100% FRESH!"
