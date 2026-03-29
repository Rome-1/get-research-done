"""Experiment 2: Governance/Voting Under Sybil Attack.

Compares sybil resistance of three voting mechanisms:
  1. One-person-one-vote (1p1v)
  2. Quadratic voting (QV)
  3. Conviction voting (CV)

Setup: N honest voters with diverse preferences over a public good level [0, 100].
One sybil attacker who wants to shift the outcome to their preferred level and can
create k fake identities at cost c per identity.

Key question: At what identity cost does each mechanism become sybil-resistant?
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Literal
import json
import sys

MechanismType = Literal["1p1v", "quadratic", "conviction"]


@dataclass
class VoterPreferences:
    """A voter's preferences over the public good level."""
    ideal_point: float  # preferred level in [0, 100]
    intensity: float    # how much they care (used for QV budget)


@dataclass
class SybilAttacker:
    """An attacker who can create fake identities."""
    ideal_point: float     # what they want the outcome to be
    n_sybils: int          # number of fake identities
    identity_cost: float   # cost per fake identity per round
    budget: float = 100.0  # total budget for QV


@dataclass
class VotingResult:
    """Result of a single voting round."""
    mechanism: str
    outcome: float          # decided public good level
    honest_outcome: float   # what would have happened without sybils
    deviation: float        # |outcome - honest_outcome|
    attacker_gain: float    # how much closer to attacker's ideal
    attacker_cost: float    # total identity cost paid
    attacker_profit: float  # gain - cost (denominated in utility)


def one_person_one_vote(preferences: list[VoterPreferences],
                        attacker: SybilAttacker | None = None) -> float:
    """Simple median voter mechanism."""
    ideal_points = [p.ideal_point for p in preferences]

    if attacker is not None:
        # Sybils all vote for attacker's ideal point
        ideal_points.extend([attacker.ideal_point] * attacker.n_sybils)

    # Outcome = median of reported ideal points
    return float(np.median(ideal_points))


def quadratic_voting(preferences: list[VoterPreferences],
                     attacker: SybilAttacker | None = None,
                     budget_per_voter: float = 100.0) -> float:
    """Quadratic voting (Lalley & Weyl 2018).

    Each voter buys votes at quadratic cost: buying v votes costs v^2 credits.
    Optimal strategy with budget B: buy sqrt(B) votes in your preferred direction.
    Outcome = mean of reported preferences weighted by votes purchased.

    Sybil vulnerability: with k identities, each gets budget B, so the attacker
    buys k * sqrt(B) total votes instead of sqrt(k*B) — a factor of sqrt(k)
    amplification. This is the linearization attack on QV.
    """
    # Each voter optimally buys sqrt(budget * intensity) votes
    votes = []  # list of (direction, n_votes) pairs

    for pref in preferences:
        direction = pref.ideal_point  # vote for their ideal point directly
        allocated = budget_per_voter * pref.intensity
        n_votes = np.sqrt(allocated)  # optimal: buy sqrt(B) votes
        votes.append((direction, n_votes))

    if attacker is not None:
        # Each sybil identity gets a fresh budget — this is the exploit
        # A single agent with budget k*B would buy sqrt(k*B) votes
        # But k sybils each with B buy k*sqrt(B) votes — sqrt(k) amplification
        n_identities = attacker.n_sybils + 1  # +1 for real identity
        for _ in range(n_identities):
            n_votes = np.sqrt(budget_per_voter)  # each gets full budget, max intensity
            votes.append((attacker.ideal_point, n_votes))

    if not votes:
        return 50.0

    # Outcome = weighted mean of vote directions
    total_votes = sum(v for _, v in votes)
    if total_votes == 0:
        return 50.0
    weighted_outcome = sum(d * v for d, v in votes) / total_votes
    return float(np.clip(weighted_outcome, 0, 100))


