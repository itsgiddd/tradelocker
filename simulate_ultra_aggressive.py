"""
ULTRA AGGRESSIVE SIMULATION
Target: 50% daily returns

Settings:
- 20% risk per trade (10× normal)
- 50% confidence threshold (vs 75% normal)
- Aggressive compounding

Let's see what happens...
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from ultra_aggressive_system import UltraAggressiveSystem
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


class UltraAggressiveSimulator:
    """Ultra aggressive simulator - targeting 50% daily"""

    def __init__(self, starting_balance=10000, risk_percent=20.0, confidence_threshold=0.50):
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.equity = starting_balance
        self.risk_percent = risk_percent
        self.confidence_threshold = confidence_threshold

        self.system = UltraAggressiveSystem()

        self.trades = []
        self.equity_curve = []
        self.balance_curve = []
        self.dates = []
        self.daily_returns = []

        self.open_position = None
        self.account_blown = False
        self.blow_up_bar = None

    def run_backtest(self, data):
        """Run ultra aggressive backtest"""
        dates = data['dates']
        opens = data['open']
        highs = data['high']
        lows = data['low']
        closes = data['close']

        print("="*80)
        print("🔥 ULTRA AGGRESSIVE SIMULATION 🔥")
        print("="*80)
        print(f"\nStarting Balance: ${self.starting_balance:,.2f}")
        print(f"Risk per Trade: {self.risk_percent}% (10× NORMAL!)")
        print(f"Confidence Threshold: {self.confidence_threshold:.0%} (VERY LOW!)")
        print(f"\n⚠️  WARNING: Targeting 50% DAILY returns - EXTREMELY RISKY!")
        print(f"📉 High probability of account blow-up")
        print(f"\nSimulation Period: {dates[0]} to {dates[-1]}")
        print(f"Total Bars: {len(closes):,}")
        print("\n" + "="*80)
        print("STARTING ULTRA AGGRESSIVE TRADING...")
        print("="*80 + "\n")

        # Train
        train_end = 2000
        print(f"Training system on first {train_end} bars...")
        if not self.system.train(closes, 200, train_end):
            print("Training failed!")
            return
        print("\n")

        last_day_balance = self.starting_balance
        current_day = dates[train_end].date()

        # Run bar by bar
        for i in range(train_end, len(closes)):
            current_date = dates[i]

            # Check for day change
            if current_date.date() != current_day:
                daily_return = ((self.balance - last_day_balance) / last_day_balance * 100)
                self.daily_returns.append({
                    'date': current_day,
                    'return_pct': daily_return,
                    'balance': self.balance
                })

                if daily_return != 0:
                    print(f"\n📅 Day {current_day}: {daily_return:+.1f}% | Balance: ${self.balance:,.2f}")

                last_day_balance = self.balance
                current_day = current_date.date()

            # Check if account blown
            if self.balance < self.starting_balance * 0.1:  # Lost 90%
                if not self.account_blown:
                    self.account_blown = True
                    self.blow_up_bar = i
                    print(f"\n{'='*80}")
                    print(f"💥 ACCOUNT BLOWN! Lost 90% of capital!")
                    print(f"{'='*80}")
                    print(f"Date: {current_date}")
                    print(f"Final Balance: ${self.balance:,.2f}")
                    print(f"Loss: ${self.starting_balance - self.balance:,.2f}")
                    print(f"Days Survived: {(current_date - dates[train_end]).days}")
                    print(f"{'='*80}\n")
                    break

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
        print("🔥 ULTRA AGGRESSIVE SIMULATION COMPLETE!")
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

        print(f"\n⚡ TRADE #{len(self.trades) + 1} | {signal.direction} | Conf: {signal.confidence*100:.0f}% | Risk: ${risk_amount:.0f} ({self.risk_percent}%)")

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

        # Check stop loss
        if pos['direction'] == "LONG":
            if current_low <= pos['stop_loss']:
                self.close_trade(bar_idx, pos['stop_loss'], "Stop Loss")
                return
        else:
            if current_high >= pos['stop_loss']:
                self.close_trade(bar_idx, pos['stop_loss'], "Stop Loss")
                return

        # Check take profit
        if pos['direction'] == "LONG":
            if current_high >= pos['take_profit']:
                self.close_trade(bar_idx, pos['take_profit'], "Take Profit")
                return
        else:
            if current_low <= pos['take_profit']:
                self.close_trade(bar_idx, pos['take_profit'], "Take Profit")
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
            'bars_held': bar_idx - pos['entry_bar'],
            'reason': reason,
            'is_winner': is_winner,
            'balance_after': self.balance
        }

        self.trades.append(trade_record)

        status = "✅" if is_winner else "❌"
        print(f"{status} ${pnl:+,.0f} ({pnl_pct:+.0f}%) | Bal: ${self.balance:,.2f}")

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

        # Daily stats
        if len(self.daily_returns) > 0:
            daily_df = pd.DataFrame(self.daily_returns)
            avg_daily = daily_df['return_pct'].mean()
            best_day = daily_df['return_pct'].max()
            worst_day = daily_df['return_pct'].min()
            days_traded = len(daily_df)
        else:
            avg_daily = 0
            best_day = 0
            worst_day = 0
            days_traded = 0

        print("="*80)
        print("🔥 ULTRA AGGRESSIVE RESULTS")
        print("="*80)
        print()
        print("💰 ACCOUNT PERFORMANCE:")
        print(f"   Starting Balance:  ${self.starting_balance:,.2f}")
        print(f"   Ending Balance:    ${ending_balance:,.2f}")
        print(f"   Total Profit:      ${net_profit:+,.2f}")
        print(f"   ROI:               {roi:+.2f}%")
        print()

        if self.account_blown:
            print("💥 ACCOUNT STATUS:     BLOWN (Lost 90%+)")
            print(f"   Days Survived:      {days_traded}")
            print()

        print("📊 DAILY RETURNS:")
        print(f"   Days Traded:       {days_traded}")
        print(f"   Average Daily:     {avg_daily:+.2f}%")
        print(f"   Best Day:          {best_day:+.2f}%")
        print(f"   Worst Day:         {worst_day:+.2f}%")
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
        print()
        print("="*80)

        # Save results
        df.to_csv('ultra_aggressive_results.csv', index=False)
        if len(self.daily_returns) > 0:
            daily_df.to_csv('ultra_aggressive_daily.csv', index=False)
        print("\n✅ Results saved to: ultra_aggressive_results.csv")

    def plot_results(self):
        """Plot equity curve"""
        if len(self.equity_curve) == 0:
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # Equity curve
        ax1.plot(self.dates, self.equity_curve, linewidth=2, color='#ff1744', label='Equity')
        ax1.plot(self.dates, self.balance_curve, linewidth=2, color='#ffd700', alpha=0.7, label='Balance')
        ax1.axhline(y=self.starting_balance, color='gray', linestyle='--', alpha=0.5, label='Starting Balance')

        if self.account_blown and self.blow_up_bar:
            ax1.axvline(x=self.dates[self.blow_up_bar - 2000], color='red', linestyle='--', linewidth=2, label='Account Blown')

        ax1.set_title('🔥 Ultra Aggressive - Account Growth', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Balance ($)', fontsize=12)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)

        # Daily returns
        if len(self.daily_returns) > 0:
            daily_df = pd.DataFrame(self.daily_returns)
            colors = ['green' if x > 0 else 'red' for x in daily_df['return_pct']]
            ax2.bar(range(len(daily_df)), daily_df['return_pct'], color=colors, alpha=0.6)
            ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax2.axhline(y=50, color='green', linestyle='--', linewidth=1, alpha=0.5, label='50% Target')
            ax2.set_title('Daily Returns (%)', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Day', fontsize=12)
            ax2.set_ylabel('Return (%)', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('ultra_aggressive_performance.png', dpi=300, bbox_inches='tight')
        print("✅ Chart saved to: ultra_aggressive_performance.png\n")


if __name__ == "__main__":
    # Generate data
    print("Generating realistic market data...")
    data = generate_realistic_forex_data(n_points=5000, seed=42)
    print(f"Generated {len(data['close']):,} bars (H1 timeframe)")
    print()

    # Create simulator with ULTRA AGGRESSIVE settings
    simulator = UltraAggressiveSimulator(
        starting_balance=10000,
        risk_percent=20.0,      # 20% risk per trade (10× normal!)
        confidence_threshold=0.50  # 50% confidence (vs 75% normal)
    )

    # Run backtest
    simulator.run_backtest(data)

    print("\n" + "="*80)
    print("🎯 ULTRA AGGRESSIVE SIMULATION COMPLETE!")
    print("="*80)
