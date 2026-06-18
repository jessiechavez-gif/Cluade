#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 EXTRACTOR DE CONTRATACIONES ABIERTAS — ESTADO DE CHIHUAHUA
 Arrendamiento de equipo de transporte (concepto 325 del COG / CONAC)
================================================================================

Objetivo
--------
Obtener la CIFRA DURA del gasto estatal en arrendamiento vehicular en Chihuahua,
filtrando el concepto "Arrendamiento de equipo de transporte" y agregando por
EJERCICIO (año) y ENTE PÚBLICO solicitante.

Fuente: Portal de Contrataciones Abiertas del Estado de Chihuahua
        https://contrataciones.chihuahua.gob.mx/

Dos modos de uso
----------------
1) parse   (RECOMENDADO — 100% funcional, sin depender de la API):
   - En el portal aplicas los filtros:
       Concepto de contratación = "Arrendamiento de equipo de transporte"
       (deja Tipo de procedimiento en blanco para traer licitación + invitación
        + adjudicación directa; o fíjalo si solo quieres licitación pública)
       Rango de fechas amplio (p.ej. 01/2016 a hoy)
   - Pones "Todos" en registros por página, das Buscar y luego "Exportar".
   - Corres:  python extractor_chihuahua.py parse archivo_exportado.xlsx

2) scrape  (AUTOMATIZADO — pega directo al endpoint del portal):
   - El portal usa jQuery DataTables con procesamiento del lado del servidor.
   - Solo necesitas confirmar 2 cosas en la pestaña Network del navegador
     (Claude Code te ayuda con esto): la URL del endpoint XHR y los nombres de
     los parámetros del filtro. Los pegas en la sección CONFIG de abajo.
   - Corres:  python extractor_chihuahua.py scrape

Salidas (en la carpeta --out, por defecto ./salida_chihuahua)
   detalle_filtrado.csv      -> una fila por contratación que cumple el filtro
   resumen_por_anio.csv       -> total de contrataciones y monto por año
   resumen_por_anio_ente.csv  -> total y monto por año x ente público

Instalación de dependencias
   pip install pandas openpyxl requests
================================================================================
"""

import argparse
import re
import sys
import time
import unicodedata
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("Falta pandas. Instala con: pip install pandas openpyxl")


# ==============================================================================
# CONFIG — Solo necesitas tocar esto para el modo 'scrape'
# ==============================================================================

# URL del endpoint que devuelve la tabla (XHR). CONFÍRMALO en Network -> XHR.
# Patrón típico de este portal (Django + DataTables). Ajusta si difiere.
SCRAPE_ENDPOINT = "https://contrataciones.chihuahua.gob.mx/buscar/"

# Nombres EXACTOS de los parámetros del filtro tal como los manda el formulario.
# Cópialos del payload de la petición XHR (pestaña Network -> Payload/Form Data).
# Los valores de ejemplo corresponden al concepto 325; verifica el texto/clave
# que realmente envía el portal (a veces es un id numérico en vez del texto).
EXTRA_FILTER_PARAMS = {
    "concepto": "Arrendamiento de equipo de transporte",   # concepto 325
    # "tipo_procedimiento": "",   # vacío = todos; o "Licitación pública"
    # "materia": "Arrendamiento",
    # "fecha_inicio": "2016-01-01",
    # "fecha_fin": "2030-12-31",
}

# Tamaño de página para paginar en modo scrape.
PAGE_SIZE = 100
REQUEST_PAUSE_SEC = 0.5          # cortesía entre peticiones
REQUEST_TIMEOUT_SEC = 60

# Texto del concepto objetivo (concepto 325 del Clasificador por Objeto del Gasto)
CONCEPTO_OBJETIVO = "arrendamiento de equipo de transporte"

# Palabras clave para el cruce opcional sobre la descripción (--incluir-descripcion),
# que cacha registros mal clasificados que igual son arrendamiento vehicular.
DESC_KEYWORDS = ["vehic", "vehíc", "automovil", "automóvil", "camioneta",
                 "patrulla", "ambulancia", "flotilla", "parque vehicular"]


# ==============================================================================
# Utilidades de limpieza
# ==============================================================================

def quitar_acentos(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def norm(texto) -> str:
    """Normaliza para comparar: minúsculas, sin acentos, sin espacios extra."""
    return re.sub(r"\s+", " ", quitar_acentos(str(texto)).lower()).strip()


def parse_monto(valor) -> float:
    """
    Convierte montos en texto a float.
    Maneja: '$1,234,567.89', '1.234.567,89', 'N/D', vacíos, paréntesis (negativos).
    """
    if valor is None:
        return float("nan")
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip()
    if s == "" or norm(s) in {"n/d", "nd", "na", "n/a", "sin dato", "-"}:
        return float("nan")
    negativo = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^\d,.\-]", "", s)            # deja solo dígitos, , . y -
    if s.count(",") and s.count("."):
        # El separador decimal es el último símbolo que aparezca
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")   # formato 1.234.567,89
        else:
            s = s.replace(",", "")                       # formato 1,234,567.89
    elif s.count(","):
        # Si la coma parece decimal (2 dígitos al final) la tratamos como punto
        if re.search(r",\d{1,2}$", s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        num = float(s)
    except ValueError:
        return float("nan")
    return -num if negativo else num


def extraer_anio(valor) -> int:
    """Obtiene el año de un valor de fecha o de un texto que lo contenga."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)) and 2000 <= valor <= 2100:
        return int(valor)
    s = str(valor).strip()
    # Intento directo con pandas (acepta dd/mm/yyyy, yyyy-mm-dd, etc.)
    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if pd.notna(dt):
        return int(dt.year)
    # Respaldo: busca un año de 4 dígitos plausible
    m = re.search(r"(20\d{2})", s)
    return int(m.group(1)) if m else None


