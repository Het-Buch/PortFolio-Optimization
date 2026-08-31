"""PSO/GWO/BAT portfolio optimization + risk metrics. Pure NumPy. Self-check: python -m ml.optimizers"""

import numpy as np

RISK_FREE = 0.065  # ~India 10y G-Sec
MAX_WEIGHT = 0.35  # unconstrained max-Sharpe always corners into one asset
TRADING_DAYS = 252


# ---------------------------------------------------------------- risk model

def annualized_stats(prices):
    """(mean returns, covariance) annualized from a price DataFrame.

    Ledoit-Wolf shrinkage when available: sample covariance on 5-20 assets with
    limited history is badly conditioned, and shrinkage is the standard remedy.
    """
    rets = prices.pct_change().dropna(how="all").dropna(axis=1, how="all")
    if rets.empty or rets.shape[0] < 2:
        n = max(prices.shape[1], 1)
        return np.zeros(n), np.eye(n) * 0.04

    rets = rets.fillna(0.0)
    mu = rets.mean().to_numpy() * TRADING_DAYS

    try:
        from sklearn.covariance import LedoitWolf
        cov = LedoitWolf().fit(rets.to_numpy()).covariance_ * TRADING_DAYS
    except Exception:
        cov = rets.cov().to_numpy() * TRADING_DAYS

    # Guard against a singular matrix from duplicate/constant columns.
    cov = cov + np.eye(len(cov)) * 1e-8
    return mu, cov


def portfolio_stats(w, mu, cov):
    ret = float(w @ mu)
    vol = float(np.sqrt(max(w @ cov @ w, 1e-12)))
    return ret, vol


def sharpe(w, mu, cov, rf=RISK_FREE):
    ret, vol = portfolio_stats(w, mu, cov)
    return (ret - rf) / vol


def risk_metrics(weights, prices, rf=RISK_FREE):
    """VaR/CVaR/drawdown/Sortino for a weighting, from historical returns."""
    rets = prices.pct_change().dropna(how="all").fillna(0.0)
    if rets.empty:
        return {}
    port = rets.to_numpy() @ np.asarray(weights, dtype=float)

    curve = np.cumprod(1 + port)
    drawdown = float((curve / np.maximum.accumulate(curve) - 1).min())

    downside = port[port < 0]
    dn_vol = float(downside.std() * np.sqrt(TRADING_DAYS)) if downside.size else 0.0
    ann_ret = float(port.mean() * TRADING_DAYS)

    return {
        "var_95": float(np.percentile(port, 5)),
        "cvar_95": float(port[port <= np.percentile(port, 5)].mean()) if port.size else 0.0,
        "max_drawdown": drawdown,
        "sortino": (ann_ret - rf) / dn_vol if dn_vol > 0 else 0.0,
        "calmar": ann_ret / abs(drawdown) if drawdown < 0 else 0.0,
    }


# ------------------------------------------------------------------- helpers

def _repair(x, cap=MAX_WEIGHT):
    """Project onto the long-only simplex, honouring a per-asset cap."""
    x = np.clip(np.atleast_2d(x).astype(float), 0, None)

    for row in x:
        s = row.sum()
        row[:] = np.ones_like(row) / len(row) if s <= 1e-12 else row / s

        # A cap below equal weight is infeasible; leave the row normalized.
        if cap is None or cap * len(row) < 1.0 - 1e-9:
            continue

        # Redistribute excess in proportion to existing weights, so the search
        # signal survives -- spreading it evenly would flatten every candidate.
        for _ in range(50):
            over = row > cap + 1e-12
            if not over.any():
                break
            excess = float((row[over] - cap).sum())
            row[over] = cap
            under = row < cap - 1e-12
            if not under.any():
                break
            pool = float(row[under].sum())
            if pool <= 1e-12:
                row[under] += excess / under.sum()
            else:
                row[under] += row[under] / pool * excess
        np.clip(row, 0, cap, out=row)
        row /= row.sum()

    return x


def _score(pop, fn):
    return np.array([fn(w) for w in pop])


def _init(n_assets, size, rng):
    return _repair(rng.random((size, n_assets)))


# -------------------------------------------------------------- optimizers

