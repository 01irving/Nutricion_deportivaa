# -*- coding: utf-8 -*-
"""
Guarda en la BD las RUTINAS SIMPLES de la biblioteca: una por cada
sesión de las plantillas del estudio (PLANTILLAS_SEMANA en
rutinas_tab.py) y una por cada sesión distinta de las rutinas semanales
guardadas por el usuario. Quedan en rutinas_guardadas (semanal=0) con su
prescripción completa y aparecen en el desplegable ★ de la celda Sesión,
en el combo 'Rutina guardada simple' y en ⤒ AGREGAR AL DÍA.

La tabla ya existe en la BD (rutinas_guardadas + rutinas_guardadas_ejercicios,
con la columna semanal para distinguir el tipo); este cargador solo llena
el tipo simple con upsert por nombre.

Uso:
    python cargar_rutinas_simples.py [--dry-run]
"""
import ast
import json
import os
import shutil
import sqlite3
import sys

RUTA = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(RUTA, "Nutrición_deportiva.db")
DRY = "--dry-run" in sys.argv

CAMPOS = ("grupo", "num", "nombre", "equipo",
          "series", "repeticiones", "descanso_rep", "descanso_series",
          "peso")


def plantillas_desde_codigo():
    """Extrae PLANTILLAS_SEMANA de rutinas_tab.py sin importar tkinter."""
    with open(os.path.join(RUTA, "rutinas_tab.py"), encoding="utf-8",
              newline="") as f:
        arbol = ast.parse(f.read())
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign) and any(
            getattr(t, "id", "") == "PLANTILLAS_SEMANA" for t in nodo.targets
        ):
            return ast.literal_eval(nodo.value)
    raise SystemExit("PLANTILLAS_SEMANA no encontrada")


def estudio_corto(nombre_plantilla):
    """'Split 4 días · Tren superior / inferior (Pedersen 2022)' →
    'Pedersen 2022'."""
    nombre = nombre_plantilla.strip()
    if "(" in nombre and nombre.endswith(")"):
        return nombre[nombre.rindex("(") + 1:-1]
    return nombre


def ficha(grupo, num):
    """Ficha del catálogo por (grupo, num) o None."""
    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        try:
            r = conn.execute(
                "SELECT nombre, equipo FROM rutinas_ejercicios "
                "WHERE grupo = ? AND num = ?",
                (grupo, num),
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return None
    return dict(r) if r else None


def filas_de_sesion(ejercicios, plantilla=None):
    """Filas para rutinas_guardadas_ejercicios con la prescripción de la
    plantilla (o la que ya traiga cada ficha)."""
    base = plantilla or {}
    filas = []
    for i, (grupo, num, _marca) in enumerate(ejercicios, start=1):
        datos = ficha(grupo, num) or {"nombre": f"{grupo} #{num}",
                                      "equipo": ""}
        filas.append({
            "dia": "",
            "orden": i,
            "descanso": 0,
            "grupo": grupo,
            "num": num,
            "nombre": datos.get("nombre") or f"{grupo} #{num}",
            "equipo": datos.get("equipo") or "",
            "series": base.get("series") or "3",
            "repeticiones": base.get("repeticiones") or "12",
            "descanso_rep": "",
            "descanso_series": base.get("descanso_series") or "60",
            "peso": "",
            "notas": "",
        })
    return filas


def filas_de_guardada(rutina, sesion):
    """Filas de una sesión (notas) de una rutina semanal guardada."""
    filas = []
    for i, e in enumerate(
        [e for e in rutina.get("ejercicios", [])
         if not e.get("descanso")
         and (e.get("notas") or "").strip() == sesion],
        start=1,
    ):
        fila = {"dia": "", "orden": i, "descanso": 0, "notas": ""}
        for c in CAMPOS:
            fila[c] = e.get(c) or ""
        filas.append(fila)
    return filas


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    # --- 1) sesiones de las plantillas del estudio --------------------------
    rutinas = []   # (nombre, filas)
    for p in plantillas_desde_codigo():
        estudio = estudio_corto(p["nombre"])
        for sesion, ejercicios in p["sesiones"].items():
            nombre = f"{sesion} ({estudio})"
            filas = filas_de_sesion(ejercicios, p)
            if filas:
                rutinas.append((nombre, filas))

    # --- 2) sesiones de las rutinas semanales guardadas ---------------------
    for r in con.execute(
        "SELECT id_rutina_guardada, nombre FROM rutinas_guardadas "
        "WHERE semanal = 1"
    ):
        rutina = {
            "ejercicios": [
                dict(e) for e in con.execute(
                    "SELECT * FROM rutinas_guardadas_ejercicios "
                    "WHERE rutina_guardada_id = ? "
                    "ORDER BY CASE dia "
                    "WHEN 'Lunes' THEN 1 WHEN 'Martes' THEN 2 "
                    "WHEN 'Miércoles' THEN 3 WHEN 'Jueves' THEN 4 "
                    "WHEN 'Viernes' THEN 5 WHEN 'Sábado' THEN 6 "
                    "ELSE 7 END, orden",
                    (r["id_rutina_guardada"],),
                )
            ]
        }
        vistas = []
        for e in rutina["ejercicios"]:
            ses = (e.get("notas") or "").strip()
            if e.get("descanso") or not ses or ses in vistas:
                continue
            vistas.append(ses)
            nombre = f"{ses} · {r['nombre']}"
            filas = filas_de_guardada(rutina, ses)
            if filas:
                rutinas.append((nombre, filas))
    con.close()

    print(f"Rutinas simples a guardar: {len(rutinas)}")
    for nombre, filas in rutinas:
        print(f"  {nombre:52} | {len(filas)} ejercicios")
    if DRY:
        return 0

    if not os.path.exists(DB.replace(".db", "_respaldo_rutinas_simples.db")):
        shutil.copy(DB, DB.replace(".db", "_respaldo_rutinas_simples.db"))

    sys.path.insert(0, RUTA)
    import database
    for nombre, filas in rutinas:
        database.guardar_rutina_guardada(nombre, 0, filas)
    print("LISTO: rutinas simples guardadas en la BD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
