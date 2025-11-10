"""
PRODUCTION SYSTEM BACKTESTING

Test the production system for 70-75% accuracy target
"""

import numpy as np
import pandas as pd
from production_system import ProductionTradingSystem, TradeSignal
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')


def generate_realistic_market_data(n_points: int = 3000, seed: int = 42) -> Dict[str, np.ndarray]:
    """
    Generate realistic OHLC data
    """
    np.random.seed(seed)

    closes = []
    current = 1.1000  # EUR/USD starting point

    for i in range(n_points):
        # Regime shifts every ~300 bars
        if i % 300 == 0:
            trend = np.random.choice([-1, 0, 1], p=[0.3, 0.4, 0.3])

        # Drift + noise
        drift = trend * 0.0001 if 'trend' in locals() else 0
        volatility = 0.0008

        # Mean reversion
        if current > 1.1500:
            drift -= 0.0002
        elif current < 1.0500:
            drift += 0.0002

        # Random walk
        change = drift + np.random.normal(0, volatility)
        current = current * (1 + change)

        closes.append(current)

    closes = np.array(closes)

    # Generate OHLC
    noise_factor = 0.0003

    opens = closes * (1 + np.random.normal(0, noise_factor, len(closes)))
    highs = closes * (1 + np.abs(np.random.normal(0, noise_factor, len(closes))))
    lows = closes * (1 - np.abs(np.random.normal(0, noise_factor, len(closes))))

    # Ensure OHLC relationships
    highs = np.maximum.reduce([opens, closes, highs])
    lows = np.minimum.reduce([opens, closes, lows])

    return {
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes
    }


def backtest_production_system():
    """
    Comprehensive backtest of production system
    """
    print("=" * 80)
    print("PRODUCTION SYSTEM BACKTEST")
    print("=" * 80)
    print()
    print("Target: 70-75% accuracy on ultra-selective, high-confluence setups")
    print()
    print("Enhancements over Ultimate Hybrid (62.16%):")
    print("  ✅ Support/Resistance detection and awareness")
    print("  ✅ Smart exit strategies (partials before major S/R)")
    print("  ✅ Higher confluence requirements (>= 0.75)")
    print("  ✅ Minimum R/R ratio (>= 1.5)")
    print("  ✅ Trade warnings for reversal risks")
    print()

    # Generate data
    print("Generating market data...")
    data = generate_realistic_market_data(n_points=3000, seed=42)

    opens = data['open']
    highs = data['high']
    lows = data['low']
    closes = data['close']

    print(f"Generated {len(closes)} bars\n")

    # Initialize system
    system = ProductionTradingSystem()

    # Train
    train_end = 1500
    print(f"Training period: bars 200 to {train_end}")
    if not system.train(closes, 200, train_end):
        print("Training failed!")
        return

    # Backtest
    print("\n" + "=" * 80)
    print("BACKTESTING ON UNSEEN DATA")
    print("=" * 80 + "\n")

    trades = []
    signals_generated = 0

    for idx in range(train_end, len(closes) - 20, 5):
        # Historical data up to this point
        hist_prices = closes[:idx]
        hist_highs = highs[:idx]
        hist_lows = lows[:idx]

        # Generate signal
        signal = system.generate_signal(hist_prices, hist_highs, hist_lows)

        if signal is None:
            continue

        signals_generated += 1

        # Print signal details (first 3 only)
        if signals_generated <= 3:
            print(f"\n{'='*60}")
            print(f"SIGNAL #{signals_generated} at bar {idx}")
            print(f"{'='*60}")
            print(f"Direction: {signal.direction}")
            print(f"Entry: {signal.entry_price:.5f}")
            print(f"Stop Loss: {signal.stop_loss:.5f}")
            print(f"Initial Target: {signal.initial_target:.5f}")
            print(f"Final Target: {signal.final_target:.5f}")
            print(f"\nConfluence Score: {signal.confidence:.2%}")
            print("Confluence Factors:")
            for factor in signal.confluence_factors:
                print(f"  {factor}")
            print(f"\nRisk/Reward: {signal.risk_reward_ratio:.2f}")
            print(f"Position Size: {signal.position_size:.2f} units")
            print(f"Risk: ${signal.risk_amount:.2f}")
            print(f"Reward: ${signal.reward_amount:.2f}")
            print(f"\nS/R Context: {signal.sr_context}")
            print(f"Exit Strategy: {signal.exit_strategy['type']}")
            if signal.warnings:
                print("\nWARNINGS:")
                for warning in signal.warnings:
                    print(f"  {warning}")
            print(f"{'='*60}\n")

        # Simulate trade outcome
        trade_result = simulate_trade(
            signal, highs[idx:idx+20], lows[idx:idx+20], closes[idx:idx+20]
        )

        trades.append(trade_result)

        if signals_generated % 10 == 0:
            print(f"Processed {signals_generated} signals...", end='\r')

    print(f"\n\nTotal signals generated: {signals_generated}\n")

    # Analyze results
    analyze_results(trades)