def pso(fn, n_assets, size=30, iters=100, seed=0, w=0.7, c1=1.5, c2=1.5):
    """Particle Swarm. Minimizes fn."""
    rng = np.random.default_rng(seed)
    pos = _init(n_assets, size, rng)
    vel = np.zeros_like(pos)

    pbest, pbest_val = pos.copy(), _score(pos, fn)
    g = int(pbest_val.argmin())
    gbest, gbest_val = pbest[g].copy(), float(pbest_val[g])

    for _ in range(iters):
        r1, r2 = rng.random(pos.shape), rng.random(pos.shape)
        vel = w * vel + c1 * r1 * (pbest - pos) + c2 * r2 * (gbest - pos)
        pos = _repair(pos + vel)

        val = _score(pos, fn)
        better = val < pbest_val
        pbest[better], pbest_val[better] = pos[better], val[better]

        g = int(pbest_val.argmin())
        if pbest_val[g] < gbest_val:
            gbest, gbest_val = pbest[g].copy(), float(pbest_val[g])

    return gbest, gbest_val


def gwo(fn, n_assets, size=30, iters=100, seed=0):
    """Grey Wolf. Alpha/beta/delta encircle the prey; `a` decays 2 -> 0."""
    rng = np.random.default_rng(seed)
    pop = _init(n_assets, size, rng)

    for t in range(iters):
        val = _score(pop, fn)
        order = np.argsort(val)
        alpha, beta, delta = pop[order[0]], pop[order[1]], pop[order[2]]

        a = 2 - 2 * t / max(iters - 1, 1)
        new = np.empty_like(pop)
        for i, x in enumerate(pop):
            xs = []
            for leader in (alpha, beta, delta):
                A = 2 * a * rng.random(n_assets) - a
                C = 2 * rng.random(n_assets)
                xs.append(leader - A * np.abs(C * leader - x))
            new[i] = np.mean(xs, axis=0)
        pop = _repair(new)

    val = _score(pop, fn)
    best = int(val.argmin())
    return pop[best], float(val[best])


def bat(fn, n_assets, size=30, iters=100, seed=0,
        loudness=0.5, pulse=0.5, fmin=0.0, fmax=2.0):
    """Bat Algorithm. Frequency-tuned flight + local random walk."""
    rng = np.random.default_rng(seed)
    pop = _init(n_assets, size, rng)
    vel = np.zeros_like(pop)
    val = _score(pop, fn)

    b = int(val.argmin())
    best, best_val = pop[b].copy(), float(val[b])

    for _ in range(iters):
        freq = fmin + (fmax - fmin) * rng.random((size, 1))
        vel = vel + (pop - best) * freq
        cand = _repair(pop + vel)

        # Local search around the current best for a subset of the swarm.
        local = rng.random(size) > pulse
        if local.any():
            cand[local] = _repair(best + 0.01 * rng.normal(size=(local.sum(), n_assets)))

        cand_val = _score(cand, fn)
        accept = (cand_val < val) & (rng.random(size) < loudness)
        pop[accept], val[accept] = cand[accept], cand_val[accept]

        b = int(val.argmin())
        if val[b] < best_val:
            best, best_val = pop[b].copy(), float(val[b])

    return best, best_val


def slsqp(fn, n_assets, **_):
    """Convex baseline. Without a reference optimum there is no way to tell a
    working swarm from a broken one."""
    from scipy.optimize import minimize
    x0 = np.ones(n_assets) / n_assets
    res = minimize(
        lambda x: fn(_repair(x)[0]), x0, method="SLSQP",
        bounds=[(0.0, 1.0)] * n_assets,
        constraints=({"type": "eq", "fun": lambda x: x.sum() - 1},),
        options={"maxiter": 200, "ftol": 1e-9},
    )
    w = _repair(res.x)[0]
    return w, float(fn(w))


# -------------------------------------------------- hybrids and ensembles

def pso_gwo(fn, n_assets, seed=0, **kw):
    """PSO explores, GWO refines around its result."""
    w1, _ = pso(fn, n_assets, seed=seed, iters=60, **kw)
    w2, v2 = gwo(fn, n_assets, seed=seed + 1, iters=60, **kw)
    return (w1, fn(w1)) if fn(w1) < v2 else (w2, v2)


def gwo_bat(fn, n_assets, seed=0, **kw):
    w1, v1 = gwo(fn, n_assets, seed=seed, iters=60, **kw)
    w2, v2 = bat(fn, n_assets, seed=seed + 1, iters=60, **kw)
    return (w1, v1) if v1 < v2 else (w2, v2)


