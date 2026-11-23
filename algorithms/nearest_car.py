"""
Nearest-Car Algorithm (NC).
Selects the elevator with the minimal effective physical distance to the pickup floor,
factoring in operational availability, direction heading, and capacity limits.
"""

from typing import List, Optional, Tuple, Dict, Any
from .base import DispatchAlgorithm, DispatchDecision
from agents.elevator_agent import ElevatorAgent, Direction
from agents.passenger_agent import Passenger


class NearestCarAlgorithm(DispatchAlgorithm):
    """
    Nearest-Car Dispatching Strategy.
    Computes effective distance to pickup floor including directional penalties
    for cars moving away or in opposite directions.
    """

    def __init__(self):
        super().__init__(
            name="Nearest-Car",
            description="Assigns passenger to the physically closest available elevator with direction compatibility check."
        )

    def select_elevator(
        self,
        request: Passenger,
        elevators: List[ElevatorAgent],
        num_floors: int,
    ) -> Tuple[Optional[int], Optional[DispatchDecision]]:
        if not elevators:
            return None, None

        best_elevator_id: Optional[int] = None
        min_cost = float("inf")
        best_breakdown: Dict[str, Any] = {}
        all_evaluations: List[Dict[str, Any]] = []

        req_floor = request.pickup_floor
        req_dir = request.direction

        for elev in elevators:
            dist = abs(elev.current_floor - req_floor)
            penalty = 0.0

            # 1. Capacity Penalty
            if elev.is_full:
                penalty += 100.0
            elif elev.remaining_capacity <= 1:
                penalty += 15.0

            # 2. Directional heading check
            if elev.direction == Direction.IDLE:
                heading = "IDLE (Direct response)"
                penalty += 0.0
            elif elev.direction == Direction.UP:
                if req_floor >= elev.current_floor:
                    if req_dir == Direction.UP or req_dir == Direction.IDLE:
                        heading = "UP ahead (On-route match)"
                        penalty += 0.0
                    else:
                        heading = "UP ahead (Opposite passenger direction)"
                        penalty += 8.0
                else:
                    heading = "UP moving away (Behind car)"
                    # Car must finish ascent to its highest stop, then descend
                    highest_stop = max(elev.get_all_target_floors()) if elev.get_all_target_floors() else elev.current_floor
                    penalty += 2.0 * abs(highest_stop - elev.current_floor) + 12.0

            elif elev.direction == Direction.DOWN:
                if req_floor <= elev.current_floor:
                    if req_dir == Direction.DOWN or req_dir == Direction.IDLE:
                        heading = "DOWN ahead (On-route match)"
                        penalty += 0.0
                    else:
                        heading = "DOWN ahead (Opposite passenger direction)"
                        penalty += 8.0
                else:
                    heading = "DOWN moving away (Above car)"
                    lowest_stop = min(elev.get_all_target_floors()) if elev.get_all_target_floors() else elev.current_floor
                    penalty += 2.0 * abs(elev.current_floor - lowest_stop) + 12.0
            else:
                heading = "UNKNOWN"

            effective_cost = dist + penalty
            eval_info = {
                "elevator_id": elev.elevator_id,
                "current_floor": round(elev.current_floor, 1),
                "raw_distance": round(dist, 1),
                "direction": elev.direction.label,
                "heading_relation": heading,
                "load": f"{elev.passenger_count}/{elev.capacity}",
                "penalty": round(penalty, 1),
                "total_cost": round(effective_cost, 2),
            }
            all_evaluations.append(eval_info)

            if effective_cost < min_cost:
                min_cost = effective_cost
                best_elevator_id = elev.elevator_id
                best_breakdown = eval_info

        explanation = (
            f"Nearest-Car selected Elevator #{best_elevator_id} with effective distance {min_cost:.1f} floors "
            f"(Raw distance: {best_breakdown.get('raw_distance')} floors, "
            f"Car at Floor {best_breakdown.get('current_floor')}, "
            f"Direction: {best_breakdown.get('direction')})."
        )

        decision = DispatchDecision(
            passenger_id=request.id,
            elevator_id=best_elevator_id if best_elevator_id is not None else -1,
            algorithm_name=self.name,
            score=min_cost,
            breakdown={"selected": best_breakdown, "candidates": all_evaluations},
            explanation=explanation,
        )
        return best_elevator_id, decision
