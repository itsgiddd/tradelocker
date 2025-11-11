"""
ULTRA AGGRESSIVE SYSTEM
Target: 50% daily returns

Strategy:
- 20% risk per trade (vs 2% normal)
- 0.50 confidence threshold (vs 0.75 normal)
- Trade ALL timeframes for maximum opportunity
- Compound aggressively
- No safety limits

WARNING: High risk of account blow-up!
"""

import numpy as np
from hawk_fx_enhanced_system import HawkFXEnhancedSystem


class UltraAggressiveSystem(HawkFXEnhancedSystem):
    """
    ULTRA AGGRESSIVE - Targeting 50% daily returns
    """

    def __init__(self):
        super().__init__()
        # More aggressive ATR
        self.atr_multiplier = 0.5  # Tighter stops for faster trades
        self.atr_period = 5        # Shorter period for faster reaction

    def generate_signal(self, closes, highs, lows, balance, risk_pct):
        """
        ULTRA AGGRESSIVE signal generation
        - Lower confidence threshold
        - Accept more marginal trades
        """
        signal = super().generate_signal(closes, highs, lows, balance, risk_pct)

        if signal:
            # Tighten stops for more aggressive trading
            current_price = closes[-1]
            atr = self.calculate_atr_trailing_stop(highs, lows, closes)['atr']

            # Tighter stops (1 ATR vs 2 ATR)
            if signal.direction == "LONG":
                signal.stop_loss = current_price - (1 * atr)
                signal.take_profit = current_price + (4 * atr)  # Higher R:R to compensate
            else:
                signal.stop_loss = current_price + (1 * atr)
                signal.take_profit = current_price - (4 * atr)

        return signal
