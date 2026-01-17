#!/bin/bash

echo "🌲 STARTING VERDE SCAN SYSTEM..."

# 1. Install dependencies
echo "📦 Installing dependencies..."
python3 -m pip install -r requirements.txt --break-system-packages --user | grep -v "already satisfied"

# 2. Run AI Pipeline to generate data
echo "🤖 Running AI Processing Pipeline..."
python3 ai/processor.py

# 3. Start Backend in background
echo "🚀 Starting Backend Server at http://localhost:8000"
python3 api/main.py &
BACKEND_PID=$!

# Wait for server to start
sleep 3

# 4. Open Frontend
echo "🌐 Opening Dashboard..."
open "http://localhost:8000"

echo "✅ System is LIVE!"
echo "Press Ctrl+C to stop."

# Wait for backend
wait $BACKEND_PID
