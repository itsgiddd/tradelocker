"""
AEGFM-Ω Diagnostic - What confidence levels does it actually produce?
"""

import numpy as np
import pandas as pd
from scipy.special import erf
import matplotlib.pyplot as plt
from aegfm_full_implementation import (
    AEGFMOmega, PathSignature, EntropicFlowEngine
)

def diagnostic_run():
    """Run diagnostic to see what signals the framework actually generates"""
    print("=" * 70)
    print("AEGFM-Ω DIAGNOSTIC - Signal Quality Analysis")
    print("=" * 70)

    aegfm = AEGFMOmega(initial_capital=100000, leverage=10)

    print("\nGenerating market data...")
    prices = aegfm.generate_market_data(n_points=10000, regime_changes=True)
    print(f"Generated {len(prices):,} price bars\n")

    print("Scanning all signals to understand confidence distribution...\n")

    # Collect all signals
    signals = []
    lookback = 150

    for idx in range(lookback, len(prices) - 100, 50):  # Sample every 50 bars
        window = prices[max(0, idx - 100):idx]

        if len(window) < 50:
            continue

        try:
            confidence, E1, D_f, sig = aegfm.compute_confidence(prices[:idx])

            signals.append({
                'idx': idx,
                'confidence': confidence,
                'E1': E1,
                'D_f': D_f,
                'entropy_ok': E1 < 2.5,
                'fractal_ok': abs(D_f - 1.5) < 0.3,
                'confidence_ok': confidence >= 0.75,
                'all_pass': (E1 < 2.5) and (abs(D_f - 1.5) < 0.3) and (confidence >= 0.75)
            })
        except:
            continue

    df = pd.DataFrame(signals)

    print(f"Collected {len(df)} signal samples")
    print("\n" + "=" * 70)
    print("SIGNAL STATISTICS")
    print("=" * 70)

    print(f"\n📊 CONFIDENCE DISTRIBUTION:")
    print(f"   Mean:        {df['confidence'].mean():.4f}")
    print(f"   Median:      {df['confidence'].median():.4f}")
    print(f"   Std:         {df['confidence'].std():.4f}")
    print(f"   Min:         {df['confidence'].min():.4f}")
    print(f"   Max:         {df['confidence'].max():.4f}")
    print(f"   25th pctl:   {df['confidence'].quantile(0.25):.4f}")
    print(f"   75th pctl:   {df['confidence'].quantile(0.75):.4f}")
    print(f"   95th pctl:   {df['confidence'].quantile(0.95):.4f}")
    print(f"   99th pctl:   {df['confidence'].quantile(0.99):.4f}")

    print(f"\n📊 ENTROPY (E₁):")
    print(f"   Mean:        {df['E1'].mean():.4f}")
    print(f"   Threshold:   2.5")
    print(f"   % Passing:   {df['entropy_ok'].mean():.2%}")

    print(f"\n📊 FRACTAL DIMENSION (D_f):")
    print(f"   Mean:        {df['D_f'].mean():.4f}")
    print(f"   Target:      1.5 ± 0.3")
    print(f"   % Passing:   {df['fractal_ok'].mean():.2%}")

    print(f"\n📊 FILTER PASS RATES:")
    print(f"   Confidence >= 0.75:  {df['confidence_ok'].mean():.2%}")
    print(f"   E₁ < 2.5:            {df['entropy_ok'].mean():.2%}")
    print(f"   |D_f - 1.5| < 0.3:   {df['fractal_ok'].mean():.2%}")
    print(f"   ALL THREE:           {df['all_pass'].mean():.2%}")

    # Find viable threshold
    print(f"\n🔍 VIABLE THRESHOLD ANALYSIS:")
    for threshold in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        viable = df[df['confidence'] >= threshold]
        if len(viable) > 0:
            pass_rate = len(viable) / len(df)
            print(f"   Confidence >= {threshold:.2f}:  {pass_rate:>6.2%} of signals "
                  f"({len(viable):>4d} signals)")

    # Now run with adjusted threshold
    print(f"\n{'=' * 70}")
    print("RUNNING BACKTEST WITH ADJUSTED THRESHOLD")
    print("=" * 70)

    # Find the 25th percentile confidence to get enough trades
    adjusted_threshold = max(0.50, df['confidence'].quantile(0.75))
    print(f"\nUsing adjusted confidence threshold: {adjusted_threshold:.3f}")
    print(f"(This should capture top 25% of signals)\n")

    # Modify AEGFM instance
    aegfm.confidence_threshold = adjusted_threshold

    # Run backtest
    trade_count = 0
    current_idx = lookback
    aegfm.trades = []
    aegfm.equity_curve = [aegfm.initial_capital]
    aegfm.capital = aegfm.initial_capital

    while trade_count < 1000 and current_idx < len(prices) - 200:
        try:
            confidence, E1, D_f, sig = aegfm.compute_confidence(prices[:current_idx])
        except:
            current_idx += 1
            continue

        # Check filters
        if E1 < 2.5 and abs(D_f - 1.5) < 0.3 and confidence >= adjusted_threshold:
            # Predict
            pred_price = aegfm.predict_next_price(prices[:current_idx])
            current_price = prices[current_idx]

            # Direction
            if pred_price > current_price * 1.001:
                direction = 1
            elif pred_price < current_price * 0.999:
                direction = -1
            else:
                current_idx += 1
                continue

            # Execute
            result = aegfm.execute_trade(prices, current_idx, direction, confidence)

            aegfm.trades.append({
                'trade_num': trade_count + 1,
                'entry_idx': current_idx,
                'direction': 'LONG' if direction > 0 else 'SHORT',
                'confidence': confidence,
                'E1': E1,
                'D_f': D_f,
                **result
            })

            aegfm.equity_curve.append(aegfm.capital)
            trade_count += 1

            if trade_count % 100 == 0:
                wr = np.mean([t['win'] for t in aegfm.trades])
                print(f"Trade {trade_count:4d} | Capital: ${aegfm.capital:>12,.0f} | "
                      f"WinRate: {wr:>5.1%}")

            current_idx = result['exit_idx'] + 5
        else:
            current_idx += 1

    if len(aegfm.trades) > 0:
        print(f"\n{'=' * 70}")
        results = aegfm.analyze_results()

        # Save
        results.to_csv('/home/user/tradelocker/aegfm_adjusted_results.csv', index=False)
        print(f"\n💾 Results saved")
    else:
        print(f"\n❌ Still no trades generated even with adjusted threshold!")
        print("This suggests fundamental issues with the framework's signal generation.")

    # Create diagnostic plots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # Confidence histogram
    axes[0, 0].hist(df['confidence'], bins=50, alpha=0.7, color='steelblue', edgecolor='black')
    axes[0, 0].axvline(x=0.75, color='red', linestyle='--', linewidth=2, label='Paper threshold (0.75)')
    axes[0, 0].axvline(x=df['confidence'].mean(), color='green', linestyle='-', linewidth=2, label='Mean')
    axes[0, 0].set_title('Confidence Distribution')
    axes[0, 0].set_xlabel('Confidence')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # E1 histogram
    axes[0, 1].hist(df['E1'], bins=50, alpha=0.7, color='orange', edgecolor='black')
    axes[0, 1].axvline(x=2.5, color='red', linestyle='--', linewidth=2, label='Threshold (2.5)')
    axes[0, 1].axvline(x=df['E1'].mean(), color='green', linestyle='-', linewidth=2, label='Mean')
    axes[0, 1].set_title('Entropy (E₁) Distribution')
    axes[0, 1].set_xlabel('E₁')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # D_f histogram
    axes[1, 0].hist(df['D_f'], bins=50, alpha=0.7, color='purple', edgecolor='black')
    axes[1, 0].axvline(x=1.5, color='green', linestyle='-', linewidth=2, label='Target (1.5)')
    axes[1, 0].axvspan(1.2, 1.8, alpha=0.2, color='green', label='Valid range')
    axes[1, 0].set_title('Fractal Dimension Distribution')
    axes[1, 0].set_xlabel('D_f')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # Scatter: Confidence vs E1
    axes[1, 1].scatter(df['E1'], df['confidence'], alpha=0.5, s=20)
    axes[1, 1].axhline(y=0.75, color='red', linestyle='--', label='Conf threshold')
    axes[1, 1].axvline(x=2.5, color='orange', linestyle='--', label='E₁ threshold')
    axes[1, 1].set_title('Confidence vs Entropy')
    axes[1, 1].set_xlabel('E₁')
    axes[1, 1].set_ylabel('Confidence')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/tradelocker/aegfm_diagnostic.png', dpi=150, bbox_inches='tight')
    print(f"📊 Diagnostic plots saved\n")


if __name__ == "__main__":
    diagnostic_run()
