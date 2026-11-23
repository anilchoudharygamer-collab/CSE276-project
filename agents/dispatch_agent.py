"""
Central Dispatch Agent.
Coordinates passenger assignments among the elevator group using the selected
dispatching strategy (Nearest-Car, Collective-Control, or Utility-Based Intelligent).
"""

from typing import List, Optional, Dict, Any, Deque
from collections import deque
from .elevator_agent import ElevatorAgent
from .passenger_agent import Passenger, PassengerStatus
from algorithms.base import DispatchAlgorithm, DispatchDecision
from algorithms.nearest_car import NearestCarAlgorithm
from algorithms.collective_control import CollectiveControlAlgorithm
from algorithms.utility_based import UtilityBasedAlgorithm


class DispatchAgent:
    """
    Central Intelligent Dispatch Controller.
    Receives hall calls, manages queueing, executes algorithm evaluation,
    and maintains audit logs of all dispatch decisions.
    """

    def __init__(self, algorithm: Optional[DispatchAlgorithm] = None, max_history: int = 150):
        self.algorithm: DispatchAlgorithm = algorithm or UtilityBasedAlgorithm()
        self.decision_history: Deque[DispatchDecision] = deque(maxlen=max_history)
        self.total_dispatches: int = 0
        self.unassigned_queue: List[Passenger] = []

    def set_algorithm(self, algorithm: DispatchAlgorithm):
        """Switches the active dispatch strategy at runtime."""
        self.algorithm = algorithm

    def dispatch_batch(
        self,
        requests: List[Passenger],
        elevators: List[ElevatorAgent],
        num_floors: int,
    ) -> List[Tuple[Optional[int], Optional[DispatchDecision]]]:
        """
        Dispatches a batch of simultaneous passenger requests arriving in the same tick.
        Prioritizes VIP requests first, then sorts by pickup floor to avoid contention.
        """
        # Sort VIP first, then by pickup floor
        sorted_requests = sorted(requests, key=lambda p: (not p.is_priority, p.pickup_floor))
        results = []
        for req in sorted_requests:
            res = self.dispatch_request(req, elevators, num_floors)
            results.append(res)
        return results

    def dispatch_request(
        self,
        request: Passenger,
        elevators: List[ElevatorAgent],
        num_floors: int,
    ) -> Tuple[Optional[int], Optional[DispatchDecision]]:
        """
        Processes an incoming passenger request and assigns it to the optimal elevator.
        """
        chosen_id, decision = self.algorithm.select_elevator(
            request=request,
            elevators=elevators,
            num_floors=num_floors,
        )

        if chosen_id is not None and decision is not None:
            # Assign to the corresponding elevator
            matched = False
            for elev in elevators:
                if elev.elevator_id == chosen_id:
                    elev.assign_pickup(request)
                    matched = True
                    break

            if matched:
                self.decision_history.appendleft(decision)
                self.total_dispatches += 1
                return chosen_id, decision

        # If no elevator could accommodate (e.g. all full and restricted)
        if request not in self.unassigned_queue:
            self.unassigned_queue.append(request)
        return None, None

    def retry_unassigned(self, elevators: List[ElevatorAgent], num_floors: int) -> int:
        """Attempts to dispatch previously unassigned requests."""
        if not self.unassigned_queue:
            return 0

        successfully_dispatched = 0
        remaining: List[Passenger] = []

        for req in self.unassigned_queue:
            if req.status != PassengerStatus.WAITING:
                continue
            chosen_id, _ = self.dispatch_request(req, elevators, num_floors)
            if chosen_id is not None:
                successfully_dispatched += 1
            else:
                remaining.append(req)

        self.unassigned_queue = remaining
        return successfully_dispatched

    def get_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns the most recent dispatch decisions formatted for the UI."""
        return [d.to_dict() for d in list(self.decision_history)[:limit]]

    def get_filtered_decisions(
        self,
        elevator_id: Optional[int] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Returns filtered dispatch decisions by elevator ID."""
        decisions = [d.to_dict() for d in self.decision_history]
        if elevator_id is not None:
            decisions = [d for d in decisions if d["elevator_id"] == elevator_id]
        return decisions[:limit]
