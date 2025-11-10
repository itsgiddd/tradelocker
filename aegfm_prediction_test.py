"""
AEGFM-Ω Pure Prediction Test
Ignore the broken filters - just test if predictions have directional accuracy
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from aegfm_full_implementation import AEGFMOmega

def test_prediction_accuracy():
    """Test if the prediction formula has any edge at all"""
    print("=" * 70)
    print("AEGFM-Ω PREDICTION ACCURACY TEST")
    print("=" * 70)
    print("\nThis test ignores the broken confidence/fractal filters")
    print("and just evaluates if predictions have directional accuracy.\n")

    aegfm = AEGFMOmega(initial_capital=100000, leverage=10)

    print("Generating market data...")
    prices = aegfm.generate_market_data(n_points=10000, regime_changes=True)
    print(f"Generated {len(prices):,} price bars\n")

    print("Testing prediction accuracy...\n")

    predictions = []
    lookback = 150
    errors = []

    for idx in range(lookback, len(prices) - 10, 10):  # Every 10 bars
        try:
            # Make prediction
            pred_price = aegfm.predict_next_price(prices[:idx])
            actual_price_future = prices[idx + 5]  # 5 bars ahead
            current_price = prices[idx]

            # Determine directions
            pred_direction = 1 if pred_price > current_price else -1
            actual_direction = 1 if actual_price_future > current_price else -1

            correct = (pred_direction == actual_direction)

            predictions.append({
                'idx': idx,
                'current_price': current_price,
                'predicted_price': pred_price,
                'actual_future_price': actual_price_future,
                'pred_direction': pred_direction,
                'actual_direction': actual_direction,
                'correct': correct,
                'pred_return': (pred_price - current_price) / current_price,
                'actual_return': (actual_price_future - current_price) / current_price
            })

            if len(predictions) % 100 == 0:
                print(f"  Collected {len(predictions)} predictions...", end='\r')

            if len(predictions) >= 1000:
                break

        except Exception as e:
            errors.append(str(e))
            if len(errors) < 5:  # Print first few errors
                print(f"  Error at idx {idx}: {e}")
            continue

    if len(errors) > 0:
        print(f"\n  Total errors: {len(errors)}")
        print(f"  Most common error: {max(set(errors), key=errors.count)}")

    df = pd.DataFrame(predictions)

    print(f"\nCollected {len(df)} predictions\n")

    if len(df) == 0:
        print("❌ No predictions generated! The prediction function is broken.\n")
        return

    print("=" * 70)
    print("PREDICTION RESULTS")
    print("=" * 70)

    accuracy = df['correct'].mean()
    print(f"\n🎯 DIRECTIONAL ACCURACY:")
    print(f"   Correct predictions:     {df['correct'].sum()} / {len(df)}")
    print(f"   Accuracy:                {accuracy:.2%}")
    print(f"   Random baseline:         50.00%")
    print(f"   Paper claims:            75-80%")

    print(f"\n📊 PREDICTION STATISTICS:")
    print(f"   Mean predicted return:   {df['pred_return'].mean():+.4%}")
    print(f"   Mean actual return:      {df['actual_return'].mean():+.4%}")
    print(f"   Pred return std:         {df['pred_return'].std():.4%}")
    print(f"   Actual return std:       {df['actual_return'].std():.4%}")

    # Test if better than random
    from scipy import stats as scipy_stats
    n = len(df)
    n_correct = df['correct'].sum()
    try:
        p_value = scipy_stats.binomtest(n_correct, n, 0.5, alternative='greater').pvalue
    except:
        # Fallback for older scipy
        p_value = scipy_stats.binom_test(n_correct, n, 0.5, alternative='greater')

    print(f"\n📈 STATISTICAL SIGNIFICANCE:")
    print(f"   Binomial test p-value:   {p_value:.4f}")
    if p_value < 0.05:
        print(f"   ✅ Significantly better than random (p < 0.05)")
    else:
        print(f"   ❌ NOT significantly better than random")

    # Now run actual backtest with NO FILTERS - just trade everything
    print(f"\n{'=' * 70}")
    print("RUNNING BACKTEST WITH NO FILTERS (1000 TRADES)")
    print("=" * 70)
    print("\nTrading every signal regardless of confidence/entropy/fractal...\n")

    aegfm.trades = []
    aegfm.equity_curve = [aegfm.initial_capital]
    aegfm.capital = aegfm.initial_capital

    trade_count = 0
    current_idx = lookback

    while trade_count < 1000 and current_idx < len(prices) - 200:
        try:
            # Just predict - no filters
            pred_price = aegfm.predict_next_price(prices[:current_idx])
            current_price = prices[current_idx]

            # Direction from prediction
            if pred_price > current_price * 1.0005:  # Tiny threshold to avoid churn
                direction = 1
            elif pred_price < current_price * 0.9995:
                direction = -1
            else:
                current_idx += 1
                continue

            # Execute trade
            result = aegfm.execute_trade(prices, current_idx, direction, confidence=0.5)

            aegfm.trades.append({
                'trade_num': trade_count + 1,
                'entry_idx': current_idx,
                'direction': 'LONG' if direction > 0 else 'SHORT',
                'confidence': 0.5,  # Dummy value
                'prediction': pred_price,
                'actual': current_price,
                **result
            })

            aegfm.equity_curve.append(aegfm.capital)
            trade_count += 1

            if trade_count % 100 == 0:
                wr = np.mean([t['win'] for t in aegfm.trades])
                avg_ret = np.mean([t['return'] for t in aegfm.trades])
                print(f"Trade {trade_count:4d} | Capital: ${aegfm.capital:>12,.0f} | "
                      f"WinRate: {wr:>5.1%} | AvgRet: {avg_ret:>+6.3%}")

            current_idx = result['exit_idx'] + 1

        except Exception as e:
            current_idx += 1
            continue

    print(f"\n{'=' * 70}")
    if len(aegfm.trades) > 0:
        results_df = aegfm.analyze_results()
        results_df.to_csv('/home/user/tradelocker/aegfm_nofilter_results.csv', index=False)
    else:
        print("❌ No trades generated!")

    # Visualize prediction accuracy
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # Accuracy over time
    window = 50
    rolling_acc = df['correct'].rolling(window=window, min_periods=10).mean()
    axes[0, 0].plot(rolling_acc, linewidth=2)
    axes[0, 0].axhline(y=0.5, color='orange', linestyle='--', linewidth=2, label='Random (50%)')
    axes[0, 0].axhline(y=0.75, color='green', linestyle='--', linewidth=2, label='Target (75%)')
    axes[0, 0].axhline(y=accuracy, color='red', linestyle='-', linewidth=2, label=f'Mean ({accuracy:.1%})')
    axes[0, 0].set_title(f'Rolling Prediction Accuracy ({window} samples)', fontweight='bold')
    axes[0, 0].set_xlabel('Prediction Number')
    axes[0, 0].set_ylabel('Accuracy')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].set_ylim(0.2, 1.0)

    # Predicted vs Actual returns
    axes[0, 1].scatter(df['pred_return'], df['actual_return'], alpha=0.5, s=20)
    axes[0, 1].plot([-0.02, 0.02], [-0.02, 0.02], 'r--', linewidth=2, label='Perfect prediction')
    axes[0, 1].set_title('Predicted vs Actual Returns', fontweight='bold')
    axes[0, 1].set_xlabel('Predicted Return')
    axes[0, 1].set_ylabel('Actual Return')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # Accuracy histogram
    axes[1, 0].bar(['Correct', 'Incorrect'],
                   [df['correct'].sum(), len(df) - df['correct'].sum()],
                   color=['green', 'red'], alpha=0.7, edgecolor='black')
    axes[1, 0].axhline(y=len(df)/2, color='orange', linestyle='--', linewidth=2, label='Random baseline')
    axes[1, 0].set_title('Prediction Outcomes', fontweight='bold')
    axes[1, 0].set_ylabel('Count')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3, axis='y')

    # If we have trades, show equity curve
    if len(aegfm.equity_curve) > 1:
        axes[1, 1].plot(aegfm.equity_curve, linewidth=2, color='steelblue')
        axes[1, 1].axhline(y=aegfm.initial_capital, color='gray', linestyle='--', linewidth=2, label='Initial')
        axes[1, 1].set_title('Equity Curve (No Filters)', fontweight='bold')
        axes[1, 1].set_xlabel('Trade Number')
        axes[1, 1].set_ylabel('Capital ($)')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
    else:
        axes[1, 1].text(0.5, 0.5, 'No trades executed', ha='center', va='center', fontsize=16)
        axes[1, 1].set_title('Equity Curve', fontweight='bold')

    plt.tight_layout()
    plt.savefig('/home/user/tradelocker/aegfm_prediction_test.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 Charts saved to: aegfm_prediction_test.png")

    print(f"\n{'=' * 70}")
    print("FINAL VERDICT")
    print("=" * 70)

    if accuracy >= 0.75:
        print("✅ Framework achieves 75%+ directional accuracy")
    elif accuracy >= 0.60:
        print(f"⚠️  Framework achieves {accuracy:.1%} (better than random, but not 75%)")
    elif accuracy >= 0.52 and p_value < 0.05:
        print(f"⚠️  Framework achieves {accuracy:.1%} (slight edge, statistically significant)")
    else:
        print(f"❌ Framework achieves {accuracy:.1%} (no meaningful edge)")

    print("\n🔬 KEY ISSUES IDENTIFIED:")
    print("   1. Confidence formula produces values ~8-17% (not 75%)")
    print("   2. Fractal dimension always ~2.0 (target 1.2-1.8)")
    print("   3. Filters make trading impossible")
    print(f"   4. Raw predictions: {accuracy:.1%} accuracy (not 75-80%)")
    print(f"\n❌ The AEGFM-Ω framework does NOT achieve its claimed performance.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    test_prediction_accuracy()
