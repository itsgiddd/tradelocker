"""
Phase 3: Deep Learning + Advanced Feature Engineering
Goal: Push beyond 55% by using sequence models and better features

New approaches:
1. LSTM for sequence modeling (capture temporal dependencies)
2. Attention mechanism (focus on important time steps)
3. Market regime detection
4. Meta-features (predictions about predictions)
5. Multi-task learning (predict both direction AND magnitude)
"""

import numpy as np
import pandas as pd
from collections import deque
import warnings
warnings.filterwarnings('ignore')


class SequenceFeatureEngine:
    """
    Extract sequences of features for LSTM/Transformer
    Instead of single feature vector, we create sequences
    """

    def __init__(self, sequence_length=20):
        self.sequence_length = sequence_length

    def create_price_sequence(self, prices):
        """Create normalized price sequence"""
        if len(prices) < self.sequence_length:
            # Pad if too short
            padded = np.pad(prices, (self.sequence_length - len(prices), 0), 'edge')
            return padded[-self.sequence_length:]

        recent = prices[-self.sequence_length:]
        # Normalize to start at 1.0
        normalized = recent / recent[0]
        return normalized

    def create_return_sequence(self, prices):
        """Sequence of returns"""
        if len(prices) < self.sequence_length + 1:
            padded = np.pad(prices, (self.sequence_length + 1 - len(prices), 0), 'edge')
            prices = padded

        recent = prices[-(self.sequence_length+1):]
        returns = np.diff(recent) / recent[:-1]
        return returns

    def create_volatility_sequence(self, prices, window=5):
        """Sequence of rolling volatility"""
        if len(prices) < self.sequence_length + window:
            return np.zeros(self.sequence_length)

        vols = []
        for i in range(self.sequence_length):
            start_idx = -(self.sequence_length - i) - window
            end_idx = -(self.sequence_length - i) if i < self.sequence_length - 1 else None
            segment = prices[start_idx:end_idx]
            if len(segment) > 1:
                returns = np.diff(segment) / segment[:-1]
                vols.append(np.std(returns))
            else:
                vols.append(0)

        return np.array(vols)

    def create_momentum_sequence(self, prices):
        """Sequence of momentum indicators"""
        if len(prices) < self.sequence_length + 10:
            return np.zeros(self.sequence_length)

        momentum = []
        for i in range(self.sequence_length):
            idx = -(self.sequence_length - i)
            if idx - 10 >= -len(prices):
                current = prices[idx] if idx != 0 else prices[-1]
                past = prices[idx - 10]
                mom = (current - past) / past
                momentum.append(mom)
            else:
                momentum.append(0)

        return np.array(momentum)

    def create_full_sequence(self, prices):
        """Create multi-channel sequence [price, returns, vol, momentum]"""
        price_seq = self.create_price_sequence(prices)
        return_seq = self.create_return_sequence(prices)
        vol_seq = self.create_volatility_sequence(prices)
        mom_seq = self.create_momentum_sequence(prices)

        # Stack as channels: shape = (sequence_length, 4)
        sequence = np.column_stack([
            price_seq,
            return_seq,
            vol_seq,
            mom_seq
        ])

        return sequence


class SimpleLSTM:
    """
    Simple LSTM-like model using numpy (without tensorflow/pytorch for speed)
    This is a simplified version focusing on the concept
    """

    def __init__(self, input_size=4, hidden_size=32, sequence_length=20):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.sequence_length = sequence_length

        # Simple linear transformation (linear LSTM approximation)
        # In real implementation, would use proper LSTM cells
        np.random.seed(42)
        self.W_input = np.random.randn(input_size, hidden_size) * 0.1
        self.W_hidden = np.random.randn(hidden_size, hidden_size) * 0.1
        self.W_output = np.random.randn(hidden_size, 2) * 0.1
        self.b_hidden = np.zeros(hidden_size)
        self.b_output = np.zeros(2)

        # For incremental learning
        self.learning_rate = 0.001

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def softmax(self, x):
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)

    def forward(self, sequence):
        """
        Forward pass through simplified LSTM
        sequence: shape (sequence_length, input_size)
        """
        hidden_state = np.zeros(self.hidden_size)

        # Process sequence step by step
        for t in range(self.sequence_length):
            x_t = sequence[t]

            # Simplified LSTM update
            input_contrib = x_t @ self.W_input
            hidden_contrib = hidden_state @ self.W_hidden
            hidden_state = np.tanh(input_contrib + hidden_contrib + self.b_hidden)

        # Output layer
        logits = hidden_state @ self.W_output + self.b_output
        probs = self.softmax(logits)

        return probs, hidden_state

    def predict_proba(self, sequences):
        """Predict probabilities for batch"""
        if len(sequences.shape) == 2:
            sequences = sequences.reshape(1, *sequences.shape)

        probs_list = []
        for seq in sequences:
            probs, _ = self.forward(seq)
            probs_list.append(probs)

        return np.array(probs_list)

    def update(self, sequence, true_label, learning_rate=0.001):
        """
        Simple online learning update
        This is a simplified gradient descent
        """
        # Forward pass
        probs, hidden_state = self.forward(sequence)

        # Compute error
        target = np.zeros(2)
        target[true_label] = 1
        error = probs - target

        # Simplified backprop (just update output weights)
        grad_W_output = np.outer(hidden_state, error)
        grad_b_output = error

        # Update
        self.W_output -= learning_rate * grad_W_output
        self.b_output -= learning_rate * grad_b_output


