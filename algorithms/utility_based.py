"""
Utility-Based Intelligent Dispatch Algorithm.
Multi-criteria objective optimization function that minimizes passenger waiting time,
journey duration, elevator congestion, and energy consumption using configurable weights.
"""

from typing import List, Optional, Tuple, Dict, Any
from .base import DispatchAlgorithm, DispatchDecision
from agents.elevator_agent import ElevatorAgent, Direction
from agents.passenger_agent import Passenger
from config.settings import UtilityWeights


class UtilityBasedAlgorithm(DispatchAlgorithm):
    """
    Intelligent Utility-Based Multi-Criteria Dispatching Strategy.
    Computes a comprehensive cost function for each elevator agent and selects
    the candidate with the optimal utility score.
    """

    def __init__(self, weights: Optional[UtilityWeights] = None):
        super().__init__(
            name="Utility-Based Intelligent",
            description="Multi-objective AI optimization minimizing wait time, travel time, congestion, and energy."
        )
        self.weights = weights or UtilityWeights()

    def set_weights(self, weights: UtilityWeights):
        self.weights = weights

    def estimate_pickup_time(
        self,
        elev: ElevatorAgent,
        pickup_floor: int,
        req_dir: Direction,
    ) -> Tuple[float, int, float]:
        """
        Estimates the time (in seconds) required for the elevator to reach the pickup floor,
        the number of intermediate stops, and direction compatibility penalty.
        """
        cur = elev.current_floor
        stops = elev.get_all_target_floors()
        speed = max(0.1, elev.speed)
        stop_delay = elev.door_operation_time * 2 + 1.5

        intermediate_stops = 0
        effective_distance = 0.0
        dir_penalty_factor = 0.0

        if elev.direction == Direction.IDLE:
            effective_distance = abs(cur - pickup_floor)
            intermediate_stops = 0
            dir_penalty_factor = 0.2

        elif elev.direction == Direction.UP:
            if pickup_floor >= cur:
                # Moving towards pickup
                effective_distance = pickup_floor - cur
                intermediate_stops = sum(1 for s in stops if cur <= s < pickup_floor)
                if req_dir == Direction.UP:
                    dir_penalty_factor = 0.0  # Perfect on-route match
                else:
                    dir_penalty_factor = 1.2  # Will stop and reverse later
            else:
                # Moving away upwards: must complete ascent then descend
                highest = max(stops) if stops else cur
                effective_distance = (highest - cur) + (highest - pickup_floor)
                intermediate_stops = len(stops)
                dir_penalty_factor = 2.5

        elif elev.direction == Direction.DOWN:
            if pickup_floor <= cur:
                # Moving towards pickup downwards
                effective_distance = cur - pickup_floor
                intermediate_stops = sum(1 for s in stops if pickup_floor < s <= cur)
                if req_dir == Direction.DOWN:
                    dir_penalty_factor = 0.0  # Perfect on-route match
                else:
                    dir_penalty_factor = 1.2
            else:
                # Moving away downwards: must complete descent then ascend
                lowest = min(stops) if stops else cur
                effective_distance = (cur - lowest) + (pickup_floor - lowest)
                intermediate_stops = len(stops)
                dir_penalty_factor = 2.5

        travel_time = effective_distance / speed
        stop_time = intermediate_stops * stop_delay
        total_time = travel_time + stop_time

        return total_time, intermediate_stops, dir_penalty_factor

    def select_elevator(
        self,
        request: Passenger,
        elevators: List[ElevatorAgent],
        num_floors: int,
    ) -> Tuple[Optional[int], Optional[DispatchDecision]]:
        if not elevators:
            return None, None

        w = self.weights
        req_floor = request.pickup_floor
        req_dest = request.destination_floor
        req_dir = request.direction
        is_prio = request.is_priority

        best_elevator_id: Optional[int] = None
        min_cost = float("inf")
        best_breakdown: Dict[str, Any] = {}
        all_evals: List[Dict[str, Any]] = []

        for elev in elevators:
            # 1. Pickup Time Estimation
            est_pickup_sec, inter_stops, dir_factor = self.estimate_pickup_time(
                elev, req_floor, req_dir
            )

            # 2. Waiting Time Component
            cur_wait_sec = max(0.0, request.wait_time(0.0))  # baseline
            total_est_wait = cur_wait_sec + est_pickup_sec

            # 3. Load Factor & Congestion
            effective_passengers = elev.passenger_count + len(elev.assigned_pickups)
            load_factor = effective_passengers / max(1, elev.capacity)
            capacity_overload = 100.0 if elev.is_full else (25.0 if elev.remaining_capacity <= 1 else 0.0)

            # 4. In-Transit Journey Time
            direct_dist = abs(req_dest - req_floor)
            est_journey_sec = direct_dist / max(0.1, elev.speed)

            # 5. Existing Stops Count
            existing_stops_count = len(elev.get_all_target_floors())

            # 6. Energy Impact
            # Energy cost is correlated with extra distance required by the assignment
            extra_dist = abs(elev.current_floor - req_floor)

            # 7. Priority Handling
            priority_bonus = 20.0 if is_prio else 0.0

            # Compute weighted terms
            cost_pickup = w.pickup_time_weight * est_pickup_sec
            cost_wait = w.wait_time_weight * (total_est_wait * 0.5)
            cost_load = w.load_weight * (load_factor * 15.0) + capacity_overload
            cost_dir = w.direction_penalty_weight * (dir_factor * 10.0)
            cost_journey = w.journey_time_weight * (est_journey_sec * 0.4)
            cost_stops = w.existing_stops_weight * (existing_stops_count * 2.5)
            cost_energy = w.energy_weight * (extra_dist * 1.2)
            cost_priority = - (w.priority_weight * priority_bonus)

            total_cost = (
                cost_pickup
                + cost_wait
                + cost_load
                + cost_dir
                + cost_journey
                + cost_stops
                + cost_energy
                + cost_priority
            )

            eval_info = {
                "elevator_id": elev.elevator_id,
                "current_floor": round(elev.current_floor, 1),
                "direction": elev.direction.label,
                "load": f"{elev.passenger_count}/{elev.capacity}",
                "est_pickup_sec": round(est_pickup_sec, 1),
                "cost_pickup": round(cost_pickup, 2),
                "cost_wait": round(cost_wait, 2),
                "cost_load": round(cost_load, 2),
                "cost_dir": round(cost_dir, 2),
                "cost_journey": round(cost_journey, 2),
                "cost_stops": round(cost_stops, 2),
                "cost_energy": round(cost_energy, 2),
                "priority_bonus": round(cost_priority, 2),
                "total_cost": round(total_cost, 2),
            }
            all_evals.append(eval_info)

            if total_cost < min_cost:
                min_cost = total_cost
                best_elevator_id = elev.elevator_id
                best_breakdown = eval_info

        explanation = (
            f"Utility-Based AI selected Elevator #{best_elevator_id} with optimal utility score {min_cost:.2f}. "
            f"(Est. pickup: {best_breakdown.get('est_pickup_sec')}s, "
            f"Load: {best_breakdown.get('load')}, "
            f"Floor: {best_breakdown.get('current_floor')}, "
            f"Dir: {best_breakdown.get('direction')}"
            f"{', VIP Priority Urgency Applied' if is_prio else ''})."
        )

        decision = DispatchDecision(
            passenger_id=request.id,
            elevator_id=best_elevator_id if best_elevator_id is not None else -1,
            algorithm_name=self.name,
            score=min_cost,
            breakdown={"selected": best_breakdown, "candidates": all_evals},
            explanation=explanation,
        )
        return best_elevator_id, decision