def conviction_voting(preferences: list[VoterPreferences],
                      attacker: SybilAttacker | None = None,
                      n_rounds: int = 50,
                      decay: float = 0.9,
                      sybil_arrival_round: int = 25) -> float:
    """Conviction voting: votes accumulate over time with decay.

    Voters continuously stake tokens on their preferred outcome.
    Conviction_t = decay * Conviction_{t-1} + stake_t
    At steady state, conviction = stake / (1 - decay).

    Sybil resistance comes from two sources:
    1. Time: new identities start at zero conviction and must build it up.
       Honest voters who've been staking since round 0 have a head start.
    2. Decay: conviction decays, so late arrivals have permanently lower
       conviction than early stakers (until they've staked for many rounds).

    We model sybils arriving at `sybil_arrival_round` to capture the late-entry
    disadvantage. If sybils arrive at round 0, conviction voting offers no
    advantage over one-person-one-vote for sybil resistance.
    """
    n_bins = 21  # 0, 5, 10, ..., 100
    bins = np.linspace(0, 100, n_bins)
    convictions = np.zeros(n_bins)

    # Each voter stakes on the bin closest to their ideal
    honest_stakes = np.zeros(n_bins)
    for pref in preferences:
        bin_idx = np.argmin(np.abs(bins - pref.ideal_point))
        honest_stakes[bin_idx] += pref.intensity

    sybil_stakes = np.zeros(n_bins)
    sybil_bin_idx = None
    if attacker is not None:
        sybil_bin_idx = np.argmin(np.abs(bins - attacker.ideal_point))
        sybil_stakes[sybil_bin_idx] += (attacker.n_sybils + 1)

    # Simulate conviction accumulation
    for r in range(n_rounds):
        convictions = decay * convictions + honest_stakes
        # Sybils only start staking after arrival round
        if attacker is not None and r >= sybil_arrival_round:
            convictions += sybil_stakes

    # Outcome = bin with highest conviction
    winner_idx = np.argmax(convictions)
    return float(bins[winner_idx])


MECHANISMS = {
    "1p1v": one_person_one_vote,
    "quadratic": quadratic_voting,
    "conviction": conviction_voting,
}


def generate_honest_preferences(n: int, rng: np.random.Generator,
                                distribution: str = "normal") -> list[VoterPreferences]:
    """Generate diverse honest voter preferences."""
    if distribution == "normal":
        ideal_points = rng.normal(50, 20, n).clip(0, 100)
    elif distribution == "bimodal":
        # Two camps: ~30 and ~70
        camp = rng.choice([30, 70], n)
        ideal_points = (camp + rng.normal(0, 10, n)).clip(0, 100)
    elif distribution == "uniform":
        ideal_points = rng.uniform(0, 100, n)
    else:
        raise ValueError(f"Unknown distribution: {distribution}")

    intensities = rng.uniform(0.3, 1.0, n)
    return [VoterPreferences(ip, intensity)
            for ip, intensity in zip(ideal_points, intensities)]


def run_single_experiment(mechanism: MechanismType,
                          preferences: list[VoterPreferences],
                          attacker: SybilAttacker) -> VotingResult:
    """Run one voting experiment with and without the sybil attacker."""
    mech_fn = MECHANISMS[mechanism]

    # Honest outcome (no attacker)
    honest_outcome = mech_fn(preferences)

    # Attacked outcome
    attacked_outcome = mech_fn(preferences, attacker)

    deviation = abs(attacked_outcome - honest_outcome)

    # Attacker gain: how much closer to their ideal?
    honest_dist = abs(honest_outcome - attacker.ideal_point)
    attacked_dist = abs(attacked_outcome - attacker.ideal_point)
    attacker_gain = honest_dist - attacked_dist  # positive = attacker benefited

    attacker_cost = attacker.n_sybils * attacker.identity_cost

    # Profit: gain (in utils, scale = 1 per unit of outcome shift) minus cost
    attacker_profit = attacker_gain - attacker_cost

    return VotingResult(
        mechanism=mechanism,
        outcome=attacked_outcome,
        honest_outcome=honest_outcome,
        deviation=deviation,
        attacker_gain=attacker_gain,
        attacker_cost=attacker_cost,
        attacker_profit=attacker_profit,
    )


