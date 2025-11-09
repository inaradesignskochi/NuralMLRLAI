import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, Dropout, LSTM
from tensorflow.keras.optimizers import Adam
import os

class MLModel:
    def __init__(self, model_path='models/smc_model.h5'):
        self.model_path = model_path
        self.model = None
        self.load_or_create_model()

    def load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.model_path):
            try:
                self.model = load_model(self.model_path)
                print(f"Loaded existing model from {self.model_path}")
            except Exception as e:
                print(f"Error loading model: {e}")
                self.create_model()
        else:
            self.create_model()

    def create_model(self):
        """Create a new ML model for price prediction"""
        self.model = Sequential([
            LSTM(64, input_shape=(30, 5), return_sequences=True),
            Dropout(0.2),
            LSTM(32),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1, activation='sigmoid')  # Binary classification: up/down
        ])

        self.model.compile(
            loss='binary_crossentropy',
            optimizer=Adam(learning_rate=0.001),
            metrics=['accuracy']
        )
        print("Created new ML model")

    def preprocess(self, df):
        """Convert raw OHLCV to ML features"""
        if df is None or len(df) < 30:
            return None

        df = df.copy()

        # Add technical features
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        df['macd'] = self._calculate_macd(df['close'])
        df['atr'] = self._calculate_atr(df)

        # Select features
        features = df[['returns', 'volatility', 'rsi', 'macd', 'atr']].tail(30).values

        # Handle NaN values
        features = np.nan_to_num(features, nan=0.0)

        # Normalize features
        if features.std(axis=0).any():
            features = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-8)

        return features

    def predict(self, features):
        """Generate prediction (0-1 confidence)"""
        if features is None or self.model is None:
            return 0.5

        try:
            prediction = self.model.predict(features.reshape(1, 30, 5), verbose=0)[0][0]
            return float(prediction)
        except Exception as e:
            print(f"Prediction error: {e}")
            return 0.5

    def save_model(self):
        """Save model to disk"""
        if self.model:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self.model.save(self.model_path)
            print(f"Model saved to {self.model_path}")

    @staticmethod
    def _calculate_rsi(prices, period=14):
        """Calculate RSI"""
        if len(prices) < period + 1:
            return pd.Series([50.0] * len(prices), index=prices.index)

        deltas = prices.diff()
        gain = (deltas.where(deltas > 0, 0)).rolling(window=period).mean()
        loss = (-deltas.where(deltas < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)

    @staticmethod
    def _calculate_macd(prices, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        if len(prices) < slow:
            return pd.Series([0.0] * len(prices), index=prices.index)

        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        return macd.fillna(0.0)

    @staticmethod
    def _calculate_atr(df, period=14):
        """Calculate ATR"""
        if len(df) < period:
            return pd.Series([0.0] * len(df), index=df.index)

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr.fillna(0.0)