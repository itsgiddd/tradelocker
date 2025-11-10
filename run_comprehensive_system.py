"""
COMPREHENSIVE TRADING SYSTEM - MAIN EXECUTION

Combines:
- AEGFM-Ω (Entropy, Fractal, Geometric)
- Pattern Detection
- Support/Resistance
- Proper Risk Management
- Exit Strategies

Target: 75% accuracy through confluence and proper context
"""

import numpy as np
import pandas as pd
from comprehensive_trading_system import (
    EntropyAnalyzer, FractalDimensionAnalyzer, GeometricFlowAnalyzer,
    SupportResistanceDetector, TradeSetup, SupportResistanceLevel
)
from pattern_detection import PatternDetector
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')


class ComprehensiveTradingSystem:
    """
    Complete trading system combining all components
    """

    def __init__(self):
        # AEGFM-Ω components
        self.entropy_analyzer = EntropyAnalyzer()
        self.fractal_analyzer = FractalDimensionAnalyzer()
        self.geometric_analyzer = GeometricFlowAnalyzer()

        # Pattern detection
        self.pattern_detector = PatternDetector()

        # S/R detection
        self.sr_detector = SupportResistanceDetector()

    def analyze_market(self, highs: np.ndarray, lows: np.ndarray,
                      closes: np.ndarray) -> Dict[str, any]:
        """
        Complete market analysis combining all components

        Returns comprehensive market state
        """
        analysis = {}

        # 1. AEGFM-Ω Analysis
        entropy_signal = self.entropy_analyzer.entropy_signal(closes)
        fractal_signal = self.fractal_analyzer.fd_signal(closes)
        geometric_signal = self.geometric_analyzer.geometric_signal(closes)

        analysis['entropy'] = entropy_signal
        analysis['fractal'] = fractal_signal
        analysis['geometry'] = geometric_signal

        # 2. Support/Resistance Levels
        sr_levels = self.sr_detector.detect_levels(highs, lows, closes)
        analysis['sr_levels'] = sr_levels

        # 3. Pattern Detection
        patterns = self.pattern_detector.detect_all_patterns(highs, lows, closes)
        analysis['patterns'] = patterns

        # 4. Confluence Score (0 to 1)
        confluence_score = self.calculate_confluence(
            entropy_signal, fractal_signal, geometric_signal, patterns
        )
        analysis['confluence_score'] = confluence_score

        return analysis

    def calculate_confluence(self, entropy: Dict, fractal: Dict,
                            geometry: Dict, patterns: List) -> float:
        """
        Calculate confluence score based on alignment of signals

        High confluence = multiple factors agree = higher probability setup
        """
        score = 0.5  # Base score

        # Entropy settling (continuation) or destabilizing (reversal)
        if entropy['signal'] == "SETTLING":
            score += 0.1
        elif entropy['signal'] == "DESTABILIZING":
            score += 0.05  # Reversal less certain

        # Fractal dimension in predictable range
        if fractal['predictability'] == "HIGH":
            score += 0.15
        elif fractal['predictability'] == "MODERATE":
            score += 0.10

        # Strong geometric momentum
        if geometry['momentum'] > 0.7:
            score += 0.10
        elif geometry['momentum'] > 0.5:
            score += 0.05

        # Valid patterns detected
        if patterns:
            best_pattern_confidence = max(p.confidence for p in patterns)
            score += best_pattern_confidence * 0.2

        return min(1.0, score)

    def generate_trade_setup(self, highs: np.ndarray, lows: np.ndarray,
                            closes: np.ndarray,
                            account_size: float = 1000,
                            risk_percent: float = 0.02) -> Optional[TradeSetup]:
        """
        Generate complete trade setup with risk management and exit strategy

        Returns TradeSetup or None if no valid setup
        """
        # Analyze market
        analysis = self.analyze_market(highs, lows, closes)

        # Need confluence >= 0.65 for 75% target
        if analysis['confluence_score'] < 0.65:
            return None

        # Need at least one pattern
        if not analysis['patterns']:
            return None

        # Best pattern
        best_pattern = analysis['patterns'][0]

        # Need good risk/reward
        if best_pattern.risk_reward < 1.5:
            return None

        # Check if target hits major S/R (reversal risk)
        sr_at_target = self.sr_detector.check_proximity_to_sr(
            best_pattern.take_profit,
            analysis['sr_levels'],
            tolerance=0.01
        )

        warnings = []
        exit_strategy = {}

        if sr_at_target:
            # WARNING: Target near major S/R
            warnings.append(
                f"⚠️ TARGET NEAR {sr_at_target.strength} {'SUPPORT' if sr_at_target.is_support else 'RESISTANCE'} "
                f"AT {sr_at_target.price:.4f} - HIGH REVERSAL RISK"
            )

            # Exit strategy: Take partials before S/R
            exit_strategy = {
                'type': 'SCALP_TO_SR',
                'partial_exit_price': sr_at_target.price * 0.998,  # Before S/R
                'partial_exit_percent': 50,
                'move_sl_to_breakeven': True,
                'watch_for_reversal': True,
                'reversal_signals': [
                    "Long wicks at S/R level",
                    "Engulfing candle at S/R",
                    "3 consecutive opposite candles"
                ]
            }
        else:
            # Normal swing trade
            exit_strategy = {
                'type': 'SWING',
                'trail_stop': True,
                'take_profit': best_pattern.take_profit
            }

        # Determine direction
        current_price = closes[-1]
        direction = "LONG" if best_pattern.entry_price > current_price else "SHORT"

        # Position sizing
        risk_amount = account_size * risk_percent
        risk_pips = abs(best_pattern.entry_price - best_pattern.stop_loss)
        position_size = risk_amount / risk_pips

        reward_pips = abs(best_pattern.take_profit - best_pattern.entry_price)
        reward_amount = position_size * reward_pips

        # Create trade setup
        trade = TradeSetup(
            direction=direction,
            entry=best_pattern.entry_price,
            stop_loss=best_pattern.stop_loss,
            take_profit=best_pattern.take_profit,
            position_size=position_size,
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            risk_reward=best_pattern.risk_reward,
            confidence=analysis['confluence_score'],
            pattern=best_pattern,
            exit_strategy=exit_strategy,
            warnings=warnings
        )

        return trade

    def backtest(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                window: int = 100, horizon: int = 10) -> Dict[str, any]:
        """
        Backtest the system

        Uses walk-forward analysis
        """
        results = []

        for i in range(window, len(closes) - horizon, 5):
            # Historical data
            hist_highs = highs[:i]
            hist_lows = lows[:i]
            hist_closes = closes[:i]

            # Generate setup
            setup = self.generate_trade_setup(hist_highs, hist_lows, hist_closes)

            if setup is None:
                continue

            # Simulate outcome
            entry = setup.entry
            sl = setup.stop_loss
            tp = setup.take_profit

            # Check next bars
            hit_sl = False
            hit_tp = False

            for j in range(i, min(i + horizon, len(closes))):
                # Check stop loss
                if setup.direction == "LONG":
                    if lows[j] <= sl:
                        hit_sl = True
                        break
                    if highs[j] >= tp:
                        hit_tp = True
                        break
                else:  # SHORT
                    if highs[j] >= sl:
                        hit_sl = True
                        break
                    if lows[j] <= tp:
                        hit_tp = True
                        break

            # Record result
            if hit_tp:
                outcome = "WIN"
                pnl = setup.reward_amount
            elif hit_sl:
                outcome = "LOSS"
                pnl = -setup.risk_amount
            else:
                outcome = "OPEN"
                pnl = 0

            results.append({
                'entry': entry,
                'sl': sl,
                'tp': tp,
                'outcome': outcome,
                'pnl': pnl,
                'confidence': setup.confidence,
                'pattern': setup.pattern.pattern_type.value if setup.pattern else None,
                'warnings': len(setup.warnings) > 0
            })

        # Analysis
        df = pd.DataFrame(results)

        if len(df) == 0:
            return {"error": "No trades generated"}

        closed_trades = df[df['outcome'].isin(['WIN', 'LOSS'])]

        if len(closed_trades) == 0:
            return {"error": "No closed trades"}

        win_rate = (closed_trades['outcome'] == 'WIN').mean()
        total_pnl = closed_trades['pnl'].sum()
        avg_win = closed_trades[closed_trades['outcome'] == 'WIN']['pnl'].mean()
        avg_loss = abs(closed_trades[closed_trades['outcome'] == 'LOSS']['pnl'].mean())

        # High confidence trades (>= 0.75)
        high_conf = closed_trades[closed_trades['confidence'] >= 0.75]
        high_conf_win_rate = (high_conf['outcome'] == 'WIN').mean() if len(high_conf) > 0 else 0

        return {
            'total_signals': len(df),
            'closed_trades': len(closed_trades),
            'win_rate': win_rate,
            'high_conf_win_rate': high_conf_win_rate,
            'high_conf_trades': len(high_conf),
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': (avg_win / avg_loss) if avg_loss > 0 else 0
        }


