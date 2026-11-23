"""
Algorithm Comparison and Benchmarking Engine.
Executes parallel reproducible simulation runs of Nearest-Car, Collective-Control,
and Utility-Based Intelligent Dispatch under identical traffic seeds and scenarios.
"""

from typing import Dict, Any, List, Optional
import copy
import pandas as pd
import numpy as np

from config.settings import SimulationConfig, TrafficScenarioType
from simulation.engine import SimulationEngine
from agents.dispatch_agent import DispatchAgent
from algorithms.nearest_car import NearestCarAlgorithm
from algorithms.collective_control import CollectiveControlAlgorithm
from algorithms.utility_based import UtilityBasedAlgorithm
from .metrics import SimulationMetrics


class AlgorithmComparator:
    """
    Automated Benchmark Engine.
    Executes identical seeded traffic across all 3 dispatch algorithms
    and produces rigorous comparative analytics.
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.base_config = config or SimulationConfig()

    def run_benchmark(
        self,
        duration_sec: float = 180.0,
        scenario: Optional[TrafficScenarioType] = None,
        seed: Optional[int] = None,
        progress_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Runs an identical simulation across Nearest-Car, Collective-Control,
        and Utility-Based algorithms for the specified duration.
        """
        bench_scenario = scenario or self.base_config.scenario
        bench_seed = seed if seed is not None else self.base_config.random_seed

        algorithms = [
            NearestCarAlgorithm(),
            CollectiveControlAlgorithm(),
            UtilityBasedAlgorithm(self.base_config.utility_weights),
        ]

        results: Dict[str, Any] = {}
        total_algos = len(algorithms)

        for idx, algo in enumerate(algorithms):
            # Create isolated fresh config copy
            run_config = copy.deepcopy(self.base_config)
            run_config.scenario = bench_scenario
            run_config.random_seed = bench_seed

            dispatch_agent = DispatchAgent(algorithm=algo)
            engine = SimulationEngine(config=run_config, dispatch_agent=dispatch_agent)
            engine.reset(bench_seed)
            engine.start()

            # Advance simulation in discrete 1.0s ticks
            dt = 1.0
            steps = int(duration_sec / dt)
            for s in range(steps):
                engine.step(dt)
                if progress_callback:
                    pct = ((idx * steps + s + 1) / (total_algos * steps))
                    progress_callback(pct, f"Evaluating {algo.name} ({s+1}/{steps}s)...")

            # Compute run metrics
            pax_metrics = SimulationMetrics.calculate_passenger_metrics(
                engine.all_passengers, engine.completed_passengers, engine.current_time
            )
            elev_metrics = SimulationMetrics.calculate_elevator_metrics(
                engine.building.elevators, engine.current_time
            )

            # Store passenger wait times for histogram/distribution
            wait_times = [p.wait_time(engine.current_time) for p in engine.all_passengers]

            results[algo.name] = {
                "algorithm_name": algo.name,
                "summary": engine.get_summary_metrics(),
                "passenger_metrics": pax_metrics,
                "elevator_metrics": elev_metrics,
                "history_snapshots": engine.history_snapshots,
                "wait_times": wait_times,
                "total_passengers": len(engine.all_passengers),
                "completed_passengers": len(engine.completed_passengers),
            }

        # Build comparison summary table
        comparison_table = []
        for name, data in results.items():
            pm = data["passenger_metrics"]
            em = data["elevator_metrics"]
            comparison_table.append({
                "Algorithm": name,
                "Avg Wait Time (s)": pm["avg_wait_sec"],
                "P95 Wait Time (s)": pm["p95_wait_sec"],
                "Max Wait Time (s)": pm["max_wait_sec"],
                "Avg Journey Time (s)": pm["avg_journey_sec"],
                "Passengers Served": pm["completed"],
                "Total Distance (floors)": em["total_distance_floors"],
                "Total Energy (kWh)": em["total_energy_kwh"],
                "Elevator Utilization (%)": em["avg_utilization_pct"],
            })

        df_comparison = pd.DataFrame(comparison_table)

        # Determine winner
        best_wait = df_comparison.loc[df_comparison["Avg Wait Time (s)"].idxmin()]["Algorithm"]
        best_journey = df_comparison.loc[df_comparison["Avg Journey Time (s)"].idxmin()]["Algorithm"]
        best_energy = df_comparison.loc[df_comparison["Total Energy (kWh)"].idxmin()]["Algorithm"]
        best_served = df_comparison.loc[df_comparison["Passengers Served"].idxmax()]["Algorithm"]

        # Calculate Utility-Based improvements relative to Nearest-Car
        nc_wait = results["Nearest-Car"]["passenger_metrics"]["avg_wait_sec"]
        ub_wait = results["Utility-Based Intelligent"]["passenger_metrics"]["avg_wait_sec"]
        wait_improvement = ((nc_wait - ub_wait) / max(0.1, nc_wait)) * 100.0

        nc_energy = results["Nearest-Car"]["elevator_metrics"]["total_energy_kwh"]
        ub_energy = results["Utility-Based Intelligent"]["elevator_metrics"]["total_energy_kwh"]
        energy_improvement = ((nc_energy - ub_energy) / max(0.001, nc_energy)) * 100.0

        return {
            "scenario": bench_scenario.value if hasattr(bench_scenario, "value") else str(bench_scenario),
            "seed": bench_seed,
            "duration_sec": duration_sec,
            "raw_results": results,
            "comparison_df": df_comparison,
            "winners": {
                "lowest_wait_time": best_wait,
                "lowest_journey_time": best_journey,
                "lowest_energy": best_energy,
                "highest_throughput": best_served,
            },
            "utility_improvements": {
                "wait_time_reduction_pct": round(wait_improvement, 1),
                "energy_savings_pct": round(energy_improvement, 1),
            },
        }
