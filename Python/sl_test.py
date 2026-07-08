import duckdb
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


DB_PATH = r"C:\Users\gragg\Projects\enhanced_garmin_golf_analytics\DB\golf.duckdb"

st.set_page_config(
    page_title="Golf Analytics",
    layout="wide"
)

st.title("Latest Round Analysis")

con = duckdb.connect(DB_PATH)

df = con.execute(
"""
        WITH latest_round AS(
            SELECT
                MAX(rounds.start_time) AS start_time
            FROM rounds
            JOIN holes 
                ON holes.round_id = rounds.round_id
            WHERE holes.putts IS NOT NULL
            GROUP BY ALL
            HAVING start_time = MAX(start_time)
        ),

        best_round AS (
            SELECT
                rounds.course,
                rounds.tee_box,
                rounds.round_id,
                SUM(holes.strokes) AS total_strokes
            FROM rounds
            LEFT JOIN latest_round
                ON latest_round.start_time = rounds.start_time
            JOIN holes 
                ON holes.round_id = rounds.round_id
            WHERE 1=1
                AND holes.putts IS NOT NULL
                AND latest_round.start_time IS NULL
            GROUP BY ALL
            ORDER BY total_strokes ASC
            LIMIT 1
        ),

        holes_scores AS (
            SELECT
                holes.hole,
                rounds.course,
                AVG(holes.strokes) AS avg_strokes,
                holes.par,
                COUNT(*) AS played_count
            FROM holes
            JOIN rounds
                ON holes.round_id = rounds.round_id
            LEFT JOIN latest_round
                ON latest_round.start_time = rounds.start_time
            WHERE 1=1
                AND holes.putts IS NOT NULL
                AND latest_round.start_time IS NULL
            GROUP BY ALL
            HAVING played_count >=3
        ), 

        comparison AS (
            SELECT 
                rounds.course,
                rounds.tee_box,
                holes.hole,
                holes.strokes, 
                holes.putts,
                holes.par,
                holes.strokes - holes_scores.avg_strokes AS diff_from_avg, 
                holes.strokes - best_round_holes.strokes AS diff_from_best,

                SUM(holes.strokes - best_round_holes.strokes) OVER (
                    ORDER BY holes.hole
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS running_diff_from_best,    

                SUM(holes.strokes - holes_scores.avg_strokes) OVER (
                    ORDER BY holes.hole
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS running_diff_from_avg

            FROM latest_round
            JOIN rounds
                ON latest_round.start_time = rounds.start_time
            JOIN holes
                ON holes.round_id = rounds.round_id
            JOIN holes_scores
                ON holes.hole = holes_scores.hole
                AND rounds.course = holes_scores.course
            LEFT JOIN best_round 
                ON best_round.course = rounds.course
                AND best_round.tee_box = rounds.tee_box
            LEFT JOIN holes AS best_round_holes
                ON best_round_holes.round_id = best_round.round_id
                AND best_round_holes.hole = holes.hole
            WHERE 1=1
                AND holes.putts IS NOT NULL
            ORDER BY holes.hole)

        SELECT *
        FROM comparison
        """
).fetchdf()

# --------------------
# Top metrics
# --------------------
top1, top2, top3 = st.columns([3, 1, 1])
mid1, mid2, mid3 = st.columns(3)
bot1, bot2, bot3, bot4 = st.columns(4)

with top1:
    st.metric(
        "Course",
        df["course"].iloc[0]
    )

with top2:
    st.metric(
        "Tee Box",
        df["tee_box"].iloc[0]
    )

with top3:
    st.metric(
        "Par",
        f"{df['par'].sum():.0f}"
    )

with mid1:
    st.metric(
        "Strokes",
        f"{df['strokes'].sum():.0f}"
    )

with mid2:
    st.metric(
        "Net Score",
        f"{df['strokes'].sum() - df['par'].sum():+.0f}"
    )

with mid3:
    st.metric(
        "Putts Avg.",
        f"{df['putts'].mean():.1f}"
    )

with bot3:
    st.metric(
        "Best Hole",
        int(df.loc[df["diff_from_avg"].idxmin(), "hole"])
    )

with bot4:
    st.metric(
        "Worst Hole",
        int(df.loc[df["diff_from_avg"].idxmax(), "hole"])
    )

st.divider()

# --------------------
# Running totals
# --------------------

left, right = st.columns(2)



