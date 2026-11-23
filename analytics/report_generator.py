"""
Report Generator and Data Exporter.
Serializes simulation results, passenger logs, elevator telemetry,
and comparative benchmarks to CSV, JSON, and print-ready executive PDF/HTML reports.
"""

from typing import List, Dict, Any, Optional
import json
import pandas as pd
from agents.passenger_agent import Passenger
from agents.elevator_agent import ElevatorAgent


class ReportGenerator:
    """Exports structured simulation records for analysis, archival, and reporting."""

    @staticmethod
    def export_passengers_df(passengers: List[Passenger], current_time: float) -> pd.DataFrame:
        """Converts passenger records to a clean DataFrame."""
        if not passengers:
            return pd.DataFrame(columns=[
                "id", "pickup_floor", "destination_floor", "direction",
                "request_time", "board_time", "alight_time", "wait_time",
                "travel_time", "total_journey_time", "is_priority", "status", "assigned_elevator_id"
            ])
        data = [p.to_dict(current_time) for p in passengers]
        return pd.DataFrame(data)

    @staticmethod
    def export_elevators_df(elevators: List[ElevatorAgent]) -> pd.DataFrame:
        """Converts elevator telemetry to a DataFrame."""
        if not elevators:
            return pd.DataFrame()
        data = [e.to_dict() for e in elevators]
        return pd.DataFrame(data)

    @staticmethod
    def generate_json_report(summary_metrics: Dict[str, Any], config_dict: Dict[str, Any]) -> str:
        """Produces a unified JSON export containing configuration and summary metrics."""
        payload = {
            "simulation_config": config_dict,
            "performance_metrics": summary_metrics,
        }
        return json.dumps(payload, indent=2)

    @staticmethod
    def generate_executive_html_report(
        summary_metrics: Dict[str, Any],
        config_dict: Dict[str, Any],
        elevators_telemetry: List[Dict[str, Any]],
        comparison_df: Optional[pd.DataFrame] = None,
    ) -> str:
        """
        Generates a publication-grade, print-ready HTML/PDF executive summary report
        with embedded CSS formatting optimized for browser PDF printing.
        """
        elev_rows = []
        for e in elevators_telemetry:
            elev_rows.append(f"""
            <tr>
                <td><strong>Elevator #{e['elevator_id']}</strong></td>
                <td>Floor {e['current_floor']}</td>
                <td>{e['direction']}</td>
                <td>{e['passenger_count']}/{e['capacity']}</td>
                <td>{e['total_passengers_served']}</td>
                <td>{e['total_distance_floors']}</td>
                <td>{e['total_energy_kwh']:.4f} kWh</td>
            </tr>
            """)
        elev_rows_str = "".join(elev_rows)

        comp_table_html = ""
        if comparison_df is not None and not comparison_df.empty:
            comp_table_html = f"""
            <h3>Algorithm Benchmark Comparison</h3>
            {comparison_df.to_html(classes="report-table", index=False)}
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <title>Elevator System Performance Report</title>
        <style>
            @media print {{
                body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                .no-print {{ display: none; }}
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                color: #1E293B;
                background: #FFFFFF;
                margin: 0;
                padding: 30px;
                line-height: 1.5;
            }}
            .header {{
                border-bottom: 3px solid #0284C7;
                padding-bottom: 16px;
                margin-bottom: 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .title {{
                font-size: 22px;
                font-weight: 800;
                color: #0F172A;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .subtitle {{
                font-size: 13px;
                color: #64748B;
            }}
            .kpi-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }}
            .kpi-card {{
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 14px;
                border-left: 4px solid #0284C7;
            }}
            .kpi-label {{
                font-size: 11px;
                font-weight: 700;
                color: #64748B;
                text-transform: uppercase;
            }}
            .kpi-value {{
                font-size: 22px;
                font-weight: 800;
                color: #0F172A;
                margin-top: 4px;
            }}
            .report-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 24px;
                font-size: 13px;
            }}
            .report-table th {{
                background: #F1F5F9;
                color: #334155;
                font-weight: 700;
                text-align: left;
                padding: 10px 12px;
                border-bottom: 2px solid #CBD5E1;
            }}
            .report-table td {{
                padding: 9px 12px;
                border-bottom: 1px solid #E2E8F0;
            }}
            .footer {{
                margin-top: 40px;
                border-top: 1px solid #E2E8F0;
                padding-top: 12px;
                font-size: 11px;
                color: #94A3B8;
                text-align: center;
            }}
            .print-btn {{
                background: #0284C7;
                color: #FFFFFF;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
                cursor: pointer;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <div>
                    <div class="title">🏢 Intelligent Elevator Dispatch System</div>
                    <div class="subtitle">Official Executive Performance & Telemetry Audit Report</div>
                </div>
                <div class="no-print">
                    <button class="print-btn" onclick="window.print()">🖨️ Print / Save to PDF</button>
                </div>
            </div>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">Simulation Time</div>
                    <div class="kpi-value">{summary_metrics.get('current_time_sec', 0)}s</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Average Wait Time</div>
                    <div class="kpi-value">{summary_metrics.get('avg_wait_time_sec', 0):.1f}s</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Passengers Served</div>
                    <div class="kpi-value">{summary_metrics.get('total_served', 0)}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Total Energy</div>
                    <div class="kpi-value">{summary_metrics.get('total_energy_kwh', 0):.3f} kWh</div>
                </div>
            </div>

            <h3>Elevator Fleet Telemetry</h3>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Car</th>
                        <th>Position</th>
                        <th>Direction</th>
                        <th>Load</th>
                        <th>Served</th>
                        <th>Mileage</th>
                        <th>Energy Consumed</th>
                    </tr>
                </thead>
                <tbody>
                    {elev_rows_str}
                </tbody>
            </table>

            {comp_table_html}

            <div class="footer">
                Generated by Intelligent Elevator Group Dispatch Agent System • Confidential & Proprietary
            </div>
        </body>
        </html>
        """
        return html
