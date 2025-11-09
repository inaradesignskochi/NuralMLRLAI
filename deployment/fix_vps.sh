#!/bin/bash

# SMC Trading Bot - VPS Fix Script
# Run this to fix remaining issues on Oracle Cloud VPS

set -e

echo "🔧 Fixing SMC Trading Bot VPS issues..."

# Install nano editor
echo "📝 Installing nano editor..."
sudo apt-get install -y nano

# Copy systemd service file
echo "⚙️  Setting up systemd service..."
sudo cp /opt/smc-bot/deployment/smc-bot.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start service
echo "🚀 Starting systemd service..."
sudo systemctl enable smc-bot.service
sudo systemctl start smc-bot.service

# Wait a moment for containers to start
echo "⏳ Waiting for containers to start..."
sleep 10

# Check status
echo "📊 Checking service status..."
sudo systemctl status smc-bot.service --no-pager

echo "🐳 Checking Docker containers..."
docker-compose ps

echo "🏥 Checking API health..."
curl -s http://localhost:5000/api/health || echo "API not ready yet"

echo "✅ VPS fixes applied!"
echo ""
echo "🌐 Access your bot:"
echo "   Dashboard: http://129.154.43.166:3000"
echo "   API: http://129.154.43.166:5000"
echo ""
echo "⚠️  Remember to add your Delta Exchange API credentials to .env file:"
echo "   nano .env"