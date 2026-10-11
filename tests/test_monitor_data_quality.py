from src.audit_data_quality import evaluate_check, print_report


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

    coverage = [
        (2026, 6, 1, 6, 35595),
    ]

    print_report(checks, coverage)
    output = capsys.readouterr().out

    assert "Errores: 1" in output
    assert "Advertencias: 1" in output
    assert "Resultado final: ERROR" in output
    assert "2026: 6 meses con datos" in output
