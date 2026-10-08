"""
CLARIUS Backend - Dashboard Intelligence Service

Dynamically profiles DuckDB business datasets, calculates aggregate KPIs,
evaluates data quality, and constructs ECharts visualizations from actual schema.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import duckdb

from app.infrastructure.database import db_manager

logger = logging.getLogger("clarius.dashboard.intelligence")

SYSTEM_TABLES = {
    "users", "organizations", "data_sources", "queries", "dashboards", 
    "reports", "documents", "audit_logs", "roles", "permissions", 
    "user_roles", "role_permissions", "role_hierarchy", "access_scopes", 
    "user_access_scopes", "branches", "departments", "jobs",
    "conversations", "conversation_messages", "dataset_versions",
    "document_versions", "sync_history"
}


class DashboardIntelligenceService:
    """Service handling dynamic metadata-driven business intelligence dashboard generation."""

    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or db_manager.get_connection()

    def get_overview(self, target_dataset: Optional[str] = None) -> Dict[str, Any]:
        """Generate full data-driven dashboard payload for all or a target dataset."""
        all_tables = self._get_business_tables()

        if not all_tables:
            return {
                "summary": {
                    "total_datasets": 0,
                    "total_records": 0,
                    "average_quality_score": 100.0,
                    "last_updated": datetime.utcnow().isoformat()
                },
                "datasets": [],
                "kpis": [],
                "quality": [],
                "visualizations": []
            }

        filtered_tables = [t for t in all_tables if t == target_dataset] if target_dataset else all_tables

        datasets_meta = []
        kpis = []
        quality_metrics = []
        visualizations = []
        total_records = 0
        quality_scores = []

        for tname in filtered_tables:
            meta = self._profile_table(tname)
            if meta:
                datasets_meta.append(meta)
                total_records += meta["rows"]
                quality_scores.append(meta["quality_score"])
                
                kpis.extend(meta["kpis"])
                quality_metrics.append(meta["quality_detail"])
                if meta["visualization"]:
                    visualizations.append(meta["visualization"])

        avg_quality = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 100.0

        return {
            "summary": {
                "total_datasets": len(all_tables),
                "total_records": total_records,
                "average_quality_score": avg_quality,
                "last_updated": datetime.utcnow().isoformat()
            },
            "datasets": datasets_meta,
            "kpis": kpis,
            "quality": quality_metrics,
            "visualizations": visualizations
        }

    def _get_business_tables(self) -> List[str]:
        """Fetch all user business dataset tables in main schema."""
        try:
            rows = self.conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
            return [r[0] for r in rows if r[0] not in SYSTEM_TABLES]
        except Exception as e:
            logger.error(f"Error fetching business tables: {e}")
            return []

    def _profile_table(self, tname: str) -> Optional[Dict[str, Any]]:
        """Profile a single table's columns, row counts, KPIs, quality, and ECharts specs."""
        try:
            cols_res = self.conn.execute(f"DESCRIBE {tname}").fetchall()
            if not cols_res:
                return None

            col_defs = []
            numeric_cols = []
            date_cols = []
            category_cols = []

            for col_info in cols_res:
                cname = col_info[0]
                ctype = str(col_info[1]).upper()
                col_defs.append({"name": cname, "type": ctype})

                clower = cname.lower()
                is_id = clower.endswith("_id") or clower == "id" or clower.endswith("code") or clower.endswith("_key")

                monetary_keywords = ["price", "sales", "amount", "revenue", "cost", "inr", "fee", "charge", "val", "total", "qty", "quantity"]
                if (("INT" in ctype or "DOUBLE" in ctype or "FLOAT" in ctype or "DECIMAL" in ctype or "NUMERIC" in ctype) or any(kw in clower for kw in monetary_keywords)) and not is_id:
                    numeric_cols.append(cname)
                elif "TIMESTAMP" in ctype or "DATE" in ctype or "time" in clower or "date" in clower or "year" in clower or "month" in clower:
                    date_cols.append(cname)
                elif "VARCHAR" in ctype and not is_id:
                    category_cols.append(cname)

            # Row count
            row_count_res = self.conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()
            row_count = row_count_res[0] if row_count_res else 0

            # Quality calculation
            quality_score = 100.0
            null_count = 0
            if row_count > 0 and len(cols_res) > 0:
                sampled_cols = [c[0] for c in cols_res[:10]]
                null_exprs = " + ".join([f"COUNT(CASE WHEN {c} IS NULL THEN 1 END)" for c in sampled_cols])
                try:
                    null_res = self.conn.execute(f"SELECT ({null_exprs}) FROM {tname}").fetchone()
                    null_count = null_res[0] if null_res and null_res[0] else 0
                    null_rate = null_count / (row_count * len(sampled_cols))
                    quality_score = max(50.0, round(100.0 - (null_rate * 100.0), 1))
                except Exception:
                    quality_score = 95.0

            # Generate Dynamic KPIs
            kpis = []
            
            # KPI 1: Record Count
            kpis.append({
                "id": f"kpi_{tname}_count",
                "label": f"Total {tname.replace('_', ' ').title()}",
                "value": f"{row_count:,}",
                "unit": "Records",
                "subtitle": f"Row count in dataset '{tname}'",
                "dataset": tname,
                "source_column": "COUNT(*)"
            })

            # KPI 2 & 3: Numerical Sums / Averages
            for num_col in numeric_cols[:4]:
                try:
                    clean_expr = f"COALESCE(TRY_CAST(REGEXP_REPLACE(CAST({num_col} AS VARCHAR), '[^0-9.]', '', 'g') AS DOUBLE), 0)"
                    stats_res = self.conn.execute(f"SELECT SUM({clean_expr}), AVG({clean_expr}) FROM {tname} WHERE {clean_expr} > 0").fetchone()
                    if stats_res and stats_res[0] is not None and stats_res[0] > 0:
                        sum_val = float(stats_res[0])
                        avg_val = float(stats_res[1]) if stats_res[1] is not None else 0.0

                        col_lower = num_col.lower()
                        is_inr = any(kw in col_lower or kw in tname.lower() for kw in ["inr", "rs", "rupee", "₹", "india"])
                        curr_symbol = "₹" if is_inr else "$"
                        is_monetary = any(kw in col_lower for kw in ["price", "sales", "amount", "revenue", "cost", "inr", "fee", "charge", "val"])

                        formatted_sum = f"{curr_symbol}{sum_val:,.2f}" if is_monetary else f"{sum_val:,.1f}"
                        formatted_avg = f"{curr_symbol}{avg_val:,.2f}" if is_monetary else f"{avg_val:,.1f}"

                        kpis.append({
                            "id": f"kpi_{tname}_{num_col}_sum",
                            "label": f"Total {num_col.replace('_', ' ').title()}",
                            "value": formatted_sum,
                            "unit": num_col.replace('_', ' ').title(),
                            "subtitle": f"Sum total of column '{num_col}'",
                            "dataset": tname,
                            "source_column": num_col
                        })

                        kpis.append({
                            "id": f"kpi_{tname}_{num_col}_avg",
                            "label": f"Average {num_col.replace('_', ' ').title()}",
                            "value": formatted_avg,
                            "unit": f"Avg / {num_col.replace('_', ' ').title()}",
                            "subtitle": f"Average value of column '{num_col}'",
                            "dataset": tname,
                            "source_column": num_col
                        })
                except Exception as e:
                    logger.warning(f"Error computing KPI for {tname}.{num_col}: {e}")

            # Generate ECharts Visualization if appropriate
            visualization = None

            # Case A: Time Series (Date column + Numeric column)
            if date_cols and numeric_cols:
                dcol = date_cols[0]
                ncol = numeric_cols[0]
                try:
                    ts_res = self.conn.execute(f"""
                        SELECT CAST({dcol} AS VARCHAR) as d_val, SUM({ncol}) as n_val
                        FROM {tname}
                        WHERE {dcol} IS NOT NULL AND {ncol} IS NOT NULL
                        GROUP BY 1
                        ORDER BY 1
                        LIMIT 12
                    """).fetchall()

                    if len(ts_res) >= 2:
                        x_data = [str(r[0])[:10] for r in ts_res]
                        y_data = [round(float(r[1]), 2) for r in ts_res]

                        visualization = {
                            "id": f"viz_{tname}_trend",
                            "title": f"{ncol.replace('_', ' ').title()} Trend Over Time",
                            "type": "line",
                            "dataset": tname,
                            "chart_options": {
                                "title": {"text": f"{tname.replace('_', ' ').title()} - {ncol.replace('_', ' ').title()} Trend", "textStyle": {"color": "#f8fafc", "fontSize": 14}},
                                "tooltip": {"trigger": "axis"},
                                "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
                                "xAxis": {"type": "category", "data": x_data, "axisLine": {"lineStyle": {"color": "#64748b"}}},
                                "yAxis": {"type": "value", "axisLine": {"lineStyle": {"color": "#64748b"}}, "splitLine": {"lineStyle": {"color": "#1e293b"}}},
                                "series": [{
                                    "name": ncol.replace('_', ' ').title(),
                                    "type": "line",
                                    "smooth": True,
                                    "data": y_data,
                                    "itemStyle": {"color": "#3b82f6"},
                                    "areaStyle": {"color": "rgba(59, 130, 246, 0.15)"}
                                }]
                            }
                        }
                except Exception as e:
                    logger.warning(f"Error creating time series chart for {tname}: {e}")

            # Case B: Categorical Top Breakdown (Category column + Numeric column)
            if not visualization and category_cols and numeric_cols:
                ccol = category_cols[0]
                ncol = numeric_cols[0]
                try:
                    cat_res = self.conn.execute(f"""
                        SELECT CAST({ccol} AS VARCHAR) as c_val, SUM({ncol}) as n_val
                        FROM {tname}
                        WHERE {ccol} IS NOT NULL AND {ncol} IS NOT NULL
                        GROUP BY 1
                        ORDER BY 2 DESC
                        LIMIT 6
                    """).fetchall()

                    if len(cat_res) >= 2:
                        x_data = [str(r[0]) for r in cat_res]
                        y_data = [round(float(r[1]), 2) for r in cat_res]

                        visualization = {
                            "id": f"viz_{tname}_breakdown",
                            "title": f"Top {ccol.replace('_', ' ').title()} by {ncol.replace('_', ' ').title()}",
                            "type": "bar",
                            "dataset": tname,
                            "chart_options": {
                                "title": {"text": f"Top {ccol.replace('_', ' ').title()} by {ncol.replace('_', ' ').title()}", "textStyle": {"color": "#f8fafc", "fontSize": 14}},
                                "tooltip": {"trigger": "item"},
                                "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
                                "xAxis": {"type": "category", "data": x_data, "axisLine": {"lineStyle": {"color": "#64748b"}}},
                                "yAxis": {"type": "value", "axisLine": {"lineStyle": {"color": "#64748b"}}, "splitLine": {"lineStyle": {"color": "#1e293b"}}},
                                "series": [{
                                    "name": ncol.replace('_', ' ').title(),
                                    "type": "bar",
                                    "data": y_data,
                                    "itemStyle": {"color": "#10b981", "borderRadius": [4, 4, 0, 0]}
                                }]
                            }
                        }
                except Exception as e:
                    logger.warning(f"Error creating bar breakdown chart for {tname}: {e}")

            return {
                "name": tname,
                "business_name": tname.replace("_", " ").title(),
                "description": f"Enterprise dataset '{tname}' registered in DuckDB.",
                "rows": row_count,
                "columns": len(cols_res),
                "quality_score": quality_score,
                "health": "Healthy" if quality_score >= 80 else "Attention Required",
                "kpis": kpis,
                "quality_detail": {
                    "dataset": tname,
                    "quality_score": quality_score,
                    "total_rows": row_count,
                    "sampled_nulls": null_count,
                    "column_count": len(cols_res)
                },
                "visualization": visualization
            }
        except Exception as e:
            logger.error(f"Failed to profile table '{tname}': {e}")
            return None


dashboard_intelligence_service = DashboardIntelligenceService()