def simulate_trade(signal: TradeSignal, future_highs: np.ndarray,
                  future_lows: np.ndarray, future_closes: np.ndarray) -> Dict:
    """
    Simulate trade outcome with smart exits
    """
    entry = signal.entry_price
    sl = signal.stop_loss
    initial_target = signal.initial_target
    final_target = signal.final_target

    # Track partial exits
    exits = []
    remaining_position = 1.0  # 100%

    # Simulate bar by bar
    for i in range(len(future_highs)):
        if signal.direction == "LONG":
            # Check stop loss
            if future_lows[i] <= sl:
                # Hit stop - exit remaining position
                exits.append({
                    'bar': i,
                    'price': sl,
                    'percent': remaining_position,
                    'pnl_per_unit': sl - entry,
                    'reason': 'Stop Loss'
                })
                break

            # Check initial target
            if future_highs[i] >= initial_target and remaining_position > 0.5:
                # Take 50% off
                exits.append({
                    'bar': i,
                    'price': initial_target,
                    'percent': 0.5,
                    'pnl_per_unit': initial_target - entry,
                    'reason': 'Initial Target (50%)'
                })
                remaining_position -= 0.5

                # Move stop to breakeven
                sl = entry

            # Check final target
            if future_highs[i] >= final_target and remaining_position > 0:
                # Exit remaining
                exits.append({
                    'bar': i,
                    'price': final_target,
                    'percent': remaining_position,
                    'pnl_per_unit': final_target - entry,
                    'reason': 'Final Target'
                })
                break

        else:  # SHORT
            # Check stop loss
            if future_highs[i] >= sl:
                exits.append({
                    'bar': i,
                    'price': sl,
                    'percent': remaining_position,
                    'pnl_per_unit': entry - sl,
                    'reason': 'Stop Loss'
                })
                break

            # Check initial target
            if future_lows[i] <= initial_target and remaining_position > 0.5:
                exits.append({
                    'bar': i,
                    'price': initial_target,
                    'percent': 0.5,
                    'pnl_per_unit': entry - initial_target,
                    'reason': 'Initial Target (50%)'
                })
                remaining_position -= 0.5
                sl = entry

            # Check final target
            if future_lows[i] <= final_target and remaining_position > 0:
                exits.append({
                    'bar': i,
                    'price': final_target,
                    'percent': remaining_position,
                    'pnl_per_unit': entry - final_target,
                    'reason': 'Final Target'
                })
                break

    # If still open at end, close at market
    if remaining_position > 0:
        last_price = future_closes[-1]
        pnl_per_unit = (last_price - entry) if signal.direction == "LONG" else (entry - last_price)
        exits.append({
            'bar': len(future_closes) - 1,
            'price': last_price,
            'percent': remaining_position,
            'pnl_per_unit': pnl_per_unit,
            'reason': 'End of test period'
        })

    # Calculate total P/L
    total_pnl = 0
    hit_initial_target = False
    hit_final_target = False
    hit_stop = False

    for exit in exits:
        weighted_pnl = exit['pnl_per_unit'] * exit['percent']
        total_pnl += weighted_pnl * signal.position_size

        if 'Initial Target' in exit['reason']:
            hit_initial_target = True
        if 'Final Target' in exit['reason']:
            hit_final_target = True
        if 'Stop Loss' in exit['reason']:
            hit_stop = True

    # Determine outcome
    if hit_stop:
        outcome = "LOSS"
    elif hit_initial_target:
        outcome = "PARTIAL_WIN"
    elif hit_final_target:
        outcome = "FULL_WIN"
    else:
        outcome = "OPEN"

    # Consider partial win as success for accuracy calculation
    is_winner = outcome in ["PARTIAL_WIN", "FULL_WIN"]

    return {
        'signal': signal,
        'outcome': outcome,
        'is_winner': is_winner,
        'pnl': total_pnl,
        'exits': exits,
        'hit_initial_target': hit_initial_target,
        'hit_final_target': hit_final_target
    }


