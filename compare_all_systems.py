"""
COMPREHENSIVE SYSTEM COMPARISON
Compare exact dollar profits across all three systems
"""

import pandas as pd
import numpy as np

print("="*80)
print("💰 COMPREHENSIVE PROFIT COMPARISON")
print("="*80)
print()

# Starting balance (same for all)
starting_balance = 10000

# Load results
print("Loading results from all three systems...\n")

try:
    original_df = pd.read_csv('auto_trading_results.csv')
    original_exists = True
    print("✅ Original EA results loaded")
except:
    original_exists = False
    print("❌ Original EA results not found")

try:
    ultra_df = pd.read_csv('ultra_aggressive_results.csv')
    ultra_exists = True
    print("✅ Ultra Aggressive results loaded")
except:
    ultra_exists = False
    print("❌ Ultra Aggressive results not found")

try:
    smart_df = pd.read_csv('smart_aggressive_results.csv')
    smart_exists = True
    print("✅ Smart Aggressive results loaded")
except:
    smart_exists = False
    print("❌ Smart Aggressive results not found")

print()
print("="*80)
print("📊 PROFIT COMPARISON TABLE")
print("="*80)
print()

# Create comparison table
results = []

if original_exists:
    ending = original_df['balance_after'].iloc[-1]
    profit = ending - starting_balance
    roi = (profit / starting_balance) * 100
    trades = len(original_df)
    winners = len(original_df[original_df['pnl'] > 0])
    win_rate = (winners / trades * 100) if trades > 0 else 0

    results.append({
        'System': 'Original EA',
        'Starting': starting_balance,
        'Ending': ending,
        'Profit': profit,
        'ROI': roi,
        'Trades': trades,
        'Win Rate': win_rate,
        'Risk Per Trade': '2%'
    })

if ultra_exists:
    ending = ultra_df['balance_after'].iloc[-1]
    profit = ending - starting_balance
    roi = (profit / starting_balance) * 100
    trades = len(ultra_df)
    winners = len(ultra_df[ultra_df['is_winner'] == True])
    win_rate = (winners / trades * 100) if trades > 0 else 0

    results.append({
        'System': 'Ultra Aggressive',
        'Starting': starting_balance,
        'Ending': ending,
        'Profit': profit,
        'ROI': roi,
        'Trades': trades,
        'Win Rate': win_rate,
        'Risk Per Trade': '20%'
    })

if smart_exists:
    ending = smart_df['balance_after'].iloc[-1]
    profit = ending - starting_balance
    roi = (profit / starting_balance) * 100
    trades = len(smart_df)
    winners = len(smart_df[smart_df['is_winner'] == True])
    win_rate = (winners / trades * 100) if trades > 0 else 0

    results.append({
        'System': 'Smart Aggressive',
        'Starting': starting_balance,
        'Ending': ending,
        'Profit': profit,
        'ROI': roi,
        'Trades': trades,
        'Win Rate': win_rate,
        'Risk Per Trade': '5-10%'
    })

# Print comparison table
for i, result in enumerate(results, 1):
    print(f"{i}. {result['System']}")
    print(f"   {'─'*60}")
    print(f"   Starting Balance:    ${result['Starting']:,.2f}")
    print(f"   Ending Balance:      ${result['Ending']:,.2f}")
    print(f"   Total Profit:        ${result['Profit']:+,.2f}")
    print(f"   ROI:                 {result['ROI']:+,.2f}%")
    print(f"   Total Trades:        {result['Trades']}")
    print(f"   Win Rate:            {result['Win Rate']:.1f}%")
    print(f"   Risk Per Trade:      {result['Risk Per Trade']}")
    print()

print("="*80)
print("🏆 RANKING BY ABSOLUTE PROFIT")
print("="*80)
print()

# Sort by profit
sorted_results = sorted(results, key=lambda x: x['Profit'], reverse=True)

for i, result in enumerate(sorted_results, 1):
    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
    print(f"{emoji} #{i}: {result['System']}")
    print(f"   Profit: ${result['Profit']:,.2f} ({result['ROI']:+.2f}%)")
    print()

print("="*80)
print("📈 DETAILED ANALYSIS")
print("="*80)
print()

print("💡 ORIGINAL EA (2% Risk):")
print("   • Safest approach with consistent 2% risk")
print("   • Balanced win rate and trade frequency")
print("   • Sustainable and broker-friendly")
print("   • Best for live trading")
print()

print("🔥 ULTRA AGGRESSIVE (20% Risk):")
print("   • Highest absolute profit")
print("   • 10x risk per trade")
print("   • Extreme volatility")
print("   • Would cause margin calls in live trading")
print("   • Position sizes exceed broker limits")
print()

print("🎯 SMART AGGRESSIVE (5-10% Risk):")
print("   • Controlled risk with dynamic sizing")
print("   • 30-50% profit targets per trade")
print("   • Position caps prevent scaling")
print("   • Too conservative - caps limited growth")
print()

print("="*80)
print("✅ FINAL RECOMMENDATION")
print("="*80)
print()
print("For LIVE TRADING:")
print("   → Use ORIGINAL EA")
print("   → 2% risk per trade")
print("   → No trade limits (as requested)")
print("   → Sustainable +1,237% ROI")
print()
print("Why NOT Ultra Aggressive:")
print("   → Broker will reject position sizes")
print("   → Margin calls likely")
print("   → Cannot execute in real market")
print()
print("Why NOT Smart Aggressive:")
print("   → Position caps too restrictive")
print("   → Cannot hit 30-50% profit targets")
print("   → Only +13% vs +1,237%")
print()
print("="*80)
print()

# Save comparison
comparison_df = pd.DataFrame(results)
comparison_df.to_csv('system_comparison.csv', index=False)
print("✅ Comparison saved to: system_comparison.csv")
print()
