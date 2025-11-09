#!/bin/bash

# SMC Trading Bot - Oracle Cloud VPS Setup Script
# Run this script on your Oracle Cloud VPS to set up the environment

set -e

echo "🚀 Starting SMC Trading Bot VPS Setup..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Install Docker Compose
echo "🐳 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install UFW if not present
echo "🔥 Installing UFW firewall..."
sudo apt-get install -y ufw

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw --force enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp
sudo ufw allow 3000/tcp

# Create app directory
echo "📁 Creating application directory..."
sudo mkdir -p /opt/smc-bot
sudo chown -R $USER:$USER /opt/smc-bot
cd /opt/smc-bot

# Clone repository (if not already cloned)
if [ ! -d ".git" ]; then
    echo "📥 Cloning repository..."
    git clone https://github.com/inaradesignskochi/NuralMLRLAI.git .
fi

# Configure environment
echo "⚙️  Configuring environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API credentials!"
    echo "   nano .env"
fi

# Build and start containers
echo "🏗️  Building and starting containers..."
docker-compose build
docker-compose up -d

# Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/smc-bot.service > /dev/null <<EOF
[Unit]
Description=SMC Trading Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/smc-bot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ubuntu
Group=docker

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "🚀 Enabling and starting systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable smc-bot.service
sudo systemctl start smc-bot.service

# Apply Docker group changes
echo "🔄 Applying Docker group changes..."
newgrp docker

echo "✅ SMC Trading Bot VPS setup complete!"
echo ""
echo "🌐 Access your bot at:"
echo "   Dashboard: http://$(curl -s ifconfig.me):3000"
echo "   API: http://$(curl -s ifconfig.me):5000"
echo ""
echo "🔧 To check status:"
echo "   sudo systemctl status smc-bot.service"
echo "   docker-compose ps"
echo ""
echo "📝 Remember to:"
echo "   1. Edit .env with your Delta Exchange API credentials"
echo "   2. Test the bot functionality"
echo "   3. Set up monitoring if needed"