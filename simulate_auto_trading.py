"""
AUTO-TRADING SIMULATION
Simulates the EA (Expert Advisor) trading automatically and shows account growth

This shows EXACTLY what would happen if you ran the UltimateHybridEA.mq5
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from production_system import ProductionTradingSystem
import warnings
warnings.filterwarnings('ignore')


def generate_realistic_forex_data(n_points=5000, seed=42):
    """
    Generate realistic EUR/USD-like data
    """
    np.random.seed(seed)

    prices = []
    dates = []
    current = 1.1000  # Starting price
    current_date = datetime(2023, 1, 1)

    for i in range(n_points):
        # Market regimes
        if i % 500 == 0:
            trend = np.random.choice([-1, 0, 1], p=[0.3, 0.4, 0.3])

        # Drift + volatility
        drift = trend * 0.0001 if 'trend' in locals() else 0
        volatility = 0.0008

        # Mean reversion
        if current > 1.1500:
            drift -= 0.0002
        elif current < 1.0500:
            drift += 0.0002

        # Random walk
        change = drift + np.random.normal(0, volatility)
        current = max(1.0000, min(1.2000, current * (1 + change)))

        prices.append(current)
        dates.append(current_date)
        current_date += timedelta(hours=1)  # H1 timeframe

    closes = np.array(prices)

    # Generate OHLC
    noise = 0.0003
    opens = closes * (1 + np.random.normal(0, noise, len(closes)))
    highs = closes * (1 + np.abs(np.random.normal(0, noise, len(closes))))
    lows = closes * (1 - np.abs(np.random.normal(0, noise, len(closes))))

    # Ensure OHLC relationships
    highs = np.maximum.reduce([opens, closes, highs])
    lows = np.minimum.reduce([opens, closes, lows])

    return {
        'dates': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes
    }


class AutoTradingSimulator:
    """
    Simulates the EA trading automatically
    """

    def __init__(self, starting_balance=10000, risk_percent=2.0,
                 confidence_threshold=0.75):
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.equity = starting_balance
        self.risk_percent = risk_percent
        self.confidence_threshold = confidence_threshold

        # Trading system
        self.system = ProductionTradingSystem()

        # Track results
        self.trades = []
        self.equity_curve = []
        self.balance_curve = []
        self.dates = []

        # State
        self.open_position = None

    def run_backtest(self, data):
        """
        Run complete backtest simulation
        """
        dates = data['dates']
        opens = data['open']
        highs = data['high']
        lows = data['low']
        closes = data['close']

        print("="*80)
        print("AUTO-TRADING SIMULATION")
        print("="*80)
        print(f"\nStarting Balance: ${self.starting_balance:,.2f}")
        print(f"Risk per Trade: {self.risk_percent}%")
        print(f"Confidence Threshold: {self.confidence_threshold:.0%}")
        print(f"Trade Limits: NONE - Will trade EVERY valid signal!")
        print(f"\nSimulation Period: {dates[0]} to {dates[-1]}")
        print(f"Total Bars: {len(closes):,}")
        print("\n" + "="*80)
        print("STARTING AUTO-TRADING...")
        print("="*80 + "\n")

        # Train the system
        train_end = 2000
        print(f"Training system on first {train_end} bars...")
        if not self.system.train(closes, 200, train_end):
            print("Training failed!")
            return
        print("Training complete!\n")

        # Run bar by bar
        for i in range(train_end, len(closes)):
            current_date = dates[i]

            # Update equity curve
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

            # Look for signal (NO TRADE LIMITS!)
            hist_closes = closes[:i]
            hist_highs = highs[:i]
            hist_lows = lows[:i]

            signal = self.system.generate_signal(
                hist_closes, hist_highs, hist_lows,
                self.balance, self.risk_percent
            )

            if signal and signal.confidence >= self.confidence_threshold:
                # Open position
                self.open_trade(signal, i, opens[i], current_date)

            # Progress update
            if i % 500 == 0:
                pnl = self.balance - self.starting_balance
                pnl_pct = (pnl / self.starting_balance) * 100
                print(f"Bar {i:5d} | Balance: ${self.balance:,.2f} | P/L: ${pnl:+,.2f} ({pnl_pct:+.2f}%) | Trades: {len(self.trades)}", end='\r')

        print("\n\n" + "="*80)
        print("AUTO-TRADING COMPLETE!")
        print("="*80 + "\n")

        self.print_results()
        self.plot_results()

    def open_trade(self, signal, bar_idx, entry_price, date):
        """Open new position"""
        # Calculate position size based on risk
        risk_amount = self.balance * (self.risk_percent / 100)
        risk_pips = abs(entry_price - signal.stop_loss) / entry_price

        # Simple position size (in base currency terms)
        position_size = risk_amount / risk_pips

        self.open_position = {
            'signal': signal,
            'entry_bar': bar_idx,
            'entry_date': date,
            'entry_price': entry_price,
            'direction': signal.direction,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.final_target,
            'position_size': position_size,
            'risk_amount': risk_amount,
            'partial_exit_done': False
        }

        print(f"\n{'='*60}")
        print(f"TRADE #{len(self.trades) + 1} OPENED")
        print(f"{'='*60}")
        print(f"Date: {date}")
        print(f"Direction: {signal.direction}")
        print(f"Entry: {entry_price:.5f}")
        print(f"Stop Loss: {signal.stop_loss:.5f}")
        print(f"Take Profit: {signal.final_target:.5f}")
        print(f"Confidence: {signal.confidence:.1%}")
        print(f"Risk: ${risk_amount:.2f}")
        print(f"Balance: ${self.balance:,.2f}")
        print(f"{'='*60}\n")

    def manage_position(self, bar_idx, highs, lows, closes):
        """Manage open position"""
        pos = self.open_position
        current_high = highs[bar_idx]
        current_low = lows[bar_idx]
        current_close = closes[bar_idx]

        # Check stop loss hit
        if pos['direction'] == "LONG":
            if current_low <= pos['stop_loss']:
                # Stop loss hit
                self.close_trade(bar_idx, pos['stop_loss'], "Stop Loss Hit")
                return

            # Check partial exit (50% at initial target)
            if not pos['partial_exit_done'] and current_high >= pos['signal'].initial_target:
                # Partial exit
                partial_pnl = (pos['signal'].initial_target - pos['entry_price']) * pos['position_size'] * 0.5
                self.balance += partial_pnl
                pos['partial_exit_done'] = True
                pos['stop_loss'] = pos['entry_price']  # Move to breakeven
                print(f"  → Partial Exit: +${partial_pnl:.2f} (50% closed)")

            # Check take profit hit
            if current_high >= pos['take_profit']:
                self.close_trade(bar_idx, pos['take_profit'], "Take Profit Hit")
                return

        else:  # SHORT
            if current_high >= pos['stop_loss']:
                # Stop loss hit
                self.close_trade(bar_idx, pos['stop_loss'], "Stop Loss Hit")
                return

            # Check partial exit
            if not pos['partial_exit_done'] and current_low <= pos['signal'].initial_target:
                # Partial exit
                partial_pnl = (pos['entry_price'] - pos['signal'].initial_target) * pos['position_size'] * 0.5
                self.balance += partial_pnl
                pos['partial_exit_done'] = True
                pos['stop_loss'] = pos['entry_price']  # Move to breakeven
                print(f"  → Partial Exit: +${partial_pnl:.2f} (50% closed)")

            # Check take profit
            if current_low <= pos['take_profit']:
                self.close_trade(bar_idx, pos['take_profit'], "Take Profit Hit")
                return

        # Trailing stop after 2R profit
        current_price = current_close
        if pos['direction'] == "LONG":
            profit = current_price - pos['entry_price']
            risk = pos['entry_price'] - pos['signal'].stop_loss
            if profit >= 2 * risk:
                new_sl = current_price - risk
                if new_sl > pos['stop_loss']:
                    pos['stop_loss'] = new_sl
        else:
            profit = pos['entry_price'] - current_price
            risk = pos['signal'].stop_loss - pos['entry_price']
            if profit >= 2 * risk:
                new_sl = current_price + risk
                if new_sl < pos['stop_loss']:
                    pos['stop_loss'] = new_sl

    def close_trade(self, bar_idx, exit_price, reason):
        """Close position"""
        pos = self.open_position

        # Calculate P/L
        if pos['direction'] == "LONG":
            pnl_per_unit = exit_price - pos['entry_price']
        else:
            pnl_per_unit = pos['entry_price'] - exit_price

        # Account for partial exit
        remaining_size = 0.5 if pos['partial_exit_done'] else 1.0
        total_pnl = pnl_per_unit * pos['position_size'] * remaining_size

        self.balance += total_pnl

        # Record trade
        bars_held = bar_idx - pos['entry_bar']
        is_winner = total_pnl > 0

        self.trades.append({
            'entry_date': pos['entry_date'],
            'exit_date': self.dates[bar_idx] if bar_idx < len(self.dates) else pos['entry_date'],
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'pnl': total_pnl,
            'pnl_pct': (total_pnl / pos['risk_amount']) * 100,
            'confidence': pos['signal'].confidence,
            'bars_held': bars_held,
            'reason': reason,
            'is_winner': is_winner,
            'balance_after': self.balance
        })

        print(f"\n{'='*60}")
        print(f"TRADE #{len(self.trades)} CLOSED")
        print(f"{'='*60}")
        print(f"Exit: {exit_price:.5f}")
        print(f"Reason: {reason}")
        print(f"P/L: ${total_pnl:+.2f} ({(total_pnl/pos['risk_amount'])*100:+.1f}%)")
        print(f"Result: {'✅ WIN' if is_winner else '❌ LOSS'}")
        print(f"Bars Held: {bars_held}")
        print(f"New Balance: ${self.balance:,.2f}")
        print(f"{'='*60}\n")

        self.open_position = None

    def calculate_floating_pnl(self, pos, current_close, current_high, current_low):
        """Calculate current floating P/L"""
        if pos['direction'] == "LONG":
            unrealized = (current_close - pos['entry_price']) * pos['position_size']
        else:
            unrealized = (pos['entry_price'] - current_close) * pos['position_size']

        if pos['partial_exit_done']:
            unrealized *= 0.5

        return unrealized

    def print_results(self):
        """Print detailed results"""
        if not self.trades:
            print("No trades executed!")
            return

        df = pd.DataFrame(self.trades)

        # Overall stats
        total_trades = len(df)
        winners = df['is_winner'].sum()
        losers = total_trades - winners
        win_rate = df['is_winner'].mean()

        total_pnl = df['pnl'].sum()
        total_pnl_pct = (total_pnl / self.starting_balance) * 100

        avg_win = df[df['is_winner']]['pnl'].mean() if winners > 0 else 0
        avg_loss = df[~df['is_winner']]['pnl'].mean() if losers > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # Max drawdown
        peak = self.starting_balance
        max_dd = 0
        for balance in self.balance_curve:
            if balance > peak:
                peak = balance
            dd = ((peak - balance) / peak) * 100
            if dd > max_dd:
                max_dd = dd

        print("FINAL RESULTS")
        print("="*80)
        print()
        print(f"📊 ACCOUNT SUMMARY:")
        print(f"  Starting Balance:  ${self.starting_balance:,.2f}")
        print(f"  Ending Balance:    ${self.balance:,.2f}")
        print(f"  Total Profit:      ${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")
        print()

        print(f"📈 TRADING STATISTICS:")
        print(f"  Total Trades:      {total_trades}")
        print(f"  Winners:           {winners} ({win_rate:.1%})")
        print(f"  Losers:            {losers}")
        print(f"  Win Rate:          {win_rate:.1%}")
        print()

        print(f"💰 PROFIT/LOSS:")
        print(f"  Average Win:       ${avg_win:+,.2f}")
        print(f"  Average Loss:      ${avg_loss:+,.2f}")
        print(f"  Profit Factor:     {profit_factor:.2f}")
        print(f"  Max Drawdown:      {max_dd:.2f}%")
        print()

        print(f"⏱️  HOLDING TIME:")
        print(f"  Avg Bars Held:     {df['bars_held'].mean():.1f}")
        print(f"  Max Bars Held:     {df['bars_held'].max()}")
        print()

        # Best and worst trades
        best_trade = df.loc[df['pnl'].idxmax()]
        worst_trade = df.loc[df['pnl'].idxmin()]

        print(f"🏆 BEST TRADE:")
        print(f"  Date: {best_trade['entry_date']}")
        print(f"  Direction: {best_trade['direction']}")
        print(f"  P/L: ${best_trade['pnl']:+,.2f}")
        print()

        print(f"💔 WORST TRADE:")
        print(f"  Date: {worst_trade['entry_date']}")
        print(f"  Direction: {worst_trade['direction']}")
        print(f"  P/L: ${worst_trade['pnl']:+,.2f}")
        print()

        print("="*80)

        # Monthly breakdown
        df['month'] = pd.to_datetime(df['entry_date']).dt.to_period('M')
        monthly = df.groupby('month').agg({
            'pnl': 'sum',
            'is_winner': ['sum', 'count', 'mean']
        })

        if len(monthly) > 0:
            print("\n📅 MONTHLY BREAKDOWN:")
            print("-"*80)
            for month, row in monthly.iterrows():
                month_pnl = row[('pnl', 'sum')]
                month_trades = row[('is_winner', 'count')]
                month_wr = row[('is_winner', 'mean')]
                print(f"  {month}: ${month_pnl:+8,.2f} | {month_trades:2.0f} trades | {month_wr:5.1%} win rate")
            print("-"*80 + "\n")

        # Save results
        df.to_csv('/home/user/tradelocker/auto_trading_results.csv', index=False)
        print("💾 Detailed results saved to: auto_trading_results.csv\n")

    def plot_results(self):
        """Plot equity curve and other charts"""
        if not self.trades:
            return

        fig, axes = plt.subplots(3, 1, figsize=(14, 10))

        # 1. Equity Curve
        ax1 = axes[0]
        ax1.plot(self.dates, self.equity_curve, label='Equity', linewidth=2, color='blue')
        ax1.plot(self.dates, self.balance_curve, label='Balance', linewidth=1, alpha=0.7, color='green')
        ax1.axhline(y=self.starting_balance, color='red', linestyle='--', label='Starting Balance')
        ax1.set_title('Account Growth - Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Account Value ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # 2. Cumulative P/L
        df = pd.DataFrame(self.trades)
        df['cumulative_pnl'] = df['pnl'].cumsum()

        ax2 = axes[1]
        ax2.plot(range(len(df)), df['cumulative_pnl'], linewidth=2, color='green')
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax2.set_title('Cumulative Profit/Loss', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Trade Number')
        ax2.set_ylabel('Cumulative P/L ($)')
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # 3. Trade P/L Distribution
        ax3 = axes[2]
        colors = ['green' if x else 'red' for x in df['is_winner']]
        ax3.bar(range(len(df)), df['pnl'], color=colors, alpha=0.7)
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax3.set_title('Individual Trade Results', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Trade Number')
        ax3.set_ylabel('P/L ($)')
        ax3.grid(True, alpha=0.3)
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        plt.tight_layout()
        plt.savefig('/home/user/tradelocker/auto_trading_performance.png', dpi=150, bbox_inches='tight')
        print("📊 Performance charts saved to: auto_trading_performance.png\n")
        plt.close()


def main():
    """Run the simulation"""

    # Generate market data
    print("Generating realistic market data...")
    data = generate_realistic_forex_data(n_points=5000, seed=42)
    print(f"Generated {len(data['close']):,} bars (H1 timeframe)")
    print()

    # Create simulator
    simulator = AutoTradingSimulator(
        starting_balance=10000,
        risk_percent=2.0,
        confidence_threshold=0.75
    )

    # Run backtest
    simulator.run_backtest(data)

    print("\n" + "="*80)
    print("SIMULATION COMPLETE!")
    print("="*80)
    print("\nThis shows what would happen if you ran the EA automatically.")
    print("Remember:")
    print("  • This is simulated data, not real market data")
    print("  • Real results will vary")
    print("  • Always test on demo account first!")
    print("  • Past performance ≠ future results")
    print("\nFiles created:")
    print("  • auto_trading_results.csv (trade-by-trade details)")
    print("  • auto_trading_performance.png (equity curve charts)")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
