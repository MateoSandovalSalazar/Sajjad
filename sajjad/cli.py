"""
Sajjad CLI

Entry point for the Phase 0 MVP.
Usage: python sajjad.py --domain example.com --output report.pdf
"""

import logging
import os
import sys

import click
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from sajjad import __version__
from sajjad.exceptions import SajjadError, ToolNotFoundError
from sajjad.orchestrator import ScanOrchestrator, verify_tools
from sajjad.reporting import generate_pdf

load_dotenv()
console = Console()

SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "bold yellow",
    "medium": "yellow",
    "low": "blue",
    "info": "dim",
}

STAGE_ICONS = {
    "DISCOVERY": "🔍",
    "DNS":       "🌐",
    "HTTP":      "📡",
    "PORTS":     "🔌",
    "TLS":       "🔒",
    "VULNS":     "⚠️ ",
    "OSINT":     "🕵️ ",
    "ANALYSIS":  "📊",
    "COMPLETE":  "✅",
}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def _print_banner() -> None:
    console.print(
        Panel(
            Text.from_markup(
                f"[bold blue]SAJJAD[/bold blue] "
                f"[red]·[/red] "
                f"Attack Surface Monitor "
                f"[dim]v{__version__}[/dim]"
            ),
            border_style="blue",
            padding=(0, 2),
        )
    )


def _print_summary(result) -> None:
    sev_colors = {
        "critical": "red",
        "high": "yellow",
        "medium": "dark_orange",
        "low": "blue",
        "info": "dim",
    }
    score = result.risk_score
    level = result.risk_level
    score_color = sev_colors.get(level, "white")

    console.print()
    console.rule("[bold]Resultados del Escaneo[/bold]")

    # Risk score
    console.print(
        f"\n  [bold]Risk Score:[/bold] "
        f"[{score_color} bold]{score}/100 — "
        f"{level.upper()}[/{score_color} bold]"
    )

    # Stats table
    stats = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    stats.add_column(style="dim")
    stats.add_column(style="bold")
    stats.add_row("Subdominios descubiertos", str(len(result.subdomains)))
    stats.add_row("Hosts activos", str(len(result.live_hosts)))
    total_ports = sum(len(v) for v in result.open_ports.values())
    stats.add_row("Puertos abiertos", str(total_ports))
    stats.add_row("Hallazgos totales", str(result.total_findings))
    console.print(stats)

    # Findings by severity
    if result.summary:
        sev_table = Table(
            title="Hallazgos por Severidad",
            box=box.ROUNDED,
            padding=(0, 3),
        )
        sev_table.add_column("Severidad", style="bold")
        sev_table.add_column("Cantidad", justify="right")

        for sev in ("critical", "high", "medium", "low", "info"):
            count = result.summary.get(sev, 0)
            if count == 0:
                continue
            color = sev_colors.get(sev, "white")
            sev_table.add_row(
                f"[{color}]{sev.upper()}[/{color}]",
                f"[{color} bold]{count}[/{color} bold]",
            )
        console.print(sev_table)

    # Critical findings preview
    critical = result.findings_by_severity.get("critical", [])
    if critical:
        console.print(
            "\n[bold red]Hallazgos críticos:[/bold red]"
        )
        for f in critical[:5]:
            console.print(f"  [red]▸[/red] {f.title}")
        if len(critical) > 5:
            console.print(
                f"  [dim]… y {len(critical) - 5} más[/dim]"
            )


@click.command()
@click.option(
    "--domain", "-d",
    required=True,
    help="Dominio objetivo a escanear (debe ser de tu propiedad).",
)
@click.option(
    "--output", "-o",
    default="reporte.pdf",
    show_default=True,
    help="Ruta del archivo PDF de salida.",
)
@click.option(
    "--company",
    default="",
    help="Nombre de la empresa para el reporte.",
)
@click.option(
    "--skip-verify",
    is_flag=True,
    default=False,
    help="Omitir verificación de herramientas al inicio.",
)
@click.option(
    "--timeout",
    default=int(os.getenv("SCAN_TIMEOUT", "300")),
    show_default=True,
    help="Timeout en segundos por etapa.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Mostrar logs de debug.",
)
def main(
    domain: str,
    output: str,
    company: str,
    skip_verify: bool,
    timeout: int,
    verbose: bool,
) -> None:
    """
    Sajjad — External Attack Surface Monitor.

    Escanea la superficie de ataque externa de un dominio
    y genera un reporte PDF profesional con todos los hallazgos.

    ⚠  Solo escanear dominios de tu propiedad.
    """
    _setup_logging(verbose)
    _print_banner()

    console.print(
        f"\n  [bold]Dominio objetivo:[/bold] [cyan]{domain}[/cyan]"
    )
    console.print(
        f"  [bold]Reporte de salida:[/bold] [cyan]{output}[/cyan]\n"
    )

    if not skip_verify:
        try:
            verify_tools()
        except ToolNotFoundError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Preparando escaneo…", total=None)

        def on_progress(stage: str, message: str) -> None:
            icon = STAGE_ICONS.get(stage, "·")
            progress.update(
                task,
                description=(
                    f"{icon} [bold][{stage}][/bold] {message}"
                ),
            )

        orchestrator = ScanOrchestrator(
            domain=domain,
            on_progress=on_progress,
            scan_timeout=timeout,
            nuclei_rate_limit=int(
                os.getenv("NUCLEI_RATE_LIMIT", "150")
            ),
        )

        try:
            result = orchestrator.run()
        except SajjadError as exc:
            progress.stop()
            console.print(
                f"\n[bold red]Error durante el escaneo:"
                f"[/bold red] {exc}"
            )
            sys.exit(1)
        except KeyboardInterrupt:
            progress.stop()
            console.print(
                "\n[yellow]Escaneo interrumpido "
                "por el usuario.[/yellow]"
            )
            sys.exit(130)

    _print_summary(result)

    # Generate PDF
    console.print("\n[dim]Generando reporte PDF…[/dim]")
    try:
        out_path = generate_pdf(
            result,
            output_path=output,
            company_name=company,
        )
        console.print(
            f"\n[bold green]✓ Reporte guardado:[/bold green] "
            f"[cyan]{out_path}[/cyan]"
        )
    except Exception as exc:
        console.print(
            f"[bold red]Error generando PDF:[/bold red] {exc}"
        )
        sys.exit(1)
