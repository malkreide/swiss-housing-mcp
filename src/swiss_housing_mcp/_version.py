"""Die eine Stelle, an der dieses Paket seine Identitaet aufloest.

Gelesen aus den Metadaten der *installierten* Distribution, nie von Hand
geschrieben. Ein Literal ist eine zweite Kopie einer Angabe, die der Build
bestimmt, und zweite Kopien driften — `swiss-procurement-mcp` meldete
`0.4.0` an simap.ch, waehrend das Paket auf PyPI bei `0.18.3` stand,
vierzehn Minor-Versionen spaeter, aus genau so einer Konstante.

Ein eigenes Modul statt einer Aufloesung in `__init__`, damit andere Module
die Version importieren koennen, ohne die Paketwurzel zu laden.

Der Fallback markiert sich selbst als solcher: ein lokales PEP-440-Segment
nach `+` kann nie mit einem Release verwechselt werden, anders als ein
plausibel aussehendes `0.0.0`.

Neben der Version stehen hier `__summary__` und `__homepage__`. Sie sind aus
demselben Grund hier und nicht als Literal in `server.py`: Spec `2026-07-28`
stempelt den `serverInfo`-Block in **jedes** Resultat, `description` und
`websiteUrl` inbegriffen. Beide Angaben stehen bereits in `pyproject.toml`
(`description`, `urls.Homepage`) und von dort in den Paket-Metadaten — ein
zweites Vorkommen in `src/` waere derselbe Drift-Anfang wie eine
hartkodierte Version, nur ohne Gate, das ihn faengt.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as _pkg_metadata
from importlib.metadata import version as _pkg_version

_DIST = "swiss-housing-mcp"

try:
    __version__ = _pkg_version(_DIST)
except PackageNotFoundError:  # Quellbaum statt Installation
    __version__ = "0.0.0+source"


def _from_metadata() -> tuple[str | None, str | None]:
    """(Summary, Homepage) aus den Distributions-Metadaten.

    `Home-page` ist bei modernen Backends leer — hatchling schreibt
    `[project.urls]` ausschliesslich als `Project-URL: <Label>, <URL>`. Wer
    nur `m["Home-page"]` liest, bekommt hier `None` und haelt es fuer «nicht
    gesetzt», obwohl die URL in `pyproject.toml` steht (nachgemessen mit
    hatchling 1.x). Deshalb wird die Label-Zeile gelesen.

    Nicht installiert: beide `None`. Der Server laesst die Felder dann weg,
    statt etwas zu behaupten — ein Quellbaum-Lauf soll sich nicht als
    veroeffentlichtes Paket ausgeben.
    """
    try:
        meta = _pkg_metadata(_DIST)
    except PackageNotFoundError:
        return None, None
    homepage = meta.get("Home-page")
    if not homepage:
        for label, value in (
            raw.split(",", 1) for raw in meta.get_all("Project-URL") or () if "," in raw
        ):
            if label.strip().lower() == "homepage":
                homepage = value.strip()
                break
    return meta.get("Summary") or None, homepage or None


__summary__, __homepage__ = _from_metadata()

__all__ = ["__homepage__", "__summary__", "__version__"]
