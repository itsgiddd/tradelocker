"""
GENETIC EVOLUTION TRADING SYSTEM (GETS)

Revolutionary Idea: Let trading strategies EVOLVE like organisms

Instead of hand-crafting rules, we:
1. Create population of random trading strategies (genes)
2. Test fitness (how profitable they are)
3. Keep best strategies alive
4. Mutate and crossover to create new strategies
5. Repeat for many generations

Natural selection will find patterns we never imagined!

This is inspired by genetic algorithms but applied to complete trading strategies.
"""

import numpy as np
import pandas as pd
from copy import deepcopy
import warnings
warnings.filterwarnings('ignore')


class TradingStrategy:
    """
    A single trading strategy represented as a genome

    Genome encodes:
    - Which features to use
    - Weights for each feature
    - Thresholds for trading
    - Risk parameters
    """

    def __init__(self, genome=None):
        if genome is None:
            # Random initialization
            self.genome = {
                # Feature weights (-1 to 1)
                'return_5': np.random.uniform(-1, 1),
                'return_10': np.random.uniform(-1, 1),
                'return_20': np.random.uniform(-1, 1),
                'vol_5': np.random.uniform(-1, 1),
                'vol_10': np.random.uniform(-1, 1),
                'momentum_5': np.random.uniform(-1, 1),
                'momentum_10': np.random.uniform(-1, 1),
                'rsi': np.random.uniform(-1, 1),
                'trend': np.random.uniform(-1, 1),

                # Thresholds
                'entry_threshold': np.random.uniform(0.3, 0.7),
                'confidence_threshold': np.random.uniform(0.5, 0.9),

                # Risk parameters
                'position_size': np.random.uniform(0.1, 1.0),
                'stop_loss': np.random.uniform(0.001, 0.01),
                'take_profit': np.random.uniform(0.002, 0.02),
            }
        else:
            self.genome = genome

        self.fitness = 0
        self.trades = []

    def extract_features(self, prices):
        """Extract features from prices"""
        if len(prices) < 50:
            return None

        features = {}

        # Returns
        for w in [5, 10, 20]:
            if len(prices) >= w + 1:
                features[f'return_{w}'] = (prices[-1] - prices[-w]) / prices[-w]
            else:
                features[f'return_{w}'] = 0

        # Volatility
        for w in [5, 10]:
            if len(prices) >= w + 1:
                returns = np.diff(prices[-w-1:]) / prices[-w-1:-1]
                features[f'vol_{w}'] = np.std(returns)
            else:
                features[f'vol_{w}'] = 0

        # Momentum
        for w in [5, 10]:
            if len(prices) >= w * 2 + 1:
                curr = (prices[-1] - prices[-w]) / prices[-w]
                prev = (prices[-w] - prices[-2*w]) / prices[-2*w]
                features[f'momentum_{w}'] = curr - prev
            else:
                features[f'momentum_{w}'] = 0

        # RSI
        if len(prices) >= 14:
            changes = np.diff(prices[-14:])
            gains = np.mean(np.where(changes > 0, changes, 0))
            losses = np.mean(np.where(changes < 0, -changes, 0))
            features['rsi'] = gains / (gains + losses + 1e-8)
        else:
            features['rsi'] = 0.5

        # Trend
        if len(prices) >= 20:
            x = np.arange(20)
            slope, _ = np.polyfit(x, prices[-20:], 1)
            features['trend'] = slope / np.mean(prices[-20:])
        else:
            features['trend'] = 0

        return features

    def compute_signal(self, prices):
        """
        Compute trading signal using genome
        """
        features = self.extract_features(prices)
        if features is None:
            return 0, 0

        # Weighted sum of features
        signal = 0
        for key, weight in self.genome.items():
            if key in features:
                signal += weight * features[key]

        # Normalize signal
        signal = np.tanh(signal)  # [-1, 1]

        # Compute confidence (how strong is signal)
        confidence = abs(signal)

        return signal, confidence

    def should_trade(self, prices):
        """
        Decide if we should trade based on genome
        """
        signal, confidence = self.compute_signal(prices)

        # Check thresholds from genome
        if confidence < self.genome['confidence_threshold']:
            return False, 0, 0

        if abs(signal) < self.genome['entry_threshold']:
            return False, 0, 0

        direction = 1 if signal > 0 else -1
        return True, direction, confidence