# ==============================================================================
# Detección automática de columnas (el export puede traer encabezados distintos)
# ==============================================================================

# Para cada campo lógico, lista de palabras clave que deben aparecer en el header.
PATRONES_COLUMNA = {
    "ente_publico":      [["ente"], ["dependencia"], ["unidad", "compradora"]],
    "concepto":          [["concepto"]],
    "materia":           [["materia"]],
    "tipo_procedimiento":[["tipo", "procedimiento"], ["procedimiento"]],
    "descripcion":       [["descripcion", "procedimiento"], ["descripcion"], ["objeto"]],
    "num_procedimiento": [["num", "procedimiento"], ["no", "procedimiento"], ["numero", "procedimiento"]],
    "proveedor":         [["proveedor"], ["contratista"], ["adjudicado"]],
    "ejercicio":         [["ejercicio"], ["anio"], ["ano"]],
    "fecha":             [["fecha", "contrato"], ["fecha", "fallo"], ["fecha", "adjud"], ["fecha"]],
    "monto":             [["monto", "contrat"], ["importe", "contrat"], ["monto", "adjud"],
                          ["monto", "maximo"], ["importe"], ["monto"]],
}


def detectar_columnas(df: pd.DataFrame) -> dict:
    """Mapea campo_logico -> nombre_real_de_columna usando coincidencia por palabras."""
    headers = {col: norm(col) for col in df.columns}
    mapping = {}
    for campo, grupos in PATRONES_COLUMNA.items():
        encontrada = None
        for palabras in grupos:                     # respeta la prioridad del orden
            for col, h in headers.items():
                if col in mapping.values():
                    continue
                if all(p in h for p in palabras):
                    encontrada = col
                    break
            if encontrada:
                break
        if encontrada:
            mapping[campo] = encontrada
    return mapping


# ==============================================================================
# Modo PARSE
# ==============================================================================

