"""
Building Structure model.
Represents floors, waiting queues, shafts, and physical layout of the building.
"""

from typing import List, Dict, Any, Optional
from agents.elevator_agent import ElevatorAgent
from agents.passenger_agent import Passenger, Direction, PassengerStatus
from config.settings import SimulationConfig


class Floor:
    """Represents an individual building floor with hall call queues."""

    def __init__(self, floor_number: int, name: Optional[str] = None):
        self.floor_number = floor_number
        self.name = name or (f"Ground (Lobby)" if floor_number == 0 else f"Floor {floor_number}")
        self.up_waiting_queue: List[Passenger] = []
        self.down_waiting_queue: List[Passenger] = []

    @property
    def total_waiting(self) -> int:
        return len(self.up_waiting_queue) + len(self.down_waiting_queue)

    def add_passenger(self, passenger: Passenger):
        if passenger.direction == Direction.UP:
            self.up_waiting_queue.append(passenger)
        else:
            self.down_waiting_queue.append(passenger)

    def remove_passenger(self, passenger: Passenger):
        if passenger in self.up_waiting_queue:
            self.up_waiting_queue.remove(passenger)
        if passenger in self.down_waiting_queue:
            self.down_waiting_queue.remove(passenger)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "floor": self.floor_number,
            "name": self.name,
            "up_count": len(self.up_waiting_queue),
            "down_count": len(self.down_waiting_queue),
            "total_waiting": self.total_waiting,
            "has_priority": any(p.is_priority for p in (self.up_waiting_queue + self.down_waiting_queue)),
        }


class Building:
    """Represents the complete multi-floor building structure."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.floors: List[Floor] = [Floor(i) for i in range(config.num_floors)]
        self.elevators: List[ElevatorAgent] = []
        self._initialize_elevators()

    def _initialize_elevators(self):
        self.elevators.clear()
        for i in range(self.config.num_elevators):
            # Spread initial elevators across floors for realistic distribution
            init_floor = (i * (self.config.num_floors - 1)) // max(1, self.config.num_elevators - 1) if self.config.num_elevators > 1 else 0
            elev = ElevatorAgent(
                elevator_id=i + 1,
                capacity=self.config.elevator_capacity,
                speed=self.config.elevator_speed,
                door_operation_time=self.config.door_operation_time,
                passenger_transfer_time=self.config.passenger_transfer_time,
                initial_floor=float(init_floor),
                floor_height_meters=self.config.floor_height_meters,
                motor_power_moving_kw=self.config.motor_power_moving_kw,
                motor_power_idle_kw=self.config.motor_power_idle_kw,
                door_cycle_kwh=self.config.door_cycle_kwh,
            )
            self.elevators.append(elev)

    def get_floor(self, floor_num: int) -> Optional[Floor]:
        if 0 <= floor_num < len(self.floors):
            return self.floors[floor_num]
        return None

    def add_passenger(self, passenger: Passenger):
        floor = self.get_floor(passenger.pickup_floor)
        if floor:
            floor.add_passenger(passenger)

    def remove_passenger(self, passenger: Passenger):
        floor = self.get_floor(passenger.pickup_floor)
        if floor:
            floor.remove_passenger(passenger)

    def get_total_waiting_passengers(self) -> int:
        return sum(f.total_waiting for f in self.floors)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_floors": self.config.num_floors,
            "num_elevators": self.config.num_elevators,
            "floors": [f.to_dict() for f in self.floors],
            "elevators": [e.to_dict() for e in self.elevators],
            "total_waiting": self.get_total_waiting_passengers(),
        }
