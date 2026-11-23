"""
Traffic Pattern Generator.
Generates realistic passenger arrival streams across standard traffic scenarios:
- Morning Up-Peak
- Lunch Two-Way Traffic
- Evening Down-Peak
- Custom User-Defined Traffic
Deterministic and seed-controllable for fair algorithmic benchmarking.
"""

from typing import List, Optional, Tuple
import numpy as np
from config.settings import TrafficScenarioType, SimulationConfig
from agents.passenger_agent import Passenger, PassengerStatus


class TrafficGenerator:
    """
    Simulates stochastic passenger arrivals in a multi-floor building.
    Uses Poisson arrival processes and weighted floor distributions.
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = np.random.default_rng(config.random_seed)
        self.passenger_counter = 0

    def reset(self, seed: Optional[int] = None):
        """Resets the generator state and optionally re-seeds RNG."""
        if seed is not None:
            self.config.random_seed = seed
        self.rng = np.random.default_rng(self.config.random_seed)
        self.passenger_counter = 0

    def set_scenario(self, scenario: TrafficScenarioType):
        self.config.scenario = scenario

    def _sample_floor_pair(self, scenario: TrafficScenarioType, num_floors: int) -> Tuple[int, int]:
        """Samples a (pickup_floor, destination_floor) pair according to the traffic scenario."""
        floors = np.arange(num_floors)
        upper_floors = np.arange(1, num_floors)

        if scenario == TrafficScenarioType.MORNING_UP_PEAK:
            # 85% arrive at ground floor going up; 15% random inter-floor
            if self.rng.random() < 0.85:
                pickup = 0
                dest = int(self.rng.choice(upper_floors))
            else:
                pickup = int(self.rng.choice(floors))
                choices = [f for f in floors if f != pickup]
                dest = int(self.rng.choice(choices))

        elif scenario == TrafficScenarioType.EVENING_DOWN_PEAK:
            # 85% depart upper floors going down to ground floor; 15% random
            if self.rng.random() < 0.85:
                pickup = int(self.rng.choice(upper_floors))
                dest = 0
            else:
                pickup = int(self.rng.choice(floors))
                choices = [f for f in floors if f != pickup]
                dest = int(self.rng.choice(choices))

        elif scenario == TrafficScenarioType.LUNCH_TWO_WAY:
            # 45% going down to ground/food level (floors 0, 1)
            # 45% returning from ground/food level to upper floors
            # 10% inter-floor
            r = self.rng.random()
            if r < 0.45:
                pickup = int(self.rng.choice(upper_floors))
                dest = int(self.rng.choice([0, 1] if num_floors > 2 else [0]))
            elif r < 0.90:
                pickup = int(self.rng.choice([0, 1] if num_floors > 2 else [0]))
                valid_upper = [f for f in upper_floors if f != pickup]
                dest = int(self.rng.choice(valid_upper))
            else:
                pickup = int(self.rng.choice(floors))
                choices = [f for f in floors if f != pickup]
                dest = int(self.rng.choice(choices))

        else:  # CUSTOM / Uniform Random
            pickup = int(self.rng.choice(floors))
            choices = [f for f in floors if f != pickup]
            dest = int(self.rng.choice(choices))

        return pickup, dest

    def generate_passengers(self, current_time: float, dt: float) -> List[Passenger]:
        """
        Generates passengers arriving in the time window [current_time, current_time + dt].
        Arrival count sampled from Poisson distribution: Poisson(rate * dt).
        """
        lambda_rate = max(0.01, self.config.passenger_arrival_rate)
        expected_arrivals = lambda_rate * dt

        # Sample number of arriving passengers
        num_arrivals = self.rng.poisson(expected_arrivals)
        passengers: List[Passenger] = []

        for _ in range(num_arrivals):
            self.passenger_counter += 1
            pickup, dest = self._sample_floor_pair(self.config.scenario, self.config.num_floors)
            is_priority = (self.rng.random() < self.config.priority_passenger_ratio)

            # Uniform random offset within this tick interval
            time_offset = self.rng.uniform(0.0, dt)
            req_time = current_time + time_offset

            p = Passenger(
                id=f"P-{self.passenger_counter:04d}",
                pickup_floor=pickup,
                destination_floor=dest,
                request_time=req_time,
                is_priority=is_priority,
                status=PassengerStatus.WAITING,
            )
            passengers.append(p)

        return passengers

    def generate_single_request(
        self,
        current_time: float,
        pickup_floor: Optional[int] = None,
        destination_floor: Optional[int] = None,
        is_priority: bool = False,
    ) -> Passenger:
        """Manually injects a single passenger request (for interactive manual testing in UI)."""
        self.passenger_counter += 1
        num_floors = self.config.num_floors

        if pickup_floor is None or destination_floor is None or pickup_floor == destination_floor:
            p_floor, d_floor = self._sample_floor_pair(self.config.scenario, num_floors)
        else:
            p_floor = max(0, min(num_floors - 1, pickup_floor))
            d_floor = max(0, min(num_floors - 1, destination_floor))

        p = Passenger(
            id=f"P-{self.passenger_counter:04d}",
            pickup_floor=p_floor,
            destination_floor=d_floor,
            request_time=current_time,
            is_priority=is_priority,
            status=PassengerStatus.WAITING,
        )
        return p
