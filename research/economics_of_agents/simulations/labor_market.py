"""Experiment 3: Labor Market with AI Workers.

Models a matching market for cognitive tasks where:
- Human workers have fixed supply and heterogeneous skill levels
- AI workers have elastic supply (bounded only by compute cost) and
  quality that improves over time

Key question: What are the wage dynamics as AI marginal cost approaches zero?

Hypothesis: Three distinct phases emerge:
  1. Complementary — AI handles low-skill tasks, humans specialize, both benefit
  2. Substitution — AI quality reaches human-level, human wages fall
  3. Displacement — AI cost << human cost, humans priced out of substitutable tasks
"""

import numpy as np
from dataclasses import dataclass
import json
import os


@dataclass
class Task:
    """A unit of cognitive work to be completed."""
    skill_required: float   # minimum skill level to complete [0, 1]
    value: float            # economic value if completed
    task_id: int


@dataclass
class HumanWorker:
    """A human worker with fixed skill and reservation wage."""
    skill: float            # skill level [0, 1]
    reservation_wage: float # minimum acceptable wage
    worker_id: int
    employed: bool = False
    wage: float = 0.0


@dataclass
class AIWorker:
    """An AI worker with configurable quality and marginal cost."""
    quality: float          # equivalent skill level [0, 1]
    marginal_cost: float    # cost per task (compute + API fees)


@dataclass
class LaborMarketState:
    """State of the labor market at a point in time."""
    period: int
    human_employment_rate: float
    mean_human_wage: float
    median_human_wage: float
    human_wages_by_skill: dict  # skill_quintile -> mean_wage
    ai_tasks_completed: int
    human_tasks_completed: int
    total_output: float
    consumer_surplus: float
    gini_coefficient: float
    phase: str  # "complementary", "substitution", "displacement"


