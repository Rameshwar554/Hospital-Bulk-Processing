import pytest
from fastapi import HTTPException
from app.main import parse_csv


def test_valid_csv_with_optional_phone():
    rows = parse_csv(
        b"name,address,phone\nGeneral Hospital,123 Main St,555-0101\nCity Hospital,45 Park Ave,\n"
    )
    assert len(rows) == 2
    assert rows[0].phone == "555-0101"
    assert rows[1].phone is None


def test_missing_required_column():
    with pytest.raises(HTTPException) as exc:
        parse_csv(b"name,phone\nGeneral Hospital,555-0101\n")
    assert exc.value.status_code == 400


def test_more_than_twenty_rows():
    content = "name,address\n" + "".join(
        f"Hospital {i},Address {i}\n" for i in range(21)
    )
    with pytest.raises(HTTPException) as exc:
        parse_csv(content.encode())
    assert exc.value.status_code == 400


def test_blank_required_value():
    with pytest.raises(HTTPException):
        parse_csv(b"name,address\n,Some address\n")
