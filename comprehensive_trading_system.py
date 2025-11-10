"""
COMPREHENSIVE TRADING SYSTEM
Combining AEGFM-Ω + Pattern Recognition + S/R Analysis + Risk Management

Target: 75% accuracy through proper context, exit strategies, and confluence

Components:
1. AEGFM-Ω (Entropy + Fractal + Geometric flows)
2. Pattern Detection (ALL reversal and continuation patterns)
3. Multi-timeframe Support/Resistance
4. Proper Entry/Exit with risk management
5. Confluence scoring for 75%+ setups
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


# =============================================================================
# CORE DATA STRUCTURES
# =============================================================================

class PatternType(Enum):
    # Reversal patterns
    DOUBLE_BOTTOM = "Double Bottom"
    DOUBLE_TOP = "Double Top"
    HEAD_SHOULDERS = "Head & Shoulders"
    INV_HEAD_SHOULDERS = "Inverse Head & Shoulders"
    TRIPLE_BOTTOM = "Triple Bottom"
    TRIPLE_TOP = "Triple Top"
    FALLING_WEDGE = "Falling Wedge"
    RISING_WEDGE = "Rising Wedge"

    # Continuation patterns
    BULL_FLAG = "Bull Flag"
    BEAR_FLAG = "Bear Flag"
    BULL_PENNANT = "Bull Pennant"
    BEAR_PENNANT = "Bear Pennant"
    ASCENDING_TRIANGLE = "Ascending Triangle"
    DESCENDING_TRIANGLE = "Descending Triangle"
    SYMMETRICAL_TRIANGLE = "Symmetrical Triangle"
    RECTANGLE = "Rectangle"


@dataclass
class SupportResistanceLevel:
    """Support or Resistance level"""
    price: float
    strength: str  # "Very Strong", "Strong", "Moderate", "Minor"
    touches: int
    is_support: bool
    historical_context: str


@dataclass
class ChartPattern:
    """Detected chart pattern"""
    pattern_type: PatternType
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0 to 1
    risk_reward: float
    confluence_factors: List[str]
    warnings: List[str]


@dataclass
class TradeSetup:
    """Complete trade recommendation"""
    direction: str  # "LONG" or "SHORT"
    entry: float
    stop_loss: float
    take_profit: float
    position_size: float
    risk_amount: float
    reward_amount: float
    risk_reward: float
    confidence: float
    pattern: Optional[ChartPattern]
    exit_strategy: Dict[str, any]
    warnings: List[str]


# =============================================================================
# 1. AEGFM-Ω COMPONENTS
# =============================================================================

class EntropyAnalyzer:
    """
    Shannon entropy analysis for market uncertainty

    Low entropy = market settling = continuation likely
    High entropy = market destabilizing = reversal/breakout likely
    """

    def compute_entropy(self, prices: np.ndarray, bins: int = 10) -> float:
        """
        Compute Shannon entropy of price distribution

        Returns 0 to ~3.3 (for 10 bins)
        """
        if len(prices) < bins:
            return 0

        # Create price distribution
        hist, _ = np.histogram(prices, bins=bins)

        # Normalize to probabilities
        probs = hist / hist.sum()

        # Remove zeros
        probs = probs[probs > 0]

        # Shannon entropy
        entropy = -np.sum(probs * np.log2(probs))

        return entropy

    def entropy_signal(self, prices: np.ndarray, window: int = 50) -> Dict[str, float]:
        """
        Analyze entropy trend

        Returns:
        - current_entropy
        - entropy_change (increasing/decreasing)
        - signal: "SETTLING", "DESTABILIZING", or "NEUTRAL"
        """
        if len(prices) < window * 2:
            return {"current": 0, "change": 0, "signal": "NEUTRAL"}

        # Current entropy
        current_entropy = self.compute_entropy(prices[-window:])

        # Previous entropy
        prev_entropy = self.compute_entropy(prices[-window*2:-window])

        # Change
        entropy_change = current_entropy - prev_entropy

        # Signal
        if entropy_change < -0.2:
            signal = "SETTLING"  # Continuation likely
        elif entropy_change > 0.2:
            signal = "DESTABILIZING"  # Reversal/breakout likely
        else:
            signal = "NEUTRAL"

        return {
            "current": current_entropy,
            "change": entropy_change,
            "signal": signal
        }


class FractalDimensionAnalyzer:
    """
    Fractal dimension analysis using Higuchi method

    FD ≈ 1.0 → trending (predictable)
    FD ≈ 1.5 → transitional
    FD ≈ 2.0 → ranging (unpredictable)
    """

    def higuchi_fd(self, prices: np.ndarray, kmax: int = 10) -> float:
        """
        Compute Higuchi fractal dimension
        """
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

            if len(lm) > 0:
                lk.append(np.mean(lm))

        if len(lk) > 2:
            x = np.log(np.arange(1, len(lk) + 1))
            y = np.log(lk)
            slope, _ = np.polyfit(x, y, 1)
            return -slope

        return 2.0

    def fd_signal(self, prices: np.ndarray) -> Dict[str, any]:
        """
        Analyze fractal dimension signal

        Returns market regime and predictability
        """
        fd = self.higuchi_fd(prices[-100:] if len(prices) >= 100 else prices)

        if fd < 1.3:
            regime = "STRONG_TREND"
            predictability = "HIGH"
        elif fd < 1.7:
            regime = "TRENDING"
            predictability = "MODERATE"
        else:
            regime = "RANGING"
            predictability = "LOW"

        return {
            "fractal_dimension": fd,
            "regime": regime,
            "predictability": predictability
        }


class GeometricFlowAnalyzer:
    """
    Analyze price geometry: angles, curvature, momentum
    """

    def compute_price_angle(self, prices: np.ndarray, window: int = 20) -> float:
        """
        Compute angle of price trajectory (in degrees)
        """
        if len(prices) < window:
            return 0

        # Linear regression on recent prices
        x = np.arange(window)
        y = prices[-window:]

        slope, _ = np.polyfit(x, y, 1)

        # Convert slope to angle (degrees)
        angle = np.degrees(np.arctan(slope / np.mean(y)))

        return angle

    def compute_curvature(self, prices: np.ndarray, window: int = 20) -> float:
        """
        Compute curvature (acceleration/deceleration)

        Positive = accelerating up
        Negative = decelerating/reversing
        """
        if len(prices) < window:
            return 0

        # Fit quadratic
        x = np.arange(window)
        y = prices[-window:]

        coeffs = np.polyfit(x, y, 2)

        # Second derivative = curvature
        curvature = 2 * coeffs[0]

        return curvature

    def geometric_signal(self, prices: np.ndarray) -> Dict[str, float]:
        """
        Complete geometric analysis
        """
        angle = self.compute_price_angle(prices)
        curvature = self.compute_curvature(prices)

        # Momentum strength (0 to 1)
        momentum = min(1.0, abs(angle) / 45.0)  # 45° = strong

        return {
            "angle": angle,
            "curvature": curvature,
            "momentum": momentum
        }


# =============================================================================
# 2. SUPPORT & RESISTANCE DETECTION
# =============================================================================

class SupportResistanceDetector:
    """
    Multi-timeframe support and resistance detection
    """

    def find_swing_points(self, highs: np.ndarray, lows: np.ndarray,
                          lookback: int = 5) -> Tuple[List[int], List[int]]:
        """
        Find swing highs and swing lows

        Returns: (swing_high_indices, swing_low_indices)
        """
        swing_highs = []
        swing_lows = []

        for i in range(lookback, len(highs) - lookback):
            # Swing high
            if highs[i] == np.max(highs[i-lookback:i+lookback+1]):
                swing_highs.append(i)

            # Swing low
            if lows[i] == np.min(lows[i-lookback:i+lookback+1]):
                swing_lows.append(i)

        return swing_highs, swing_lows

    def cluster_levels(self, prices: List[float], tolerance: float = 0.002) -> List[Tuple[float, int]]:
        """
        Cluster similar price levels together

        Returns: [(level, count)]
        """
        if len(prices) == 0:
            return []

        prices_sorted = sorted(prices)
        clusters = []
        current_cluster = [prices_sorted[0]]

        for price in prices_sorted[1:]:
            if abs(price - current_cluster[0]) / current_cluster[0] <= tolerance:
                current_cluster.append(price)
            else:
                # Save cluster
                clusters.append((np.mean(current_cluster), len(current_cluster)))
                current_cluster = [price]

        # Last cluster
        if current_cluster:
            clusters.append((np.mean(current_cluster), len(current_cluster)))

        return clusters

    def detect_levels(self, highs: np.ndarray, lows: np.ndarray,
                     closes: np.ndarray) -> List[SupportResistanceLevel]:
        """
        Detect all major S/R levels
        """
        levels = []

        # Find swing points
        swing_highs, swing_lows = self.find_swing_points(highs, lows)

        # Cluster resistance levels (from swing highs)
        if swing_highs:
            resistance_prices = [highs[i] for i in swing_highs]
            resistance_clusters = self.cluster_levels(resistance_prices)

            for price, touches in resistance_clusters:
                strength = self.categorize_strength(touches)
                levels.append(SupportResistanceLevel(
                    price=price,
                    strength=strength,
                    touches=touches,
                    is_support=False,
                    historical_context=f"{touches} swing highs near this level"
                ))

        # Cluster support levels (from swing lows)
        if swing_lows:
            support_prices = [lows[i] for i in swing_lows]
            support_clusters = self.cluster_levels(support_prices)

            for price, touches in support_clusters:
                strength = self.categorize_strength(touches)
                levels.append(SupportResistanceLevel(
                    price=price,
                    strength=strength,
                    touches=touches,
                    is_support=True,
                    historical_context=f"{touches} swing lows near this level"
                ))

        # Sort by strength
        strength_order = {"Very Strong": 4, "Strong": 3, "Moderate": 2, "Minor": 1}
        levels.sort(key=lambda x: strength_order.get(x.strength, 0), reverse=True)

        return levels

    def categorize_strength(self, touches: int) -> str:
        """Categorize S/R strength based on touches"""
        if touches >= 5:
            return "Very Strong"
        elif touches >= 3:
            return "Strong"
        elif touches >= 2:
            return "Moderate"
        else:
            return "Minor"

    def check_proximity_to_sr(self, price: float, levels: List[SupportResistanceLevel],
                              tolerance: float = 0.005) -> Optional[SupportResistanceLevel]:
        """
        Check if price is near a major S/R level

        Returns the nearest level if within tolerance, else None
        """
        for level in levels:
            if abs(price - level.price) / price <= tolerance:
                return level
        return None


# =============================================================================
# Save point - This file is getting very long
# Continue in next message with pattern detection
# =============================================================================

if __name__ == "__main__":
    print("Comprehensive Trading System - Module 1 Loaded")
    print("Components: AEGFM-Ω (Entropy, Fractal, Geometric)")
    print("           Support/Resistance Detection")
    print()
    print("Next: Pattern Detection, Trade Setup Generation")
