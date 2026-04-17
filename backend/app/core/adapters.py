"""Pandas <-> Task boundary adapters. Keep pandas isolated to this module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Task

if TYPE_CHECKING:
    import pandas as pd


_COLUMN_MAP = {
    "unique_id": "UniqueID",
    "product_name": "Product Name",
    "component": "Components",
    "machine": "Machine Number",
    "quantity": "Quantity Required",
    "run_time_per_1000": "Run Time (min/1000)",
    "order_processing_date": "Order Processing Date",
    "promised_delivery_date": "Promised Delivery Date",
    "start_time": "Start Time",
    "end_time": "End Time",
}

_CORE_COLUMNS = set(_COLUMN_MAP.values())


def dataframe_to_tasks(df: "pd.DataFrame") -> list[Task]:
    import pandas as pd

    tasks: list[Task] = []
    for _, row in df.iterrows():
        extras = {col: row[col] for col in df.columns if col not in _CORE_COLUMNS}
        start = row.get("Start Time")
        end = row.get("End Time")
        tasks.append(
            Task(
                unique_id=int(row["UniqueID"]),
                product_name=str(row["Product Name"]),
                component=str(row["Components"]),
                machine=str(row["Machine Number"]),
                quantity=float(row["Quantity Required"]),
                run_time_per_1000=float(row["Run Time (min/1000)"]),
                order_processing_date=pd.Timestamp(row["Order Processing Date"]).to_pydatetime(),
                promised_delivery_date=pd.Timestamp(row["Promised Delivery Date"]).to_pydatetime(),
                start_time=pd.Timestamp(start).to_pydatetime() if pd.notna(start) else None,
                end_time=pd.Timestamp(end).to_pydatetime() if pd.notna(end) else None,
                extras=extras,
            )
        )
    return tasks


def tasks_to_dataframe(tasks: list[Task]) -> "pd.DataFrame":
    import pandas as pd

    rows = []
    for t in tasks:
        row = {
            "UniqueID": t.unique_id,
            "Product Name": t.product_name,
            "Components": t.component,
            "Machine Number": t.machine,
            "Quantity Required": t.quantity,
            "Run Time (min/1000)": t.run_time_per_1000,
            "Order Processing Date": t.order_processing_date,
            "Promised Delivery Date": t.promised_delivery_date,
            "Start Time": t.start_time,
            "End Time": t.end_time,
        }
        row.update(t.extras)
        rows.append(row)
    return pd.DataFrame(rows)
