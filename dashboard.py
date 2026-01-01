import pandas as pd
import streamlit as st


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Basic cleaning: ensure numeric columns are numeric
    for col in df.columns:
        if col not in ["player", "team", "country"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derive some helper columns
    if "minutesPlayed" in df.columns:
        df["90s"] = df["minutesPlayed"] / 90.0

    return df


def format_number(val):
    if pd.isna(val):
        return ""
    if isinstance(val, (int, float)):
        # Show integers without decimals, others with 2 decimals
        if float(val).is_integer():
            return f"{int(val)}"
        return f"{val:.2f}"
    return str(val)


def build_top_table(
    df: pd.DataFrame,
    metric: str,
    per_90: bool = False,
    min_minutes: int = 0,
    ascending: bool = False,
    extra_cols: list[str] | None = None,
) -> pd.DataFrame:
    work = df.copy()

    # Filter by minutes played if available
    if "minutesPlayed" in work.columns and min_minutes > 0:
        work = work[work["minutesPlayed"] >= min_minutes]

    # Calculate per 90 if requested and minutes column exists
    metric_col = metric
    if per_90 and "minutesPlayed" in work.columns:
        metric_per90 = f"{metric}_per90"
        work[metric_per90] = work[metric] / (work["minutesPlayed"] / 90.0)
        metric_col = metric_per90

    # Sort and take top 10
    work = work.sort_values(metric_col, ascending=ascending).head(10)

    # Build display table
    display_cols = ["player", "team", metric_col]
    if extra_cols:
        display_cols.extend(extra_cols)

    display = work[display_cols].copy()
    display.insert(0, "Rk", range(1, len(display) + 1))

    # Rename metric column for pretty display
    pretty_name = metric.replace("_", " ").title()
    display = display.rename(columns={metric_col: pretty_name})
    
    # Rename age and country columns for pretty display
    if "age" in display.columns:
        display = display.rename(columns={"age": "Age"})
    if "age_x" in display.columns:
        display = display.rename(columns={"age_x": "Age"})
    if "age_y" in display.columns:
        display = display.rename(columns={"age_y": "Age"})
    if "country" in display.columns:
        display = display.rename(columns={"country": "Country"})

    # Apply formatting (skip non-numeric columns like country)
    for col in display.columns:
        if col not in ["Rk", "player", "team", "country", "Country"]:
            display[col] = display[col].map(format_number)

    return display


def inject_opta_styles():
    """
    Inject CSS to approximate the Opta Analyst Premier League stats table style:
    - Clean white card background
    - Bold blue header
    - Subtle row separators and hover highlight
    """
    st.markdown(
        """
        <style>
        /* Page background */
        .main {
            background-color: #0b1120;
        }

        /* Center column max width */
        .block-container {
            max-width: 1100px !important;
            padding-top: 1.5rem !important;
        }

        /* Card-like container for each table */
        .opta-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.3);
            margin-bottom: 1.5rem;
        }

        /* Title style similar to Opta headings */
        .opta-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.4rem;
        }

        .opta-subtitle {
            font-size: 0.8rem;
            font-weight: 500;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.4rem;
        }

        /* Dataframe header */
        .opta-card table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.86rem;
        }

        .opta-card thead tr {
            background: linear-gradient(90deg, #0f172a, #1d4ed8);
        }

        .opta-card th {
            color: #e5e7eb;
            font-weight: 600;
            padding: 0.5rem 0.75rem;
            text-align: left;
            border-bottom: 1px solid rgba(15, 23, 42, 0.3);
            white-space: nowrap;
        }

        .opta-card tbody tr:nth-child(even) {
            background-color: #f9fafb;
        }

        .opta-card tbody tr:nth-child(odd) {
            background-color: #ffffff;
        }

        .opta-card tbody tr:hover {
            background-color: #e5f0ff;
        }

        .opta-card td {
            padding: 0.45rem 0.75rem;
            border-bottom: 1px solid #e5e7eb;
            color: #0f172a;
        }

        .opta-card td:first-child {
            font-weight: 600;
            color: #6b7280;
        }

        .opta-card td:nth-child(2) {
            font-weight: 600;
        }

        /* Strip default Streamlit dataframe overflow */
        .opta-card .stDataFrame {
            border-radius: 0;
        }

        /* Hide index column Streamlit sometimes injects */
        .stDataFrame [data-testid="stTable"] tbody tr td:first-child {
            padding-left: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="Super Lig Player Stats Dashboard",
        layout="centered",
        page_icon="📊",
    )

    inject_opta_styles()

    df = load_data("tackles_joined.csv")

    st.markdown(
        "<h2 style='color:#f9fafb; font-weight:700; margin-bottom:0.25rem;'>"
        "Super Lig Player Stats</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='color:#9ca3af; font-size:0.9rem; margin-bottom:1rem;'>"
        "Top 10 player rankings across key metrics, styled in the spirit of "
        "Opta Analyst's Premier League stats tables."
        "</div>",
        unsafe_allow_html=True,
    )

    # Sidebar controls
    st.sidebar.markdown("### Filters")
    min_minutes = st.sidebar.slider(
        "En az oynanan dakika",
        min_value=0,
        max_value=int(df.get("minutesPlayed", pd.Series([0])).max() or 0),
        value=300,
        step=90,
    )
    # Handle age range with proper defaults
    age_col = None
    if "age" in df.columns:
        age_col = "age"
    elif "age_x" in df.columns:
        age_col = "age_x"
    elif "age_y" in df.columns:
        age_col = "age_y"
    
    if age_col:
        age_series = df[age_col].dropna()
        if len(age_series) > 0:
            age_min = int(age_series.min())
            age_max = int(age_series.max())
        else:
            age_min, age_max = 16, 45  # Default range if no valid ages
    else:
        age_min, age_max = 16, 45  # Default range if age column doesn't exist
    
    # Ensure min < max
    if age_min >= age_max:
        age_min, age_max = 16, 45
    
    age_range = st.sidebar.slider(
        "Yaş aralığı",
        min_value=age_min,
        max_value=age_max,
        value=(age_min, age_max),
        step=1,
    )

    # Nationality filter
    nationality_filter = st.sidebar.selectbox(
        "Oyuncu Milliyeti",
        options=["Tümü", "Türk Oyuncular", "Yabancı Oyuncular"],
        index=0,
    )

    per90_default = True if "minutesPlayed" in df.columns else False
    per_90 = st.sidebar.checkbox("90 dakika bazında verileri göster", value=per90_default)

    # Filter dataframe by age range
    if age_col:
        age_min_selected, age_max_selected = age_range
        df = df[(df[age_col] >= age_min_selected) & (df[age_col] <= age_max_selected)]
    
    # Filter dataframe by nationality
    if "country" in df.columns:
        if nationality_filter == "Türk Oyuncular":
            df = df[df["country"] == "Türkiye"]
        elif nationality_filter == "Yabancı Oyuncular":
            df = df[(df["country"] != "Türkiye") & (df["country"].notna())]

    # Define metric groups inspired by Opta layouts
    metric_groups = {
        "Attacking": [
            ("goals", False),
            ("assists", False),
            ("totalShots", False),
            ("shotsOnTarget", False),
            ("expectedGoals", False),
        ],
        "Possession & Passing": [
            ("accuratePassesPercentage", True),
            ("keyPasses", False),
            ("accurateFinalThirdPasses", False),
            ("accurateLongBallsPercentage", True),
        ],
        "Defending": [
            ("tackles", False),
            ("interceptions", False),
            ("clearances", False),
            ("groundDuelsWon", False),
            ("groundDuelsWonPercentage", True),
            ("totalDuelsWon", False),
            ("totalDuelsWonPercentage", True),
        ],
    }

    # Render one card per metric group
    for group_name, group_metrics in metric_groups.items():
        st.markdown(
            f"<div class='opta-subtitle'>{group_name.upper()}</div>",
            unsafe_allow_html=True,
        )

        cols = st.columns(2)

        for i, (metric, is_percentage) in enumerate(group_metrics):
            if metric not in df.columns:
                continue

            with cols[i % 2]:
                # Determine which age column exists and prepare extra columns
                extra_cols = []
                # Use the age_col determined earlier in the main function
                if age_col:
                    extra_cols.append(age_col)
                if "country" in df.columns:
                    extra_cols.append("country")
                
                table = build_top_table(
                    df=df,
                    metric=metric,
                    per_90=per_90 and not is_percentage,
                    min_minutes=min_minutes,
                    ascending=False,
                    extra_cols=extra_cols if extra_cols else None,
                )

                metric_label = metric.replace("Percentage", " %").replace("_", " ").title()
                subtitle = f"Top 10 · {metric_label}"

                st.markdown(
                    "<div class='opta-card'>"
                    f"<div class='opta-title'>{metric_label}</div>"
                    f"<div style='font-size:0.75rem; color:#6b7280; margin-bottom:0.5rem;'>{subtitle}</div>",
                    unsafe_allow_html=True,
                )

                st.dataframe(
                    table,
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()


