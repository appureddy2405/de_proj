"""Streamlit dashboard over the dbt marts.   Run:  streamlit run dashboard/app.py"""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import psycopg
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config  # noqa: E402

st.set_page_config(page_title="LoL ranked analytics", layout="wide")


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    with psycopg.connect(config.warehouse_dsn()) as conn:
        cur = conn.execute(sql)
        df = pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])
    for col in df.columns:  # Postgres numeric -> Decimal; charts need floats
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    return df


st.title("League of Legends - ranked analytics")

try:
    regions = query("select * from marts.mart_region_summary")
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not read the marts. Run `python -m pipeline.cli run-all` first.\n\n{exc}")
    st.stop()

total, detailed = int(regions["matches"].sum()), int(regions["matches_with_detail"].sum())
c1, c2, c3, c4 = st.columns(4)
c1.metric("Matches scraped", f"{total:,}")
c2.metric("With participant detail", f"{detailed:,}")
c3.metric("Detail coverage", f"{detailed / total:.1%}" if total else "n/a")
c4.metric("Regions", regions["region"].nunique())
if total and detailed / total < 0.5:
    st.warning("Most matches have no participant rows loaded, so champion and item stats cover only a subset.")

tab_champs, tab_items, tab_regions, tab_quality = st.tabs(["Champions", "Items", "Regions", "Data quality"])

with tab_champs:
    champs = query("select * from marts.mart_champion_performance")
    f1, f2, f3, f4 = st.columns(4)
    patch = f1.selectbox("Patch", sorted(champs["patch_version"].unique()))
    queue = f2.selectbox("Queue", sorted(champs["queue_type"].unique()))
    role = f3.selectbox("Role", ["All", *sorted(champs["position"].dropna().unique())])
    min_games = f4.slider("Minimum games", 1, 100, 30)
    view = champs[(champs["patch_version"] == patch) & (champs["queue_type"] == queue) & (champs["games"] >= min_games)]
    if role != "All":
        view = view[view["position"] == role]
    if view.empty:
        st.info("No champions meet the minimum-games filter. Lower it to see more.")
    else:
        top = view.sort_values("win_rate", ascending=False).head(15)
        st.bar_chart(top.set_index("champion_name")["win_rate"])
        st.dataframe(
            view.sort_values("games", ascending=False)[
                ["champion_name", "position", "games", "win_rate", "pick_rate", "avg_kda",
                 "avg_gold_per_min", "avg_damage_per_min"]
            ],
            width="stretch", hide_index=True,
        )

with tab_items:
    items = query("select * from marts.mart_item_popularity")
    if items.empty:
        st.info("No item data.")
    else:
        top_items = items.groupby("item_name", as_index=False).agg(builds=("builds", "sum")).nlargest(20, "builds")
        st.bar_chart(top_items.set_index("item_name")["builds"])

with tab_regions:
    by_region = regions.groupby("region", as_index=False).agg(
        matches=("matches", "sum"), detail=("matches_with_detail", "sum"), avg_minutes=("avg_duration_minutes", "mean")
    )
    st.bar_chart(by_region.set_index("region")[["matches", "detail"]])
    st.dataframe(regions, width="stretch", hide_index=True)

with tab_quality:
    report_path = config.REPORT_DIR / "quality_warehouse.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())
        st.caption(f"Last run: {report['ran_at']}  |  {report['summary']}")
        st.dataframe(pd.DataFrame(report["checks"])[["id", "severity", "status", "violations", "description"]],
                     width="stretch", hide_index=True)
    else:
        st.info("No quality report yet. Run `python -m pipeline.cli check-warehouse`.")
