"""
Base class and decision contracts for Elevator Group Dispatching Algorithms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from agents.elevator_agent import ElevatorAgent
from agents.passenger_agent import Passenger


@dataclass
class DispatchDecision:
    """Explains why a specific elevator was selected for a passenger request."""
    passenger_id: str
    elevator_id: int
    algorithm_name: str
    score: float
    breakdown: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passenger_id": self.passenger_id,
            "elevator_id": self.elevator_id,
            "algorithm": self.algorithm_name,
            "score": round(self.score, 3),
            "breakdown": self.breakdown,
            "explanation": self.explanation,
        }


class DispatchAlgorithm(ABC):
    """Abstract Base Class for all Elevator Dispatch Algorithms."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def select_elevator(
        self,
        request: Passenger,
        elevators: List[ElevatorAgent],
        num_floors: int,
    ) -> Tuple[Optional[int], Optional[DispatchDecision]]:
        """
        Evaluates all available elevators for the given passenger request
        and returns the chosen elevator_id and the DispatchDecision rationale.
        """
        pass
