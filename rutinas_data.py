# -*- coding: utf-8 -*-
"""
Catálogo de ejercicios de rutinas (hombros y brazos).

Reconstruye la tabla `rutinas_ejercicios` a partir de los JSON extraídos de
las guías de Delavier y de las ilustraciones de assets/rutinas. Así la base
se puede regenerar sin depender de un archivo .db copiado.
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))

GRUPOS = {
    "hombros": {
        "catalogo": "hombros_ejercicios.json",
        "guia": "guia_hombros_extraido.json",
        "imagenes": os.path.join("assets", "rutinas", "hombros"),
        "paginas": (3, 21),
    },
    "brazos": {
        "catalogo": "brazos_ejercicios.json",
        "guia": "guia_brazos_extraido.json",
        "imagenes": os.path.join("assets", "rutinas", "brazos"),
        "paginas": (3, 28),
    },
}

EQUIPOS = {
    "MANCUERNAS", "MANCUERNA", "POLEA", "POLEADOBLE", "BARRA", "MÁQUINA",
    "MAQUINA", "PESOCORPORAL", "ESTIRAMIENTO",
}

H_POS = "POSICIÓNINICIAL"
H_EJE = "EJECUCIÓNDELMOVIMIENTO"
H_MUS = "MÚSCULOSTRABAJADOS"
H_COM = "COMENTARIOS"
H_OBS = "OBSERVACIÓN"


def _norm(linea):
    return re.sub(r"\s+", "", linea).upper()


def _bloque(lineas, desde, hasta):
    frag = [
        l.strip() for l in lineas[desde:hasta]
        if l.strip() and not _norm(l).startswith("GUÍADE")
    ]
    return re.sub(r"\s+", " ", " ".join(frag)).strip()


def _parsear(pagina):
    lineas = pagina["text"].split("\n")
    idx = {}
    for i, linea in enumerate(lineas):
        n = _norm(linea)
        for clave, valor in (
            ("pos", H_POS), ("eje", H_EJE), ("mus", H_MUS),
            ("com", H_COM), ("obs", H_OBS),
        ):
            if n == valor and clave not in idx:
                idx[clave] = i
        if n.startswith("GUÍADE") and "pie" not in idx:
            idx["pie"] = i

    if not all(k in idx for k in ("pos", "eje", "mus", "pie")):
        return None

    equipo_idx = None
    for i in range(idx["pie"] + 1, len(lineas)):
        if _norm(lineas[i]) in EQUIPOS:
            equipo_idx = i
            break
    if equipo_idx is None:
        return None

    num = None
    for i in range(equipo_idx - 1, idx["pie"], -1):
        if re.fullmatch(r"\d{2}", lineas[i].strip()):
            num = lineas[i].strip()
            break
    if not num:
        return None

    posicion = _bloque(lineas, idx["pos"] + 1, idx["eje"])
    fin_mus = idx.get("com", idx.get("obs", idx["pie"]))
    musculos = _bloque(lineas, idx["mus"] + 1, fin_mus)
    comentarios = ""
    if "com" in idx:
        comentarios = _bloque(lineas, idx["com"] + 1, idx.get("obs", idx["pie"]))
    observacion = ""
    if "obs" in idx:
        observacion = _bloque(lineas, idx["obs"] + 1, idx["pie"])

    ejecucion = ""
    ultimo = None
    for i in range(len(lineas) - 1, -1, -1):
        if lineas[i].strip() == num:
            ultimo = i
            break
    if ultimo is not None:
        trozos, actual = [], []
        for linea in lineas[ultimo + 1:]:
            s = linea.strip()
            if s in ("—", "-", "–"):
                if actual:
                    trozos.append(actual)
                    actual = []
                continue
            if s:
                actual.append(s)
        if actual:
            trozos.append(actual)
        partes = [
            re.sub(r"\s+", " ", " ".join(t)).strip().rstrip(",;")
            for t in trozos if t
        ]
        ejecucion = "\n".join("• " + p for p in partes)

    return {
        "num": num,
        "posicion": posicion,
        "ejecucion": ejecucion,
        "musculos": musculos,
        "comentarios": comentarios,
        "observacion": observacion,
    }


def _componer(ficha):
    partes = [
        "POSICIÓN INICIAL", ficha["posicion"].rstrip(":").strip(),
        "", "EJECUCIÓN", ficha["ejecucion"],
        "", "MÚSCULOS TRABAJADOS", ficha["musculos"],
    ]
    if ficha["comentarios"]:
        partes += ["", "COMENTARIOS", ficha["comentarios"]]
    if ficha["observacion"]:
        partes += ["", "OBSERVACIÓN", ficha["observacion"]]
    return "\n".join(partes).strip()


def _leer_json(ruta):
    for codificacion in ("utf-8-sig", "utf-8"):
        try:
            with open(ruta, "r", encoding=codificacion) as fh:
                return json.load(fh)
        except Exception:
            continue
    return None


def cargar_catalogo_rutinas(conn):
    """Inserta las fichas que falten en rutinas_ejercicios (por grupo y número)."""
    insertados = 0
    for grupo, config in GRUPOS.items():
        ruta_guia = os.path.join(BASE, config["guia"])
        ruta_catalogo = os.path.join(BASE, config["catalogo"])
        if not (os.path.exists(ruta_guia) and os.path.exists(ruta_catalogo)):
            continue

        paginas = _leer_json(ruta_guia) or []
        catalogo = _leer_json(ruta_catalogo) or []
        por_num = {c.get("num"): c for c in catalogo if c.get("num")}

        existentes = {
            fila[0]
            for fila in conn.execute(
                "SELECT num FROM rutinas_ejercicios WHERE grupo = ?", (grupo,)
            )
        }

        desde, hasta = config["paginas"]
        for pagina in paginas:
            numero_pagina = pagina.get("page")
            if not numero_pagina or not (desde <= numero_pagina <= hasta):
                continue
            ficha = _parsear(pagina)
            if not ficha or ficha["num"] in existentes:
                continue
            datos = por_num.get(ficha["num"])
            if not datos:
                continue

            ruta_img = os.path.join(BASE, config["imagenes"], datos.get("imagen", ""))
            blob = None
            if datos.get("imagen") and os.path.exists(ruta_img):
                with open(ruta_img, "rb") as fh:
                    blob = fh.read()

            conn.execute(
                "INSERT INTO rutinas_ejercicios "
                "(grupo, num, nombre, equipo, imagen_nombre, imagen_blob, descripcion) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    grupo,
                    ficha["num"],
                    datos.get("nombre"),
                    datos.get("equipo"),
                    datos.get("imagen"),
                    blob,
                    _componer(ficha),
                ),
            )
            insertados += 1

    return insertados
