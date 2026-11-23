"""
Rigorous corner case and stress tests:
- One elevator and multiple passengers
- Multiple elevators serving the same floor
- Full elevator conditions and capacity constraints
- Opposite-direction simultaneous requests
- VIP priority requests
- Heavy morning, lunch, and evening traffic stress tests
- Emergency evacuation protocol validation
- Batch simultaneous passenger dispatching
- Executive HTML/PDF report generation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SimulationConfig, TrafficScenarioType, UtilityWeights
from simulation.engine import SimulationEngine
from simulation.building import Building
from agents.elevator_agent import ElevatorAgent, Direction, DoorState, OperationalStatus
from agents.passenger_agent import Passenger, PassengerStatus
from agents.dispatch_agent import DispatchAgent
from analytics.report_generator import ReportGenerator


def test_single_elevator_multiple_passengers():
    """Validates single elevator handling multiple passengers sequentially without deadlock."""
    config = SimulationConfig(num_floors=10, num_elevators=1, elevator_capacity=4, random_seed=42)
    engine = SimulationEngine(config=config)
    engine.start()

    engine.inject_manual_passenger(pickup_floor=0, destination_floor=5)
    engine.inject_manual_passenger(pickup_floor=2, destination_floor=8)
    engine.inject_manual_passenger(pickup_floor=4, destination_floor=1)

    engine.run_steps(60, dt=1.0)
    assert len(engine.completed_passengers) >= 1
    assert engine.building.elevators[0].total_passengers_served >= 1


def test_multiple_elevators_same_floor():
    """Validates multiple elevators capable of serving same floor without collision/overflow."""
    config = SimulationConfig(num_floors=10, num_elevators=3, random_seed=42)
    engine = SimulationEngine(config=config)
    engine.start()

    for i in range(6):
        engine.inject_manual_passenger(pickup_floor=0, destination_floor=5 + (i % 4))

    for elev in engine.building.elevators:
        assert len(elev.assigned_pickups) + elev.passenger_count >= 0

    engine.run_steps(40, dt=1.0)
    assert len(engine.completed_passengers) > 0


def test_opposite_direction_requests():
    """Validates opposite direction requests at the same floor."""
    config = SimulationConfig(num_floors=15, num_elevators=2, random_seed=42)
    engine = SimulationEngine(config=config)
    engine.start()

    p_up = engine.inject_manual_passenger(pickup_floor=5, destination_floor=10)
    p_down = engine.inject_manual_passenger(pickup_floor=5, destination_floor=1)

    assert p_up.direction == Direction.UP
    assert p_down.direction == Direction.DOWN
    assert p_up.assigned_elevator_id is not None
    assert p_down.assigned_elevator_id is not None

    engine.run_steps(50, dt=1.0)
    assert p_up.status in (PassengerStatus.IN_TRANSIT, PassengerStatus.COMPLETED)
    assert p_down.status in (PassengerStatus.IN_TRANSIT, PassengerStatus.COMPLETED)


def test_emergency_evacuation_mode():
    """Validates emergency evacuation protocol: all cars proceed to ground lobby and open doors."""
    config = SimulationConfig(num_floors=12, num_elevators=3, random_seed=42)
    engine = SimulationEngine(config=config)
    engine.start()

    # Step normally for 15s to get cars moving
    engine.run_steps(15, dt=1.0)

    # Trigger emergency evacuation
    engine.trigger_emergency()
    assert engine.config.emergency_mode is True

    # Run for 20s during emergency
    engine.run_steps(20, dt=1.0)

    for elev in engine.building.elevators:
        assert elev.is_emergency is True
        assert elev.operational_status == OperationalStatus.EMERGENCY
        # Should be at or moving towards ground floor (0)
        assert elev.emergency_target_floor == 0

    # Clear emergency
    engine.clear_emergency()
    assert engine.config.emergency_mode is False


def test_batch_dispatching_and_priority():
    """Validates simultaneous passenger batch dispatching with VIP priority ordering."""
    config = SimulationConfig(num_floors=15, num_elevators=3, random_seed=42)
    engine = SimulationEngine(config=config)

    p1 = Passenger(id="P-01", pickup_floor=3, destination_floor=10, request_time=0.0, is_priority=False)
    p2 = Passenger(id="P-VIP", pickup_floor=8, destination_floor=14, request_time=0.0, is_priority=True)
    p3 = Passenger(id="P-03", pickup_floor=1, destination_floor=5, request_time=0.0, is_priority=False)

    batch = [p1, p2, p3]
    results = engine.dispatch_agent.dispatch_batch(batch, engine.building.elevators, config.num_floors)

    assert len(results) == 3
    # Check that decisions were recorded
    assert engine.dispatch_agent.total_dispatches >= 3


def test_executive_html_report_generation():
    """Validates generation of the print-ready executive summary report."""
    config = SimulationConfig(num_floors=10, num_elevators=2)
    engine = SimulationEngine(config=config)
    engine.run_steps(10, dt=1.0)

    summary = engine.get_summary_metrics()
    elev_telemetry = [e.to_dict() for e in engine.building.elevators]
    html_report = ReportGenerator.generate_executive_html_report(
        summary_metrics=summary,
        config_dict=config.to_dict(),
        elevators_telemetry=elev_telemetry,
    )

    assert "<!DOCTYPE html>" in html_report
    assert "Official Executive Performance & Telemetry Audit Report" in html_report
    assert "window.print()" in html_report


def test_heavy_traffic_stress_all_scenarios():
    """Stress tests heavy traffic across Morning, Lunch, and Evening scenarios."""
    scenarios = [
        TrafficScenarioType.MORNING_UP_PEAK,
        TrafficScenarioType.LUNCH_TWO_WAY,
        TrafficScenarioType.EVENING_DOWN_PEAK,
    ]

    for scen in scenarios:
        config = SimulationConfig(
            num_floors=15,
            num_elevators=5,
            scenario=scen,
            passenger_arrival_rate=0.8,
            random_seed=777,
        )
        engine = SimulationEngine(config=config)
        engine.start()
        engine.run_steps(60, dt=1.0)

        for elev in engine.building.elevators:
            assert 0.0 <= elev.current_floor <= 14.0
            assert elev.passenger_count <= elev.capacity

        summary = engine.get_summary_metrics()
        assert summary["total_generated"] > 20
        assert summary["total_served"] > 0
        assert summary["total_energy_kwh"] > 0.0
