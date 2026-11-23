"""
Performance Metrics computation module.
Calculates statistical summaries for passenger wait times, journey times,
elevator utilization, kinematics, and energy efficiency.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from agents.passenger_agent import Passenger, PassengerStatus
from agents.elevator_agent import ElevatorAgent


class SimulationMetrics:
    """Computes comprehensive Key Performance Indicators (KPIs) for the elevator system."""

    @staticmethod
    def calculate_passenger_metrics(
        all_passengers: List[Passenger],
        completed_passengers: List[Passenger],
        current_time: float,
    ) -> Dict[str, Any]:
        total_pax = len(all_passengers)
        completed_count = len(completed_passengers)
        waiting_count = sum(1 for p in all_passengers if p.status == PassengerStatus.WAITING)
        in_transit_count = sum(1 for p in all_passengers if p.status == PassengerStatus.IN_TRANSIT)

        if not all_passengers:
            return {
                "total_passengers": 0,
                "completed": 0,
                "waiting": 0,
                "in_transit": 0,
                "avg_wait_sec": 0.0,
                "median_wait_sec": 0.0,
                "p95_wait_sec": 0.0,
                "max_wait_sec": 0.0,
                "std_wait_sec": 0.0,
                "avg_journey_sec": 0.0,
                "max_journey_sec": 0.0,
                "priority_count": 0,
                "priority_avg_wait_sec": 0.0,
            }

        wait_times = [p.wait_time(current_time) for p in all_passengers]
        completed_journeys = [p.total_journey_time(current_time) for p in completed_passengers]
        prio_waits = [p.wait_time(current_time) for p in all_passengers if p.is_priority]

        return {
            "total_passengers": total_pax,
            "completed": completed_count,
            "waiting": waiting_count,
            "in_transit": in_transit_count,
            "avg_wait_sec": round(float(np.mean(wait_times)), 2),
            "median_wait_sec": round(float(np.median(wait_times)), 2),
            "p95_wait_sec": round(float(np.percentile(wait_times, 95)), 2) if wait_times else 0.0,
            "max_wait_sec": round(float(np.max(wait_times)), 2),
            "std_wait_sec": round(float(np.std(wait_times)), 2),
            "avg_journey_sec": round(float(np.mean(completed_journeys)), 2) if completed_journeys else 0.0,
            "max_journey_sec": round(float(np.max(completed_journeys)), 2) if completed_journeys else 0.0,
            "priority_count": len(prio_waits),
            "priority_avg_wait_sec": round(float(np.mean(prio_waits)), 2) if prio_waits else 0.0,
        }

    @staticmethod
    def calculate_elevator_metrics(
        elevators: List[ElevatorAgent],
        sim_duration_sec: float,
    ) -> Dict[str, Any]:
        if not elevators:
            return {}

        total_distance_floors = sum(e.total_distance_floors for e in elevators)
        total_distance_meters = sum(e.total_distance_meters for e in elevators)
        total_energy_kwh = sum(e.total_energy_kwh for e in elevators)
        total_door_cycles = sum(e.door_cycles for e in elevators)
        total_served = sum(e.total_passengers_served for e in elevators)

        total_moving_time = sum(e.moving_time for e in elevators)
        total_idle_time = sum(e.idle_time for e in elevators)
        total_capacity_time = max(0.1, sim_duration_sec * len(elevators))

        avg_utilization_pct = min(100.0, (total_moving_time / total_capacity_time) * 100.0)

        # Average energy per passenger
        kwh_per_pax = (total_energy_kwh / total_served) if total_served > 0 else 0.0

        return {
            "total_elevators": len(elevators),
            "total_distance_floors": round(total_distance_floors, 1),
            "total_distance_meters": round(total_distance_meters, 1),
            "total_energy_kwh": round(total_energy_kwh, 4),
            "kwh_per_passenger": round(kwh_per_pax, 4),
            "total_door_cycles": total_door_cycles,
            "total_passengers_served": total_served,
            "avg_utilization_pct": round(avg_utilization_pct, 1),
            "total_moving_sec": round(total_moving_time, 1),
            "total_idle_sec": round(total_idle_time, 1),
        }