class LaborMarket:
    """Simulates a labor market with human and AI workers."""

    def __init__(self,
                 n_humans: int = 100,
                 n_tasks_per_period: int = 150,
                 ai_quality: float = 0.3,
                 ai_marginal_cost: float = 5.0,
                 ai_quality_growth: float = 0.02,
                 ai_cost_decay: float = 0.98,
                 ai_quality_ceiling: float = 0.85,
                 new_task_rate: float = 0.02,
                 seed: int = 42):
        self.rng = np.random.default_rng(seed)

        # Generate human workers with beta-distributed skills
        skills = self.rng.beta(2, 5, n_humans)  # right-skewed: most have medium skill
        # Reservation wages correlate with skill (opportunity cost)
        res_wages = 2.0 + skills * 8.0 + self.rng.normal(0, 0.5, n_humans).clip(-1, 3)

        self.humans = [
            HumanWorker(skill=s, reservation_wage=w, worker_id=i)
            for i, (s, w) in enumerate(zip(skills, res_wages))
        ]

        self.n_tasks_per_period = n_tasks_per_period
        self.base_n_tasks = n_tasks_per_period
        self.ai_quality_init = ai_quality
        self.ai_quality = ai_quality
        self.ai_marginal_cost = ai_marginal_cost
        self.ai_quality_growth = ai_quality_growth
        self.ai_cost_decay = ai_cost_decay
        self.ai_quality_ceiling = ai_quality_ceiling  # AI doesn't reach 1.0
        self.new_task_rate = new_task_rate  # fraction of new tasks created per period

        self.history: list[LaborMarketState] = []

    def _generate_tasks(self) -> list[Task]:
        """Generate a set of tasks for one period."""
        # Tasks have diverse skill requirements
        skill_reqs = self.rng.beta(2, 3, self.n_tasks_per_period)
        # Value increases with difficulty (higher skill tasks pay more)
        values = 3.0 + skill_reqs * 12.0 + self.rng.exponential(1.0, self.n_tasks_per_period)
        return [Task(skill_required=s, value=v, task_id=i)
                for i, (s, v) in enumerate(zip(skill_reqs, values))]

    def _compute_gini(self, incomes: np.ndarray) -> float:
        """Compute Gini coefficient of income distribution."""
        if len(incomes) == 0 or incomes.sum() == 0:
            return 0.0
        sorted_inc = np.sort(incomes)
        n = len(sorted_inc)
        index = np.arange(1, n + 1)
        return float((2 * np.sum(index * sorted_inc) / (n * np.sum(sorted_inc))) - (n + 1) / n)

    def _classify_phase(self, state: LaborMarketState) -> str:
        """Classify the current market phase using employment AND AI task share.

        Complementary: AI does < 30% of tasks, employment > 70%
        Substitution: AI does 30-70% of tasks, employment declining
        Displacement: AI does > 70% of tasks, employment < 30%
        """
        total_tasks = state.ai_tasks_completed + state.human_tasks_completed
        ai_share = state.ai_tasks_completed / total_tasks if total_tasks > 0 else 0
        emp = state.human_employment_rate

        if ai_share < 0.3 and emp > 0.7:
            return "complementary"
        elif ai_share > 0.7 or emp < 0.3:
            return "displacement"
        else:
            return "substitution"

    def step(self, period: int) -> LaborMarketState:
        """Run one period of the labor market."""
        tasks = self._generate_tasks()

        # Reset employment
        for h in self.humans:
            h.employed = False
            h.wage = 0.0

        ai_tasks = 0
        human_tasks = 0
        total_output = 0.0
        consumer_surplus = 0.0

        # Simple matching: for each task, choose cheapest qualified worker
        # AI is always available (elastic supply) at marginal_cost
        ai_worker = AIWorker(quality=self.ai_quality, marginal_cost=self.ai_marginal_cost)

        # Sort tasks by value (highest value tasks filled first)
        tasks_sorted = sorted(tasks, key=lambda t: t.value, reverse=True)

        for task in tasks_sorted:
            # Find cheapest qualified human
            qualified_humans = [
                h for h in self.humans
                if not h.employed and h.skill >= task.skill_required
            ]

            # Sort by reservation wage (cheapest first)
            qualified_humans.sort(key=lambda h: h.reservation_wage)

            # Can AI do this task?
            ai_can = ai_worker.quality >= task.skill_required
            ai_cost = ai_worker.marginal_cost if ai_can else float('inf')

            best_human = qualified_humans[0] if qualified_humans else None
            human_cost = best_human.reservation_wage if best_human else float('inf')

            if ai_cost < human_cost and ai_can:
                # AI takes the task
                ai_tasks += 1
                total_output += task.value
                consumer_surplus += task.value - ai_cost
            elif best_human is not None:
                # Human takes the task
                # Wage = max(reservation_wage, ai_cost * 0.95) — AI sets wage ceiling
                if ai_can:
                    wage = max(best_human.reservation_wage,
                              min(ai_cost * 0.95, task.value * 0.5))
                else:
                    # No AI competition — human gets more of the surplus
                    wage = max(best_human.reservation_wage, task.value * 0.4)

                best_human.employed = True
                best_human.wage = wage
                human_tasks += 1
                total_output += task.value
                consumer_surplus += task.value - wage
            # else: task goes unfilled

        # Compute statistics
        employed = [h for h in self.humans if h.employed]
        human_wages = np.array([h.wage for h in employed]) if employed else np.array([0.0])
        all_incomes = np.array([h.wage for h in self.humans])  # 0 for unemployed

        # Wages by skill quintile
        skills = np.array([h.skill for h in self.humans])
        quintile_edges = np.percentile(skills, [0, 20, 40, 60, 80, 100])
        wages_by_skill = {}
        for q in range(5):
            mask = (skills >= quintile_edges[q]) & (skills < quintile_edges[q + 1] + 0.001)
            q_wages = all_incomes[mask]
            wages_by_skill[f"Q{q+1}"] = float(np.mean(q_wages)) if len(q_wages) > 0 else 0.0

        emp_rate = len(employed) / len(self.humans)

        state = LaborMarketState(
            period=period,
            human_employment_rate=emp_rate,
            mean_human_wage=float(np.mean(human_wages)) if len(human_wages) > 0 else 0.0,
            median_human_wage=float(np.median(human_wages)) if len(human_wages) > 0 else 0.0,
            human_wages_by_skill=wages_by_skill,
            ai_tasks_completed=ai_tasks,
            human_tasks_completed=human_tasks,
            total_output=total_output,
            consumer_surplus=consumer_surplus,
            gini_coefficient=self._compute_gini(all_incomes),
            phase="",
        )
        state.phase = self._classify_phase(state)
        self.history.append(state)

        # AI improves over time — sigmoid growth (fast in middle, slow at ceiling)
        # q(t+1) = q(t) + growth * q(t) * (1 - q(t)/ceiling)  [logistic]
        q = self.ai_quality
        c = self.ai_quality_ceiling
        self.ai_quality = q + self.ai_quality_growth * q * (1.0 - q / c)
        self.ai_quality = min(c, max(0.01, self.ai_quality))
        self.ai_marginal_cost = max(0.01, self.ai_marginal_cost * self.ai_cost_decay)

        # New task creation: AI-driven productivity creates new task categories
        # that require human skills AI doesn't have (creativity, judgment, trust)
        # These are high-skill tasks that grow the total task pool
        new_tasks = int(self.base_n_tasks * self.new_task_rate)
        self.n_tasks_per_period = self.base_n_tasks + new_tasks * period

        return state


