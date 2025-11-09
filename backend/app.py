from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
from datetime import datetime
import pandas as pd

from config import get_config, update_environment, RISK_PARAMS, TRADING_PARAMS, ENVIRONMENT_MODE
from delta_exchange_client import DeltaExchangeClient
from smc_strategy import SMCStrategy
from ml_model import MLModel

app = Flask(__name__)
CORS(app)

# Initialize components
delta_client = DeltaExchangeClient()
ml_model = MLModel()
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

                    if not signal:
                        continue

                    # Get ML prediction
                    ml_features = ml_model.preprocess(df)
                    ml_confidence = ml_model.predict(ml_features)

                    # Combine signals
                    combined_confidence = (signal['confidence'] + ml_confidence) / 2

                    if combined_confidence < 0.65:
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
                            'entry_price': position['entry_price'],
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