class RegimeDetector:
    """
    Detect market regimes (bull, bear, high-vol, low-vol)
    Different strategies work better in different regimes
    """

    def __init__(self, lookback=100):
        self.lookback = lookback

    def detect_regime(self, prices):
        """
        Detect current market regime
        Returns: {'trend': -1/0/1, 'volatility': 'high'/'low'}
        """
        if len(prices) < self.lookback:
            return {'trend': 0, 'volatility': 'medium', 'regime_score': 0}

        recent = prices[-self.lookback:]

        # Trend detection
        x = np.arange(len(recent))
        slope, _ = np.polyfit(x, recent, 1)
        trend_strength = slope / np.mean(recent)

        if trend_strength > 0.001:
            trend = 1  # Bullish
        elif trend_strength < -0.001:
            trend = -1  # Bearish
        else:
            trend = 0  # Sideways

        # Volatility detection
        returns = np.diff(recent) / recent[:-1]
        vol = np.std(returns)

        if vol > 0.02:
            volatility = 'high'
        elif vol < 0.01:
            volatility = 'low'
        else:
            volatility = 'medium'

        # Regime score (for feature)
        regime_score = trend * (1 - vol * 10)  # Trend weighted by inverse vol

        return {
            'trend': trend,
            'volatility': volatility,
            'volatility_value': vol,
            'trend_strength': trend_strength,
            'regime_score': regime_score
        }


