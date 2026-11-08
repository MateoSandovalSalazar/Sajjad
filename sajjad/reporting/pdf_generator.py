"""
PDF Report Generation

Renders the Jinja2 HTML template with scan data and converts
it to PDF via WeasyPrint. Falls back to saving the HTML file
if WeasyPrint is unavailable.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from sajjad.models.report import Report
from sajjad.models.scan_result import ScanResult

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_pdf(
    result: ScanResult,
    output_path: str,
    company_name: str = "",
    white_label: bool = False,
) -> Path:
    report = Report(
        scan_result=result,
        company_name=company_name,
        white_label=white_label,
    )

    html_content = _render_html(report)
    out = Path(output_path)

    try:
        _write_pdf(html_content, out)
        logger.info("PDF report saved to %s", out)
    except ImportError:
        html_out = out.with_suffix(".html")
        html_out.write_text(html_content, encoding="utf-8")
        logger.warning(
            "WeasyPrint not available — HTML report saved to %s",
            html_out,
        )
        return html_out

    return out


def _render_html(report: Report) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.globals["now"] = datetime.now(timezone.utc)

    template = env.get_template("report.html")
    return template.render(
        result=report.scan_result,
        company_name=report.company_name,
        white_label=report.white_label,
        brand=report.brand_name,
        css_brand=_css_safe(report.footer_brand),
        analyst_notes=report.analyst_notes,
        generated_at=report.generated_at.strftime(
            "%d/%m/%Y %H:%M UTC"
        ),
    )


def _css_safe(value: str) -> str:
    """
    El pie de página se compone con `content:` dentro de <style>,
    donde el autoescape de Jinja no aplica: una comilla o un
    `</style>` en el nombre del cliente rompería la hoja de
    estilos o inyectaría markup. Se eliminan esos caracteres.
    """
    return "".join(
        c for c in value if c not in '"\\<>\n\r'
    ).strip()


def _write_pdf(html_content: str, output_path: Path) -> None:
    from weasyprint import HTML

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf(
        str(output_path)
    )
