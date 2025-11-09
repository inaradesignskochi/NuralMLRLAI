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

```bash
git clone https://github.com/yourusername/smc-trading-bot.git
cd smc-trading-bot
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Delta Exchange API credentials
```

### 3. Build and Run

```bash
docker-compose build
docker-compose up -d
```

### 4. Access Dashboard

Open http://localhost:3000 in your browser.

## Usage

### Start/Stop Bot

Use the dashboard controls or API:

```bash
# Start bot
curl -X POST http://localhost:5000/api/control/start

# Stop bot
curl -X POST http://localhost:5000/api/control/stop
```

### Switch Environment

```bash
# Switch to testnet
curl -X POST http://localhost:5000/api/control/environment \
  -H "Content-Type: application/json" \
  -d '{"environment": "testnet"}'

# Switch to live (be careful!)
curl -X POST http://localhost:5000/api/control/environment \
  -H "Content-Type: application/json" \
  -d '{"environment": "live"}'
```

### View Logs

```bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
docker-compose logs -f frontend
```

## Configuration

Edit `backend/config.py` to adjust:

- Risk parameters
- Trading symbols
- SMC detection sensitivity
- Position sizing

## API Endpoints

- `GET /api/status` - Bot status
- `POST /api/control/start` - Start bot
- `POST /api/control/stop` - Stop bot
- `POST /api/control/environment` - Switch environment
- `GET /api/trades` - Get trades
- `GET /api/parameters` - Get parameters
- `POST /api/parameters` - Update parameters

## Troubleshooting

### Bot not starting

Check logs: `docker-compose logs backend`

### API connection errors

Verify API credentials in `.env` file

### Dashboard not loading

Check if backend is running: `curl http://localhost:5000/api/health`

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