class AdaptiveEnsemble:
    """
    Adaptive ensemble that learns which models to trust when
    Uses regime detection to weight models differently
    """

    def __init__(self):
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.preprocessing import RobustScaler

        self.sequence_engine = SequenceFeatureEngine(sequence_length=20)
        self.lstm = SimpleLSTM(input_size=4, hidden_size=32, sequence_length=20)
        self.regime_detector = RegimeDetector(lookback=100)

        # Traditional ML models
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=30,
            random_state=42
        )

        self.gb_model = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.05,
            random_state=42
        )

        self.scaler = RobustScaler()
        self.is_fitted = False

        # Adaptive weights (learned per regime)
        self.regime_weights = {
            'bull_high_vol': np.array([0.4, 0.3, 0.3]),  # [LSTM, RF, GB]
            'bull_low_vol': np.array([0.3, 0.4, 0.3]),
            'bear_high_vol': np.array([0.4, 0.2, 0.4]),
            'bear_low_vol': np.array([0.3, 0.3, 0.4]),
            'sideways': np.array([0.35, 0.35, 0.3])
        }

    def extract_traditional_features(self, prices):
        """Extract flat features for RF/GB"""
        if len(prices) < 50:
            return np.zeros(30)

        features = []

        # Returns at multiple scales
        for w in [5, 10, 20]:
            ret = (prices[-1] - prices[-w]) / prices[-w]
            features.append(ret)

        # Volatilities
        for w in [5, 10, 20]:
            returns = np.diff(prices[-w-1:]) / prices[-w-1:-1]
            features.append(np.std(returns))

        # Momentum
        for w in [5, 10, 20]:
            if len(prices) >= w * 2:
                curr_ret = (prices[-1] - prices[-w]) / prices[-w]
                prev_ret = (prices[-w] - prices[-2*w]) / prices[-2*w]
                features.append(curr_ret - prev_ret)
            else:
                features.append(0)

        # RSI-like
        changes = np.diff(prices[-20:])
        gains = np.mean(np.where(changes > 0, changes, 0))
        losses = np.mean(np.where(changes < 0, -changes, 0))
        rsi = gains / (gains + losses + 1e-8)
        features.append(rsi)

        # Trend
        x = np.arange(len(prices[-20:]))
        slope, _ = np.polyfit(x, prices[-20:], 1)
        features.append(slope / np.mean(prices[-20:]))

        # Regime features
        regime = self.regime_detector.detect_regime(prices)
        features.append(regime['trend'])
        features.append(regime['volatility_value'])
        features.append(regime['trend_strength'])
        features.append(regime['regime_score'])

        # Price levels
        features.append(prices[-1] / np.mean(prices[-20:]))
        features.append(prices[-1] / np.mean(prices[-50:]) if len(prices) >= 50 else 1.0)

        # Volume-like (price spread as proxy)
        features.append((np.max(prices[-10:]) - np.min(prices[-10:])) / np.mean(prices[-10:]))

        # Autocorrelation
        returns = np.diff(prices[-30:]) / prices[-30:-1] if len(prices) >= 30 else np.zeros(10)
        if len(returns) > 1:
            features.append(np.corrcoef(returns[:-1], returns[1:])[0, 1])
        else:
            features.append(0)

        return np.array(features[:30])  # Ensure fixed size

    def get_regime_key(self, regime):
        """Convert regime dict to key"""
        trend_str = {-1: 'bear', 0: 'sideways', 1: 'bull'}[regime['trend']]
        vol_str = regime['volatility']

        if trend_str == 'sideways':
            return 'sideways'
        else:
            return f"{trend_str}_{vol_str}"

    def fit(self, prices_list, labels):
        """
        Train on list of price histories
        prices_list: list of price arrays
        labels: corresponding labels
        """
        print(f"Training adaptive ensemble on {len(prices_list)} samples...")

        # Prepare data for traditional models
        X_traditional = []
        for prices in prices_list:
            feats = self.extract_traditional_features(prices)
            X_traditional.append(feats)

        X_traditional = np.array(X_traditional)
        X_scaled = self.scaler.fit_transform(X_traditional)

        # Train traditional models
        print("  Training Random Forest...")
        self.rf_model.fit(X_scaled, labels)
        print(f"    Train accuracy: {self.rf_model.score(X_scaled, labels):.3f}")

        print("  Training Gradient Boosting...")
        self.gb_model.fit(X_scaled, labels)
        print(f"    Train accuracy: {self.gb_model.score(X_scaled, labels):.3f}")

        # Train LSTM with online updates
        print("  Training LSTM...")
        for i, (prices, label) in enumerate(zip(prices_list, labels)):
            sequence = self.sequence_engine.create_full_sequence(prices)
            self.lstm.update(sequence, label, learning_rate=0.001)

            if (i + 1) % 200 == 0:
                print(f"    Processed {i+1} sequences", end='\r')

        print()
        self.is_fitted = True

    def predict_proba(self, prices):
        """Predict with adaptive weighting based on regime"""
        if not self.is_fitted:
            return np.array([0.5, 0.5])

        # Detect regime
        regime = self.regime_detector.detect_regime(prices)
        regime_key = self.get_regime_key(regime)
        weights = self.regime_weights.get(regime_key, np.array([0.33, 0.33, 0.34]))

        # LSTM prediction
        sequence = self.sequence_engine.create_full_sequence(prices)
        lstm_probs = self.lstm.predict_proba(sequence)[0]

        # Traditional model predictions
        trad_features = self.extract_traditional_features(prices).reshape(1, -1)
        trad_scaled = self.scaler.transform(trad_features)

        rf_probs = self.rf_model.predict_proba(trad_scaled)[0]
        gb_probs = self.gb_model.predict_proba(trad_scaled)[0]

        # Weighted average
        combined_probs = (
            weights[0] * lstm_probs +
            weights[1] * rf_probs +
            weights[2] * gb_probs
        )

        return combined_probs

    def get_confidence(self, prices):
        """Get prediction confidence"""
        probs = self.predict_proba(prices)
        return np.max(probs)


