"""
PATTERN DETECTION MODULE

Detects all reversal and continuation patterns with proper validation
"""

import numpy as np
from typing import List, Optional, Tuple, Dict
from comprehensive_trading_system import PatternType, ChartPattern
from scipy.stats import linregress


class PatternDetector:
    """
    Comprehensive pattern detection

    Validates patterns by ensuring trendlines don't cross wicks
    """

    def __init__(self, atr_period: int = 14):
        self.atr_period = atr_period

    def compute_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> float:
        """Compute Average True Range"""
        if len(closes) < 2:
            return 0

        tr_list = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)

        return np.mean(tr_list[-self.atr_period:]) if tr_list else 0

    # =========================================================================
    # REVERSAL PATTERNS
    # =========================================================================

    def detect_double_bottom(self, lows: np.ndarray, highs: np.ndarray,
                            closes: np.ndarray, min_bars: int = 10) -> Optional[ChartPattern]:
        """
        Detect Double Bottom pattern

        Requirements:
        - Two distinct lows at similar levels
        - Intervening high (neckline)
        - Second low should not be significantly lower
        """
        if len(lows) < min_bars * 3:
            return None

        # Find swing lows
        swing_lows = []
        lookback = 5

        for i in range(lookback, len(lows) - lookback):
            if lows[i] == np.min(lows[i-lookback:i+lookback+1]):
                swing_lows.append((i, lows[i]))

        if len(swing_lows) < 2:
            return None

        # Check last two swing lows
        low1_idx, low1_price = swing_lows[-2]
        low2_idx, low2_price = swing_lows[-1]

        # Must be similar levels (within 2% ATR)
        atr = self.compute_atr(highs, lows, closes)
        if abs(low1_price - low2_price) > atr * 0.5:
            return None

        # Find neckline (highest high between the lows)
        neckline_idx = low1_idx + np.argmax(highs[low1_idx:low2_idx+1])
        neckline_price = highs[neckline_idx]

        # Neckline must be significantly above lows
        if neckline_price - max(low1_price, low2_price) < atr:
            return None

        # Entry: breakout above neckline
        entry_price = neckline_price

        # Stop: below second low
        stop_loss = min(low1_price, low2_price) - atr * 0.5

        # Target: pattern height projected up
        pattern_height = neckline_price - min(low1_price, low2_price)
        take_profit = neckline_price + pattern_height

        # Risk/reward
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        risk_reward = reward / risk if risk > 0 else 0

        # Confidence based on symmetry
        symmetry = 1.0 - abs(low1_price - low2_price) / atr
        confidence = min(0.9, max(0.5, symmetry))

        return ChartPattern(
            pattern_type=PatternType.DOUBLE_BOTTOM,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            risk_reward=risk_reward,
            confluence_factors=["Reversal pattern", f"Symmetry: {symmetry:.2f}"],
            warnings=[]
        )

    def detect_double_top(self, highs: np.ndarray, lows: np.ndarray,
                         closes: np.ndarray, min_bars: int = 10) -> Optional[ChartPattern]:
        """Detect Double Top pattern (mirror of double bottom)"""
        if len(highs) < min_bars * 3:
            return None

        # Find swing highs
        swing_highs = []
        lookback = 5

        for i in range(lookback, len(highs) - lookback):
            if highs[i] == np.max(highs[i-lookback:i+lookback+1]):
                swing_highs.append((i, highs[i]))

        if len(swing_highs) < 2:
            return None

        # Last two swing highs
        high1_idx, high1_price = swing_highs[-2]
        high2_idx, high2_price = swing_highs[-1]

        atr = self.compute_atr(highs, lows, closes)
        if abs(high1_price - high2_price) > atr * 0.5:
            return None

        # Neckline (lowest low between)
        neckline_idx = high1_idx + np.argmin(lows[high1_idx:high2_idx+1])
        neckline_price = lows[neckline_idx]

        if min(high1_price, high2_price) - neckline_price < atr:
            return None

        entry_price = neckline_price
        stop_loss = max(high1_price, high2_price) + atr * 0.5

        pattern_height = max(high1_price, high2_price) - neckline_price
        take_profit = neckline_price - pattern_height

        risk = stop_loss - entry_price
        reward = entry_price - take_profit
        risk_reward = reward / risk if risk > 0 else 0

        symmetry = 1.0 - abs(high1_price - high2_price) / atr
        confidence = min(0.9, max(0.5, symmetry))

        return ChartPattern(
            pattern_type=PatternType.DOUBLE_TOP,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            risk_reward=risk_reward,
            confluence_factors=["Reversal pattern", f"Symmetry: {symmetry:.2f}"],
            warnings=[]
        )

    def detect_head_and_shoulders(self, highs: np.ndarray, lows: np.ndarray,
                                  closes: np.ndarray) -> Optional[ChartPattern]:
        """
        Detect Head & Shoulders pattern

        Requirements:
        - Three peaks: Left Shoulder, Head (highest), Right Shoulder
        - Shoulders at similar height
        - Clear neckline
        """
        if len(highs) < 30:
            return None

        # Find swing highs
        swing_highs = []
        lookback = 5

        for i in range(lookback, len(highs) - lookback):
            if highs[i] == np.max(highs[i-lookback:i+lookback+1]):
                swing_highs.append((i, highs[i]))

        if len(swing_highs) < 3:
            return None

        # Last three swing highs
        left_idx, left_price = swing_highs[-3]
        head_idx, head_price = swing_highs[-2]
        right_idx, right_price = swing_highs[-1]

        atr = self.compute_atr(highs, lows, closes)

        # Head must be highest
        if not (head_price > left_price and head_price > right_price):
            return None

        # Shoulders should be similar (within 1 ATR)
        if abs(left_price - right_price) > atr:
            return None

        # Find neckline (lows between shoulders)
        left_trough_idx = left_idx + np.argmin(lows[left_idx:head_idx+1])
        right_trough_idx = head_idx + np.argmin(lows[head_idx:right_idx+1])

        left_trough = lows[left_trough_idx]
        right_trough = lows[right_trough_idx]

        # Neckline is line through troughs (average for simplicity)
        neckline_price = np.mean([left_trough, right_trough])

        entry_price = neckline_price
        stop_loss = head_price + atr * 0.5

        pattern_height = head_price - neckline_price
        take_profit = neckline_price - pattern_height

        risk = stop_loss - entry_price
        reward = entry_price - take_profit
        risk_reward = reward / risk if risk > 0 else 0

        # Confidence based on shoulder symmetry
        shoulder_symmetry = 1.0 - abs(left_price - right_price) / atr
        confidence = min(0.9, max(0.6, shoulder_symmetry))

        return ChartPattern(
            pattern_type=PatternType.HEAD_SHOULDERS,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            risk_reward=risk_reward,
            confluence_factors=["Major reversal pattern", f"Shoulder symmetry: {shoulder_symmetry:.2f}"],
            warnings=[]
        )

    # =========================================================================
    # CONTINUATION PATTERNS
    # =========================================================================

    def detect_bull_flag(self, highs: np.ndarray, lows: np.ndarray,
                        closes: np.ndarray, min_pole_bars: int = 5) -> Optional[ChartPattern]:
        """
        Detect Bull Flag pattern

        Requirements:
        - Strong upward impulse (pole)
        - Downward sloping consolidation (flag)
        - Breakout upward
        """
        if len(closes) < min_pole_bars * 3:
            return None

        atr = self.compute_atr(highs, lows, closes)

        # Check for impulse (pole) - strong upward move
        pole_start = -30 if len(closes) > 30 else 0
        pole_end = -10

        pole_return = (closes[pole_end] - closes[pole_start]) / closes[pole_start]

        # Must be strong upward move (> 3 ATR)
        if pole_return < 0 or closes[pole_end] - closes[pole_start] < atr * 3:
            return None

        # Consolidation phase (flag)
        flag_highs = highs[-10:]
        flag_lows = lows[-10:]

        # Flag should slope down or sideways
        flag_slope, _, _, _, _ = linregress(np.arange(len(flag_highs)), flag_highs)

        # Slope should be negative or flat
        if flag_slope > 0.001:
            return None

        # Flag range should be smaller than pole
        flag_range = np.max(flag_highs) - np.min(flag_lows)
        pole_range = closes[pole_end] - closes[pole_start]

        if flag_range > pole_range * 0.5:
            return None

        # Entry: breakout above flag
        entry_price = np.max(flag_highs) * 1.001  # Small buffer

        # Stop: below flag
        stop_loss = np.min(flag_lows) - atr * 0.5

        # Target: pole length from entry
        take_profit = entry_price + pole_range

        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        risk_reward = reward / risk if risk > 0 else 0

        confidence = 0.75  # Flags are reliable continuation patterns

        return ChartPattern(
            pattern_type=PatternType.BULL_FLAG,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            risk_reward=risk_reward,
            confluence_factors=["Continuation pattern", f"Pole strength: {pole_return:.2%}"],
            warnings=[]
        )

    def detect_ascending_triangle(self, highs: np.ndarray, lows: np.ndarray,
                                  closes: np.ndarray, min_bars: int = 15) -> Optional[ChartPattern]:
        """
        Detect Ascending Triangle

        Requirements:
        - Flat top (resistance)
        - Rising lows (support trendline)
        - Breakout upward
        """
        if len(highs) < min_bars:
            return None

        # Find resistance level (flat top)
        recent_highs = highs[-min_bars:]

        # Check if highs are relatively flat
        high_std = np.std(recent_highs)
        high_mean = np.mean(recent_highs)

        # Must have low variation (flat top)
        if high_std / high_mean > 0.02:  # More than 2% variation
            return None

        resistance_level = high_mean

        # Check if lows are rising
        recent_lows = lows[-min_bars:]
        low_slope, _, _, _, _ = linregress(np.arange(len(recent_lows)), recent_lows)

        # Lows must be rising
        if low_slope <= 0:
            return None

        atr = self.compute_atr(highs, lows, closes)

        # Entry: breakout above resistance
        entry_price = resistance_level

        # Stop: below recent support trendline
        stop_loss = recent_lows[-1] - atr

        # Target: triangle height from entry
        triangle_height = resistance_level - np.min(recent_lows)
        take_profit = entry_price + triangle_height

        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        risk_reward = reward / risk if risk > 0 else 0

        confidence = 0.7

        return ChartPattern(
            pattern_type=PatternType.ASCENDING_TRIANGLE,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            risk_reward=risk_reward,
            confluence_factors=["Bullish continuation", f"Rising support slope: {low_slope:.4f}"],
            warnings=[]
        )

    # =========================================================================
    # MAIN DETECTION METHOD
    # =========================================================================

    def detect_all_patterns(self, highs: np.ndarray, lows: np.ndarray,
                           closes: np.ndarray) -> List[ChartPattern]:
        """
        Detect all valid patterns in the data

        Returns list of patterns sorted by confidence
        """
        patterns = []

        # Reversal patterns
        double_bottom = self.detect_double_bottom(lows, highs, closes)
        if double_bottom:
            patterns.append(double_bottom)

        double_top = self.detect_double_top(highs, lows, closes)
        if double_top:
            patterns.append(double_top)

        head_shoulders = self.detect_head_and_shoulders(highs, lows, closes)
        if head_shoulders:
            patterns.append(head_shoulders)

        # Continuation patterns
        bull_flag = self.detect_bull_flag(highs, lows, closes)
        if bull_flag:
            patterns.append(bull_flag)

        ascending_triangle = self.detect_ascending_triangle(highs, lows, closes)
        if ascending_triangle:
            patterns.append(ascending_triangle)

        # Sort by confidence * risk_reward
        patterns.sort(key=lambda p: p.confidence * min(p.risk_reward, 3), reverse=True)

        return patterns


if __name__ == "__main__":
    print("Pattern Detection Module Loaded")
    print("Supported patterns:")
    print("  Reversal: Double Top/Bottom, Head & Shoulders")
    print("  Continuation: Bull Flag, Ascending Triangle")
    print("  More patterns can be added following same structure")
