import duckdb
import polars as pl
import lancedb
import time

from degen_tracker.lance import LanceDBLogs

pl.Config.set_fmt_str_lengths(200)
pl.Config.set_fmt_float("full")

# Resumes sync based on latest block number. Useful for if the database gets out of sync. Requires an existing logs database to work.


# Attempt to connect to the database and open the table
try:
    # Open lancedb table
    uri: str = "logs"
    db: lancedb.DBConnection = lancedb.connect(uri)
    logs_tbl = db.open_table("logs")
except Exception as e:
    print(f"Failed to connect to the database or open the table: {e}")
    # Exit the script or handle the error as needed
    raise SystemExit(e)

resume_block_number = pl_df = logs_tbl.to_polars().select('block_number').sort(
    by='block_number', descending=True).head(5).collect()['block_number'][0]
print(resume_block_number)

# Resume the query from resume_block_number
start_time = time.time()

# Initialize this dataclass, which will be used to build the logs database
lance_logs = LanceDBLogs()
lance_logs.db_sync(
    start_block=resume_block_number, block_chunks=500)

print('Time took to sync base erc20 logs:', time.time() - start_time)


# can use lance to polars lazy frame https://lancedb.github.io/lancedb/python/polars_arrow/#from-pydantic-models
