# Enhanced Smart Money Concepts (SMC) Trading Bot - Complete 3-Phase Implementation Plan

## Overview
A fully automated SMC trading bot with ML/AI for Delta Exchange ETH and BTC trading, progressing through three phases: Local Docker, Oracle Cloud VPS, and Reinforcement Learning integration. All services use free-tier options.

---

## Phase 1: Local Docker Container Setup

### Objectives
- Run the entire bot stack locally in Docker containers
- Integrate the provided dashboard for monitoring
- Connect to Delta Exchange testnet
- Validate SMC logic and ML model inference

### Architecture Components

#### 1.1 Project Structure
```
smc-trading-bot/
├── backend/
│   ├── app.py                    # Flask API server
│   ├── config.py                 # Configuration management
│   ├── delta_exchange_client.py   # Delta Exchange API client
│   ├── smc_strategy.py           # SMC trading logic
│   ├── ml_model.py               # ML inference engine
│   ├── risk_manager.py           # Risk and position management
│   ├── requirements.txt          # Python dependencies
│   └── Dockerfile                # Backend container
├── frontend/
│   ├── index.html                # Enhanced dashboard
│   ├── static/
│   │   ├── styles.css
│   │   └── app.js
│   └── Dockerfile                # Frontend container
├── models/
│   ├── smc_model.h5              # Pre-trained ML model
│   └── training_data/            # Historical data for training
├── docker-compose.yml            # Multi-container orchestration
└── README.md

```

#### 1.2 Backend Components

**requirements.txt:**
```
Flask==2.3.0
Flask-CORS==4.0.0
requests==2.31.0
websocket-client==1.6.0
pandas==2.0.0
numpy==1.24.0
scikit-learn==1.3.0
tensorflow==2.13.0
python-dotenv==1.0.0
PyYAML==6.0
schedule==1.2.0
```

**backend/config.py:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT_MODE = os.getenv('ENVIRONMENT_MODE', 'testnet')

CONFIG = {
    'testnet': {
        'delta_api_url': 'https://testnet-api.delta.exchange',
        'delta_ws_url': 'wss://testnet-stream.delta.exchange/ws',
        'api_key': os.getenv('DELTA_TESTNET_API_KEY'),
        'api_secret': os.getenv('DELTA_TESTNET_SECRET'),
    },
    'live': {
        'delta_api_url': 'https://api.delta.exchange',
        'delta_ws_url': 'wss://stream.delta.exchange/ws',
        'api_key': os.getenv('DELTA_LIVE_API_KEY'),
        'api_secret': os.getenv('DELTA_LIVE_SECRET'),
    }
}

# Risk Management
RISK_PARAMS = {
    'max_risk_per_trade': 0.01,     # 1% per trade
    'max_position_size': 0.05,      # 5% of account
    'reward_risk_ratio': 2.0,
    'max_drawdown': 0.15,           # 15% max drawdown
}

# Trading Parameters
TRADING_PARAMS = {
    'symbols': ['BTC', 'ETH'],
    'timeframe': '15m',
    'order_block_lookback': 50,
    'choch_sensitivity': 0.002,
}

def get_config():
    return CONFIG[ENVIRONMENT_MODE]
```

**backend/delta_exchange_client.py:**
```python
import requests
import websocket
import json
import hmac
import hashlib
from datetime import datetime
import asyncio
from config import get_config

