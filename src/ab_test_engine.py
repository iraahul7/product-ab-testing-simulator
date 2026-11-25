"""
Product Experimentation & A/B Testing Statistical Engine
Author: Rahul
"""

import numpy as np
import pandas as pd
from scipy import stats


def calculate_sample_size(baseline_rate: float, mde: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Calculate required sample size per variant for a two-proportion z-test."""
    p1 = baseline_rate
    p2 = baseline_rate + mde
    p_pooled = (p1 + p2) / 2.0
    z_alpha = stats.norm.ppf(1 - alpha / 2.0)
    z_beta = stats.norm.ppf(power)
    n = ((z_alpha * np.sqrt(2 * p_pooled * (1 - p_pooled)) +
          z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / ((p2 - p1) ** 2)
    return int(np.ceil(n))


def simulate_experiment(n_users: int = 40000, seed: int = 42) -> pd.DataFrame:
    """Generate a 40,000-user randomized checkout A/B test dataset."""
    rng = np.random.default_rng(seed)
    variant = rng.choice(["Control", "Treatment"], size=n_users, p=[0.50, 0.50])
    device = rng.choice(["Mobile", "Desktop"], size=n_users, p=[0.72, 0.28])

    conv_prob = np.where(variant == "Control", 0.214, 0.256)
    converted = rng.binomial(1, conv_prob)
    order_value = np.where(
        converted == 1,
        np.round(rng.normal(loc=1485, scale=390, size=n_users).clip(299, 6000), 2),
        0.0
    )

    return pd.DataFrame({
        "user_id": range(100001, 100001 + n_users),
        "variant": variant,
        "device": device,
        "converted": converted,
        "order_value_inr": order_value
    })


def evaluate_ab_test(df: pd.DataFrame) -> dict:
    """Run two-proportion z-test and 95% confidence interval estimation."""
    ctrl = df[df["variant"] == "Control"]
    trt = df[df["variant"] == "Treatment"]

    n_c, x_c = len(ctrl), ctrl["converted"].sum()
    n_t, x_t = len(trt), trt["converted"].sum()

    p_c = x_c / n_c
    p_t = x_t / n_t
    diff = p_t - p_c

    p_pool = (x_c + x_t) / (n_c + n_t)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / n_c + 1 / n_t))
    z_stat = diff / se_pool
    p_val = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    se_unpooled = np.sqrt((p_c * (1 - p_c) / n_c) + (p_t * (1 - p_t) / n_t))
    ci_low = diff - 1.96 * se_unpooled
    ci_high = diff + 1.96 * se_unpooled

    return {
        "n_control": n_c,
        "n_treatment": n_t,
        "control_rate": p_c,
        "treatment_rate": p_t,
        "absolute_lift": diff,
        "relative_lift": diff / p_c,
        "z_stat": z_stat,
        "p_value": p_val,
        "ci_95": (ci_low, ci_high)
    }


if __name__ == "__main__":
    req_n = calculate_sample_size(baseline_rate=0.214, mde=0.02)
    print(f"Minimum Sample Size Required per Variant (2% MDE, 80% Power): {req_n:,}")

    df = simulate_experiment(40000)
    df.to_csv("data/ab_experiment_40k_users.csv", index=False)
    res = evaluate_ab_test(df)

    print(f"Control Conversion:   {res['control_rate']:.2%} (n={res['n_control']:,})")
    print(f"Treatment Conversion: {res['treatment_rate']:.2%} (n={res['n_treatment']:,})")
    print(f"Absolute Lift:        +{res['absolute_lift']:.2%} (Relative: +{res['relative_lift']:.2%})")
    print(f"95% Confidence Int:   [+{res['ci_95'][0]:.2%}, +{res['ci_95'][1]:.2%}]")
    print(f"Z-Statistic:          {res['z_stat']:.4f} | P-Value: {res['p_value']:.4e}")
