"""
Elevator Agent module.
Autonomous elevator agent handling kinematics, door state machine,
passenger boarding/alighting, capacity limits, and energy consumption telemetry.
"""

from enum import Enum
from typing import List, Set, Optional, Dict, Any, Tuple
from .passenger_agent import Passenger, PassengerStatus, Direction


class DoorState(str, Enum):
    CLOSED = "CLOSED"
    OPENING = "OPENING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"


class OperationalStatus(str, Enum):
    NORMAL = "NORMAL"
    OVERLOAD = "OVERLOAD"
    MAINTENANCE = "MAINTENANCE"
    EMERGENCY = "EMERGENCY"


class ElevatorAgent:
    """
    Autonomous Elevator Agent operating in a multi-elevator group.
    Maintains autonomous local schedule, door state machine, passenger cargo,
    and telemetry metrics.
    """

    def __init__(
        self,
        elevator_id: int,
        capacity: int = 8,
        speed: float = 1.0,               # Floors per second
        door_operation_time: float = 2.0, # Seconds to open or close doors
        passenger_transfer_time: float = 0.8,
        initial_floor: float = 0.0,
        floor_height_meters: float = 3.5,
        motor_power_moving_kw: float = 15.0,
        motor_power_idle_kw: float = 0.35,
        door_cycle_kwh: float = 0.0035,
    ):
        self.elevator_id = elevator_id
        self.capacity = capacity
        self.speed = speed
        self.door_operation_time = door_operation_time
        self.passenger_transfer_time = passenger_transfer_time
        self.current_floor: float = float(initial_floor)
        self.floor_height_meters = floor_height_meters
        self.motor_power_moving_kw = motor_power_moving_kw
        self.motor_power_idle_kw = motor_power_idle_kw
        self.door_cycle_kwh = door_cycle_kwh

        # Operational states
        self.direction: Direction = Direction.IDLE
        self.door_state: DoorState = DoorState.CLOSED
        self.door_timer: float = 0.0
        self.operational_status: OperationalStatus = OperationalStatus.NORMAL

        # Cargo & Stop Queues
        self.passengers: List[Passenger] = []
        self.assigned_pickups: List[Passenger] = []
        self.target_floor: Optional[int] = None
        self.next_destination: Optional[int] = None

        # Predictive Parking indicator
        self.is_repositioning: bool = False
        self.idle_duration: float = 0.0

        # Safety & Emergency state
        self.is_emergency: bool = False
        self.emergency_target_floor: int = 0

        # Telemetry & Metrics
        self.total_distance_floors: float = 0.0
        self.total_distance_meters: float = 0.0
        self.total_passengers_served: int = 0
        self.door_cycles: int = 0
        self.total_energy_kwh: float = 0.0
        self.moving_time: float = 0.0
        self.idle_time: float = 0.0
        self.door_time: float = 0.0

    @property
    def passenger_count(self) -> int:
        return len(self.passengers)

    @property
    def remaining_capacity(self) -> int:
        return max(0, self.capacity - len(self.passengers))

    @property
    def is_full(self) -> bool:
        return len(self.passengers) >= self.capacity

    @property
    def load_factor(self) -> float:
        return len(self.passengers) / max(1, self.capacity)

    @property
    def rounded_floor(self) -> int:
        return int(round(self.current_floor))

    @property
    def pickup_floors_str(self) -> str:
        floors = sorted(list({p.pickup_floor for p in self.assigned_pickups}))
        return ", ".join(f"F{f}" for f in floors) if floors else "None"

    @property
    def dropoff_floors_str(self) -> str:
        floors = sorted(list({p.destination_floor for p in self.passengers}))
        return ", ".join(f"F{f}" for f in floors) if floors else "None"

    def trigger_emergency(self, safe_floor: int = 0):
        """Activates emergency evacuation protocol for this elevator."""
        self.is_emergency = True
        self.emergency_target_floor = safe_floor
        self.operational_status = OperationalStatus.EMERGENCY
        self.assigned_pickups.clear()
        self.target_floor = safe_floor
        if safe_floor > self.rounded_floor:
            self.direction = Direction.UP
        elif safe_floor < self.rounded_floor:
            self.direction = Direction.DOWN
        else:
            self.direction = Direction.IDLE
            self.door_state = DoorState.OPEN
            self.door_timer = 9999.0

    def clear_emergency(self):
        """Clears emergency mode and restores normal operation."""
        self.is_emergency = False
        self.operational_status = OperationalStatus.NORMAL
        self.door_timer = 0.0
        self.door_state = DoorState.CLOSING
        self._update_target()

    def get_all_target_floors(self) -> Set[int]:
        """All scheduled stops: drop-offs for onboard passengers and assigned pickup floors."""
        stops = {p.destination_floor for p in self.passengers}
        stops.update({p.pickup_floor for p in self.assigned_pickups})
        if self.is_repositioning and self.target_floor is not None:
            stops.add(self.target_floor)
        return stops

    def assign_pickup(self, passenger: Passenger) -> bool:
        """Assigns a passenger pickup to this elevator agent."""
        if self.is_emergency:
            return False
        if passenger not in self.assigned_pickups:
            self.assigned_pickups.append(passenger)
            passenger.assigned_elevator_id = self.elevator_id
            self.is_repositioning = False
            self._update_target()
            return True
        return False

    def reposition_to(self, floor: int):
        """Dispatches an idle elevator towards a high-demand floor for predictive staging."""
        if self.direction == Direction.IDLE and not self.passengers and not self.assigned_pickups:
            self.target_floor = floor
            self.is_repositioning = True
            if floor > self.rounded_floor:
                self.direction = Direction.UP
            elif floor < self.rounded_floor:
                self.direction = Direction.DOWN
            else:
                self.direction = Direction.IDLE
                self.is_repositioning = False

    def _update_target(self):
        """Computes the current immediate target floor and next direction."""
        cur_int = self.rounded_floor
        dropoffs = {p.destination_floor for p in self.passengers}

        # If car is full or doors are closed at cur_int with onboard passengers,
        # prioritize delivering onboard passengers
        if self.is_full:
            pickups = {p.pickup_floor for p in self.assigned_pickups if p.pickup_floor != cur_int}
        else:
            pickups = {p.pickup_floor for p in self.assigned_pickups}

        all_stops = dropoffs.union(pickups)
        if self.is_repositioning and self.target_floor is not None:
            all_stops.add(self.target_floor)

        if not all_stops:
            self.target_floor = None
            self.next_destination = None
            self.direction = Direction.IDLE
            self.is_repositioning = False
            return

        # 1. If currently moving UP
        if self.direction == Direction.UP:
            above = [f for f in all_stops if f > cur_int]
            if above:
                self.target_floor = min(above)
                remaining = [f for f in all_stops if f > self.target_floor]
                self.next_destination = min(remaining) if remaining else None
            else:
                # Reverse to DOWN
                below = [f for f in all_stops if f < cur_int]
                if below:
                    self.direction = Direction.DOWN
                    self.target_floor = max(below)
                    remaining = [f for f in all_stops if f < self.target_floor]
                    self.next_destination = max(remaining) if remaining else None
                elif cur_int in all_stops and not self.is_full:
                    self.target_floor = cur_int
                else:
                    self.target_floor = None
                    self.direction = Direction.IDLE

        # 2. If currently moving DOWN
        elif self.direction == Direction.DOWN:
            below = [f for f in all_stops if f < cur_int]
            if below:
                self.target_floor = max(below)
                remaining = [f for f in all_stops if f < self.target_floor]
                self.next_destination = max(remaining) if remaining else None
            else:
                # Reverse to UP
                above = [f for f in all_stops if f > cur_int]
                if above:
                    self.direction = Direction.UP
                    self.target_floor = min(above)
                    remaining = [f for f in all_stops if f > self.target_floor]
                    self.next_destination = min(remaining) if remaining else None
                elif cur_int in all_stops and not self.is_full:
                    self.target_floor = cur_int
                else:
                    self.target_floor = None
                    self.direction = Direction.IDLE

        # 3. If IDLE
        else:
            if dropoffs:
                # Onboard passengers take precedence
                closest_dropoff = min(dropoffs, key=lambda f: abs(f - self.current_floor))
                self.target_floor = closest_dropoff
                if closest_dropoff > self.current_floor:
                    self.direction = Direction.UP
                elif closest_dropoff < self.current_floor:
                    self.direction = Direction.DOWN
                else:
                    self.direction = Direction.IDLE
            elif cur_int in pickups and not self.is_full and self.door_state == DoorState.CLOSED:
                # Can pick up at current floor
                self.target_floor = cur_int
            else:
                other_stops = [f for f in all_stops if f != cur_int]
                if other_stops:
                    closest = min(other_stops, key=lambda f: abs(f - self.current_floor))
                    self.target_floor = closest
                    if closest > self.current_floor:
                        self.direction = Direction.UP
                    elif closest < self.current_floor:
                        self.direction = Direction.DOWN
                    else:
                        self.direction = Direction.IDLE
                elif cur_int in all_stops and not self.is_full:
                    self.target_floor = cur_int
                else:
                    self.target_floor = None
                    self.direction = Direction.IDLE

    def step(self, dt: float, current_sim_time: float) -> Tuple[List[Passenger], List[Passenger]]:
        """
        Executes one simulation step of delta time `dt`.
        Returns:
            Tuple of (boarded_passengers, alighted_passengers)
        """
        boarded_this_step: List[Passenger] = []
        alighted_this_step: List[Passenger] = []

        # Update power baseline for idle/operating
        idle_kw = self.motor_power_idle_kw * (dt / 3600.0)
        self.total_energy_kwh += idle_kw

        # Emergency Evacuation Protocol Handling
        if self.is_emergency:
            safe_f = self.emergency_target_floor
            if abs(self.current_floor - safe_f) < 1e-4:
                # Arrived at safe floor
                self.current_floor = float(safe_f)
                self.direction = Direction.IDLE
                self.door_state = DoorState.OPEN
                # Evacuate all onboard passengers
                for p in self.passengers:
                    p.alight_time = current_sim_time
                    p.status = PassengerStatus.COMPLETED
                    alighted_this_step.append(p)
                    self.total_passengers_served += 1
                self.passengers.clear()
                self.door_timer = 9999.0  # Keep doors safely open during emergency
                return boarded_this_step, alighted_this_step
            else:
                # Move towards safe floor
                self.moving_time += dt
                move_dist = self.speed * dt
                self.total_energy_kwh += self.motor_power_moving_kw * (dt / 3600.0)
                if safe_f > self.current_floor:
                    self.direction = Direction.UP
                    self.current_floor = min(float(safe_f), self.current_floor + move_dist)
                else:
                    self.direction = Direction.DOWN
                    self.current_floor = max(float(safe_f), self.current_floor - move_dist)
                return boarded_this_step, alighted_this_step

        # 1. Door state machine
        if self.door_state == DoorState.OPENING:
            self.door_timer -= dt
            self.door_time += dt
            if self.door_timer <= 0:
                self.door_state = DoorState.OPEN
                cur_floor = self.rounded_floor

                # A. Alight passengers destined for this floor
                still_onboard: List[Passenger] = []
                for p in self.passengers:
                    if p.destination_floor == cur_floor:
                        p.alight_time = current_sim_time
                        p.status = PassengerStatus.COMPLETED
                        alighted_this_step.append(p)
                        self.total_passengers_served += 1
                    else:
                        still_onboard.append(p)
                self.passengers = still_onboard

                # B. Board assigned passengers at this floor up to capacity
                remaining_pickups: List[Passenger] = []
                for p in self.assigned_pickups:
                    if p.pickup_floor == cur_floor:
                        if len(self.passengers) < self.capacity:
                            p.board_time = current_sim_time
                            p.status = PassengerStatus.IN_TRANSIT
                            self.passengers.append(p)
                            boarded_this_step.append(p)
                        else:
                            remaining_pickups.append(p)
                    else:
                        remaining_pickups.append(p)
                self.assigned_pickups = remaining_pickups

                # Duration doors remain open: proportional to passenger flow
                transfers = len(boarded_this_step) + len(alighted_this_step)
                self.door_timer = max(1.5, transfers * self.passenger_transfer_time)
            return boarded_this_step, alighted_this_step

        elif self.door_state == DoorState.OPEN:
            self.door_timer -= dt
            self.door_time += dt
            if self.door_timer <= 0:
                self.door_state = DoorState.CLOSING
                self.door_timer = self.door_operation_time
            return boarded_this_step, alighted_this_step

        elif self.door_state == DoorState.CLOSING:
            self.door_timer -= dt
            self.door_time += dt
            if self.door_timer <= 0:
                self.door_state = DoorState.CLOSED
                self.door_cycles += 1
                self.total_energy_kwh += self.door_cycle_kwh
                if self.is_repositioning and self.target_floor == self.rounded_floor:
                    self.is_repositioning = False
                self._update_target()
            return boarded_this_step, alighted_this_step

        # 2. Car is CLOSED: Moving or Idle
        self._update_target()

        if self.target_floor is None:
            self.direction = Direction.IDLE
            self.idle_time += dt
            self.idle_duration += dt
            return boarded_this_step, alighted_this_step

        self.idle_duration = 0.0

        # Check if already at target floor
        if abs(self.current_floor - self.target_floor) < 1e-4:
            self.current_floor = float(self.target_floor)
            cur_int = self.rounded_floor
            has_dropoff = any(p.destination_floor == cur_int for p in self.passengers)
            has_pickup = (not self.is_full) and any(p.pickup_floor == cur_int for p in self.assigned_pickups)

            if has_dropoff or has_pickup:
                self.door_state = DoorState.OPENING
                self.door_timer = self.door_operation_time
            else:
                if self.is_repositioning:
                    self.is_repositioning = False
                    self.direction = Direction.IDLE
                    self.target_floor = None
                else:
                    self._update_target()
            return boarded_this_step, alighted_this_step

        # Move towards target floor
        self.moving_time += dt
        move_dist = self.speed * dt
        energy_active = self.motor_power_moving_kw * (dt / 3600.0)
        self.total_energy_kwh += energy_active

        if self.target_floor > self.current_floor:
            self.direction = Direction.UP
            if self.current_floor + move_dist >= self.target_floor:
                travelled = self.target_floor - self.current_floor
                self.current_floor = float(self.target_floor)
            else:
                travelled = move_dist
                self.current_floor += move_dist
        else:
            self.direction = Direction.DOWN
            if self.current_floor - move_dist <= self.target_floor:
                travelled = self.current_floor - self.target_floor
                self.current_floor = float(self.target_floor)
            else:
                travelled = move_dist
                self.current_floor -= move_dist

        self.total_distance_floors += travelled
        self.total_distance_meters += travelled * self.floor_height_meters

        # Check if reached target floor after moving
        if abs(self.current_floor - self.target_floor) < 1e-4:
            self.current_floor = float(self.target_floor)
            cur_int = self.rounded_floor
            has_dropoff = any(p.destination_floor == cur_int for p in self.passengers)
            has_pickup = (not self.is_full) and any(p.pickup_floor == cur_int for p in self.assigned_pickups)
            if has_dropoff or has_pickup:
                self.door_state = DoorState.OPENING
                self.door_timer = self.door_operation_time
            else:
                if self.is_repositioning:
                    self.is_repositioning = False
                    self.direction = Direction.IDLE
                    self.target_floor = None
                else:
                    self._update_target()

        return boarded_this_step, alighted_this_step

    def to_dict(self) -> Dict[str, Any]:
        """Serializes current elevator state for visualization and dashboard telemetry."""
        return {
            "elevator_id": self.elevator_id,
            "current_floor": round(self.current_floor, 2),
            "rounded_floor": self.rounded_floor,
            "direction": self.direction.label,
            "direction_symbol": self.direction.symbol,
            "door_state": self.door_state.value,
            "passenger_count": self.passenger_count,
            "capacity": self.capacity,
            "remaining_capacity": self.remaining_capacity,
            "load_factor": round(self.load_factor, 2),
            "is_full": self.is_full,
            "target_floor": self.target_floor,
            "next_destination": self.next_destination,
            "operational_status": self.operational_status.value,
            "is_emergency": self.is_emergency,
            "pickup_floors_str": self.pickup_floors_str,
            "dropoff_floors_str": self.dropoff_floors_str,
            "is_repositioning": self.is_repositioning,
            "assigned_pickups_count": len(self.assigned_pickups),
            "all_stops": sorted(list(self.get_all_target_floors())),
            "total_distance_floors": round(self.total_distance_floors, 1),
            "total_distance_meters": round(self.total_distance_meters, 1),
            "total_passengers_served": self.total_passengers_served,
            "total_energy_kwh": round(self.total_energy_kwh, 4),
            "moving_time": round(self.moving_time, 1),
            "idle_time": round(self.idle_time, 1),
        }
