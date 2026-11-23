"""
Live Building Visualization Component.
Renders an architectural cutaway of the multi-shaft building with support for
both Cyber Dark and Industrial Light themes, live elevator movement, door states,
onboard passengers, assigned pickups, destinations, and VIP queues.
"""

from typing import List, Dict, Any, Optional
from simulation.building import Building
from agents.elevator_agent import ElevatorAgent, DoorState, Direction, OperationalStatus


def render_building_html(
    building: Building,
    current_time: float,
    theme: str = "dark",
    emergency_mode: bool = False,
) -> str:
    """
    Generates a modern, responsive HTML/CSS visualizer for the building simulation.
    Supports both Cyber Dark and Industrial Light themes.
    """
    num_floors = building.config.num_floors
    elevators = building.elevators
    num_elevators = len(elevators)
    is_light = (theme.lower() == "light")

    # Theme CSS variables
    if is_light:
        bg_main = "#F1F5F9"
        bg_card = "#FFFFFF"
        border_card = "#CBD5E1"
        text_primary = "#0F172A"
        text_secondary = "#64748B"
        shaft_bg = "rgba(241, 245, 249, 0.7)"
        shaft_border = "rgba(148, 163, 184, 0.4)"
        cabin_bg = "#FFFFFF"
        cabin_border_default = "#94A3B8"
        row_bg = "rgba(255, 255, 255, 0.9)"
        row_border = "rgba(226, 232, 240, 0.8)"
        row_hover = "rgba(241, 245, 249, 0.9)"
        ground_bg = "rgba(16, 185, 129, 0.12)"
        cable_color = "rgba(100, 116, 139, 0.3)"
    else:
        bg_main = "#0B0F19"
        bg_card = "#111827"
        border_card = "#1F2937"
        text_primary = "#F3F4F6"
        text_secondary = "#9CA3AF"
        shaft_bg = "rgba(15, 23, 42, 0.6)"
        shaft_border = "rgba(75, 85, 99, 0.4)"
        cabin_bg = "#1E293B"
        cabin_border_default = "#38BDF8"
        row_bg = "rgba(17, 24, 39, 0.7)"
        row_border = "rgba(55, 65, 81, 0.4)"
        row_hover = "rgba(30, 41, 59, 0.7)"
        ground_bg = "rgba(16, 185, 129, 0.08)"
        cable_color = "rgba(100, 116, 139, 0.2)"

    # Pre-compute elevator data
    elev_data = []
    for e in elevators:
        # Determine status colors and direction
        if e.is_emergency or e.operational_status == OperationalStatus.EMERGENCY:
            dir_icon = "🚨"
            dir_color = "#EF4444"
            dir_class = "emergency"
            dir_label = "EVACUATE"
        elif e.direction == Direction.UP:
            dir_icon = "▲"
            dir_color = "#00F0FF" if not is_light else "#0284C7"
            dir_class = "moving-up"
            dir_label = "UP"
        elif e.direction == Direction.DOWN:
            dir_icon = "▼"
            dir_color = "#F59E0B"
            dir_class = "moving-down"
            dir_label = "DOWN"
        else:
            dir_icon = "■"
            dir_color = "#9CA3AF"
            dir_class = "idle"
            dir_label = "IDLE"

        # Door state
        if e.door_state == DoorState.OPEN:
            door_label = "OPEN"
            door_color = "#10B981"
            door_css = "door-open"
        elif e.door_state == DoorState.OPENING:
            door_label = "OPENING"
            door_color = "#34D399"
            door_css = "door-moving"
        elif e.door_state == DoorState.CLOSING:
            door_label = "CLOSING"
            door_color = "#F59E0B"
            door_css = "door-moving"
        else:
            door_label = "CLOSED"
            door_color = "#64748B" if is_light else "#4B5563"
            door_css = "door-closed"

        # Load indicator
        load_pct = min(100, int(e.load_factor * 100))
        if load_pct >= 90:
            load_bar_color = "#EF4444"
            status_chip = "FULL"
        elif load_pct >= 60:
            load_bar_color = "#F59E0B"
            status_chip = "BUSY"
        else:
            load_bar_color = "#10B981"
            status_chip = "NORMAL"

        elev_data.append({
            "id": e.elevator_id,
            "floor": e.current_floor,
            "rounded_floor": e.rounded_floor,
            "dir_icon": dir_icon,
            "dir_color": dir_color,
            "dir_class": dir_class,
            "dir_label": dir_label,
            "passengers": e.passenger_count,
            "capacity": e.capacity,
            "load_pct": load_pct,
            "load_bar_color": load_bar_color,
            "status_chip": status_chip,
            "door_label": door_label,
            "door_color": door_color,
            "door_css": door_css,
            "target": e.target_floor if e.target_floor is not None else "-",
            "is_emergency": e.is_emergency,
            "pickups_str": e.pickup_floors_str,
            "dropoffs_str": e.dropoff_floors_str,
        })

    # Floor rows (from top floor down to ground floor 0)
    floor_rows_html = []
    for f_idx in reversed(range(num_floors)):
        floor_obj = building.floors[f_idx]
        is_ground = (f_idx == 0)
        floor_label = "LOBBY (G)" if is_ground else f"F {f_idx:02d}"

        # Waiting queues
        up_waiting = len(floor_obj.up_waiting_queue)
        down_waiting = len(floor_obj.down_waiting_queue)
        has_priority = any(p.is_priority for p in (floor_obj.up_waiting_queue + floor_obj.down_waiting_queue))

        up_badge = f'<span class="badge badge-up">▲ {up_waiting}</span>' if up_waiting > 0 else '<span class="badge badge-muted">▲ 0</span>'
        down_badge = f'<span class="badge badge-down">▼ {down_waiting}</span>' if down_waiting > 0 else '<span class="badge badge-muted">▼ 0</span>'
        prio_badge = '<span class="badge badge-prio">⚡ VIP</span>' if has_priority else ''

        # Shaft cells for this floor
        shaft_cells = []
        for e in elev_data:
            at_this_floor = abs(e["floor"] - f_idx) < 0.5
            if at_this_floor:
                # Elevator Cabin
                cabin_html = f"""
                <div class="cabin {e['dir_class']} {e['door_css']}">
                    <div class="cabin-header">
                        <span class="cabin-title">E{e['id']}</span>
                        <span class="cabin-dir" style="color: {e['dir_color']};">{e['dir_icon']}</span>
                    </div>
                    <div class="cabin-load">
                        <div class="load-bar-bg">
                            <div class="load-bar-fill" style="width: {e['load_pct']}%; background: {e['load_bar_color']};"></div>
                        </div>
                        <span class="load-text">{e['passengers']}/{e['capacity']}</span>
                    </div>
                    <div class="cabin-info-tags">
                        <span class="tag-chip">🎯{e['target']}</span>
                        <span class="tag-chip door-tag" style="color: {e['door_color']};">{e['door_label'][:3]}</span>
                    </div>
                </div>
                """
                shaft_cells.append(f'<div class="shaft-cell occupied">{cabin_html}</div>')
            else:
                # Empty shaft guides
                shaft_cells.append('<div class="shaft-cell"><div class="cable-line"></div></div>')

        shaft_cells_str = "".join(shaft_cells)

        floor_row = f"""
        <div class="floor-row {'ground-floor' if is_ground else ''}">
            <div class="floor-label-cell">
                <span class="floor-num">{floor_label}</span>
            </div>
            <div class="floor-corridor-cell">
                <div class="queue-badges">
                    {up_badge}
                    {down_badge}
                    {prio_badge}
                </div>
            </div>
            {shaft_cells_str}
        </div>
        """
        floor_rows_html.append(floor_row)

    # Shaft Headers
    shaft_headers = []
    for e in elev_data:
        shaft_headers.append(f"""
        <div class="shaft-header">
            <div class="shaft-title">SHAFT {e['id']}</div>
            <div class="shaft-subtitle">Car #{e['id']} ({e['dir_label']})</div>
        </div>
        """)
    shaft_headers_str = "".join(shaft_headers)
    all_floors_str = "".join(floor_rows_html)

    # Emergency Alert Banner
    emergency_banner_html = ""
    if emergency_mode:
        emergency_banner_html = """
        <div class="emergency-banner">
            <span>🚨 EMERGENCY EVACUATION ACTIVE - ALL CARS RETURNING TO GROUND LOBBY</span>
        </div>
        """

    # Complete HTML component
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, monospace;
        }}
        body {{
            background: {bg_main};
            color: {text_primary};
            padding: 10px;
            overflow-x: auto;
        }}
        .building-container {{
            background: {bg_card};
            border: 1px solid {border_card};
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
            min-width: 680px;
        }}
        .emergency-banner {{
            background: linear-gradient(90deg, #991B1B, #DC2626, #991B1B);
            color: #FFFFFF;
            font-weight: 800;
            font-size: 13px;
            letter-spacing: 0.06em;
            padding: 10px 16px;
            border-radius: 8px;
            margin-bottom: 14px;
            text-align: center;
            border: 2px solid #F87171;
            animation: pulse-emergency 1.2s infinite;
        }}
        @keyframes pulse-emergency {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.85; transform: scale(0.99); }}
        }}
        .building-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid {border_card};
            padding-bottom: 12px;
            margin-bottom: 14px;
        }}
        .building-title {{
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: {'#00F0FF' if not is_light else '#0284C7'};
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .telemetry-pills {{
            display: flex;
            gap: 10px;
            font-size: 12px;
        }}
        .pill {{
            background: {'#1F2937' if not is_light else '#E2E8F0'};
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid {'#374151' if not is_light else '#CBD5E1'};
            color: {text_secondary};
        }}
        .pill strong {{
            color: {text_primary};
        }}

        /* Grid header */
        .grid-header {{
            display: grid;
            grid-template-columns: 85px 140px repeat({num_elevators}, 1fr);
            gap: 8px;
            padding-bottom: 8px;
            border-bottom: 1px solid {border_card};
            margin-bottom: 6px;
        }}
        .header-cell {{
            font-size: 11px;
            font-weight: 600;
            color: {text_secondary};
            text-transform: uppercase;
            letter-spacing: 0.05em;
            display: flex;
            align-items: center;
        }}
        .shaft-header {{
            background: {'#1E293B' if not is_light else '#F8FAFC'};
            border: 1px solid {'#334155' if not is_light else '#CBD5E1'};
            border-radius: 6px;
            padding: 6px 4px;
            text-align: center;
        }}
        .shaft-title {{
            font-size: 11px;
            font-weight: 700;
            color: {'#00F0FF' if not is_light else '#0284C7'};
        }}
        .shaft-subtitle {{
            font-size: 9px;
            color: {text_secondary};
        }}

        /* Floor rows */
        .floors-wrapper {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .floor-row {{
            display: grid;
            grid-template-columns: 85px 140px repeat({num_elevators}, 1fr);
            gap: 8px;
            min-height: 48px;
            background: {row_bg};
            border-bottom: 1px solid {row_border};
            align-items: center;
            padding: 2px 0;
            transition: background 0.2s ease;
        }}
        .floor-row:hover {{
            background: {row_hover};
        }}
        .ground-floor {{
            background: {ground_bg};
            border-left: 3px solid #10B981;
            border-bottom: 2px solid #10B981;
        }}
        .floor-label-cell {{
            padding-left: 6px;
        }}
        .floor-num {{
            font-size: 12px;
            font-weight: 700;
            color: {text_primary};
            letter-spacing: 0.03em;
        }}
        .floor-corridor-cell {{
            padding-right: 4px;
        }}
        .queue-badges {{
            display: flex;
            gap: 4px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .badge {{
            font-size: 10px;
            padding: 2px 5px;
            border-radius: 4px;
            font-weight: 600;
        }}
        .badge-up {{
            background: rgba(0, 240, 255, 0.15);
            color: {'#00F0FF' if not is_light else '#0284C7'};
            border: 1px solid rgba(0, 240, 255, 0.4);
        }}
        .badge-down {{
            background: rgba(245, 158, 11, 0.15);
            color: #F59E0B;
            border: 1px solid rgba(245, 158, 11, 0.4);
        }}
        .badge-muted {{
            background: {'rgba(55, 65, 81, 0.3)' if not is_light else 'rgba(203, 213, 225, 0.5)'};
            color: {text_secondary};
        }}
        .badge-prio {{
            background: rgba(239, 68, 68, 0.25);
            color: #F87171;
            border: 1px solid #EF4444;
            animation: pulse 1.5s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.7; transform: scale(0.96); }}
        }}

        /* Shaft cell */
        .shaft-cell {{
            height: 48px;
            position: relative;
            background: {shaft_bg};
            border-left: 1px dashed {shaft_border};
            border-right: 1px dashed {shaft_border};
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .cable-line {{
            position: absolute;
            top: 0;
            bottom: 0;
            left: 50%;
            width: 1px;
            background: {cable_color};
        }}

        /* Cabin styling */
        .cabin {{
            width: 94%;
            height: 92%;
            background: {cabin_bg};
            border-radius: 6px;
            border: 1.5px solid {cabin_border_default};
            padding: 3px 6px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
            z-index: 2;
            transition: all 0.3s ease;
        }}
        .cabin.moving-up {{
            border-color: {'#00F0FF' if not is_light else '#0284C7'};
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
        }}
        .cabin.moving-down {{
            border-color: #F59E0B;
            box-shadow: 0 0 10px rgba(245, 158, 11, 0.3);
        }}
        .cabin.idle {{
            border-color: #64748B;
        }}
        .cabin.emergency {{
            border-color: #EF4444;
            background: rgba(239, 68, 68, 0.2);
            box-shadow: 0 0 14px rgba(239, 68, 68, 0.5);
            animation: pulse-emergency 1.5s infinite;
        }}
        .cabin.door-open {{
            background: {'#064E3B' if not is_light else '#D1FAE5'};
            border-color: #10B981;
            box-shadow: 0 0 12px rgba(16, 185, 129, 0.4);
        }}
        .cabin-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 10px;
            font-weight: 700;
        }}
        .cabin-title {{
            color: {text_primary};
        }}
        .cabin-dir {{
            font-size: 11px;
            font-weight: 800;
        }}
        .cabin-load {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .load-bar-bg {{
            flex: 1;
            height: 5px;
            background: {'#334155' if not is_light else '#E2E8F0'};
            border-radius: 3px;
            overflow: hidden;
        }}
        .load-bar-fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }}
        .load-text {{
            font-size: 9px;
            color: {text_secondary};
            font-weight: 600;
        }}
        .cabin-info-tags {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 8px;
            font-weight: 600;
        }}
        .tag-chip {{
            color: {text_secondary};
        }}
        .door-tag {{
            font-weight: 700;
            text-transform: uppercase;
        }}
    </style>
    </head>
    <body>
        <div class="building-container">
            {emergency_banner_html}
            <div class="building-header">
                <div class="building-title">
                    <span>🏢 MULTI-SHAFT BUILDING VISUALIZER</span>
                </div>
                <div class="telemetry-pills">
                    <div class="pill">SIM TIME: <strong>{current_time:.1f}s</strong></div>
                    <div class="pill">FLOORS: <strong>{num_floors}</strong></div>
                    <div class="pill">ELEVATORS: <strong>{num_elevators}</strong></div>
                    <div class="pill">WAITING: <strong>{building.get_total_waiting_passengers()}</strong></div>
                    <div class="pill">THEME: <strong>{theme.upper()}</strong></div>
                </div>
            </div>

            <div class="grid-header">
                <div class="header-cell">FLOOR</div>
                <div class="header-cell">QUEUE (UP/DN)</div>
                {shaft_headers_str}
            </div>

            <div class="floors-wrapper">
                {all_floors_str}
            </div>
        </div>
    </body>
    </html>
    """
    return html
