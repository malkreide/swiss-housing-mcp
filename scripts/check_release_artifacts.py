#!/usr/bin/env python3
"""
check_release_artifacts.py — Release-Gate für MCP-Server.

Prüft die GEBAUTEN Artefakte, nicht die Quelldateien. Grund: der mcp-name-Marker
muss im publizierten README stehen, also im Description-Feld der Wheel-METADATA.
Ein Marker, der nur in README.de.md oder nur im Repo steht, hilft nicht — und
PyPI-Releases sind unveränderlich, das Nachrüsten kostet einen Versionssprung.

Aufruf (nach `python -m build`):
    python3 check_release_artifacts.py --dist dist [--tag v1.2.0]

Exit-Code: 0 = alles in Ordnung, 1 = Release stoppen.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from email import message_from_string
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore

MARKER_RE = re.compile(r"<!--\s*mcp-name:\s*([^\s>]+)\s*-->")
FAILS: list[str] = []
OKS: list[str] = []


def fail(msg: str) -> None:
    FAILS.append(msg)


def ok(msg: str) -> None:
    OKS.append(msg)


def wheel_metadata(wheel: Path) -> tuple[dict, str]:
    """Liefert (Header, Description-Body) aus der METADATA des Wheels."""
    with zipfile.ZipFile(wheel) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        raw = zf.read(name).decode("utf-8", errors="replace")
    msg = message_from_string(raw)
    body = msg.get_payload() or ""
    if not body:
        body = msg.get("Description", "") or ""
    return dict(msg.items()), body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tag", default=None, help="z. B. v1.2.0")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    dist = Path(args.dist).resolve()

    wheels = sorted(dist.glob("*.whl"))
    if not wheels:
        print(f"✗ Kein Wheel in {dist} — zuerst `python -m build` ausführen")
        return 1
    wheel = wheels[-1]

    headers, description = wheel_metadata(wheel)

    # --- A1: Marker im publizierten README (= Wheel-METADATA) ----------------
    markers = MARKER_RE.findall(description)
    if not markers:
        fail(
            f"A1: kein <!-- mcp-name: ... --> Marker in {wheel.name} (METADATA). "
            "Die MCP-Registry kann die PyPI-Ownership nicht prüfen. "
            "Marker in die von pyproject als `readme` deklarierte Datei aufnehmen "
            "und neu bauen — nach dem Upload ist die Version unveränderlich."
        )
    elif len(markers) > 1:
        fail(f"A1: {len(markers)} Marker in METADATA, genau einer erwartet: {markers}")
    else:
        ok(f"A1: Marker im Wheel vorhanden → {markers[0]}")

    # --- Quellen gegenprüfen -------------------------------------------------
    server_json = repo / "server.json"
    pyproject = repo / "pyproject.toml"

    proj_version = None
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        proj_version = data.get("project", {}).get("version")
        readme_decl = data.get("project", {}).get("readme")
        if isinstance(readme_decl, str) and markers:
            src = repo / readme_decl
            if src.exists() and not MARKER_RE.search(
                src.read_text(encoding="utf-8", errors="replace")
            ):
                fail(
                    f"A1: Marker im Wheel, aber nicht in {readme_decl} — "
                    "Quelle und Artefakt driften auseinander"
                )

    if server_json.exists():
        sj = json.loads(server_json.read_text(encoding="utf-8"))

        # --- A2: description ≤ 100 Zeichen -----------------------------------
        desc = sj.get("description", "")
        if len(desc) > 100:
            fail(
                f"A2: server.json description ist {len(desc)} Zeichen (max. 100). "
                "Die Registry antwortet mit 422 — und zwar erst NACH dem "
                "erfolgreichen PyPI-Upload."
            )
        else:
            ok(f"A2: server.json description {len(desc)}/100 Zeichen")

        if markers and sj.get("name") and sj["name"] != markers[0]:
            fail(f"A1: Marker '{markers[0]}' ≠ server.json name '{sj['name']}'")

        sj_version = sj.get("version")
        if sj_version and proj_version and sj_version != proj_version:
            fail(f"Version: server.json {sj_version} ≠ pyproject {proj_version}")
        elif sj_version:
            ok(f"Version: server.json und pyproject stimmen überein ({sj_version})")
    else:
        ok("server.json nicht vorhanden — A2 übersprungen")

    # --- A4: Tag zeigt auf den Stand, der publiziert wird --------------------
    if args.tag:
        tag_version = args.tag.lstrip("v")
        meta_version = headers.get("Version")
        if meta_version and tag_version != meta_version:
            fail(
                f"A4: Tag {args.tag} ≠ gebaute Version {meta_version}. "
                "Ein Re-Run eines alten Tag-Laufs checkt den alten Commit aus. "
                "Neuen Tag setzen oder workflow_dispatch auf dem Default-Branch nutzen."
            )
        else:
            ok(f"A4: Tag und gebaute Version stimmen überein ({meta_version})")

    for line in OKS:
        print(f"✓ {line}")
    for line in FAILS:
        print(f"✗ {line}")
    print(f"\n{len(FAILS)} Blocker, {len(OKS)} Prüfungen bestanden")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
