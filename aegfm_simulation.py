"""
AEGFM-Ω Trading Framework Simulation
Tests the claimed 75-80% win rate over 1000+ trades
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import erf
import matplotlib.pyplot as plt
from collections import defaultdict

class AEGFMSimulator:
    def __init__(self, initial_capital=100000, leverage=10, target_trades=1000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.leverage = leverage
        self.target_trades = target_trades

        # Parameters from the paper
        self.confidence_threshold = 0.75
        self.entropy_threshold = 2.5
        self.fractal_range = (1.2, 1.8)  # |D_f - 1.5| < 0.3
        self.target_return = 0.004  # 0.4% per trade
        self.stop_loss = 0.002  # 0.2%

        # Results tracking
        self.trades = []
        self.equity_curve = [initial_capital]

    def generate_realistic_price_data(self, n_points=50000):
        """Generate realistic price data with trends, mean reversion, and noise"""
        np.random.seed(42)

        # Start with geometric brownian motion
        dt = 1/252/390  # 1-minute bars
        mu = 0.0001  # Slight drift
        sigma = 0.02  # Realistic volatility

        returns = np.random.normal(mu * dt, sigma * np.sqrt(dt), n_points)

        # Add regime changes (trends and mean reversion)
        regime_length = 500
        for i in range(0, n_points, regime_length):
            regime = np.random.choice(['trend', 'mean_revert', 'random'], p=[0.3, 0.3, 0.4])
            end = min(i + regime_length, n_points)

            if regime == 'trend':
                trend = np.random.choice([-1, 1]) * 0.0003
                returns[i:end] += trend
            elif regime == 'mean_revert':
                returns[i:end] *= 0.5  # Lower volatility

        # Add occasional jumps (news events)
        n_jumps = 50
        jump_indices = np.random.choice(n_points, n_jumps, replace=False)
        jump_sizes = np.random.normal(0, 0.01, n_jumps)
        returns[jump_indices] += jump_sizes

        # Convert to prices
        prices = 100 * np.exp(np.cumsum(returns))

        return prices

    def compute_entropy(self, window):
        """Compute Shannon entropy of price distribution"""
        # Discretize prices into bins
        hist, _ = np.histogram(window, bins=20, density=True)
        hist = hist[hist > 0]  # Remove zero bins
        entropy = -np.sum(hist * np.log(hist + 1e-10))
        return entropy

    def compute_fractal_dimension(self, window):
        """Estimate fractal dimension using box-counting method"""
        # Simplified Higuchi fractal dimension
        N = len(window)
        k_max = min(10, N // 4)

        L = []
        for k in range(1, k_max):
            Lk = 0
            for m in range(k):
                indices = range(m, N, k)
                if len(indices) < 2:
                    continue
                subset = window[list(indices)]
                length = np.sum(np.abs(np.diff(subset)))
                normalization = (N - 1) / (len(indices) * k)
                Lk += length * normalization
            if Lk > 0:
                L.append(Lk / k)

        if len(L) < 2:
            return 1.5  # Default

        # Fit log-log relationship
        x = np.log(range(1, len(L) + 1))
        y = np.log(L)
        slope, _ = np.polyfit(x, y, 1)

        D_f = 2 - slope
        return max(1.0, min(2.0, D_f))  # Bound between 1 and 2

    def compute_momentum_score(self, window):
        """Compute momentum tensor eigenvalue (simplified)"""
        if len(window) < 3:
            return 0

        # First and second derivatives
        velocity = np.diff(window)
        acceleration = np.diff(velocity)

        # Momentum score based on consistent direction
        momentum = np.mean(velocity) / (np.std(velocity) + 1e-6)
        return momentum

    def compute_signature(self, window):
        """Simplified path signature (first 2 orders)"""
        # Order 0: constant
        sig0 = 1

        # Order 1: integral of path
        sig1 = np.sum(np.diff(window))

        # Order 2: iterated integral (simplified)
        diffs = np.diff(window)
        sig2 = 0
        for i in range(len(diffs)):
            sig2 += diffs[i] * np.sum(diffs[i+1:])

        return np.array([sig0, sig1, sig2])

    def compute_confidence(self, entropy, fractal_dim, momentum, signature):
        """Compute confidence score as per the paper"""
        # γ(t) = α₀ + Σ(αₖ·sigₖ) + β·(D_f-1.5)² + δ·ΔE₁
        alpha_0 = 0.0
        alpha_sig = 0.1
        beta = -2.0  # Penalize deviation from 1.5
        delta = -0.5  # Penalize high entropy

        gamma = (alpha_0 +
                alpha_sig * np.sum(np.abs(signature)) / 10 +
                beta * (fractal_dim - 1.5)**2 +
                delta * (entropy - 2.0))

        # Sigmoid
        confidence = 1 / (1 + np.exp(-gamma))

        # Multiply by momentum quality
        momentum_factor = np.tanh(np.abs(momentum))

        confidence *= momentum_factor

        return confidence

    def should_trade(self, entropy, fractal_dim, confidence):
        """Apply trading filters"""
        if confidence < self.confidence_threshold:
            return False, "Low confidence"

        if entropy > self.entropy_threshold:
            return False, "High entropy"

        if not (self.fractal_range[0] < fractal_dim < self.fractal_range[1]):
            return False, "Fractal dimension out of range"

        return True, "All conditions met"

    def execute_trade(self, prices, entry_idx, direction, confidence):
        """Simulate trade execution with realistic slippage"""
        entry_price = prices[entry_idx]

        # Add realistic slippage (0.01% - 0.05%)
        slippage = np.random.uniform(0.0001, 0.0005) * entry_price
        entry_price += slippage * direction

        # Calculate position size (Kelly fraction)
        kelly_fraction = (confidence - 0.5) / 2  # Simplified Kelly
        position_size = self.capital * self.leverage * kelly_fraction * 0.5  # Conservative

        # Track through bars until TP or SL hit
        take_profit = entry_price * (1 + direction * self.target_return)
        stop_loss = entry_price * (1 - direction * self.stop_loss)

        max_hold = 100  # Max 100 bars (~100 minutes)

        for i in range(1, min(max_hold, len(prices) - entry_idx)):
            current_price = prices[entry_idx + i]

            # Check take profit
            if direction > 0 and current_price >= take_profit:
                pnl = position_size * self.target_return
                return {
                    'exit_idx': entry_idx + i,
                    'exit_reason': 'TP',
                    'pnl': pnl,
                    'return': self.target_return,
                    'bars_held': i,
                    'win': True
                }
            elif direction < 0 and current_price <= take_profit:
                pnl = position_size * self.target_return
                return {
                    'exit_idx': entry_idx + i,
                    'exit_reason': 'TP',
                    'pnl': pnl,
                    'return': self.target_return,
                    'bars_held': i,
                    'win': True
                }

            # Check stop loss
            if direction > 0 and current_price <= stop_loss:
                pnl = -position_size * self.stop_loss
                return {
                    'exit_idx': entry_idx + i,
                    'exit_reason': 'SL',
                    'pnl': pnl,
                    'return': -self.stop_loss,
                    'bars_held': i,
                    'win': False
                }
            elif direction < 0 and current_price >= stop_loss:
                pnl = -position_size * self.stop_loss
                return {
                    'exit_idx': entry_idx + i,
                    'exit_reason': 'SL',
                    'pnl': pnl,
                    'return': -self.stop_loss,
                    'bars_held': i,
                    'win': False
                }

        # Timed out - exit at market
        exit_price = prices[min(entry_idx + max_hold, len(prices) - 1)]
        pnl_pct = direction * (exit_price - entry_price) / entry_price
        pnl = position_size * pnl_pct

        return {
            'exit_idx': entry_idx + max_hold,
            'exit_reason': 'Timeout',
            'pnl': pnl,
            'return': pnl_pct,
            'bars_held': max_hold,
            'win': pnl > 0
        }

    def run_simulation(self):
        """Run complete simulation"""
        print("=" * 60)
        print("AEGFM-Ω TRADING SIMULATION")
        print("=" * 60)
        print(f"Initial Capital: ${self.capital:,.0f}")
        print(f"Leverage: {self.leverage}x")
        print(f"Target Trades: {self.target_trades}")
        print(f"Confidence Threshold: {self.confidence_threshold}")
        print("\nGenerating market data...")

        prices = self.generate_realistic_price_data()
        print(f"Generated {len(prices):,} price bars")

        window_size = 50
        lookback = 100

        print("\nScanning for trading opportunities...\n")

        current_idx = lookback
        trade_count = 0
        signals_checked = 0

        while trade_count < self.target_trades and current_idx < len(prices) - 200:
            # Extract window for analysis
            window = prices[current_idx - window_size:current_idx]

            # Compute indicators
            entropy = self.compute_entropy(window)
            fractal_dim = self.compute_fractal_dimension(window)
            momentum = self.compute_momentum_score(window)
            signature = self.compute_signature(window)
            confidence = self.compute_confidence(entropy, fractal_dim, momentum, signature)

            signals_checked += 1

            # Check if we should trade
            should_trade, reason = self.should_trade(entropy, fractal_dim, confidence)

            if should_trade:
                # Determine direction from momentum
                direction = 1 if momentum > 0 else -1

                # Execute trade
                result = self.execute_trade(prices, current_idx, direction, confidence)

                # Update capital
                self.capital += result['pnl']
                self.equity_curve.append(self.capital)

                # Record trade
                trade_record = {
                    'trade_num': trade_count + 1,
                    'entry_idx': current_idx,
                    'direction': 'LONG' if direction > 0 else 'SHORT',
                    'confidence': confidence,
                    'entropy': entropy,
                    'fractal_dim': fractal_dim,
                    'momentum': momentum,
                    **result
                }
                self.trades.append(trade_record)

                trade_count += 1

                if trade_count % 100 == 0:
                    win_rate = np.mean([t['win'] for t in self.trades])
                    avg_return = np.mean([t['return'] for t in self.trades])
                    print(f"Trade {trade_count}: Capital=${self.capital:,.0f} | "
                          f"Win Rate={win_rate:.1%} | Avg Return={avg_return:.3%}")

                # Jump to exit to avoid overlapping trades
                current_idx = result['exit_idx'] + 10
            else:
                current_idx += 1

        print(f"\n{'=' * 60}")
        print(f"Checked {signals_checked:,} potential signals")
        print(f"Executed {trade_count} trades")
        print(f"Signal selectivity: {trade_count/signals_checked:.2%}")

        return self.analyze_results()

    def analyze_results(self):
        """Comprehensive results analysis"""
        df = pd.DataFrame(self.trades)

        print("\n" + "=" * 60)
        print("SIMULATION RESULTS")
        print("=" * 60)

        # Overall performance
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        wins = df[df['win'] == True]
        losses = df[df['win'] == False]

        print(f"\n📊 OVERALL PERFORMANCE:")
        print(f"   Final Capital:      ${self.capital:,.2f}")
        print(f"   Total Return:       {total_return:+.2%}")
        print(f"   Total P&L:          ${self.capital - self.initial_capital:+,.2f}")

        print(f"\n📈 WIN/LOSS STATISTICS:")
        print(f"   Total Trades:       {len(df)}")
        print(f"   Winning Trades:     {len(wins)} ({len(wins)/len(df):.1%})")
        print(f"   Losing Trades:      {len(losses)} ({len(losses)/len(df):.1%})")
        print(f"   Win Rate:           {len(wins)/len(df):.2%} (Target: 75%)")

        print(f"\n💰 RETURN STATISTICS:")
        print(f"   Average Return:     {df['return'].mean():.3%}")
        print(f"   Average Win:        {wins['return'].mean():.3%}")
        print(f"   Average Loss:       {losses['return'].mean():.3%}")
        print(f"   Best Trade:         {df['return'].max():.3%}")
        print(f"   Worst Trade:        {df['return'].min():.3%}")
        print(f"   Profit Factor:      {wins['pnl'].sum() / abs(losses['pnl'].sum()):.2f}")

        print(f"\n📉 RISK METRICS:")
        equity_series = pd.Series(self.equity_curve)
        drawdowns = (equity_series - equity_series.cummax()) / equity_series.cummax()
        max_drawdown = drawdowns.min()

        print(f"   Max Drawdown:       {max_drawdown:.2%}")
        print(f"   Std Dev of Returns: {df['return'].std():.3%}")

        # Sharpe ratio (assuming risk-free rate = 0)
        if df['return'].std() > 0:
            sharpe = df['return'].mean() / df['return'].std() * np.sqrt(252 * 390)  # Annualized
            print(f"   Sharpe Ratio:       {sharpe:.2f}")

        print(f"\n⏱️  TRADE DURATION:")
        print(f"   Avg Bars Held:      {df['bars_held'].mean():.1f}")
        print(f"   Min Hold:           {df['bars_held'].min()}")
        print(f"   Max Hold:           {df['bars_held'].max()}")

        print(f"\n🎯 CONFIDENCE ANALYSIS:")
        print(f"   Avg Confidence:     {df['confidence'].mean():.3f}")
        print(f"   Min Confidence:     {df['confidence'].min():.3f}")
        print(f"   Max Confidence:     {df['confidence'].max():.3f}")

        # Confidence vs Win Rate correlation
        high_conf = df[df['confidence'] > 0.80]
        if len(high_conf) > 0:
            print(f"   High Conf (>0.80) WR: {high_conf['win'].mean():.2%} ({len(high_conf)} trades)")

        print(f"\n🔬 EXIT REASONS:")
        exit_counts = df['exit_reason'].value_counts()
        for reason, count in exit_counts.items():
            print(f"   {reason:12s}: {count:4d} ({count/len(df):5.1%})")

        # Test the 50% daily claim
        print(f"\n💡 COMPOUND TESTING:")
        avg_return_per_trade = df['return'].mean()
        compound_100 = (1 + avg_return_per_trade) ** 100 - 1
        print(f"   Avg return/trade:   {avg_return_per_trade:.3%}")
        print(f"   (1 + r)^100 - 1:    {compound_100:.2%}")
        print(f"   Claimed target:     50.00%")
        print(f"   Achievement:        {compound_100/0.5:.1%} of target")

        print(f"\n{'=' * 60}")
        print("VERDICT:")
        print("=" * 60)

        win_rate = len(wins) / len(df)

        if win_rate >= 0.75:
            print("✅ Framework EXCEEDS claimed 75% win rate!")
        elif win_rate >= 0.70:
            print("⚠️  Framework achieves 70%+ but below 75% claim")
        elif win_rate >= 0.60:
            print("❌ Framework achieves 60%+ (good but not revolutionary)")
        elif win_rate >= 0.50:
            print("❌ Framework barely breaks even")
        else:
            print("❌ Framework LOSES money - below random")

        if total_return > 0:
            print(f"💵 Net profitable: +{total_return:.2%}")
        else:
            print(f"💸 Net unprofitable: {total_return:.2%}")

        return df


def main():
    """Run simulation"""
    simulator = AEGFMSimulator(
        initial_capital=100000,
        leverage=10,
        target_trades=1000
    )

    results = simulator.run_simulation()

    # Save results
    results.to_csv('/home/user/tradelocker/aegfm_results.csv', index=False)
    print(f"\n💾 Results saved to: aegfm_results.csv")

    # Create visualization
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # Equity curve
    axes[0, 0].plot(simulator.equity_curve)
    axes[0, 0].set_title('Equity Curve')
    axes[0, 0].set_xlabel('Trade Number')
    axes[0, 0].set_ylabel('Capital ($)')
    axes[0, 0].grid(True, alpha=0.3)

    # Return distribution
    axes[0, 1].hist(results['return'], bins=50, alpha=0.7, edgecolor='black')
    axes[0, 1].set_title('Return Distribution')
    axes[0, 1].set_xlabel('Return per Trade')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].axvline(x=0, color='red', linestyle='--', label='Break-even')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # Win rate over time (rolling 100 trades)
    rolling_wr = results['win'].rolling(window=100, min_periods=10).mean()
    axes[1, 0].plot(rolling_wr)
    axes[1, 0].axhline(y=0.75, color='green', linestyle='--', label='Target 75%')
    axes[1, 0].axhline(y=0.50, color='orange', linestyle='--', label='Random 50%')
    axes[1, 0].set_title('Rolling Win Rate (100 trades)')
    axes[1, 0].set_xlabel('Trade Number')
    axes[1, 0].set_ylabel('Win Rate')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].set_ylim(0.3, 0.9)

    # Confidence vs Outcome
    wins = results[results['win'] == True]
    losses = results[results['win'] == False]
    axes[1, 1].scatter(wins.index, wins['confidence'], alpha=0.5, s=20, c='green', label='Wins')
    axes[1, 1].scatter(losses.index, losses['confidence'], alpha=0.5, s=20, c='red', label='Losses')
    axes[1, 1].axhline(y=0.75, color='blue', linestyle='--', label='Threshold')
    axes[1, 1].set_title('Confidence Score vs Outcome')
    axes[1, 1].set_xlabel('Trade Number')
    axes[1, 1].set_ylabel('Confidence')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/tradelocker/aegfm_analysis.png', dpi=100, bbox_inches='tight')
    print(f"📊 Charts saved to: aegfm_analysis.png")
    print("\n✅ Simulation complete!")


if __name__ == "__main__":
    main()
