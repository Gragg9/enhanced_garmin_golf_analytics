import duckdb
from pathlib import Path

from json_ingest import parse_export, round_to_dict, holes_to_dicts


DATABASE_PATH = r"C:\Users\gragg\Projects\GolfAnalytics\DB\golf.duckdb"
DATA_DIR = Path(r"C:\Users\gragg\Projects\GolfAnalytics\Data")


def load_rounds(con, rounds):
    """Insert rounds into DuckDB."""

    rows = [round_to_dict(r) for r in rounds]

    con.executemany(
        """
        INSERT OR REPLACE INTO rounds (
            round_id,
            course_id,
            course,
            city,
            state,
            start_time,
            end_time,
            tee_box,
            score_type,
            tee_rating,
            tee_slope,
            holes_completed
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        [
            (
                r["round_id"],
                r["course_id"],
                r["course"],
                r["city"],
                r["state"],
                r["start_time"],
                r["end_time"],
                r["tee_box"],
                r["score_type"],
                r["tee_rating"],
                r["tee_slope"],
                r["holes_completed"],
            )
            for r in rows
        ],
    )


def load_holes(con, rounds):
    """Insert holes into DuckDB."""

    hole_rows = []

    for r in rounds:
        hole_rows.extend(holes_to_dicts(r))

    con.executemany(
        """
        INSERT OR REPLACE INTO holes (
            round_id,
            hole,
            strokes,
            putts,
            penalties,
            fairway_outcome
        )
        VALUES (
            ?, ?, ?, ?, ?, ?
        )
        """,
        [
            (
                h["round_id"],
                h["hole"],
                h["strokes"],
                h["putts"],
                h["penalties"],
                h["fairway_outcome"],
            )
            for h in hole_rows
        ],
    )


def main():
    con = duckdb.connect(DATABASE_PATH)

    json_files = sorted(DATA_DIR.glob("*.json"))

    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {DATA_DIR}")

    all_rounds = []

    for file in json_files:
        print(f"Loading {file.name}...")

        rounds = parse_export(str(file))
        all_rounds.extend(rounds)

    print(f"Total rounds loaded from JSON: {len(all_rounds)}")

    # Optional: wrap in transaction for speed + safety
    con.execute("BEGIN TRANSACTION")

    try:
        load_rounds(con, all_rounds)
        load_holes(con, all_rounds)

        con.execute("COMMIT")

    except Exception as e:
        con.execute("ROLLBACK")
        raise e

    finally:
        con.close()

    print("Load complete.")


if __name__ == "__main__":
    main()