from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from sqlmodel import Session, select

from app.models import TaskRow
from scripts.import_excel import import_dataframe, load_dataframe, row_to_taskrow

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXCEL_PATH = PROJECT_ROOT / "Product Details_v1.xlsx"


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "UniqueID": 1,
                "Sr. No": 1,
                "Product Name": "Product 1",
                "Order Processing Date": pd.Timestamp("2024-08-21"),
                "Promised Delivery Date": pd.Timestamp("2024-08-28"),
                "Quantity Required": 9000,
                "Components": "C1",
                "Operation": "Op1",
                "Process Type": "Machining",
                "Machine Number": "M1",
                "Run Time (min/1000)": 10.0,
                "Cycle Time (seconds)": 0.5,
                "Setup time (seconds)": 120.0,
                "status": "InProgress",
            },
            {
                "UniqueID": 2,
                "Sr. No": 2,
                "Product Name": "Product 1",
                "Order Processing Date": pd.Timestamp("2024-08-21"),
                "Promised Delivery Date": pd.Timestamp("2024-08-28"),
                "Quantity Required": 9000,
                "Components": "C2",
                "Operation": "Op2",
                "Process Type": "Outsource",
                "Machine Number": "OutSrc",
                "Run Time (min/1000)": 200.0,
                "Cycle Time (seconds)": None,
                "Setup time (seconds)": None,
                "status": None,
            },
        ]
    )


def test_row_to_taskrow_coerces_types() -> None:
    df = _sample_df()
    row = row_to_taskrow(df.iloc[0])
    assert isinstance(row, TaskRow)
    assert row.unique_id == 1
    assert row.quantity_required == 9000
    assert row.run_time_per_1000 == 10.0
    assert row.order_processing_date == datetime(2024, 8, 21)
    assert row.machine_number == "M1"


def test_row_to_taskrow_handles_null_status() -> None:
    df = _sample_df()
    row = row_to_taskrow(df.iloc[1])
    assert row.status == "InProgress"  # default kicks in
    assert row.cycle_time_seconds is None
    assert row.setup_time_seconds is None


def test_load_dataframe_rejects_missing_columns(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xlsx"
    pd.DataFrame([{"UniqueID": 1}]).to_excel(bad, sheet_name="P", index=False)
    with pytest.raises(ValueError, match="Missing required columns"):
        load_dataframe(bad, "P")


def test_import_dataframe_inserts_all_rows(session: Session) -> None:
    df = _sample_df()
    deleted, inserted = import_dataframe(df, session)
    assert deleted == 0
    assert inserted == 2
    rows = session.exec(select(TaskRow)).all()
    assert len(rows) == 2


def test_import_dataframe_wipes_on_reimport(session: Session) -> None:
    df = _sample_df()
    import_dataframe(df, session)
    deleted, inserted = import_dataframe(df.head(1), session)
    assert deleted == 2
    assert inserted == 1
    rows = session.exec(select(TaskRow)).all()
    assert len(rows) == 1
    assert rows[0].component == "C1"


@pytest.mark.skipif(not EXCEL_PATH.exists(), reason=f"missing fixture {EXCEL_PATH}")
def test_import_real_excel_round_trip(session: Session) -> None:
    df = load_dataframe(EXCEL_PATH, "P")
    deleted, inserted = import_dataframe(df, session)
    assert deleted == 0
    assert inserted == len(df)

    rows = session.exec(select(TaskRow)).all()
    assert len(rows) == inserted
    # Spot-check: whatever the first UID is, its core fields round-tripped cleanly.
    first = next((r for r in rows if r.unique_id == 1), None)
    assert first is not None
    assert first.product_name.strip() != ""
    assert first.component.startswith("C")
    assert first.machine_number.strip() != ""
    assert first.quantity_required > 0
    assert first.run_time_per_1000 > 0
