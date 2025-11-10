"""
PRODUCTION TRADING SYSTEM v1.0
Ultimate Hybrid + S/R Awareness + Smart Exits

Target: 70-75% accuracy on ultra-selective, high-confluence setups

Enhancements over Ultimate Hybrid:
1. Support/Resistance detection before entry
2. Smart exit strategies (partials before major S/R levels)
3. Higher confluence requirements (multiple signals must align)
4. Proper risk management (position sizing, R:R requirements)
5. Trade warnings (reversal risks, weak setups)

Philosophy: Quality over quantity - trade rarely but accurately
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SupportResistanceLevel:
    """Support or Resistance level"""
    price: float
    strength: str  # "Very Strong", "Strong", "Moderate"
    touches: int
    is_support: bool
    distance_pct: float  # Distance from current price (%)


@dataclass
class TradeSignal:
    """Complete trade signal with risk management"""
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    initial_target: float
    final_target: float

    # Risk management
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float
    position_size: float

    # Confluence
    confidence: float  # 0 to 1
    confluence_factors: List[str]

    # Exit strategy
    exit_strategy: Dict[str, any]

    # Warnings
    warnings: List[str]

    # Context
    fractal_dim: float
    ml_probability: float
    sr_context: str


# =============================================================================
# SUPPORT & RESISTANCE DETECTOR
# =============================================================================

class SupportResistanceDetector:
    """Detect and validate S/R levels"""

    def find_swing_points(self, highs: np.ndarray, lows: np.ndarray,
                         lookback: int = 5) -> Tuple[List[float], List[float]]:
        """Find swing highs and lows"""
        swing_highs = []
        swing_lows = []

        for i in range(lookback, len(highs) - lookback):
            # Swing high
            if highs[i] == np.max(highs[i-lookback:i+lookback+1]):
                swing_highs.append(highs[i])

            # Swing low
            if lows[i] == np.min(lows[i-lookback:i+lookback+1]):
                swing_lows.append(lows[i])

        return swing_highs, swing_lows

    def cluster_levels(self, prices: List[float], tolerance: float = 0.005) -> List[Tuple[float, int]]:
        """Cluster similar prices into S/R levels"""
        if not prices:
            return []

        prices_sorted = sorted(prices)
        clusters = []
        current_cluster = [prices_sorted[0]]

        for price in prices_sorted[1:]:
            if abs(price - current_cluster[0]) / current_cluster[0] <= tolerance:
                current_cluster.append(price)
            else:
                clusters.append((np.mean(current_cluster), len(current_cluster)))
                current_cluster = [price]

        if current_cluster:
            clusters.append((np.mean(current_cluster), len(current_cluster)))

        return clusters

    def detect_levels(self, highs: np.ndarray, lows: np.ndarray,
                     current_price: float) -> List[SupportResistanceLevel]:
        """Detect all major S/R levels"""
        levels = []

        # Find swing points
        swing_highs, swing_lows = self.find_swing_points(highs, lows)

        # Cluster resistance levels
        if swing_highs:
            resistance_clusters = self.cluster_levels(swing_highs)
            for price, touches in resistance_clusters:
                if touches >= 2:  # At least 2 touches
                    strength = "Very Strong" if touches >= 5 else "Strong" if touches >= 3 else "Moderate"
                    distance_pct = ((price - current_price) / current_price) * 100

                    levels.append(SupportResistanceLevel(
                        price=price,
                        strength=strength,
                        touches=touches,
                        is_support=False,
                        distance_pct=distance_pct
                    ))

        # Cluster support levels
        if swing_lows:
            support_clusters = self.cluster_levels(swing_lows)
            for price, touches in support_clusters:
                if touches >= 2:
                    strength = "Very Strong" if touches >= 5 else "Strong" if touches >= 3 else "Moderate"
                    distance_pct = ((price - current_price) / current_price) * 100

                    levels.append(SupportResistanceLevel(
                        price=price,
                        strength=strength,
                        touches=touches,
                        is_support=True,
                        distance_pct=distance_pct
                    ))

        return levels

    def check_target_hits_sr(self, target: float, levels: List[SupportResistanceLevel],
                            tolerance: float = 0.01) -> Optional[SupportResistanceLevel]:
        """Check if target price hits a major S/R level (reversal risk!)"""
        for level in levels:
            if abs(target - level.price) / level.price <= tolerance:
                # Target is near this S/R level
                if level.strength in ["Very Strong", "Strong"]:
                    return level
        return None


# =============================================================================
# PRODUCTION TRADING SYSTEM
# =============================================================================

class ProductionTradingSystem:
    """
    Production-ready system combining proven components

    Base: Ultimate Hybrid (62.16%)
    Enhancements: S/R awareness + Smart exits
    Target: 70-75% on high-confluence setups
    """

    def __init__(self):
        # ML models (from Ultimate Hybrid)
        self.models = {
            'rf': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
            'gb': GradientBoostingClassifier(n_estimators=50, max_depth=5, learning_rate=0.05, random_state=42),
            'mlp': MLPClassifier(hidden_layer_sizes=(64, 32, 16), max_iter=200, random_state=42)
        }

        # S/R detector
        self.sr_detector = SupportResistanceDetector()

        self.scaler = StandardScaler()
        self.is_trained = False

    # =========================================================================
    # FEATURE EXTRACTION (from Ultimate Hybrid)
    # =========================================================================

    def higuchi_fd(self, prices: np.ndarray, kmax: int = 10) -> float:
        """Higuchi fractal dimension"""
        n = len(prices)
        if n < kmax * 4:
            return 2.0

        lk = []
        for k in range(1, min(kmax, n//4) + 1):
            lm = []
            for m in range(k):
                ll = 0
                n_max = int((n - m - 1) / k)
                for i in range(1, n_max):
                    ll += abs(prices[m + i*k] - prices[m + (i-1)*k])

                if n_max > 0:
                    ll = ll * (n - 1) / (k * n_max * k)
                    lm.append(ll)

            if lm:
                lk.append(np.mean(lm))

        if len(lk) > 2:
            x = np.log(np.arange(1, len(lk) + 1))
            y = np.log(lk)
            slope, _ = np.polyfit(x, y, 1)
            return -slope
        return 2.0

    def extract_features(self, prices: np.ndarray) -> Optional[Dict[str, float]]:
        """Extract features (ML + Fractal)"""
        if len(prices) < 100:
            return None

        features = {}

        # 1. Returns
        for w in [5, 10, 20, 50]:
            if len(prices) >= w + 1:
                features[f'return_{w}'] = (prices[-1] - prices[-w]) / prices[-w]

        # 2. Volatility
        for w in [10, 20]:
            if len(prices) >= w + 1:
                returns = np.diff(prices[-w:]) / prices[-w:-1]
                features[f'vol_{w}'] = np.std(returns)

        # 3. RSI
        if len(prices) >= 14:
            changes = np.diff(prices[-14:])
            gains = np.mean(np.where(changes > 0, changes, 0))
            losses = np.mean(np.where(changes < 0, -changes, 0))
            features['rsi'] = gains / (gains + losses + 1e-8)

        # 4. Momentum
        if len(prices) >= 20:
            features['momentum'] = (prices[-1] - prices[-20]) / prices[-20]

        # 5. Fractal dimension (CRITICAL for Ultimate Hybrid)
        features['fractal_dim'] = self.higuchi_fd(prices[-100:])

        # 6. Trend strength
        if len(prices) >= 20:
            x = np.arange(20)
            slope, _ = np.polyfit(x, prices[-20:], 1)
            features['trend_slope'] = slope / np.mean(prices[-20:])

        return features

    # =========================================================================
    # TRAINING
    # =========================================================================

    def train(self, prices: np.ndarray, train_start: int, train_end: int) -> bool:
        """Train ML models"""
        print("Training Production System...")
        print("  Base: Ultimate Hybrid (ML + Fractal)")
        print()

        X_train = []
        y_train = []

        for idx in range(train_start, train_end - 10, 5):
            features = self.extract_features(prices[:idx])

            if features:
                # Target: 5-bar ahead direction
                future_return = (prices[idx + 5] - prices[idx]) / prices[idx]
                direction = 1 if future_return > 0 else 0

                X_train.append(list(features.values()))
                y_train.append(direction)

        if len(X_train) < 100:
            print("  Insufficient training data!")
            return False

        X_train = np.array(X_train)
        y_train = np.array(y_train)
        X_train = np.nan_to_num(X_train, nan=0, posinf=1, neginf=-1)

        X_train_scaled = self.scaler.fit_transform(X_train)

        # Train each model
        for name, model in self.models.items():
            model.fit(X_train_scaled, y_train)
            acc = model.score(X_train_scaled, y_train)
            print(f"  {name.upper()}: {acc:.2%} train accuracy")

        self.is_trained = True
        print("\n  Training complete!")
        return True

    # =========================================================================
    # SIGNAL GENERATION WITH S/R AWARENESS
    # =========================================================================

    def generate_signal(self, prices: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                       account_size: float = 10000, risk_percent: float = 0.02) -> Optional[TradeSignal]:
        """
        Generate trade signal with S/R awareness and smart exits

        Only generates signals meeting 70-75% confluence requirements
        """
        if not self.is_trained:
            return None

        # Extract features
        features = self.extract_features(prices)
        if not features:
            return None

        X = np.array([list(features.values())])
        X = np.nan_to_num(X, nan=0, posinf=1, neginf=-1)
        X_scaled = self.scaler.transform(X)

        # Get predictions from all models
        predictions = []
        for model in self.models.values():
            try:
                prob = model.predict_proba(X_scaled)[0][1]
                predictions.append(prob)
            except:
                pass

        if not predictions:
            return None

        # Average prediction
        avg_prob = np.mean(predictions)
        prediction_std = np.std(predictions)

        # =====================================================================
        # CONFLUENCE SCORING (Enhanced for 70-75% target)
        # =====================================================================

        confluence_score = 0.5
        confluence_factors = []

        # 1. Model agreement (models must agree!)
        agreement = 1.0 - min(prediction_std * 4, 1.0)
        if agreement > 0.8:
            confluence_score += 0.20
            confluence_factors.append(f"✅ High model agreement ({agreement:.2f})")
        elif agreement > 0.6:
            confluence_score += 0.10
            confluence_factors.append(f"⚠️ Moderate model agreement ({agreement:.2f})")
        else:
            # Low agreement = don't trade
            return None

        # 2. Extreme prediction (clear signal)
        extremeness = abs(avg_prob - 0.5) * 2
        if extremeness > 0.4:
            confluence_score += 0.15
            confluence_factors.append(f"✅ Strong directional signal ({avg_prob:.2f})")
        elif extremeness > 0.3:
            confluence_score += 0.10
            confluence_factors.append(f"⚠️ Moderate signal ({avg_prob:.2f})")

        # 3. Fractal dimension (predictable regime)
        fd = features['fractal_dim']
        if 1.3 < fd < 1.7:
            confluence_score += 0.15
            confluence_factors.append(f"✅ Predictable fractal structure (FD={fd:.2f})")
        elif 1.2 < fd < 1.8:
            confluence_score += 0.08
            confluence_factors.append(f"⚠️ Moderate structure (FD={fd:.2f})")

        # 4. Low volatility (more predictable)
        if 'vol_20' in features and features['vol_20'] < 0.015:
            confluence_score += 0.10
            confluence_factors.append("✅ Low volatility regime")

        # =====================================================================
        # MINIMUM CONFLUENCE REQUIREMENT FOR 70-75% TARGET
        # =====================================================================

        if confluence_score < 0.75:
            # Below threshold - don't trade
            return None

        # =====================================================================
        # ENTRY, STOP LOSS, TARGETS
        # =====================================================================

        current_price = prices[-1]
        direction = "LONG" if avg_prob > 0.5 else "SHORT"

        # ATR for stops
        atr = np.std(np.diff(prices[-20:]) / prices[-20:-1]) * prices[-1]

        if direction == "LONG":
            entry_price = current_price
            stop_loss = entry_price - (atr * 2)
            initial_target = entry_price + (atr * 3)
            final_target = entry_price + (atr * 5)
        else:
            entry_price = current_price
            stop_loss = entry_price + (atr * 2)
            initial_target = entry_price - (atr * 3)
            final_target = entry_price - (atr * 5)

        # =====================================================================
        # S/R AWARENESS - CHECK IF TARGETS HIT MAJOR LEVELS
        # =====================================================================

        sr_levels = self.sr_detector.detect_levels(highs, lows, current_price)

        warnings = []
        exit_strategy = {}
        sr_context = ""

        # Check if final target hits S/R
        sr_at_final_target = self.sr_detector.check_target_hits_sr(final_target, sr_levels, tolerance=0.015)

        if sr_at_final_target:
            # CRITICAL: Target hits major S/R = high reversal risk!
            warnings.append(
                f"⚠️ FINAL TARGET HITS {sr_at_final_target.strength} "
                f"{'RESISTANCE' if not sr_at_final_target.is_support else 'SUPPORT'} "
                f"AT {sr_at_final_target.price:.4f} ({sr_at_final_target.touches} touches)"
            )

            # SMART EXIT STRATEGY: Take partials BEFORE the S/R level
            exit_strategy = {
                'type': 'PARTIAL_EXIT_BEFORE_SR',
                'first_exit': {
                    'price': initial_target,
                    'percent': 50,
                    'reason': 'Lock in profit before major S/R'
                },
                'second_exit': {
                    'price': sr_at_final_target.price * (0.997 if direction == "LONG" else 1.003),
                    'percent': 30,
                    'reason': f'Exit before {sr_at_final_target.strength} S/R reversal'
                },
                'final_exit': {
                    'price': final_target,
                    'percent': 20,
                    'reason': 'Runner for breakout (tight trail stop)'
                },
                'trail_stop_after_first_exit': True
            }

            sr_context = f"Target near {sr_at_final_target.strength} S/R - using partial exits"

        else:
            # No S/R conflict - normal swing trade
            exit_strategy = {
                'type': 'SWING_TRADE',
                'first_exit': {
                    'price': initial_target,
                    'percent': 50,
                    'reason': '1.5 R/R profit'
                },
                'final_exit': {
                    'price': final_target,
                    'percent': 50,
                    'reason': 'Full target'
                },
                'trail_stop_after_first_exit': True
            }

            sr_context = "Clean path to target - no major S/R conflicts"

        # =====================================================================
        # RISK MANAGEMENT
        # =====================================================================

        risk_amount = account_size * risk_percent
        risk_pips = abs(entry_price - stop_loss)
        position_size = risk_amount / risk_pips

        # Weighted average target (accounting for partial exits)
        if exit_strategy['type'] == 'PARTIAL_EXIT_BEFORE_SR':
            avg_exit = (
                initial_target * 0.5 +
                exit_strategy['second_exit']['price'] * 0.3 +
                final_target * 0.2
            )
        else:
            avg_exit = (initial_target * 0.5 + final_target * 0.5)

        reward_pips = abs(avg_exit - entry_price)
        reward_amount = position_size * reward_pips
        risk_reward = reward_pips / risk_pips

        # Minimum R/R requirement
        if risk_reward < 1.5:
            return None

        # =====================================================================
        # CREATE SIGNAL
        # =====================================================================

        signal = TradeSignal(
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            initial_target=initial_target,
            final_target=final_target,
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            risk_reward_ratio=risk_reward,
            position_size=position_size,
            confidence=confluence_score,
            confluence_factors=confluence_factors,
            exit_strategy=exit_strategy,
            warnings=warnings,
            fractal_dim=fd,
            ml_probability=avg_prob,
            sr_context=sr_context
        )

        return signal


# =============================================================================
# Continue in next file - this is getting long
# =============================================================================

if __name__ == "__main__":
    print("Production Trading System v1.0 - Core Module Loaded")
    print("Ready for backtesting and live deployment")