def cargar_export(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path, dtype=str)
    elif path.suffix.lower() in {".csv", ".txt"}:
        # Autodetecta separador y prueba codificaciones comunes
        for enc in ("utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(path, dtype=str, sep=None, engine="python", encoding=enc)
                break
            except (UnicodeDecodeError, Exception):
                df = None
        if df is None:
            raise ValueError(f"No pude leer {path}")
    else:
        raise ValueError(f"Formato no soportado: {path.suffix}")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def filtrar_arrendamiento(df: pd.DataFrame, mapping: dict, incluir_desc: bool) -> pd.DataFrame:
    col_concepto = mapping.get("concepto")
    if col_concepto is None and not incluir_desc:
        raise ValueError(
            "No encontré columna de 'Concepto de contratación'. "
            "Revisa el export o usa --incluir-descripcion para filtrar por descripción."
        )

    mask = pd.Series(False, index=df.index)
    if col_concepto is not None:
        mask = df[col_concepto].apply(norm).str.contains(CONCEPTO_OBJETIVO, na=False)

    if incluir_desc:
        col_desc = mapping.get("descripcion")
        col_mat = mapping.get("materia")
        if col_desc is not None:
            desc_norm = df[col_desc].apply(norm)
            kw = desc_norm.apply(lambda t: any(k in t for k in DESC_KEYWORDS))
            if col_mat is not None:
                es_arrend = df[col_mat].apply(norm).str.contains("arrendamiento", na=False)
                mask = mask | (kw & es_arrend)
            else:
                mask = mask | kw

    return df[mask].copy()


def agregar(df: pd.DataFrame, mapping: dict):
    """Devuelve (detalle, resumen_anual, resumen_anio_ente)."""
    out = pd.DataFrame(index=df.index)

    out["ejercicio"] = None
    if mapping.get("ejercicio"):
        out["ejercicio"] = df[mapping["ejercicio"]].apply(extraer_anio)
    if out["ejercicio"].isna().all() and mapping.get("fecha"):
        out["ejercicio"] = df[mapping["fecha"]].apply(extraer_anio)

    out["ente_publico"] = df[mapping["ente_publico"]] if mapping.get("ente_publico") else "(sin dato)"
    out["tipo_procedimiento"] = df[mapping["tipo_procedimiento"]] if mapping.get("tipo_procedimiento") else "(sin dato)"
    out["num_procedimiento"] = df[mapping["num_procedimiento"]] if mapping.get("num_procedimiento") else ""
    out["proveedor"] = df[mapping["proveedor"]] if mapping.get("proveedor") else ""
    out["descripcion"] = df[mapping["descripcion"]] if mapping.get("descripcion") else ""
    out["monto"] = df[mapping["monto"]].apply(parse_monto) if mapping.get("monto") else float("nan")

    detalle = out.copy()

    resumen_anual = (
        detalle.groupby("ejercicio", dropna=False)
        .agg(num_contrataciones=("monto", "size"),
             monto_total=("monto", "sum"),
             monto_promedio=("monto", "mean"))
        .reset_index()
        .sort_values("ejercicio")
    )

    resumen_ae = (
        detalle.groupby(["ejercicio", "ente_publico"], dropna=False)
        .agg(num_contrataciones=("monto", "size"),
             monto_total=("monto", "sum"))
        .reset_index()
        .sort_values(["ejercicio", "monto_total"], ascending=[True, False])
    )

    return detalle, resumen_anual, resumen_ae


# ==============================================================================
# Modo SCRAPE (DataTables server-side). Andamiaje listo; confirma endpoint/params.
# ==============================================================================

def construir_payload_datatables(start: int, length: int) -> dict:
    """Parámetros estándar que envía DataTables del lado servidor, más los filtros."""
    payload = {
        "draw": 1,
        "start": start,
        "length": length,
        "search[value]": "",
        "search[regex]": "false",
        "order[0][column]": 0,
        "order[0][dir]": "asc",
    }
    payload.update(EXTRA_FILTER_PARAMS)
    return payload


def scrape_todo() -> pd.DataFrame:
    try:
        import requests
    except ImportError:
        sys.exit("Falta requests para el modo scrape. Instala con: pip install requests")

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (extractor-contrataciones; uso institucional)",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://contrataciones.chihuahua.gob.mx/",
    })

    filas, start, total = [], 0, None
    while True:
        payload = construir_payload_datatables(start, PAGE_SIZE)
        try:
            r = sess.get(SCRAPE_ENDPOINT, params=payload, timeout=REQUEST_TIMEOUT_SEC)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"\n[!] Error al consultar el endpoint en start={start}: {e}")
            print("    Confirma SCRAPE_ENDPOINT y EXTRA_FILTER_PARAMS desde la pestaña")
            print("    Network del navegador (la petición XHR al hacer 'Buscar').")
            break

        lote = data.get("data", [])
        if total is None:
            total = data.get("recordsFiltered", data.get("recordsTotal", 0))
            print(f"[i] Registros que coinciden con el filtro: {total}")
        if not lote:
            break

        filas.extend(lote)
        start += PAGE_SIZE
        print(f"    descargados {min(start, total or start)}/{total or '?'}", end="\r")
        if total and start >= total:
            break
        time.sleep(REQUEST_PAUSE_SEC)

    print()
    if not filas:
        return pd.DataFrame()

    # DataTables suele devolver listas (por columna) o dicts (por nombre).
    if isinstance(filas[0], dict):
        return pd.DataFrame(filas)
    return pd.DataFrame(filas)  # columnas posicionales: renómbralas según el portal


