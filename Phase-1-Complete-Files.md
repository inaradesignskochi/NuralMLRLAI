# Complete Phase 1 Implementation Files

## File 1: backend/app.py (Flask API Server)

```python
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
from datetime import datetime
import pandas as pd

from config import get_config, update_environment, RISK_PARAMS, TRADING_PARAMS, ENVIRONMENT_MODE
from delta_exchange_client import DeltaExchangeClient
from smc_strategy import SMCStrategy

app = Flask(__name__)
CORS(app)

# Initialize components
delta_client = DeltaExchangeClient()
smc_strategy = SMCStrategy(RISK_PARAMS)

# Global bot state
bot_state = {
    'running': False,
    'environment': ENVIRONMENT_MODE,
    'account_balance': 10000.0,
    'open_trades': [],
    'closed_trades': [],
    'total_pnl': 0.0,
    'win_count': 0,
    'loss_count': 0,
    'last_update': datetime.now().isoformat()
}

# Trading loop control
trading_thread = None
stop_trading = threading.Event()

def trading_loop():
    """Main trading loop - runs in background"""
    print("Trading loop started")
    
    while not stop_trading.is_set():
        if not bot_state['running']:
            time.sleep(5)
            continue
        
        try:
            # Limit concurrent trades
            if len(bot_state['open_trades']) >= RISK_PARAMS['max_open_trades']:
                time.sleep(30)
                continue
            
            # Fetch wallet balance
            wallet = delta_client.get_wallet_balance()
            if wallet and 'result' in wallet:
                bot_state['account_balance'] = float(wallet['result'][0]['balance'])
            
            # Analyze each symbol
            for symbol in TRADING_PARAMS['symbols']:
                try:
                    # Fetch candle data
                    candles = delta_client.fetch_candles(
                        symbol,
                        resolution=TRADING_PARAMS['timeframe'].replace('m', ''),
                        limit=200
                    )
                    
                    if not candles:
                        continue
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    df = df.astype({'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
                    
                    # Generate signal
                    signal = smc_strategy.generate_signal(df, symbol)
                    
                    if not signal or signal['confidence'] < 0.65:
                        continue
                    
                    # Calculate position
                    position = smc_strategy.calculate_position(signal, bot_state['account_balance'])
                    
                    if not position:
                        continue
                    
                    # Get product ID
                    product_id = delta_client.get_product_id(symbol)
                    if not product_id:
                        continue
                    
                    # Place order
                    order_result = delta_client.place_order(
                        product_id=product_id,
                        side=position['side'],
                        size=position['position_size'],
                        order_type='market_order'
                    )
                    
                    if order_result and 'result' in order_result:
                        trade = {
                            'id': order_result['result']['id'],
                            'symbol': symbol,
                            'side': position['side'].upper(),
                            'entry': position['entry_price'],
                            'size': position['position_size'],
                            'stop_loss': position['stop_loss'],
                            'take_profit': position['take_profit'],
                            'risk': position['risk_amount'],
                            'potential_profit': position['potential_profit'],
                            'pnl': 0.0,
                            'status': 'OPEN',
                            'opened_at': datetime.now().isoformat()
                        }
                        
                        bot_state['open_trades'].append(trade)
                        print(f"✅ Opened {trade['side']} trade on {symbol}")
                
                except Exception as e:
                    print(f"Error processing {symbol}: {e}")
            
            # Update open trades
            update_open_trades()
            
        except Exception as e:
            print(f"Error in trading loop: {e}")
        
        time.sleep(60)  # Wait 1 minute before next iteration

def update_open_trades():
    """Update status and PnL of open trades"""
    positions = delta_client.get_positions()
    
    if not positions or 'result' not in positions:
        return
    
    for trade in bot_state['open_trades'][:]:
        try:
            # Find matching position
            matching_pos = None
            for pos in positions['result']:
                if pos['product_symbol'] == trade['symbol']:
                    matching_pos = pos
                    break
            
            if matching_pos:
                # Update PnL
                trade['pnl'] = float(matching_pos.get('realized_pnl', 0))
                
                # Check if closed
                if float(matching_pos.get('size', 0)) == 0:
                    trade['status'] = 'CLOSED'
                    trade['closed_at'] = datetime.now().isoformat()
                    
                    bot_state['open_trades'].remove(trade)
                    bot_state['closed_trades'].append(trade)
                    bot_state['total_pnl'] += trade['pnl']
                    
                    if trade['pnl'] > 0:
                        bot_state['win_count'] += 1
                    else:
                        bot_state['loss_count'] += 1
                    
                    print(f"✅ Closed trade on {trade['symbol']}: PnL = ${trade['pnl']:.2f}")
        
        except Exception as e:
            print(f"Error updating trade: {e}")

# API Routes

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get bot status"""
    total_trades = bot_state['win_count'] + bot_state['loss_count']
    win_rate = (bot_state['win_count'] / total_trades) if total_trades > 0 else 0.0
    
    return jsonify({
        'running': bot_state['running'],
        'environment': bot_state['environment'],
        'account_balance': bot_state['account_balance'],
        'open_trades': len(bot_state['open_trades']),
        'total_trades': total_trades,
        'total_pnl': bot_state['total_pnl'],
        'win_rate': win_rate,
        'last_update': datetime.now().isoformat()
    })

@app.route('/api/control/start', methods=['POST'])
def start_bot():
    """Start trading bot"""
    bot_state['running'] = True
    return jsonify({'status': 'Bot started', 'running': True})

@app.route('/api/control/stop', methods=['POST'])
def stop_bot():
    """Stop trading bot"""
    bot_state['running'] = False
    return jsonify({'status': 'Bot stopped', 'running': False})

@app.route('/api/control/environment', methods=['POST'])
def switch_environment():
    """Switch between testnet and live"""
    data = request.json
    env = data.get('environment', 'testnet')
    
    if update_environment(env):
        bot_state['environment'] = env
        # Reinitialize client with new environment
        global delta_client
        delta_client = DeltaExchangeClient()
        return jsonify({'environment': env, 'status': 'Environment switched'})
    
    return jsonify({'error': 'Invalid environment'}), 400

@app.route('/api/trades', methods=['GET'])
def get_trades():
    """Get all trades"""
    return jsonify({
        'open_trades': bot_state['open_trades'],
        'closed_trades': bot_state['closed_trades'][-50:]  # Last 50
    })

@app.route('/api/trades/close/<trade_id>', methods=['POST'])
def close_trade(trade_id):
    """Manually close a trade"""
    for trade in bot_state['open_trades']:
        if str(trade['id']) == trade_id:
            try:
                product_id = delta_client.get_product_id(trade['symbol'])
                # Place opposite order to close
                opposite_side = 'sell' if trade['side'] == 'BUY' else 'buy'
                
                result = delta_client.place_order(
                    product_id=product_id,
                    side=opposite_side,
                    size=trade['size'],
                    order_type='market_order'
                )
                
                if result:
                    return jsonify({'status': 'Trade closed', 'trade_id': trade_id})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Trade not found'}), 404

@app.route('/api/parameters', methods=['GET'])
def get_parameters():
    """Get trading parameters"""
    return jsonify({
        'risk': RISK_PARAMS,
        'trading': TRADING_PARAMS
    })

@app.route('/api/parameters', methods=['POST'])
def update_parameters():
    """Update trading parameters"""
    data = request.json
    
    if 'risk' in data:
        RISK_PARAMS.update(data['risk'])
    
    if 'trading' in data:
        TRADING_PARAMS.update(data['trading'])
    
    return jsonify({
        'status': 'Parameters updated',
        'risk': RISK_PARAMS,
        'trading': TRADING_PARAMS
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # Start trading loop in background
    trading_thread = threading.Thread(target=trading_loop, daemon=True)
    trading_thread.start()
    
    # Start Flask app
    print("🚀 SMC Trading Bot starting...")
    print(f"📊 Environment: {ENVIRONMENT_MODE}")
    print(f"🔧 Trading symbols: {TRADING_PARAMS['symbols']}")
    app.run(host='0.0.0.0', port=5000, debug=False)
```

