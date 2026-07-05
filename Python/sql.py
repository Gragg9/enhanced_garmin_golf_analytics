import duckdb

DB_PATH = r"C:\Users\gragg\Projects\GolfAnalytics\DB\golf.duckdb"

con = duckdb.connect(DB_PATH)

print(con.execute("SELECT * FROM rounds").fetchdf())