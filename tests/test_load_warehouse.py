import importlib

import pytest

loader = importlib.import_module("src.load_warehouse")


class FakeConnection:
    def __init__(self):
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1

    def close(self):
        self.close_calls += 1


def configure_mocks(monkeypatch, connection, events):
    dataframe = object()
    dimension_keys = object()

    monkeypatch.setattr(
        loader,
        "create_connection",
        lambda: connection,
    )

    monkeypatch.setattr(
        loader,
        "load_parquet_files",
        lambda: dataframe,
    )

    dimension_functions = [
        "load_dim_fecha",
        "load_dim_territorio",
        "load_dim_organismo",
        "load_dim_destino",
        "load_dim_sexo",
    ]

    for function_name in dimension_functions:
        def fake_dimension(conn, df, name=function_name):
            events.append(name)

        monkeypatch.setattr(
            loader,
            function_name,
            fake_dimension,
        )

    monkeypatch.setattr(
        loader,
        "get_dimension_keys",
        lambda conn, df: dimension_keys,
    )

    monkeypatch.setattr(
        loader,
        "load_fact_financiamiento",
        lambda conn, df: events.append(
            "load_fact_financiamiento"
        ),
    )

    return dataframe, dimension_keys


def test_load_warehouse_commits_once_when_successful(monkeypatch):
    connection = FakeConnection()
    events = []

    configure_mocks(monkeypatch, connection, events)

    loader.load_warehouse()

    assert events == [
        "load_dim_fecha",
        "load_dim_territorio",
        "load_dim_organismo",
        "load_dim_destino",
        "load_dim_sexo",
        "load_fact_financiamiento",
    ]

    assert connection.commit_calls == 1
    assert connection.rollback_calls == 0
    assert connection.close_calls == 1


def test_load_warehouse_rolls_back_when_fact_load_fails(monkeypatch):
    connection = FakeConnection()
    events = []

    configure_mocks(monkeypatch, connection, events)

    def fail_fact_load(conn, df):
        raise RuntimeError("Error simulado al cargar hechos.")

    monkeypatch.setattr(
        loader,
        "load_fact_financiamiento",
        fail_fact_load,
    )

    with pytest.raises(
        RuntimeError,
        match="Error simulado al cargar hechos",
    ):
        loader.load_warehouse()

    assert connection.commit_calls == 0
    assert connection.rollback_calls == 1
    assert connection.close_calls == 1


def test_load_warehouse_rolls_back_when_dimension_load_fails(
    monkeypatch,
):
    connection = FakeConnection()
    events = []

    configure_mocks(monkeypatch, connection, events)

    def fail_dimension_load(conn, df):
        events.append("load_dim_territorio")
        raise RuntimeError("Error simulado al cargar territorio.")

    monkeypatch.setattr(
        loader,
        "load_dim_territorio",
        fail_dimension_load,
    )

    with pytest.raises(
        RuntimeError,
        match="Error simulado al cargar territorio",
    ):
        loader.load_warehouse()

    assert events == [
        "load_dim_fecha",
        "load_dim_territorio",
    ]

    assert connection.commit_calls == 0
    assert connection.rollback_calls == 1
    assert connection.close_calls == 1