"""
Collective-Control Algorithm (CC).
Standard duplex/triplex collective dispatching strategy that prioritizes serving calls
along the elevator's current direction of travel before reversing or assigning idle units.
"""

from typing import List, Optional, Tuple, Dict, Any
from .base import DispatchAlgorithm, DispatchDecision
from agents.elevator_agent import ElevatorAgent, Direction
from agents.passenger_agent import Passenger


class CollectiveControlAlgorithm(DispatchAlgorithm):
    """
    Collective-Control Dispatching Strategy.
    Enforces directional persistence: elevators continue in current direction,
    collecting compatible calls along the way.
    """

    def __init__(self):
        super().__init__(
            name="Collective-Control",
            description="Prioritizes on-route compatible direction calls to minimize reversals and stops."
        )

    def select_elevator(
        self,
        request: Passenger,
        elevators: List[ElevatorAgent],
        num_floors: int,
    ) -> Tuple[Optional[int], Optional[DispatchDecision]]:
        if not elevators:
            return None, None

        req_floor = request.pickup_floor
        req_dir = request.direction

        best_elevator_id: Optional[int] = None
        min_score = float("inf")
        best_breakdown: Dict[str, Any] = {}
        all_evals: List[Dict[str, Any]] = []

        for elev in elevators:
            cur = elev.current_floor
            stops = elev.get_all_target_floors()
            category = ""
            score = 0.0

            # Capacity safety check
            capacity_penalty = 150.0 if elev.is_full else (15.0 if elev.remaining_capacity <= 1 else 0.0)

            # Categorize relation:
            # 1. On-Route Matching Direction (Category A - highest priority)
            is_on_route = False
            if elev.direction == Direction.UP and req_dir == Direction.UP and req_floor >= cur:
                is_on_route = True
                category = "A: Co-directional UP ahead"
                # Cost is distance + small penalty for intermediate stops
                intermediate_stops = sum(1 for s in stops if cur <= s <= req_floor)
                score = (req_floor - cur) + (intermediate_stops * 1.5)

            elif elev.direction == Direction.DOWN and req_dir == Direction.DOWN and req_floor <= cur:
                is_on_route = True
                category = "A: Co-directional DOWN ahead"
                intermediate_stops = sum(1 for s in stops if req_floor <= s <= cur)
                score = (cur - req_floor) + (intermediate_stops * 1.5)

            # 2. Idle Car (Category B - secondary priority)
            elif elev.direction == Direction.IDLE:
                category = "B: Idle elevator"
                dist = abs(cur - req_floor)
                # Slight base penalty so on-route moving cars pick up natural stops,
                # but close idle cars are preferred over distant reversing cars.
                score = 10.0 + dist

            # 3. Opposite Direction or Passed Call (Category C - Reversal needed)
            else:
                category = "C: Requires reversal"
                if elev.direction == Direction.UP:
                    # Car will ascend to highest stop, then reverse to go down
                    highest = max(stops) if stops else cur
                    run_remaining = max(0.0, highest - cur)
                    return_dist = abs(highest - req_floor)
                    score = 30.0 + (run_remaining * 2.0) + return_dist
                else:
                    # Car will descend to lowest stop, then reverse to go up
                    lowest = min(stops) if stops else cur
                    run_remaining = max(0.0, cur - lowest)
                    return_dist = abs(req_floor - lowest)
                    score = 30.0 + (run_remaining * 2.0) + return_dist

            total_score = score + capacity_penalty
            eval_info = {
                "elevator_id": elev.elevator_id,
                "category": category,
                "current_floor": round(cur, 1),
                "direction": elev.direction.label,
                "base_score": round(score, 1),
                "capacity_penalty": capacity_penalty,
                "total_score": round(total_score, 2),
                "passengers": f"{elev.passenger_count}/{elev.capacity}",
            }
            all_evals.append(eval_info)

            if total_score < min_score:
                min_score = total_score
                best_elevator_id = elev.elevator_id
                best_breakdown = eval_info

        explanation = (
            f"Collective-Control assigned Elevator #{best_elevator_id} "
            f"under {best_breakdown.get('category')} (Score: {min_score:.1f}, "
            f"Car at Floor {best_breakdown.get('current_floor')}, "
            f"Direction: {best_breakdown.get('direction')})."
        )

        decision = DispatchDecision(
            passenger_id=request.id,
            elevator_id=best_elevator_id if best_elevator_id is not None else -1,
            algorithm_name=self.name,
            score=min_score,
            breakdown={"selected": best_breakdown, "candidates": all_evals},
            explanation=explanation,
        )
        return best_elevator_id, decision
