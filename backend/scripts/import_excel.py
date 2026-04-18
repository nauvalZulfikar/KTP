"""Import a sheet from Product Details_v1.xlsx into the SQLite TaskRow table.

Wipes existing rows and reinserts, so the workbook stays the source of truth.
The default sheet is 'As-Is' (current scheduling scenario). Other common sheet
names: 'Non-Preemptive', 'What-If 1'…'What-If 5'.

Run from the backend directory:

    python -m scripts.import_excel
    python -m scripts.import_excel --path "../Product Details_v1.xlsx" --sheet "What-If 1"
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import delete
from sqlmodel import Session

from app.config import settings
from app.db import engine, init_db
from app.models import TaskRow

_COLUMN_MAP: dict[str, str] = {
    "UniqueID": "unique_id",
    "Sr. No": "sr_no",
    "Product Name": "product_name",
    "Order Processing Date": "order_processing_date",
    "Promised Delivery Date": "promised_delivery_date",
    "Quantity Required": "quantity_required",
    "Components": "component",
    "Operation": "operation",
    "Process Type": "process_type",
    "Machine Number": "machine_number",
    "Run Time (min/1000)": "run_time_per_1000",
    "Cycle Time (seconds)": "cycle_time_seconds",
    "Setup time (seconds)": "setup_time_seconds",
    "status": "status",
}

REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "UniqueID",
    "Product Name",
    "Order Processing Date",
    "Promised Delivery Date",
    "Quantity Required",
    "Components",
    "Machine Number",
    "Run Time (min/1000)",
})


def load_dataframe(path: Path, sheet: str = "As-Is") -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")
    # Drop trailing/empty rows where the primary key is blank.
    df = df[df["UniqueID"].notna()].reset_index(drop=True)
    return df


def _is_blank(value: Any) -> bool:
    """Treat NaN, None, empty strings, and whitespace-only strings as missing."""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def row_to_taskrow(row: "pd.Series[Any]") -> TaskRow:
    data: dict[str, Any] = {}
    for excel_col, attr in _COLUMN_MAP.items():
        if excel_col not in row.index:
            continue
        value = row[excel_col]
        data[attr] = None if _is_blank(value) else value

    data["unique_id"] = int(data["unique_id"])
    data["quantity_required"] = int(data["quantity_required"])
    data["run_time_per_1000"] = float(data["run_time_per_1000"])
    data["order_processing_date"] = pd.Timestamp(data["order_processing_date"]).to_pydatetime()
    data["promised_delivery_date"] = pd.Timestamp(data["promised_delivery_date"]).to_pydatetime()
    if data.get("sr_no") is not None:
        data["sr_no"] = int(data["sr_no"])
    for f in ("cycle_time_seconds", "setup_time_seconds"):
        if data.get(f) is not None:
            data[f] = float(data[f])
    if not data.get("status"):
        data.pop("status", None)

    return TaskRow(**data)


def import_dataframe(df: pd.DataFrame, session: Session) -> tuple[int, int]:
    """Wipe TaskRow rows in the session's DB and insert the provided DataFrame.
    Commits the transaction. Returns (deleted, inserted)."""
    deleted = session.execute(delete(TaskRow)).rowcount or 0
    for _, row in df.iterrows():
        session.add(row_to_taskrow(row))
    session.commit()
    return deleted, len(df)


def import_excel(path: Path, sheet: str = "As-Is") -> tuple[int, int]:
    df = load_dataframe(path, sheet)
    init_db()
    with Session(engine) as session:
        return import_dataframe(df, session)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=settings.excel_path,
        help=f"Excel workbook path (default: {settings.excel_path})",
    )
    parser.add_argument("--sheet", default="As-Is", help="Sheet name (default: As-Is)")
    args = parser.parse_args()

    deleted, inserted = import_excel(args.path, args.sheet)
    print(f"Deleted {deleted} existing row(s).")
    print(f"Inserted {inserted} row(s) from {args.path} [sheet={args.sheet}].")


if __name__ == "__main__":
    main()