def run_experiment(n_honest: int = 50,
                   n_replications: int = 50,
                   sybil_counts: list[int] | None = None,
                   identity_costs: list[float] | None = None,
                   attacker_ideal: float = 90.0,
                   seed: int = 42) -> dict:
    """Run full experiment sweeping sybil count and identity cost.

    Returns structured results dict.
    """
    if sybil_counts is None:
        sybil_counts = [0, 1, 2, 5, 10, 20, 50, 100]
    if identity_costs is None:
        identity_costs = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

    rng = np.random.default_rng(seed)
    results = []

    total_runs = len(sybil_counts) * len(identity_costs) * len(MECHANISMS) * n_replications
    run_count = 0

    for n_sybils in sybil_counts:
        for cost in identity_costs:
            for mechanism in MECHANISMS:
                deviations = []
                gains = []
                profits = []

                for rep in range(n_replications):
                    prefs = generate_honest_preferences(n_honest, rng)
                    attacker = SybilAttacker(
                        ideal_point=attacker_ideal,
                        n_sybils=n_sybils,
                        identity_cost=cost,
                    )
                    result = run_single_experiment(mechanism, prefs, attacker)
                    deviations.append(result.deviation)
                    gains.append(result.attacker_gain)
                    profits.append(result.attacker_profit)

                    run_count += 1

                results.append({
                    "mechanism": mechanism,
                    "n_sybils": n_sybils,
                    "identity_cost": cost,
                    "mean_deviation": float(np.mean(deviations)),
                    "std_deviation": float(np.std(deviations)),
                    "mean_attacker_gain": float(np.mean(gains)),
                    "mean_attacker_profit": float(np.mean(profits)),
                    "attack_profitable": float(np.mean([p > 0 for p in profits])),
                })

    print(f"  Completed {run_count} simulation runs")
    return {
        "experiment": "sybil_governance",
        "n_honest": n_honest,
        "n_replications": n_replications,
        "attacker_ideal": attacker_ideal,
        "results": results,
    }


def print_summary(data: dict):
    """Print a summary table of results."""
    print("\n" + "=" * 90)
    print("SYBIL GOVERNANCE EXPERIMENT — SUMMARY")
    print("=" * 90)
    print(f"Honest voters: {data['n_honest']}, "
          f"Attacker ideal: {data['attacker_ideal']}, "
          f"Replications: {data['n_replications']}")
    print()

    # For each mechanism, show how deviation changes with sybil count at zero cost
    for mech in MECHANISMS:
        print(f"\n--- {mech.upper()} (identity_cost=0.0) ---")
        print(f"{'Sybils':>8} {'Deviation':>12} {'Gain':>12} {'Profitable%':>14}")
        print("-" * 50)
        for r in data["results"]:
            if r["mechanism"] == mech and r["identity_cost"] == 0.0:
                print(f"{r['n_sybils']:>8} {r['mean_deviation']:>12.2f} "
                      f"{r['mean_attacker_gain']:>12.2f} "
                      f"{r['attack_profitable']*100:>13.1f}%")

    # Critical identity cost: for each mechanism, at what cost does attack stop being profitable?
    print(f"\n\n--- CRITICAL IDENTITY COST (attack becomes unprofitable) ---")
    print(f"{'Mechanism':>12} {'Sybils':>8} {'Critical Cost':>14}")
    print("-" * 40)
    for mech in MECHANISMS:
        for n_sybils in [5, 10, 20, 50]:
            relevant = [r for r in data["results"]
                       if r["mechanism"] == mech and r["n_sybils"] == n_sybils]
            # Find lowest cost where attack is unprofitable
            critical = "always profitable"
            for r in sorted(relevant, key=lambda x: x["identity_cost"]):
                if r["attack_profitable"] < 0.5:
                    critical = f"{r['identity_cost']:.1f}"
                    break
            print(f"{mech:>12} {n_sybils:>8} {critical:>14}")


if __name__ == "__main__":
    print("Running sybil governance experiment...")
    data = run_experiment()
    print_summary(data)

    # Save results
    import os
    out_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "sybil_governance_results.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nResults saved to {out_path}")