# ==============================================================================
# Salidas
# ==============================================================================

def guardar(detalle, resumen_anual, resumen_ae, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    detalle.to_csv(out_dir / "detalle_filtrado.csv", index=False, encoding="utf-8-sig")
    resumen_anual.to_csv(out_dir / "resumen_por_anio.csv", index=False, encoding="utf-8-sig")
    resumen_ae.to_csv(out_dir / "resumen_por_anio_ente.csv", index=False, encoding="utf-8-sig")

    total_monto = detalle["monto"].sum(skipna=True)
    n = len(detalle)
    print(f"\n{'='*60}")
    print(f" RESULTADO — Arrendamiento de equipo de transporte (Chihuahua)")
    print(f"{'='*60}")
    print(f" Contrataciones encontradas : {n}")
    print(f" Monto total identificado   : ${total_monto:,.2f} MXN")
    sin_monto = int(detalle['monto'].isna().sum())
    if sin_monto:
        print(f" (Ojo: {sin_monto} registros sin monto legible — revísalos en el detalle)")
    print(f"\n Archivos en: {out_dir.resolve()}")
    print(f"   - detalle_filtrado.csv")
    print(f"   - resumen_por_anio.csv")
    print(f"   - resumen_por_anio_ente.csv")


# ==============================================================================
# CLI
# ==============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="Extrae y agrega arrendamiento de equipo de transporte (Chihuahua).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="modo", required=True)

    p_parse = sub.add_parser("parse", help="Procesa el archivo exportado del portal.")
    p_parse.add_argument("archivo", help="Ruta al .xlsx/.csv exportado del portal.")
    p_parse.add_argument("--out", default="salida_chihuahua", help="Carpeta de salida.")
    p_parse.add_argument("--incluir-descripcion", action="store_true",
                         help="Además del concepto 325, cacha registros de arrendamiento "
                              "cuya descripción mencione vehículos (mal clasificados).")
    p_parse.add_argument("--map", nargs="*", default=[],
                         help="Override de columnas, p.ej. monto='Monto del contrato'.")

    p_scrape = sub.add_parser("scrape", help="Descarga directo del endpoint del portal.")
    p_scrape.add_argument("--out", default="salida_chihuahua", help="Carpeta de salida.")
    p_scrape.add_argument("--incluir-descripcion", action="store_true")

    args = ap.parse_args()
    out_dir = Path(args.out)

    if args.modo == "parse":
        df = cargar_export(Path(args.archivo))
        print(f"[i] Filas leídas del export: {len(df)}")
        mapping = detectar_columnas(df)
        # Aplica overrides manuales tipo  campo='Nombre Columna'
        for item in args.map:
            if "=" in item:
                k, v = item.split("=", 1)
                mapping[k.strip()] = v.strip().strip("'\"")
        print("[i] Columnas detectadas:")
        for k, v in mapping.items():
            print(f"      {k:18s} -> {v}")
        faltan = [c for c in ("ente_publico", "monto") if c not in mapping]
        if faltan:
            print(f"[!] No detecté: {faltan}. Usa --map para fijarlas, "
                  f"p.ej.  --map monto='NombreExacto' ente_publico='NombreExacto'")

        filtrado = filtrar_arrendamiento(df, mapping, args.incluir_descripcion)
        print(f"[i] Filas que cumplen el filtro: {len(filtrado)}")
        if filtrado.empty:
            print("[!] Cero coincidencias. Verifica el filtro de concepto en el portal "
                  "o prueba --incluir-descripcion.")
            return
        detalle, r_anual, r_ae = agregar(filtrado, mapping)
        guardar(detalle, r_anual, r_ae, out_dir)

    elif args.modo == "scrape":
        df = scrape_todo()
        if df.empty:
            print("[!] No se descargaron filas. Revisa CONFIG (endpoint/parámetros).")
            return
        print(f"[i] Filas descargadas: {len(df)}")
        mapping = detectar_columnas(df)
        print("[i] Columnas detectadas:", mapping)
        filtrado = filtrar_arrendamiento(df, mapping, args.incluir_descripcion) \
            if mapping.get("concepto") else df
        detalle, r_anual, r_ae = agregar(filtrado, mapping)
        guardar(detalle, r_anual, r_ae, out_dir)


if __name__ == "__main__":
    main()