def analyze_results(trades: List[Dict]):
    """
    Comprehensive results analysis
    """
    if not trades:
        print("❌ No trades generated!")
        return

    df = pd.DataFrame([{
        'outcome': t['outcome'],
        'is_winner': t['is_winner'],
        'pnl': t['pnl'],
        'confidence': t['signal'].confidence,
        'risk_reward': t['signal'].risk_reward_ratio,
        'direction': t['signal'].direction,
        'has_warning': len(t['signal'].warnings) > 0,
        'hit_initial_target': t['hit_initial_target'],
        'hit_final_target': t['hit_final_target']
    } for t in trades])

    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    # Overall stats
    total_trades = len(df)
    winners = df['is_winner'].sum()
    losers = total_trades - winners
    win_rate = df['is_winner'].mean()

    print(f"Total Trades: {total_trades}")
    print(f"Winners: {winners}")
    print(f"Losers: {losers}")
    print(f"Win Rate: {win_rate:.2%}")
    print()

    # Target achievement
    print("Target Achievement:")
    print(f"  Hit Initial Target: {df['hit_initial_target'].sum()} ({df['hit_initial_target'].mean():.1%})")
    print(f"  Hit Final Target: {df['hit_final_target'].sum()} ({df['hit_final_target'].mean():.1%})")
    print()

    # P/L
    total_pnl = df['pnl'].sum()
    avg_win = df[df['is_winner']]['pnl'].mean() if winners > 0 else 0
    avg_loss = abs(df[~df['is_winner']]['pnl'].mean()) if losers > 0 else 0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

    print(f"Total P/L: ${total_pnl:.2f}")
    print(f"Average Win: ${avg_win:.2f}")
    print(f"Average Loss: ${avg_loss:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print()

    # High confidence subset (>= 0.80)
    high_conf = df[df['confidence'] >= 0.80]
    if len(high_conf) > 0:
        hc_win_rate = high_conf['is_winner'].mean()
        print(f"Ultra-High Confidence (>= 0.80) Trades: {len(high_conf)}")
        print(f"  Win Rate: {hc_win_rate:.2%}")
        print()

    # Warning trades
    warning_trades = df[df['has_warning']]
    if len(warning_trades) > 0:
        warning_win_rate = warning_trades['is_winner'].mean()
        print(f"Trades with S/R Warnings: {len(warning_trades)}")
        print(f"  Win Rate: {warning_win_rate:.2%}")
        print(f"  (Warnings = target near major S/R level)")
        print()

    # Statistical significance
    from scipy.stats import binomtest
    p_value = binomtest(winners, total_trades, 0.5, alternative='greater').pvalue
    print(f"Statistical Significance:")
    print(f"  P-value: {p_value:.6f}")
    print(f"  Significant (p < 0.05): {'✅ YES' if p_value < 0.05 else '❌ NO'}")
    print()

    # Verdict
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)
    print()

    if win_rate >= 0.75:
        print(f"🎉🎉🎉 75% TARGET ACHIEVED! Win Rate: {win_rate:.2%}")
        print("\n*** PRODUCTION SYSTEM VALIDATED ***")
    elif win_rate >= 0.70:
        print(f"🎉 70% TARGET ACHIEVED! Win Rate: {win_rate:.2%}")
        print(f"\nClose to 75% target - only {(0.75 - win_rate)*100:.1f}% away!")
    elif win_rate >= 0.65:
        print(f"✅ Solid Performance: {win_rate:.2%}")
        print(f"\nImprovement over Ultimate Hybrid (62.16%)!")
    elif win_rate >= 0.60:
        print(f"⚠️  Moderate Performance: {win_rate:.2%}")
        print("\nSimilar to Ultimate Hybrid baseline")
    else:
        print(f"❌ Below Target: {win_rate:.2%}")
        print("\nNeed further refinement")

    print()
    print("Comparison:")
    print(f"  Ultimate Hybrid (baseline): 62.16%")
    print(f"  Production System:          {win_rate:.2%}")

    if win_rate > 0.6216:
        improvement = ((win_rate - 0.6216) / 0.6216) * 100
        print(f"  Improvement:                +{improvement:.1f}%")
        print("\n  🚀 NEW RECORD!")

    print()
    print("=" * 80)


if __name__ == "__main__":
    backtest_production_system()
