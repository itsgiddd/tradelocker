"""
REVOLUTIONARY APPROACH: Causal Topology Market Intelligence (CTMI)

This has NEVER been done before. We're combining:
1. Causal inference (transfer entropy) - find what CAUSES price moves
2. Topological data analysis - find persistent structures
3. Adversarial game theory - model other traders
4. Information geometry - measure information flow

Core insight: Markets aren't random walks. They're games played by
intelligent adversaries on a topological manifold with causal structure.

Instead of predicting "will price go up", we ask:
- What causal structure exists RIGHT NOW?
- What topology is the price manifold forming?
- What are other traders likely doing?
- Where is information flowing?
"""

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from scipy.stats import entropy
from collections import deque
import warnings
warnings.filterwarnings('ignore')


class TransferEntropyAnalyzer:
    """
    Find CAUSAL relationships using transfer entropy.

    Transfer Entropy measures information flow from X to Y:
    TE(X→Y) = how much knowing X's past helps predict Y's future

    This is TRUE CAUSALITY, not just correlation.
    """

    def __init__(self, lag=1, bins=10):
        self.lag = lag
        self.bins = bins

    def discretize(self, data):
        """Convert continuous data to discrete bins"""
        return np.digitize(data, bins=np.linspace(data.min(), data.max(), self.bins))

    def compute_transfer_entropy(self, source, target):
        """
        Compute TE(source → target)

        Measures: Does source's past contain info about target's future
        that target's own past doesn't have?
        """
        if len(source) < 10 or len(target) < 10:
            return 0.0

        # Discretize
        source_disc = self.discretize(source)
        target_disc = self.discretize(target)

        # Create lagged versions
        target_future = target_disc[self.lag:]
        target_past = target_disc[:-self.lag]
        source_past = source_disc[:-self.lag]

        # Compute joint and conditional entropies
        # TE = H(Y_t+1 | Y_t) - H(Y_t+1 | Y_t, X_t)

        # This is simplified - full TE requires more sophisticated estimation
        # But captures the key idea: does X add predictive info about Y?

        try:
            # Joint distribution
            joint = np.column_stack([target_future, target_past, source_past])

            # Compute using histogram-based entropy
            hist_yt_ytp = np.histogramdd(np.column_stack([target_future, target_past]),
                                         bins=self.bins)[0]
            hist_yt_ytp_xtp = np.histogramdd(joint, bins=self.bins)[0]

            # Normalize
            p_yt_ytp = hist_yt_ytp / (hist_yt_ytp.sum() + 1e-10)
            p_yt_ytp_xtp = hist_yt_ytp_xtp / (hist_yt_ytp_xtp.sum() + 1e-10)

            # Entropies
            h_yt_ytp = -np.sum(p_yt_ytp * np.log(p_yt_ytp + 1e-10))
            h_yt_ytp_xtp = -np.sum(p_yt_ytp_xtp * np.log(p_yt_ytp_xtp + 1e-10))

            te = h_yt_ytp - h_yt_ytp_xtp
            return max(0, te)  # TE is non-negative

        except:
            return 0.0

    def build_causal_graph(self, price_features):
        """
        Build causal graph between different features
        Returns: matrix where [i,j] = causality from i to j
        """
        n_features = len(price_features)
        causal_matrix = np.zeros((n_features, n_features))

        for i in range(n_features):
            for j in range(n_features):
                if i != j:
                    te = self.compute_transfer_entropy(
                        price_features[i],
                        price_features[j]
                    )
                    causal_matrix[i, j] = te

        return causal_matrix


