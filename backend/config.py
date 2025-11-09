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
    'max_open_trades': 3,           # Max concurrent trades
}

# Trading Parameters
TRADING_PARAMS = {
    'symbols': ['BTCUSD', 'ETHUSD'],
    'timeframe': '15m',
    'order_block_lookback': 50,
    'choch_sensitivity': 0.002,
    'min_engulfing_ratio': 1.5,
}

def get_config():
    return CONFIG[ENVIRONMENT_MODE]

def update_environment(env):
    """Update environment mode"""
    global ENVIRONMENT_MODE
    if env in ['testnet', 'live']:
        ENVIRONMENT_MODE = env
        return True
    return False