with left:
    st.subheader("Score vs Best Round")

    y = df["running_diff_from_best"].tolist()
    x = df["hole"].tolist()

    fig_best = go.Figure()

    # ---- Main line ----
    fig_best.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            line=dict(color="aliceblue", width=3),
            marker=dict(color="aliceblue", size=4),
            showlegend=False,
        )
    )

    # ---- Green fill (below zero) ----
    x_fill = []
    y_fill = []

    for i in range(len(x) - 1):
        x_fill.append(x[i])
        y_fill.append(min(y[i], 0))

        # Crossing zero?
        if (y[i] < 0 < y[i+1]) or (y[i] > 0 > y[i+1]):
            frac = abs(y[i]) / abs(y[i+1] - y[i])
            x_cross = x[i] + frac * (x[i+1] - x[i])

            x_fill.append(x_cross)
            y_fill.append(0)

    x_fill.append(x[-1])
    y_fill.append(min(y[-1], 0))

    fig_best.add_trace(
        go.Scatter(
            x=x_fill,
            y=y_fill,
            mode="lines",
            line=dict(width=0),
            fill="tozeroy",
            fillcolor="rgba(50,205,50,0.25)",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # ---- Red fill (above zero) ----
    x_fill = []
    y_fill = []

    for i in range(len(x) - 1):
        x_fill.append(x[i])
        y_fill.append(max(y[i], 0))

        if (y[i] < 0 < y[i+1]) or (y[i] > 0 > y[i+1]):
            frac = abs(y[i]) / abs(y[i+1] - y[i])
            x_cross = x[i] + frac * (x[i+1] - x[i])

            x_fill.append(x_cross)
            y_fill.append(0)

    x_fill.append(x[-1])
    y_fill.append(max(y[-1], 0))

    fig_best.add_trace(
        go.Scatter(
            x=x_fill,
            y=y_fill,
            mode="lines",
            line=dict(width=0),
            fill="tozeroy",
            fillcolor="rgba(255,0,0,0.25)",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # ---- Zero line ----
    fig_best.add_hline(
        y=0,
        line_dash="solid",
        line_color="darkolivegreen",
        line_width=3,
        annotation_text="Even Score",
        annotation_position="top left",
    )

    # ---- Last point label ----
    last = df.iloc[-1]

    fig_best.add_trace(
        go.Scatter(
            x=[last["hole"] + 0.1],
            y=[last["running_diff_from_best"]],
            mode="text",
            text=[f"{last['running_diff_from_best']:+.0f}"],
            textposition="middle right",
            textfont=dict(
                size=20,
                color="limegreen" if last["running_diff_from_best"] <= 0 else "red",
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig_best.update_layout(
        xaxis_title="Hole",
        yaxis_title="Running Difference",
        showlegend=False,
    )

    st.plotly_chart(fig_best, width="stretch")                          


with right:
    st.subheader("Score vs Average")

    y = df["running_diff_from_avg"].tolist()
    x = df["hole"].tolist()

    fig_avg = go.Figure()

    # ---- Main line ----
    fig_avg.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            line=dict(color="aliceblue", width=3),
            marker=dict(color="aliceblue", size=4),
            showlegend=False,
        )
    )

    # ---- Green fill (below zero) ----
    x_fill = []
    y_fill = []

    for i in range(len(x) - 1):
        x_fill.append(x[i])
        y_fill.append(min(y[i], 0))

        if (y[i] < 0 < y[i + 1]) or (y[i] > 0 > y[i + 1]):
            frac = abs(y[i]) / abs(y[i + 1] - y[i])
            x_cross = x[i] + frac * (x[i + 1] - x[i])

            x_fill.append(x_cross)
            y_fill.append(0)

    x_fill.append(x[-1])
    y_fill.append(min(y[-1], 0))

    fig_avg.add_trace(
        go.Scatter(
            x=x_fill,
            y=y_fill,
            mode="lines",
            line=dict(width=0),
            fill="tozeroy",
            fillcolor="rgba(50,205,50,0.25)",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # ---- Red fill (above zero) ----
    x_fill = []
    y_fill = []

    for i in range(len(x) - 1):
        x_fill.append(x[i])
        y_fill.append(max(y[i], 0))

        if (y[i] < 0 < y[i + 1]) or (y[i] > 0 > y[i + 1]):
            frac = abs(y[i]) / abs(y[i + 1] - y[i])
            x_cross = x[i] + frac * (x[i + 1] - x[i])

            x_fill.append(x_cross)
            y_fill.append(0)

    x_fill.append(x[-1])
    y_fill.append(max(y[-1], 0))

    fig_avg.add_trace(
        go.Scatter(
            x=x_fill,
            y=y_fill,
            mode="lines",
            line=dict(width=0),
            fill="tozeroy",
            fillcolor="rgba(255,0,0,0.25)",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # ---- Zero line ----
    fig_avg.add_hline(
        y=0,
        line_dash="solid",
        line_color="darkolivegreen",
        line_width=3,
        annotation_text="Average Score",
        annotation_position="top left",
    )

    # ---- Last point label ----
    last = df.iloc[-1]

    fig_avg.add_trace(
        go.Scatter(
            x=[last["hole"] + 0.1],
            y=[last["running_diff_from_avg"]],
            mode="text",
            text=[f"{last['running_diff_from_avg']:+.1f}"],
            textposition="bottom right" if last["running_diff_from_avg"] > 0 else "top right",
            textfont=dict(
                size=20,
                color="limegreen" if last["running_diff_from_avg"] <= 0 else "red",
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig_avg.update_layout(
        xaxis_title="Hole",
        yaxis_title="Running Difference",
        showlegend=False,
    )

    st.plotly_chart(fig_avg, width="stretch")

# --------------------
# Detail table
# --------------------

st.subheader("Hole Details")

st.dataframe(
    df,
    width="stretch",
    hide_index=True
)