class DeltaExchangeClient:
    def __init__(self):
        self.config = get_config()
        self.base_url = self.config['delta_api_url']
        self.ws_url = self.config['delta_ws_url']
        self.api_key = self.config['api_key']
        self.api_secret = self.config['api_secret']
        self.session = requests.Session()

    def _sign_request(self, method, endpoint, params=None):
        """Sign request with API key and secret"""
        timestamp = str(int(datetime.now().timestamp() * 1000))
        
        if method == 'GET':
            query_string = '&'.join([f"{k}={v}" for k, v in (params or {}).items()])
            message = f"{method}{endpoint}?{query_string}{timestamp}"
        else:
            message = f"{method}{endpoint}{json.dumps(params or {})}{timestamp}"
        
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-API-KEY': self.api_key,
            'X-SIGNATURE': signature,
            'X-TIMESTAMP': timestamp,
            'Content-Type': 'application/json'
        }
        return headers

    def fetch_historical_data(self, symbol, interval='15m', limit=500):
        """Fetch historical OHLCV data"""
        endpoint = '/v2/history/candles'
        params = {
            'symbol': symbol,
            'resolution': interval,
            'limit': limit
        }
        headers = self._sign_request('GET', endpoint, params)
        
        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=headers,
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return None

    def get_account_info(self):
        """Fetch account balance and position info"""
        endpoint = '/v2/account'
        headers = self._sign_request('GET', endpoint)
        
        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return None

    def place_order(self, symbol, side, quantity, order_type='MARKET', price=None):
        """Place a new order"""
        endpoint = '/v2/orders'
        params = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'order_type': order_type,
            'product_id': 1  # Perpetual futures
        }
        
        if order_type == 'LIMIT' and price:
            params['price'] = price
        
        headers = self._sign_request('POST', endpoint, params)
        
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=params,
                headers=headers,
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    def cancel_order(self, order_id):
        """Cancel an existing order"""
        endpoint = f'/v2/orders/{order_id}'
        headers = self._sign_request('DELETE', endpoint)
        
        try:
            response = self.session.delete(
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"Error canceling order: {e}")
            return None

    def get_open_positions(self):
        """Get all open positions"""
        endpoint = '/v2/positions'
        headers = self._sign_request('GET', endpoint)
        
        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return None

    async def subscribe_to_ticker(self, symbol, callback):
        """Subscribe to real-time ticker updates via WebSocket"""
        try:
            def on_message(ws, message):
                data = json.loads(message)
                callback(data)
            
            def on_error(ws, error):
                print(f"WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                print("WebSocket closed")
            
            def on_open(ws):
                subscribe_msg = {
                    'type': 'subscribe',
                    'channel': f'{symbol}_ticker'
                }
                ws.send(json.dumps(subscribe_msg))
            
            ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            ws.run_forever()
        except Exception as e:
            print(f"Error in WebSocket subscription: {e}")
```

**backend/smc_strategy.py:**
```python
import pandas as pd
import numpy as np
from ml_model import MLModel

class SMCStrategy:
    def __init__(self, ml_model, risk_params):
        self.ml_model = ml_model
        self.risk_params = risk_params
        self.open_trades = {}

    def detect_order_blocks(self, df, lookback=50):
        """Identify order blocks (supply/demand zones)"""
        order_blocks = []
        
        for i in range(lookback, len(df)):
            # Bullish order block: strong candle followed by down move
            if (df['close'].iloc[i] > df['open'].iloc[i] and 
                df['close'].iloc[i+1] < df['open'].iloc[i+1]):
                order_blocks.append({
                    'type': 'BULLISH',
                    'high': df['high'].iloc[i],
                    'low': df['low'].iloc[i],
                    'time': df['time'].iloc[i],
                    'confirmed': False
                })
            
            # Bearish order block: strong down candle followed by up move
            if (df['close'].iloc[i] < df['open'].iloc[i] and 
                df['close'].iloc[i+1] > df['open'].iloc[i+1]):
                order_blocks.append({
                    'type': 'BEARISH',
                    'high': df['high'].iloc[i],
                    'low': df['low'].iloc[i],
                    'time': df['time'].iloc[i],
                    'confirmed': False
                })
        
        return order_blocks

    def detect_choch(self, df):
        """Detect Change of Character (market structure breaks)"""
        choch_points = []
        
        # Simple CHoCH: break of recent high or low
        for i in range(2, len(df)):
            recent_high = df['high'].iloc[max(0, i-20):i].max()
            recent_low = df['low'].iloc[max(0, i-20):i].min()
            
            if df['high'].iloc[i] > recent_high:
                choch_points.append({
                    'type': 'BULLISH_CHOCH',
                    'price': df['high'].iloc[i],
                    'time': df['time'].iloc[i]
                })
            elif df['low'].iloc[i] < recent_low:
                choch_points.append({
                    'type': 'BEARISH_CHOCH',
                    'price': df['low'].iloc[i],
                    'time': df['time'].iloc[i]
                })
        
        return choch_points

    def detect_engulfing(self, df):
        """Detect engulfing candlestick patterns"""
        engulfing_patterns = []
        
        for i in range(1, len(df)):
            prev_open = df['open'].iloc[i-1]
            prev_close = df['close'].iloc[i-1]
            curr_open = df['open'].iloc[i]
            curr_close = df['close'].iloc[i]
            
            # Bullish engulfing
            if (prev_close < prev_open and 
                curr_close > prev_open and 
                curr_open < prev_close):
                engulfing_patterns.append({
                    'type': 'BULLISH_ENGULFING',
                    'time': df['time'].iloc[i],
                    'strength': (curr_close - curr_open) / (prev_close - prev_open)
                })
            
            # Bearish engulfing
            if (prev_close > prev_open and 
                curr_close < prev_open and 
                curr_open > prev_close):
                engulfing_patterns.append({
                    'type': 'BEARISH_ENGULFING',
                    'time': df['time'].iloc[i],
                    'strength': (curr_open - curr_close) / (curr_open - prev_open)
                })
        
        return engulfing_patterns

    def generate_signal(self, df, symbol):
        """Generate trading signal combining SMC and ML"""
        # Get SMC components
        order_blocks = self.detect_order_blocks(df)
        choch = self.detect_choch(df)
        engulfing = self.detect_engulfing(df)
        
        # Get ML prediction
        ml_features = self.ml_model.preprocess(df)
        ml_signal = self.ml_model.predict(ml_features)
        
        # Combine signals
        signal = {
            'symbol': symbol,
            'ml_confidence': ml_signal,
            'order_blocks': order_blocks[-3:] if order_blocks else [],
            'choch': choch[-1] if choch else None,
            'engulfing': engulfing[-1] if engulfing else None,
            'timestamp': df['time'].iloc[-1]
        }
        
        return signal

    def calculate_position(self, signal, account_balance):
        """Calculate trade size, SL, TP"""
        if not signal or signal['ml_confidence'] < 0.6:
            return None
        
        # Position sizing
        risk_amount = account_balance * self.risk_params['max_risk_per_trade']
        
        # Use order block for SL placement
        if signal['order_blocks']:
            latest_block = signal['order_blocks'][-1]
            if signal['ml_confidence'] > 0.7:  # Strong signal
                if latest_block['type'] == 'BULLISH':
                    stop_loss = latest_block['low']
                    entry = latest_block['high']
                else:
                    stop_loss = latest_block['high']
                    entry = latest_block['low']
            else:
                return None
        else:
            return None
        
        # Calculate position size
        sl_distance = abs(entry - stop_loss)
        position_size = risk_amount / sl_distance if sl_distance > 0 else 0
        
        # Take profit
        take_profit = entry + (entry - stop_loss) * self.risk_params['reward_risk_ratio']
        
        return {
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'side': 'BUY' if signal['ml_confidence'] > 0.5 else 'SELL'
        }
```

**backend/ml_model.py:**
```python
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model as tf_load_model

class MLModel:
    def __init__(self, model_path):
        self.model = tf_load_model(model_path)

    def preprocess(self, df):
        """Convert raw OHLCV to ML features"""
        df = df.copy()
        
        # Add technical features
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        df['macd'] = self._calculate_macd(df['close'])
        df['atr'] = self._calculate_atr(df)
        
        # Normalize features
        features = df[['returns', 'volatility', 'rsi', 'macd', 'atr']].tail(30).values
        features = (features - features.mean()) / (features.std() + 1e-8)
        
        return features

    def predict(self, features):
        """Generate prediction (0-1 confidence)"""
        if features is None or len(features) == 0:
            return 0.5
        
        prediction = self.model.predict(features.reshape(1, -1, 1), verbose=0)[0][0]
        return float(prediction)

    @staticmethod
    def _calculate_rsi(prices, period=14):
        """Calculate RSI"""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100. / (1. + rs)
        
        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta
            
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            rs = up / down if down != 0 else 0
            rsi[i] = 100. - 100. / (1. + rs)
        
        return rsi

    @staticmethod
    def _calculate_macd(prices, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        return macd

    @staticmethod
    def _calculate_atr(df, period=14):
        """Calculate ATR"""
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr
```

**backend/app.py:**
```python
from flask import Flask, jsonify, request
from flask_cors import CORS
import asyncio
import threading
from config import get_config, ENVIRONMENT_MODE, RISK_PARAMS, TRADING_PARAMS
from delta_exchange_client import DeltaExchangeClient
from smc_strategy import SMCStrategy
from ml_model import MLModel
import pandas as pd

app = Flask(__name__)
CORS(app)

# Initialize clients and strategy
client = DeltaExchangeClient()
ml_model = MLModel('models/smc_model.h5')
strategy = SMCStrategy(ml_model, RISK_PARAMS)

# Global state
bot_state = {
    'running': False,
    'environment': ENVIRONMENT_MODE,
    'account_balance': 10000,
    'open_trades': [],
    'closed_trades': [],
    'pnl': 0,
    'trades_count': 0,
    'win_rate': 0.625
}

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get bot status"""
    account_info = client.get_account_info()
    return jsonify({
        'running': bot_state['running'],
        'environment': bot_state['environment'],
        'account_balance': bot_state['account_balance'],
        'open_trades': len(bot_state['open_trades']),
        'total_pnl': bot_state['pnl'],
        'win_rate': bot_state['win_rate']
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

@app.route('/api/control/switch-env', methods=['POST'])
def switch_environment():
    """Switch between testnet and live"""
    data = request.json
    env = data.get('environment', 'testnet')
    if env in ['testnet', 'live']:
        bot_state['environment'] = env
        return jsonify({'environment': env, 'status': 'Environment switched'})
    return jsonify({'error': 'Invalid environment'}), 400

@app.route('/api/trades', methods=['GET'])
def get_trades():
    """Get all trades"""
    return jsonify({
        'open_trades': bot_state['open_trades'],
        'closed_trades': bot_state['closed_trades']
    })

@app.route('/api/trades/manual', methods=['POST'])
def manual_trade():
    """Execute manual trade"""
    data = request.json
    symbol = data.get('symbol')
    side = data.get('side')
    quantity = data.get('quantity')
    
    order = client.place_order(symbol, side, quantity)
    if order:
        bot_state['open_trades'].append({
            'id': order.get('id'),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry': order.get('price'),
            'status': 'OPEN'
        })
        return jsonify({'status': 'Order placed', 'order': order})
    return jsonify({'error': 'Failed to place order'}), 400

@app.route('/api/parameters', methods=['GET'])
def get_parameters():
    """Get trading parameters"""
    return jsonify(TRADING_PARAMS)

@app.route('/api/parameters', methods=['POST'])
def update_parameters():
    """Update trading parameters"""
    data = request.json
    TRADING_PARAMS.update(data)
    return jsonify({'status': 'Parameters updated', 'parameters': TRADING_PARAMS})

def trading_loop():
    """Main trading loop (runs in background thread)"""
    while True:
        if bot_state['running']:
            try:
                for symbol in TRADING_PARAMS['symbols']:
                    # Fetch data
                    data = client.fetch_historical_data(symbol, TRADING_PARAMS['timeframe'])
                    if not data:
                        continue
                    
                    df = pd.DataFrame(data)
                    
                    # Generate signal
                    signal = strategy.generate_signal(df, symbol)
                    
                    # Calculate position
                    position = strategy.calculate_position(signal, bot_state['account_balance'])
                    
                    # Execute if signal strong enough
                    if position and signal['ml_confidence'] > 0.65:
                        order = client.place_order(
                            symbol,
                            position['side'],
                            position['position_size']
                        )
                        if order:
                            bot_state['open_trades'].append(order)
                            bot_state['trades_count'] += 1
            except Exception as e:
                print(f"Error in trading loop: {e}")
        
        asyncio.sleep(60)  # Run every minute

# Start trading loop in background thread
trading_thread = threading.Thread(target=trading_loop, daemon=True)
trading_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

**backend/Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

#### 1.3 Frontend (Enhanced Dashboard)

Use the provided dashboard HTML, enhanced with real API integration:

**frontend/app.js (excerpt for real API integration):**
```javascript
const API_BASE = 'http://localhost:5000/api';

class DashboardController {
    async fetchStatus() {
        const response = await fetch(`${API_BASE}/status`);
        return await response.json();
    }

    async fetchTrades() {
        const response = await fetch(`${API_BASE}/trades`);
        return await response.json();
    }

    async startBot() {
        const response = await fetch(`${API_BASE}/control/start`, { method: 'POST' });
        return await response.json();
    }

    async stopBot() {
        const response = await fetch(`${API_BASE}/control/stop`, { method: 'POST' });
        return await response.json();
    }

    async switchEnvironment(env) {
        const response = await fetch(`${API_BASE}/control/switch-env`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ environment: env })
        });
        return await response.json();
    }

    async updateMetrics() {
        const status = await this.fetchStatus();
        document.getElementById('bot-status-text').textContent = 
            status.running ? 'Running' : 'Stopped';
        document.getElementById('bot-status-dot').style.backgroundColor = 
            status.running ? '#22c55e' : '#ef4444';
        document.getElementById('total-pnl').textContent = 
            `$${status.total_pnl.toFixed(2)}`;
        document.getElementById('open-trades').textContent = status.open_trades;
        document.getElementById('win-rate').textContent = 
            `${(status.win_rate * 100).toFixed(1)}%`;
    }
}

const controller = new DashboardController();

// Real-time updates
setInterval(() => controller.updateMetrics(), 3000);
```

#### 1.4 Docker Compose Configuration

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - ENVIRONMENT_MODE=testnet
      - DELTA_TESTNET_API_KEY=${DELTA_TESTNET_API_KEY}
      - DELTA_TESTNET_SECRET=${DELTA_TESTNET_SECRET}
    volumes:
      - ./backend:/app
      - ./models:/app/models
    networks:
      - smc-network
    command: python app.py

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - smc-network

networks:
  smc-network:
    driver: bridge
```

**frontend/Dockerfile:**
```dockerfile
FROM nginx:alpine

COPY index.html /usr/share/nginx/html/
COPY static /usr/share/nginx/html/static

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### 1.5 Environment Setup (.env file)

```bash
# Delta Exchange Testnet Credentials
DELTA_TESTNET_API_KEY=your_testnet_key
DELTA_TESTNET_SECRET=your_testnet_secret

# Delta Exchange Live Credentials (keep empty for testnet only)
DELTA_LIVE_API_KEY=
DELTA_LIVE_SECRET=

# Environment Mode (testnet or live)
ENVIRONMENT_MODE=testnet

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=1
```

#### 1.6 Running Phase 1 Locally

```bash
# Clone/create project
git clone <your-repo> smc-trading-bot
cd smc-trading-bot

# Create environment file
cp .env.example .env
# Edit .env with your testnet credentials

# Build and run Docker containers
docker-compose build
docker-compose up

# Access dashboard at http://localhost:3000
# Backend API at http://localhost:5000
```

---

## Phase 2: Oracle Cloud VPS Deployment

### Objectives
- Deploy bot on Oracle Cloud free-tier VPS
- Integrate with GitHub for automated deployments
- Use 24/7 hosting with persistent data storage
- Scale to production-ready monitoring

### 2.1 Oracle Cloud Setup

**Create Oracle Cloud Account:**
- Sign up at oracle.com/cloud/free
- Get 1x AMD VM or 4x ARM VMs (always free tier)
- 25 GB storage (always free)
- Minimal network bandwidth

**VPS Configuration:**
- OS: Ubuntu 22.04 LTS
- Compute Shape: VM.Standard.E2.1.Micro (1 OCPU, 1 GB RAM)
- Storage: 50 GB

**Security List Setup (Firewall):**
```bash
# Allow traffic on:
- Port 22 (SSH)
- Port 80 (HTTP)
- Port 443 (HTTPS)
- Port 5000 (Backend API)
- Port 3000 (Frontend)
```

### 2.2 VPS Setup Script (setup.sh)

```bash
#!/bin/bash

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo apt-get install -y git

# Create app directory
mkdir -p /opt/smc-bot
cd /opt/smc-bot

# Clone from GitHub
git clone https://github.com/YOUR-USERNAME/smc-trading-bot.git .

# Create .env file with credentials
echo "DELTA_TESTNET_API_KEY=$DELTA_KEY" >> .env
echo "DELTA_TESTNET_SECRET=$DELTA_SECRET" >> .env
echo "ENVIRONMENT_MODE=testnet" >> .env

# Build and start containers
docker-compose build
docker-compose up -d

echo "Bot deployed successfully!"
```

### 2.3 GitHub Actions CI/CD (.github/workflows/deploy.yml)

```yaml
name: Deploy to Oracle Cloud VPS

on:
  push:
    branches:
      - main
      - develop

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker Images
      run: docker-compose build
    
    - name: Deploy to VPS via SSH
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.ORACLE_VPS_IP }}
        username: ubuntu
        key: ${{ secrets.ORACLE_SSH_KEY }}
        script: |
          cd /opt/smc-bot
          git pull origin main
          docker-compose pull
          docker-compose up -d --remove-orphans
          echo "Deployment complete"
```

### 2.4 Systemd Service for Auto-start

**File: /etc/systemd/system/smc-bot.service**
```ini
[Unit]
Description=SMC Trading Bot
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/smc-bot
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable smc-bot.service
sudo systemctl start smc-bot.service
sudo systemctl status smc-bot.service
```

### 2.5 Monitoring & Logging

**Journalctl logs:**
```bash
sudo journalctl -u smc-bot -f  # Follow logs
```

**Docker logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Free Monitoring Tools:**
- **Prometheus + Grafana** (Docker containers, free-tier)
- **ELK Stack** (Elasticsearch, Logstash, Kibana - optional)

---

## Phase 3: Reinforcement Learning & AI Integration

### Objectives
- Add Reinforcement Learning (RL) for adaptive trading
- Integrate AI-assisted signal pipelines
- Use free-tier ML services
- Implement continuous learning

### 3.1 Reinforcement Learning Module

**rl_agent.py:**
```python
import numpy as np
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam
from collections import deque
import random

class DQNAgent:
    """Deep Q-Network agent for trading decisions"""
    
    def __init__(self, state_size, action_size, learning_rate=0.001):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95  # Discount factor
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = learning_rate
        
        # Build Q-network
        self.model = self._build_model()
        self.target_model = self._build_model()
    
    def _build_model(self):
        """Build neural network model"""
        model = Sequential([
            Dense(64, activation='relu', input_dim=self.state_size),
            Dense(64, activation='relu'),
            Dense(32, activation='relu'),
            Dense(self.action_size, activation='linear')
        ])
        model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))
        return model
    
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay memory"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state):
        """Choose action (explore or exploit)"""
        if np.random.random() < self.epsilon:
            return random.randrange(self.action_size)  # Explore
        return np.argmax(self.model.predict(state)[0])  # Exploit
    
    def replay(self, batch_size):
        """Train on batch from replay memory"""
        if len(self.memory) < batch_size:
            return
        
        batch = random.sample(self.memory, batch_size)
        states = np.array([item[0] for item in batch])
        actions = np.array([item[1] for item in batch])
        rewards = np.array([item[2] for item in batch])
        next_states = np.array([item[3] for item in batch])
        dones = np.array([item[4] for item in batch])
        
        # Predict Q-values for starting state
        targets = self.model.predict(states)
        
        # Predict Q-values for next state
        next_q_values = self.target_model.predict(next_states)
        
        for i in range(batch_size):
            if dones[i]:
                targets[i][actions[i]] = rewards[i]
            else:
                targets[i][actions[i]] = rewards[i] + self.gamma * np.max(next_q_values[i])
        
        self.model.fit(states, targets, epochs=1, verbose=0)
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def update_target_model(self):
        """Update target network with main network weights"""
        self.target_model.set_weights(self.model.get_weights())
```

### 3.2 AI-Assisted Signal Pipeline

**ai_pipeline.py:**
```python
import numpy as np
import pandas as pd
from rl_agent import DQNAgent

class AISignalPipeline:
    """AI-powered trading signal generation"""
    
    def __init__(self, state_size=50):
        self.state_size = state_size
        self.action_size = 3  # 0: Hold, 1: Buy, 2: Sell
        self.agent = DQNAgent(state_size, self.action_size)
        self.episode_reward = 0
        self.trades_episode = 0
    
    def extract_state(self, df, order_blocks, choch, engulfing):
        """Extract state vector for RL agent"""
        # Price features
        price_features = np.array([
            df['close'].pct_change().tail(10).mean(),
            df['close'].pct_change().tail(10).std(),
            df['high'].tail(10).max() / df['low'].tail(10).min() - 1,
        ])
        
        # SMC features
        ob_distance = len(order_blocks) / 10  # Normalized
        choch_signal = 1 if choch else 0
        engulfing_signal = 1 if engulfing else 0
        
        smc_features = np.array([ob_distance, choch_signal, engulfing_signal])
        
        # Combine features
        state = np.concatenate([price_features, smc_features])
        
        # Pad to state_size
        if len(state) < self.state_size:
            state = np.pad(state, (0, self.state_size - len(state)))
        else:
            state = state[:self.state_size]
        
        return state.reshape(1, self.state_size)
    
    def get_action(self, state):
        """Get action from RL agent"""
        return self.agent.act(state)
    
    def learn_from_trade(self, state, action, reward, next_state, done):
        """Update RL agent based on trade outcome"""
        self.agent.remember(state, action, reward, next_state, done)
        self.agent.replay(32)
        self.episode_reward += reward
        
        if done:
            self.agent.update_target_model()
    
    def get_signal(self, df, order_blocks, choch, engulfing):
        """Generate AI-assisted trading signal"""
        state = self.extract_state(df, order_blocks, choch, engulfing)
        action = self.get_action(state)
        
        confidence = np.max(self.agent.model.predict(state)[0]) / 10  # Normalize
        
        return {
            'action': action,
            'confidence': confidence,
            'signal': 'BUY' if action == 1 else ('SELL' if action == 2 else 'HOLD')
        }
```

### 3.3 Integration with Main Strategy

**enhanced_strategy.py:**
```python
from smc_strategy import SMCStrategy
from ai_pipeline import AISignalPipeline

class EnhancedSMCStrategy(SMCStrategy):
    """SMC Strategy enhanced with AI/RL"""
    
    def __init__(self, ml_model, risk_params):
        super().__init__(ml_model, risk_params)
        self.ai_pipeline = AISignalPipeline(state_size=50)
        self.trade_history = []
    
    def generate_signal(self, df, symbol):
        """Enhanced signal generation with AI"""
        # Get base SMC signal
        base_signal = super().generate_signal(df, symbol)
        
        # Extract state for RL agent
        state = self.ai_pipeline.extract_state(
            df,
            base_signal['order_blocks'],
            base_signal['choch'],
            base_signal['engulfing']
        )
        
        # Get AI-assisted action
        ai_signal = self.ai_pipeline.get_signal(
            df,
            base_signal['order_blocks'],
            base_signal['choch'],
            base_signal['engulfing']
        )
        
        # Combine signals
        combined_confidence = (base_signal['ml_confidence'] + ai_signal['confidence']) / 2
        
        return {
            **base_signal,
            'ai_signal': ai_signal['signal'],
            'combined_confidence': combined_confidence,
            'rl_state': state
        }
    
    def record_trade_outcome(self, trade_result):
        """Learn from executed trades"""
        if 'rl_state' in trade_result:
            reward = trade_result['pnl'] / trade_result['risk']
            next_state = trade_result['final_state']
            done = trade_result['closed']
            
            # Update RL agent
            self.ai_pipeline.learn_from_trade(
                trade_result['rl_state'],
                trade_result['action'],
                reward,
                next_state,
                done
            )
            
            self.trade_history.append(trade_result)
```

### 3.4 Free AI/ML Services Integration

**Google Colab for Model Training (Free):**
```python
# Upload training data to Google Colab
# Train new models using free GPU
# Download and update models

# In your bot:
import gdown

# Download latest model from Google Drive
gdown.download('share_link', 'smc_model.h5', quiet=False)
```

**TensorFlow Lite for Edge Inference:**
```python
import tensorflow as tf

# Convert model to TFLite for faster inference
converter = tf.lite.TFLiteConverter.from_keras_model(model)
lite_model = converter.convert()

# Use in production for faster predictions
```

### 3.5 Continuous Learning Loop

**training_pipeline.py:**
```python
import schedule
import time
from datetime import datetime

class ContinuousLearningPipeline:
    """Continuous model training and improvement"""
    
    def __init__(self, bot):
        self.bot = bot
        self.training_interval_hours = 24
        self.last_training = datetime.now()
    
    def collect_training_data(self):
        """Collect recent trade data"""
        recent_trades = self.bot.closed_trades[-100:]  # Last 100 trades
        return recent_trades
    
    def retrain_models(self):
        """Retrain ML and RL models"""
        print("Starting continuous learning...")
        
        # Collect data
        training_data = self.collect_training_data()
        
        if len(training_data) < 20:
            print("Insufficient data for retraining")
            return
        
        # Retrain ML model
        X, y = self._prepare_ml_data(training_data)
        self.bot.ml_model.model.fit(X, y, epochs=5, batch_size=16, verbose=0)
        
        # Retrain RL agent
        for trade in training_data:
            reward = trade['pnl'] / max(trade['risk'], 0.01)
            self.bot.strategy.ai_pipeline.learn_from_trade(
                trade['state'],
                trade['action'],
                reward,
                trade['next_state'],
                trade['done']
            )
        
        self.last_training = datetime.now()
        print(f"Retraining complete at {self.last_training}")
    
    @staticmethod
    def _prepare_ml_data(trades):
        """Format trades for ML training"""
        X = np.array([t['features'] for t in trades])
        y = np.array([1 if t['pnl'] > 0 else 0 for t in trades])
        return X, y
    
    def schedule_training(self):
        """Schedule periodic retraining"""
        schedule.every(self.training_interval_hours).hours.do(self.retrain_models)
        
        while True:
            schedule.run_pending()
            time.sleep(60)
```

### 3.6 Monitoring Dashboard Enhancements

Add to dashboard:
- Real-time RL model performance metrics
- Training progress indicators
- Model accuracy over time
- Feature importance visualization
- Cumulative reward charts

**dashboard_enhancements.html:**
```html
<!-- ML Model Performance Tab -->
<div id="ml-performance-view" class="hidden">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Model Accuracy -->
        <div class="card p-5">
            <h3 class="text-sm font-medium text-gray-400">ML Model Accuracy</h3>
            <canvas id="accuracy-chart"></canvas>
        </div>
        
        <!-- RL Agent Reward -->
        <div class="card p-5">
            <h3 class="text-sm font-medium text-gray-400">RL Cumulative Reward</h3>
            <canvas id="reward-chart"></canvas>
        </div>
        
        <!-- Training Status -->
        <div class="card p-5">
            <h3 class="text-sm font-medium text-gray-400">Training Status</h3>
            <div id="training-status">
                <p>Last Training: <span id="last-training">Never</span></p>
                <button onclick="triggerRetraining()">Retrain Now</button>
            </div>
        </div>
    </div>
</div>
```

---

## Free Tier Service Usage

| Service             | Free Tier Benefit                          | Limit                                |
|-------------------|------------------------------------------|--------------------------------------|
| Oracle Cloud       | 1x Micro VM + 25GB storage (Always Free) | 2 OCPU max, 1 GB RAM                |
| GitHub            | Free repos, Actions (2000 min/month)      | Public repos recommended             |
| Google Colab       | Free GPU/TPU for model training          | 12 hrs per session max               |
| TensorFlow         | Open-source, free                        | No limit                            |
| PyTorch           | Open-source, free                        | No limit                            |
| Docker Hub         | Free public images, 1 private             | No build minutes limit on pull       |
| Prometheus/Grafana | Open-source, free                        | Self-hosted on VPS                  |

---

## Deployment Checklist

### Phase 1 (Local)
- [ ] Set up Docker and Docker Compose
- [ ] Configure .env with testnet credentials
- [ ] Build and test backend container
- [ ] Build and test frontend container
- [ ] Verify API endpoints (localhost:5000)
- [ ] Test dashboard connectivity
- [ ] Test SMC signal generation
- [ ] Verify testnet trades execution

### Phase 2 (Oracle Cloud VPS)
- [ ] Create Oracle Cloud account
- [ ] Create Ubuntu 22.04 VPS instance
- [ ] Configure firewall/security list
- [ ] Run VPS setup script
- [ ] Clone GitHub repository
- [ ] Deploy with Docker Compose
- [ ] Set up systemd service
- [ ] Configure GitHub Actions CI/CD
- [ ] Test remote dashboard access
- [ ] Set up monitoring

### Phase 3 (RL/AI Integration)
- [ ] Implement DQN agent
- [ ] Create AI signal pipeline
- [ ] Integrate RL with trading strategy
- [ ] Set up continuous learning loop
- [ ] Test model retraining
- [ ] Add ML monitoring to dashboard
- [ ] Validate RL performance metrics

---

## Next Steps & Recommendations

1. **Start Small:** Begin with testnet trading to validate strategy
2. **Monitor Continuously:** Use dashboards to track performance
3. **Iterate & Improve:** Continuously retrain models with new data
4. **Scale Gradually:** Move to live trading with minimal position sizes
5. **Backup & Safety:** Regular backups of models and trade history
6. **Documentation:** Keep detailed logs of all changes and performance

---

## Support & Resources

- **Delta Exchange API:** https://guides.delta.exchange
- **Docker Docs:** https://docs.docker.com
- **GitHub Actions:** https://github.com/features/actions
- **TensorFlow Guide:** https://www.tensorflow.org/guide
- **Oracle Cloud Free Tier:** https://www.oracle.com/cloud/free

This complete 3-phase plan provides a professional, scalable framework for deploying an automated SMC trading bot using entirely free or open-source services.