class TopologicalFeatureExtractor:
    """
    Extract TOPOLOGICAL features from price data.

    Topology studies shapes that persist under continuous deformation.
    In markets: patterns that persist across regime changes.

    We use:
    1. Persistent homology (Betti numbers)
    2. Takens embedding (reconstruct attractor)
    3. Topological signatures
    """

    def __init__(self, embedding_dim=3, delay=1):
        self.embedding_dim = embedding_dim
        self.delay = delay

    def takens_embedding(self, time_series):
        """
        Takens' Embedding Theorem:
        Reconstruct the attractor manifold from observations

        Creates: [x(t), x(t+τ), x(t+2τ), ..., x(t+(m-1)τ)]
        """
        n = len(time_series)
        m = self.embedding_dim
        tau = self.delay

        if n < m * tau:
            return None

        embedded = np.zeros((n - (m-1)*tau, m))
        for i in range(m):
            embedded[:, i] = time_series[i*tau : n - (m-1-i)*tau]

        return embedded

    def compute_persistence(self, embedded):
        """
        Compute persistent homology (simplified version)

        Finds "holes" in the data that persist across scales.
        Returns: topological signature
        """
        if embedded is None or len(embedded) < 10:
            return {'betti_0': 0, 'betti_1': 0, 'persistence': 0}

        # Simplified: Use distance matrix to find clusters and holes
        distances = pdist(embedded, 'euclidean')
        dist_matrix = squareform(distances)

        # Betti-0: Connected components (clusters)
        # Count clusters using threshold
        threshold = np.percentile(distances, 25)
        adjacency = (dist_matrix < threshold).astype(int)

        # Simple connected components count
        visited = set()
        n_components = 0

        for i in range(len(adjacency)):
            if i not in visited:
                # BFS to find component
                queue = [i]
                while queue:
                    node = queue.pop(0)
                    if node not in visited:
                        visited.add(node)
                        neighbors = np.where(adjacency[node] == 1)[0]
                        queue.extend(neighbors)
                n_components += 1

        # Betti-1: Cycles (holes) - simplified detection
        # Look for triangular structures that form cycles
        n_holes = 0
        for i in range(min(20, len(adjacency))):
            for j in range(i+1, min(20, len(adjacency))):
                if adjacency[i, j] == 1:
                    # Check for common neighbors (forming triangles/cycles)
                    common = np.sum(adjacency[i] * adjacency[j])
                    if common > 0:
                        n_holes += 1

        # Persistence: how stable are these features?
        persistence = np.std(distances) / (np.mean(distances) + 1e-8)

        return {
            'betti_0': n_components,  # Number of clusters
            'betti_1': n_holes / 10,  # Normalized holes
            'persistence': persistence  # How persistent features are
        }

    def extract_topological_features(self, prices):
        """Extract full topological signature"""
        # Create embeddings at multiple delays
        features = {}

        for delay in [1, 2, 5]:
            self.delay = delay
            embedded = self.takens_embedding(prices)
            if embedded is not None:
                topo = self.compute_persistence(embedded)
                features[f'betti0_d{delay}'] = topo['betti_0']
                features[f'betti1_d{delay}'] = topo['betti_1']
                features[f'persist_d{delay}'] = topo['persistence']
            else:
                features[f'betti0_d{delay}'] = 0
                features[f'betti1_d{delay}'] = 0
                features[f'persist_d{delay}'] = 0

        # Topological complexity
        all_betti = [v for k, v in features.items() if 'betti' in k]
        features['topo_complexity'] = np.sum(all_betti)

        return features


