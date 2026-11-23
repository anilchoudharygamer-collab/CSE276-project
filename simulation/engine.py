"""
Discrete-Event Simulation Engine.
Coordinates elevators, passengers, central dispatch agent, traffic generator,
demand prediction, and metric tracking across simulation clock ticks.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
import numpy as np
from agents.elevator_agent import ElevatorAgent
from agents.passenger_agent import Passenger, PassengerStatus
from agents.dispatch_agent import DispatchAgent
from config.settings import SimulationConfig
from .building import Building
from .traffic_generator import TrafficGenerator
from .demand_prediction import DemandPredictor


class SimulationState(str, Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class SimulationEngine:
    """
    Core Discrete-Event Simulation Engine for Elevator Dispatching.
    Provides deterministic stepping, scenario injection, and real-time state introspection.
    """

    def __init__(
        self,
        config: Optional[SimulationConfig] = None,
        dispatch_agent: Optional[DispatchAgent] = None,
    ):
        self.config = config or SimulationConfig()
        self.building = Building(self.config)
        self.dispatch_agent = dispatch_agent or DispatchAgent()
        self.traffic_generator = TrafficGenerator(self.config)
        self.demand_predictor = DemandPredictor(self.config)

        self.current_time: float = 0.0
        self.state: SimulationState = SimulationState.STOPPED

        # Passenger collection
        self.all_passengers: List[Passenger] = []
        self.completed_passengers: List[Passenger] = []
        self.rejected_passengers: List[Passenger] = []

        # Time-series telemetry snapshots for charts
        self.history_snapshots: List[Dict[str, Any]] = []
        self.last_snapshot_time: float = 0.0
        self.snapshot_interval: float = 2.0  # seconds between recorded telemetry points

        # Simulation Replay buffer (detailed state for visual scrubbing)
        self.replay_buffer: List[Dict[str, Any]] = []
        self.max_replay_snapshots: int = 150

        # Floor-wise 2D Demand Matrix: O x D
        self.demand_matrix: np.ndarray = np.zeros(
            (self.config.num_floors, self.config.num_floors), dtype=np.int32
        )

    def reset(self, new_seed: Optional[int] = None):
        """Resets the simulation completely, optionally updating the random seed."""
        if new_seed is not None:
            self.config.random_seed = new_seed

        self.current_time = 0.0
        self.state = SimulationState.STOPPED
        self.all_passengers.clear()
        self.completed_passengers.clear()
        self.rejected_passengers.clear()
        self.history_snapshots.clear()
        self.replay_buffer.clear()
        self.last_snapshot_time = 0.0
        self.demand_matrix = np.zeros(
            (self.config.num_floors, self.config.num_floors), dtype=np.int32
        )

        self.building = Building(self.config)
        self.traffic_generator.reset(self.config.random_seed)
        self.demand_predictor = DemandPredictor(self.config)
        self.dispatch_agent.unassigned_queue.clear()
        self.dispatch_agent.decision_history.clear()
        self.dispatch_agent.total_dispatches = 0

    def start(self):
        self.state = SimulationState.RUNNING

    def pause(self):
        self.state = SimulationState.PAUSED

    def resume(self):
        self.state = SimulationState.RUNNING

    def trigger_emergency(self):
        """Activates system-wide emergency evacuation protocol."""
        self.config.emergency_mode = True
        for elev in self.building.elevators:
            elev.trigger_emergency(self.config.safe_evacuation_floor)

    def clear_emergency(self):
        """Deactivates emergency mode and returns elevators to normal service."""
        self.config.emergency_mode = False
        for elev in self.building.elevators:
            elev.clear_emergency()

    def inject_manual_passenger(
        self,
        pickup_floor: int,
        destination_floor: int,
        is_priority: bool = False,
    ) -> Passenger:
        """Injects a custom passenger request immediately into the running simulation."""
        p = self.traffic_generator.generate_single_request(
            current_time=self.current_time,
            pickup_floor=pickup_floor,
            destination_floor=destination_floor,
            is_priority=is_priority,
        )
        self.all_passengers.append(p)
        self.demand_matrix[pickup_floor, destination_floor] += 1
        self.building.add_passenger(p)
        self.demand_predictor.record_request(p, self.current_time)

        # Dispatch immediately
        self.dispatch_agent.dispatch_request(
            request=p,
            elevators=self.building.elevators,
            num_floors=self.config.num_floors,
        )
        return p

    def step(self, dt: Optional[float] = None):
        """
        Executes a single simulation tick of duration `dt` seconds.
        """
        delta = dt if dt is not None else self.config.time_step
        if delta <= 0:
            return

        # 1. Generate stochastic passenger arrivals for this tick
        if not self.config.emergency_mode:
            new_arrivals = self.traffic_generator.generate_passengers(self.current_time, delta)
            for p in new_arrivals:
                self.all_passengers.append(p)
                self.building.add_passenger(p)
                self.demand_predictor.record_request(p, self.current_time)
                if 0 <= p.pickup_floor < self.config.num_floors and 0 <= p.destination_floor < self.config.num_floors:
                    self.demand_matrix[p.pickup_floor, p.destination_floor] += 1

            # Dispatch batch of calls intelligently
            self.dispatch_agent.dispatch_batch(
                requests=new_arrivals,
                elevators=self.building.elevators,
                num_floors=self.config.num_floors,
            )

            # Retry any previously queued unassigned requests
            self.dispatch_agent.retry_unassigned(self.building.elevators, self.config.num_floors)

        # 2. Advance all elevator agents
        for elev in self.building.elevators:
            boarded, alighted = elev.step(delta, self.current_time)

            # Update building floor queues for boarded passengers
            for p in boarded:
                self.building.remove_passenger(p)

            # Move alighted passengers to completed list
            for p in alighted:
                if p not in self.completed_passengers:
                    self.completed_passengers.append(p)

        # 3. Intelligent Demand Prediction & Repositioning
        if self.config.enable_demand_prediction:
            self.demand_predictor.evaluate_predictive_repositioning(
                self.building.elevators, self.current_time
            )

        # 4. Advance simulation clock
        self.current_time += delta

        # 5. Capture periodic telemetry snapshot for Plotly visualization
        if self.current_time - self.last_snapshot_time >= self.snapshot_interval:
            self._record_snapshot()
            self.last_snapshot_time = self.current_time

    def run_steps(self, steps: int, dt: Optional[float] = None):
        """Runs multiple discrete ticks in succession."""
        for _ in range(steps):
            self.step(dt)

    def _record_snapshot(self):
        """Captures aggregate telemetry at current simulation time."""
        total_waiting = self.building.get_total_waiting_passengers()
        served_count = len(self.completed_passengers)
        in_transit_count = sum(e.passenger_count for e in self.building.elevators)

        # Current average wait time
        waits = [p.wait_time(self.current_time) for p in self.all_passengers if p.status != PassengerStatus.REJECTED]
        avg_wait = sum(waits) / max(1, len(waits))

        # Elevator utilization and energy
        total_energy = sum(e.total_energy_kwh for e in self.building.elevators)
        moving_cars = sum(1 for e in self.building.elevators if e.direction != e.direction.IDLE)
        utilization = (moving_cars / max(1, len(self.building.elevators))) * 100.0

        snapshot = {
            "time": round(self.current_time, 1),
            "total_waiting": total_waiting,
            "total_served": served_count,
            "total_in_transit": in_transit_count,
            "avg_wait_time": round(avg_wait, 2),
            "total_energy_kwh": round(total_energy, 4),
            "active_elevators_pct": round(utilization, 1),
        }
        self.history_snapshots.append(snapshot)
        # Cap snapshot history length
        if len(self.history_snapshots) > 1000:
            self.history_snapshots = self.history_snapshots[-800:]

        # Record replay state snapshot
        replay_state = {
            "time": round(self.current_time, 1),
            "elevators": [e.to_dict() for e in self.building.elevators],
            "total_waiting": total_waiting,
            "total_served": served_count,
            "emergency_mode": self.config.emergency_mode,
        }
        self.replay_buffer.append(replay_state)
        if len(self.replay_buffer) > self.max_replay_snapshots:
            self.replay_buffer.pop(0)

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calculates instantaneous and cumulative simulation performance metrics."""
        waits = [p.wait_time(self.current_time) for p in self.all_passengers]
        completed_journeys = [
            p.total_journey_time(self.current_time)
            for p in self.completed_passengers
        ]

        avg_wait = (sum(waits) / len(waits)) if waits else 0.0
        max_wait = max(waits) if waits else 0.0
        avg_journey = (sum(completed_journeys) / len(completed_journeys)) if completed_journeys else 0.0

        total_distance_floors = sum(e.total_distance_floors for e in self.building.elevators)
        total_distance_meters = sum(e.total_distance_meters for e in self.building.elevators)
        total_energy_kwh = sum(e.total_energy_kwh for e in self.building.elevators)
        total_door_cycles = sum(e.door_cycles for e in self.building.elevators)

        total_moving_time = sum(e.moving_time for e in self.building.elevators)
        total_elev_time = max(0.1, self.current_time * len(self.building.elevators))
        avg_utilization_pct = (total_moving_time / total_elev_time) * 100.0

        return {
            "current_time_sec": round(self.current_time, 1),
            "total_generated": len(self.all_passengers),
            "total_served": len(self.completed_passengers),
            "total_waiting": self.building.get_total_waiting_passengers(),
            "total_in_transit": sum(e.passenger_count for e in self.building.elevators),
            "avg_wait_time_sec": round(avg_wait, 2),
            "max_wait_time_sec": round(max_wait, 2),
            "avg_journey_time_sec": round(avg_journey, 2),
            "avg_utilization_pct": round(min(100.0, avg_utilization_pct), 1),
            "total_distance_floors": round(total_distance_floors, 1),
            "total_distance_meters": round(total_distance_meters, 1),
            "total_energy_kwh": round(total_energy_kwh, 4),
            "total_door_cycles": total_door_cycles,
            "rejected_requests": len(self.rejected_passengers),
            "emergency_mode": self.config.emergency_mode,
            "algorithm_name": self.dispatch_agent.algorithm.name,
        }
