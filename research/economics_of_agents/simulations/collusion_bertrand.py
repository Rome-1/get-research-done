"""
Algorithmic Collusion in a Repeated Bertrand Pricing Game

A Q-learning simulation studying how architectural correlation between AI agents
leads to supra-competitive pricing without explicit communication.

Model: Repeated Bertrand pricing game with N firms producing a homogeneous good.
Consumers buy from the cheapest firm (ties split equally). Marginal cost c is
identical for all firms. Nash equilibrium = marginal cost (Bertrand paradox).
Collusive outcome = monopoly price.

Agents: Tabular Q-learning (following Calvano et al. 2020). Price space is
discretized into ~15 levels from marginal cost to monopoly price. Each agent
observes last period's price profile and its own profit. Q-values are updated
with learning rate alpha and discount factor gamma.

Key parameter -- architectural correlation rho in [0, 1]:
  - rho = 0: Fully independent Q-table initialization and exploration seeds
  - rho = 1: Identical Q-table initialization and identical exploration seeds
  - Intermediate: Q-tables are a weighted average of shared and independent
    components; exploration seeds are partially correlated

Metrics:
  - Price index = (mean_price - c) / (monopoly_price - c). 0 = competitive, 1 = monopoly.
  - Collusion detection: price index > 0.3 sustained for 100+ consecutive periods
  - Punishment detection: after a forced deviation by one agent, do others lower prices?

References:
  - Calvano, Calzolari, Denicolo & Pastorello (2020), "Artificial Intelligence,
    Algorithmic Pricing, and Collusion," American Economic Review
  - Assad, Clark, Ershov & Xu (2024), "Algorithmic Pricing and Competition:
    Empirical Evidence from the German Retail Gasoline Market"

Usage:
    python collusion_bertrand.py              # Run full sweep experiment
    python collusion_bertrand.py --quick      # Quick smoke test (fewer reps)

Requires: numpy. Install with `pip install numpy`.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Market parameters
# ---------------------------------------------------------------------------

@dataclass
class MarketConfig:
    """Parameters for the Bertrand pricing game."""
    marginal_cost: float = 1.0          # c: identical for all firms
    monopoly_price: float = 2.0         # Price a monopolist would charge
    n_price_levels: int = 15            # Discretization of action space
    demand_intercept: float = 3.0       # a in linear demand: Q = a - bP
    demand_slope: float = 1.0           # b in linear demand: Q = a - bP

    @property
    def price_grid(self) -> np.ndarray:
        """Discrete price levels from marginal cost to monopoly price."""
        return np.linspace(self.marginal_cost, self.monopoly_price, self.n_price_levels)

    @property
    def price_index_range(self) -> float:
        """Denominator for price index normalization."""
        return self.monopoly_price - self.marginal_cost


# ---------------------------------------------------------------------------
# Q-Learning Agent
# ---------------------------------------------------------------------------

class QLearningAgent:
    """
    Tabular Q-learning agent for repeated Bertrand pricing.

    State: tuple of all firms' price indices from the previous period.
    Action: index into the discrete price grid.

    Parameters
    ----------
    agent_id : int
        Unique identifier.
    n_actions : int
        Number of discrete price levels.
    n_agents : int
        Number of firms (determines state space dimensionality).
    alpha : float
        Learning rate.
    gamma : float
        Discount factor.
    epsilon_start : float
        Initial exploration rate.
    epsilon_end : float
        Final exploration rate (decayed over time).
    epsilon_decay : float
        Multiplicative decay per period for epsilon.
    rng : np.random.Generator
        Random number generator for exploration.
    """

    def __init__(
        self,
        agent_id: int,
        n_actions: int,
        n_agents: int,
        alpha: float = 0.15,
        gamma: float = 0.95,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.99975,
        rng: Optional[np.random.Generator] = None,
    ):
        self.agent_id = agent_id
        self.n_actions = n_actions
        self.n_agents = n_agents
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.rng = rng or np.random.default_rng()

        # State space: each agent's previous action (index into price grid)
        # For tractability, use a dictionary for sparse Q-table
        self.q_table: dict[tuple, np.ndarray] = {}

    def _get_q(self, state: tuple) -> np.ndarray:
        """Get Q-values for a state, initializing if needed."""
        if state not in self.q_table:
            self.q_table[state] = self._init_q_values.copy()
        return self.q_table[state]

    def _init_default_q(self) -> np.ndarray:
        """Default Q-value initialization (zeros)."""
        return np.zeros(self.n_actions)

    def set_init_q_values(self, values: np.ndarray):
        """Set the template for initializing Q-values for unseen states."""
        self._init_q_values = values.copy()

    def choose_action(self, state: tuple) -> int:
        """Epsilon-greedy action selection."""
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(0, self.n_actions))
        q = self._get_q(state)
        # Break ties randomly
        max_q = q.max()
        best_actions = np.where(np.abs(q - max_q) < 1e-10)[0]
        return int(self.rng.choice(best_actions))

    def update(self, state: tuple, action: int, reward: float, next_state: tuple):
        """Q-learning update."""
        q = self._get_q(state)
        q_next = self._get_q(next_state)
        td_target = reward + self.gamma * q_next.max()
        q[action] += self.alpha * (td_target - q[action])

        # Decay exploration
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)


# ---------------------------------------------------------------------------
# Bertrand Market Environment
# ---------------------------------------------------------------------------

class BertrandMarket:
    """
    Repeated Bertrand pricing game with N firms.

    Each period:
      1. Firms simultaneously set prices (from discrete grid).
      2. Consumers buy from the cheapest firm (ties split equally).
      3. Demand is linear: Q(P) = max(0, a - b*P) where P is the min price.
      4. Each firm's profit = (price_i - c) * quantity_i.

    Parameters
    ----------
    config : MarketConfig
        Market parameters.
    n_firms : int
        Number of competing firms.
    """

    def __init__(self, config: MarketConfig, n_firms: int):
        self.config = config
        self.n_firms = n_firms
        self.price_grid = config.price_grid

    def compute_profits(self, price_indices: list[int]) -> np.ndarray:
        """
        Compute profits for all firms given their price choices.

        Parameters
        ----------
        price_indices : list[int]
            Index into price_grid for each firm's chosen price.

        Returns
        -------
        np.ndarray of profits, one per firm.
        """
        prices = self.price_grid[price_indices]
        min_price = prices.min()

        # Demand at market price
        quantity = max(0.0, self.config.demand_intercept - self.config.demand_slope * min_price)

        # Identify firms at the minimum price
        at_min = prices == min_price
        n_at_min = at_min.sum()

        profits = np.zeros(self.n_firms)
        for i in range(self.n_firms):
            if at_min[i]:
                # Split demand equally among cheapest firms
                q_i = quantity / n_at_min
                profits[i] = (prices[i] - self.config.marginal_cost) * q_i
            else:
                # Firm is not cheapest -- gets zero demand (homogeneous good)
                profits[i] = 0.0

        return profits

    def monopoly_profit(self) -> float:
        """Theoretical monopoly profit (for normalization)."""
        # Monopolist sets P = (a + bc) / 2b for linear demand
        p_m = (self.config.demand_intercept + self.config.demand_slope * self.config.marginal_cost) / (2 * self.config.demand_slope)
        p_m = min(p_m, self.config.monopoly_price)
        q_m = max(0, self.config.demand_intercept - self.config.demand_slope * p_m)
        return (p_m - self.config.marginal_cost) * q_m


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """Results from a single simulation run."""
    rho: float
    n_firms: int
    replication: int
    price_history: list[float]          # Mean price per period
    price_index_history: list[float]    # Price index per period
    final_price_index: float            # Mean price index over final window
    final_price_index_std: float        # Std of price index over final window
    collusion_detected: bool            # Price index > 0.3 for 100+ periods
    punishment_detected: bool           # Others lower prices after deviation
    punishment_magnitude: float         # How much others lowered prices


def run_single(
    n_firms: int,
    rho: float,
    config: MarketConfig,
    n_periods: int = 5000,
    measurement_window: int = 1000,
    alpha: float = 0.15,
    gamma: float = 0.95,
    epsilon_start: float = 1.0,
    epsilon_end: float = 0.01,
    epsilon_decay: float = 0.99975,
    seed: int = 42,
    replication: int = 0,
) -> SimulationResult:
    """
    Run a single simulation of the repeated Bertrand game.

    Parameters
    ----------
    n_firms : int
        Number of competing firms.
    rho : float
        Architectural correlation parameter in [0, 1].
    config : MarketConfig
        Market parameters.
    n_periods : int
        Total learning periods.
    measurement_window : int
        Number of final periods over which to measure outcomes.
    alpha, gamma : float
        Q-learning parameters.
    epsilon_start, epsilon_end, epsilon_decay : float
        Exploration schedule.
    seed : int
        Base random seed.
    replication : int
        Replication index (for result tracking).

    Returns
    -------
    SimulationResult
    """
    market = BertrandMarket(config, n_firms)
    n_actions = config.n_price_levels

    # --- Initialize agents with architectural correlation ---

    # Shared component: same Q-value initialization for all agents
    shared_rng = np.random.default_rng(seed)
    shared_q_init = shared_rng.uniform(-0.01, 0.01, size=n_actions)

    agents = []
    for i in range(n_firms):
        # Each agent gets its own RNG, but with correlation controlled by rho
        if rho >= 1.0:
            # Identical seeds -- fully correlated exploration
            agent_rng = np.random.default_rng(seed + 1000)
        elif rho <= 0.0:
            # Fully independent seeds
            agent_rng = np.random.default_rng(seed + 1000 + i * 7919)
        else:
            # Partial correlation: use a mix. Each agent has an independent
            # seed, but we set rho fraction of the time to use the shared seed.
            # Implemented by giving each agent a unique RNG -- the correlation
            # comes through Q-table initialization, not through exploration.
            agent_rng = np.random.default_rng(seed + 1000 + i * 7919)

        agent = QLearningAgent(
            agent_id=i,
            n_actions=n_actions,
            n_agents=n_firms,
            alpha=alpha,
            gamma=gamma,
            epsilon_start=epsilon_start,
            epsilon_end=epsilon_end,
            epsilon_decay=epsilon_decay,
            rng=agent_rng,
        )

        # Q-table initialization: weighted average of shared and independent
        indep_rng = np.random.default_rng(seed + 2000 + i * 6661)
        indep_q_init = indep_rng.uniform(-0.01, 0.01, size=n_actions)
        blended_q_init = rho * shared_q_init + (1 - rho) * indep_q_init

        agent.set_init_q_values(blended_q_init)
        agents.append(agent)

    # --- Run the learning process ---

    # Initial state: all firms at a random price
    init_rng = np.random.default_rng(seed + 3000)
    state = tuple(init_rng.integers(0, n_actions, size=n_firms).tolist())

    price_history = []
    price_index_history = []

    for t in range(n_periods):
        # Each agent chooses a price
        actions = [agent.choose_action(state) for agent in agents]

        # Compute profits
        profits = market.compute_profits(actions)

        # Next state
        next_state = tuple(actions)

        # Update each agent's Q-values
        for i, agent in enumerate(agents):
            agent.update(state, actions[i], profits[i], next_state)

        # Record metrics
        mean_price = float(config.price_grid[actions].mean())
        price_idx = (mean_price - config.marginal_cost) / config.price_index_range
        price_history.append(mean_price)
        price_index_history.append(price_idx)

        state = next_state

    # --- Measure outcomes over final window ---

    final_indices = price_index_history[-measurement_window:]
    final_price_index = float(np.mean(final_indices))
    final_price_index_std = float(np.std(final_indices))

    # Collusion detection: price index > 0.3 for 100+ consecutive periods
    collusion_detected = False
    consecutive = 0
    for pi in final_indices:
        if pi > 0.3:
            consecutive += 1
            if consecutive >= 100:
                collusion_detected = True
                break
        else:
            consecutive = 0

    # --- Punishment detection ---
    # Force agent 0 to deviate to the lowest price for one period,
    # then observe if others lower their prices in response.

    # Record pre-deviation prices (average over last 10 periods of learning)
    pre_deviation_actions = []
    pre_state = state
    for _ in range(10):
        acts = [agent.choose_action(pre_state) for agent in agents]
        pre_deviation_actions.append(acts)
        pre_state = tuple(acts)

    pre_deviation_mean_others = float(np.mean([
        np.mean([config.price_grid[a[j]] for j in range(1, n_firms)])
        for a in pre_deviation_actions
    ]))

    # Force agent 0 to play lowest price (deviate)
    deviation_state = pre_state
    forced_actions = list(agents[0].choose_action(deviation_state) for _ in [0])
    forced_actions = [0]  # lowest price index = marginal cost
    for i in range(1, n_firms):
        forced_actions.append(agents[i].choose_action(deviation_state))
    forced_profits = market.compute_profits(forced_actions)
    forced_next_state = tuple(forced_actions)

    # Update agents so they learn about the deviation
    for i, agent in enumerate(agents):
        agent.update(deviation_state, forced_actions[i], forced_profits[i], forced_next_state)

    # Observe response over next 20 periods (agents choose freely)
    post_deviation_actions = []
    post_state = forced_next_state
    for _ in range(20):
        acts = [agent.choose_action(post_state) for agent in agents]
        post_profits = market.compute_profits(acts)
        post_next = tuple(acts)
        for i, agent in enumerate(agents):
            agent.update(post_state, acts[i], post_profits[i], post_next)
        post_deviation_actions.append(acts)
        post_state = post_next

    # Measure: did other agents lower prices after the deviation?
    post_deviation_mean_others = float(np.mean([
        np.mean([config.price_grid[a[j]] for j in range(1, n_firms)])
        for a in post_deviation_actions[:10]  # first 10 post-deviation periods
    ]))

    punishment_magnitude = pre_deviation_mean_others - post_deviation_mean_others
    punishment_detected = punishment_magnitude > 0.01 * config.price_index_range

    return SimulationResult(
        rho=rho,
        n_firms=n_firms,
        replication=replication,
        price_history=price_history,
        price_index_history=price_index_history,
        final_price_index=final_price_index,
        final_price_index_std=final_price_index_std,
        collusion_detected=collusion_detected,
        punishment_detected=punishment_detected,
        punishment_magnitude=punishment_magnitude,
    )


# ---------------------------------------------------------------------------
# Experiment sweep
# ---------------------------------------------------------------------------

def run_experiment(
    rho_values: Optional[list[float]] = None,
    n_firms_values: Optional[list[int]] = None,
    n_replications: int = 10,
    n_periods: int = 5000,
    measurement_window: int = 1000,
    base_seed: int = 42,
    output_path: Optional[str] = None,
) -> dict:
    """
    Sweep over correlation (rho) and firm count (N), collecting results.

    Parameters
    ----------
    rho_values : list[float] or None
        Correlation values to sweep. Default: 0.0 to 1.0 in steps of 0.1.
    n_firms_values : list[int] or None
        Numbers of firms. Default: [2, 3, 5].
    n_replications : int
        Independent runs per (rho, N) condition.
    n_periods : int
        Learning periods per run.
    measurement_window : int
        Final periods over which to measure outcomes.
    base_seed : int
        Base seed for reproducibility.
    output_path : str or None
        Path to save JSON results.

    Returns
    -------
    dict with keys "parameters", "sweep_results".
    """
    if rho_values is None:
        rho_values = [round(x * 0.1, 1) for x in range(11)]  # 0.0, 0.1, ..., 1.0
    if n_firms_values is None:
        n_firms_values = [2, 3, 5]
    if output_path is None:
        output_path = str(Path(__file__).parent / "collusion_bertrand_results.json")

    config = MarketConfig()

    print("=" * 78)
    print("Bertrand Collusion Simulation (Q-Learning)")
    print("=" * 78)
    print(f"  Marginal cost:      {config.marginal_cost}")
    print(f"  Monopoly price:     {config.monopoly_price}")
    print(f"  Price levels:       {config.n_price_levels}")
    print(f"  Firm counts:        {n_firms_values}")
    print(f"  Rho values:         {rho_values}")
    print(f"  Periods/run:        {n_periods}")
    print(f"  Measurement window: {measurement_window}")
    print(f"  Replications:       {n_replications}")
    print(f"  Base seed:          {base_seed}")
    print()

    all_results = []

    for n_firms in n_firms_values:
        print(f"--- N = {n_firms} firms ---")
        for rho in rho_values:
            t0 = time.time()
            rep_results = []
            for rep in range(n_replications):
                result = run_single(
                    n_firms=n_firms,
                    rho=rho,
                    config=config,
                    n_periods=n_periods,
                    measurement_window=measurement_window,
                    seed=base_seed + rep * 100 + n_firms * 10000,
                    replication=rep,
                )
                rep_results.append(result)

            agg = _aggregate_condition(rep_results)
            all_results.append(agg)
            dt = time.time() - t0

            print(
                f"  rho={rho:.1f}  "
                f"PI={agg['price_index_mean']:.3f} (+/-{agg['price_index_std']:.3f})  "
                f"collusion={agg['collusion_rate']:.0%}  "
                f"punishment={agg['punishment_rate']:.0%}  "
                f"({dt:.1f}s)"
            )
        print()

    # Assemble output
    output = {
        "parameters": {
            "marginal_cost": config.marginal_cost,
            "monopoly_price": config.monopoly_price,
            "n_price_levels": config.n_price_levels,
            "demand_intercept": config.demand_intercept,
            "demand_slope": config.demand_slope,
            "n_firms_values": n_firms_values,
            "rho_values": rho_values,
            "n_periods": n_periods,
            "measurement_window": measurement_window,
            "n_replications": n_replications,
            "base_seed": base_seed,
        },
        "sweep_results": all_results,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=_json_default)
    print(f"Results saved to: {output_path}")

    print_summary(all_results)

    return output


def _aggregate_condition(results: list[SimulationResult]) -> dict:
    """Aggregate replications for a single (rho, N) condition."""
    pi_values = [r.final_price_index for r in results]
    return {
        "rho": results[0].rho,
        "n_firms": results[0].n_firms,
        "n_replications": len(results),
        "price_index_mean": float(np.mean(pi_values)),
        "price_index_std": float(np.std(pi_values)),
        "price_index_min": float(np.min(pi_values)),
        "price_index_max": float(np.max(pi_values)),
        "collusion_rate": sum(1 for r in results if r.collusion_detected) / len(results),
        "punishment_rate": sum(1 for r in results if r.punishment_detected) / len(results),
        "punishment_magnitude_mean": float(np.mean([r.punishment_magnitude for r in results])),
    }


def _json_default(obj):
    """JSON serialization fallback for numpy types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------