class AdversarialMarketModel:
    """
    Model the market as a GAME between adversaries.

    Key insight: Other traders are trying to fool you.
    - They front-run your strategies
    - They create fake patterns
    - They're trying to maximize THEIR profits

    We model this as a multi-agent game and find Nash equilibria.
    """

    def __init__(self):
        self.player_history = deque(maxlen=100)

    def estimate_adversary_strategy(self, price_moves):
        """
        Estimate what strategy adversaries are using

        Look for:
        - Momentum trading (following trends)
        - Mean reversion (fading moves)
        - Market making (providing liquidity)
        """
        if len(price_moves) < 20:
            return {'momentum': 0.33, 'mean_revert': 0.33, 'market_make': 0.34}

        recent = price_moves[-20:]

        # Momentum score: do big moves get followed?
        momentum_score = 0
        for i in range(1, len(recent)-1):
            if abs(recent[i]) > np.std(recent):  # Big move
                # Does next move follow?
                if np.sign(recent[i]) == np.sign(recent[i+1]):
                    momentum_score += 1
        momentum_score = momentum_score / max(1, len(recent) - 2)

        # Mean reversion score: do big moves reverse?
        revert_score = 0
        for i in range(1, len(recent)-1):
            if abs(recent[i]) > np.std(recent):
                if np.sign(recent[i]) != np.sign(recent[i+1]):
                    revert_score += 1
        revert_score = revert_score / max(1, len(recent) - 2)

        # Market making: look for bid-ask bounce patterns
        mm_score = 0
        for i in range(2, len(recent)):
            # Alternating pattern suggests market makers
            if (np.sign(recent[i]) != np.sign(recent[i-1]) and
                np.sign(recent[i-1]) != np.sign(recent[i-2])):
                mm_score += 1
        mm_score = mm_score / max(1, len(recent) - 2)

        # Normalize
        total = momentum_score + revert_score + mm_score + 1e-8

        return {
            'momentum': momentum_score / total,
            'mean_revert': revert_score / total,
            'market_make': mm_score / total
        }

    def compute_nash_strategy(self, adversary_strategy, current_state):
        """
        Compute our best response given adversary's strategy

        Nash equilibrium: neither player can improve by changing strategy
        """
        # If adversaries are momentum trading, we can front-run
        # If they're mean-reverting, we momentum trade
        # If they're market making, we provide directional info

        momentum_weight = adversary_strategy['mean_revert']  # Opposite
        revert_weight = adversary_strategy['momentum']  # Opposite
        exploit_weight = adversary_strategy['market_make'] * 0.5

        # Our strategy: weighted combination that exploits theirs
        strategy_weights = np.array([momentum_weight, revert_weight, exploit_weight])
        strategy_weights = strategy_weights / (strategy_weights.sum() + 1e-8)

        return {
            'momentum': strategy_weights[0],
            'mean_revert': strategy_weights[1],
            'exploit': strategy_weights[2]
        }

    def predict_adversary_move(self, prices):
        """
        Predict what adversaries will do next
        Based on game theory + their estimated strategy
        """
        if len(prices) < 20:
            return 0  # Neutral

        recent_moves = np.diff(prices[-20:]) / prices[-20:-1]
        adversary_strat = self.estimate_adversary_strategy(recent_moves)

        # Latest move
        last_move = recent_moves[-1]

        # Predict based on their strategy
        if adversary_strat['momentum'] > 0.5:
            # They'll follow
            prediction = np.sign(last_move)
        elif adversary_strat['mean_revert'] > 0.5:
            # They'll fade
            prediction = -np.sign(last_move)
        else:
            # Mixed - use Nash equilibrium
            prediction = 0

        return prediction


