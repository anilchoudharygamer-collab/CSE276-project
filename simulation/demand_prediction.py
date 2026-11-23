"""
Intelligent Demand Prediction and Predictive Parking Module.
Analyzes rolling historical passenger arrival distributions to forecast floor traffic demand
and autonomously repositions idle elevators to anticipate future passenger calls.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import numpy as np
from agents.elevator_agent import ElevatorAgent, Direction
from agents.passenger_agent import Passenger
from config.settings import SimulationConfig


class DemandPredictor:
    """
    Statistical Demand Prediction Agent.
    Tracks passenger arrival frequency per floor, computes rolling arrival probabilities,
    and manages predictive repositioning of idle elevator units.
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.num_floors = config.num_floors
        # Rolling arrival history: (timestamp, pickup_floor)
        self.arrival_history: deque[Tuple[float, int]] = deque(maxlen=500)
        self.reposition_log: deque[Dict[str, Any]] = deque(maxlen=50)
        self.last_reposition_check_time: float = 0.0

    def record_request(self, passenger: Passenger, current_time: float):
        """Records an incoming passenger request for demand modeling."""
        self.arrival_history.append((current_time, passenger.pickup_floor))

    def get_predicted_demand_distribution(self, current_time: float) -> np.ndarray:
        """
        Computes probability distribution P(floor) of expected passenger pickups
        based on the sliding time window. Falls back to uniform prior if insufficient data.
        """
        window = self.config.demand_history_window
        cutoff = current_time - window

        # Count arrivals in window
        counts = np.zeros(self.num_floors, dtype=np.float64)
        total_recent = 0

        for t, floor in self.arrival_history:
            if t >= cutoff and 0 <= floor < self.num_floors:
                # Give slightly higher weight to more recent arrivals
                recency_weight = 1.0 + (t - cutoff) / max(1.0, window)
                counts[floor] += recency_weight
                total_recent += 1

        # Laplace smoothing prior
        smoothed = counts + 0.1
        probabilities = smoothed / np.sum(smoothed)
        return probabilities

    def evaluate_predictive_repositioning(
        self,
        elevators: List[ElevatorAgent],
        current_time: float,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates whether idle elevators should be repositioned to high-demand floors.
        Runs periodically (e.g. every 5-10 simulation seconds).
        """
        if not self.config.enable_demand_prediction:
            return []

        # Throttle check frequency
        if current_time - self.last_reposition_check_time < 5.0:
            return []
        self.last_reposition_check_time = current_time

        # Identify idle elevators that have remained stationary for threshold
        threshold = self.config.idle_reposition_threshold_sec
        eligible_idle_cars = [
            e for e in elevators
            if e.direction == Direction.IDLE
            and not e.passengers
            and not e.assigned_pickups
            and e.idle_duration >= threshold
        ]

        if not eligible_idle_cars:
            return []

        probs = self.get_predicted_demand_distribution(current_time)
        # Find top demand floors with probability > 15%
        high_demand_indices = np.argsort(probs)[::-1]
        actions_taken: List[Dict[str, Any]] = []

        for target_floor in high_demand_indices:
            floor_prob = float(probs[target_floor])
            if floor_prob < 0.12:
                break  # Demand is too evenly distributed

            # Check if there is already an elevator at or near this floor
            nearby_cars = [
                e for e in elevators
                if abs(e.current_floor - target_floor) <= 1.5
            ]

            if not nearby_cars and eligible_idle_cars:
                # Find the closest idle car to this high-demand floor
                best_car = min(eligible_idle_cars, key=lambda e: abs(e.current_floor - target_floor))
                if abs(best_car.current_floor - target_floor) >= 2.0:
                    best_car.reposition_to(int(target_floor))
                    action_record = {
                        "time": round(current_time, 1),
                        "elevator_id": best_car.elevator_id,
                        "from_floor": best_car.rounded_floor,
                        "to_floor": int(target_floor),
                        "predicted_probability": round(floor_prob * 100, 1),
                        "reason": f"Predicted high pickup demand ({floor_prob*100:.1f}%) at Floor {target_floor}",
                    }
                    self.reposition_log.appendleft(action_record)
                    actions_taken.append(action_record)
                    eligible_idle_cars.remove(best_car)

        return actions_taken

    def get_summary_stats(self, current_time: float) -> Dict[str, Any]:
        """Returns demand prediction metrics for display in the dashboard."""
        probs = self.get_predicted_demand_distribution(current_time)
        top_floor = int(np.argmax(probs))
        top_prob = float(probs[top_floor])

        return {
            "top_demand_floor": top_floor,
            "top_demand_probability": round(top_prob * 100, 1),
            "distribution": [round(float(p) * 100, 1) for p in probs],
            "recent_repositions": list(self.reposition_log)[:5],
            "total_predictive_actions": len(self.reposition_log),
        }