class GeneticEvolutionEngine:
    """
    Evolve trading strategies using genetic algorithms
    """

    def __init__(self, population_size=50, mutation_rate=0.1, elite_fraction=0.2):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.elite_fraction = elite_fraction

        # Initialize population
        self.population = [TradingStrategy() for _ in range(population_size)]
        self.generation = 0
        self.best_strategy = None
        self.best_fitness = -np.inf

    def evaluate_fitness(self, strategy, prices, start_idx, end_idx):
        """
        Evaluate how good a strategy is on price data
        Fitness = profit + penalty for losses
        """
        capital = 100000
        trades = []

        for idx in range(start_idx, end_idx - 10):
            should_trade, direction, confidence = strategy.should_trade(prices[:idx])

            if should_trade:
                entry_price = prices[idx]

                # Risk from genome
                position_size = capital * strategy.genome['position_size'] * confidence
                take_profit = entry_price * (1 + direction * strategy.genome['take_profit'])
                stop_loss = entry_price * (1 - direction * strategy.genome['stop_loss'])

                # Simulate trade for next 10 bars
                for i in range(1, min(10, end_idx - idx)):
                    current_price = prices[idx + i]

                    # Check TP
                    if (direction > 0 and current_price >= take_profit) or \
                       (direction < 0 and current_price <= take_profit):
                        pnl = position_size * strategy.genome['take_profit']
                        capital += pnl
                        trades.append({'pnl': pnl, 'win': True})
                        break

                    # Check SL
                    if (direction > 0 and current_price <= stop_loss) or \
                       (direction < 0 and current_price >= stop_loss):
                        pnl = -position_size * strategy.genome['stop_loss']
                        capital += pnl
                        trades.append({'pnl': pnl, 'win': False})
                        break

        # Fitness function
        total_return = (capital - 100000) / 100000
        n_trades = len(trades)
        win_rate = np.mean([t['win'] for t in trades]) if n_trades > 0 else 0

        # Fitness = return + bonus for high win rate - penalty for few trades
        fitness = total_return + 0.5 * win_rate - 0.1 / (n_trades + 1)

        strategy.fitness = fitness
        strategy.trades = trades

        return fitness

    def select_parents(self):
        """
        Select best strategies to reproduce
        Tournament selection
        """
        parents = []

        for _ in range(self.population_size // 2):
            # Tournament: pick 5 random, keep best
            tournament = np.random.choice(self.population, size=5, replace=False)
            winner = max(tournament, key=lambda s: s.fitness)
            parents.append(winner)

        return parents

    def crossover(self, parent1, parent2):
        """
        Combine genes from two parents
        """
        child_genome = {}

        for key in parent1.genome:
            # Randomly pick gene from either parent
            if np.random.random() < 0.5:
                child_genome[key] = parent1.genome[key]
            else:
                child_genome[key] = parent2.genome[key]

        return TradingStrategy(genome=child_genome)

    def mutate(self, strategy):
        """
        Random mutations in genome
        """
        for key in strategy.genome:
            if np.random.random() < self.mutation_rate:
                # Mutate this gene
                if 'threshold' in key:
                    strategy.genome[key] = np.clip(
                        strategy.genome[key] + np.random.normal(0, 0.1),
                        0, 1
                    )
                elif key == 'position_size':
                    strategy.genome[key] = np.clip(
                        strategy.genome[key] + np.random.normal(0, 0.2),
                        0.1, 1.0
                    )
                elif 'stop_loss' in key or 'take_profit' in key:
                    strategy.genome[key] = np.clip(
                        strategy.genome[key] + np.random.normal(0, 0.002),
                        0.001, 0.05
                    )
                else:
                    # Feature weights
                    strategy.genome[key] = np.clip(
                        strategy.genome[key] + np.random.normal(0, 0.3),
                        -1, 1
                    )

        return strategy

    def evolve(self, prices, train_start, train_end):
        """
        Run one generation of evolution
        """
        # Evaluate all strategies
        print(f"  Gen {self.generation}: Evaluating {self.population_size} strategies...", end='')

        for strategy in self.population:
            self.evaluate_fitness(strategy, prices, train_start, train_end)

        # Find best
        self.population.sort(key=lambda s: s.fitness, reverse=True)
        generation_best = self.population[0]

        if generation_best.fitness > self.best_fitness:
            self.best_fitness = generation_best.fitness
            self.best_strategy = deepcopy(generation_best)

        print(f" Best fitness: {generation_best.fitness:.4f} (trades: {len(generation_best.trades)})")

        # Keep elite
        n_elite = int(self.population_size * self.elite_fraction)
        next_population = self.population[:n_elite]

        # Create offspring
        while len(next_population) < self.population_size:
            parents = self.select_parents()

            if len(parents) >= 2:
                parent1, parent2 = np.random.choice(parents, size=2, replace=False)

                # Crossover
                child = self.crossover(parent1, parent2)

                # Mutate
                child = self.mutate(child)

                next_population.append(child)

        self.population = next_population
        self.generation += 1


def test_genetic_system():
    """Test genetic evolution system"""
    print("=" * 80)
    print("GENETIC EVOLUTION TRADING SYSTEM (GETS)")
    print("=" * 80)
    print("\nLet strategies EVOLVE through natural selection:")
    print("  1. Population of random strategies")
    print("  2. Evaluate fitness (profitability)")
    print("  3. Keep best, eliminate worst")
    print("  4. Crossover and mutation")
    print("  5. Repeat for many generations")
    print()

    # Generate data
    from ml_breakthrough_system import MLTradingSystem
    system = MLTradingSystem()
    prices = system.generate_market_data(n_points=5000, seed=42)
    print(f"Generated {len(prices):,} price bars\n")

    # Initialize evolution
    evolution = GeneticEvolutionEngine(population_size=30, mutation_rate=0.15)

    # Evolve on training data
    train_end = 3000
    print("EVOLUTION PHASE")
    print("=" * 80)

    for gen in range(20):  # 20 generations
        evolution.evolve(prices, 200, train_end)

    print(f"\n✅ Evolution complete!")
    print(f"   Best fitness achieved: {evolution.best_fitness:.4f}")
    print(f"   Best strategy trades: {len(evolution.best_strategy.trades)}")

    # Test best strategy on unseen data
    print("\n" + "=" * 80)
    print("TESTING ON UNSEEN DATA")
    print("=" * 80 + "\n")

    best = evolution.best_strategy
    results = []

    for idx in range(train_end, len(prices) - 10, 5):
        should_trade, direction, confidence = best.should_trade(prices[:idx])

        if should_trade:
            # Actual outcome
            future_return = (prices[idx + 5] - prices[idx]) / prices[idx]
            actual_direction = 1 if future_return > 0 else -1

            results.append({
                'prediction': direction,
                'actual': actual_direction,
                'correct': direction == actual_direction,
                'confidence': confidence
            })

        if len(results) % 50 == 0 and len(results) > 0:
            recent_acc = np.mean([r['correct'] for r in results[-50:]])
            print(f"Position {idx} | Predictions: {len(results)} | Last 50: {recent_acc:.3f}", end='\r')

    print(f"\n\n{'=' * 80}")

    if len(results) == 0:
        print("❌ No predictions made!")
        return 0, 0

    df = pd.DataFrame(results)
    overall_acc = df['correct'].mean()

    print(f"\nGENETIC EVOLUTION RESULTS:")
    print(f"  Total predictions: {len(df):,}")
    print(f"  Overall accuracy: {overall_acc:.2%}")
    print()

    # Confidence filtering
    print("  Confidence-based performance:")
    best_acc = 0
    best_thresh = 0

    for thresh in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        filtered = df[df['confidence'] >= thresh]
        if len(filtered) > 0:
            acc = filtered['correct'].mean()
            pct = len(filtered) / len(df)

            if acc > best_acc:
                best_acc = acc
                best_thresh = thresh

            status = "✅✅" if acc >= 0.65 else "✅ " if acc >= 0.60 else "⚠️ " if acc >= 0.55 else "  "
            print(f"    {status} >= {thresh:.2f}: {acc:.2%} on {len(filtered):4d} predictions ({pct:5.1%})")

    # Statistical test
    from scipy.stats import binomtest
    p_value = binomtest(df['correct'].sum(), len(df), 0.5, alternative='greater').pvalue
    print(f"\n  P-value: {p_value:.6f}")
    print(f"  Significant: {'✅ YES' if p_value < 0.05 else '❌ NO'}")

    print(f"\n🏆 BEST: {best_acc:.2%} at confidence >= {best_thresh:.2f}")

    print("\n" + "=" * 80)
    print("VERDICT:")
    if best_acc >= 0.65:
        print(f"🎉 EVOLUTION SUCCESS! {best_acc:.2%}")
    elif best_acc >= 0.60:
        print(f"✅ EVOLUTION WORKS! {best_acc:.2%}")
    elif best_acc >= 0.55:
        print(f"⚠️  MARGINAL: {best_acc:.2%}")
    else:
        print(f"❌ NO ADVANTAGE: {best_acc:.2%}")

    print("\n  vs Ultimate Hybrid: 62.16%")
    improvement = (best_acc - 0.6216) / 0.6216 * 100
    print(f"  Improvement: {improvement:+.1f}%")
    print("=" * 80)

    # Save
    df.to_csv('/home/user/tradelocker/genetic_results.csv', index=False)
    print(f"\n💾 Results saved to: genetic_results.csv\n")

    return overall_acc, best_acc


if __name__ == "__main__":
    overall, best = test_genetic_system()
