"""
Configuration module for the Intelligent Elevator Group Dispatch Agent System.
Defines simulation settings, utility weights, traffic scenario types, and serialization.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, Optional
import json


class TrafficScenarioType(str, Enum):
    MORNING_UP_PEAK = "Morning Up-Peak"
    LUNCH_TWO_WAY = "Lunch Two-Way"
    EVENING_DOWN_PEAK = "Evening Down-Peak"
    CUSTOM = "Custom Traffic"


# Convenient alias for backward-compatibility
TrafficScenario = TrafficScenarioType


class SystemTheme(str, Enum):
    DARK = "dark"
    LIGHT = "light"


@dataclass
class UtilityWeights:
    """Weights for the Utility-Based Intelligent Dispatch scoring function."""
    pickup_time_weight: float = 1.0        # Impact of estimated wait time until pickup
    wait_time_weight: float = 1.2          # Penalty for passenger waiting time accumulation
    load_weight: float = 0.8               # Penalty for elevator congestion/load factor
    direction_penalty_weight: float = 2.5  # Penalty for non-matching or reversing direction
    journey_time_weight: float = 0.8       # Impact of estimated in-transit time to destination
    existing_stops_weight: float = 0.5     # Penalty per already queued stop in car
    priority_weight: float = 3.0           # Bonus/urgency multiplier for VIP/emergency requests
    energy_weight: float = 0.3             # Penalty for unnecessary movement / power draw

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UtilityWeights":
        valid_keys = {k for k in cls.__dataclass_fields__.keys()}
        filtered = {k: float(v) for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class SimulationConfig:
    """Core parameters controlling building, elevator physics, and simulation dynamics."""
    # Building specifications
    num_floors: int = 15
    num_elevators: int = 5
    ground_floor: int = 0
    floor_height_meters: float = 3.5

    # Elevator mechanical parameters
    elevator_capacity: int = 8             # Max passengers per car
    elevator_speed: float = 1.0            # Floors per second
    door_operation_time: float = 2.0       # Seconds for door opening or closing
    passenger_transfer_time: float = 0.8   # Seconds per passenger boarding or alighting

    # Energy modeling parameters
    motor_power_moving_kw: float = 15.0    # Active power consumption during ascent/descent
    motor_power_idle_kw: float = 0.35      # Standby power draw when stationary
    door_cycle_kwh: float = 0.0035         # Energy per open-close cycle

    # Simulation execution parameters
    time_step: float = 1.0                 # Seconds simulated per engine tick
    random_seed: int = 42
    scenario: TrafficScenarioType = TrafficScenarioType.MORNING_UP_PEAK
    passenger_arrival_rate: float = 0.35   # Average passengers generated per second in peak
    priority_passenger_ratio: float = 0.08 # 8% VIP/priority requests

    # Intelligent Demand Prediction parameters
    enable_demand_prediction: bool = True
    demand_history_window: int = 60        # Seconds of history window for Markov/Poisson model
    idle_reposition_threshold_sec: float = 8.0 # Seconds car remains idle before predictive park

    # Safety & Operating Modes
    emergency_mode: bool = False           # Fire/earthquake emergency evacuation protocol
    safe_evacuation_floor: int = 0         # Floor to which all elevators evacuate
    theme: SystemTheme = SystemTheme.DARK  # UI Theme: dark or light

    # Utility algorithm configuration
    utility_weights: UtilityWeights = field(default_factory=UtilityWeights)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scenario"] = self.scenario.value if isinstance(self.scenario, TrafficScenarioType) else str(self.scenario)
        d["theme"] = self.theme.value if isinstance(self.theme, SystemTheme) else str(self.theme)
        d["utility_weights"] = self.utility_weights.to_dict()
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationConfig":
        d = dict(data)
        if "scenario" in d and isinstance(d["scenario"], str):
            try:
                d["scenario"] = TrafficScenarioType(d["scenario"])
            except ValueError:
                d["scenario"] = TrafficScenarioType.MORNING_UP_PEAK
        if "theme" in d and isinstance(d["theme"], str):
            try:
                d["theme"] = SystemTheme(d["theme"])
            except ValueError:
                d["theme"] = SystemTheme.DARK
        if "utility_weights" in d and isinstance(d["utility_weights"], dict):
            d["utility_weights"] = UtilityWeights.from_dict(d["utility_weights"])
        valid_keys = {k for k in cls.__dataclass_fields__.keys()}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def from_json(cls, json_str: str) -> "SimulationConfig":
        return cls.from_dict(json.loads(json_str))
