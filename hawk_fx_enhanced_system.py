"""
HAWK FX ENHANCED SYSTEM
Combines Ultimate Hybrid ML + Your Mentor's ATR Trailing Stop

Key Enhancement:
- Only take trades that ALIGN with ATR trailing stop trend
- This should significantly improve win rate by filtering against-trend trades

Your Mentor's Formula (HAWK FX Gold Bar):
- ATR-based trailing stop
- Buy: Price above trailing stop + crossover
- Sell: Price below trailing stop + crossunder
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
from typing import List, Optional
import warnings
warnings.filterwarnings('ignore')


@dataclass
class TradeSignal:
    """Trade signal with full context"""
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float

    confidence: float  # 0 to 1
    confluence_factors: List[str]

    # ATR context
    atr_trend: str  # "BULLISH" or "BEARISH"
    atr_trailing_stop: float

    # ML context
    ml_probability: float
    fractal_dim: float


class HawkFXEnhancedSystem:
    """
    Ultimate Hybrid ML + HAWK FX ATR Trailing Stop
    """

    def __init__(self):
        self.rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.mlp_model = MLPClassifier(hidden_layer_sizes=(50, 30), max_iter=500, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False

        # HAWK FX parameters (from your mentor's formula)
        self.atr_multiplier = 1  # 'a' in original formula
        self.atr_period = 10     # 'c' in original formula

    def calculate_atr_trailing_stop(self, highs: np.ndarray, lows: np.ndarray,
                                     closes: np.ndarray) -> dict:
        """
        Calculate ATR Trailing Stop (HAWK FX method)
        Returns: {
            'trailing_stop': value,
            'trend': 'BULLISH' or 'BEARISH',
            'signal': 'BUY', 'SELL', or 'NONE'
        }
        """
        # Calculate ATR
        high_low = highs - lows
        high_close = np.abs(highs - np.roll(closes, 1))
        low_close = np.abs(lows - np.roll(closes, 1))

        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = np.mean(true_range[-self.atr_period:])

        n_loss = self.atr_multiplier * atr
        src = closes[-1]
        src_prev = closes[-2] if len(closes) > 1 else closes[-1]

        # Calculate trailing stop (matching your mentor's logic)
        if len(closes) < 2:
            trailing_stop = src - n_loss
            prev_trailing_stop = trailing_stop
        else:
            prev_trailing_stop = getattr(self, 'prev_trailing_stop', src - n_loss)

            if src > prev_trailing_stop and src_prev > prev_trailing_stop:
                trailing_stop = max(prev_trailing_stop, src - n_loss)
            elif src < prev_trailing_stop and src_prev < prev_trailing_stop:
                trailing_stop = min(prev_trailing_stop, src + n_loss)
            elif src > prev_trailing_stop:
                trailing_stop = src - n_loss
            else:
                trailing_stop = src + n_loss

        self.prev_trailing_stop = trailing_stop

        # Determine position (from your mentor's pos logic)
        if src_prev < prev_trailing_stop and src > trailing_stop:
            pos = 1  # Long
        elif src_prev > prev_trailing_stop and src < trailing_stop:
            pos = -1  # Short
        else:
            pos = getattr(self, 'prev_pos', 0)

        self.prev_pos = pos

        # Calculate EMA(1) - basically just the close
        ema = src

        # Crossovers (from your mentor's formula)
        above = ema > trailing_stop and (src_prev <= prev_trailing_stop if len(closes) > 1 else False)
        below = ema < trailing_stop and (src_prev >= prev_trailing_stop if len(closes) > 1 else False)

        # Buy/Sell signals (HAWK FX logic)
        buy = src > trailing_stop and above
        sell = src < trailing_stop and below

        # Bar trend
        bar_buy = src > trailing_stop
        bar_sell = src < trailing_stop

        return {
            'trailing_stop': trailing_stop,
            'trend': 'BULLISH' if bar_buy else 'BEARISH',
            'signal': 'BUY' if buy else ('SELL' if sell else 'NONE'),
            'atr': atr,
            'above_stop': bar_buy
        }

    def higuchi_fd(self, prices: np.ndarray, k_max: int = 8) -> float:
        """Calculate Higuchi Fractal Dimension"""
        n = len(prices)
        lk = []

        for k in range(1, k_max + 1):
            lm_sum = 0
            for m in range(k):
                ll = 0
                max_idx = int((n - m - 1) / k)

                for i in range(1, max_idx):
                    ll += abs(prices[m + i * k] - prices[m + (i - 1) * k])

                if max_idx > 0:
                    ll = ll * (n - 1) / (k * max_idx * k)
                    lm_sum += ll

            lk.append(lm_sum / k if k > 0 else 0)

        # Linear regression to get slope
        x = np.log(np.arange(1, k_max + 1))
        y = np.log([l for l in lk if l > 0])

        if len(y) < 3:
            return 2.0

        x = x[:len(y)]
        slope = np.polyfit(x, y, 1)[0]

        return -slope

    def extract_features(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> dict:
        """Extract ML features"""
        features = {}

        # Returns
        for w in [5, 10, 20, 50]:
            if len(closes) > w:
                features[f'return_{w}'] = (closes[-1] - closes[-w]) / closes[-w]
            else:
                features[f'return_{w}'] = 0

        # Volatility
        for w in [10, 20]:
            if len(closes) > w:
                returns = np.diff(closes[-w:]) / closes[-w:-1]
                features[f'vol_{w}'] = np.std(returns)
            else:
                features[f'vol_{w}'] = 0

        # RSI
        if len(closes) >= 14:
            delta = np.diff(closes[-15:])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = np.mean(gain)
            avg_loss = np.mean(loss)
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
            features['rsi'] = rsi / 100.0
        else:
            features['rsi'] = 0.5

        # Momentum
        if len(closes) > 20:
            features['momentum'] = (closes[-1] - closes[-20]) / closes[-20]
        else:
            features['momentum'] = 0

        # Fractal dimension
        if len(closes) >= 100:
            features['fractal_dim'] = self.higuchi_fd(closes[-100:])
        else:
            features['fractal_dim'] = 2.0

        return features

    def train(self, closes: np.ndarray, train_start: int, train_end: int) -> bool:
        """Train ML models"""
        print("Training HAWK FX Enhanced System...")
        print("  - Ultimate Hybrid ML base")
        print("  - ATR Trailing Stop filter")

        X_list = []
        y_list = []

        forward_window = 10

        for i in range(train_start, train_end - forward_window):
            if i < 100:
                continue

            hist_closes = closes[:i]
            features = self.extract_features(hist_closes, hist_closes, hist_closes)

            feature_vector = [
                features['return_5'],
                features['return_10'],
                features['return_20'],
                features['return_50'],
                features['vol_10'],
                features['vol_20'],
                features['rsi'],
                features['momentum'],
                features['fractal_dim']
            ]

            future_return = (closes[i + forward_window] - closes[i]) / closes[i]
            label = 1 if future_return > 0.002 else 0

            X_list.append(feature_vector)
            y_list.append(label)

        X = np.array(X_list)
        y = np.array(y_list)

        if len(X) < 50:
            return False

        X_scaled = self.scaler.fit_transform(X)

        self.rf_model.fit(X_scaled, y)
        self.gb_model.fit(X_scaled, y)
        self.mlp_model.fit(X_scaled, y)

        rf_acc = self.rf_model.score(X_scaled, y)
        gb_acc = self.gb_model.score(X_scaled, y)
        mlp_acc = self.mlp_model.score(X_scaled, y)

        print(f"\n  RF: {rf_acc*100:.2f}% train accuracy")
        print(f"  GB: {gb_acc*100:.2f}% train accuracy")
        print(f"  MLP: {mlp_acc*100:.2f}% train accuracy")
        print("\n  Training complete!")

        self.is_trained = True
        return True

    def generate_signal(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                       balance: float, risk_pct: float) -> Optional[TradeSignal]:
        """
        Generate trade signal with HAWK FX ATR filter

        KEY LOGIC:
        1. Calculate ML prediction (Ultimate Hybrid)
        2. Calculate ATR trailing stop (HAWK FX)
        3. ONLY take trades that align with ATR trend
        4. This filters out counter-trend trades
        """
        if not self.is_trained:
            return None

        if len(closes) < 100:
            return None

        # Get ML prediction
        features = self.extract_features(closes, highs, lows)

        feature_vector = np.array([[
            features['return_5'],
            features['return_10'],
            features['return_20'],
            features['return_50'],
            features['vol_10'],
            features['vol_20'],
            features['rsi'],
            features['momentum'],
            features['fractal_dim']
        ]])

        feature_scaled = self.scaler.transform(feature_vector)

        rf_proba = self.rf_model.predict_proba(feature_scaled)[0][1]
        gb_proba = self.gb_model.predict_proba(feature_scaled)[0][1]
        mlp_proba = self.mlp_model.predict_proba(feature_scaled)[0][1]

        ml_proba = (rf_proba + gb_proba + mlp_proba) / 3

        # Get ATR trailing stop (HAWK FX)
        atr_data = self.calculate_atr_trailing_stop(highs, lows, closes)

        # Confluence scoring
        confidence = 0.5
        factors = []

        # Strong momentum
        if abs(features['momentum']) > 0.02:
            confidence += 0.10
            factors.append("Strong momentum")

        # Predictable fractal dimension
        if 1.3 < features['fractal_dim'] < 1.7:
            confidence += 0.15
            factors.append(f"Predictable structure (FD={features['fractal_dim']:.2f})")

        # Low volatility
        if features['vol_10'] < 0.01:
            confidence += 0.10
            factors.append("Low volatility")

        # ML confidence
        if ml_proba > 0.6:
            confidence += 0.15
            factors.append(f"ML confidence ({ml_proba*100:.0f}%)")
        elif ml_proba < 0.4:
            confidence += 0.15
            factors.append(f"ML confidence ({(1-ml_proba)*100:.0f}%)")

        # Multi-timeframe alignment
        if ((features['return_5'] > 0 and features['return_10'] > 0 and features['return_20'] > 0) or
            (features['return_5'] < 0 and features['return_10'] < 0 and features['return_20'] < 0)):
            confidence += 0.10
            factors.append("Multi-timeframe alignment")

        # *** CRITICAL: ATR TREND ALIGNMENT (HAWK FX) ***
        atr_trend = atr_data['trend']

        # Determine ML direction
        ml_direction = "LONG" if ml_proba > 0.5 else "SHORT"

        # ONLY trade if ATR trend aligns with ML prediction
        if ml_direction == "LONG" and atr_trend == "BULLISH":
            direction = "LONG"
            confidence += 0.20  # BIG bonus for ATR alignment
            factors.append("✅ ATR TREND ALIGNED (BULLISH)")
        elif ml_direction == "SHORT" and atr_trend == "BEARISH":
            direction = "SHORT"
            confidence += 0.20  # BIG bonus for ATR alignment
            factors.append("✅ ATR TREND ALIGNED (BEARISH)")
        else:
            # REJECT trade - ATR trend doesn't align
            return None

        # Calculate stops using ATR
        current_price = closes[-1]
        atr = atr_data['atr']

        if direction == "LONG":
            stop_loss = current_price - (2 * atr)
            take_profit = current_price + (3 * atr)
        else:
            stop_loss = current_price + (2 * atr)
            take_profit = current_price - (3 * atr)

        return TradeSignal(
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=min(confidence, 1.0),
            confluence_factors=factors,
            atr_trend=atr_trend,
            atr_trailing_stop=atr_data['trailing_stop'],
            ml_probability=ml_proba,
            fractal_dim=features['fractal_dim']
        )