def ensemble(fn, n_assets, seed=0, **kw):
    """Average the three swarms' weights, keep it only if it actually wins."""
    results = [algo(fn, n_assets, seed=seed, **kw)
               for algo in (pso, gwo, bat)]
    avg = _repair(np.mean([w for w, _ in results], axis=0))[0]
    best_w, best_v = min(results, key=lambda r: r[1])
    return (avg, fn(avg)) if fn(avg) < best_v else (best_w, best_v)


ALGORITHMS = {
    "PSO": pso, "GWO": gwo, "BAT": bat, "SLSQP": slsqp,
    "PSO->GWO": pso_gwo, "GWO->BAT": gwo_bat, "Ensemble": ensemble,
}


def optimize(prices, algorithm="PSO", rf=RISK_FREE, seed=0):
    """Maximize Sharpe for the given price history. Returns weights + metrics."""
    mu, cov = annualized_stats(prices)
    n = len(mu)
    if n == 0:
        return np.array([]), {}
    if n == 1:
        w = np.ones(1)
        ret, vol = portfolio_stats(w, mu, cov)
        return w, {"expected_return": ret, "risk": vol,
                   "sharpe": sharpe(w, mu, cov, rf), "algorithm": algorithm}

    fn = lambda w: -sharpe(w, mu, cov, rf)
    solver = ALGORITHMS.get(algorithm, pso)
    w, _ = solver(fn, n, seed=seed)

    ret, vol = portfolio_stats(w, mu, cov)
    return w, {"expected_return": ret, "risk": vol,
               "sharpe": sharpe(w, mu, cov, rf), "algorithm": algorithm}


def compare(prices, rf=RISK_FREE, seed=0):
    """Every algorithm on the same problem -- the report's comparison table."""
    mu, cov = annualized_stats(prices)
    n = len(mu)
    if n < 2:
        return {}
    fn = lambda w: -sharpe(w, mu, cov, rf)

    out = {}
    for name, solver in ALGORITHMS.items():
        w, _ = solver(fn, n, seed=seed)
        ret, vol = portfolio_stats(w, mu, cov)
        out[name] = {"weights": w, "expected_return": ret,
                     "risk": vol, "sharpe": sharpe(w, mu, cov, rf)}
    return out


# ------------------------------------------------------------- self-check

def _self_check():
    rng = np.random.default_rng(0)
    n, days = 4, 500

    # Asset 0 is deliberately the best: highest drift, lowest vol.
    drift = np.array([0.0012, 0.0004, 0.0003, 0.0002])
    vol = np.array([0.008, 0.020, 0.022, 0.025])
    rets = rng.normal(drift, vol, size=(days, n))

    import pandas as pd
    prices = pd.DataFrame(100 * np.cumprod(1 + rets, axis=0),
                          columns=list("ABCD"))

    mu, cov = annualized_stats(prices)
    assert cov.shape == (n, n), cov.shape
    assert np.allclose(cov, cov.T), "covariance must be symmetric"
    assert np.linalg.eigvalsh(cov).min() > 0, "covariance must be positive definite"

    ref_w, ref = slsqp(lambda w: -sharpe(w, mu, cov), n)

    for name, solver in ALGORITHMS.items():
        w, _ = solver(lambda w: -sharpe(w, mu, cov), n, seed=1)
        assert w.shape == (n,), f"{name}: bad shape {w.shape}"
        assert abs(w.sum() - 1) < 1e-6, f"{name}: weights sum to {w.sum()}"
        assert (w >= -1e-9).all(), f"{name}: negative weight {w}"
        # Must be in the same league as the convex optimum, and beat equal weight.
        got = sharpe(w, mu, cov)
        assert got > sharpe(np.ones(n) / n, mu, cov), f"{name}: lost to equal-weight"
        assert got > -ref * 0.95, f"{name}: sharpe {got:.3f} vs capped optimum {-ref:.3f}"
        assert w[0] >= MAX_WEIGHT - 1e-6, f"{name}: did not max out the dominant asset ({w[0]:.2f})"
        print(f"  {name:<10} sharpe={got:6.3f}  w={np.round(w, 3)}")

    m = risk_metrics(ref_w, prices)
    assert m["max_drawdown"] <= 0, m
    assert m["var_95"] < 0, m
    print(f"  risk       { {k: round(v, 4) for k, v in m.items()} }")
    print("optimizers: OK")


if __name__ == "__main__":
    _self_check()
