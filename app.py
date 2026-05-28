from __future__ import annotations

import json
import os
import shutil
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "rawdata.csv"
CUTS_PATH = BASE_DIR / "budget_cuts.json"
CUTS_BACKUP_PATH = BASE_DIR / "budget_cuts.json.bak"

MONEY_COL = "Amount $000"
ACTIVE_YEARS = [2027]
ACTIVE_AMOUNT_TYPES = ["Main Estimates"]
ID_COLS = [
    "Department",
    "Vote",
    "App ID",
    "Parent ID",
    "Appropriation Name",
    "Category Name",
    "Year",
    "Amount Type",
    "Periodicity",
]


st.set_page_config(
    page_title="Budget 2026 Cutter",
    page_icon=":",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --accent: #22c7a9;
            --accent-soft: rgba(34, 199, 169, .16);
            --gold: #f2b84b;
            --danger: #ff6b6b;
            --ink: #eef6f8;
            --muted: #a8bac5;
            --line: rgba(214, 233, 238, .18);
            --panel: #152535;
            --panel-2: #1c3143;
            --deep: #0b1118;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(34, 199, 169, .16), transparent 28rem),
                linear-gradient(180deg, #111d29 0%, #0b1118 52%, #101822 100%);
            color: var(--ink);
        }
        .block-container {
            padding-top: 1.8rem;
        }
        [data-testid="stSidebar"] {
            background: #07101a;
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] * {
            color: #eef6f8;
        }
        [data-testid="stSidebar"] .stButton button {
            background: #ef4444;
            color: #ffffff;
            border: 0;
        }
        h1, h2, h3 {
            letter-spacing: 0;
            color: #f7fbfc;
        }
        p, span, label, div {
            color: inherit;
        }
        .hero {
            border: 1px solid var(--line);
            background:
                linear-gradient(135deg, rgba(34, 199, 169, .18), rgba(242, 184, 75, .09)),
                #132233;
            padding: 1.4rem 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            box-shadow: 0 18px 48px rgba(0, 0, 0, .22);
        }
        .hero h1 {
            margin: 0 0 .35rem 0;
            font-size: 2.05rem;
            line-height: 1.15;
        }
        .hero p {
            color: var(--muted);
            margin: 0;
            font-size: 1rem;
        }
        .section-note {
            color: var(--muted);
            font-size: .94rem;
            margin-top: -.3rem;
            margin-bottom: .7rem;
        }
        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, #1a2c3e, #132332);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: .85rem 1rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, .20);
        }
        div[data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: linear-gradient(180deg, #17293a, #111f2c);
            box-shadow: 0 10px 28px rgba(0, 0, 0, .20);
            overflow: hidden;
        }
        div[data-testid="stExpander"] summary {
            background: #20384d;
            border-bottom: 1px solid var(--line);
        }
        div[data-testid="stExpander"] summary p {
            color: #f7fbfc;
            font-weight: 700;
        }
        div[data-testid="stDataFrame"], div[data-testid="stTable"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
        }
        input, textarea, select {
            color: #f7fbfc !important;
        }
        .stButton button, .stDownloadButton button {
            border-radius: 6px;
            border: 1px solid var(--accent);
            color: #eafffb;
            background: rgba(34, 199, 169, .12);
            min-height: 2.4rem;
        }
        .stButton button:hover, .stDownloadButton button:hover {
            border-color: #6ff0dd;
            background: var(--accent-soft);
            color: #ffffff;
        }
        .cut-shell {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: .9rem 1rem;
            background: rgba(7, 16, 26, .38);
            margin-bottom: .8rem;
        }
        .cut-title {
            font-size: 1rem;
            font-weight: 800;
            color: #f7fbfc;
            margin-bottom: .25rem;
        }
        .cut-meta {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-bottom: .55rem;
        }
        .chip {
            display: inline-block;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, .06);
            color: #dcecf0;
            border-radius: 999px;
            padding: .18rem .55rem;
            font-size: .78rem;
        }
        .scope-box {
            background: rgba(255, 255, 255, .055);
            border-left: 3px solid var(--gold);
            color: #d8e6eb;
            padding: .65rem .8rem;
            border-radius: 6px;
            line-height: 1.45;
        }
        .dept-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: .8rem .9rem;
            background: linear-gradient(180deg, rgba(28, 49, 67, .94), rgba(15, 28, 40, .94));
            min-height: 8.1rem;
            margin-bottom: .55rem;
            box-shadow: 0 8px 22px rgba(0, 0, 0, .18);
        }
        .dept-card-selected {
            border-color: var(--accent);
            box-shadow: 0 0 0 1px rgba(34, 199, 169, .38), 0 10px 30px rgba(0, 0, 0, .24);
        }
        .dept-name {
            color: #f7fbfc;
            font-weight: 800;
            line-height: 1.25;
            margin-bottom: .45rem;
        }
        .dept-stats {
            color: var(--muted);
            font-size: .84rem;
            line-height: 1.45;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_budget_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding="cp1252").reset_index(names="source_row")
    df[MONEY_COL] = pd.to_numeric(df[MONEY_COL], errors="coerce").fillna(0)
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df = df[df["Year"].isin(ACTIVE_YEARS)].copy()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].fillna("").astype(str)
    df = df[df["Amount Type"].isin(ACTIVE_AMOUNT_TYPES)].copy()
    df["line_item_id"] = df[["source_row", *ID_COLS]].astype(str).agg(" | ".join, axis=1)
    df["amount_dollars"] = df[MONEY_COL] * 1000
    return df


