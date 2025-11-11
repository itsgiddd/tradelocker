"""
SMART AGGRESSIVE SYSTEM
Target: 30-50% profit per trade
Risk: 5-10% per trade (controlled)

Key Features:
- Dynamic position sizing with caps
- Probability-based take profit (30% min, 50% max)
- Stop loss: 5-10% of account
- Protection against runaway position sizes
- Margin safety checks
"""

import numpy as np
from hawk_fx_enhanced_system import HawkFXEnhancedSystem


class SmartAggressiveSystem(HawkFXEnhancedSystem):
    """
    SMART AGGRESSIVE - Controlled risk for sustainable growth
    """

    def __init__(self):
        super().__init__()
        # ATR settings
        self.atr_multiplier = 1.5
        self.atr_period = 14

        # Risk limits
        self.max_risk_percent = 10.0  # Maximum 10% risk
        self.min_risk_percent = 5.0   # Minimum 5% risk
        self.max_position_value = 100000  # Cap position at $100k

        # Profit targets
        self.min_profit_target = 0.30  # 30% minimum
        self.max_profit_target = 0.50  # 50% maximum

    def calculate_dynamic_risk(self, confidence, balance):
        """
        Calculate risk based on confidence
        Higher confidence = higher risk (within limits)
        """
        # Scale risk from 5% to 10% based on confidence
        # Confidence 0.5 = 5% risk
        # Confidence 1.0 = 10% risk
        risk_range = self.max_risk_percent - self.min_risk_percent
        confidence_scaled = (confidence - 0.5) / 0.5  # Scale 0.5-1.0 to 0-1
        confidence_scaled = max(0, min(1, confidence_scaled))

        risk_percent = self.min_risk_percent + (risk_range * confidence_scaled)

        return risk_percent

    def calculate_profit_target(self, confidence, ml_probability):
        """
        Calculate profit target based on probability
        Higher probability = higher target

        Returns: profit target as fraction of account (0.30 to 0.50)
        """
        # Average the confidence and ML probability
        avg_prob = (confidence + ml_probability) / 2

        # Scale from 30% to 50% based on probability
        target_range = self.max_profit_target - self.min_profit_target
        prob_scaled = (avg_prob - 0.5) / 0.5  # Scale 0.5-1.0 to 0-1
        prob_scaled = max(0, min(1, prob_scaled))

        profit_target = self.min_profit_target + (target_range * prob_scaled)

        return profit_target

    def calculate_position_size_with_caps(self, balance, risk_percent, entry_price, stop_loss):
        """
        Calculate position size with safety caps

        Prevents:
        - Oversized positions
        - Margin calls
        - Liquidity issues
        """
        # Calculate raw position size
        risk_amount = balance * (risk_percent / 100)
        risk_pips = abs(entry_price - stop_loss) / entry_price

        raw_position_size = risk_amount / risk_pips if risk_pips > 0 else 0

        # Calculate position value
        position_value = raw_position_size * entry_price

        # Apply cap to prevent oversized positions
        if position_value > self.max_position_value:
            capped_position_size = self.max_position_value / entry_price
            capped_risk_percent = (capped_position_size * risk_pips * 100) / balance

            return {
                'position_size': capped_position_size,
                'risk_percent': capped_risk_percent,
                'risk_amount': capped_position_size * risk_pips * balance / 100,
                'capped': True,
                'cap_reason': f'Position capped at ${self.max_position_value:,.0f}'
            }

        # Also cap if risk amount exceeds 10% of balance (safety)
        max_risk_amount = balance * 0.10
        if risk_amount > max_risk_amount:
            capped_position_size = (max_risk_amount / risk_pips) if risk_pips > 0 else 0

            return {
                'position_size': capped_position_size,
                'risk_percent': 10.0,
                'risk_amount': max_risk_amount,
                'capped': True,
                'cap_reason': 'Risk capped at 10% of account'
            }

        return {
            'position_size': raw_position_size,
            'risk_percent': risk_percent,
            'risk_amount': risk_amount,
            'capped': False,
            'cap_reason': None
        }

    def generate_signal(self, closes, highs, lows, balance, base_risk_pct):
        """
        Generate signal with smart risk management
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

        # Get ATR trailing stop
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

        # ATR trend alignment
        atr_trend = atr_data['trend']
        ml_direction = "LONG" if ml_proba > 0.5 else "SHORT"

        if ml_direction == "LONG" and atr_trend == "BULLISH":
            direction = "LONG"
            confidence += 0.20
            factors.append("✅ ATR TREND ALIGNED (BULLISH)")
        elif ml_direction == "SHORT" and atr_trend == "BEARISH":
            direction = "SHORT"
            confidence += 0.20
            factors.append("✅ ATR TREND ALIGNED (BEARISH)")
        else:
            return None

        # Calculate dynamic risk
        risk_percent = self.calculate_dynamic_risk(confidence, balance)

        # Calculate profit target
        profit_target_pct = self.calculate_profit_target(confidence, ml_proba)

        # Calculate stops using ATR
        current_price = closes[-1]
        atr = atr_data['atr']

        # Stop loss: 1.5 ATR (tighter control)
        if direction == "LONG":
            stop_loss = current_price - (1.5 * atr)
        else:
            stop_loss = current_price + (1.5 * atr)

        # Calculate position size with caps
        position_info = self.calculate_position_size_with_caps(
            balance, risk_percent, current_price, stop_loss
        )

        # Calculate take profit based on profit target percentage
        # TP = Entry + (Account * Target%) / Position Size
        profit_target_amount = balance * profit_target_pct

        if direction == "LONG":
            take_profit = current_price + (profit_target_amount / position_info['position_size'])
        else:
            take_profit = current_price - (profit_target_amount / position_info['position_size'])

        # Add position info to factors
        if position_info['capped']:
            factors.append(f"⚠️ {position_info['cap_reason']}")

        factors.append(f"Risk: {position_info['risk_percent']:.1f}% of account")
        factors.append(f"Target: {profit_target_pct*100:.0f}% profit (${profit_target_amount:,.0f})")

        # Create signal with all info
        from dataclasses import dataclass
        from typing import List

        @dataclass
        class SmartSignal:
            direction: str
            entry_price: float
            stop_loss: float
            take_profit: float
            confidence: float
            confluence_factors: List[str]
            atr_trend: str
            atr_trailing_stop: float
            ml_probability: float
            fractal_dim: float
            # Smart aggressive specific
            risk_percent: float
            risk_amount: float
            profit_target_pct: float
            profit_target_amount: float
            position_size: float
            position_capped: bool

        return SmartSignal(
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=min(confidence, 1.0),
            confluence_factors=factors,
            atr_trend=atr_trend,
            atr_trailing_stop=atr_data['trailing_stop'],
            ml_probability=ml_proba,
            fractal_dim=features['fractal_dim'],
            risk_percent=position_info['risk_percent'],
            risk_amount=position_info['risk_amount'],
            profit_target_pct=profit_target_pct,
            profit_target_amount=profit_target_amount,
            position_size=position_info['position_size'],
            position_capped=position_info['capped']
        )
