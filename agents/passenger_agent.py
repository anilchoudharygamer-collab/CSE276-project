"""
Passenger Agent module for Intelligent Elevator Dispatch.
Represents individual passengers with origin, destination, timing, status, and priority.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class PassengerStatus(str, Enum):
    WAITING = "WAITING"
    BOARDING = "BOARDING"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class Direction(int, Enum):
    DOWN = -1
    IDLE = 0
    UP = 1

    @property
    def label(self) -> str:
        if self == Direction.UP:
            return "UP"
        elif self == Direction.DOWN:
            return "DOWN"
        return "IDLE"

    @property
    def symbol(self) -> str:
        if self == Direction.UP:
            return "▲"
        elif self == Direction.DOWN:
            return "▼"
        return "■"


@dataclass
class Passenger:
    """Represents a passenger agent in the simulation."""
    id: str
    pickup_floor: int
    destination_floor: int
    request_time: float
    is_priority: bool = False
    assigned_elevator_id: Optional[int] = None
    board_time: Optional[float] = None
    alight_time: Optional[float] = None
    status: PassengerStatus = PassengerStatus.WAITING

    @property
    def direction(self) -> Direction:
        if self.destination_floor > self.pickup_floor:
            return Direction.UP
        elif self.destination_floor < self.pickup_floor:
            return Direction.DOWN
        return Direction.IDLE

    def wait_time(self, current_time: float) -> float:
        """Returns the time spent waiting for an elevator to pick them up."""
        if self.board_time is not None:
            return max(0.0, self.board_time - self.request_time)
        return max(0.0, current_time - self.request_time)

    def travel_time(self, current_time: float) -> float:
        """Returns the time spent inside the elevator cabin."""
        if self.board_time is None:
            return 0.0
        if self.alight_time is not None:
            return max(0.0, self.alight_time - self.board_time)
        return max(0.0, current_time - self.board_time)

    def total_journey_time(self, current_time: float) -> float:
        """Total time from pressing the hall call button to reaching destination."""
        if self.alight_time is not None:
            return max(0.0, self.alight_time - self.request_time)
        return max(0.0, current_time - self.request_time)

    def to_dict(self, current_time: Optional[float] = None) -> Dict[str, Any]:
        cur = current_time if current_time is not None else (self.alight_time or self.request_time)
        return {
            "id": self.id,
            "pickup_floor": self.pickup_floor,
            "destination_floor": self.destination_floor,
            "direction": self.direction.label,
            "request_time": round(self.request_time, 2),
            "board_time": round(self.board_time, 2) if self.board_time is not None else None,
            "alight_time": round(self.alight_time, 2) if self.alight_time is not None else None,
            "wait_time": round(self.wait_time(cur), 2),
            "travel_time": round(self.travel_time(cur), 2),
            "total_journey_time": round(self.total_journey_time(cur), 2),
            "is_priority": self.is_priority,
            "status": self.status.value,
            "assigned_elevator_id": self.assigned_elevator_id,
        }