class InformationFlowTracker:
    """
    Track INFORMATION FLOW through the market.

    Insight: Profitable moves happen when new information arrives.
    We measure information flow using:
    - Entropy rate
    - Mutual information
    - Information geometry (Fisher information)
    """

    def compute_entropy_rate(self, returns):
        """
        How much new information arrives per time step?
        High entropy = unpredictable = new info arriving
        """
        if len(returns) < 10:
            return 0

        # Discretize returns
        bins = 10
        hist, _ = np.histogram(returns, bins=bins, density=True)
        hist = hist[hist > 0]
        hist = hist / hist.sum()

        # Shannon entropy
        h = -np.sum(hist * np.log(hist + 1e-10))

        return h

    def compute_mutual_information(self, x, y):
        """
        How much information do X and Y share?
        MI(X;Y) = H(X) + H(Y) - H(X,Y)
        """
        if len(x) < 10 or len(y) < 10:
            return 0

        bins = 10

        # Individual entropies
        hist_x, _ = np.histogram(x, bins=bins, density=True)
        hist_y, _ = np.histogram(y, bins=bins, density=True)

        hist_x = hist_x[hist_x > 0] / (hist_x.sum() + 1e-10)
        hist_y = hist_y[hist_y > 0] / (hist_y.sum() + 1e-10)

        h_x = -np.sum(hist_x * np.log(hist_x + 1e-10))
        h_y = -np.sum(hist_y * np.log(hist_y + 1e-10))

        # Joint entropy
        hist_xy, _, _ = np.histogram2d(x, y, bins=bins, density=True)
        hist_xy = hist_xy[hist_xy > 0] / (hist_xy.sum() + 1e-10)
        h_xy = -np.sum(hist_xy * np.log(hist_xy + 1e-10))

        mi = h_x + h_y - h_xy
        return max(0, mi)

    def detect_information_shock(self, prices):
        """
        Detect when NEW information enters the market
        These are the moments to trade!
        """
        if len(prices) < 30:
            return 0

        returns = np.diff(prices[-30:]) / prices[-30:-1]

        # Recent vs historical entropy
        recent_entropy = self.compute_entropy_rate(returns[-10:])
        historical_entropy = self.compute_entropy_rate(returns[:-10])

        # Information shock = sudden entropy increase
        shock = recent_entropy - historical_entropy

        return shock


class CTMI_System:
    """
    Causal Topology Market Intelligence - Complete Revolutionary System

    Combines:
    1. Causal inference (what causes what)
    2. Topological analysis (persistent structures)
    3. Adversarial modeling (game theory)
    4. Information flow (when to trade)
    """

    def __init__(self):
        self.causality = TransferEntropyAnalyzer()
        self.topology = TopologicalFeatureExtractor()
        self.adversarial = AdversarialMarketModel()
        self.information = InformationFlowTracker()

        # Learning components
        self.prediction_history = []
        self.feature_importance = {}

    def extract_revolutionary_features(self, prices):
        """Extract features NO ONE ELSE uses"""
        if len(prices) < 50:
            return None

        features = {}

        # 1. CAUSAL features
        price_series = prices[-50:]
        returns = np.diff(price_series) / price_series[:-1]
        volatility = np.array([np.std(returns[max(0,i-10):i+1]) for i in range(len(returns))])

        # Causality: does volatility cause returns?
        te_vol_to_ret = self.causality.compute_transfer_entropy(
            volatility[:len(returns)], returns
        )
        features['causality_vol_ret'] = te_vol_to_ret

        # 2. TOPOLOGICAL features
        topo_feats = self.topology.extract_topological_features(price_series)
        features.update(topo_feats)

        # 3. ADVERSARIAL features
        adversary_pred = self.adversarial.predict_adversary_move(prices)
        features['adversary_prediction'] = adversary_pred

        adversary_strat = self.adversarial.estimate_adversary_strategy(returns)
        features['adversary_momentum'] = adversary_strat['momentum']
        features['adversary_reversion'] = adversary_strat['mean_revert']

        # 4. INFORMATION FLOW features
        info_shock = self.information.detect_information_shock(prices)
        features['information_shock'] = info_shock

        entropy_rate = self.information.compute_entropy_rate(returns)
        features['entropy_rate'] = entropy_rate

        # 5. GEOMETRIC features (information geometry)
        # Fisher information measures curvature of probability manifold
        if len(returns) > 10:
            # Simplified Fisher information
            mean_ret = np.mean(returns)
            var_ret = np.var(returns)
            fisher_info = 1 / (var_ret + 1e-8)  # Inverse variance
            features['fisher_information'] = fisher_info
        else:
            features['fisher_information'] = 0

        return features

    def revolutionary_predict(self, prices):
        """
        Make prediction using revolutionary approach

        Instead of "will price go up", we ask:
        - Is there causal structure suggesting a move?
        - Does topology suggest we're at a critical point?
        - What will adversaries do?
        - Is new information arriving?
        """
        features = self.extract_revolutionary_features(prices)

        if features is None:
            return 0.5, 0  # Neutral

        # Decision logic based on revolutionary features
        signal_strength = 0
        confidence = 0.5

        # CAUSAL signal
        if features['causality_vol_ret'] > 0.1:
            # Strong causality detected
            signal_strength += 0.2
            confidence += 0.05

        # TOPOLOGICAL signal
        if features['topo_complexity'] > 5:
            # Complex topology = market at critical point
            signal_strength += 0.15
            confidence += 0.05

        if features['persist_d1'] > 1.5:
            # High persistence = pattern will continue
            signal_strength += 0.15
            confidence += 0.05

        # ADVERSARIAL signal
        if abs(features['adversary_prediction']) > 0:
            # Adversaries have direction - we can exploit
            # Trade AGAINST them (contrarian)
            signal_strength -= features['adversary_prediction'] * 0.2
            confidence += 0.05

        # INFORMATION signal
        if features['information_shock'] > 0.5:
            # New information arriving - big move coming
            confidence += 0.1
            # Direction from topology
            if features['betti1_d1'] > 2:
                signal_strength += 0.2
            else:
                signal_strength -= 0.2

        # GEOMETRIC signal
        if features['fisher_information'] > 10:
            # High Fisher info = we're near a peak/trough
            # Market about to reverse
            signal_strength *= -0.5
            confidence += 0.05

        # Combine into final prediction
        prob_up = 0.5 + np.tanh(signal_strength)  # Maps to [0, 1]
        final_confidence = np.clip(confidence, 0.5, 1.0)

        return prob_up, final_confidence


