"""
Comprehensive Test Runner for the Intelligent Elevator Dispatch System.
Validates agents, dispatch algorithms, simulation dynamics, emergency mode, and reports.
"""

import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.test_agents import (
    test_passenger_agent_properties,
    test_elevator_capacity_limit,
    test_elevator_boundaries_and_movement,
    test_elevator_energy_accumulation,
)
from tests.test_algorithms import (
    test_nearest_car_algorithm,
    test_collective_control_direction_matching,
    test_utility_based_priority_and_weights,
)
from tests.test_simulation import (
    test_simulation_engine_lifecycle,
    test_traffic_scenarios_generation,
    test_algorithm_benchmark_comparator,
)
from tests.test_corner_cases import (
    test_single_elevator_multiple_passengers,
    test_multiple_elevators_same_floor,
    test_opposite_direction_requests,
    test_emergency_evacuation_mode,
    test_batch_dispatching_and_priority,
    test_executive_html_report_generation,
    test_heavy_traffic_stress_all_scenarios,
)

TESTS = [
    ("Passenger Agent Properties", test_passenger_agent_properties),
    ("Elevator Capacity Limit Enforcement", test_elevator_capacity_limit),
    ("Elevator Boundaries & Movement Kinematics", test_elevator_boundaries_and_movement),
    ("Elevator Energy Accumulation", test_elevator_energy_accumulation),
    ("Nearest-Car Algorithm Logic", test_nearest_car_algorithm),
    ("Collective-Control Co-Directional Matching", test_collective_control_direction_matching),
    ("Utility-Based Priority and Scoring", test_utility_based_priority_and_weights),
    ("Simulation Engine Lifecycle & State", test_simulation_engine_lifecycle),
    ("Traffic Scenarios Generation", test_traffic_scenarios_generation),
    ("3-Algorithm Benchmark Execution & Metrics", test_algorithm_benchmark_comparator),
    ("Single Elevator Multiple Passengers Handling", test_single_elevator_multiple_passengers),
    ("Multiple Elevators Serving Same Floor", test_multiple_elevators_same_floor),
    ("Opposite Direction Simultaneous Requests", test_opposite_direction_requests),
    ("Emergency Evacuation Safety Mode", test_emergency_evacuation_mode),
    ("Simultaneous Batch Dispatching with VIP Order", test_batch_dispatching_and_priority),
    ("Executive HTML/PDF Report Generation", test_executive_html_report_generation),
    ("Heavy Traffic Stress Across All 3 Scenarios", test_heavy_traffic_stress_all_scenarios),
]

def run_all():
    print("=" * 65)
    print("RUNNING UPGRADED ELEVATOR AGENT SYSTEM TEST SUITE (17 TESTS)")
    print("=" * 65)
    passed = 0
    failed = 0

    for name, func in TESTS:
        try:
            func()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 65)
    print(f"Results: {passed} PASSED, {failed} FAILED (Total: {len(TESTS)})")
    print("=" * 65)
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_all()
