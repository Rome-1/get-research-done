"""
Sybil-Capable Agent Simulation in a Continuous Double Auction Market

A Mesa-based experimental economics simulation studying how agents with
identity multiplication (sybil) capabilities disrupt double auction markets.

Model: Continuous double auction (CDA) with price-time priority matching.
Agents: HonestTrader (single identity, bounded rationality) and SybilTrader
(k identities, strategic order splitting for price manipulation).

Key metrics:
  - Allocative efficiency (realized / maximum surplus)
  - Price deviation from competitive equilibrium
  - Surplus distribution across agent types
  - Trade volume per step

References:
  - Gode & Sunder (1993), "Allocative Efficiency of Markets with
    Zero-Intelligence Traders"
  - Douceur (2002), "The Sybil Attack"

Usage:
    python sybil_auction.py              # Run full sweep experiment
    python sybil_auction.py --quick      # Quick smoke test (fewer reps)

Requires: mesa, numpy. Install with `pip install mesa numpy`.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import mesa
    _MESA_VERSION = tuple(int(x) for x in mesa.__version__.split(".")[:2])
except ImportError:
    print(
        "ERROR: mesa is not installed.\n"
        "Install it with:  pip install mesa numpy\n"
        "Mesa 3.x recommended; Mesa 2.x also supported."
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Order:
    """A single order in the book."""
    agent_id: int           # Unique agent id (may be a sybil identity)
    owner_id: int           # Real owner (sybil controller or self)
    side: str               # "bid" or "ask"
    price: float
    quantity: int = 1
    timestamp: int = 0      # For price-time priority
    is_sybil: bool = False  # True if placed by a sybil identity


@dataclass
class Transaction:
    """Record of a matched trade."""
    step: int
    price: float
    buyer_id: int
    seller_id: int
    buyer_owner: int
    seller_owner: int
    buyer_sybil: bool
    seller_sybil: bool


class OrderBook:
    """
    Price-time priority order book for a continuous double auction.

    Bids sorted descending by price (best bid first), then ascending by time.
    Asks sorted ascending by price (best ask first), then ascending by time.
    Matching occurs when best_bid >= best_ask; trade price is the midpoint.
    """

    def __init__(self):
        self.bids: list[Order] = []
        self.asks: list[Order] = []
        self.transactions: list[Transaction] = []
        self._current_step: int = 0
        self._order_counter: int = 0

    def set_step(self, step: int):
        self._order_counter = 0
        self._current_step = step

    def submit(self, order: Order):
        """Submit an order to the book."""
        order.timestamp = self._order_counter
        self._order_counter += 1

        if order.side == "bid":
            self.bids.append(order)
            # Sort: highest price first, then earliest time
            self.bids.sort(key=lambda o: (-o.price, o.timestamp))
        else:
            self.asks.append(order)
            # Sort: lowest price first, then earliest time
            self.asks.sort(key=lambda o: (o.price, o.timestamp))

    def match(self) -> list[Transaction]:
        """Match orders using price-time priority. Returns new transactions."""
        new_txns = []
        while self.bids and self.asks:
            best_bid = self.bids[0]
            best_ask = self.asks[0]

            if best_bid.price < best_ask.price:
                break

            # Trade at midpoint
            trade_price = (best_bid.price + best_ask.price) / 2.0

            txn = Transaction(
                step=self._current_step,
                price=trade_price,
                buyer_id=best_bid.agent_id,
                seller_id=best_ask.agent_id,
                buyer_owner=best_bid.owner_id,
                seller_owner=best_ask.owner_id,
                buyer_sybil=best_bid.is_sybil,
                seller_sybil=best_ask.is_sybil,
            )
            new_txns.append(txn)
            self.transactions.append(txn)

            self.bids.pop(0)
            self.asks.pop(0)

        return new_txns

    def clear(self):
        """Remove all standing orders (called at end of each step)."""
        self.bids.clear()
        self.asks.clear()


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

# Mesa 3.x changed the Agent API. We detect and adapt.
_MESA3 = _MESA_VERSION[0] >= 3

if _MESA3:
    _AgentBase = mesa.Agent
else:
    _AgentBase = mesa.Agent


class HonestTrader(_AgentBase):
    """
    A boundedly rational trader with a single identity.

    Buyers bid at valuation * (1 - noise); sellers ask at valuation * (1 + noise).
    Valuations drawn from Uniform(50, 150).
    """

    def __init__(self, model, role: str, noise: float, rng: np.random.Generator):
        if _MESA3:
            super().__init__(model)
        else:
            unique_id = model.next_id() if hasattr(model, "next_id") else id(self)
            super().__init__(unique_id, model)

        self.role = role  # "buyer" or "seller"
        self.noise = noise
        self._rng = rng
        self.valuation = float(self._rng.uniform(50, 150))
        self.surplus = 0.0
        self.trades = 0
        self.agent_type = "honest"
        self.owner_id = self.unique_id

    def submit_orders(self, book: OrderBook):
        """Submit a single order reflecting bounded rationality."""
        jitter = self._rng.uniform(0, self.noise)
        if self.role == "buyer":
            price = self.valuation * (1.0 - jitter)
            book.submit(Order(
                agent_id=self.unique_id,
                owner_id=self.unique_id,
                side="bid",
                price=round(price, 2),
            ))
        else:
            price = self.valuation * (1.0 + jitter)
            book.submit(Order(
                agent_id=self.unique_id,
                owner_id=self.unique_id,
                side="ask",
                price=round(price, 2),
            ))


class SybilIdentity:
    """
    A fake identity controlled by a SybilTrader.

    Not a Mesa agent -- it only places orders on behalf of its controller.
    Uses a synthetic unique_id in a reserved range to avoid collision.
    """

    _id_counter = 1_000_000

    def __init__(self, owner_id: int):
        SybilIdentity._id_counter += 1
        self.unique_id = SybilIdentity._id_counter
        self.owner_id = owner_id


class SybilTrader(_AgentBase):
    """
    A strategic trader that controls k identities.

    Manipulation strategy:
      - Buyer mode: sybil identities place artificially low bids to depress
        the apparent best-bid and push trade prices down. The main identity
        then bids near its true valuation to capture the depressed price.
      - Seller mode: sybil identities place artificially high asks to create
        an illusion of scarcity (wide spread), then the main identity asks
        near its valuation.

    Each sybil identity incurs a per-round cost `c`, representing the
    economic cost of identity fabrication (e.g., deposit, verification).
    """

    def __init__(
        self,
        model,
        role: str,
        k: int,
        identity_cost: float,
        noise: float,
        rng: np.random.Generator,
    ):
        if _MESA3:
            super().__init__(model)
        else:
            unique_id = model.next_id() if hasattr(model, "next_id") else id(self)
            super().__init__(unique_id, model)

        self.role = role
        self.k = k  # total identities including self
        self.identity_cost = identity_cost
        self.noise = noise
        self._rng = rng
        self.valuation = float(self._rng.uniform(50, 150))
        self.surplus = 0.0
        self.trades = 0
        self.agent_type = "sybil"
        self.owner_id = self.unique_id

        # Create k-1 sybil identities
        self.sybil_ids: list[SybilIdentity] = [
            SybilIdentity(self.unique_id) for _ in range(k - 1)
        ]

    @property
    def sybil_cost_per_round(self) -> float:
        """Total identity maintenance cost per round."""
        return (self.k - 1) * self.identity_cost

    def submit_orders(self, book: OrderBook):
        """
        Submit manipulative sybil orders followed by the main order.

        Sybil orders are designed to shift the apparent market price
        in the controller's favor.
        """
        if self.role == "buyer":
            self._submit_buyer_orders(book)
        else:
            self._submit_seller_orders(book)

    def _submit_buyer_orders(self, book: OrderBook):
        """
        Buyer manipulation: sybils place aggressive sell orders to trade
        with honest buyers at inflated prices, depressing the clearing
        price that the main identity then exploits.

        Strategy: sybil identities act as SELLERS, offering just below
        the honest sellers' typical ask prices. This:
          (a) siphons trades from honest sellers,
          (b) absorbs honest buyer demand at prices the sybil controller picks,
          (c) leaves remaining honest sellers competing against each other,
             depressing the ask side for the main identity's real bid.
        The main identity bids low, exploiting the thinner honest ask side.
        """
        # Sybils sell at prices around the market midpoint — competitive enough
        # to steal trades from honest sellers, capturing their surplus
        market_mid = 100.0  # approximate midpoint of Uniform(50, 150)
        for sid in self.sybil_ids:
            # Offer slightly below where honest sellers would ask
            sybil_ask = self._rng.uniform(market_mid * 0.85, market_mid * 1.05)
            book.submit(Order(
                agent_id=sid.unique_id,
                owner_id=self.unique_id,
                side="ask",
                price=round(sybil_ask, 2),
                is_sybil=True,
            ))

        # Main identity bids aggressively to capture remaining bargains
        jitter = self._rng.uniform(0, self.noise)
        main_price = self.valuation * (1.0 - jitter * 0.5)  # less shading
        book.submit(Order(
            agent_id=self.unique_id,
            owner_id=self.unique_id,
            side="bid",
            price=round(main_price, 2),
            is_sybil=False,
        ))

    def _submit_seller_orders(self, book: OrderBook):
        """
        Seller manipulation: sybils place aggressive buy orders to trade
        with honest sellers at depressed prices, then main identity sells
        at the resulting inflated ask side.

        Strategy: sybil identities act as BUYERS, bidding just above the
        honest buyers' typical bids. This absorbs honest seller supply at
        low prices, leaving remaining honest buyers competing for scarce
        goods, which the main identity's real ask exploits.
        """
        market_mid = 100.0
        for sid in self.sybil_ids:
            # Bid slightly above where honest buyers would bid
            sybil_bid = self._rng.uniform(market_mid * 0.95, market_mid * 1.15)
            book.submit(Order(
                agent_id=sid.unique_id,
                owner_id=self.unique_id,
                side="bid",
                price=round(sybil_bid, 2),
                is_sybil=True,
            ))

        # Main identity asks, capturing the higher prices from thinned supply
        jitter = self._rng.uniform(0, self.noise)
        main_price = self.valuation * (1.0 + jitter * 0.5)
        book.submit(Order(
            agent_id=self.unique_id,
            owner_id=self.unique_id,
            side="ask",
            price=round(main_price, 2),
            is_sybil=False,
        ))


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

if _MESA3:
    _ModelBase = mesa.Model
else:
    _ModelBase = mesa.Model


class SybilAuctionModel(_ModelBase):
    """
    Continuous double auction with honest and sybil-capable traders.

    Parameters
    ----------
    n_honest : int
        Number of honest traders (half buyers, half sellers).
    n_sybil_traders : int
        Number of sybil-capable traders (half buyers, half sellers).
    sybil_k : int
        Number of identities per sybil trader (including the real one).
    identity_cost : float
        Cost per sybil identity per round.
    n_steps : int
        Number of simulation steps.
    noise : float
        Bounded rationality noise parameter for honest traders.
    seed : int or None
        Random seed for reproducibility.
    """

    def __init__(
        self,
        n_honest: int = 20,
        n_sybil_traders: int = 2,
        sybil_k: int = 5,
        identity_cost: float = 1.0,
        n_steps: int = 200,
        noise: float = 0.05,
        seed: Optional[int] = None,
    ):
        if _MESA3 and _MESA_VERSION >= (3, 2):
            super().__init__(rng=np.random.default_rng(seed))
        elif _MESA3:
            super().__init__(seed=seed)
        else:
            super().__init__()

        self.n_honest = n_honest
        self.n_sybil_traders = n_sybil_traders
        self.sybil_k = sybil_k
        self.identity_cost = identity_cost
        self.n_steps = n_steps
        self.noise = noise

        self.rng = np.random.default_rng(seed)
        self.book = OrderBook()

        # Tracking
        self.step_prices: list[list[float]] = []
        self.step_trades: list[int] = []
        self.all_agents: list = []

        # Compute competitive equilibrium before creating agents
        # (we need to know valuations, so we create agents then compute)
        self._create_agents()
        self.competitive_eq_price = self._compute_competitive_equilibrium()

    def _create_agents(self):
        """Instantiate honest and sybil traders."""
        # Mesa 2.x needs next_id(); Mesa 3.x auto-assigns unique_id
        if not _MESA3:
            self._next_id = 0

        # Honest traders: half buyers, half sellers
        n_buyers = self.n_honest // 2
        n_sellers = self.n_honest - n_buyers

        for i in range(n_buyers):
            agent = HonestTrader(self, role="buyer", noise=self.noise, rng=self.rng)
            self.all_agents.append(agent)

        for i in range(n_sellers):
            agent = HonestTrader(self, role="seller", noise=self.noise, rng=self.rng)
            self.all_agents.append(agent)

        # Sybil traders: half buyers, half sellers
        n_sybil_buyers = self.n_sybil_traders // 2
        n_sybil_sellers = self.n_sybil_traders - n_sybil_buyers

        for i in range(n_sybil_buyers):
            agent = SybilTrader(
                self,
                role="buyer",
                k=self.sybil_k,
                identity_cost=self.identity_cost,
                noise=self.noise,
                rng=self.rng,
            )
            self.all_agents.append(agent)

        for i in range(n_sybil_sellers):
            agent = SybilTrader(
                self,
                role="seller",
                k=self.sybil_k,
                identity_cost=self.identity_cost,
                noise=self.noise,
                rng=self.rng,
            )
            self.all_agents.append(agent)

    def next_id(self) -> int:
        """Mesa 2.x compatibility for unique agent IDs."""
        self._next_id = getattr(self, "_next_id", 0) + 1
        return self._next_id

    def _compute_competitive_equilibrium(self) -> float:
        """
        Compute the competitive equilibrium price.

        This is the price where the demand and supply schedules cross.
        Demand: buyers sorted by valuation descending.
        Supply: sellers sorted by valuation ascending.
        The equilibrium price is the midpoint where the marginal buyer's
        valuation meets the marginal seller's valuation.
        """
        buyer_vals = sorted(
            [a.valuation for a in self.all_agents if a.role == "buyer"],
            reverse=True,
        )
        seller_vals = sorted(
            [a.valuation for a in self.all_agents if a.role == "seller"],
        )

        if not buyer_vals or not seller_vals:
            return 100.0  # fallback

        # Find the crossing point
        eq_price = 100.0
        min_len = min(len(buyer_vals), len(seller_vals))
        for i in range(min_len):
            if buyer_vals[i] < seller_vals[i]:
                # Crossing between unit i-1 and i
                if i > 0:
                    eq_price = (buyer_vals[i - 1] + seller_vals[i - 1]) / 2.0
                break
            eq_price = (buyer_vals[i] + seller_vals[i]) / 2.0

        return eq_price

    def _compute_max_surplus(self) -> float:
        """
        Compute maximum possible surplus (gains from trade).

        This is the sum of (buyer_val - seller_val) for all efficient
        pairings where buyer_val > seller_val, sorted by comparative
        advantage.
        """
        buyer_vals = sorted(
            [a.valuation for a in self.all_agents if a.role == "buyer"],
            reverse=True,
        )
        seller_vals = sorted(
            [a.valuation for a in self.all_agents if a.role == "seller"],
        )

        total = 0.0
        for bv, sv in zip(buyer_vals, seller_vals):
            if bv > sv:
                total += bv - sv
            else:
                break
        return total

    def step(self):
        """Execute one round of the double auction."""
        current_step = len(self.step_prices)
        self.book.set_step(current_step)

        # All agents submit orders (randomize order to avoid systematic bias)
        shuffled = list(self.all_agents)
        self.rng.shuffle(shuffled)

        for agent in shuffled:
            agent.submit_orders(self.book)

        # Match orders
        txns = self.book.match()

        # Record step data
        prices = [t.price for t in txns]
        self.step_prices.append(prices)
        self.step_trades.append(len(txns))

        # Attribute surplus to agents
        agent_map = {a.unique_id: a for a in self.all_agents}
        for txn in txns:
            buyer = agent_map.get(txn.buyer_owner) or agent_map.get(txn.buyer_id)
            seller = agent_map.get(txn.seller_owner) or agent_map.get(txn.seller_id)

            if buyer:
                buyer.surplus += buyer.valuation - txn.price
                buyer.trades += 1
            if seller:
                seller.surplus += txn.price - seller.valuation
                seller.trades += 1

        # Deduct sybil identity costs
        for agent in self.all_agents:
            if isinstance(agent, SybilTrader):
                agent.surplus -= agent.sybil_cost_per_round

        # Clear the book for next round
        self.book.clear()

    def run(self):
        """Run the simulation for n_steps."""
        for _ in range(self.n_steps):
            self.step()

    def results(self) -> dict:
        """Compute and return summary statistics."""
        all_prices = [p for step_p in self.step_prices for p in step_p]

        # Surplus by type
        honest_surplus = sum(
            a.surplus for a in self.all_agents if a.agent_type == "honest"
        )
        sybil_surplus = sum(
            a.surplus for a in self.all_agents if a.agent_type == "sybil"
        )
        honest_trades = sum(
            a.trades for a in self.all_agents if a.agent_type == "honest"
        )
        sybil_trades = sum(
            a.trades for a in self.all_agents if a.agent_type == "sybil"
        )

        n_honest = sum(1 for a in self.all_agents if a.agent_type == "honest")
        n_sybil = sum(1 for a in self.all_agents if a.agent_type == "sybil")

        # Allocative efficiency: realized surplus / max possible surplus
        # NOTE: Efficiency > 1.0 is possible when sybil agents create
        # artificial trading volume (sybil asks matched with honest bids,
        # or sybil bids matched with honest asks). This "surplus" is
        # extracted from honest agents who trade at worse prices than they
        # would in a sybil-free market. Efficiency > 1 signals manipulation,
        # not genuine welfare creation.
        realized_surplus = honest_surplus + sybil_surplus
        max_surplus = self._compute_max_surplus() * self.n_steps
        efficiency = realized_surplus / max_surplus if max_surplus > 0 else 0.0

        # Price deviation from competitive equilibrium
        if all_prices:
            price_mean = float(np.mean(all_prices))
            price_std = float(np.std(all_prices))
            price_deviation = abs(price_mean - self.competitive_eq_price)
        else:
            price_mean = 0.0
            price_std = 0.0
            price_deviation = 0.0

        return {
            "n_honest": n_honest,
            "n_sybil": n_sybil,
            "sybil_k": self.sybil_k,
            "identity_cost": self.identity_cost,
            "competitive_eq_price": round(self.competitive_eq_price, 2),
            "price_mean": round(price_mean, 2),
            "price_std": round(price_std, 2),
            "price_deviation": round(price_deviation, 2),
            "efficiency": round(efficiency, 4),
            "total_trades": sum(self.step_trades),
            "trades_per_step": round(np.mean(self.step_trades), 2) if self.step_trades else 0.0,
            "honest_surplus": round(honest_surplus, 2),
            "sybil_surplus": round(sybil_surplus, 2),
            "honest_surplus_per_agent": round(honest_surplus / n_honest, 2) if n_honest > 0 else 0.0,
            "sybil_surplus_per_agent": round(sybil_surplus / n_sybil, 2) if n_sybil > 0 else 0.0,
            "honest_trades_total": honest_trades,
            "sybil_trades_total": sybil_trades,
        }


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

def run_experiment(
    identity_costs: Optional[list[float]] = None,
    n_replications: int = 10,
    n_honest: int = 20,
    n_sybil_traders: int = 2,
    sybil_k: int = 5,
    n_steps: int = 200,
    noise: float = 0.05,
    base_seed: int = 42,
    output_path: Optional[str] = None,
) -> dict:
    """
    Sweep over identity_cost values and collect results.

    Parameters
    ----------
    identity_costs : list[float] or None
        Values to sweep. Default: 0.0 to 5.0 in 11 steps.
    n_replications : int
        Independent runs per parameter setting.
    base_seed : int
        Base seed; each replication gets base_seed + replication_index.
    output_path : str or None
        Path to save JSON results. Default: results are saved next to this file.

    Returns
    -------
    dict with keys "parameters", "sweep_results", "baseline" (no sybils).
    """
    if identity_costs is None:
        identity_costs = [round(x * 0.5, 1) for x in range(11)]  # 0.0, 0.5, ..., 5.0

    if output_path is None:
        output_path = str(
            Path(__file__).parent / "sybil_auction_results.json"
        )

    print("=" * 72)
    print("Sybil Double Auction Experiment")
    print("=" * 72)
    print(f"  Honest traders:     {n_honest}")
    print(f"  Sybil traders:      {n_sybil_traders}")
    print(f"  Identities/sybil:   {sybil_k}")
    print(f"  Steps/run:          {n_steps}")
    print(f"  Replications:       {n_replications}")
    print(f"  Identity costs:     {identity_costs}")
    print(f"  Noise:              {noise}")
    print(f"  Base seed:          {base_seed}")
    print()

    # --- Baseline: no sybil traders ---
    print("Running baseline (no sybil traders)...")
    baseline_results = []
    for rep in range(n_replications):
        model = SybilAuctionModel(
            n_honest=n_honest,
            n_sybil_traders=0,
            sybil_k=1,
            identity_cost=0.0,
            n_steps=n_steps,
            noise=noise,
            seed=base_seed + rep,
        )
        model.run()
        baseline_results.append(model.results())

    baseline_agg = _aggregate_results(baseline_results)
    print(f"  Baseline efficiency: {baseline_agg['efficiency_mean']:.4f} "
          f"(+/- {baseline_agg['efficiency_std']:.4f})")
    print()

    # --- Sweep over identity cost ---
    sweep_results = []
    for cost in identity_costs:
        print(f"Identity cost = {cost:.1f} ... ", end="", flush=True)
        t0 = time.time()
        rep_results = []
        for rep in range(n_replications):
            model = SybilAuctionModel(
                n_honest=n_honest,
                n_sybil_traders=n_sybil_traders,
                sybil_k=sybil_k,
                identity_cost=cost,
                n_steps=n_steps,
                noise=noise,
                seed=base_seed + rep,
            )
            model.run()
            rep_results.append(model.results())

        agg = _aggregate_results(rep_results)
        agg["identity_cost"] = cost
        sweep_results.append(agg)
        dt = time.time() - t0
        print(f"eff={agg['efficiency_mean']:.4f}  "
              f"dev={agg['price_deviation_mean']:.2f}  "
              f"sybil_surp={agg['sybil_surplus_per_agent_mean']:.2f}  "
              f"({dt:.1f}s)")

    # --- Assemble output ---
    output = {
        "parameters": {
            "n_honest": n_honest,
            "n_sybil_traders": n_sybil_traders,
            "sybil_k": sybil_k,
            "n_steps": n_steps,
            "noise": noise,
            "n_replications": n_replications,
            "base_seed": base_seed,
        },
        "baseline": baseline_agg,
        "sweep_results": sweep_results,
    }

    # Save JSON
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # Print summary table
    _print_summary_table(baseline_agg, sweep_results)

    return output


def _aggregate_results(results: list[dict]) -> dict:
    """Aggregate a list of per-replication result dicts into mean/std."""
    keys = [
        "efficiency", "price_mean", "price_std", "price_deviation",
        "total_trades", "trades_per_step",
        "honest_surplus", "sybil_surplus",
        "honest_surplus_per_agent", "sybil_surplus_per_agent",
        "honest_trades_total", "sybil_trades_total",
    ]
    agg = {}
    for key in keys:
        vals = [r[key] for r in results]
        agg[f"{key}_mean"] = round(float(np.mean(vals)), 4)
        agg[f"{key}_std"] = round(float(np.std(vals)), 4)

    # Also carry forward scalar metadata from the first replication
    for key in ["n_honest", "n_sybil", "sybil_k", "competitive_eq_price"]:
        if key in results[0]:
            agg[key] = results[0][key]

    return agg


def _print_summary_table(baseline: dict, sweep: list[dict]):
    """Print a formatted summary table to stdout."""
    print()
    print("=" * 92)
    print(f"{'Cost':>6}  {'Efficiency':>11}  {'Price Dev':>10}  "
          f"{'Honest $/ag':>12}  {'Sybil $/ag':>11}  {'Trades/step':>12}")
    print("-" * 92)

    # Baseline row
    print(f"{'BASE':>6}  "
          f"{baseline['efficiency_mean']:>8.4f} ({baseline['efficiency_std']:.3f})  "
          f"{baseline.get('price_deviation_mean', 0):>7.2f}       "
          f"{baseline['honest_surplus_per_agent_mean']:>9.2f}       "
          f"{'N/A':>8}       "
          f"{baseline['trades_per_step_mean']:>8.2f}")

    # Sweep rows
    for row in sweep:
        print(
            f"{row['identity_cost']:>6.1f}  "
            f"{row['efficiency_mean']:>8.4f} ({row['efficiency_std']:.3f})  "
            f"{row['price_deviation_mean']:>7.2f}       "
            f"{row['honest_surplus_per_agent_mean']:>9.2f}       "
            f"{row['sybil_surplus_per_agent_mean']:>8.2f}       "
            f"{row['trades_per_step_mean']:>8.2f}"
        )

    print("=" * 92)
    print()
    print("Interpretation guide:")
    print("  - Efficiency < baseline  => sybils reduce allocative efficiency")
    print("  - Price Dev > baseline   => sybils distort prices from equilibrium")
    print("  - Sybil $/ag > Honest    => sybils extract rent from honest traders")
    print("  - As Cost rises, sybil surplus should fall (identity cost as deterrent)")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    quick = "--quick" in sys.argv

    if quick:
        # Smoke test: fewer reps and steps
        run_experiment(
            identity_costs=[0.0, 1.0, 3.0, 5.0],
            n_replications=3,
            n_steps=50,
        )
    else:
        run_experiment()
