"""
HAWK FX ENHANCED SIMULATION
Ultimate Hybrid ML + Your Mentor's ATR Trailing Stop Filter

This should dramatically improve win rate by ONLY trading with the ATR trend!
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from hawk_fx_enhanced_system import HawkFXEnhancedSystem
import warnings
warnings.filterwarnings('ignore')


def generate_realistic_forex_data(n_points=5000, seed=42):
    """Generate realistic EUR/USD-like data"""
    np.random.seed(seed)

    prices = []
    dates = []
    current = 1.1000
    current_date = datetime(2023, 1, 1)

    for i in range(n_points):
        if i % 500 == 0:
            trend = np.random.choice([-1, 0, 1], p=[0.3, 0.4, 0.3])

        drift = trend * 0.0001 if 'trend' in locals() else 0
        volatility = 0.0008

        if current > 1.1500:
            drift -= 0.0002
        elif current < 1.0500:
            drift += 0.0002

        change = drift + np.random.normal(0, volatility)
        current = max(1.0000, min(1.2000, current * (1 + change)))

        prices.append(current)
        dates.append(current_date)
        current_date += timedelta(hours=1)

    closes = np.array(prices)

    noise = 0.0003
    opens = closes * (1 + np.random.normal(0, noise, len(closes)))
    highs = closes * (1 + np.abs(np.random.normal(0, noise, len(closes))))
    lows = closes * (1 - np.abs(np.random.normal(0, noise, len(closes))))

    highs = np.maximum.reduce([opens, closes, highs])
    lows = np.minimum.reduce([opens, closes, lows])

    return {
        'dates': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes
    }


class HawkFXSimulator:
    """Simulator using HAWK FX Enhanced System"""

    def __init__(self, starting_balance=10000, risk_percent=2.0, confidence_threshold=0.75):
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.equity = starting_balance
        self.risk_percent = risk_percent
        self.confidence_threshold = confidence_threshold

        self.system = HawkFXEnhancedSystem()

        self.trades = []
        self.equity_curve = []
        self.balance_curve = []
        self.dates = []

        self.open_position = None

    def run_backtest(self, data):
        """Run complete backtest"""
        dates = data['dates']
        opens = data['open']
        highs = data['high']
        lows = data['low']
        closes = data['close']

        print("="*80)
        print("🦅 HAWK FX ENHANCED SIMULATION")
        print("="*80)
        print(f"\nStarting Balance: ${self.starting_balance:,.2f}")
        print(f"Risk per Trade: {self.risk_percent}%")
        print(f"Confidence Threshold: {self.confidence_threshold:.0%}")
        print(f"\n🎯 FILTERING: Only trades that ALIGN with ATR trend!")
        print(f"📈 This should dramatically improve win rate!")
        print(f"\nSimulation Period: {dates[0]} to {dates[-1]}")
        print(f"Total Bars: {len(closes):,}")
        print("\n" + "="*80)
        print("STARTING AUTO-TRADING...")
        print("="*80 + "\n")

        # Train
        train_end = 2000
        print(f"Training system on first {train_end} bars...")
        if not self.system.train(closes, 200, train_end):
            print("Training failed!")
            return
        print("\n")

        # Run bar by bar
        for i in range(train_end, len(closes)):
            current_date = dates[i]

            # Update equity
            if self.open_position:
                self.equity = self.balance + self.calculate_floating_pnl(
                    self.open_position, closes[i], highs[i], lows[i]
                )
            else:
                self.equity = self.balance

            self.equity_curve.append(self.equity)
            self.balance_curve.append(self.balance)
            self.dates.append(current_date)

            # Manage open position
            if self.open_position:
                self.manage_position(i, highs, lows, closes)
                continue

            # Look for signal
            hist_closes = closes[:i]
            hist_highs = highs[:i]
            hist_lows = lows[:i]

            signal = self.system.generate_signal(
                hist_closes, hist_highs, hist_lows,
                self.balance, self.risk_percent
            )

            if signal and signal.confidence >= self.confidence_threshold:
                self.open_trade(signal, i, opens[i], current_date)

            # Progress
            if i % 500 == 0:
                pnl = self.balance - self.starting_balance
                pnl_pct = (pnl / self.starting_balance) * 100
                print(f"Bar {i:5d} | Balance: ${self.balance:,.2f} | P/L: ${pnl:+,.2f} ({pnl_pct:+.2f}%) | Trades: {len(self.trades)}", end='\r')

        print("\n\n" + "="*80)
        print("🦅 HAWK FX SIMULATION COMPLETE!")
        print("="*80 + "\n")

        self.print_results()
        self.plot_results()

    def open_trade(self, signal, bar_idx, entry_price, date):
        """Open new position"""
        risk_amount = self.balance * (self.risk_percent / 100)
        risk_pips = abs(entry_price - signal.stop_loss) / entry_price
        position_size = risk_amount / risk_pips

        self.open_position = {
            'signal': signal,
            'entry_bar': bar_idx,
            'entry_date': date,
            'entry_price': entry_price,
            'direction': signal.direction,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'position_size': position_size,
            'risk_amount': risk_amount
        }

        print(f"\n{'='*70}")
        print(f"🎯 TRADE #{len(self.trades) + 1} OPENED")
        print(f"{'='*70}")
        print(f"Date: {date}")
        print(f"Direction: {signal.direction}")
        print(f"Entry: {entry_price:.5f}")
        print(f"Stop Loss: {signal.stop_loss:.5f}")
        print(f"Take Profit: {signal.take_profit:.5f}")
        print(f"Confidence: {signal.confidence*100:.1f}%")
        print(f"ATR Trend: {signal.atr_trend}")
        print(f"ATR Trailing Stop: {signal.atr_trailing_stop:.5f}")
        print(f"Fractal Dim: {signal.fractal_dim:.2f}")
        print(f"\n📊 Confluence Factors:")
        for factor in signal.confluence_factors:
            print(f"  • {factor}")
        print(f"\n💰 Risk: ${risk_amount:.2f}")
        print(f"Balance: ${self.balance:,.2f}")
        print(f"{'='*70}\n")

    def calculate_floating_pnl(self, pos, current_close, current_high, current_low):
        """Calculate unrealized P/L"""
        if pos['direction'] == "LONG":
            pnl = (current_close - pos['entry_price']) * pos['position_size']
        else:
            pnl = (pos['entry_price'] - current_close) * pos['position_size']
        return pnl

    def manage_position(self, bar_idx, highs, lows, closes):
        """Manage open position"""
        pos = self.open_position

        current_high = highs[bar_idx]
        current_low = lows[bar_idx]
        current_close = closes[bar_idx]

        # Check stop loss
        if pos['direction'] == "LONG":
            if current_low <= pos['stop_loss']:
                self.close_trade(bar_idx, pos['stop_loss'], "Stop Loss Hit")
                return
        else:
            if current_high >= pos['stop_loss']:
                self.close_trade(bar_idx, pos['stop_loss'], "Stop Loss Hit")
                return

        # Check take profit
        if pos['direction'] == "LONG":
            if current_high >= pos['take_profit']:
                self.close_trade(bar_idx, pos['take_profit'], "Take Profit Hit")
                return
        else:
            if current_low <= pos['take_profit']:
                self.close_trade(bar_idx, pos['take_profit'], "Take Profit Hit")
                return

    def close_trade(self, bar_idx, exit_price, reason):
        """Close position"""
        pos = self.open_position

        if pos['direction'] == "LONG":
            pnl = (exit_price - pos['entry_price']) * pos['position_size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['position_size']

        pnl_pct = (pnl / pos['risk_amount']) * 100
        is_winner = pnl > 0

        self.balance += pnl

        trade_record = {
            'entry_date': pos['entry_date'],
            'exit_date': self.dates[bar_idx] if bar_idx < len(self.dates) else pos['entry_date'],
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'confidence': pos['signal'].confidence,
            'atr_trend': pos['signal'].atr_trend,
            'fractal_dim': pos['signal'].fractal_dim,
            'bars_held': bar_idx - pos['entry_bar'],
            'reason': reason,
            'is_winner': is_winner,
            'balance_after': self.balance
        }

        self.trades.append(trade_record)

        print(f"\n{'='*70}")
        print(f"{'✅ WIN' if is_winner else '❌ LOSS'} - TRADE #{len(self.trades)} CLOSED")
        print(f"{'='*70}")
        print(f"Exit: {exit_price:.5f}")
        print(f"Reason: {reason}")
        print(f"P/L: ${pnl:+,.2f} ({pnl_pct:+.1f}%)")
        print(f"Bars Held: {trade_record['bars_held']}")
        print(f"New Balance: ${self.balance:,.2f}")
        print(f"{'='*70}\n")

        self.open_position = None

    def print_results(self):
        """Print final results"""
        df = pd.DataFrame(self.trades)

        if len(df) == 0:
            print("No trades generated!")
            return

        total_trades = len(df)
        winners = df[df['is_winner'] == True]
        losers = df[df['is_winner'] == False]

        win_count = len(winners)
        loss_count = len(losers)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        total_profit = winners['pnl'].sum() if len(winners) > 0 else 0
        total_loss = abs(losers['pnl'].sum()) if len(losers) > 0 else 1
        net_profit = df['pnl'].sum()

        avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
        avg_loss = abs(losers['pnl'].mean()) if len(losers) > 0 else 0

        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        ending_balance = self.balance
        roi = ((ending_balance - self.starting_balance) / self.starting_balance) * 100

        # Max drawdown
        balances = df['balance_after'].values
        peak = balances[0]
        max_dd = 0
        for b in balances:
            if b > peak:
                peak = b
            dd = ((peak - b) / peak * 100) if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        print("="*80)
        print("🦅 HAWK FX ENHANCED RESULTS")
        print("="*80)
        print()
        print("💰 ACCOUNT GROWTH:")
        print(f"   Starting Balance:  ${self.starting_balance:,.2f}")
        print(f"   Ending Balance:    ${ending_balance:,.2f}")
        print(f"   Total Profit:      ${net_profit:+,.2f}")
        print(f"   ROI:               {roi:+.2f}%")
        print()
        print("📈 TRADING STATISTICS:")
        print(f"   Total Trades:      {total_trades} trades")
        print(f"   Winners:           {win_count} trades ({win_rate:.1f}%)")
        print(f"   Losers:            {loss_count} trades ({100-win_rate:.1f}%)")
        print(f"   Profit Factor:     {profit_factor:.2f}")
        print()
        print("💵 AVERAGE TRADE:")
        print(f"   Average Win:       ${avg_win:+,.2f}")
        print(f"   Average Loss:      ${avg_loss:,.2f}")
        print(f"   Win/Loss Ratio:    {avg_win/avg_loss:.2f}x" if avg_loss > 0 else "   Win/Loss Ratio:    N/A")
        print()
        print("📉 RISK METRICS:")
        print(f"   Max Drawdown:      {max_dd:.2f}%")
        print()
        print("="*80)

        # Save results
        df.to_csv('hawk_fx_results.csv', index=False)
        print("\n✅ Results saved to: hawk_fx_results.csv")

    def plot_results(self):
        """Plot equity curve"""
        if len(self.equity_curve) == 0:
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # Equity curve
        ax1.plot(self.dates, self.equity_curve, linewidth=2, color='#00d4ff', label='Equity')
        ax1.plot(self.dates, self.balance_curve, linewidth=2, color='#ffd700', alpha=0.7, label='Balance')
        ax1.axhline(y=self.starting_balance, color='gray', linestyle='--', alpha=0.5, label='Starting Balance')
        ax1.set_title('🦅 HAWK FX Enhanced - Account Growth', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Balance ($)', fontsize=12)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)

        # Drawdown
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak * 100

        ax2.fill_between(self.dates, 0, drawdown, color='#ff1744', alpha=0.5)
        ax2.set_title('Drawdown (%)', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Drawdown (%)', fontsize=12)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('hawk_fx_performance.png', dpi=300, bbox_inches='tight')
        print("✅ Chart saved to: hawk_fx_performance.png\n")


if __name__ == "__main__":
    # Generate data
    print("Generating realistic market data...")
    data = generate_realistic_forex_data(n_points=5000, seed=42)
    print(f"Generated {len(data['close']):,} bars (H1 timeframe)")
    print()

    # Create simulator
    simulator = HawkFXSimulator(
        starting_balance=10000,
        risk_percent=2.0,
        confidence_threshold=0.75
    )

    # Run backtest
    simulator.run_backtest(data)

    print("\n" + "="*80)
    print("🎯 SIMULATION COMPLETE!")
    print("="*80)
