from src.audit_data_quality import (
    evaluate_check,
    find_missing_months,
    print_report,
)


def test_zero_errors_are_classified_as_ok():
    result = evaluate_check("Acciones negativas", 0)

    assert result["status"] == "OK"
    assert result["count"] == 0


def test_positive_error_count_is_classified_as_error():
    result = evaluate_check("Acciones negativas", 5)

    assert result["status"] == "ERROR"
    assert result["count"] == 5


def test_positive_warning_count_is_not_an_error():
    result = evaluate_check(
        "Acciones sin monto",
        100,
        level="warning",
    )

    assert result["status"] == "ADVERTENCIA"
    assert result["count"] == 100


def test_warning_with_zero_count_is_ok():
    result = evaluate_check(
        "Acciones sin monto",
        0,
        level="warning",
    )

    assert result["status"] == "OK"


def test_report_displays_errors_and_warnings(capsys):
    checks = [
        evaluate_check("Acciones negativas", 0),
        evaluate_check("Acciones sin monto", 12, level="warning"),
        evaluate_check("Montos negativos", 2),
    ]

    # En el periodo observado falta el mes 4.
    coverage = [
        (2026, [1, 2, 3, 5, 6], 5, 1, 6, 35595),
    ]

    print_report(checks, coverage)
    output = capsys.readouterr().out

    assert "Errores: 1" in output
    assert "Advertencias: 1" in output
    assert "Resultado final: ERROR" in output
    assert "2026: 5 meses con datos" in output
    assert "Meses faltantes dentro del periodo observado: 04" in output


def test_find_missing_months_detects_gap_between_observed_months():
    assert find_missing_months([1, 2, 4, 5]) == [3]


def test_find_missing_months_does_not_require_future_months():
    assert find_missing_months([1, 2, 3, 4, 5, 6]) == []


def test_find_missing_months_ignores_months_before_first_observation():
    assert find_missing_months([3, 4, 5]) == []


def test_find_missing_months_handles_unsorted_and_repeated_months():
    assert find_missing_months([5, 1, 2, 2, 5]) == [3, 4]


def test_find_missing_months_handles_empty_input():
    assert find_missing_months([]) == []