def run_experiment(n_periods: int = 100,
                   ai_cost_scenarios: list[float] | None = None,
                   seed: int = 42) -> dict:
    """Run the labor market experiment across multiple AI cost scenarios.

    Each scenario starts with a different AI marginal cost and simulates
    the market evolving over n_periods as AI quality improves and cost decays.
    """
    if ai_cost_scenarios is None:
        ai_cost_scenarios = [20.0, 10.0, 5.0, 2.0, 1.0, 0.5, 0.1]

    all_results = []

    for initial_cost in ai_cost_scenarios:
        print(f"  Running scenario: AI initial cost = {initial_cost:.1f}")
        market = LaborMarket(
            ai_marginal_cost=initial_cost,
            ai_quality=0.2,          # start lower
            ai_quality_growth=0.005, # slower quality improvement
            ai_cost_decay=0.99,      # slower cost decay
            seed=seed,
        )

        for t in range(n_periods):
            market.step(t)

        # Extract trajectory
        trajectory = {
            "initial_ai_cost": initial_cost,
            "periods": [
                {
                    "period": s.period,
                    "employment_rate": s.human_employment_rate,
                    "mean_wage": s.mean_human_wage,
                    "median_wage": s.median_human_wage,
                    "wages_by_skill": s.human_wages_by_skill,
                    "ai_tasks": s.ai_tasks_completed,
                    "human_tasks": s.human_tasks_completed,
                    "total_output": s.total_output,
                    "consumer_surplus": s.consumer_surplus,
                    "gini": s.gini_coefficient,
                    "phase": s.phase,
                }
                for s in market.history
            ],
        }

        # Phase transitions
        phases = [s.phase for s in market.history]
        transitions = []
        for i in range(1, len(phases)):
            if phases[i] != phases[i-1]:
                transitions.append({
                    "period": i,
                    "from": phases[i-1],
                    "to": phases[i],
                })
        trajectory["phase_transitions"] = transitions

        # Summary stats for final 10 periods
        final = market.history[-10:]
        trajectory["final_summary"] = {
            "mean_employment_rate": float(np.mean([s.human_employment_rate for s in final])),
            "mean_wage": float(np.mean([s.mean_human_wage for s in final])),
            "mean_gini": float(np.mean([s.gini_coefficient for s in final])),
            "mean_total_output": float(np.mean([s.total_output for s in final])),
            "dominant_phase": max(set(s.phase for s in final),
                                 key=lambda p: sum(1 for s in final if s.phase == p)),
        }

        all_results.append(trajectory)

    return {
        "experiment": "labor_market",
        "n_periods": n_periods,
        "n_humans": 100,
        "n_tasks_per_period": 150,
        "results": all_results,
    }


def print_summary(data: dict):
    """Print summary of labor market experiment."""
    print("\n" + "=" * 80)
    print("LABOR MARKET EXPERIMENT — SUMMARY")
    print("=" * 80)
    print(f"Periods: {data['n_periods']}, Humans: {data['n_humans']}, "
          f"Tasks/period: {data['n_tasks_per_period']}")

    print(f"\n{'AI Cost':>10} {'Employ%':>10} {'Mean Wage':>12} {'Gini':>8} {'Output':>10} {'Phase':>15}")
    print("-" * 70)

    for scenario in data["results"]:
        s = scenario["final_summary"]
        print(f"{scenario['initial_ai_cost']:>10.1f} "
              f"{s['mean_employment_rate']*100:>9.1f}% "
              f"{s['mean_wage']:>12.2f} "
              f"{s['mean_gini']:>8.3f} "
              f"{s['mean_total_output']:>10.1f} "
              f"{s['dominant_phase']:>15}")

    # Phase transition summary
    print("\n--- PHASE TRANSITIONS ---")
    for scenario in data["results"]:
        cost = scenario["initial_ai_cost"]
        transitions = scenario["phase_transitions"]
        if transitions:
            t_str = " → ".join(
                f"[t={t['period']}] {t['from']}→{t['to']}"
                for t in transitions
            )
            print(f"  Cost={cost:.1f}: {t_str}")
        else:
            phases = set(p["phase"] for p in scenario["periods"])
            print(f"  Cost={cost:.1f}: stays in {phases.pop()}")

    # Wage by skill quintile for extreme scenarios
    print("\n--- WAGES BY SKILL QUINTILE (final state) ---")
    print(f"{'AI Cost':>10} {'Q1(low)':>10} {'Q2':>10} {'Q3':>10} {'Q4':>10} {'Q5(high)':>10}")
    print("-" * 65)
    for scenario in data["results"]:
        cost = scenario["initial_ai_cost"]
        final_period = scenario["periods"][-1]
        ws = final_period["wages_by_skill"]
        print(f"{cost:>10.1f} "
              f"{ws.get('Q1', 0):>10.2f} "
              f"{ws.get('Q2', 0):>10.2f} "
              f"{ws.get('Q3', 0):>10.2f} "
              f"{ws.get('Q4', 0):>10.2f} "
              f"{ws.get('Q5', 0):>10.2f}")


if __name__ == "__main__":
    print("Running labor market experiment...")
    data = run_experiment()
    print_summary(data)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "labor_market_results.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nResults saved to {out_path}")
