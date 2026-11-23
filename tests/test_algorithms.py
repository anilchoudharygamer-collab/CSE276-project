# Unit tests for Dispatch Algorithms

from agents.elevator_agent import ElevatorAgent, Direction
from agents.passenger_agent import Passenger
from algorithms.nearest_car import NearestCarAlgorithm
from algorithms.collective_control import CollectiveControlAlgorithm
from algorithms.utility_based import UtilityBasedAlgorithm
from config.settings import UtilityWeights


def create_test_elevators():
    """Creates a group of 3 elevators at different floors and directions."""
    e1 = ElevatorAgent(elevator_id=1, capacity=8, initial_floor=2.0)
    e1.direction = Direction.UP
    e1.target_floor = 10

    e2 = ElevatorAgent(elevator_id=2, capacity=8, initial_floor=6.0)
    e2.direction = Direction.IDLE

    e3 = ElevatorAgent(elevator_id=3, capacity=8, initial_floor=12.0)
    e3.direction = Direction.DOWN
    e3.target_floor = 0

    return [e1, e2, e3]


def test_nearest_car_algorithm():
    elevators = create_test_elevators()
    nc = NearestCarAlgorithm()

    # Passenger at floor 5 wanting to go to floor 8
    p = Passenger(id="P-01", pickup_floor=5, destination_floor=8, request_time=0.0)
    chosen_id, decision = nc.select_elevator(p, elevators, num_floors=15)

    assert chosen_id is not None
    assert decision is not None
    assert decision.algorithm_name == "Nearest-Car"
    assert "explanation" in decision.to_dict()


def test_collective_control_direction_matching():
    elevators = create_test_elevators()
    cc = CollectiveControlAlgorithm()

    # Passenger at Floor 4 wanting to go UP to Floor 9
    # E1 is at Floor 2 moving UP (Category A: Co-directional ahead)
    # E2 is at Floor 6 IDLE
    p_up = Passenger(id="P-UP", pickup_floor=4, destination_floor=9, request_time=0.0)
    chosen_id, decision = cc.select_elevator(p_up, elevators, num_floors=15)

    # E1 should be prioritized because it is already moving UP and Floor 4 is ahead of it!
    assert chosen_id == 1
    assert "Co-directional UP" in decision.explanation


def test_utility_based_priority_and_weights():
    elevators = create_test_elevators()
    weights = UtilityWeights(priority_weight=5.0)
    ub = UtilityBasedAlgorithm(weights=weights)

    p_vip = Passenger(id="P-VIP", pickup_floor=6, destination_floor=14, request_time=0.0, is_priority=True)
    chosen_id, decision = ub.select_elevator(p_vip, elevators, num_floors=15)

    assert chosen_id is not None
    assert decision.score < float("inf")
    assert "priority_bonus" in decision.breakdown["selected"]
