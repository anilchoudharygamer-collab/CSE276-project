"""
Interactive Plotly Visualization Charts.
Generates charts for algorithm benchmarking, live telemetry, and spatial demand:
- 1. Average waiting time comparison
- 2. Average journey time comparison
- 3. Elevator utilization comparison
- 4. Energy consumption comparison
- 5. Passengers served over time
- 6. Waiting time distribution histogram/box plot
- 7. Live simulation telemetry time-series
- 8. Demand prediction probability distribution
- 9. 2D Floor-to-Floor Passenger Demand Heatmap (Origin x Destination)
- 10. Traffic Intensity curve over time
"""

from typing import Dict, Any, List, Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

ALGO_COLORS = {
    "Nearest-Car": "#EF4444",              # Coral Red
    "Collective-Control": "#F59E0B",       # Amber
    "Utility-Based Intelligent": "#00F0FF", # Cyber Cyan
}

def get_theme_layout(theme: str = "dark") -> dict:
    is_light = (theme.lower() == "light")
    return dict(
        paper_bgcolor="#FFFFFF" if is_light else "#111827",
        plot_bgcolor="#F8FAFC" if is_light else "#0F172A",
        font=dict(color="#0F172A" if is_light else "#E2E8F0", family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, monospace"),
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
    )


def plot_wait_time_comparison(comparison_df: pd.DataFrame, theme: str = "dark") -> go.Figure:
    """1. Average waiting time comparison across algorithms."""
    colors = [ALGO_COLORS.get(name, "#38BDF8") for name in comparison_df["Algorithm"]]

    fig = go.Figure(data=[
        go.Bar(
            x=comparison_df["Algorithm"],
            y=comparison_df["Avg Wait Time (s)"],
            marker_color=colors,
            text=comparison_df["Avg Wait Time (s)"].apply(lambda v: f"{v:.1f}s"),
            textposition="auto",
            name="Avg Wait Time",
        )
    ])
    fig.update_layout(
        **get_theme_layout(theme),
        title="⏱️ Average Passenger Waiting Time (Lower is Better)",
        xaxis_title="Dispatch Algorithm",
        yaxis_title="Seconds",
    )
    return fig


def plot_journey_time_comparison(comparison_df: pd.DataFrame, theme: str = "dark") -> go.Figure:
    """2. Average journey time comparison across algorithms."""
    colors = [ALGO_COLORS.get(name, "#38BDF8") for name in comparison_df["Algorithm"]]

    fig = go.Figure(data=[
        go.Bar(
            x=comparison_df["Algorithm"],
            y=comparison_df["Avg Journey Time (s)"],
            marker_color=colors,
            text=comparison_df["Avg Journey Time (s)"].apply(lambda v: f"{v:.1f}s"),
            textposition="auto",
            name="Avg Journey Time",
        )
    ])
    fig.update_layout(
        **get_theme_layout(theme),
        title="🚀 Average Total Journey Time (Lower is Better)",
        xaxis_title="Dispatch Algorithm",
        yaxis_title="Seconds",
    )
    return fig


def plot_utilization_comparison(comparison_df: pd.DataFrame, theme: str = "dark") -> go.Figure:
    """3. Elevator utilization comparison."""
    colors = [ALGO_COLORS.get(name, "#38BDF8") for name in comparison_df["Algorithm"]]

    fig = go.Figure(data=[
        go.Bar(
            x=comparison_df["Algorithm"],
            y=comparison_df["Elevator Utilization (%)"],
            marker_color=colors,
            text=comparison_df["Elevator Utilization (%)"].apply(lambda v: f"{v:.1f}%"),
            textposition="auto",
            name="Utilization %",
        )
    ])
    fig.update_layout(
        **get_theme_layout(theme),
        title="⚙️ Elevator Fleet Utilization Rate (%)",
        xaxis_title="Dispatch Algorithm",
        yaxis_title="Fleet Active Time (%)",
        yaxis_range=[0, 100],
    )
    return fig


def plot_energy_comparison(comparison_df: pd.DataFrame, theme: str = "dark") -> go.Figure:
    """4. Energy consumption comparison."""
    colors = [ALGO_COLORS.get(name, "#38BDF8") for name in comparison_df["Algorithm"]]

    fig = go.Figure(data=[
        go.Bar(
            x=comparison_df["Algorithm"],
            y=comparison_df["Total Energy (kWh)"],
            marker_color=colors,
            text=comparison_df["Total Energy (kWh)"].apply(lambda v: f"{v:.3f} kWh"),
            textposition="auto",
            name="Total Energy",
        )
    ])
    fig.update_layout(
        **get_theme_layout(theme),
        title="⚡ Total Electrical Energy Consumption (kWh) (Lower is Better)",
        xaxis_title="Dispatch Algorithm",
        yaxis_title="Energy (kWh)",
    )
    return fig


def plot_passengers_served_over_time(raw_results: Dict[str, Any], theme: str = "dark") -> go.Figure:
    """5. Cumulative passengers served over simulation time across algorithms."""
    fig = go.Figure()

    for algo_name, data in raw_results.items():
        snaps = data.get("history_snapshots", [])
        if not snaps:
            continue
        times = [s["time"] for s in snaps]
        served = [s["total_served"] for s in snaps]
        color = ALGO_COLORS.get(algo_name, "#38BDF8")

        fig.add_trace(go.Scatter(
            x=times,
            y=served,
            mode="lines+markers",
            name=algo_name,
            line=dict(color=color, width=2.5),
            marker=dict(size=4),
        ))

    fig.update_layout(
        **get_theme_layout(theme),
        title="📈 Cumulative Passengers Served Over Time",
        xaxis_title="Simulation Time (s)",
        yaxis_title="Completed Trips",
    )
    return fig


def plot_wait_time_distribution(raw_results: Dict[str, Any], theme: str = "dark") -> go.Figure:
    """6. Waiting time distribution comparison (Box Plot)."""
    fig = go.Figure()

    for algo_name, data in raw_results.items():
        waits = data.get("wait_times", [])
        if not waits:
            continue
        color = ALGO_COLORS.get(algo_name, "#38BDF8")

        fig.add_trace(go.Box(
            y=waits,
            name=algo_name,
            marker_color=color,
            boxmean=True,
        ))

    fig.update_layout(
        **get_theme_layout(theme),
        title="📊 Passenger Waiting Time Distribution & Spread",
        xaxis_title="Dispatch Algorithm",
        yaxis_title="Wait Time (Seconds)",
    )
    return fig


def plot_live_telemetry(history_snapshots: List[Dict[str, Any]], theme: str = "dark") -> go.Figure:
    """7. Live telemetry dual-axis line chart for real-time simulation page."""
    if not history_snapshots:
        return go.Figure()

    times = [s["time"] for s in history_snapshots]
    waiting = [s["total_waiting"] for s in history_snapshots]
    served = [s["total_served"] for s in history_snapshots]
    energy = [s["total_energy_kwh"] for s in history_snapshots]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=waiting, mode="lines", name="Waiting Queue",
        line=dict(color="#F59E0B", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=times, y=served, mode="lines", name="Total Served",
        line=dict(color="#10B981", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=times, y=energy, mode="lines", name="Energy (kWh)",
        line=dict(color="#00F0FF", width=2, dash="dash"),
        yaxis="y2"
    ))

    fig.update_layout(
        **get_theme_layout(theme),
        title="📡 Real-Time Telemetry: Queue, Throughput & Energy",
        xaxis_title="Time (s)",
        yaxis=dict(title="Passenger Count"),
        yaxis2=dict(
            title="Energy (kWh)",
            overlaying="y",
            side="right",
            showgrid=False
        ),
    )
    return fig


def plot_demand_prediction_chart(distribution: List[float], theme: str = "dark") -> go.Figure:
    """8. Floor demand probability distribution forecasted by Demand Predictor."""
    floors = [f"F {i:02d}" if i > 0 else "Lobby (G)" for i in range(len(distribution))]
    top_floor_idx = int(np.argmax(distribution))
    colors = ["#00F0FF" if i == top_floor_idx else "#334155" for i in range(len(distribution))]

    fig = go.Figure(data=[
        go.Bar(
            x=floors,
            y=distribution,
            marker_color=colors,
            text=[f"{v:.1f}%" for v in distribution],
            textposition="auto",
        )
    ])
    fig.update_layout(
        **get_theme_layout(theme),
        title="🧠 Predictive Floor Demand Probability Distribution P(Floor)",
        xaxis_title="Building Floor",
        yaxis_title="Probability (%)",
    )
    return fig


def plot_passenger_demand_heatmap(demand_matrix: np.ndarray, theme: str = "dark") -> go.Figure:
    """9. 2D Origin-Destination Passenger Flow Heatmap."""
    num_floors = demand_matrix.shape[0]
    floor_labels = [f"F{i}" if i > 0 else "Lobby" for i in range(num_floors)]

    colorscale = "Viridis" if theme == "dark" else "Blues"

    fig = go.Figure(data=go.Heatmap(
        z=demand_matrix,
        x=floor_labels,
        y=floor_labels,
        colorscale=colorscale,
        colorbar=dict(title="Trips"),
        hoverongaps=False,
    ))
    fig.update_layout(
        **get_theme_layout(theme),
        title="🗺️ 2D Passenger Origin-to-Destination Flow Heatmap",
        xaxis_title="Destination Floor",
        yaxis_title="Pickup (Origin) Floor",
    )
    return fig


def plot_elevator_workload_distribution(elevators_telemetry: List[Dict[str, Any]], theme: str = "dark") -> go.Figure:
    """10. Workload distribution across the elevator fleet."""
    car_ids = [f"E{e['elevator_id']}" for e in elevators_telemetry]
    served = [e["total_passengers_served"] for e in elevators_telemetry]
    distance = [e["total_distance_floors"] for e in elevators_telemetry]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=car_ids, y=served, name="Passengers Served",
        marker_color="#10B981"
    ))
    fig.add_trace(go.Bar(
        x=car_ids, y=distance, name="Distance (Floors)",
        marker_color="#38BDF8"
    ))

    fig.update_layout(
        **get_theme_layout(theme),
        title="🚡 Fleet Workload & Mileage Distribution",
        xaxis_title="Elevator Car",
        yaxis_title="Value",
        barmode="group",
    )
    return fig
