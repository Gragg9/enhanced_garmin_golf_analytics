import duckdb

DB_PATH = r"C:\Users\gragg\Projects\enhanced_garmin_golf_analytics\DB\golf.duckdb"

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

print(df)

