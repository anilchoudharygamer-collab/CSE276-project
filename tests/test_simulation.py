# Unit tests for Simulation Engine, Building, Traffic Generator, and Benchmark Comparator.

from config.settings import SimulationConfig, TrafficScenarioType
from simulation.engine import SimulationEngine, SimulationState
from simulation.building import Building
from simulation.traffic_generator import TrafficGenerator
from analytics.comparison import AlgorithmComparator
from analytics.metrics import SimulationMetrics


def test_simulation_engine_lifecycle():
    config = SimulationConfig(num_floors=10, num_elevators=3, random_seed=42)
    engine = SimulationEngine(config=config)

    assert engine.state == SimulationState.STOPPED
    assert engine.current_time == 0.0

    engine.start()
    assert engine.state == SimulationState.RUNNING

    # Step simulation 10 seconds
    engine.run_steps(10, dt=1.0)
    assert engine.current_time == 10.0
    assert len(engine.history_snapshots) > 0

    engine.pause()
    assert engine.state == SimulationState.PAUSED

    engine.reset()
    assert engine.current_time == 0.0
    assert engine.state == SimulationState.STOPPED
    assert len(engine.all_passengers) == 0


def test_traffic_scenarios_generation():
    config = SimulationConfig(num_floors=15, num_elevators=4, random_seed=123)
    gen = TrafficGenerator(config)

    # 1. Morning Up-Peak (mostly pickup = 0)
    gen.set_scenario(TrafficScenarioType.MORNING_UP_PEAK)
    pax_morning = [gen._sample_floor_pair(TrafficScenarioType.MORNING_UP_PEAK, 15) for _ in range(50)]
    ground_pickups = sum(1 for p, d in pax_morning if p == 0)
    assert ground_pickups >= 35  # At least 70-85% at ground floor

    # 2. Evening Down-Peak (mostly dest = 0)
    gen.set_scenario(TrafficScenarioType.EVENING_DOWN_PEAK)
    pax_evening = [gen._sample_floor_pair(TrafficScenarioType.EVENING_DOWN_PEAK, 15) for _ in range(50)]
    ground_dests = sum(1 for p, d in pax_evening if d == 0)
    assert ground_dests >= 35


def test_algorithm_benchmark_comparator():
    """Runs a mini benchmark to verify all 3 algorithms complete and calculate metrics."""
    config = SimulationConfig(num_floors=8, num_elevators=3, random_seed=99)
    comparator = AlgorithmComparator(config=config)

    results = comparator.run_benchmark(
        duration_sec=20.0,
        scenario=TrafficScenarioType.MORNING_UP_PEAK,
        seed=99,
    )

    assert "comparison_df" in results
    assert "winners" in results
    df = results["comparison_df"]
    assert len(df) == 3
    assert set(df["Algorithm"]) == {"Nearest-Car", "Collective-Control", "Utility-Based Intelligent"}
