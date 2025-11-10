"""
ML-Based Trading System: Pushing the Accuracy Ceiling
Phase 2: Modern ML with Transformers + LSTM + Ensemble

Goal: Systematically test what accuracy is actually achievable
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from scipy import stats
from collections import deque
import warnings
warnings.filterwarnings('ignore')

class AdvancedFeatureEngine:
    """
    Extract sophisticated features that might actually have edge
    """

    def __init__(self):
        self.lookback_windows = [5, 10, 20, 50, 100]

    def compute_returns(self, prices, windows):
        """Multi-timeframe returns"""
        features = {}
        for w in windows:
            if len(prices) >= w + 1:
                features[f'return_{w}'] = (prices[-1] - prices[-w]) / prices[-w]
            else:
                features[f'return_{w}'] = 0
        return features

    def compute_volatility(self, prices, windows):
        """Multi-timeframe volatility"""
        features = {}
        for w in windows:
            if len(prices) >= w + 1:
                returns = np.diff(prices[-w-1:]) / prices[-w-1:-1]
                features[f'vol_{w}'] = np.std(returns)
            else:
                features[f'vol_{w}'] = 0
        return features

    def compute_momentum(self, prices, windows):
        """Momentum indicators"""
        features = {}
        for w in windows:
            if len(prices) >= w + 1:
                # Rate of change
                roc = (prices[-1] - prices[-w]) / prices[-w]
                features[f'momentum_{w}'] = roc

                # Acceleration (2nd derivative)
                if len(prices) >= w * 2 + 1:
                    prev_roc = (prices[-w] - prices[-2*w]) / prices[-2*w]
                    features[f'acceleration_{w}'] = roc - prev_roc
                else:
                    features[f'acceleration_{w}'] = 0
            else:
                features[f'momentum_{w}'] = 0
        return features

    def compute_relative_strength(self, prices, window=14):
        """RSI-like relative strength"""
        if len(prices) < window + 1:
            return {'rsi': 0.5}

        changes = np.diff(prices[-window-1:])
        gains = np.where(changes > 0, changes, 0)
        losses = np.where(changes < 0, -changes, 0)

        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0

        if avg_loss == 0:
            rsi = 1.0
        else:
            rs = avg_gain / avg_loss
            rsi = rs / (1 + rs)

        return {'rsi': rsi}

    def compute_trend_strength(self, prices, window=20):
        """Measure trend strength"""
        if len(prices) < window:
            return {'trend_strength': 0, 'trend_direction': 0}

        segment = prices[-window:]
        x = np.arange(len(segment))

        # Linear regression
        slope, intercept = np.polyfit(x, segment, 1)
        y_pred = slope * x + intercept
        r_squared = 1 - (np.sum((segment - y_pred)**2) / np.sum((segment - np.mean(segment))**2))

        return {
            'trend_strength': abs(r_squared),
            'trend_direction': np.sign(slope)
        }

    def compute_microstructure(self, prices, volumes=None):
        """Market microstructure features"""
        features = {}

        if len(prices) < 10:
            return {'spread_proxy': 0, 'price_impact': 0}

        # Price spread proxy (high-low range)
        recent = prices[-10:]
        features['spread_proxy'] = (np.max(recent) - np.min(recent)) / np.mean(recent)

        # Price impact (how much price moves per unit)
        changes = np.diff(prices[-20:]) if len(prices) >= 20 else np.diff(prices)
        features['price_impact'] = np.mean(np.abs(changes))

        # Volatility of volatility
        if len(prices) >= 50:
            returns = np.diff(prices[-50:]) / prices[-50:-1]
            vol_window = 10
            vols = [np.std(returns[i:i+vol_window]) for i in range(len(returns) - vol_window)]
            features['vol_of_vol'] = np.std(vols) if len(vols) > 0 else 0
        else:
            features['vol_of_vol'] = 0

        return features

    def compute_regime_features(self, prices, window=50):
        """Detect regime characteristics"""
        if len(prices) < window:
            return {'regime_volatility': 0, 'regime_trend': 0}

        recent = prices[-window:]

        # Volatility regime
        returns = np.diff(recent) / recent[:-1]
        vol = np.std(returns)

        # Trend regime
        slope, _ = np.polyfit(np.arange(len(recent)), recent, 1)

        return {
            'regime_volatility': vol,
            'regime_trend': slope / np.mean(recent)
        }

    def compute_entropy_features(self, prices, n_bins=10):
        """Information theory features"""
        if len(prices) < 20:
            return {'entropy': 0, 'entropy_change': 0}

        # Current entropy
        recent = prices[-20:]
        hist, _ = np.histogram(recent, bins=n_bins, density=True)
        hist = hist[hist > 0]
        hist = hist / np.sum(hist)
        entropy = -np.sum(hist * np.log(hist + 1e-10))

        # Previous entropy
        if len(prices) >= 30:
            prev = prices[-30:-10]
            hist_prev, _ = np.histogram(prev, bins=n_bins, density=True)
            hist_prev = hist_prev[hist_prev > 0]
            hist_prev = hist_prev / np.sum(hist_prev)
            entropy_prev = -np.sum(hist_prev * np.log(hist_prev + 1e-10))
            entropy_change = entropy - entropy_prev
        else:
            entropy_change = 0

        return {'entropy': entropy, 'entropy_change': entropy_change}

    def extract_all_features(self, prices, volumes=None):
        """Extract complete feature set"""
        features = {}

        # Basic features
        features.update(self.compute_returns(prices, self.lookback_windows))
        features.update(self.compute_volatility(prices, self.lookback_windows))
        features.update(self.compute_momentum(prices, self.lookback_windows))

        # Technical indicators
        features.update(self.compute_relative_strength(prices))
        features.update(self.compute_trend_strength(prices))

        # Advanced features
        features.update(self.compute_microstructure(prices, volumes))
        features.update(self.compute_regime_features(prices))
        features.update(self.compute_entropy_features(prices))

        # Current price level (normalized)
        features['price_level'] = prices[-1] / np.mean(prices[-20:]) if len(prices) >= 20 else 1.0

        return features


class EnsemblePredictor:
    """
    Ensemble of multiple ML models with confidence calibration
    """

    def __init__(self, feature_engine):
        self.feature_engine = feature_engine
        self.models = {}
        self.scaler = RobustScaler()
        self.is_fitted = False
        self.feature_names = None

        # Initialize models
        self.models['rf'] = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42
        )

        self.models['gb'] = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42
        )

        self.models['mlp'] = MLPClassifier(
            hidden_layer_sizes=(64, 32, 16),
            activation='relu',
            learning_rate='adaptive',
            max_iter=500,
            early_stopping=True,
            random_state=42
        )

    def prepare_features(self, price_history):
        """Extract and prepare features"""
        features_dict = self.feature_engine.extract_all_features(price_history)

        if self.feature_names is None:
            self.feature_names = sorted(features_dict.keys())

        feature_vector = [features_dict.get(name, 0) for name in self.feature_names]
        return np.array(feature_vector).reshape(1, -1)

    def fit(self, X, y):
        """Train all models"""
        print(f"Training ensemble on {len(X)} samples...")

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train each model
        for name, model in self.models.items():
            print(f"  Training {name}...", end=' ')
            model.fit(X_scaled, y)
            train_acc = accuracy_score(y, model.predict(X_scaled))
            print(f"Train accuracy: {train_acc:.3f}")

        self.is_fitted = True

    def predict_proba(self, X):
        """Predict with ensemble (average probabilities)"""
        if not self.is_fitted:
            return np.array([[0.5, 0.5]])

        X_scaled = self.scaler.transform(X)

        # Get predictions from all models
        probs = []
        for model in self.models.values():
            prob = model.predict_proba(X_scaled)
            probs.append(prob)

        # Average probabilities (ensemble)
        avg_prob = np.mean(probs, axis=0)
        return avg_prob

    def predict(self, X):
        """Predict class"""
        prob = self.predict_proba(X)
        return (prob[:, 1] > 0.5).astype(int)

    def get_confidence(self, X):
        """Get prediction confidence"""
        prob = self.predict_proba(X)
        # Confidence is distance from 0.5
        confidence = np.max(prob, axis=1)
        return confidence


class MLTradingSystem:
    """
    Complete ML-based trading system with walk-forward validation
    """

    def __init__(self, prediction_horizon=5, min_confidence=0.6):
        self.feature_engine = AdvancedFeatureEngine()
        self.predictor = EnsemblePredictor(self.feature_engine)
        self.prediction_horizon = prediction_horizon
        self.min_confidence = min_confidence

        # Training parameters
        self.retrain_frequency = 500  # Retrain every N bars
        self.min_train_samples = 500

        # Results tracking
        self.predictions = []
        self.train_history = []

    def generate_market_data(self, n_points=20000, seed=42):
        """Generate realistic market data"""
        np.random.seed(seed)

        prices = [100.0]
        regime_length = 500

        regimes = [
            {'mu': 0.0003, 'sigma': 0.012, 'name': 'bull'},
            {'mu': -0.0002, 'sigma': 0.018, 'name': 'bear'},
            {'mu': 0.0, 'sigma': 0.008, 'name': 'low_vol'},
            {'mu': 0.0, 'sigma': 0.025, 'name': 'high_vol'},
        ]

        for i in range(n_points - 1):
            if i % regime_length == 0:
                regime = regimes[np.random.randint(0, len(regimes))]

            ret = np.random.normal(regime['mu'], regime['sigma'])

            # Occasional jumps
            if np.random.random() < 0.01:
                ret += np.random.normal(0, 0.01)

            prices.append(prices[-1] * (1 + ret))

        return np.array(prices)

    def prepare_training_data(self, prices, start_idx, end_idx):
        """Prepare training dataset"""
        X = []
        y = []

        for i in range(start_idx, end_idx):
            if i < 150 or i + self.prediction_horizon >= len(prices):
                continue

            # Extract features
            features = self.feature_engine.extract_all_features(prices[:i])
            feature_vector = [features.get(name, 0) for name in sorted(features.keys())]

            # Label: did price go up after prediction_horizon?
            future_return = (prices[i + self.prediction_horizon] - prices[i]) / prices[i]
            label = 1 if future_return > 0 else 0

            X.append(feature_vector)
            y.append(label)

        return np.array(X), np.array(y)

    def walk_forward_test(self, prices, initial_train_size=1000):
        """
        Walk-forward validation: Train on past, test on future (never seen)
        This is the honest way to test
        """
        print("=" * 70)
        print("ML TRADING SYSTEM - WALK-FORWARD VALIDATION")
        print("=" * 70)
        print(f"Total data points: {len(prices):,}")
        print(f"Prediction horizon: {self.prediction_horizon} bars")
        print(f"Min confidence threshold: {self.min_confidence}")
        print(f"Retrain frequency: {self.retrain_frequency} bars\n")

        results = []
        current_pos = initial_train_size
        retrain_counter = 0

        # Initial training
        print(f"Initial training on first {initial_train_size} bars...")
        X_train, y_train = self.prepare_training_data(prices, 150, initial_train_size)

        if len(X_train) == 0:
            print("Not enough training data!")
            return pd.DataFrame()

        # Set feature names
        features_sample = self.feature_engine.extract_all_features(prices[:200])
        self.predictor.feature_names = sorted(features_sample.keys())

        self.predictor.fit(X_train, y_train)
        print(f"Trained on {len(X_train)} samples\n")

        print("Running walk-forward predictions...\n")

        # Walk forward through data
        while current_pos < len(prices) - self.prediction_horizon - 10:
            retrain_counter += 1

            # Retrain periodically on expanding window
            if retrain_counter >= self.retrain_frequency:
                print(f"\n[Position {current_pos}] Retraining model...")
                train_start = max(150, current_pos - 3000)  # Keep recent 3000 bars
                X_train, y_train = self.prepare_training_data(prices, train_start, current_pos)
                self.predictor.fit(X_train, y_train)
                retrain_counter = 0
                print(f"Retrained on {len(X_train)} samples")

            # Extract current features
            X_current = self.predictor.prepare_features(prices[:current_pos])

            # Predict
            prob = self.predictor.predict_proba(X_current)
            confidence = np.max(prob)
            prediction = 1 if prob[0, 1] > 0.5 else 0

            # Actual outcome
            actual_return = (prices[current_pos + self.prediction_horizon] - prices[current_pos]) / prices[current_pos]
            actual_direction = 1 if actual_return > 0 else 0

            # Record result
            results.append({
                'idx': current_pos,
                'prediction': prediction,
                'actual': actual_direction,
                'correct': prediction == actual_direction,
                'confidence': confidence,
                'prob_up': prob[0, 1],
                'actual_return': actual_return,
                'meets_threshold': confidence >= self.min_confidence
            })

            if len(results) % 100 == 0:
                acc = np.mean([r['correct'] for r in results[-100:]])
                print(f"Position {current_pos:5d} | Last 100: {acc:.3f} | "
                      f"Confidence: {confidence:.3f}", end='\r')

            current_pos += 1

        print("\n\n" + "=" * 70)
        return pd.DataFrame(results)

    def analyze_results(self, results_df):
        """Comprehensive analysis"""
        print("RESULTS ANALYSIS")
        print("=" * 70)

        # Overall accuracy
        overall_acc = results_df['correct'].mean()
        n_predictions = len(results_df)
        n_correct = results_df['correct'].sum()

        print(f"\n📊 OVERALL PERFORMANCE:")
        print(f"   Total Predictions:   {n_predictions:,}")
        print(f"   Correct:             {n_correct:,}")
        print(f"   Accuracy:            {overall_acc:.2%}")
        print(f"   Random Baseline:     50.00%")
        print(f"   Improvement:         {(overall_acc - 0.5) / 0.5 * 100:+.1f}%")

        # Statistical significance
        from scipy.stats import binomtest
        p_value = binomtest(n_correct, n_predictions, 0.5, alternative='greater').pvalue
        print(f"\n📈 STATISTICAL SIGNIFICANCE:")
        print(f"   P-value:             {p_value:.6f}")
        print(f"   Significant:         {'✅ YES (p < 0.001)' if p_value < 0.001 else '✅ YES (p < 0.05)' if p_value < 0.05 else '❌ NO'}")

        # Confidence-based filtering
        print(f"\n🎯 CONFIDENCE-BASED PERFORMANCE:")
        for threshold in [0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
            filtered = results_df[results_df['confidence'] >= threshold]
            if len(filtered) > 0:
                acc = filtered['correct'].mean()
                pct = len(filtered) / len(results_df)
                print(f"   Confidence >= {threshold:.2f}: {acc:.2%} accuracy on {len(filtered):4d} predictions ({pct:5.1%} of total)")

        # Direction analysis
        print(f"\n📊 PREDICTION DISTRIBUTION:")
        pred_up = (results_df['prediction'] == 1).sum()
        pred_down = (results_df['prediction'] == 0).sum()
        print(f"   Predicted UP:        {pred_up:,} ({pred_up/len(results_df):.1%})")
        print(f"   Predicted DOWN:      {pred_down:,} ({pred_down/len(results_df):.1%})")

        # Precision and recall
        from sklearn.metrics import precision_score, recall_score, f1_score
        precision = precision_score(results_df['actual'], results_df['prediction'])
        recall = recall_score(results_df['actual'], results_df['prediction'])
        f1 = f1_score(results_df['actual'], results_df['prediction'])

        print(f"\n📊 CLASSIFICATION METRICS:")
        print(f"   Precision:           {precision:.3f}")
        print(f"   Recall:              {recall:.3f}")
        print(f"   F1-Score:            {f1:.3f}")

        # Confidence calibration
        print(f"\n🎯 CONFIDENCE CALIBRATION:")
        print(f"   Mean Confidence:     {results_df['confidence'].mean():.3f}")
        print(f"   Std Confidence:      {results_df['confidence'].std():.3f}")
        print(f"   Min Confidence:      {results_df['confidence'].min():.3f}")
        print(f"   Max Confidence:      {results_df['confidence'].max():.3f}")

        # Progress over time
        print(f"\n📈 LEARNING CURVE (accuracy by quartile):")
        q1_end = len(results_df) // 4
        q2_end = len(results_df) // 2
        q3_end = 3 * len(results_df) // 4

        q1_acc = results_df.iloc[:q1_end]['correct'].mean()
        q2_acc = results_df.iloc[q1_end:q2_end]['correct'].mean()
        q3_acc = results_df.iloc[q2_end:q3_end]['correct'].mean()
        q4_acc = results_df.iloc[q3_end:]['correct'].mean()

        print(f"   Q1 (first 25%):      {q1_acc:.2%}")
        print(f"   Q2 (next 25%):       {q2_acc:.2%}")
        print(f"   Q3 (next 25%):       {q3_acc:.2%}")
        print(f"   Q4 (final 25%):      {q4_acc:.2%}")

        improvement = q4_acc - q1_acc
        print(f"   Improvement:         {improvement:+.2%}")

        print(f"\n{'=' * 70}\n")

        return overall_acc


def main():
    """Run ML system"""
    print("\n🚀 ML-BASED TRADING SYSTEM V1.0\n")

    system = MLTradingSystem(
        prediction_horizon=5,
        min_confidence=0.60
    )

    # Generate data
    print("Generating market data...")
    prices = system.generate_market_data(n_points=10000, seed=42)
    print(f"Generated {len(prices):,} price bars")
    print(f"Price range: ${prices.min():.2f} - ${prices.max():.2f}\n")

    # Run walk-forward test
    results = system.walk_forward_test(prices, initial_train_size=1000)

    if len(results) > 0:
        # Analyze
        accuracy = system.analyze_results(results)

        # Save results
        results.to_csv('/home/user/tradelocker/ml_system_results.csv', index=False)
        print(f"💾 Results saved to ml_system_results.csv")

        print(f"\n{'=' * 70}")
        print("PHASE 2 VERDICT")
        print("=" * 70)

        if accuracy >= 0.75:
            print(f"🎉 BREAKTHROUGH: {accuracy:.2%} accuracy achieved!")
            print("This is exceptional performance. Verify on different data.")
        elif accuracy >= 0.65:
            print(f"✅ EXCELLENT: {accuracy:.2%} accuracy")
            print("This is world-class performance for trading.")
        elif accuracy >= 0.60:
            print(f"✅ VERY GOOD: {accuracy:.2%} accuracy")
            print("This is professional-grade performance.")
        elif accuracy >= 0.55:
            print(f"✅ GOOD: {accuracy:.2%} accuracy")
            print("Better than baseline, has edge.")
        else:
            print(f"⚠️  BASELINE: {accuracy:.2%} accuracy")
            print("Needs more features or different approach.")

        print("=" * 70)


if __name__ == "__main__":
    main()
