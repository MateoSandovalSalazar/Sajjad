"""
Tests del render del reporte.

Se ejercita `_render_html` en vez de `generate_pdf` para no
depender de WeasyPrint: lo que interesa verificar es el HTML que
alimenta al PDF (puertos, marca, escapado), no la conversión.
"""

from sajjad.models.report import Report
from sajjad.models.scan_result import ScanResult
from sajjad.reporting.pdf_generator import _css_safe, _render_html


def _result(**kwargs) -> ScanResult:
    defaults = dict(
        domain="example.com",
        subdomains=["www.example.com"],
        live_hosts=["www.example.com"],
        open_ports={"www.example.com": [80, 443]},
        risk_score=42,
        risk_level="medium",
    )
    defaults.update(kwargs)
    return ScanResult(**defaults)


def test_open_ports_render_as_table():
    html = _render_html(Report(scan_result=_result()))

    assert "Puertos Abiertos por Host" in html
    assert "80, 443" in html
    assert "No se detectaron puertos abiertos" not in html


def test_empty_open_ports_render_empty_state():
    html = _render_html(Report(scan_result=_result(open_ports={})))

    assert "No se detectaron puertos abiertos" in html


def test_default_report_carries_sajjad_branding():
    html = _render_html(
        Report(scan_result=_result(), company_name="Acme SA")
    )

    assert "SAJJAD" in html
    assert "Sajjad EASM · Pág." in html
    # Sin white-label, el cliente aparece como destinatario.
    assert "Acme SA" in html


def test_white_label_replaces_sajjad_with_client_brand():
    html = _render_html(
        Report(
            scan_result=_result(),
            company_name="Acme SA",
            white_label=True,
        )
    )

    assert "Acme SA" in html
    assert "SAJJAD" not in html
    assert "Sajjad EASM" not in html


def test_white_label_without_company_falls_back_to_sajjad():
    """Un PDF sin marca alguna sería peor que uno con la nuestra."""
    report = Report(scan_result=_result(), white_label=True)

    assert report.brand_name == "SAJJAD"
    assert report.footer_brand == "Sajjad EASM"


def test_css_safe_strips_style_breaking_characters():
    assert _css_safe('Ac"me</style>') == "Acme/style"
    assert _css_safe("Acme & Co") == "Acme & Co"


def test_client_name_cannot_inject_into_footer_css():
    html = _render_html(
        Report(
            scan_result=_result(),
            company_name='Acme"; } body { display:none } .x {',
            white_label=True,
        )
    )

    assert "display:none" in html  # sobrevive como texto…
    assert '"; }' not in html      # …pero sin romper la regla CSS