def generate_realistic_market_data(n_points: int = 2000, seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic OHLC data with regime shifts and patterns
    """
    np.random.seed(seed)

    prices = []
    current = 100.0

    for i in range(n_points):
        # Regime shifts
        if i % 200 == 0:
            trend = np.random.choice([-1, 0, 1])
        elif 'trend' not in locals():
            trend = 0

        # Base movement
        drift = trend * 0.001
        volatility = 0.01

        # Add mean reversion
        if current > 110:
            drift -= 0.002
        elif current < 90:
            drift += 0.002

        # Random walk with drift
        change = drift + np.random.normal(0, volatility)
        current = current * (1 + change)

        prices.append(current)

    prices = np.array(prices)

    # Generate OHLC from prices
    data = {
        'close': prices,
        'open': prices * (1 + np.random.normal(0, 0.002, len(prices))),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.003, len(prices)))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.003, len(prices))))
    }

    df = pd.DataFrame(data)

    # Ensure OHLC relationships
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)

    return df


def test_comprehensive_system():
    """
    Test the comprehensive trading system
    """
    print("=" * 80)
    print("COMPREHENSIVE TRADING SYSTEM TEST")
    print("Target: 75% accuracy through confluence and proper exits")
    print("=" * 80)
    print()

    # Generate data
    print("Generating realistic market data...")
    df = generate_realistic_market_data(n_points=2000, seed=42)

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values

    print(f"Generated {len(df)} bars")
    print()

    # Initialize system
    system = ComprehensiveTradingSystem()

    # Backtest
    print("Running backtest...")
    print()

    results = system.backtest(highs, lows, closes, window=200, horizon=20)

    # Display results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    if 'error' in results:
        print(f"❌ {results['error']}")
        return

    print(f"Total Signals Generated: {results['total_signals']}")
    print(f"Closed Trades: {results['closed_trades']}")
    print()

    print(f"Overall Win Rate: {results['win_rate']:.2%}")
    print()

    print(f"High Confidence (>= 0.75) Trades: {results['high_conf_trades']}")
    print(f"High Confidence Win Rate: {results['high_conf_win_rate']:.2%}")
    print()

    if results['high_conf_win_rate'] >= 0.75:
        print("✅ 75% TARGET ACHIEVED on high-confidence setups!")
    elif results['high_conf_win_rate'] >= 0.70:
        print("⚠️  Close to 75% target")
    else:
        print("❌ Did not reach 75% target")

    print()
    print(f"Total P/L: ${results['total_pnl']:.2f}")
    print(f"Average Win: ${results['avg_win']:.2f}")
    print(f"Average Loss: ${results['avg_loss']:.2f}")
    print(f"Profit Factor: {results['profit_factor']:.2f}")

    print()
    print("=" * 80)
    print("KEY DIFFERENCES FROM FAILED APPROACHES:")
    print("=" * 80)
    print("✅ Confluence scoring (multiple signals must align)")
    print("✅ Support/Resistance checked BEFORE pattern targets")
    print("✅ Exit strategies included (scalp vs swing)")
    print("✅ Warnings for reversal risks at S/R levels")
    print("✅ Only trades high-confidence setups (>= 0.65 confluence)")
    print("✅ Realistic risk/reward requirements (>= 1.5)")
    print("=" * 80)


if __name__ == "__main__":
    test_comprehensive_system()
