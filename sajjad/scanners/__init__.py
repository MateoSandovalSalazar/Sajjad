"""
Shared utilities for all scanner modules.

Every scanner uses run_tool() to invoke external binaries
and parse_jsonl() to handle ProjectDiscovery's JSONL output.
"""

import json
import logging
import os
import subprocess
from typing import Any

from sajjad.exceptions import ScanTimeoutError, ToolNotFoundError

logger = logging.getLogger(__name__)

# ProjectDiscovery tools live here. We resolve binaries explicitly
# so the Go tools always win over Python package CLI shims (e.g.
# the `httpx` CLI that ships with the Python httpx package).
_GO_BIN = os.path.expanduser("~/go/bin")


def _resolve_binary(name: str) -> str:
    """Return absolute path to tool, preferring ~/go/bin."""
    candidate = os.path.join(_GO_BIN, name)
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return name  # fall back; subprocess raises FileNotFoundError


def run_tool(cmd: list[str], timeout: int = 300) -> str:
    resolved = [_resolve_binary(cmd[0])] + cmd[1:]
    logger.debug("Executing: %s", " ".join(resolved))
    try:
        result = subprocess.run(
            resolved,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0 and result.stderr:
            logger.warning(
                "%s stderr: %s",
                tool_name,
                result.stderr[:500],
            )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise ScanTimeoutError(
            f"Timeout after {timeout}s running: {' '.join(cmd)}"
        )
    except FileNotFoundError:
        raise ToolNotFoundError(
            f"Tool not found: {cmd[0]!r}. "
            f"Checked {_GO_BIN} and PATH. "
            "Ensure it is installed."
        )


def parse_jsonl(output: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for line in output.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            results.append(json.loads(stripped))
        except json.JSONDecodeError:
            logger.debug(
                "Skipping non-JSON line: %.80s", stripped
            )
    return results
