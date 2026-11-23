# Unit tests for PassengerAgent and ElevatorAgent.
# Tests capacity limits, door state machines, kinematics, and priority requests.

from agents.passenger_agent import Passenger, PassengerStatus, Direction
from agents.elevator_agent import ElevatorAgent, DoorState, OperationalStatus


def test_passenger_agent_properties():
    p1 = Passenger(
        id="P-001",
        pickup_floor=0,
        destination_floor=10,
        request_time=5.0,
        is_priority=True,
    )
    assert p1.direction == Direction.UP
    assert p1.wait_time(15.0) == 10.0
    assert p1.travel_time(15.0) == 0.0

    p1.board_time = 12.0
    p1.status = PassengerStatus.IN_TRANSIT
    assert p1.wait_time(20.0) == 7.0
    assert p1.travel_time(20.0) == 8.0

    p1.alight_time = 22.0
    p1.status = PassengerStatus.COMPLETED
    assert p1.travel_time(30.0) == 10.0
    assert p1.total_journey_time(30.0) == 17.0


def test_elevator_capacity_limit():
    """Ensure elevator strictly enforces maximum cabin capacity."""
    elev = ElevatorAgent(elevator_id=1, capacity=3, speed=1.0)
    # Add 4 passengers for pickup at floor 0
    for i in range(4):
        p = Passenger(id=f"P-{i}", pickup_floor=0, destination_floor=5, request_time=0.0)
        elev.assign_pickup(p)

    # Arrive at floor 0 and cycle doors
    elev.step(0.1, current_sim_time=0.1) # Starts door opening
    elev.door_timer = 0.0 # Force open
    boarded, alighted = elev.step(0.1, current_sim_time=0.2)

    # Only 3 passengers can board
    assert len(boarded) == 3
    assert elev.passenger_count == 3
    assert elev.is_full is True
    assert len(elev.assigned_pickups) == 1  # 4th passenger remains waiting for subsequent pickup


def test_elevator_boundaries_and_movement():
    """Ensure elevator stays within valid floor bounds and moves correctly."""
    elev = ElevatorAgent(elevator_id=1, capacity=8, speed=1.0, initial_floor=0.0)
    p = Passenger(id="P-1", pickup_floor=4, destination_floor=2, request_time=0.0)
    elev.assign_pickup(p)

    assert elev.direction == Direction.UP
    assert elev.target_floor == 4

    # Run for 2 seconds -> should be at floor 2
    elev.step(2.0, current_sim_time=2.0)
    assert 1.9 <= elev.current_floor <= 2.1
    assert elev.direction == Direction.UP

    # Run for 2 more seconds -> reaches floor 4
    elev.step(2.0, current_sim_time=4.0)
    assert elev.current_floor == 4.0


def test_elevator_energy_accumulation():
    """Ensure moving and idle power are tracked."""
    elev = ElevatorAgent(elevator_id=1, motor_power_moving_kw=10.0, motor_power_idle_kw=1.0)
    initial_energy = elev.total_energy_kwh

    # Idle step
    elev.step(1.0, current_sim_time=1.0)
    assert elev.total_energy_kwh > initial_energy
    assert elev.idle_time == 1.0
