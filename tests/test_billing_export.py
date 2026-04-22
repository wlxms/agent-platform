"""Tests for CSV export (T3.2)."""


def test_export_records_to_csv():
    from agentp_billing.service import export_records_csv
    records = [
        {"instance_id": "i1", "model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "cost": 0.0025, "total_tokens": 150, "timestamp": "2026-01-15T10:00:00Z"},
        {"instance_id": "i2", "model": "gpt-4o", "input_tokens": 200, "output_tokens": 100, "cost": 0.005, "total_tokens": 300, "timestamp": "2026-01-16T11:00:00Z"},
    ]
    csv_content = export_records_csv(records)
    lines = csv_content.strip().split("\n")
    assert lines[0].startswith("instance_id")
    assert "i1" in lines[1]
    assert "i2" in lines[2]


def test_export_empty_records():
    from agentp_billing.service import export_records_csv
    csv_content = export_records_csv([])
    lines = csv_content.strip().split("\n")
    assert lines[0].startswith("instance_id")
    assert len(lines) == 1