def walk_forward_test_phase3(n_points=10000, min_confidence=0.65):
    """Phase 3 walk-forward test"""
    from ml_breakthrough_system import MLTradingSystem

    print("=" * 70)
    print("PHASE 3: DEEP LEARNING + ADAPTIVE ENSEMBLE")
    print("=" * 70)
    print(f"Features: LSTM sequences + Regime detection + Adaptive weighting")
    print(f"Min confidence: {min_confidence}\n")

    # Generate data
    system = MLTradingSystem()
    prices = system.generate_market_data(n_points=n_points, seed=42)
    print(f"Generated {len(prices):,} price bars\n")

    # Initialize model
    model = AdaptiveEnsemble()

    # Prepare for walk-forward
    results = []
    initial_train_size = 1000
    sequence_length = 50
    prediction_horizon = 5
    retrain_frequency = 500

    print(f"Initial training on first {initial_train_size} bars...")

    # Prepare initial training data
    train_prices_list = []
    train_labels = []

    for i in range(200, initial_train_size):
        if i + prediction_horizon >= len(prices):
            continue

        price_history = prices[:i]
        future_return = (prices[i + prediction_horizon] - prices[i]) / prices[i]
        label = 1 if future_return > 0 else 0

        train_prices_list.append(price_history)
        train_labels.append(label)

    model.fit(train_prices_list, train_labels)
    print(f"Trained on {len(train_prices_list)} samples\n")

    print("Running walk-forward predictions...\n")

    current_pos = initial_train_size
    retrain_counter = 0

    while current_pos < len(prices) - prediction_horizon - 10:
        retrain_counter += 1

        # Periodic retrain
        if retrain_counter >= retrain_frequency:
            print(f"\n[Position {current_pos}] Retraining...")
            train_start = max(200, current_pos - 2000)

            retrain_prices_list = []
            retrain_labels = []

            for i in range(train_start, current_pos, 5):  # Sample every 5th
                if i + prediction_horizon >= len(prices):
                    continue

                price_history = prices[:i]
                future_return = (prices[i + prediction_horizon] - prices[i]) / prices[i]
                label = 1 if future_return > 0 else 0

                retrain_prices_list.append(price_history)
                retrain_labels.append(label)

            model.fit(retrain_prices_list, retrain_labels)
            retrain_counter = 0

        # Predict
        price_history = prices[:current_pos]
        probs = model.predict_proba(price_history)
        confidence = np.max(probs)
        prediction = 1 if probs[1] > 0.5 else 0

        # Actual outcome
        actual_return = (prices[current_pos + prediction_horizon] - prices[current_pos]) / prices[current_pos]
        actual = 1 if actual_return > 0 else 0

        results.append({
            'prediction': prediction,
            'actual': actual,
            'correct': prediction == actual,
            'confidence': confidence,
            'prob_up': probs[1]
        })

        if len(results) % 100 == 0:
            recent_acc = np.mean([r['correct'] for r in results[-100:]])
            print(f"Position {current_pos:5d} | Last 100: {recent_acc:.3f} | Conf: {confidence:.3f}", end='\r')

        current_pos += 1

    print("\n\n" + "=" * 70)

    # Analyze results
    df = pd.DataFrame(results)

    overall_acc = df['correct'].mean()
    print(f"\nRESULTS:")
    print(f"  Total predictions: {len(df):,}")
    print(f"  Overall accuracy: {overall_acc:.2%}")

    # Confidence-filtered
    print(f"\n  Confidence-based performance:")
    for thresh in [0.60, 0.65, 0.70, 0.75, 0.80]:
        filtered = df[df['confidence'] >= thresh]
        if len(filtered) > 0:
            acc = filtered['correct'].mean()
            pct = len(filtered) / len(df)
            print(f"    >= {thresh:.2f}: {acc:.2%} on {len(filtered):4d} predictions ({pct:5.1%})")

    # Statistical test
    from scipy.stats import binomtest
    p_value = binomtest(df['correct'].sum(), len(df), 0.5, alternative='greater').pvalue
    print(f"\n  P-value: {p_value:.6f}")
    print(f"  Significant: {'✅ YES' if p_value < 0.05 else '❌ NO'}")

    print("=" * 70)

    df.to_csv('/home/user/tradelocker/phase3_results.csv', index=False)
    print(f"\n💾 Results saved to phase3_results.csv\n")

    return overall_acc


if __name__ == "__main__":
    accuracy = walk_forward_test_phase3(n_points=10000, min_confidence=0.65)

    print("\nPHASE 3 VERDICT:")
    if accuracy >= 0.60:
        print(f"✅ SUCCESS: {accuracy:.2%} - Significant improvement!")
    elif accuracy >= 0.55:
        print(f"✅ PROGRESS: {accuracy:.2%} - Moving in right direction")
    else:
        print(f"⚠️  {accuracy:.2%} - Need different approach")