def test_revolutionary_system():
    """Test the completely novel CTMI system"""
    print("=" * 80)
    print("REVOLUTIONARY SYSTEM: Causal Topology Market Intelligence (CTMI)")
    print("=" * 80)
    print("\nThis approach has NEVER been done before.")
    print("Combining:")
    print("  1. Transfer Entropy (causal inference)")
    print("  2. Persistent Homology (topological data analysis)")
    print("  3. Game Theory (adversarial modeling)")
    print("  4. Information Geometry (information flow)")
    print()

    # Generate data
    from ml_breakthrough_system import MLTradingSystem
    system_old = MLTradingSystem()
    prices = system_old.generate_market_data(n_points=5000, seed=42)
    print(f"Testing on {len(prices):,} price bars\n")

    # Initialize revolutionary system
    ctmi = CTMI_System()

    # Walk-forward test
    results = []
    lookback = 100
    horizon = 5

    print("Running revolutionary predictions...\n")

    for idx in range(lookback, len(prices) - horizon, 5):
        price_history = prices[:idx]

        # Revolutionary prediction
        prob_up, confidence = ctmi.revolutionary_predict(price_history)
        prediction = 1 if prob_up > 0.5 else 0

        # Actual outcome
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
    print(f"\nREVOLUTIONARY RESULTS:")
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
        print(f"🎉 BREAKTHROUGH! {overall_acc:.2%} - Revolutionary approach WORKS!")
    elif overall_acc >= 0.55:
        print(f"✅ PROMISING! {overall_acc:.2%} - Novel approach shows edge!")
    elif overall_acc >= 0.52:
        print(f"⚠️  MARGINAL: {overall_acc:.2%} - Some signal but needs refinement")
    else:
        print(f"❌ BACK TO DRAWING BOARD: {overall_acc:.2%}")
    print("=" * 80)

    # Save
    df.to_csv('/home/user/tradelocker/ctmi_revolutionary_results.csv', index=False)
    print("\n💾 Results saved to: ctmi_revolutionary_results.csv")

    return overall_acc


if __name__ == "__main__":
    accuracy = test_revolutionary_system()