def load_cuts() -> dict[str, dict[str, float | str]]:
    if not CUTS_PATH.exists():
        if not CUTS_BACKUP_PATH.exists():
            return {}
        path = CUTS_BACKUP_PATH
    else:
        path = CUTS_PATH
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        if path == CUTS_PATH and CUTS_BACKUP_PATH.exists():
            try:
                with CUTS_BACKUP_PATH.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}


def save_cuts(cuts: dict[str, dict[str, float | str]]) -> None:
    tmp_path = CUTS_PATH.with_suffix(".json.tmp")
    if CUTS_PATH.exists():
        shutil.copy2(CUTS_PATH, CUTS_BACKUP_PATH)
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(cuts, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, CUTS_PATH)


def persist_line_cut(cuts: dict[str, dict[str, float | str]], row: pd.Series, cut_percent: float) -> None:
    set_line_cut(cuts, row, cut_percent)
    save_cuts(cuts)


def fmt_money(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    if amount >= 1_000_000_000:
        return f"{sign}${amount / 1_000_000_000:.2f}b"
    if amount >= 1_000_000:
        return f"{sign}${amount / 1_000_000:.2f}m"
    if amount >= 1_000:
        return f"{sign}${amount / 1_000:.1f}k"
    return f"{sign}${amount:,.0f}"


def h(value: object) -> str:
    return escape(str(value), quote=True)


def set_line_cut(cuts: dict[str, dict[str, float | str]], row: pd.Series, cut_percent: float) -> None:
    line_id = row["line_item_id"]
    cut_percent = round(float(cut_percent), 2)
    if cut_percent <= 0:
        cuts.pop(line_id, None)
        return
    amount = float(row["amount_dollars"])
    cuts[line_id] = {
        "cut_percent": cut_percent,
        "department": row["Department"],
        "vote": row["Vote"],
        "appropriation_name": row["Appropriation Name"],
        "category_name": row["Category Name"],
        "year": int(row["Year"]),
        "amount_type": row["Amount Type"],
        "original_dollars": amount,
        "savings_dollars": amount * cut_percent / 100,
    }


def set_department_cut(cuts: dict[str, dict[str, float | str]], rows: pd.DataFrame, cut_percent: float) -> None:
    for _, row in rows.iterrows():
        set_line_cut(cuts, row, cut_percent)
    save_cuts(cuts)


def apply_cuts(df: pd.DataFrame, cuts: dict[str, dict[str, float | str]]) -> pd.DataFrame:
    out = df.copy()
    out["cut_percent"] = out["line_item_id"].map(lambda x: float(cuts.get(x, {}).get("cut_percent", 0)))
    out["cut_dollars"] = out["amount_dollars"] * out["cut_percent"] / 100
    out["remaining_dollars"] = out["amount_dollars"] - out["cut_dollars"]
    return out


def prune_inactive_cuts(cuts: dict[str, dict[str, float | str]], df: pd.DataFrame) -> dict[str, dict[str, float | str]]:
    active_ids = set(df["line_item_id"])
    cleaned = {line_id: cut for line_id, cut in cuts.items() if line_id in active_ids}
    if len(cleaned) != len(cuts):
        save_cuts(cleaned)
    return cleaned


def filtered_options(df: pd.DataFrame, column: str) -> list[str]:
    return sorted(x for x in df[column].dropna().unique().tolist() if str(x).strip())


def metric_row(df: pd.DataFrame) -> None:
    total_budget = df["amount_dollars"].sum()
    total_savings = df["cut_dollars"].sum()
    affected = int((df["cut_percent"] > 0).sum())
    avg_cut = (total_savings / total_budget * 100) if total_budget else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Visible budget", fmt_money(total_budget))
    c2.metric("Savings from cuts", fmt_money(total_savings))
    c3.metric("Remaining", fmt_money(total_budget - total_savings))
    c4.metric("Average cut", f"{avg_cut:.2f}%", f"{affected:,} line items touched")


def page_hero(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def overview_page(df: pd.DataFrame) -> None:
    page_hero(
        "Budget 2027 Cutter",
        "Concrete working set: 2027 Main Estimates only. Apply granular cuts and track savings as they autosave.",
    )
    metric_row(df)

    chart_df = (
        df.groupby("Vote", as_index=False)
        .agg(budget=("amount_dollars", "sum"), savings=("cut_dollars", "sum"))
        .sort_values("budget", ascending=False)
        .head(12)
        .set_index("Vote")
    )
    st.subheader("Largest Votes")
    st.markdown('<div class="section-note">Top votes by Main Estimates budget, with savings overlaid when cuts exist.</div>', unsafe_allow_html=True)
    st.bar_chart(chart_df[["budget", "savings"]])

    st.subheader("Biggest Savings by Vote")
    vote_summary = (
        df.groupby("Vote", as_index=False)
        .agg(
            budget=("amount_dollars", "sum"),
            savings=("cut_dollars", "sum"),
            lines=("line_item_id", "count"),
        )
        .assign(cut_rate=lambda x: x["savings"] / x["budget"] * 100)
        .sort_values("savings", ascending=False)
    )
    st.dataframe(
        vote_summary.assign(
            budget=vote_summary["budget"].map(fmt_money),
            savings=vote_summary["savings"].map(fmt_money),
            cut_rate=vote_summary["cut_rate"].map(lambda x: f"{x:.2f}%"),
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Biggest Savings by Department")
    dept_summary = (
        df.groupby("Department", as_index=False)
        .agg(
            budget=("amount_dollars", "sum"),
            savings=("cut_dollars", "sum"),
            lines=("line_item_id", "count"),
        )
        .assign(cut_rate=lambda x: x["savings"] / x["budget"] * 100)
        .sort_values("savings", ascending=False)
    )
    st.dataframe(
        dept_summary.assign(
            budget=dept_summary["budget"].map(fmt_money),
            savings=dept_summary["savings"].map(fmt_money),
            cut_rate=dept_summary["cut_rate"].map(lambda x: f"{x:.2f}%"),
        ),
        width="stretch",
        hide_index=True,
    )


def line_item_editor(df: pd.DataFrame, cuts: dict[str, dict[str, float | str]]) -> None:
    st.subheader("Line Item Cuts")
    st.markdown(
        '<div class="section-note">Open a line item to inspect its scope and apply a precise cut. Every change is saved to disk immediately.</div>',
        unsafe_allow_html=True,
    )

    search = st.text_input("Search line items", placeholder="Search name, category, scope, classification, portfolio...")
    if search:
        mask = pd.Series(False, index=df.index)
        for col in [
            "Appropriation Name",
            "Category Name",
            "Current Scope",
            "Functional Classification",
            "Portfolio Name",
            "Appropriation or Category Type",
        ]:
            mask |= df[col].str.contains(search, case=False, na=False)
        df = df[mask]

    st.info("Using concrete budget figures only: 2027 Main Estimates. Estimated Actual rows are excluded.")

    df = df.sort_values(["Year", "Appropriation Name", "Category Name"])
    metric_row(df)

    nav1, nav2 = st.columns([1, 1])
    page_size = nav1.select_slider("Rows shown", options=[25, 50, 100, 250], value=50)
    total_pages = max(1, (len(df) - 1) // page_size + 1)
    page = nav2.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
    start = (int(page) - 1) * page_size
    end = start + page_size
    st.caption(f"Showing rows {start + 1:,}-{min(end, len(df)):,} of {len(df):,}. Use filters above to narrow the editor.")
    df = df.iloc[start:end]

    for _, row in df.iterrows():
        line_id = row["line_item_id"]
        current_cut = float(cuts.get(line_id, {}).get("cut_percent", 0))
        title = row["Appropriation Name"]
        category = row["Category Name"]
        amount = float(row["amount_dollars"])
        year = row["Year"]
        amount_type = row["Amount Type"]
        group_type = row["Group Type"]
        scope = row["Current Scope"]
        classification = row["Functional Classification"]
        appropriation_type = row["Appropriation or Category Type"]

        label = f"{fmt_money(amount)} - {title} - {category} - {year} {amount_type}"
        with st.expander(label, expanded=current_cut > 0):
            savings = amount * current_cut / 100
            remaining = amount - savings
            st.markdown(
                f"""
                <div class="cut-shell">
                    <div class="cut-title">{h(title)}</div>
                    <div class="cut-meta">
                        <span class="chip">{h(category)}</span>
                        <span class="chip">{h(year)} {h(amount_type)}</span>
                        <span class="chip">{h(group_type)}</span>
                        <span class="chip">{h(appropriation_type)}</span>
                        <span class="chip">{h(classification)}</span>
                    </div>
                    <div class="scope-box">{h(scope or "No scope text supplied.")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns(3)
            c1.metric("Original amount", fmt_money(amount))
            c2.metric("Savings", fmt_money(savings))
            c3.metric("Remaining", fmt_money(remaining))
            st.progress(int(current_cut), text=f"{current_cut:.1f}% cut")

            quick_cols = st.columns(5)
            quick_values = [0, 10, 25, 50, 100]
            for quick_col, quick_value in zip(quick_cols, quick_values):
                if quick_col.button(f"{quick_value}%", key=f"quick_{quick_value}_{line_id}"):
                    persist_line_cut(cuts, row, quick_value)
                    st.toast(f"Saved {quick_value}% cut")
                    st.rerun()

            col_slider, col_slider_apply, col_number, col_number_apply, col_reset = st.columns([2.4, 1, 1, 1, 1])
            slider_value = col_slider.slider(
                "Cut percent",
                min_value=0.0,
                max_value=100.0,
                value=current_cut,
                step=1.0,
                key=f"slider_{line_id}",
            )
            slider_apply = col_slider_apply.button("Save Slider", key=f"save_slider_{line_id}")
            exact_value = col_number.number_input(
                "Exact %",
                min_value=0.0,
                max_value=100.0,
                value=current_cut,
                step=0.5,
                key=f"exact_{line_id}",
            )
            exact_apply = col_number_apply.button("Save Exact", key=f"save_exact_{line_id}", type="primary")
            reset_clicked = col_reset.button("Reset", key=f"reset_{line_id}")

            if slider_apply:
                new_cut = round(float(slider_value), 2)
                persist_line_cut(cuts, row, new_cut)
                st.success(f"Saved {new_cut:.1f}% cut.")
                st.rerun()
            if exact_apply:
                new_cut = round(float(exact_value), 2)
                persist_line_cut(cuts, row, new_cut)
                st.success(f"Saved {new_cut:.1f}% cut.")
                st.rerun()
            if reset_clicked:
                persist_line_cut(cuts, row, 0)
                st.success("Cut reset to 0%.")
                st.rerun()


def department_cuts_page(df: pd.DataFrame, cuts: dict[str, dict[str, float | str]]) -> None:
    page_hero(
        "Department Cuts",
        "Apply one cut percentage across every 2027 Main Estimates line item in a department.",
    )

    dept_summary = (
        df.groupby("Department", as_index=False)
        .agg(
            budget=("amount_dollars", "sum"),
            current_savings=("cut_dollars", "sum"),
            line_items=("line_item_id", "count"),
            votes=("Vote", "nunique"),
        )
        .assign(current_rate=lambda x: x["current_savings"] / x["budget"] * 100)
        .sort_values("budget", ascending=False)
    )

    departments = dept_summary["Department"].tolist()
    if "selected_department" not in st.session_state or st.session_state["selected_department"] not in departments:
        st.session_state["selected_department"] = departments[0]

    search = st.text_input("Find department", placeholder="Type to filter departments...")
    department_list = dept_summary.copy()
    if search:
        department_list = department_list[
            department_list["Department"].str.contains(search, case=False, na=False)
        ]
    if department_list.empty:
        st.warning("No departments match that search.")
        return

    st.subheader("Choose Department")
    st.markdown(
        '<div class="section-note">Click Select on a department, then zero it out or apply a custom cut below.</div>',
        unsafe_allow_html=True,
    )
    card_cols = st.columns(3)
    for i, row in department_list.iterrows():
        is_selected = row["Department"] == st.session_state["selected_department"]
        card_class = "dept-card dept-card-selected" if is_selected else "dept-card"
        with card_cols[i % 3]:
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="dept-name">{h(row["Department"])}</div>
                    <div class="dept-stats">
                        Budget: {fmt_money(float(row["budget"]))}<br>
                        Savings: {fmt_money(float(row["current_savings"]))}<br>
                        Cut: {float(row["current_rate"]):.2f}%<br>
                        Lines: {int(row["line_items"]):,}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Select", key=f"select_dept_{row['Department']}"):
                st.session_state["selected_department"] = row["Department"]
                st.rerun()

    selected_department = st.session_state["selected_department"]
    dept_df = df[df["Department"] == selected_department].copy()
    current_budget = float(dept_df["amount_dollars"].sum())
    current_savings = float(dept_df["cut_dollars"].sum())
    current_rate = current_savings / current_budget * 100 if current_budget else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Department budget", fmt_money(current_budget))
    c2.metric("Current savings", fmt_money(current_savings))
    c3.metric("Current cut rate", f"{current_rate:.2f}%")
    c4.metric("Line items", f"{len(dept_df):,}")

    st.subheader(f"Cut {selected_department}")
    st.markdown(
        '<div class="section-note">This will overwrite the cut percentage for every line item in the selected department. You can still fine-tune individual items later.</div>',
        unsafe_allow_html=True,
    )

    if st.button("Zero Department", key=f"zero_dept_{selected_department}", type="primary"):
        set_department_cut(cuts, dept_df, 100)
        st.success(f"Zeroed out {selected_department}: {fmt_money(current_budget)} saved across {len(dept_df):,} line items.")
        st.rerun()

    quick_cols = st.columns(5)
    quick_values = [0, 10, 25, 50, 100]
    selected_quick = None
    for quick_col, quick_value in zip(quick_cols, quick_values):
        if quick_col.button(f"Set {quick_value}%", key=f"dept_quick_{quick_value}_{selected_department}"):
            selected_quick = float(quick_value)

    c_slider, c_number, c_apply = st.columns([3, 1, 1])
    slider_cut = c_slider.slider(
        "Department cut percent",
        min_value=0.0,
        max_value=100.0,
        value=round(float(current_rate), 1),
        step=1.0,
        key=f"dept_slider_{selected_department}",
    )
    exact_cut = c_number.number_input(
        "Exact %",
        min_value=0.0,
        max_value=100.0,
        value=round(float(current_rate), 1),
        step=0.5,
        key=f"dept_exact_{selected_department}",
    )
    apply_clicked = c_apply.button("Apply", key=f"dept_apply_{selected_department}")
    target_cut = selected_quick if selected_quick is not None else exact_cut if exact_cut != round(float(current_rate), 1) else slider_cut

    preview_savings = current_budget * float(target_cut) / 100
    p1, p2, p3 = st.columns(3)
    p1.metric("Preview savings", fmt_money(preview_savings))
    p2.metric("Preview remaining", fmt_money(current_budget - preview_savings))
    p3.metric("Target cut", f"{float(target_cut):.1f}%")
    st.progress(int(float(target_cut)), text=f"{float(target_cut):.1f}% department cut")

    if apply_clicked or selected_quick is not None:
        set_department_cut(cuts, dept_df, float(target_cut))
        st.success(f"Saved {float(target_cut):.1f}% cut across {len(dept_df):,} {selected_department} line items.")
        st.rerun()

    st.subheader("Department Table")
    visible_summary = dept_summary.assign(
        budget=dept_summary["budget"].map(fmt_money),
        current_savings=dept_summary["current_savings"].map(fmt_money),
        current_rate=dept_summary["current_rate"].map(lambda x: f"{x:.2f}%"),
    )
    st.dataframe(visible_summary, width="stretch", hide_index=True)


def explorer_page(df: pd.DataFrame, cuts: dict[str, dict[str, float | str]]) -> None:
    page_hero(
        "Explore and Cut",
        "Start with a Vote, narrow to a Department, then cut individual Main Estimate appropriations.",
    )
    c1, c2 = st.columns(2)
    votes = ["All votes"] + filtered_options(df, "Vote")
    vote = c1.selectbox("Vote", votes)
    if vote != "All votes":
        df = df[df["Vote"] == vote]

    departments = ["All departments"] + filtered_options(df, "Department")
    department = c2.selectbox("Department", departments)
    if department != "All departments":
        df = df[df["Department"] == department]

    line_item_editor(df, cuts)


def export_page(df: pd.DataFrame, cuts: dict[str, dict[str, float | str]]) -> None:
    page_hero("Export", "Download your active Main Estimates cut plan or the full line-item dataset with savings and remaining amounts.")

    cut_rows = pd.DataFrame(cuts.values())
    st.download_button(
        "Download cut plan JSON",
        data=json.dumps(cuts, indent=2, sort_keys=True),
        file_name="budget_cuts.json",
        mime="application/json",
    )
    st.download_button(
        "Download full line-item CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="budget_2027_with_cuts.csv",
        mime="text/csv",
    )
    if not cut_rows.empty:
        st.dataframe(cut_rows, width="stretch", hide_index=True)
    else:
        st.info("No cuts have been made yet.")


def main() -> None:
    inject_styles()
    if not DATA_PATH.exists():
        st.error(f"Could not find {DATA_PATH}")
        st.stop()

    raw_df = load_budget_data()
    cuts = load_cuts()
    cuts = prune_inactive_cuts(cuts, raw_df)
    df = apply_cuts(raw_df, cuts)

    st.sidebar.title("Budget Cutter")
    st.sidebar.caption("Concrete figures only")
    page = st.sidebar.radio("View", ["Dashboard", "Explore and Cut", "Department Cuts", "Export"])
    st.sidebar.divider()
    st.sidebar.write(f"Active rows: {len(raw_df):,}")
    st.sidebar.write(f"Active year: {', '.join(str(y) for y in ACTIVE_YEARS)}")
    st.sidebar.write(f"Active amount type: {', '.join(ACTIVE_AMOUNT_TYPES)}")
    st.sidebar.write(f"Saved cuts: {len(cuts):,}")
    st.sidebar.write(f"Autosave file: `{CUTS_PATH.name}`")

    if st.sidebar.button("Clear all cuts"):
        save_cuts({})
        st.rerun()

    if page == "Dashboard":
        overview_page(df)
    elif page == "Explore and Cut":
        explorer_page(df, cuts)
    elif page == "Department Cuts":
        department_cuts_page(df, cuts)
    else:
        export_page(df, cuts)


if __name__ == "__main__":
    main()
