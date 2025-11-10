"""
FRACTAL ATTRACTOR PHASE SPACE TRADING (FAPST)

Revolutionary Idea #2: Markets are CHAOTIC SYSTEMS with strange attractors.

Instead of predicting "will price go up", we:
1. Reconstruct the attractor in phase space (Takens' embedding)
2. Find current position on the attractor
3. Predict based on attractor flow dynamics
4. Use Lyapunov exponents to measure predictability windows

This is pure chaos theory + nonlinear dynamics.
NO ONE has done this properly for trading.

Key concepts:
- Strange attractors (Lorenz, Rossler-like patterns)
- Phase space reconstruction
- Lyapunov exponents (predictability horizons)
- Fractal dimensions (true fractal, not just correlation dimension)
- Return maps (where does attractor loop back?)
"""

import numpy as np
import pandas as pd
from scipy.spatial import KDTree
from scipy.spatial.distance import cdist
import warnings
warnings.filterwarnings('ignore')


class PhaseSpaceReconstructor:
    """
    Reconstruct market attractor in phase space using Takens' embedding.

    Takens' Theorem: Time series contains ALL information about
    the underlying dynamical system.

    We reconstruct: [x(t), x(t+τ), x(t+2τ), ..., x(t+(d-1)τ)]
    Where τ = delay, d = embedding dimension
    """

    def __init__(self, embedding_dim=5, delay=3):
        self.embedding_dim = embedding_dim
        self.delay = delay

    def find_optimal_delay(self, time_series):
        """
        Find optimal delay using first minimum of autocorrelation function
        """
        if len(time_series) < 50:
            return 3

        # Compute autocorrelation
        n = len(time_series)
        mean = np.mean(time_series)
        var = np.var(time_series)

        acf = []
        for lag in range(1, min(20, n//4)):
            corr = np.sum((time_series[:-lag] - mean) * (time_series[lag:] - mean))
            corr /= ((n - lag) * var)
            acf.append(corr)

        # Find first minimum
        for i in range(1, len(acf)-1):
            if acf[i] < acf[i-1] and acf[i] < acf[i+1]:
                return i + 1

        return 3  # Default

    def reconstruct(self, time_series):
        """
        Reconstruct phase space from time series
        Returns: embedded points [N x d] matrix
        """
        n = len(time_series)
        d = self.embedding_dim
        tau = self.delay

        if n < d * tau:
            return None

        n_points = n - (d-1) * tau
        embedded = np.zeros((n_points, d))

        for i in range(d):
            embedded[:, i] = time_series[i*tau : i*tau + n_points]

        return embedded

    def compute_correlation_dimension(self, embedded_points):
        """
        Compute correlation dimension (measure of fractal complexity)

        D = lim (log C(r) / log r)
        where C(r) = fraction of point pairs with distance < r
        """
        if embedded_points is None or len(embedded_points) < 20:
            return 1.5

        # Sample points to make it tractable
        n_sample = min(200, len(embedded_points))
        indices = np.random.choice(len(embedded_points), n_sample, replace=False)
        sampled = embedded_points[indices]

        # Compute pairwise distances
        distances = cdist(sampled, sampled, 'euclidean')
        distances = distances[np.triu_indices_from(distances, k=1)]

        # Compute correlation sum for different radii
        radii = np.percentile(distances, [10, 20, 30, 40, 50])
        corr_sums = []

        for r in radii:
            c_r = np.sum(distances < r) / len(distances)
            corr_sums.append(c_r)

        # Fit log-log slope
        log_r = np.log(radii + 1e-10)
        log_c = np.log(np.array(corr_sums) + 1e-10)

        # Linear fit
        valid = np.isfinite(log_r) & np.isfinite(log_c)
        if np.sum(valid) > 2:
            slope, _ = np.polyfit(log_r[valid], log_c[valid], 1)
            return max(1.0, min(slope, 3.0))
        else:
            return 1.5


class AttractorAnalyzer:
    """
    Analyze the strange attractor to understand market dynamics
    """

    def __init__(self, phase_space):
        self.phase_space = phase_space
        if phase_space is not None and len(phase_space) > 10:
            self.kdtree = KDTree(phase_space)
        else:
            self.kdtree = None

    def find_nearest_neighbors(self, point, k=10):
        """Find k nearest neighbors in phase space"""
        if self.kdtree is None:
            return None, None

        distances, indices = self.kdtree.query([point], k=min(k, len(self.phase_space)))
        return indices[0], distances[0]

    def predict_from_attractor(self, current_point):
        """
        Predict next move based on attractor geometry

        Idea: Find where we are on attractor, see where neighbors went
        """
        if self.phase_space is None or len(self.phase_space) < 20:
            return 0  # Neutral

        # Find nearest neighbors
        indices, distances = self.find_nearest_neighbors(current_point, k=15)
        if indices is None:
            return 0

        # Look at what happened after these similar states
        # (Need to track what came next for each point)
        predictions = []

        for idx in indices:
            if idx < len(self.phase_space) - 1:
                # Current point
                current = self.phase_space[idx]
                # Next point
                next_point = self.phase_space[idx + 1]

                # Direction of flow
                flow = next_point - current

                # Project onto first principal component (main direction)
                flow_magnitude = np.linalg.norm(flow)
                if flow_magnitude > 0:
                    # Direction in first dimension (proxy for price direction)
                    direction = np.sign(flow[0])
                    predictions.append(direction * flow_magnitude)

        if len(predictions) > 0:
            # Average prediction weighted by confidence
            avg_prediction = np.mean(predictions)
            return np.tanh(avg_prediction)  # Normalize to [-1, 1]
        else:
            return 0

    def compute_local_lyapunov(self, current_point):
        """
        Compute local Lyapunov exponent

        Measures: How fast do nearby trajectories diverge?
        High Lyapunov = chaotic, low predictability
        Low Lyapunov = stable, higher predictability
        """
        if self.phase_space is None:
            return 1.0

        # Find neighbors
        indices, distances = self.find_nearest_neighbors(current_point, k=10)
        if indices is None or len(indices) < 5:
            return 1.0

        # Track how fast neighbors diverge over time
        divergence_rates = []

        for i, idx in enumerate(indices[1:5]):  # Use first few neighbors
            if idx < len(self.phase_space) - 5:
                initial_dist = distances[i+1]
                if initial_dist < 1e-6:
                    continue

                # Distance after 5 steps
                future_dist = np.linalg.norm(
                    self.phase_space[idx + 5] - self.phase_space[indices[0] + 5]
                ) if indices[0] + 5 < len(self.phase_space) else initial_dist

                # Lyapunov: log(future_dist / initial_dist) / time
                if future_dist > 0 and initial_dist > 0:
                    lyap = np.log(future_dist / initial_dist) / 5
                    divergence_rates.append(lyap)

        if len(divergence_rates) > 0:
            return np.mean(divergence_rates)
        else:
            return 1.0


class ReturnMapAnalyzer:
    """
    Analyze return maps (Poincaré sections)

    Return map: Plot x(t+1) vs x(t)
    Shows where attractor loops back to itself
    """

    def create_return_map(self, time_series):
        """Create 1D return map"""
        if len(time_series) < 10:
            return None, None

        x_t = time_series[:-1]
        x_t_plus_1 = time_series[1:]

        return x_t, x_t_plus_1

    def find_fixed_points(self, time_series):
        """
        Find fixed points (where x(t+1) = x(t))
        These are attracting/repelling points
        """
        x_t, x_t_plus_1 = self.create_return_map(time_series)
        if x_t is None:
            return []

        # Find where x(t+1) ≈ x(t)
        differences = x_t_plus_1 - x_t
        threshold = np.std(differences) * 0.1

        fixed_points = []
        for i in range(len(differences)):
            if abs(differences[i]) < threshold:
                fixed_points.append(x_t[i])

        return fixed_points

    def predict_from_return_map(self, current_value, time_series):
        """
        Predict using return map structure

        If current value is near fixed point, predict convergence
        If far from fixed point, predict toward it
        """
        fixed_points = self.find_fixed_points(time_series)

        if len(fixed_points) == 0:
            return 0

        # Find nearest fixed point
        distances = [abs(current_value - fp) for fp in fixed_points]
        nearest_fp = fixed_points[np.argmin(distances)]

        # Predict movement toward fixed point
        direction = np.sign(nearest_fp - current_value)

        # Strength based on distance
        distance = abs(nearest_fp - current_value)
        max_dist = np.std(time_series)
        strength = min(1.0, distance / (max_dist + 1e-8))

        return direction * strength


class FractalAttractorSystem:
    """
    Complete Fractal Attractor Phase Space Trading System
    """

    def __init__(self, embedding_dim=5, delay=3):
        self.phase_reconstructor = PhaseSpaceReconstructor(embedding_dim, delay)
        self.return_map = ReturnMapAnalyzer()

        # State
        self.current_attractor = None
        self.attractor_analyzer = None

    def extract_chaotic_features(self, prices):
        """Extract features from chaotic dynamics"""
        if len(prices) < 100:
            return None

        features = {}

        # Use returns for better stationarity
        returns = np.diff(prices) / prices[:-1]

        # 1. PHASE SPACE reconstruction
        embedded = self.phase_reconstructor.reconstruct(returns[-200:] if len(returns) > 200 else returns)

        if embedded is not None:
            self.current_attractor = embedded
            self.attractor_analyzer = AttractorAnalyzer(embedded)

            # Correlation dimension
            features['correlation_dim'] = self.phase_reconstructor.compute_correlation_dimension(embedded)

            # Current position in phase space
            current_point = embedded[-1]

            # Attractor prediction
            attractor_pred = self.attractor_analyzer.predict_from_attractor(current_point)
            features['attractor_prediction'] = attractor_pred

            # Lyapunov exponent (predictability)
            lyapunov = self.attractor_analyzer.compute_local_lyapunov(current_point)
            features['lyapunov'] = lyapunov

            # Predictability window (inverse of Lyapunov)
            features['predictability'] = 1.0 / (abs(lyapunov) + 0.1)

        else:
            features['correlation_dim'] = 1.5
            features['attractor_prediction'] = 0
            features['lyapunov'] = 1.0
            features['predictability'] = 1.0

        # 2. RETURN MAP analysis
        return_map_pred = self.return_map.predict_from_return_map(returns[-1], returns[-50:])
        features['return_map_prediction'] = return_map_pred

        # 3. FRACTAL features
        # Hurst exponent (long-range dependence)
        features['hurst'] = self.compute_hurst_exponent(returns[-100:] if len(returns) > 100 else returns)

        return features

    def compute_hurst_exponent(self, time_series):
        """
        Compute Hurst exponent
        H > 0.5: persistent (trending)
        H < 0.5: anti-persistent (mean-reverting)
        H = 0.5: random walk
        """
        if len(time_series) < 20:
            return 0.5

        lags = range(2, min(20, len(time_series)//2))
        tau = []

        for lag in lags:
            # Standard deviation of differences
            std = np.std([time_series[i] - time_series[i-lag] for i in range(lag, len(time_series))])
            tau.append(std)

        # Fit log-log
        log_lags = np.log(list(lags))
        log_tau = np.log(tau)

        valid = np.isfinite(log_lags) & np.isfinite(log_tau)
        if np.sum(valid) > 2:
            slope, _ = np.polyfit(log_lags[valid], log_tau[valid], 1)
            hurst = slope
            return np.clip(hurst, 0, 1)
        else:
            return 0.5

    def fractal_predict(self, prices):
        """
        Make prediction using fractal attractor analysis
        """
        features = self.extract_chaotic_features(prices)

        if features is None:
            return 0.5, 0.5

        # Combine signals
        signal = 0

        # Attractor flow prediction
        signal += features['attractor_prediction'] * 0.4

        # Return map prediction
        signal += features['return_map_prediction'] * 0.3

        # Hurst-based: if persistent (H>0.5), follow momentum
        if features['hurst'] > 0.5:
            recent_momentum = (prices[-1] - prices[-10]) / prices[-10]
            signal += np.sign(recent_momentum) * (features['hurst'] - 0.5) * 0.3

        # Confidence based on predictability
        confidence = 0.5 + features['predictability'] * 0.2
        confidence = confidence * (1.0 / (1.0 + abs(features['lyapunov'])))

        # Correlation dimension: lower = more structure = higher confidence
        if features['correlation_dim'] < 2.0:
            confidence += 0.1

        confidence = np.clip(confidence, 0.5, 1.0)

        # Convert signal to probability
        prob_up = 0.5 + 0.5 * np.tanh(signal)

        return prob_up, confidence


def test_fractal_system():
    """Test fractal attractor system"""
    print("=" * 80)
    print("FRACTAL ATTRACTOR PHASE SPACE TRADING (FAPST)")
    print("=" * 80)
    print("\nUsing chaos theory + nonlinear dynamics:")
    print("  1. Phase space reconstruction (Takens' embedding)")
    print("  2. Strange attractor analysis")
    print("  3. Lyapunov exponents (predictability windows)")
    print("  4. Return maps (Poincaré sections)")
    print("  5. Hurst exponent (long-range dependence)")
    print()

    # Generate data
    from ml_breakthrough_system import MLTradingSystem
    system_old = MLTradingSystem()
    prices = system_old.generate_market_data(n_points=5000, seed=42)
    print(f"Testing on {len(prices):,} price bars\n")

    # Initialize system
    fapst = FractalAttractorSystem(embedding_dim=5, delay=3)

    # Walk-forward test
    results = []
    lookback = 150
    horizon = 5

    print("Running fractal attractor predictions...\n")

    for idx in range(lookback, len(prices) - horizon, 5):
        price_history = prices[:idx]

        # Fractal prediction
        prob_up, confidence = fapst.fractal_predict(price_history)
        prediction = 1 if prob_up > 0.5 else 0

        # Actual
        future_return = (prices[idx + horizon] - prices[idx]) / prices[idx]
        actual = 1 if future_return > 0 else 0

        results.append({
            'prediction': prediction,
            'actual': actual,
            'correct': prediction == actual,
            'prob_up': prob_up,
            'confidence': confidence
        })

        if len(results) % 100 == 0:
            recent_acc = np.mean([r['correct'] for r in results[-100:]])
            print(f"Position {idx:5d} | Last 100: {recent_acc:.3f} | Conf: {confidence:.3f}", end='\r')

    print("\n\n" + "=" * 80)

    # Analyze
    df = pd.DataFrame(results)

    overall_acc = df['correct'].mean()
    print(f"\nFRACTAL ATTRACTOR RESULTS:")
    print(f"  Total predictions: {len(df):,}")
    print(f"  Overall accuracy: {overall_acc:.2%}")
    print()

    # Confidence filtering
    print("  Confidence-based performance:")
    for thresh in [0.55, 0.60, 0.65, 0.70, 0.75]:
        filtered = df[df['confidence'] >= thresh]
        if len(filtered) > 0:
            acc = filtered['correct'].mean()
            pct = len(filtered) / len(df)
            status = "✅" if acc > 0.60 else "⚠️ " if acc > 0.55 else "  "
            print(f"    {status} >= {thresh:.2f}: {acc:.2%} on {len(filtered):4d} predictions ({pct:5.1%})")

    # Statistical test
    from scipy.stats import binomtest
    p_value = binomtest(df['correct'].sum(), len(df), 0.5, alternative='greater').pvalue
    print(f"\n  P-value: {p_value:.6f}")
    print(f"  Statistically significant: {'✅ YES' if p_value < 0.05 else '❌ NO'}")

    print("\n" + "=" * 80)
    print("VERDICT:")
    if overall_acc >= 0.60:
        print(f"🎉 BREAKTHROUGH! {overall_acc:.2%} - Fractal approach WORKS!")
    elif overall_acc >= 0.55:
        print(f"✅ PROMISING! {overall_acc:.2%} - Chaos theory shows edge!")
    elif overall_acc >= 0.52:
        print(f"⚠️  MARGINAL: {overall_acc:.2%} - Some signal detected")
    else:
        print(f"❌ NO EDGE: {overall_acc:.2%}")
    print("=" * 80)

    # Save
    df.to_csv('/home/user/tradelocker/fractal_results.csv', index=False)
    print("\n💾 Results saved to: fractal_results.csv")

    return overall_acc


if __name__ == "__main__":
    accuracy = test_fractal_system()
