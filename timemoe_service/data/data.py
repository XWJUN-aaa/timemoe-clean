import numpy as np
import pandas as pd
from pathlib import Path

data_path = Path("/root/projects/timemoe/data/TimeSeriesDatasets/ETTh1/data.dat")
arr = np.fromfile(data_path, dtype=np.float32).reshape(14400, 7, 5)

start = pd.Timestamp("2016-01-01 00:00:00", tz="UTC")
index = pd.date_range(start=start, periods=arr.shape[0], freq="H")

sql_lines = ["USE tk;"]

for node_idx in range(7):
    table = f"etth1_node{node_idx+1:02d}"
    for ts, row in zip(index, arr[:, node_idx, :]):
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        sql_lines.append(
            f"INSERT INTO {table} VALUES "
            f"('{ts_str}', {row[0]:.6f}, {int(row[1])}, {int(row[2])}, {int(row[3])}, {int(row[4])});"
        )

output_file = Path("/root/projects/timemoe/etth1_insert.sql")
output_file.write_text("\n".join(sql_lines))
print(f"SQL 文件已生成: {output_file}")