#!/usr/bin/env python3
"""Genera un dashboard de KPIs autocontenido a partir de un config JSON.

Uso:
    python build_dashboard.py config.json -o dashboard.html

Valida el config (fechas, series alineadas, unidades) e inyecta el JSON en
la plantilla assets/template.html. El HTML resultante no tiene dependencias
externas: funciona offline, como archivo local o publicado como Artifact.
"""
import argparse
import json
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
PLACEHOLDER = "__CONFIG_JSON__"

VALID_UNITS = {"currency", "number", "percent"}
VALID_AGG = {"sum", "avg", "last"}


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def validate(cfg: dict) -> None:
    for key in ("title", "dates", "kpis", "charts"):
        if key not in cfg:
            fail(f"falta la clave obligatoria '{key}'")
    n = len(cfg["dates"])
    if n < 2:
        fail("'dates' necesita al menos 2 fechas ISO (YYYY-MM-DD)")
    if cfg["dates"] != sorted(cfg["dates"]):
        fail("'dates' debe estar en orden ascendente")

    ids = set()
    for kpi in cfg["kpis"]:
        kid = kpi.get("id")
        if not kid or kid in ids:
            fail(f"cada KPI necesita un 'id' único (problema en {kpi.get('label', kid)})")
        ids.add(kid)
        if len(kpi.get("series", [])) != n:
            fail(f"KPI '{kid}': la serie tiene {len(kpi.get('series', []))} valores, se esperaban {n}")
        if kpi.get("unit", "number") not in VALID_UNITS:
            fail(f"KPI '{kid}': unit debe ser uno de {sorted(VALID_UNITS)}")
        if kpi.get("aggregate", "sum") not in VALID_AGG:
            fail(f"KPI '{kid}': aggregate debe ser uno de {sorted(VALID_AGG)}")
        if kpi.get("goodDirection", "up") not in {"up", "down"}:
            fail(f"KPI '{kid}': goodDirection debe ser 'up' o 'down'")

    chart_ids = set()
    for chart in cfg["charts"]:
        cid = chart.get("id")
        if not cid or cid in chart_ids:
            fail("cada chart necesita un 'id' único")
        chart_ids.add(cid)
        ctype = chart.get("type")
        if ctype == "line":
            series = chart.get("series", [])
            if not 1 <= len(series) <= 3:
                fail(f"chart '{cid}': entre 1 y 3 series (más de 3 no valida all-pairs; usa small multiples)")
            for s in series:
                if "kpi" in s:
                    if s["kpi"] not in ids:
                        fail(f"chart '{cid}': la serie apunta a un KPI inexistente '{s['kpi']}'")
                elif len(s.get("values", [])) != n:
                    fail(f"chart '{cid}': serie '{s.get('name')}' desalineada con 'dates'")
        elif ctype == "bar":
            cats = chart.get("categories", [])
            vals = chart.get("values", [])
            if not cats or len(cats) != len(vals):
                fail(f"chart '{cid}': 'categories' y 'values' deben tener la misma longitud")
            if len(cats) > 8:
                fail(f"chart '{cid}': máximo 8 categorías; agrupa el resto en 'Otros'")
            for i, v in enumerate(vals):
                if len(v) != n:
                    fail(f"chart '{cid}': values[{i}] desalineado con 'dates'")
        else:
            fail(f"chart '{cid}': type debe ser 'line' o 'bar'")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("config", help="ruta al config JSON del dashboard")
    ap.add_argument("-o", "--output", default="dashboard.html", help="archivo HTML de salida")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    validate(cfg)

    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        fail(f"la plantilla {TEMPLATE} no contiene el marcador {PLACEHOLDER}")
    # </script> dentro de un string JSON rompería el bloque; se escapa.
    payload = json.dumps(cfg, ensure_ascii=False, indent=2).replace("</", "<\\/")
    out = Path(args.output)
    out.write_text(template.replace(PLACEHOLDER, payload), encoding="utf-8")
    print(f"ok: {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