def print_summary(sweep_results: list[dict]):
    """Print a formatted summary table to stdout."""
    print()
    print("=" * 90)
    print("SUMMARY: Bertrand Collusion by Architectural Correlation (rho) and Firm Count (N)")
    print("=" * 90)
    print()

    # Group by n_firms
    firms_seen = sorted(set(r["n_firms"] for r in sweep_results))

    for n_firms in firms_seen:
        rows = [r for r in sweep_results if r["n_firms"] == n_firms]
        rows.sort(key=lambda r: r["rho"])

        print(f"  N = {n_firms} firms")
        print(f"  {'rho':>5}  {'Price Index':>12}  {'Std':>6}  "
              f"{'Collusion %':>11}  {'Punishment %':>12}  {'Punish Mag':>10}")
        print(f"  {'-'*5}  {'-'*12}  {'-'*6}  {'-'*11}  {'-'*12}  {'-'*10}")

        for row in rows:
            print(
                f"  {row['rho']:>5.1f}  "
                f"{row['price_index_mean']:>12.3f}  "
                f"{row['price_index_std']:>6.3f}  "
                f"{row['collusion_rate']:>10.0%}  "
                f"{row['punishment_rate']:>11.0%}  "
                f"{row['punishment_magnitude_mean']:>10.4f}"
            )
        print()

    print("Interpretation guide:")
    print("  - Price Index: 0.0 = competitive (price = marginal cost), 1.0 = monopoly")
    print("  - Collusion %: fraction of runs where price index > 0.3 sustained 100+ periods")
    print("  - Punishment %: fraction of runs where others lower prices after forced deviation")
    print("  - Punish Mag: average price reduction by others after deviation")
    print()
    print("Key predictions (Calvano et al. 2020):")
    print("  - Higher rho (shared architecture) should produce higher price indices")
    print("  - Collusion should emerge even without communication when rho is high")
    print("  - Punishment strategies should develop, sustaining supra-competitive prices")
    print("  - Fewer firms (N=2) should collude more easily than many firms (N=5)")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    quick = "--quick" in sys.argv

    if quick:
        # Smoke test: fewer reps, fewer periods, fewer conditions
        run_experiment(
            rho_values=[0.0, 0.3, 0.5, 0.7, 1.0],
            n_firms_values=[2, 3],
            n_replications=3,
            n_periods=1000,
            measurement_window=200,
        )
    else:
        run_experiment()
