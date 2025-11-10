"""
AEGFM-Ω Complete Implementation
Following the exact mathematical framework from the paper
"""

import numpy as np
import pandas as pd
import math
from scipy import stats
from scipy.special import erf
from scipy.fft import fft, ifft, fftfreq
from scipy.signal import welch
import matplotlib.pyplot as plt
from itertools import combinations_with_replacement
import warnings
warnings.filterwarnings('ignore')

class PathSignature:
    """Compute path signatures up to order m"""

    @staticmethod
    def signature_order_1(path):
        """First order signature: ∫ dP_t"""
        return np.sum(np.diff(path, axis=0), axis=0)

    @staticmethod
    def signature_order_2(path):
        """Second order signature: ∫∫ dP_t1 ⊗ dP_t2"""
        diffs = np.diff(path, axis=0)
        n = len(diffs)

        # For scalar path, this is just iterated integral
        if diffs.ndim == 1:
            sig2 = 0
            for i in range(n):
                sig2 += diffs[i] * np.sum(diffs[i+1:])
            return sig2
        else:
            # For vector path
            d = diffs.shape[1]
            sig2 = np.zeros((d, d))
            for i in range(n):
                sig2 += np.outer(diffs[i], np.sum(diffs[i+1:], axis=0))
            return sig2

    @staticmethod
    def signature_order_3(path):
        """Third order signature: ∫∫∫ dP_t1 ⊗ dP_t2 ⊗ dP_t3"""
        diffs = np.diff(path, axis=0)
        n = len(diffs)

        if diffs.ndim == 1:
            sig3 = 0
            for i in range(n):
                for j in range(i+1, n):
                    sig3 += diffs[i] * diffs[j] * np.sum(diffs[j+1:])
            return sig3
        else:
            # For vector - simplified
            return np.sum([np.sum(diffs[i] * diffs[j] * np.sum(diffs[j+1:], axis=0))
                          for i in range(n) for j in range(i+1, n)])

    @staticmethod
    def compute_signature(path, order=3):
        """Compute signature up to specified order"""
        # Ensure path is array
        path = np.array(path)

        sig = {
            0: 1.0,  # Zeroth order
            1: PathSignature.signature_order_1(path),
            2: PathSignature.signature_order_2(path),
            3: PathSignature.signature_order_3(path) if order >= 3 else 0
        }

        return sig


class OmegaKernel:
    """
    The Omega Kernel incorporating infinite-order dependencies:
    K_Ω(t,s) = Σ(k=1 to ∞) [α_k/k! · sig_k(P) · exp(-β_k|t-s|) · cos(2πk(t-s)/T)]
    """

    def __init__(self, max_order=10, beta_0=0.1, period=100):
        self.max_order = max_order
        self.beta_0 = beta_0
        self.period = period

    def compute(self, path, t, s):
        """Compute K_Ω(t,s) for given path segment"""
        if t <= s:
            return 0.0

        # Get path segment [s, t]
        segment = path[s:t+1]

        if len(segment) < 2:
            return 0.0

        # Compute signature
        sig = PathSignature.compute_signature(segment, order=min(3, self.max_order))

        # Sum over orders
        kernel_value = 0.0
        dt = t - s

        for k in range(1, min(self.max_order + 1, 11)):
            # α_k = 1/2^k ensures convergence
            alpha_k = 1.0 / (2 ** k)

            # β_k = k · β_0
            beta_k = k * self.beta_0

            # sig_k term (use magnitude of signature at order k)
            if k <= 3:
                sig_k_val = np.abs(sig[min(k, 3)])
                if isinstance(sig_k_val, np.ndarray):
                    sig_k_val = np.linalg.norm(sig_k_val)
            else:
                sig_k_val = 1.0  # Approximate for higher orders

            # Compute kernel term
            term = (alpha_k / math.factorial(k) *
                   sig_k_val *
                   np.exp(-beta_k * dt) *
                   np.cos(2 * np.pi * k * dt / self.period))

            kernel_value += term

        return kernel_value


