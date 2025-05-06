#!/bin/bash

# Exit immediately if any command fails
set -e

echo "🚀 Setting up the project..."

# echo "Installing sshpass"
# apt-get install -y sshpass
# echo "successfully installed sshpass"

# if [[ -z "$SSH_PASSWORD" ]]; then
#     echo "❌ SSH_PASSWORD is not set!"
#     exit 1
# fi

# Verify Java installation
if ! command -v java &> /dev/null
then
    echo "❌ Java not found! Please check the installation."
    exit 1
fi

# Set JAVA_HOME environment variable
export JAVA_HOME="$(dirname $(dirname $(readlink -f $(which java))))"
export PATH="$JAVA_HOME/bin:$PATH"
echo "✅ JAVA_HOME set to $JAVA_HOME"

# Upgrade pip and install dependencies
echo "📦 Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# echo "🚀 Connecting to the server via SSH..."
# sshpass -p "$SSH_PASSWORD" ssh "$SSH_USER@$SSH_HOST"
# echo "✅ Connected to remote server"

# Health check for TorchServe
echo "🔍 Checking TorchServe health..."
TORCHSERVE_HEALTH_URL="http://10.90.128.83:8080/ping"
for i in {1..10}; do
    if curl -s $TORCHSERVE_HEALTH_URL | grep -q "Healthy"; then
        echo "✅ TorchServe is up and running!"
        break
    fi
    echo "⏳ Waiting for TorchServe to start..."
    sleep 3
done

# Go back to the project root and start FastAPI
echo "🚀 Starting FastAPI server..."
python main.py &

# Wait for FastAPI to start
sleep 5

# Health check for FastAPI
echo "🔍 Checking FastAPI health..."
FASTAPI_HEALTH_URL="https://aimloi.dailyhunt.in/ping"
for i in {1..10}; do
    if curl -s $FASTAPI_HEALTH_URL | grep -q "Healthy"; then
        echo "✅ FastAPI is up and running!"
        break
    fi
    echo "⏳ Waiting for FastAPI to start..."
    sleep 3
done

echo "🚀 All services are up and running!"
wait