---

## File 2: backend/Dockerfile

```dockerfile
FROM python:3.11-slim

LABEL maintainer="smc-bot@trading.com"
LABEL description="SMC Trading Bot Backend"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for models
RUN mkdir -p /app/models

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')"

# Run application
CMD ["python", "app.py"]
```

---

## File 3: frontend/Dockerfile

```dockerfile
FROM nginx:alpine

LABEL maintainer="smc-bot@trading.com"
LABEL description="SMC Trading Bot Frontend"

# Copy frontend files
COPY index.html /usr/share/nginx/html/
COPY static /usr/share/nginx/html/static

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## File 4: frontend/nginx.conf

```nginx
server {
    listen 80;
    server_name localhost;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # Enable gzip compression
    gzip on;
    gzip_types text/css application/javascript application/json;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## File 5: docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: smc-bot-backend
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - ENVIRONMENT_MODE=${ENVIRONMENT_MODE:-testnet}
      - DELTA_TESTNET_API_KEY=${DELTA_TESTNET_API_KEY}
      - DELTA_TESTNET_SECRET=${DELTA_TESTNET_SECRET}
      - DELTA_LIVE_API_KEY=${DELTA_LIVE_API_KEY:-}
      - DELTA_LIVE_SECRET=${DELTA_LIVE_SECRET:-}
    volumes:
      - ./backend:/app
      - ./models:/app/models
      - bot-logs:/app/logs
    networks:
      - smc-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: smc-bot-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - smc-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  bot-logs:
    driver: local

networks:
  smc-network:
    driver: bridge
```

---

## File 6: .env.example

```bash
# Environment Configuration
ENVIRONMENT_MODE=testnet

# Delta Exchange Testnet Credentials
DELTA_TESTNET_API_KEY=your_testnet_api_key_here
DELTA_TESTNET_SECRET=your_testnet_secret_here

# Delta Exchange Live Credentials (leave empty for testnet only)
DELTA_LIVE_API_KEY=
DELTA_LIVE_SECRET=

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=0

# Logging
LOG_LEVEL=INFO
```

---

## File 7: .gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.env.local

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Docker
docker-compose.override.yml

# Models
models/*.h5
models/*.pkl

# Data
data/
*.csv
*.db
```

---

## File 8: README.md

```markdown
# SMC Trading Bot - Smart Money Concepts Automated Trading

Automated trading bot using Smart Money Concepts (Order Blocks, CHoCH, Engulfing patterns) for Delta Exchange.

## Features

- ✅ Smart Money Concepts (SMC) detection
- ✅ Order Block identification
- ✅ Change of Character (CHoCH) detection
- ✅ Engulfing candlestick patterns
- ✅ Automated trade execution
- ✅ Risk management
- ✅ Real-time dashboard
- ✅ Testnet/Live environment switching
- ✅ ETH and BTC trading support

## Prerequisites

- Docker Desktop 20.10+
- Docker Compose 2.0+
- Delta Exchange account (testnet or live)

## Quick Start

### 1. Clone Repository

\`\`\`bash
git clone https://github.com/yourusername/smc-trading-bot.git
cd smc-trading-bot
\`\`\`

### 2. Configure Environment

\`\`\`bash
cp .env.example .env
# Edit .env and add your Delta Exchange API credentials
\`\`\`

### 3. Build and Run

\`\`\`bash
docker-compose build
docker-compose up -d
\`\`\`

### 4. Access Dashboard

Open http://localhost:3000 in your browser.

## Usage

### Start/Stop Bot

Use the dashboard controls or API:

\`\`\`bash
# Start bot
curl -X POST http://localhost:5000/api/control/start

# Stop bot
curl -X POST http://localhost:5000/api/control/stop
\`\`\`

### Switch Environment

\`\`\`bash
# Switch to testnet
curl -X POST http://localhost:5000/api/control/environment \
  -H "Content-Type: application/json" \
  -d '{"environment": "testnet"}'

# Switch to live (be careful!)
curl -X POST http://localhost:5000/api/control/environment \
  -H "Content-Type: application/json" \
  -d '{"environment": "live"}'
\`\`\`

### View Logs

\`\`\`bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
docker-compose logs -f frontend
\`\`\`

## Configuration

Edit \`backend/config.py\` to adjust:

- Risk parameters
- Trading symbols
- SMC detection sensitivity
- Position sizing

## API Endpoints

- \`GET /api/status\` - Bot status
- \`POST /api/control/start\` - Start bot
- \`POST /api/control/stop\` - Stop bot
- \`POST /api/control/environment\` - Switch environment
- \`GET /api/trades\` - Get trades
- \`GET /api/parameters\` - Get parameters
- \`POST /api/parameters\` - Update parameters

## Troubleshooting

### Bot not starting

Check logs: \`docker-compose logs backend\`

### API connection errors

Verify API credentials in \`.env\` file

### Dashboard not loading

Check if backend is running: \`curl http://localhost:5000/api/health\`

## Safety

- **Always start with testnet**
- Test thoroughly before live trading
- Use proper risk management
- Monitor bot regularly
- Never share API keys

## Support

For issues, contact: support@example.com

## License

MIT License - see LICENSE file
```

---

## Deployment Steps

### Step 1: Setup Project

\`\`\`bash
mkdir smc-trading-bot
cd smc-trading-bot

# Create all directories
mkdir -p backend frontend models deployment .github/workflows
mkdir -p frontend/static/css frontend/static/js
\`\`\`

### Step 2: Add All Files

Copy all the files above into their respective directories.

### Step 3: Get Delta Exchange API Keys

1. Go to https://testnet.delta.exchange
2. Sign up / Log in
3. Navigate to Settings > API
4. Create new API key
5. Save Key and Secret securely

### Step 4: Configure Environment

\`\`\`bash
cp .env.example .env
nano .env  # Add your API credentials
\`\`\`

### Step 5: Build and Start

\`\`\`bash
# Build containers
docker-compose build

# Start containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
\`\`\`

### Step 6: Access Dashboard

Open browser: http://localhost:3000

### Step 7: Test Bot

1. Click "Start Bot" in dashboard
2. Monitor trades in real-time
3. Check logs for any errors

---

## Next Steps

After successful Phase 1 deployment:
- Proceed to Phase 2 (Oracle Cloud VPS deployment)
- Add monitoring and alerts
- Integrate Phase 3 (RL/AI enhancement)