class MinkowskiFourierTransform:
    """
    MFT[P](ω, τ) = ∫ (P(t) ⊕_λ P(t+τ)) · exp(-iωt) dt
    Where: P(t) ⊕_λ P(t+τ) = λP(t) + (1-λ)P(t+τ)
    With: λ = 1/(1 + exp(-ατ))
    """

    def __init__(self, alpha=0.1):
        self.alpha = alpha

    def compute_lambda(self, tau):
        """Compute sigmoid weight: λ = 1/(1 + exp(-ατ))"""
        return 1.0 / (1.0 + np.exp(-self.alpha * tau))

    def minkowski_weighted_sum(self, P_t, P_t_tau, tau):
        """Compute: λP(t) + (1-λ)P(t+τ)"""
        lambda_weight = self.compute_lambda(tau)
        return lambda_weight * P_t + (1 - lambda_weight) * P_t_tau

    def transform(self, prices, tau_values):
        """
        Compute MFT for given price series and tau values
        Returns: MFT[P](ω, τ) as 2D array
        """
        n = len(prices)
        n_freqs = n // 2 + 1
        n_taus = len(tau_values)

        mft_result = np.zeros((n_freqs, n_taus), dtype=complex)

        for tau_idx, tau in enumerate(tau_values):
            if tau >= n:
                continue

            # Construct weighted series
            weighted_series = np.zeros(n - tau)
            for t in range(n - tau):
                weighted_series[t] = self.minkowski_weighted_sum(
                    prices[t], prices[t + tau], tau
                )

            # Apply Fourier transform
            fft_result = fft(weighted_series)
            mft_result[:len(fft_result)//2+1, tau_idx] = fft_result[:len(fft_result)//2+1]

        return mft_result

    def inverse_transform(self, mft_data, tau_idx=0):
        """Inverse MFT to get pattern projection"""
        # Take specific tau slice
        freq_slice = mft_data[:, tau_idx]

        # Inverse FFT
        n = (len(freq_slice) - 1) * 2
        full_spectrum = np.concatenate([freq_slice, np.conj(freq_slice[-2:0:-1])])
        reconstructed = ifft(full_spectrum).real

        return reconstructed


class EntropicFlowEngine:
    """
    Market evolution via Entropic Flow Equation:
    ∂P/∂t = -∇H[P] + D_f∇²P + √(2σ(H))·Ẇ_t + N[P,u]
    """

    def __init__(self):
        pass

    def shannon_entropy(self, prices, n_bins=20):
        """
        H[P] = -∫ p(x)log(p(x)) dx
        """
        hist, _ = np.histogram(prices, bins=n_bins, density=True)
        hist = hist[hist > 0]  # Remove zeros

        # Normalize
        hist = hist / np.sum(hist)

        entropy = -np.sum(hist * np.log(hist + 1e-10))
        return entropy

    def kl_divergence(self, prices_t, prices_t_minus_1, n_bins=20):
        """KL(p_t || p_{t-1})"""
        hist_t, bins = np.histogram(prices_t, bins=n_bins, density=True)
        hist_t_1, _ = np.histogram(prices_t_minus_1, bins=bins, density=True)

        # Smooth to avoid division by zero
        hist_t = hist_t + 1e-10
        hist_t_1 = hist_t_1 + 1e-10

        # Normalize
        hist_t = hist_t / np.sum(hist_t)
        hist_t_1 = hist_t_1 / np.sum(hist_t_1)

        kl = np.sum(hist_t * np.log(hist_t / hist_t_1))
        return kl

    def compute_E1(self, prices, prices_prev, theta=0.5):
        """
        E₁(t) = -Σ p_i(t)log(p_i(t)) - θ·KL(p_t || p_{t-1})
        """
        entropy = self.shannon_entropy(prices)
        kl = self.kl_divergence(prices, prices_prev)

        E1 = entropy - theta * kl
        return E1, entropy, kl

    def fractal_dimension_higuchi(self, prices, k_max=10):
        """
        D_f(t) = 1 + lim_{j→∞} [log(Var(W_j[P])) / log(2^{-j})]
        Using Higuchi method
        """
        N = len(prices)
        L = []

        for k in range(1, min(k_max, N // 4) + 1):
            Lk = []
            for m in range(k):
                indices = np.arange(m, N, k)
                if len(indices) < 2:
                    continue

                subset = prices[indices]
                length = np.sum(np.abs(np.diff(subset)))
                normalization = (N - 1) / ((len(indices) - 1) * k)
                Lk.append(length * normalization)

            if len(Lk) > 0:
                L.append(np.mean(Lk))

        if len(L) < 2:
            return 1.5

        # Fit log-log
        x = np.log(np.arange(1, len(L) + 1))
        y = np.log(L)

        if len(x) > 1:
            slope, _ = np.polyfit(x, y, 1)
            D_f = 2 - slope
            return np.clip(D_f, 1.0, 2.0)

        return 1.5

    def entropy_dependent_volatility(self, entropy, sigma_0=0.02, gamma=0.5):
        """σ(H) = σ_0 · exp(-γH)"""
        return sigma_0 * np.exp(-gamma * entropy)


class KoopmanOperator:
    """
    Koopman operator framework for observable evolution
    K_t+1 = K_t - η∇_K|g(P_{t+1}) - K_t g(P_t)|² + λ|K_t|_*
    """

    def __init__(self, n_observables=10, learning_rate=0.01, regularization=0.001):
        self.n = n_observables
        self.eta = learning_rate
        self.lambda_reg = regularization
        self.K = np.eye(n_observables)  # Initialize as identity

    def compute_observables(self, prices):
        """
        g(P) = [P, P², sin(2πP/T), cos(2πP/T), S^(3)(P), ...]
        """
        if len(prices) < 2:
            return np.zeros(self.n)

        P = prices[-1]
        T = 100  # Period

        sig = PathSignature.compute_signature(prices[-20:] if len(prices) > 20 else prices)
        sig3_val = sig[3] if 3 in sig else 0
        if isinstance(sig3_val, np.ndarray):
            sig3_val = np.linalg.norm(sig3_val)

        # Build observable vector
        obs = np.array([
            P,
            P ** 2,
            np.sin(2 * np.pi * P / T),
            np.cos(2 * np.pi * P / T),
            float(sig3_val),
            np.mean(prices[-5:]) if len(prices) >= 5 else P,
            np.std(prices[-10:]) if len(prices) >= 10 else 0,
            np.max(prices[-10:]) if len(prices) >= 10 else P,
            np.min(prices[-10:]) if len(prices) >= 10 else P,
            len(prices) % T / T  # Phase
        ])

        return obs[:self.n]

    def predict(self, observables):
        """g(P_{t+1}) ≈ K @ g(P_t)"""
        return self.K @ observables

    def update(self, g_t, g_t_plus_1):
        """Online learning update"""
        # Prediction error
        prediction = self.K @ g_t
        error = g_t_plus_1 - prediction

        # Gradient descent update
        gradient = -2 * np.outer(error, g_t)

        # Nuclear norm regularization (approximate with Frobenius)
        reg_gradient = self.lambda_reg * self.K

        self.K = self.K - self.eta * (gradient + reg_gradient)

        return np.linalg.norm(error)


class AEGFMOmega:
    """Complete AEGFM-Ω Implementation"""

    def __init__(self, initial_capital=100000, leverage=10):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.leverage = leverage

        # Initialize components
        self.omega_kernel = OmegaKernel(max_order=10, beta_0=0.1, period=100)
        self.mft = MinkowskiFourierTransform(alpha=0.1)
        self.entropic_flow = EntropicFlowEngine()
        self.koopman = KoopmanOperator(n_observables=10, learning_rate=0.01)

        # Parameters from paper
        self.confidence_threshold = 0.75
        self.entropy_threshold = 2.5
        self.signature_order = 3

        # Trading parameters
        self.target_return = 0.004  # 0.4%
        self.stop_loss = 0.002  # 0.2%
        self.max_position_fraction = 0.1

        # Results
        self.trades = []
        self.equity_curve = [initial_capital]

    def generate_market_data(self, n_points=50000, regime_changes=True):
        """Generate realistic market data with multiple regimes"""
        np.random.seed(42)

        dt = 1/252/390
        prices = [100.0]

        # Different regime parameters
        regimes = [
            {'mu': 0.0002, 'sigma': 0.015, 'name': 'bullish'},
            {'mu': -0.0001, 'sigma': 0.020, 'name': 'bearish'},
            {'mu': 0.0, 'sigma': 0.008, 'name': 'low_vol'},
            {'mu': 0.0, 'sigma': 0.030, 'name': 'high_vol'},
        ]

        regime_length = 1000

        for i in range(n_points - 1):
            # Change regime periodically
            if regime_changes and i % regime_length == 0:
                current_regime = regimes[np.random.randint(0, len(regimes))]
            elif not regime_changes:
                current_regime = {'mu': 0.0001, 'sigma': 0.02, 'name': 'neutral'}

            # Generate return
            ret = np.random.normal(current_regime['mu'] * dt,
                                  current_regime['sigma'] * np.sqrt(dt))

            # Add occasional jumps
            if np.random.random() < 0.01:  # 1% chance of jump
                ret += np.random.normal(0, 0.01)

            prices.append(prices[-1] * (1 + ret))

        return np.array(prices)

    def compute_confidence(self, prices, window_size=100):
        """
        Complete confidence formula from paper:
        C(t) = σ(γ(t)) · erf((S-μ_S)/(√2σ_S)) · 1_{PSI<τ}
        Where: γ(t) = α₀ + Σαₖ·sigₖ + β·(D_f-1.5)² + δ·ΔE₁
        """
        if len(prices) < window_size:
            return 0.0

        window = prices[-window_size:]
        window_prev = prices[-window_size-20:-20] if len(prices) > window_size + 20 else window

        # Compute E1 and its components
        E1, entropy, kl = self.entropic_flow.compute_E1(window, window_prev)

        # Compute fractal dimension
        D_f = self.entropic_flow.fractal_dimension_higuchi(window)

        # Compute signature
        sig = PathSignature.compute_signature(window[-50:])
        sig_sum = 0
        for k in [1, 2, 3]:
            if k in sig:
                val = sig[k]
                if isinstance(val, np.ndarray):
                    sig_sum += np.linalg.norm(val)
                else:
                    sig_sum += abs(val)

        # Compute γ(t)
        alpha_0 = 0.0
        alpha_k = 0.01  # Weight for signature terms
        beta = -5.0  # Penalty for fractal deviation
        delta = -0.3  # Penalty for entropy change

        gamma = (alpha_0 +
                alpha_k * sig_sum +
                beta * (D_f - 1.5) ** 2 +
                delta * E1)

        # Sigmoid
        confidence_base = 1.0 / (1.0 + np.exp(-gamma))

        # Error function term (using returns as S)
        returns = np.diff(window) / window[:-1]
        S = np.mean(returns)
        mu_S = 0.0
        sigma_S = np.std(returns) + 1e-6

        erf_term = erf((S - mu_S) / (np.sqrt(2) * sigma_S))

        # PSI indicator (distribution shift) - simplified as 1 for now
        psi_indicator = 1.0

        confidence = confidence_base * (0.5 + 0.5 * erf_term) * psi_indicator

        return confidence, E1, D_f, sig

    def predict_next_price(self, prices, horizon=1):
        """
        Complete prediction formula:
        P̂(t+h) = exp(K_Ω·h)P_t + MFT^{-1}[Φ(ω,h)] + C(E₁,D_f,G₃)
        """
        if len(prices) < 100:
            return prices[-1]

        P_t = prices[-1]

        # Component 1: Linear evolution via Omega kernel
        kernel_sum = 0
        lookback = min(50, len(prices) - 1)
        for s in range(len(prices) - lookback, len(prices)):
            kernel_val = self.omega_kernel.compute(prices, len(prices) - 1, s)
            kernel_sum += kernel_val * prices[s]

        P_linear = kernel_sum / (lookback + 1e-6) if kernel_sum != 0 else P_t

        # Component 2: Pattern projection via MFT
        window = prices[-200:] if len(prices) > 200 else prices
        tau_values = [1, 5, 10, 20]

        try:
            mft_result = self.mft.transform(window, tau_values)
            pattern_projection = self.mft.inverse_transform(mft_result, tau_idx=0)

            if len(pattern_projection) > 0:
                # Project forward
                trend = pattern_projection[-1] - pattern_projection[0]
                P_pattern = trend * 0.1  # Scale down
            else:
                P_pattern = 0
        except:
            P_pattern = 0

        # Component 3: Cascade correction
        E1, _, _ = self.entropic_flow.compute_E1(window, window[:-10] if len(window) > 10 else window)
        D_f = self.entropic_flow.fractal_dimension_higuchi(window)

        # ∇E₁ approximation
        E1_prev, _, _ = self.entropic_flow.compute_E1(window[:-5], window[:-10])
        grad_E1 = E1 - E1_prev

        # Cascade correction: w₁·∇E₁ + w₂·(D_f - E[D_f])
        w1 = 0.1
        w2 = 0.05

        C_cascade = w1 * grad_E1 + w2 * (D_f - 1.5)

        # Combine all components
        P_pred = P_linear + P_pattern + P_t * C_cascade

        return P_pred

    def kelly_position_size(self, confidence, win_rate=0.75):
        """
        Optimal position sizing:
        f* = (μ - r_f)/σ² · min(1, L_max/CVaR) · C(t)
        Simplified Kelly: f* = (p*w - q*l)/(w*l) where p=win_rate, w=win_size, l=loss_size
        """
        p = win_rate
        w = self.target_return
        l = self.stop_loss

        kelly_frac = (p * w - (1 - p) * l) / (w * l) if (w * l) > 0 else 0
        kelly_frac = np.clip(kelly_frac, 0, 0.5)  # Conservative

        # Scale by confidence
        adjusted_fraction = kelly_frac * confidence

        return adjusted_fraction

    def execute_trade(self, prices, entry_idx, direction, confidence):
        """Execute trade with realistic dynamics"""
        entry_price = prices[entry_idx]

        # Slippage
        slippage_pct = np.random.uniform(0.0001, 0.0003)
        entry_price *= (1 + slippage_pct * direction)

        # Position size
        kelly_frac = self.kelly_position_size(confidence)
        position_size = self.capital * self.leverage * kelly_frac
        position_size = min(position_size, self.capital * self.leverage * self.max_position_fraction)

        # TP and SL
        take_profit = entry_price * (1 + direction * self.target_return)
        stop_loss = entry_price * (1 - direction * self.stop_loss)

        max_hold = 100

        for i in range(1, min(max_hold, len(prices) - entry_idx)):
            current_price = prices[entry_idx + i]

            # Check TP
            if (direction > 0 and current_price >= take_profit) or \
               (direction < 0 and current_price <= take_profit):
                pnl = position_size * self.target_return
                self.capital += pnl
                return {
                    'exit_idx': entry_idx + i,
                    'exit_reason': 'TP',
                    'pnl': pnl,
                    'return': self.target_return,
                    'bars_held': i,
                    'win': True,
                    'position_size': position_size
                }

            # Check SL
            if (direction > 0 and current_price <= stop_loss) or \
               (direction < 0 and current_price >= stop_loss):
                pnl = -position_size * self.stop_loss
                self.capital += pnl
                return {
                    'exit_idx': entry_idx + i,
                    'exit_reason': 'SL',
                    'pnl': pnl,
                    'return': -self.stop_loss,
                    'bars_held': i,
                    'win': False,
                    'position_size': position_size
                }

        # Timeout
        exit_price = prices[min(entry_idx + max_hold, len(prices) - 1)]
        pnl_pct = direction * (exit_price - entry_price) / entry_price
        pnl = position_size * pnl_pct
        self.capital += pnl

        return {
            'exit_idx': entry_idx + max_hold,
            'exit_reason': 'Timeout',
            'pnl': pnl,
            'return': pnl_pct,
            'bars_held': max_hold,
            'win': pnl > 0,
            'position_size': position_size
        }

    def run_backtest(self, target_trades=1000):
        """Run complete AEGFM-Ω backtest"""
        print("=" * 70)
        print("AEGFM-Ω COMPLETE IMPLEMENTATION BACKTEST")
        print("=" * 70)
        print(f"Initial Capital: ${self.capital:,.0f}")
        print(f"Leverage: {self.leverage}x")
        print(f"Target Trades: {target_trades}")
        print("\nGenerating market data with regime changes...")

        prices = self.generate_market_data(n_points=50000, regime_changes=True)
        print(f"Generated {len(prices):,} price bars")
        print(f"Price range: ${prices.min():.2f} - ${prices.max():.2f}")

        print("\nRunning AEGFM-Ω algorithm...\n")

        lookback = 150
        current_idx = lookback
        trade_count = 0
        signals_evaluated = 0

        while trade_count < target_trades and current_idx < len(prices) - 200:
            # Get historical window
            window = prices[max(0, current_idx - 100):current_idx]

            if len(window) < 50:
                current_idx += 1
                continue

            # Compute confidence and metrics
            try:
                confidence, E1, D_f, sig = self.compute_confidence(prices[:current_idx])
            except:
                current_idx += 1
                continue

            signals_evaluated += 1

            # Check trading conditions from paper
            trade_signal_1 = E1 < self.entropy_threshold
            trade_signal_2 = abs(D_f - 1.5) < 0.3
            trade_signal_3 = confidence >= self.confidence_threshold

            if trade_signal_1 and trade_signal_2 and trade_signal_3:
                # Predict next price
                pred_price = self.predict_next_price(prices[:current_idx])
                current_price = prices[current_idx]

                # Determine direction
                if pred_price > current_price * 1.001:
                    direction = 1  # Long
                elif pred_price < current_price * 0.999:
                    direction = -1  # Short
                else:
                    current_idx += 1
                    continue

                # Execute trade
                result = self.execute_trade(prices, current_idx, direction, confidence)

                # Update Koopman operator
                if current_idx > 10:
                    g_t = self.koopman.compute_observables(prices[:current_idx])
                    g_t_1 = self.koopman.compute_observables(prices[:current_idx+1])
                    self.koopman.update(g_t, g_t_1)

                # Record
                self.trades.append({
                    'trade_num': trade_count + 1,
                    'entry_idx': current_idx,
                    'direction': 'LONG' if direction > 0 else 'SHORT',
                    'confidence': confidence,
                    'E1': E1,
                    'D_f': D_f,
                    'prediction': pred_price,
                    'actual': current_price,
                    **result
                })

                self.equity_curve.append(self.capital)
                trade_count += 1

                if trade_count % 100 == 0:
                    wr = np.mean([t['win'] for t in self.trades])
                    avg_ret = np.mean([t['return'] for t in self.trades])
                    print(f"Trade {trade_count:4d} | Capital: ${self.capital:>12,.0f} | "
                          f"WinRate: {wr:>5.1%} | AvgRet: {avg_ret:>+6.3%} | "
                          f"Conf: {confidence:.3f}")

                current_idx = result['exit_idx'] + 5
            else:
                current_idx += 1

        print(f"\n{'=' * 70}")
        print(f"Evaluated {signals_evaluated:,} potential signals")
        print(f"Executed {trade_count} trades")
        print(f"Selectivity: {trade_count/signals_evaluated:.2%}")

        return self.analyze_results()

    def analyze_results(self):
        """Detailed analysis"""
        df = pd.DataFrame(self.trades)

        print("\n" + "=" * 70)
        print("RESULTS ANALYSIS")
        print("=" * 70)

        total_return = (self.capital - self.initial_capital) / self.initial_capital
        wins = df[df['win'] == True]
        losses = df[df['win'] == False]
        win_rate = len(wins) / len(df)

        print(f"\n📊 PERFORMANCE:")
        print(f"   Final Capital:       ${self.capital:,.2f}")
        print(f"   Total Return:        {total_return:+.2%}")
        print(f"   P&L:                 ${self.capital - self.initial_capital:+,.2f}")

        print(f"\n📈 WIN/LOSS:")
        print(f"   Total Trades:        {len(df)}")
        print(f"   Wins:                {len(wins)} ({len(wins)/len(df):.2%})")
        print(f"   Losses:              {len(losses)} ({len(losses)/len(df):.2%})")
        print(f"   Win Rate:            {win_rate:.2%}")
        print(f"   ✓ Target (75%):      {'✅ ACHIEVED' if win_rate >= 0.75 else '❌ MISSED'}")

        print(f"\n💰 RETURNS:")
        print(f"   Average Return:      {df['return'].mean():+.3%}")
        print(f"   Average Win:         {wins['return'].mean():+.3%}")
        print(f"   Average Loss:        {losses['return'].mean():+.3%}")
        print(f"   Best Trade:          {df['return'].max():+.3%}")
        print(f"   Worst Trade:         {df['return'].min():+.3%}")

        if len(losses) > 0 and losses['pnl'].sum() != 0:
            pf = abs(wins['pnl'].sum() / losses['pnl'].sum())
            print(f"   Profit Factor:       {pf:.2f}")

        print(f"\n📉 RISK:")
        equity = pd.Series(self.equity_curve)
        drawdowns = (equity - equity.cummax()) / equity.cummax()
        print(f"   Max Drawdown:        {drawdowns.min():.2%}")
        print(f"   Return Volatility:   {df['return'].std():.3%}")

        if df['return'].std() > 0:
            sharpe = df['return'].mean() / df['return'].std() * np.sqrt(252 * 390)
            print(f"   Sharpe Ratio:        {sharpe:.2f}")

        print(f"\n🎯 CONFIDENCE METRICS:")
        print(f"   Avg Confidence:      {df['confidence'].mean():.3f}")
        print(f"   Avg E₁:              {df['E1'].mean():.3f}")
        print(f"   Avg D_f:             {df['D_f'].mean():.3f}")

        print(f"\n🔬 50% DAILY TARGET TEST:")
        avg_ret = df['return'].mean()
        compound_100 = (1 + avg_ret) ** 100 - 1
        print(f"   Avg return/trade:    {avg_ret:+.3%}")
        print(f"   (1 + r)^100:         {compound_100:+.2%}")
        print(f"   Target (50%):        {'✅ POSSIBLE' if compound_100 >= 0.50 else '❌ IMPOSSIBLE'}")

        print(f"\n{'=' * 70}")
        print("VERDICT:")
        print("=" * 70)

        if win_rate >= 0.75 and total_return > 0:
            print("✅ Framework ACHIEVES claimed 75%+ win rate and profits!")
        elif win_rate >= 0.70:
            print("⚠️  Framework achieves 70%+ (good but below 75% claim)")
        elif win_rate >= 0.60:
            print("❌ Framework ~60% (good but not revolutionary)")
        else:
            print("❌ Framework FAILS to achieve claimed performance")

        print(f"{'=' * 70}\n")

        return df


def main():
    """Run full AEGFM-Ω implementation"""
    aegfm = AEGFMOmega(initial_capital=100000, leverage=10)

    results = aegfm.run_backtest(target_trades=1000)

    # Save results
    results.to_csv('/home/user/tradelocker/aegfm_full_results.csv', index=False)
    print("💾 Results saved to: aegfm_full_results.csv\n")

    # Create visualizations
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    # Equity curve
    axes[0, 0].plot(aegfm.equity_curve, linewidth=2)
    axes[0, 0].axhline(y=aegfm.initial_capital, color='gray', linestyle='--', label='Initial')
    axes[0, 0].set_title('Equity Curve', fontsize=14, fontweight='bold')
    axes[0, 0].set_xlabel('Trade Number')
    axes[0, 0].set_ylabel('Capital ($)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))

    # Returns distribution
    axes[0, 1].hist(results['return'], bins=50, alpha=0.7, color='steelblue', edgecolor='black')
    axes[0, 1].axvline(x=0, color='red', linestyle='--', linewidth=2, label='Break-even')
    axes[0, 1].axvline(x=results['return'].mean(), color='green', linestyle='-', linewidth=2, label='Mean')
    axes[0, 1].set_title('Return Distribution', fontsize=14, fontweight='bold')
    axes[0, 1].set_xlabel('Return per Trade')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # Rolling win rate
    rolling_wr = results['win'].rolling(window=50, min_periods=10).mean()
    axes[1, 0].plot(rolling_wr, linewidth=2, label='Rolling WR (50 trades)')
    axes[1, 0].axhline(y=0.75, color='green', linestyle='--', linewidth=2, label='Target 75%')
    axes[1, 0].axhline(y=0.50, color='orange', linestyle='--', linewidth=2, label='Random 50%')
    axes[1, 0].fill_between(range(len(rolling_wr)), 0.75, rolling_wr,
                            where=(rolling_wr >= 0.75), alpha=0.3, color='green')
    axes[1, 0].set_title('Rolling Win Rate', fontsize=14, fontweight='bold')
    axes[1, 0].set_xlabel('Trade Number')
    axes[1, 0].set_ylabel('Win Rate')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].set_ylim(0.2, 1.0)

    # Confidence vs outcome
    wins = results[results['win'] == True]
    losses = results[results['win'] == False]
    axes[1, 1].scatter(wins.index, wins['confidence'], alpha=0.6, s=30, c='green', label='Wins', edgecolors='darkgreen')
    axes[1, 1].scatter(losses.index, losses['confidence'], alpha=0.6, s=30, c='red', label='Losses', edgecolors='darkred')
    axes[1, 1].axhline(y=0.75, color='blue', linestyle='--', linewidth=2, label='Threshold')
    axes[1, 1].set_title('Confidence Score vs Outcome', fontsize=14, fontweight='bold')
    axes[1, 1].set_xlabel('Trade Number')
    axes[1, 1].set_ylabel('Confidence')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/tradelocker/aegfm_full_analysis.png', dpi=150, bbox_inches='tight')
    print("📊 Charts saved to: aegfm_full_analysis.png")
    print("\n✅ Complete simulation finished!\n")


if __name__ == "__main__":
    main()
