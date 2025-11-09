import pandas as pd
import numpy as np
from config import RISK_PARAMS

class SMCStrategy:
    def __init__(self, risk_params):
        self.risk_params = risk_params
        self.open_trades = {}

    def detect_order_blocks(self, df, lookback=50):
        """Identify order blocks (supply/demand zones)"""
        order_blocks = []

        for i in range(lookback, len(df)):
            # Bullish order block: strong candle followed by down move
            if (df['close'].iloc[i] > df['open'].iloc[i] and
                i+1 < len(df) and df['close'].iloc[i+1] < df['open'].iloc[i+1]):
                order_blocks.append({
                    'type': 'BULLISH',
                    'high': df['high'].iloc[i],
                    'low': df['low'].iloc[i],
                    'time': df['time'].iloc[i],
                    'confirmed': False
                })

            # Bearish order block: strong down candle followed by up move
            if (df['close'].iloc[i] < df['open'].iloc[i] and
                i+1 < len(df) and df['close'].iloc[i+1] > df['open'].iloc[i+1]):
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
        """Generate trading signal combining SMC components"""
        # Get SMC components
        order_blocks = self.detect_order_blocks(df)
        choch = self.detect_choch(df)
        engulfing = self.detect_engulfing(df)

        # Simple signal generation logic
        signal_strength = 0
        direction = 'NEUTRAL'

        # Order blocks contribute to signal
        if order_blocks:
            latest_ob = order_blocks[-1]
            if latest_ob['type'] == 'BULLISH':
                signal_strength += 0.4
                direction = 'BUY'
            else:
                signal_strength += 0.4
                direction = 'SELL'

        # CHoCH contributes to signal
        if choch:
            latest_choch = choch[-1]
            if latest_choch['type'] == 'BULLISH_CHOCH':
                signal_strength += 0.3
                if direction == 'NEUTRAL':
                    direction = 'BUY'
            else:
                signal_strength += 0.3
                if direction == 'NEUTRAL':
                    direction = 'SELL'

        # Engulfing contributes to signal
        if engulfing:
            latest_engulfing = engulfing[-1]
            if latest_engulfing['type'] == 'BULLISH_ENGULFING':
                signal_strength += 0.3
                if direction == 'NEUTRAL':
                    direction = 'BUY'
            else:
                signal_strength += 0.3
                if direction == 'NEUTRAL':
                    direction = 'SELL'

        # Generate signal if strength is sufficient
        if signal_strength >= 0.5:
            return {
                'symbol': symbol,
                'direction': direction,
                'confidence': min(signal_strength, 1.0),
                'order_blocks': order_blocks[-3:] if order_blocks else [],
                'choch': choch[-1] if choch else None,
                'engulfing': engulfing[-1] if engulfing else None,
                'timestamp': df['time'].iloc[-1] if len(df) > 0 else None
            }

        return None

    def calculate_position(self, signal, account_balance):
        """Calculate trade size, SL, TP"""
        if not signal or signal['confidence'] < 0.5:
            return None

        # Position sizing
        risk_amount = account_balance * self.risk_params['max_risk_per_trade']

        # Use current price as entry
        entry_price = signal.get('entry_price', 10000)  # Default fallback

        # Set stop loss based on signal type
        if signal['direction'] == 'BUY':
            stop_loss = entry_price * 0.98  # 2% stop loss
            take_profit = entry_price * (1 + self.risk_params['reward_risk_ratio'] * 0.02)
        else:
            stop_loss = entry_price * 1.02  # 2% stop loss
            take_profit = entry_price * (1 - self.risk_params['reward_risk_ratio'] * 0.02)

        # Calculate position size
        sl_distance = abs(entry_price - stop_loss)
        position_size = risk_amount / sl_distance if sl_distance > 0 else 0

        # Limit position size
        max_size = account_balance * self.risk_params['max_position_size'] / entry_price
        position_size = min(position_size, max_size)

        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'side': signal['direction'],
            'risk_amount': risk_amount,
            'potential_profit': position_size * abs(take_profit - entry_price)
        }