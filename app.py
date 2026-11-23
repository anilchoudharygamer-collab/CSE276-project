"""
Intelligent Elevator Group Dispatch Agent System
Premium Smart Building Management Control Center.
"""

import sys
import os

# Ensure project root is at the head of sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np

from config.settings import SimulationConfig, UtilityWeights, TrafficScenarioType, SystemTheme
from simulation.engine import SimulationEngine, SimulationState
from simulation.building import Building
from agents.dispatch_agent import DispatchAgent
from algorithms.nearest_car import NearestCarAlgorithm
from algorithms.collective_control import CollectiveControlAlgorithm
from algorithms.utility_based import UtilityBasedAlgorithm
from visualization.building_view import render_building_html
from visualization.charts import (
    plot_wait_time_comparison,
    plot_journey_time_comparison,
    plot_utilization_comparison,
    plot_energy_comparison,
    plot_passengers_served_over_time,
    plot_wait_time_distribution,
    plot_live_telemetry,
    plot_demand_prediction_chart,
    plot_passenger_demand_heatmap,
    plot_elevator_workload_distribution,
)
from analytics.comparison import AlgorithmComparator
from analytics.report_generator import ReportGenerator

# Configure Streamlit Page
st.set_page_config(
    page_title="Elevator AI Agent Control Center",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

def init_session_state():
    """Initializes persistent simulation engine and algorithm instances."""
    if "config" not in st.session_state:
        st.session_state.config = SimulationConfig()

    if "current_theme" not in st.session_state:
        st.session_state.current_theme = "dark"

    if "algorithm" not in st.session_state:
        st.session_state.algorithm = UtilityBasedAlgorithm(st.session_state.config.utility_weights)

    if "engine" not in st.session_state:
        dispatch_agent = DispatchAgent(algorithm=st.session_state.algorithm)
        engine = SimulationEngine(config=st.session_state.config, dispatch_agent=dispatch_agent)
        st.session_state.engine = engine

    if "benchmark_results" not in st.session_state:
        st.session_state.benchmark_results = None

    if "replay_idx" not in st.session_state:
        st.session_state.replay_idx = 0


init_session_state()
engine: SimulationEngine = st.session_state.engine
config: SimulationConfig = st.session_state.config
theme = st.session_state.current_theme

# Load CSS stylesheet
CSS_PATH = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(CSS_PATH):
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        theme_attr = f'data-theme="{theme}"'
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ==========================================
# SIDEBAR CONTROLS & MONITORING
# ==========================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 6px 0 12px 0;">
        <h2 style="color: #00F0FF; margin:0; font-size: 19px; font-weight: 800; letter-spacing: 0.05em;">🏢 ELEVATOR AI AGENT</h2>
        <span style="font-size: 10px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em;">Group Dispatch Control Center</span>
    </div>
    """, unsafe_allow_html=True)

    # Theme Switcher
    theme_col1, theme_col2 = st.columns(2)
    with theme_col1:
        if st.button("🌙 Cyber Dark", use_container_width=True, type="primary" if theme == "dark" else "secondary"):
            st.session_state.current_theme = "dark"
            config.theme = SystemTheme.DARK
            st.rerun()
    with theme_col2:
        if st.button("☀️ Industrial Light", use_container_width=True, type="primary" if theme == "light" else "secondary"):
            st.session_state.current_theme = "light"
            config.theme = SystemTheme.LIGHT
            st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Simulation Status Badge
    status_color = "#EF4444" if config.emergency_mode else ("#10B981" if engine.state == SimulationState.RUNNING else ("#F59E0B" if engine.state == SimulationState.PAUSED else "#6B7280"))
    status_label = "EMERGENCY" if config.emergency_mode else engine.state.value

    st.markdown(f"""
    <div style="background: {'#1E293B' if theme == 'dark' else '#F1F5F9'}; border-radius: 8px; padding: 10px; margin-bottom: 12px; border: 1px solid {'#334155' if theme == 'dark' else '#CBD5E1'}; text-align: center;">
        <span style="font-size: 11px; color: {'#94A3B8' if theme == 'dark' else '#64748B'};">STATUS: </span>
        <strong style="color: {status_color}; font-size: 13px;">{status_label}</strong>
        <div style="font-size: 12px; color: {'#E2E8F0' if theme == 'dark' else '#0F172A'}; margin-top: 4px;">Simulation Time: <strong>{engine.current_time:.1f}s</strong></div>
    </div>
    """, unsafe_allow_html=True)

    # Emergency Mode Toggle
    if not config.emergency_mode:
        if st.button("🚨 TRIGGER EMERGENCY EVACUATION", use_container_width=True):
            engine.trigger_emergency()
            st.toast("EMERGENCY EVACUATION ACTIVATED: Cars proceeding to Ground Floor", icon="🚨")
            st.rerun()
    else:
        if st.button("✅ CANCEL EMERGENCY & RESUME", type="primary", use_container_width=True):
            engine.clear_emergency()
            st.toast("Emergency cleared. Resuming normal dispatching.", icon="✅")
            st.rerun()

    st.markdown("---")
    st.subheader("🎮 Core Controls")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("▶️ Step +1s", use_container_width=True, type="primary"):
            engine.start()
            engine.step(1.0)
            st.rerun()
    with col_c2:
        if st.button("⏸️ Pause", use_container_width=True):
            engine.pause()
            st.rerun()

    col_c3, col_c4 = st.columns(2)
    with col_c3:
        if st.button("⏩ Step +5s", use_container_width=True):
            engine.start()
            engine.run_steps(5, 1.0)
            st.rerun()
    with col_c4:
        if st.button("🔄 Reset", use_container_width=True):
            engine.reset()
            st.rerun()

    st.markdown("---")
    st.subheader("⚡ Active Strategy")
    algo_names = ["Utility-Based Intelligent", "Collective-Control", "Nearest-Car"]
    current_algo_idx = 0
    if isinstance(engine.dispatch_agent.algorithm, CollectiveControlAlgorithm):
        current_algo_idx = 1
    elif isinstance(engine.dispatch_agent.algorithm, NearestCarAlgorithm):
        current_algo_idx = 2

    chosen_algo_name = st.selectbox(
        "Dispatch Strategy",
        algo_names,
        index=current_algo_idx,
    )
    if chosen_algo_name != engine.dispatch_agent.algorithm.name:
        if chosen_algo_name == "Nearest-Car":
            new_algo = NearestCarAlgorithm()
        elif chosen_algo_name == "Collective-Control":
            new_algo = CollectiveControlAlgorithm()
        else:
            new_algo = UtilityBasedAlgorithm(config.utility_weights)
        engine.dispatch_agent.set_algorithm(new_algo)
        st.toast(f"Active strategy: {chosen_algo_name}", icon="🔄")

    st.markdown("---")
    st.subheader("🚦 Traffic Scenario")
    scenarios = [s.value for s in TrafficScenarioType]
    cur_scen_idx = scenarios.index(config.scenario.value if hasattr(config.scenario, "value") else str(config.scenario))
    chosen_scenario = st.selectbox(
        "Traffic Pattern",
        scenarios,
        index=cur_scen_idx,
    )
    if chosen_scenario != config.scenario.value:
        config.scenario = TrafficScenarioType(chosen_scenario)
        engine.traffic_generator.set_scenario(config.scenario)
        st.toast(f"Scenario: {chosen_scenario}", icon="🚦")

    st.markdown("---")
    st.subheader("🙋 Manual Passenger Call")
    with st.expander("Inject Single Request", expanded=False):
        p_pickup = st.number_input("Pickup Floor", min_value=0, max_value=config.num_floors - 1, value=0)
        p_dest = st.number_input("Destination Floor", min_value=0, max_value=config.num_floors - 1, value=min(8, config.num_floors - 1))
        p_vip = st.checkbox("VIP / Priority Request (⚡ Urgent)", value=False)
        if st.button("Spawn & Dispatch Request", use_container_width=True):
            if p_pickup == p_dest:
                st.warning("Pickup and destination floors must be different.")
            else:
                p = engine.inject_manual_passenger(p_pickup, p_dest, p_vip)
                st.success(f"Dispatched {p.id} (F{p_pickup} ➔ F{p_dest}, VIP: {p_vip})")
                st.rerun()


# ==========================================
# MAIN DASHBOARD NAVIGATION
# ==========================================
tabs = st.tabs([
    "🏠 1. Overview",
    "🏢 2. Live Simulation",
    "🧠 3. Dispatch Algorithms",
    "🚦 4. Traffic Scenarios",
    "📊 5. Performance Analysis",
    "⚙️ 6. System Settings",
])

# Banner Styling based on theme
banner_class = "control-center-banner" if theme == "dark" else "control-center-banner banner-light"


# =========================================================================
# TAB 1: SYSTEM OVERVIEW
# =========================================================================
with tabs[0]:
    if config.emergency_mode:
        st.markdown("""
        <div class="emergency-alarm-bar">
            🚨 EMERGENCY EVACUATION ACTIVE: ALL ELEVATORS ARE ORDERED TO GROUND FLOOR (LOBBY)
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="{banner_class}">
        <div class="banner-title">
            <span style="color: {'#FFFFFF' if theme == 'dark' else '#0F172A'};">🏢 SMART BUILDING ELEVATOR MANAGEMENT SYSTEM</span>
        </div>
        <div class="banner-desc">
            Centralized intelligent multi-agent coordinator optimizing passenger waiting time, journey duration, elevator fleet congestion, and energy consumption.
        </div>
    </div>
    """, unsafe_allow_html=True)

    summary = engine.get_summary_metrics()

    # Hero KPI Row
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f"""
        <div class="kpi-card cyan">
            <div class="kpi-label">Active Elevators</div>
            <div class="kpi-value">{config.num_elevators} Cars</div>
            <div class="kpi-subtext">Shafts: 1 to {config.num_elevators} | Floors: 0 to {config.num_floors - 1}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi2:
        st.markdown(f"""
        <div class="kpi-card amber">
            <div class="kpi-label">Waiting Queue</div>
            <div class="kpi-value">{summary['total_waiting']}</div>
            <div class="kpi-subtext">Onboard Passengers: {summary['total_in_transit']}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi3:
        st.markdown(f"""
        <div class="kpi-card emerald">
            <div class="kpi-label">Completed Journeys</div>
            <div class="kpi-value">{summary['total_served']}</div>
            <div class="kpi-subtext">Total Passenger Calls: {summary['total_generated']}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi4:
        st.markdown(f"""
        <div class="kpi-card rose">
            <div class="kpi-label">Average Wait Time</div>
            <div class="kpi-value">{summary['avg_wait_time_sec']:.1f}s</div>
            <div class="kpi-subtext">Peak Wait: {summary['max_wait_time_sec']:.1f}s</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Middle Row: Fleet Status Table & Intelligence Card
    col_fleet, col_info = st.columns([1.6, 1])
    with col_fleet:
        st.subheader("🚡 Elevator Fleet Real-Time Status")
        elev_records = []
        for e in engine.building.elevators:
            elev_records.append({
                "Car": f"Elevator #{e.elevator_id}",
                "Floor": f"{e.current_floor:.1f}",
                "Heading": f"{e.direction.symbol} {e.direction.label}",
                "Load": f"{e.passenger_count}/{e.capacity} ({int(e.load_factor*100)}%)",
                "Doors": e.door_state.value,
                "Pickups": e.pickup_floors_str,
                "Dropoffs": e.dropoff_floors_str,
                "Energy (kWh)": f"{e.total_energy_kwh:.4f}",
            })
        st.dataframe(pd.DataFrame(elev_records), use_container_width=True, hide_index=True)

    with col_info:
        st.subheader("🧠 Intelligence Status")
        top_prediction = engine.demand_predictor.get_summary_stats(engine.current_time)
        st.markdown(f"""
        <div class="decision-card">
            <div style="font-size: 11px; color: {'#94A3B8' if theme == 'dark' else '#64748B'}; text-transform: uppercase;">Active Strategy</div>
            <div style="font-size: 16px; font-weight: 700; color: {'#00F0FF' if theme == 'dark' else '#0284C7'}; margin: 4px 0;">{engine.dispatch_agent.algorithm.name}</div>
            <div style="font-size: 12px;">{engine.dispatch_agent.algorithm.description}</div>
        </div>
        <div class="decision-card">
            <div style="font-size: 11px; color: {'#94A3B8' if theme == 'dark' else '#64748B'}; text-transform: uppercase;">Smart Demand Prediction</div>
            <div style="font-size: 14px; font-weight: 600; color: #10B981; margin: 4px 0;">
                High Demand Target: Floor {top_prediction['top_demand_floor']} ({top_prediction['top_demand_probability']}%)
            </div>
            <div style="font-size: 12px;">Autonomous Repositions: <strong>{top_prediction['total_predictive_actions']}</strong></div>
        </div>
        """, unsafe_allow_html=True)

    # Workload Distribution
    st.markdown("<br>", unsafe_allow_html=True)
    elev_telemetry = [e.to_dict() for e in engine.building.elevators]
    fig_workload = plot_elevator_workload_distribution(elev_telemetry, theme=theme)
    st.plotly_chart(fig_workload, use_container_width=True)


# =========================================================================
# TAB 2: LIVE SIMULATION & BUILDING VISUALIZATION
# =========================================================================
with tabs[1]:
    if config.emergency_mode:
        st.markdown("""
        <div class="emergency-alarm-bar">
            🚨 EMERGENCY EVACUATION PROTOCOL ACTIVE: All elevators descending to ground level
        </div>
        """, unsafe_allow_html=True)

    st.subheader("🏢 Multi-Shaft Architectural Simulation")
    st.caption("Live elevator movements, passenger boarding/alighting, and per-floor hall call queues.")

    # Stepping bar
    s_col1, s_col2, s_col3, s_col4 = st.columns([1, 1, 1, 1])
    with s_col1:
        if st.button("▶️ Step 1s", key="tab2_s1", use_container_width=True):
            engine.step(1.0)
            st.rerun()
    with s_col2:
        if st.button("⏩ Step 5s", key="tab2_s5", use_container_width=True):
            engine.run_steps(5, 1.0)
            st.rerun()
    with s_col3:
        if st.button("⏩ Step 10s", key="tab2_s10", use_container_width=True):
            engine.run_steps(10, 1.0)
            st.rerun()
    with s_col4:
        if st.button("🔄 Reset", key="tab2_reset", use_container_width=True):
            engine.reset()
            st.rerun()

    # Render Visual Building
    building_html = render_building_html(
        engine.building,
        engine.current_time,
        theme=theme,
        emergency_mode=config.emergency_mode,
    )
    components.html(building_html, height=730, scrolling=True)

    # Simulation Replay Inspector
    if engine.replay_buffer:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("⏪ Simulation Replay & State Inspector")
        st.caption("Scrub through recently recorded simulation moments to review elevator positioning and queues.")
        replay_times = [s["time"] for s in engine.replay_buffer]
        selected_time = st.select_slider(
            "Replay Timestamp (Seconds)",
            options=replay_times,
            value=replay_times[-1],
        )
        # Find matching snapshot
        snap_match = next((s for s in engine.replay_buffer if s["time"] == selected_time), None)
        if snap_match:
            rep_col1, rep_col2, rep_col3 = st.columns(3)
            with rep_col1:
                st.metric("Recorded Time", f"{snap_match['time']}s")
            with rep_col2:
                st.metric("Waiting Queue at T", snap_match["total_waiting"])
            with rep_col3:
                st.metric("Passengers Served at T", snap_match["total_served"])

    # Real-time telemetry line chart
    if engine.history_snapshots:
        st.markdown("<br>", unsafe_allow_html=True)
        fig_telemetry = plot_live_telemetry(engine.history_snapshots, theme=theme)
        st.plotly_chart(fig_telemetry, use_container_width=True)


# =========================================================================
# TAB 3: DISPATCH ALGORITHMS & DECISION EXPLANATIONS
# =========================================================================
with tabs[2]:
    st.subheader("🧠 Multi-Agent Dispatching Algorithms & Decision Rationales")
    st.markdown("""
    The central dispatch agent uses one of three dispatching strategies.
    Inspect how decisions are made, view the candidate evaluation matrix, and calibrate utility weights.
    """)

    algo_desc_col1, algo_desc_col2, algo_desc_col3 = st.columns(3)
    with algo_desc_col1:
        st.markdown(f"""
        <div class="decision-card" style="border-top: 3px solid #EF4444; height: 100%;">
            <h4 style="color: #EF4444; margin: 0 0 8px 0;">1. Nearest-Car (NC)</h4>
            <p style="font-size: 12px; color: {'#94A3B8' if theme == 'dark' else '#64748B'};">
                Greedy heuristic selecting the elevator with smallest physical distance.
                Applies availability and directional heading penalties, but ignores future stops,
                waiting accumulation, and electrical energy.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with algo_desc_col2:
        st.markdown(f"""
        <div class="decision-card" style="border-top: 3px solid #F59E0B; height: 100%;">
            <h4 style="color: #F59E0B; margin: 0 0 8px 0;">2. Collective-Control (CC)</h4>
            <p style="font-size: 12px; color: {'#94A3B8' if theme == 'dark' else '#64748B'};">
                Traditional duplex/triplex logic enforcing directional persistence.
                Cars serve co-directional calls along their travel path before reversing,
                minimizing abrupt direction changes.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with algo_desc_col3:
        st.markdown(f"""
        <div class="decision-card" style="border-top: 3px solid #00F0FF; height: 100%;">
            <h4 style="color: {'#00F0FF' if theme == 'dark' else '#0284C7'}; margin: 0 0 8px 0;">3. Utility-Based Intelligent (UB)</h4>
            <p style="font-size: 12px; color: {'#94A3B8' if theme == 'dark' else '#64748B'};">
                Multi-objective AI optimization calculating a comprehensive cost function J(e, p).
                Balances estimated pickup time, waiting duration, car load, intermediate stops,
                journey time, energy, and VIP urgency.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("⚖️ Utility Scoring Function Calibration")
    with st.form("utility_weights_form_v2"):
        w_col1, w_col2, w_col3, w_col4 = st.columns(4)
        with w_col1:
            w_pickup = st.slider("Pickup Time Weight", 0.0, 5.0, config.utility_weights.pickup_time_weight, 0.1)
            w_wait = st.slider("Wait Time Penalty Weight", 0.0, 5.0, config.utility_weights.wait_time_weight, 0.1)
        with w_col2:
            w_load = st.slider("Elevator Load Weight", 0.0, 5.0, config.utility_weights.load_weight, 0.1)
            w_dir = st.slider("Direction Penalty Weight", 0.0, 5.0, config.utility_weights.direction_penalty_weight, 0.1)
        with w_col3:
            w_journey = st.slider("Journey Time Weight", 0.0, 5.0, config.utility_weights.journey_time_weight, 0.1)
            w_stops = st.slider("Existing Stops Weight", 0.0, 5.0, config.utility_weights.existing_stops_weight, 0.1)
        with w_col4:
            w_priority = st.slider("VIP Priority Bonus Weight", 0.0, 5.0, config.utility_weights.priority_weight, 0.1)
            w_energy = st.slider("Energy Efficiency Weight", 0.0, 5.0, config.utility_weights.energy_weight, 0.1)

        if st.form_submit_button("💾 Save and Apply Scoring Weights", use_container_width=True):
            config.utility_weights = UtilityWeights(
                pickup_time_weight=w_pickup,
                wait_time_weight=w_wait,
                load_weight=w_load,
                direction_penalty_weight=w_dir,
                journey_time_weight=w_journey,
                existing_stops_weight=w_stops,
                priority_weight=w_priority,
                energy_weight=w_energy,
            )
            if isinstance(engine.dispatch_agent.algorithm, UtilityBasedAlgorithm):
                engine.dispatch_agent.algorithm.set_weights(config.utility_weights)
            st.success("Utility weights updated successfully!")

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🔍 Dispatch Decision Audit Log & Candidate Matrix")
    st.caption("Displays the evaluation matrix of ALL candidate elevators for each dispatch assignment.")

    decisions = engine.dispatch_agent.get_recent_decisions(limit=15)
    if decisions:
        for idx, d in enumerate(decisions):
            with st.expander(f"Assignment #{len(decisions) - idx}: Passenger {d['passenger_id']} ➔ Elevator #{d['elevator_id']} (Score: {d['score']})"):
                st.markdown(f"**Explanation:** {d['explanation']}")
                candidates = d.get("breakdown", {}).get("candidates", [])
                if candidates:
                    st.write("**Candidate Evaluation Matrix:**")
                    st.dataframe(pd.DataFrame(candidates), use_container_width=True, hide_index=True)
    else:
        st.info("No dispatch decisions recorded yet. Start simulation or inject a passenger call.")


# =========================================================================
# TAB 4: TRAFFIC SCENARIOS & PASSENGER DEMAND
# =========================================================================
with tabs[3]:
    st.subheader("🚦 Passenger Traffic Scenarios & Flow Forecasting")
    st.markdown("""
    Evaluate dispatch performance across standard building traffic profiles.
    """)

    scen_col1, scen_col2 = st.columns([1, 1])
    with scen_col1:
        st.markdown(f"""
        <div class="decision-card">
            <h4 style="color: {'#00F0FF' if theme == 'dark' else '#0284C7'}; margin: 0 0 6px 0;">Active Pattern: {config.scenario.value}</h4>
            <p style="font-size: 13px; color: {'#CBD5E1' if theme == 'dark' else '#334155'};">
                Arrival rate: <strong>{config.passenger_arrival_rate:.2f} passengers/second</strong><br>
                VIP Request Ratio: <strong>{int(config.priority_passenger_ratio * 100)}%</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Scenario Descriptions")
        st.markdown("""
        - **🌅 Scenario 1: Morning Up-Peak**: ~85% of passengers arrive at the ground lobby (Floor 0) headed up to office floors. Tests up-peak dispatch and bunching prevention.
        - **🍲 Scenario 2: Lunch Two-Way Traffic**: Heavy two-way flow between upper floors and food/lobby levels (Floors 0 & 1), mixed with random inter-floor meetings.
        - **🌇 Scenario 3: Evening Down-Peak**: ~85% of passengers depart from upper floors destined for the ground lobby (Floor 0). Tests evacuation throughput and down-call aggregation.
        - **⚙️ Custom Traffic**: User-configured arrival rate and floor distribution.
        """)

    with scen_col2:
        st.markdown("#### 🧠 Intelligent Demand Prediction Forecast")
        demand_stats = engine.demand_predictor.get_summary_stats(engine.current_time)
        fig_demand = plot_demand_prediction_chart(demand_stats["distribution"], theme=theme)
        st.plotly_chart(fig_demand, use_container_width=True)


# =========================================================================
# TAB 5: PERFORMANCE ANALYSIS & 3-ALGORITHM BENCHMARK
# =========================================================================
with tabs[4]:
    st.subheader("📊 Comparative Algorithm Benchmark & Spatial Heatmap")
    st.markdown("""
    Execute reproducible parallel simulations comparing **Nearest-Car**, **Collective-Control**,
    and **Utility-Based Intelligent** strategies under identical passenger demand.
    """)

    with st.container():
        b_col1, b_col2, b_col3, b_col4 = st.columns([1.5, 1.5, 1.5, 2])
        with b_col1:
            bench_duration = st.selectbox("Benchmark Duration", [60, 120, 180, 300], index=1)
        with b_col2:
            bench_scen = st.selectbox(
                "Benchmark Scenario",
                [s.value for s in TrafficScenarioType],
                index=scenarios.index(config.scenario.value),
                key="bench_scen_select_v2"
            )
        with b_col3:
            bench_seed = st.number_input("Random Seed (Reproducibility)", value=config.random_seed, step=1)
        with b_col4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            run_bench_clicked = st.button("🚀 Execute 3-Algorithm Benchmark", type="primary", use_container_width=True)

    if run_bench_clicked:
        comparator = AlgorithmComparator(config=config)
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def update_progress(pct: float, msg: str):
            progress_bar.progress(pct)
            status_text.text(msg)

        with st.spinner("Simulating parallel elevator dispatch strategies..."):
            results = comparator.run_benchmark(
                duration_sec=float(bench_duration),
                scenario=TrafficScenarioType(bench_scen),
                seed=int(bench_seed),
                progress_callback=update_progress,
            )
            st.session_state.benchmark_results = results
            progress_bar.empty()
            status_text.empty()
            st.success("Benchmark completed successfully!")

    # Display Benchmark Results
    if st.session_state.benchmark_results:
        b_res = st.session_state.benchmark_results
        df_comp = b_res["comparison_df"]
        winners = b_res["winners"]
        improvements = b_res["utility_improvements"]

        st.markdown(f"""
        <div class="winner-card">
            <h3>🏆 Benchmark Winner: {winners['lowest_wait_time']}</h3>
            <p style="margin: 0; font-size: 14px; color: {'#E2E8F0' if theme == 'dark' else '#0F172A'};">
                Under <strong>{b_res['scenario']}</strong> (Duration: {b_res['duration_sec']}s, Seed: {b_res['seed']}):<br>
                • <strong>{improvements['wait_time_reduction_pct']}%</strong> Reduction in Passenger Waiting Time vs Nearest-Car<br>
                • <strong>{improvements['energy_savings_pct']}%</strong> Energy Savings in Total Electrical Consumption<br>
                • Lowest Journey Time: <strong>{winners['lowest_journey_time']}</strong> | Highest Throughput: <strong>{winners['highest_throughput']}</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📋 Performance Metrics Comparison Table")
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        # 6 Comparative Plotly Charts
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📈 Interactive Comparative Visualizations")

        chart_row1_c1, chart_row1_c2 = st.columns(2)
        with chart_row1_c1:
            fig_wait = plot_wait_time_comparison(df_comp, theme=theme)
            st.plotly_chart(fig_wait, use_container_width=True)
        with chart_row1_c2:
            fig_journey = plot_journey_time_comparison(df_comp, theme=theme)
            st.plotly_chart(fig_journey, use_container_width=True)

        chart_row2_c1, chart_row2_c2 = st.columns(2)
        with chart_row2_c1:
            fig_util = plot_utilization_comparison(df_comp, theme=theme)
            st.plotly_chart(fig_util, use_container_width=True)
        with chart_row2_c2:
            fig_energy = plot_energy_comparison(df_comp, theme=theme)
            st.plotly_chart(fig_energy, use_container_width=True)

        chart_row3_c1, chart_row3_c2 = st.columns(2)
        with chart_row3_c1:
            fig_served = plot_passengers_served_over_time(b_res["raw_results"], theme=theme)
            st.plotly_chart(fig_served, use_container_width=True)
        with chart_row3_c2:
            fig_dist = plot_wait_time_distribution(b_res["raw_results"], theme=theme)
            st.plotly_chart(fig_dist, use_container_width=True)

    # 2D Floor-wise Passenger Demand Heatmap
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🗺️ 2D Floor-to-Floor Passenger Flow Heatmap")
    st.caption("Visualizes passenger origin-to-destination volume matrix generated from actual passenger trips.")
    fig_heatmap = plot_passenger_demand_heatmap(engine.demand_matrix, theme=theme)
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # Data Export Section
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("💾 Export Simulation Data & Reports")
    exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)

    pax_df = ReportGenerator.export_passengers_df(engine.all_passengers, engine.current_time)
    elev_df = ReportGenerator.export_elevators_df(engine.building.elevators)
    json_report = ReportGenerator.generate_json_report(engine.get_summary_metrics(), config.to_dict())

    comp_df_to_export = st.session_state.benchmark_results["comparison_df"] if st.session_state.benchmark_results else pd.DataFrame()
    html_executive_report = ReportGenerator.generate_executive_html_report(
        summary_metrics=engine.get_summary_metrics(),
        config_dict=config.to_dict(),
        elevators_telemetry=[e.to_dict() for e in engine.building.elevators],
        comparison_df=comp_df_to_export,
    )

    with exp_col1:
        st.download_button(
            label="📥 Export Passengers (CSV)",
            data=pax_df.to_csv(index=False),
            file_name=f"passenger_trips_sim_t{int(engine.current_time)}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with exp_col2:
        st.download_button(
            label="📥 Export Telemetry (CSV)",
            data=elev_df.to_csv(index=False),
            file_name=f"elevator_telemetry_sim_t{int(engine.current_time)}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with exp_col3:
        st.download_button(
            label="📥 Full Audit (JSON)",
            data=json_report,
            file_name=f"elevator_dispatch_report_t{int(engine.current_time)}.json",
            mime="application/json",
            use_container_width=True,
        )
    with exp_col4:
        st.download_button(
            label="📄 Executive Report (PDF/HTML)",
            data=html_executive_report,
            file_name=f"elevator_executive_report_t{int(engine.current_time)}.html",
            mime="text/html",
            use_container_width=True,
        )


# =========================================================================
# TAB 6: SYSTEM SETTINGS & CONFIGURATION
# =========================================================================
with tabs[5]:
    st.subheader("⚙️ System Architecture & Mechanical Dynamics")
    st.caption("Configure the physical parameters of the building, elevator mechanical dynamics, and safety evacuation.")

    with st.form("system_settings_form_v2"):
        set_col1, set_col2 = st.columns(2)

        with set_col1:
            st.markdown("#### Building & Mechanical Specifications")
            num_floors_input = st.slider("Number of Floors", min_value=5, max_value=25, value=config.num_floors)
            num_elevators_input = st.slider("Number of Elevators (Shafts)", min_value=2, max_value=8, value=config.num_elevators)
            capacity_input = st.slider("Elevator Cabin Capacity (Persons)", min_value=4, max_value=16, value=config.elevator_capacity)
            speed_input = st.slider("Elevator Speed (Floors/Second)", min_value=0.5, max_value=2.5, value=config.elevator_speed, step=0.1)
            door_time_input = st.slider("Door Operation Time (Seconds)", min_value=1.0, max_value=4.0, value=config.door_operation_time, step=0.5)

        with set_col2:
            st.markdown("#### Traffic Dynamics & Safety Settings")
            arrival_rate_input = st.slider("Peak Passenger Arrival Rate (pax/s)", min_value=0.05, max_value=1.5, value=config.passenger_arrival_rate, step=0.05)
            prio_ratio_input = st.slider("Priority / VIP Passenger Ratio (%)", min_value=0, max_value=30, value=int(config.priority_passenger_ratio * 100), step=1)
            enable_demand_pred = st.checkbox("Enable Intelligent Demand Prediction & Repositioning", value=config.enable_demand_prediction)
            safe_floor_input = st.number_input("Designated Safe Evacuation Floor", min_value=0, max_value=num_floors_input - 1, value=config.safe_evacuation_floor)
            seed_input = st.number_input("Default Random Seed", value=config.random_seed, step=1)

        if st.form_submit_button("💾 Apply Settings and Reset Simulation", type="primary", use_container_width=True):
            config.num_floors = num_floors_input
            config.num_elevators = num_elevators_input
            config.elevator_capacity = capacity_input
            config.elevator_speed = speed_input
            config.door_operation_time = door_time_input
            config.passenger_arrival_rate = arrival_rate_input
            config.priority_passenger_ratio = prio_ratio_input / 100.0
            config.enable_demand_prediction = enable_demand_pred
            config.safe_evacuation_floor = int(safe_floor_input)
            config.random_seed = int(seed_input)

            dispatch_agent = DispatchAgent(algorithm=st.session_state.algorithm)
            engine = SimulationEngine(config=config, dispatch_agent=dispatch_agent)
            st.session_state.engine = engine
            st.session_state.benchmark_results = None
            st.success("Building specifications updated! Simulation reset.")
            st.rerun()
