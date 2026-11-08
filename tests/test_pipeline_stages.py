"""
Contrato de nombres de etapa entre el motor y la interfaz.

El worker guarda `stage.lower()` en `scan.progress_stage`, y el
frontend (DomainDetail.tsx, constante STAGES) traduce esa cadena a una
etiqueta y a un porcentaje de progreso. Son dos listas en dos lenguajes
distintos sin nada que las ate.

Ya se desincronizaron una vez: la UI esperaba `email` y `scoring`, que
el orquestador nunca emitió, y le faltaba `analysis`. Resultado: al
llegar a la última etapa el índice era -1, la barra caía del 80% al 10%
y el texto volvía a "Iniciando...".

Si este test falla, hay que actualizar TAMBIÉN
`frontend/src/pages/DomainDetail.tsx` (STAGES y STAGE_LABELS).
"""

import re
from pathlib import Path

ORCHESTRATOR = (
    Path(__file__).resolve().parent.parent
    / "sajjad"
    / "orchestrator.py"
)
DOMAIN_DETAIL = (
    Path(__file__).resolve().parent.parent
    / "frontend"
    / "src"
    / "pages"
    / "DomainDetail.tsx"
)

# Las etapas que el orquestador emite hoy, en orden de ejecución.
EXPECTED_STAGES = [
    "discovery",
    "dns",
    "http",
    "ports",
    "tls",
    "vulns",
    "osint",
    "analysis",
    "complete",
]


def _stages_emitted_by_engine() -> set[str]:
    source = ORCHESTRATOR.read_text(encoding="utf-8")
    return {
        name.lower()
        for name in re.findall(r'_step\(\s*"([A-Z_]+)"', source)
    }


def test_el_motor_emite_las_etapas_esperadas():
    assert _stages_emitted_by_engine() == set(EXPECTED_STAGES)


def test_la_ui_conoce_todas_las_etapas_del_motor():
    """Cada etapa emitida tiene entrada en STAGES del frontend."""
    tsx = DOMAIN_DETAIL.read_text(encoding="utf-8")

    bloque = re.search(
        r"const STAGES = \[(.*?)\] as const", tsx, re.DOTALL
    )
    assert bloque, "No se encontró la constante STAGES en DomainDetail.tsx"
    ui_stages = set(re.findall(r"'([a-z]+)'", bloque.group(1)))

    faltan = _stages_emitted_by_engine() - ui_stages
    assert not faltan, (
        f"La UI no conoce estas etapas del motor: {sorted(faltan)}. "
        f"Durante ellas la barra de progreso se reinicia al 10%."
    )


def test_la_ui_no_espera_etapas_inexistentes():
    """Una etapa en la UI que el motor no emite infla el total y
    hace que el progreso nunca llegue al 100%."""
    tsx = DOMAIN_DETAIL.read_text(encoding="utf-8")

    bloque = re.search(
        r"const STAGES = \[(.*?)\] as const", tsx, re.DOTALL
    )
    ui_stages = set(re.findall(r"'([a-z]+)'", bloque.group(1)))

    sobran = ui_stages - _stages_emitted_by_engine()
    assert not sobran, (
        f"La UI espera etapas que el motor no emite: {sorted(sobran)}."
    )


def test_cada_etapa_tiene_etiqueta_traducida():
    """Sin etiqueta, el usuario ve 'Iniciando...' toda la etapa."""
    tsx = DOMAIN_DETAIL.read_text(encoding="utf-8")

    bloque = re.search(
        r"const STAGE_LABELS: Record<string, string> = \{(.*?)\n\}",
        tsx,
        re.DOTALL,
    )
    assert bloque, "No se encontró STAGE_LABELS en DomainDetail.tsx"
    etiquetadas = set(re.findall(r"^\s*([a-z]+):", bloque.group(1), re.M))

    faltan = _stages_emitted_by_engine() - etiquetadas
    assert not faltan, (
        f"Etapas sin etiqueta en la UI: {sorted(faltan)}"
    )
