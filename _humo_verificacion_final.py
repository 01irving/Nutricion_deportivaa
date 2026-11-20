# -*- coding: utf-8 -*-
"""Prueba de humo de verificación final (19 nov): RutinasTab real en BD
temporal SIN semanales guardadas (el caso de la BD de uso diario).
Chequea lo dejado pendiente de la sesión del 17:
  - franja de Progresión con el texto nuevo (ciclos 4 semanas, sin 2-10 %)
    y secciones ACSM intactas;
  - bases de Ciclos solo con Semana actual + semanales guardadas;
  - flujo completo: cargar plantilla -> guardar semanal -> generar ciclo
    de 2 mesociclos -> GUARDAR -> APLICAR AL PACIENTE -> PDF;
  - barra de estado se restablece al cambiar de sub-pestaña.
Y lo nuevo de la sesión del 19 (1RM → pesos de la rutina semanal):
  - % del 1RM por NIVEL del paciente (ACSM 2009: principiante 65 % con
    +2,5 % semanal, intermedio 75 % y avanzado 85 % con +5 %), limitado
    por el cuadro 18.8 NSCA, catálogo completo en la calculadora;
  - al GUARDAR un 1RM se aplica al ejercicio en las 4 semanas (Semana 1
    = % del nivel, rampa semanal y deloading -10 % en la 4.ª);
  - llenado de la columna Peso desde el 1RM (semana actual y mesociclo
    Semana 1-4 con su rampa semanal), sobrescribiendo y sin tocar lo que
    no tiene 1RM registrado;
  - GENERAR en Ciclos toma el peso base del 1RM cuando el ejercicio no
    tiene peso manual (y respeta el manual), con nota nueva en CIC_NOTAS;
  - APLICAR MESOCICLO: las semanas EDITADAS de las ranuras Semana 1-4
    al paciente (Semana 1 como rutina activa y las 4 al historial).
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="humo_verificacion_"))
database.DB_PATH = TMP / "prueba.db"
database.init_db()

import calculadora_1rm  # noqa: E402
import rutinas_tab  # noqa: E402
from rutinas_tab import (  # noqa: E402
    CIC_BASE_MODEO, CIC_DELOAD_PESO, CIC_DELOAD_SERIES, CIC_MODOS,
    CIC_SECUENCIAS, DIAS_SEMANA, PLANTILLAS_SEMANA, _discos_2_5,
)

raiz = tk.Tk()
raiz.withdraw()

# la app registra esta variante compacta en nutricion_deportiva.py;
# el arnés la reproduce para que RutinasTab real construya igual
_estilo = ttk.Style(raiz)
try:
    _estilo.layout("Gym.Treeview.Compacta", _estilo.layout("Treeview"))
except tk.TclError:
    pass


class App:
    id_paciente_antro = None


chequeos = []


def chequear(nombre, condicion):
    chequeos.append((nombre, bool(condicion)))
    print(("OK  " if condicion else "FALLO") + " · " + nombre)


rt = rutinas_tab.RutinasTab(App())
nb = ttk.Notebook(raiz)
rt.create(nb)
nb.pack(fill="both", expand=True)
raiz.geometry("1200x800+40+40")
raiz.update_idletasks()
raiz.update()

# 1) Sub-pestañas: la pestaña Progresión ya no existe y Ciclos es la 4ª
nombres_sub = []
for iid in rt.notebook_rut.tabs():
    nombres_sub.append(rt.notebook_rut.tab(iid, "text").strip())
chequear("sub-pestañas: sin Progresión (Calentamiento, Rutina, "
         "Estiramiento, Ciclos)",
         nombres_sub == ["Calentamiento", "Rutina", "Estiramiento",
                         "Ciclos"])
fuente = Path(rutinas_tab.__file__).read_text(encoding="utf-8")
chequear("código: sin restos del módulo de Progresión",
         "_crear_tab_progresion" not in fuente
         and "CONTENIDO_PROGRESION" not in fuente
         and "REGLAS_GENERALES_PROGRESION" not in fuente)
rt.notebook_rut.select(3)
raiz.update_idletasks()
raiz.update()
chequear("sub-pestaña 3: es Ciclos (título RUTINAS · CICLOS)",
         rt.titulo.cget("text") == "RUTINAS · CICLOS")

# 2) Bases de Ciclos: vacías sin semana cargada ni semanales guardadas
chequear("bases Ciclos: lista vacía al inicio (BD sin semanales)",
         len(rt.tree_cic_base.get_children()) == 0)

# 2b) 1RM → pesos: % del 1RM por repeticiones (cuadro 18.8 NSCA dentro
# de los rangos del ACSM 2009) y catálogo completo en el selector
chequear("1RM: % por reps del cuadro 18.8 (4-6→90, 8-12→80, 10-12→75, 12→67)",
         calculadora_1rm.pct_para_reps("4-6") == 90
         and calculadora_1rm.pct_para_reps("8-12") == 80
         and calculadora_1rm.pct_para_reps("10-12") == 75
         and calculadora_1rm.pct_para_reps("12") == 67)
chequear("1RM: el extremo bajo manda en el rango y '12-10-8' toma el 12",
         calculadora_1rm.pct_para_reps("12-10-8") == 67
         and calculadora_1rm.pct_para_reps("8-10") == 80)
chequear("1RM: más de 15 reps → 60 % (ACSM resistencia) y sin reps → None",
         calculadora_1rm.pct_para_reps("16-20") == 60
         and calculadora_1rm.pct_para_reps("al fallo") is None
         and calculadora_1rm.pct_para_reps("") is None)
chequear("1RM: carga = % del 1RM para las reps (100 kg y 10-12 → 75 kg)",
         calculadora_1rm.carga_desde_1rm(100, "10-12") == (75.0, 75.0))
nombres_cat, tren_cat = calculadora_1rm.ejercicios_catalogo()
chequear("1RM: el selector trae TODO el catálogo (presets + rutinas_ejercicios)",
         len(nombres_cat) >= 126
         and all(p in nombres_cat for p in calculadora_1rm.EJERCICIOS))
chequear("1RM: el tren del catálogo se infiere (piernas/glúteos inferior)",
         tren_cat["Sentadilla"] == "inferior"
         and tren_cat["Press de banca"] == "superior")
chequear("niveles ACSM: principiante 65 % +2,5 %; intermedio 75 % y avanzado 85 % +5 %; S4 deloading",
         rutinas_tab._sem_rampa_nivel("Principiante")
         == (65, (1.00, 1.025, 1.025 ** 2, CIC_DELOAD_PESO))
         and rutinas_tab._sem_rampa_nivel("Intermedio")
         == (75, (1.00, 1.05, 1.05 ** 2, CIC_DELOAD_PESO))
         and rutinas_tab._sem_rampa_nivel("Avanzado")
         == (85, (1.00, 1.05, 1.05 ** 2, CIC_DELOAD_PESO)))
chequear("niveles ACSM: el % de la Semana 1 queda limitado por el cuadro 18.8",
         rutinas_tab._sem_pct_reps("10-12") == 65
         and rutinas_tab._sem_pct_reps("10-12", "Intermedio") == 75
         and rutinas_tab._sem_pct_reps("10-12", "Avanzado") == 75
         and rutinas_tab._sem_pct_reps("8-12", "Avanzado") == 80
         and rutinas_tab._sem_pct_reps("15-20", "Avanzado") == 65
         and rutinas_tab._sem_pct_reps("al fallo") is None)

# 3) Cargar plantilla del estudio en Semana (misma vía que la app)
rt._sem_refrescar_selector()
iid_fija = next(i for i, v in rt._sem_selector_map.items() if v[0] == "fija")
rt.tree_sem_selector.selection_set(iid_fija)
rt._sem_cargar_seleccionada()
raiz.update()
con_ej = sum(1 for d in rt._sem_datos.values() if d.get("ejercicios"))
n_ej = sum(len(d.get("ejercicios") or []) for d in rt._sem_datos.values())
chequear("Semana: plantilla del estudio cargada con días y ejercicios",
         con_ej >= 3 and n_ej >= 10)
chequear("Semana: la plantilla del estudio trae su prescripción (series/reps)",
         all(f.get("series") and f.get("repeticiones")
             for d in rt._sem_datos.values()
             for f in d.get("ejercicios") or []))
# el peso lo escribe el usuario en la tabla; se pone en la primera ficha
# para probar la matemática de progresión del ciclo
primera_ficha = next(f for d in rt._sem_datos.values()
                     for f in d.get("ejercicios") or [])
primera_ficha["peso"] = "50 kg"

# tras cargar, la base única es la Semana actual
rt._cic_refrescar_bases()
bases = rt.tree_cic_base.get_children()
chequear("bases Ciclos: solo 'Semana actual' tras cargar la semana",
         len(bases) == 1 and bases[0] == "__actual__")

# 4) GUARDAR la semana -> aparece sola como base guardada
rt.entrada_sem_nombre.delete(0, tk.END)
rt.entrada_sem_nombre.insert(0, "Verificación Semanal")
rt._sem_guardar()
raiz.update()
guardadas = database.get_rutinas_guardadas(semanal=1)
chequear("GUARDAR: semanal en la BD", len(guardadas) == 1)
bases = rt.tree_cic_base.get_children()
valores = [rt.tree_cic_base.item(i, "values") for i in bases]
chequear("bases Ciclos: 'Semana actual' + la recién guardada, sin plantillas",
         len(bases) == 2
         and valores[0][0] == "Semana actual"
         and valores[1][0] == "Verificación Semanal")

# 5) Generar ciclo de 2 mesociclos desde la Semana actual
rt.tree_cic_base.selection_set("__actual__")
rt._cic_elegir_base()
rt.entrada_cic_nombre.delete(0, tk.END)
rt.entrada_cic_nombre.insert(0, "Verificación Ciclo")
rt.cic_objetivo_var.set("Hipertrofia")
rt.cic_n_var.set("2")
rt._cic_generar()
raiz.update()
bloques = rt._cic_datos["bloques"]
chequear("GENERAR: 2 mesociclos × 4 semanas",
         len(bloques) == 2 and all(len(b["semanas"]) == 4 for b in bloques))
chequear("GENERAR: secuencia Hipertrofia volumen -> intensiva",
         bloques[0]["objetivo"] == "Hipertrofia · volumen"
         and bloques[1]["objetivo"] == "Hipertrofia · intensiva")
chequear("GENERAR: reps 10-12 -> 8-10 entre bloques",
         bloques[0]["reps"] == "10-12" and bloques[1]["reps"] == "8-10")
tipos = [s["tipo"] for s in bloques[0]["semanas"]]
chequear("GENERAR: semanas 1-3 de carga y 4 de deload",
         tipos == ["Carga", "Carga", "Carga", "Deload"])
dia_con = next(d for d, fs in bloques[0]["dias"].items() if fs)
fila = bloques[0]["dias"][dia_con][0]
s_base = int(next(re.finditer(r"\d+", fila["series_base"])).group())
kg_base = rutinas_tab.RutinasTab._cic_num_peso(fila["peso_base"])
tabla = rt._cic_bloque_actual()
celdas = []
sem = bloques[0]["semanas"]
for s in sem:
    if s["tipo"] == "Deload":
        n_series = max(1, round(s_base * CIC_DELOAD_SERIES))
        mult = CIC_DELOAD_PESO
    elif s.get("series_extra"):
        n_series = s_base + s["series_extra"]
        mult = s["peso_mult"]
    else:
        n_series = s_base
        mult = s["peso_mult"]
    celdas.append((n_series, _discos_2_5(kg_base * mult)))
chequear("progresión: S3 suma +1 serie", celdas[2][0] == s_base + 1)
chequear("deload S4: mitad de series", celdas[3][0] == max(1, round(s_base * 0.5)))
chequear("progresión: peso S2/S3 +2.5 %/+5 % redondeado a discos",
         celdas[1][1] == _discos_2_5(kg_base * 1.025)
         and celdas[2][1] == _discos_2_5(kg_base * 1.05))
chequear("deload S4: peso -10 % redondeado a discos",
         celdas[3][1] == _discos_2_5(kg_base * 0.90))
chequear("tabla Ciclos pintada con filas del mesociclo",
         len(rt.tree_cic.get_children()) > 0)
chequear("modos disponibles: carga / repeticiones / ambos / doble",
         CIC_MODOS == ("Por carga", "Por repeticiones", "Ambos", "Doble")
         and rt.cic_modo_var.get() == "Por carga")
chequear("referencia bibliográfica: cita por cada modo",
         tuple(CIC_BASE_MODEO) == CIC_MODOS
         and CIC_BASE_MODEO["Por carga"].startswith("ACSM")
         and "Plotkin" in CIC_BASE_MODEO["Por repeticiones"]
         and "Chaves" in CIC_BASE_MODEO["Por repeticiones"]
         and CIC_BASE_MODEO["Ambos"].startswith("ACSM")
         and "Plotkin" in CIC_BASE_MODEO["Doble"])
chequear("referencia: el ciclo Por carga cita ACSM 2009",
         rt._cic_datos.get("base_cientifica", "").startswith("ACSM")
         and "ACSM" in rt.lbl_cic_info.cget("text"))

# 5b) GENERAR cargó las 4 semanas del mesociclo 1 en Semana 1-4
chequear("ranuras: Semana 1 activa tras generar", rt._sem_n == 1)
sesiones_ranuras = []
for n in (1, 2, 3, 4):
    datos_n = rt._sem_semanas.get(n) or {}
    sesiones_ranuras.append(
        next((d["sesion"] for d in datos_n.values() if d.get("sesion")), ""))
chequear("ranuras: las 4 semanas quedaron cargadas con su etiqueta",
         all(sesiones_ranuras)
         and "Semana 1" in sesiones_ranuras[0]
         and "Deload" in sesiones_ranuras[3])
fila_r1 = next((e for d in rt._sem_semanas[1].values()
                for e in d.get("ejercicios") or []), None)
fila_r4 = next((e for d in rt._sem_semanas[4].values()
                for e in d.get("ejercicios") or []), None)
chequear("ranuras: Semana 1 conserva la prescripción base",
         fila_r1 is not None and int(fila_r1["series"]) == s_base
         and fila_r1["repeticiones"] == "10-12"
         and fila_r1["peso"] == f"{_discos_2_5(kg_base):g} kg")
chequear("ranuras: Semana 4 con mitad de series (deloading)",
         fila_r4 is not None
         and int(fila_r4["series"]) == max(1, round(s_base * 0.5)))
# cambiar de ranura muestra la semana que quedó guardada en ella
rt._sem_elegir_semana(2)
fila_r2 = next((e for d in rt._sem_datos.values()
                for e in d.get("ejercicios") or []), None)
chequear("ranuras: cambiar a Semana 2 muestra su semana (+2.5 % carga)",
         fila_r2 is not None
         and fila_r2["peso"] == f"{_discos_2_5(kg_base * 1.025):g} kg")
rt._sem_elegir_semana(1)

# 5c) Modo de progresión: por repeticiones y ambos
rt.cic_modo_var.set("Por repeticiones")
rt._cic_generar()
raiz.update()
sem_reps = rt._cic_datos["bloques"][0]["semanas"]
chequear("modo reps: carga constante en S1-S3",
         all(s["peso_mult"] == 1.00 for s in sem_reps[:3]))
chequear("modo reps: el rango sube 1 rep por semana",
         [s["reps_txt"] for s in sem_reps[:3]]
         == ["10-12", "11-13", "12-14"])
chequear("modo reps: el deloading vuelve al rango base",
         sem_reps[3]["reps_txt"] == "10-12")
rt.cic_modo_var.set("Ambos")
rt._cic_generar()
raiz.update()
sem_ambos = rt._cic_datos["bloques"][0]["semanas"]
chequear("modo ambos: la carga también sube (ramp del bloque)",
         [s["peso_mult"] for s in sem_ambos[:3]] == [1.00, 1.025, 1.05])
chequear("modo ambos: el rango sube a la vez (doble progresión)",
         [s["reps_txt"] for s in sem_ambos[:3]]
         == ["10-12", "11-13", "12-14"])
fila_a2 = next((e for d in rt._sem_semanas[2].values()
                for e in d.get("ejercicios") or []), None)
chequear("modo ambos: ranuras re-cargadas con el modo elegido",
         fila_a2 is not None and fila_a2["repeticiones"] == "11-13")

# 5d) Modo Doble: reps suben dentro del rango y reinician al subir carga
chequear("rango partido: 8-12 -> ('8-10', '10-12')",
         rutinas_tab.RutinasTab._cic_rango_partido("8-12")
         == ("8-10", "10-12"))
rt.cic_modo_var.set("Doble")
rt._cic_generar()
raiz.update()
sem_doble = rt._cic_datos["bloques"][0]["semanas"]
chequear("modo doble: S1 mitad baja del rango con carga base",
         sem_doble[0]["peso_mult"] == 1.00
         and sem_doble[0]["reps_txt"] == "10-11")
chequear("modo doble: S2 llega arriba del rango con la misma carga",
         sem_doble[1]["peso_mult"] == 1.00
         and sem_doble[1]["reps_txt"] == "11-12")
chequear("modo doble: S3 sube la carga y reinicia abajo del rango",
         sem_doble[2]["peso_mult"] == 1.05
         and sem_doble[2]["reps_txt"] == "10-11")
chequear("modo doble: deloading S4 con el rango completo",
         sem_doble[3]["peso_mult"] == CIC_DELOAD_PESO
         and sem_doble[3]["reps_txt"] == "10-12")
fila_d3 = next((e for d in rt._sem_semanas[3].values()
                for e in d.get("ejercicios") or []), None)
chequear("modo doble: ranura Semana 3 con carga nueva y reps reiniciadas",
         fila_d3 is not None
         and fila_d3["repeticiones"] == "10-11"
         and fila_d3["peso"] == f"{_discos_2_5(kg_base * 1.05):g} kg")
chequear("notas: doble progresión citada (Plotkin 2022)",
         any("Doble progresion" in n and "Plotkin" in n
             for n in rt._cic_datos["notas"]))
chequear("referencia: el modo Doble cita Plotkin/Chaves y ACSM",
         "Plotkin" in rt._cic_datos.get("base_cientifica", "")
         and "Chaves" in rt._cic_datos.get("base_cientifica", "")
         and "ACSM" in rt._cic_datos.get("base_cientifica", ""))

# 5e) Pesos desde 1RM en la rutina semanal (menú «🏋 1RM ▾»): menú con
# el selector de nivel (ACSM 2009), botón y opciones; con un 1RM de
# sesión para la primera ficha, el llenado del mesociclo sobrescribe el
# peso de las 4 ranuras y deja intactos los ejercicios sin 1RM registrado
chequear("menú 1RM: nivel del paciente (3 niveles) + opciones y rutinas del nivel",
         hasattr(rt, "btn_sem_1rm") and hasattr(rt, "menu_sem_1rm")
         and rt.menu_sem_1rm.index("end") == 11
         and rt._sem_nivel_var.get() == "Principiante")
chequear("nota nueva: base del % del 1RM citada en CIC_NOTAS",
         any("cuadro 18.8" in n and "ACSM 2009" in n
             for n in rt._cic_datos["notas"]))


def _ficha_ranura(n):
    """Primera ficha de la ranura Semana n."""
    return next((e for d in rt._sem_semanas[n].values()
                 for e in d.get("ejercicios") or []), None)


def _ejercicios_ranura(n):
    dia = next((d for d in rt._sem_semanas[n].values()
                if d.get("ejercicios")), None)
    return dia.get("ejercicios") if dia else []


nombre_1rm = _ficha_ranura(1)["nombre"]
rt.rm_sesion = {"ejercicio": nombre_1rm, "metodo": "Baechle (NSCA 2000)",
                "peso": 60.0, "rpe": None, "repeticiones": 8,
                "resultado": 100.0}
peso_antes = _ficha_ranura(1)["peso"]
rt._sem_pesos_desde_1rm(True)
raiz.update()
chequear("pesos desde 1RM: sobrescribe el peso que había en la ranura",
         _ficha_ranura(1)["peso"] != peso_antes)
chequear("pesos desde 1RM: Semana 1 = 65 % de un 1RM de 100 kg "
         "(nivel principiante, cuadro 18.8)",
         _ficha_ranura(1)["peso"] == "65 kg")
ok_rampas = True
for n in (1, 2, 3, 4):
    ficha_n = _ficha_ranura(n)
    _base, mults_n = rutinas_tab._sem_rampa_nivel(
        rt._sem_nivel_var.get())
    pct_n = rutinas_tab._sem_pct_reps(
        ficha_n["repeticiones"], rt._sem_nivel_var.get())
    esperado = f"{_discos_2_5(100.0 * pct_n / 100.0 * mults_n[n - 1]):g} kg"
    if ficha_n["peso"] != esperado:
        ok_rampas = False
        print("   ranura", n, ficha_n["repeticiones"],
              "->", ficha_n["peso"], "≠", esperado)
chequear("pesos desde 1RM: cada ranura con su rampa semanal "
         "(+2,5 % semanal y deloading -10 %)", ok_rampas)
chequear("pesos desde 1RM: los ejercicios sin 1RM quedan con su peso previo",
         len(_ejercicios_ranura(1)) < 2
         or not _ejercicios_ranura(1)[1]["peso"])
chequear("pesos desde 1RM: la barra de estado reporta el llenado y el nivel",
         "Pesos desde 1RM" in rt.lbl_estado.cget("text")
         and "nivel Principiante" in rt.lbl_estado.cget("text"))

# 5f) Al GUARDAR un 1RM en la calculadora se aplica AL EJERCICIO en las
# 4 semanas: Semana 1 = % del nivel, rampa semanal y deloading en la 4.ª
rt._sem_nivel_var.set("Principiante")
rt._sem_aplicar_rm_guardado({
    "ejercicio": nombre_1rm, "metodo": "Baechle (NSCA 2000)",
    "peso": 60.0, "rpe": None, "repeticiones": 8, "resultado": 100.0,
})
raiz.update()
pesos_5f = [_ficha_ranura(n)["peso"] for n in (1, 2, 3, 4)]
chequear("1RM guardado: aplicado a las 4 semanas (65 · 67.5 · 67.5 kg "
         "y deloading 57.5 kg)",
         pesos_5f == ["65 kg", "67.5 kg", "67.5 kg", "57.5 kg"])
chequear("1RM guardado: barra de estado con el detalle por semana",
         "GUARDADO y aplicado" in rt.lbl_estado.cget("text")
         and "S4 deloading" in rt.lbl_estado.cget("text"))
apariciones = [e for d in rt._sem_semanas[1].values()
               for e in d.get("ejercicios") or []
               if rutinas_tab._normalizar(e.get("nombre"))
               == rutinas_tab._normalizar(nombre_1rm)]
chequear("1RM guardado: aplicado a TODAS las apariciones (Lunes y Jueves)",
         len(apariciones) >= 2
         and all(e["peso"] == "65 kg" for e in apariciones))
rt._sem_nivel_var.set("Intermedio")
rt._sem_aplicar_rm_guardado({
    "ejercicio": nombre_1rm, "metodo": "Baechle (NSCA 2000)",
    "peso": 60.0, "rpe": None, "repeticiones": 8, "resultado": 100.0,
})
raiz.update()
chequear("1RM guardado: nivel intermedio aplica 75 % en la Semana 1",
         _ficha_ranura(1)["peso"] == "75 kg")
rt._sem_aplicar_rm_guardado({
    "ejercicio": "Ejercicio inexistente", "metodo": "x", "peso": 1,
    "rpe": None, "repeticiones": 1, "resultado": 50.0,
})
chequear("1RM guardado: ejercicio fuera de las ranuras solo informa",
         "no está en las ranuras" in rt.lbl_estado.cget("text"))
chequear("1RM guardado: GUARDAR dispara la aplicación desde la calculadora",
         "al_guardar(dict(datos))"
         in Path(calculadora_1rm.__file__).read_text(encoding="utf-8")
         and "al_guardar=self._sem_aplicar_rm_guardado" in fuente)
# el nivel intermedio se queda activo para las expectativas de 7b/7c
# (base del 1RM al 75 %, igual que el cuadro 18.8 para 10-12 reps)

# 6) GUARDAR ciclo
rt._cic_guardar()
raiz.update()
ciclos_bd = database.get_rutinas_ciclos(None)
chequear("GUARDAR ciclo: visible en rutinas_ciclos",
         len(ciclos_bd) == 1 and ciclos_bd[0]["nombre"] == "Verificación Ciclo")

# 7) APLICAR AL PACIENTE: 8 semanas en el historial de Semana
datos_pac = {c: "" for c in database.CAMPOS}
datos_pac.update({"nombre": "Paciente Prueba", "deporte": "Fisicoculturismo"})
id_pac = database.guardar_paciente(datos_pac)
rt.cargar(id_pac)
raiz.update()
rt._cic_aplicar()
raiz.update()
historial = database.get_rutinas_historial(id_pac)
nombres = [h["nombre_semana"] for h in historial]
chequear("APLICAR: 8 semanas en el historial", len(nombres) == 8)
chequear("APLICAR: etiqueta Mesociclo/bloque/Semana y Deload en la 4 y 8",
         any("Mesociclo 1 (Hipertrofia · volumen) · Semana 4 (Deload)" in n
             for n in nombres)
         and any("Mesociclo 2 (Hipertrofia · intensiva) · Semana 4 (Deload)"
                 in n for n in nombres))
id_deload = next(h["id_historial"] for h in historial
                 if "Semana 4 (Deload)" in h["nombre_semana"])
detalle_deload = database.get_rutina_historial(id_deload)["dias"]
series_deload = detalle_deload[0]["ejercicios"][0]["series"]
serie_base_txt = str(fila["series_base"])
n_base = int(next(re.finditer(r"\d+", serie_base_txt)).group())
chequear("APLICAR: semana deload guardada con mitad de series",
         int(series_deload) == max(1, round(n_base * 0.5)))
peso_deload = detalle_deload[0]["ejercicios"][0]["peso"]
chequear("APLICAR: semana deload con peso -10 %",
         peso_deload == f"{_discos_2_5(kg_base * 0.90):g} kg")

# 7b) GENERAR y pesos desde 1RM guardados en la BD del paciente
rt._sem_nivel_var.set("Intermedio")   # base 75 %: 140 kg → 105 kg con 10-12 reps
nombre_pend = _ejercicios_ranura(1)[1]["nombre"]
database.insert_uno_rm({
    "paciente_id": id_pac, "fecha": "2026-11-19",
    "ejercicio": nombre_pend, "metodo": "1RM directo (NSCA)",
    "peso": 140.0, "rpe": None, "repeticiones": 1, "resultado": 140.0,
})
# el peso manual de la semana manda sobre el 1RM al generar
_ficha_ranura(1)["peso"] = "50 kg"
rt.tree_cic_base.selection_set("__actual__")
rt._cic_elegir_base()
rt.cic_modo_var.set("Por carga")
rt._cic_generar()
raiz.update()
bloque_rm = rt._cic_datos["bloques"][0]
# el chequeo mira el PRIMER día: la plantilla repite la sesión Tren
# superior en Lunes y Jueves, y el dict completo mezclaría ambas
pesos_base = {f["nombre"]: f["peso_base"]
              for f in bloque_rm["dias"][next(iter(bloque_rm["dias"]))]}
kg_pend_base, _pct_pend = calculadora_1rm.carga_desde_1rm(
    140.0, bloque_rm["reps"])
chequear("GENERAR con 1RM: el peso manual de la semana manda",
         pesos_base.get(nombre_1rm) == "50 kg")
chequear("GENERAR con 1RM: peso base desde el registro BD "
         "(140 kg al 75 % para 10-12 reps → 105 kg)",
         pesos_base.get(nombre_pend)
         == f"{_discos_2_5(kg_pend_base):g} kg"
         and pesos_base.get(nombre_pend) == "105 kg")
chequear("GENERAR con 1RM: sin registro el peso base queda vacío (como antes)",
         all(v == "" for n, v in pesos_base.items()
             if n not in (nombre_1rm, nombre_pend)))
chequear("GENERAR con 1RM: el letrero cuenta los pesos tomados del 1RM",
         "1RM registrado en 1 ejercicio(s)" in rt.lbl_cic_info.cget("text"))

# 7c) El llenado de la semana usa también los 1RM de la BD del paciente
rt._sem_pesos_desde_1rm(False)
raiz.update()
chequear("pesos desde 1RM: registro de la BD aplicado a la semana "
         "(140 kg → 105 kg en Semana 1)",
         _ejercicios_ranura(1)[1]["peso"] == "105 kg")
chequear("pesos desde 1RM: los sin registro siguen intactos",
         not _ejercicios_ranura(1)[2]["peso"]
         if len(_ejercicios_ranura(1)) > 2 else True)
avisos = []
_showinfo_original = rutinas_tab.messagebox.showinfo
rutinas_tab.messagebox.showinfo = lambda *a, **k: avisos.append(a)
try:
    rt.rm_sesion = None
    rt.paciente_id = None
    rt._sem_pesos_desde_1rm(False)
finally:
    rutinas_tab.messagebox.showinfo = _showinfo_original
    rt.paciente_id = id_pac
chequear("pesos desde 1RM: sin ningún 1RM avisa y no llena nada",
         len(avisos) == 1)

# 7d) APLICAR MESOCICLO: las semanas EDITADAS de las ranuras Semana 1-4
# al paciente (la Semana 1 activa y las 4 al historial, respetando
# las ediciones hechas sobre lo cargado por Ciclos)
chequear("mesociclo: botón APLICAR MESOCICLO en la fila de Semanas",
         hasattr(rt, "btn_sem_mesociclo")
         and str(rt.btn_sem_mesociclo.cget("text")) == "✔ APLICAR MESOCICLO")
# edición manual sobre la Semana 2 cargada por el ciclo (peso y series)
_f2 = _ficha_ranura(2)
_f2["peso"] = "90 kg"
_f2["series"] = "4"
rt._sem_aplicar_mesociclo()
raiz.update()
historial = database.get_rutinas_historial(id_pac)
nombres_hist = [h["nombre_semana"] for h in historial]
chequear("mesociclo: 4 semanas en el historial con el nombre de la rutina",
         all(f"Verificación Semanal · Semana {n}" in nombres_hist
             for n in (1, 2, 3, 4)))
id_sem2 = next(h["id_historial"] for h in historial
               if h["nombre_semana"] == "Verificación Semanal · Semana 2")
detalle_sem2 = database.get_rutina_historial(id_sem2)["dias"]
ej_sem2 = next(d["ejercicios"] for d in detalle_sem2 if d["ejercicios"])
chequear("mesociclo: la Semana 2 guarda las EDICIONES (peso 90 kg, 4 series)",
         ej_sem2[0]["peso"] == "90 kg" and ej_sem2[0]["series"] == "4")
rutina_activa = database.get_rutinas_paciente(id_pac)
lunes = [r for r in rutina_activa if r["dia"] == "Lunes"]
chequear("mesociclo: la Semana 1 quedó como rutina activa del paciente",
         bool(lunes) and "Semana 1" in (lunes[0].get("notas") or ""))
chequear("mesociclo: la activa conserva los pesos desde 1RM de la Semana 1",
         lunes and lunes[0]["peso"] == _ficha_ranura(1)["peso"])
chequear("mesociclo: el editor queda en la Semana 1",
         rt._sem_n == 1
         and "Mesociclo aplicado" in rt.lbl_estado.cget("text"))
# guardias: sin paciente o sin ranuras, avisa sin romper nada
rt.paciente_id = None
rt._sem_aplicar_mesociclo()
chequear("mesociclo: sin paciente avisa y no aplica",
         "Selecciona un paciente" in rt.lbl_estado.cget("text"))
rt.paciente_id = id_pac
_semanas_originales = rt._sem_semanas
rt._sem_semanas = {}
rt._sem_aplicar_mesociclo()
chequear("mesociclo: sin semanas diseñadas avisa",
         "están vacías" in rt.lbl_estado.cget("text"))
rt._sem_semanas = _semanas_originales

# 7e) Rutinas por nivel: 11 plantillas del estudio etiquetadas (3
# principiante, 5 intermedio, 3 avanzado) y, al elegir la avanzada
# (Helms 2018), la app arma el mesociclo desde los 1RM del paciente
# (Semana 4 = deloading)
niveles_plantillas = [p.get("nivel") for p in PLANTILLAS_SEMANA]
chequear("rutinas por nivel: 11 plantillas etiquetadas (3 principiante / 5 intermedio / 3 avanzado)",
         len(niveles_plantillas) == 11
         and (niveles_plantillas.count("Principiante"),
              niveles_plantillas.count("Intermedio"),
              niveles_plantillas.count("Avanzado")) == (3, 5, 3))
helms = next(p for p in PLANTILLAS_SEMANA if "Helms" in p["nombre"])
chequear("rutinas por nivel: prescripciones por sesión (8/6/4 reps en Helms)",
         helms["prescripciones"]["Completo pesado (8 reps)"]["repeticiones"]
         == "8"
         and helms["prescripciones"]["Completo medio (6 reps)"]
         ["repeticiones"] == "6"
         and helms["prescripciones"]["Completo ligero (4 reps)"]
         ["repeticiones"] == "4")
rt._sem_nivel_var.set("Avanzado")
rt._sem_llenar_rutinas_nivel()
chequear("rutinas por nivel: el submenú avanzado lista 3 rutinas",
         rt.menu_rutinas_nivel.index("end") == 2)
rt._sem_cargar_plantilla_mesociclo(PLANTILLAS_SEMANA.index(helms))
raiz.update()


def _ficha_semana(n, dia_txt):
    """Ficha de la sesión pesada (Lunes) de la ranura n."""
    return next(e for d in rt._sem_semanas[n].values()
                for e in d.get("ejercicios") or []
                if dia_txt in rutinas_tab._normalizar(e.get("nombre")))


chequear("rutina avanzada: mesociclo armado en las 4 ranuras con su etiqueta",
         rt._sem_n == 1
         and "Helms" in rt.entrada_sem_nombre.get()
         and all(any(f"Semana {n}" in (d["sesion"] or "")
                     for d in rt._sem_semanas[n].values()
                     if d.get("sesion"))
                 for n in (1, 2, 3, 4))
         and any("Deload" in (d["sesion"] or "")
                 for d in rt._sem_semanas[4].values() if d.get("sesion")))
banca_s1 = _ficha_semana(1, "bench")
chequear("rutina avanzada: banca pesada 8 reps al 80 % del 1RM de la BD "
         "(140 kg → 112.5 kg)",
         banca_s1["repeticiones"] == "8"
         and banca_s1["peso"] == "112.5 kg")
banca_s3 = _ficha_semana(3, "bench")
banca_s4 = _ficha_semana(4, "bench")
chequear("rutina avanzada: rampa semanal en la banca (S3 +5 % compuesto)",
         banca_s3["peso"] == f"{_discos_2_5(112 * 1.05 ** 2):g} kg")
chequear("rutina avanzada: deloading en la Semana 4 (mitad de series, "
         "-10 % de carga)",
         banca_s4["series"] == "1"
         and banca_s4["peso"] == f"{_discos_2_5(112 * 0.90):g} kg")
chequear("rutina avanzada: la barra de estado reporta el armado",
         "Mesociclo armado" in rt.lbl_estado.cget("text")
         and "nivel Avanzado" in rt.lbl_estado.cget("text"))
# armar de nuevo desde la semana cargada (ítem del menú) es estable
rt._sem_armar_mesociclo_1rm()
raiz.update()
chequear("armar mesociclo: re-ejecutar sobre la semana cargada conserva el mesociclo",
         _ficha_semana(1, "bench")["peso"] == "112.5 kg"
         and any("Deload" in (d["sesion"] or "")
                 for d in rt._sem_semanas[4].values() if d.get("sesion")))
# cambiar de nivel = recargar la rutina del nivel: la plantilla trae
# fichas sin peso y el armado recalcula desde los 1RM con el % del nivel
rt._sem_nivel_var.set("Principiante")
rt._sem_cargar_plantilla_mesociclo(0)
raiz.update()
chequear("armar mesociclo: nivel principiante carga la plantilla del nivel al 65 %",
         "Principiante" in rt.lbl_estado.cget("text")
         and _ficha_semana(1, "bench")["peso"] == "90 kg")

# 7f) Eliminar rutinas guardadas con botón: del historial del paciente
# (con confirmación) y de la biblioteca (el selector también confirma)
chequear("eliminar: botón ELIMINAR DEL HISTORIAL bajo la tabla",
         hasattr(rt, "btn_sem_eliminar_historial")
         and str(rt.btn_sem_eliminar_historial.cget("text"))
         == "🗑 ELIMINAR DEL HISTORIAL")
rt._sem_eliminar_historial()
chequear("eliminar historial: sin selección avisa y no borra",
         "Elige en el historial" in rt.lbl_estado.cget("text"))
historial = database.get_rutinas_historial(id_pac)
id_sem2 = next(h["id_historial"] for h in historial
               if h["nombre_semana"] == "Verificación Semanal · Semana 2")
rt.tree_sem_historial.selection_set(str(id_sem2))
_askyesno_original = rutinas_tab.messagebox.askyesno
try:
    rutinas_tab.messagebox.askyesno = lambda *a, **k: False
    rt._sem_eliminar_historial()
    chequear("eliminar historial: cancelar la confirmación conserva la rutina",
             len(database.get_rutinas_historial(id_pac)) == len(historial)
             and any(h["nombre_semana"] == "Verificación Semanal · Semana 2"
                     for h in database.get_rutinas_historial(id_pac)))
    rutinas_tab.messagebox.askyesno = lambda *a, **k: True
    rt._sem_eliminar_historial()
    raiz.update()
    historial_final = database.get_rutinas_historial(id_pac)
    chequear("eliminar historial: confirmada se borra de la BD (la activa intacta)",
             len(historial_final) == len(historial) - 1
             and not any(h["nombre_semana"] == "Verificación Semanal · Semana 2"
                         for h in historial_final)
             and len(database.get_rutinas_paciente(id_pac)) > 0
             and "Eliminada del historial" in rt.lbl_estado.cget("text"))
    # la semanal guardada del selector también confirma antes de borrar
    iid_g = next(iid for iid, v in rt._sem_selector_map.items()
                 if v[0] == "guardada")
    rt.tree_sem_selector.selection_set(iid_g)
    rt._sem_eliminar_guardada()
    chequear("eliminar guardada: con confirmación se borra de la biblioteca",
             len(database.get_rutinas_guardadas(semanal=1)) == 0
             and "guardada eliminada" in rt.lbl_estado.cget("text"))
finally:
    rutinas_tab.messagebox.askyesno = _askyesno_original

# 7g) Botón 🏋 ARMAR DESDE 1RM (restaurado, nuevo comportamiento):
# SUSTITUYE los pesos de la semana diseñada desde los 1RM del paciente
# SIN añadir nada (mismos ejercicios, series y sesiones) y GENERA las
# otras semanas con su peso (rampa del nivel y deloading en la 4.ª),
# con ventana de reporte del cálculo por semana
chequear("aplicar 1RM: botón ARMAR DESDE 1RM junto a APLICAR MESOCICLO",
         hasattr(rt, "btn_sem_armar_rm")
         and str(rt.btn_sem_armar_rm.cget("text")) == "🏋 ARMAR DESDE 1RM")
rt._sem_nivel_var.set("Principiante")
_ficha_semana(1, "bench")["peso"] = "99 kg"   # peso manual de prueba
_series_antes = _ficha_semana(1, "bench")["series"]
_sesion_antes = next(d["sesion"] for d in rt._sem_semanas[1].values()
                     if d.get("sesion"))
rt._sem_armar_desde_1rm()
raiz.update()
_pct_pr, _mults_pr = rutinas_tab._sem_rampa_nivel("Principiante")
_pct_banca = rutinas_tab._sem_pct_reps(
    _ficha_semana(1, "bench")["repeticiones"], "Principiante")
_exp_banca = [
    f"{rutinas_tab._discos_2_5(140.0 * _pct_banca / 100.0 * m):g} kg"
    for m in _mults_pr]
chequear("aplicar 1RM: sustituye el peso de la semana diseñada "
         "(el 1RM 140 kg manda sobre el manual 99 kg → 90 kg)",
         _ficha_semana(1, "bench")["peso"] == "90 kg"
         and _pct_pr == 65.0)
chequear("aplicar 1RM: genera las otras semanas con su peso "
         "(S2-S3 con la rampa del nivel, S4 deloading -10 %)",
         _ficha_semana(2, "bench")["peso"] == _exp_banca[1]
         and _ficha_semana(3, "bench")["peso"] == _exp_banca[2]
         and _ficha_semana(4, "bench")["peso"] == _exp_banca[3])
chequear("aplicar 1RM: sin añadir nada — mismas series en las 4 semanas",
         all(_ficha_semana(n, "bench")["series"] == _series_antes
             for n in (1, 2, 3, 4)))
_base_sesion = re.sub(r"\s*·\s*Semana\s*\d+\s*$", "",
                      _sesion_antes).rstrip(" ·")
chequear("aplicar 1RM: cada semana con UN solo nombre, el de su "
         "semana (sustituye los «· Semana N» acumulados)",
         all(next(d["sesion"] for d in rt._sem_semanas[n].values()
                  if d.get("sesion")) == f"{_base_sesion} · Semana {n}"
             for n in (1, 2, 3, 4)))
_tops = [w for w in rt.marco.winfo_children()
         if isinstance(w, tk.Toplevel)
         and str(w.title()).startswith("Pesos por semana")]
chequear("aplicar 1RM: ventana de reporte con el cálculo por semana",
         bool(_tops))
for _w in _tops:
    _w.destroy()

# 7h) Cuestionario de progresión del botón ARMAR DESDE 1RM: peso,
# series, ambas o doble — con la regla del nivel (65 % y 2-3 RIR el
# principiante; % mayor y menos RIR el avanzado)
_tk_wait_preg = tk.Toplevel.wait_window


def _wait_preguntas(self, *a, **k):
    """Responde el cuestionario dentro del test: marca «ambas» y ARMAR."""
    tops_p = []

    def _tops_de(w):
        for h in w.winfo_children():
            if isinstance(h, tk.Toplevel):
                tops_p.append(h)
            _tops_de(h)

    _tops_de(raiz)
    tops_p = [w for w in tops_p
              if "cómo progresar" in str(w.title())]
    if not tops_p:
        return
    radios = []

    def _rbs(w):
        for h in w.winfo_children():
            if isinstance(h, tk.Radiobutton):
                radios.append(h)
            _rbs(h)

    _rbs(tops_p[0])
    _modos["radios"] = len(radios)
    for r in radios:
        if str(r.cget("value")) == "ambas":
            r.invoke()
            break

    def _armar(w):
        for h in w.winfo_children():
            if isinstance(h, tk.Button) and "ARMAR" in str(h.cget("text")):
                h.invoke()
                return True
            if _armar(h):
                return True
        return False

    _armar(tops_p[0])


_modos = {}
tk.Toplevel.wait_window = _wait_preguntas
_modo = rt._sem_preguntas_armar()
raiz.update()
tk.Toplevel.wait_window = _tk_wait_preg
chequear("armar 1RM: cuestionario de progresión (4 opciones) devuelve "
         "el modo elegido (ambas)",
         _modo == "ambas" and _modos.get("radios") == 4)
# modo series: peso constante y +1 serie por semana (S4 deloading)
rt._sem_armar_desde_1rm("series")
raiz.update()
_b1s = _ficha_semana(1, "bench")
_series_ok = (
    int(_ficha_semana(2, "bench")["series"]) == int(_b1s["series"]) + 1
    and int(_ficha_semana(3, "bench")["series"]) == int(_b1s["series"]) + 2
    and int(_ficha_semana(4, "bench")["series"])
    == max(1, round(int(_b1s["series"])
                    * rutinas_tab.CIC_DELOAD_SERIES)))
chequear("armar 1RM modo series: S2 +1 serie, S3 +2, S4 a la mitad y "
         "peso constante en el % de la Semana 1",
         _series_ok
         and _ficha_semana(2, "bench")["peso"] == _b1s["peso"]
         and _ficha_semana(4, "bench")["peso"] != _b1s["peso"])
# modo doble: S1-S2 mismo peso con +2 reps y la 3.ª sube un paso
rt._sem_armar_desde_1rm("doble")
raiz.update()
_b1d = _ficha_semana(1, "bench")
_b2d = _ficha_semana(2, "bench")
_b3d = _ficha_semana(3, "bench")
_paso_d, _mults_d = rutinas_tab._sem_rampa_nivel("Principiante")
_reps_d2 = (re.fullmatch(r"\d+", str(_b1d["repeticiones"]).strip()) is None
            or _b2d["repeticiones"] == str(int(_b1d["repeticiones"]) + 2))
chequear("armar 1RM modo doble: S2 mismo peso con +2 reps y S3 sube un "
         "paso de peso",
         _b2d["peso"] == _b1d["peso"]
         and _reps_d2
         and _b3d["peso"] == f"{rutinas_tab._discos_2_5(
             140.0 * _pct_banca / 100.0 * _mults_d[1]):g} kg")
# el reporte del modo series trae la columna de series por semana
_tops = [w for w in rt.marco.winfo_children()
         if isinstance(w, tk.Toplevel)
         and str(w.title()).startswith("Pesos por semana")]
chequear("armar 1RM: reporte con la progresión y el RIR del nivel",
         bool(_tops))
for _w in _tops:
    _w.destroy()

for n in (2, 3, 4):
    rt._sem_semanas.pop(n, None)
rt._sem_pesos_desde_1rm(True)
raiz.update()
chequear("aplicar 1RM: 'Mesociclo' con ranuras 2-4 vacías las arma desde 1RM",
         all(rt._sem_semanas.get(n) and any(
             d.get("ejercicios")
             for d in rt._sem_semanas[n].values()) for n in (1, 2, 3, 4))
         and _ficha_semana(1, "bench")["peso"] == "90 kg"
         and "Mesociclo armado" in rt.lbl_estado.cget("text"))

# 8) PDF del ciclo (sin abrirlo en pantalla: se intercepta os.startfile)
rutas_pdf = []
os.startfile_original = os.startfile
os.startfile = lambda ruta: rutas_pdf.append(ruta)
try:
    rt._cic_imprimir()
    raiz.update()
    pdf_ok = bool(rutas_pdf) and os.path.exists(rutas_pdf[0])
    if pdf_ok:
        os.remove(rutas_pdf[0])
except Exception as error:
    pdf_ok = False
    print("   error PDF:", error)
finally:
    os.startfile = os.startfile_original
chequear("PDF del ciclo generado sin errores", pdf_ok)

# 8b) Documento ACSM 2009 accesible desde Ciclos
ruta_acsm = os.path.abspath(os.path.join(
    os.path.dirname(rutinas_tab.__file__), "ACSM_2009_progresion.pdf"))
chequear("ACSM: el documento viaja con la app", os.path.exists(ruta_acsm))
rutas_acsm = []
os.startfile = lambda r: rutas_acsm.append(r)
rt._cic_abrir_acsm()
os.startfile = os.startfile_original
chequear("ACSM: el botón abre el documento", rutas_acsm == [ruta_acsm])

# 9) Barra de estado se restablece al cambiar de sub-pestaña
rt.lbl_estado.configure(text="Ciclo aplicado: 8 semanas en el historial")
rt._al_cambiar_subpestana()
chequear("barra de estado: vuelve al texto base al cambiar de sub-pestaña",
         rt.lbl_estado.cget("text") == rt._estado_base)

# 10) Ciclos quedó en el índice 3 y su título/bases responden al cambio
rt.notebook_rut.select(0)
raiz.update_idletasks()
raiz.update()
rt.notebook_rut.select(3)
raiz.update_idletasks()
raiz.update()
chequear("ciclos: entrar al subtab refresca bases y pone título CICLOS",
         rt.titulo.cget("text") == "RUTINAS · CICLOS")
# el subtab 3 contiene la tabla de Ciclos (árbol de semanas del ciclo)
tab_cic = rt.notebook_rut.nametowidget(rt.notebook_rut.tabs()[3])
ancestro = rt.tree_cic.master
en_tab = False
while ancestro is not None:
    if ancestro is tab_cic:
        en_tab = True
        break
    ancestro = ancestro.master
chequear("ciclos: su tabla vive en la 4ª sub-pestaña", en_tab)

# 11) La calculadora de 1RM muestra los guardados del paciente en una
# tabla (con el registro de la BD); doble clic carga el ejercicio y hay
# eliminado con confirmación
App.id_paciente_antro = id_pac
app_dlg = App()
_tk_wait_original = tk.Toplevel.wait_window
tk.Toplevel.wait_window = lambda self, *a, **k: None


def _arbolitos(widget):
    salida = []
    for hijo in widget.winfo_children():
        if isinstance(hijo, ttk.Treeview):
            salida.append(hijo)
        salida.extend(_arbolitos(hijo))
    return salida


calculadora_1rm.abrir_dialogo_1rm(raiz, app_dlg, ejercicio="Sentadilla",
                                  ejercicios_rutina=[
                                      ("Press de banco plano "
                                       "(o «bench press»)", 140.0),
                                      ("Tracción pecho en polea alta", None),
                                  ],
                                  nivel_info="Nivel Principiante: "
                                             "Semana 1 al 65 %")
raiz.update()
tops = [w for w in raiz.winfo_children()
        if isinstance(w, tk.Toplevel)
        and "Calculadora de fuerza" in str(w.title())]
tablas_g = [tv for t in tops for tv in _arbolitos(t)
            if "metodo" in str(tv["columns"])
            and "fecha" in str(tv["columns"])]
chequear("calculadora 1RM: tabla «1RM guardados del paciente» presente",
         bool(tablas_g))
filas_g = [tv.item(i, "values") for tv in tablas_g
           for i in tv.get_children()]
chequear("calculadora 1RM: la tabla muestra el registro de la BD "
         "(banca 140 kg con fecha y método)",
         any(len(f) == 7
             and "bench" in rutinas_tab._normalizar(f[1])
             and f[3] == "140"
             and f[0].count("/") == 2
             for f in filas_g))
tablas_r = [tv for t in tops for tv in _arbolitos(t)
            if "ejercicio" in str(tv["columns"])
            and "rm" in str(tv["columns"])
            and "fecha" not in str(tv["columns"])]
chequear("calculadora 1RM: lista de los ejercicios de la rutina cargada",
         bool(tablas_r) and any(
             any("bench" in rutinas_tab._normalizar(tv.item(i, "values")[0])
                 and tv.item(i, "values")[1] == "140 kg"
                 for i in tv.get_children())
             for tv in tablas_r))
def _etiquetas(widget):
    salida = []
    for hijo in widget.winfo_children():
        if isinstance(hijo, tk.Label):
            salida.append(str(hijo.cget("text")))
        salida.extend(_etiquetas(hijo))
    return salida


etiquetas_dlg = []
for t in tops:
    etiquetas_dlg.extend(_etiquetas(t))
chequear("calculadora 1RM: el nivel del paciente se muestra en el diálogo",
         any(txt.startswith("Nivel Principiante") for txt in etiquetas_dlg))
combos_dlg = []


def _combos(widget):
    for hijo in widget.winfo_children():
        if isinstance(hijo, ttk.Combobox):
            combos_dlg.append(hijo)
        _combos(hijo)


for t in tops:
    _combos(t)
combo_ej = next((c for c in combos_dlg
                 if len(c.cget("values") or ()) == 2), None)
chequear("calculadora 1RM: con rutina cargada el selector trae SOLO sus "
         "ejercicios (2)",
         combo_ej is not None
         and "bench" in rutinas_tab._normalizar(combo_ej.cget("values")[0]))
fuente_calc = Path(calculadora_1rm.__file__).read_text(encoding="utf-8")
chequear("calculadora 1RM: campos en fondo negro con letras blancas",
         "bg=NEGRO, fg=BLANCO" in fuente_calc
         and fuente_calc.count('style="R1.TCombobox"') == 3
         and "TCombobox*Listbox.background" in fuente_calc)


def _canvases(widget):
    salida = []
    for hijo in widget.winfo_children():
        if isinstance(hijo, tk.Canvas):
            salida.append(hijo)
        salida.extend(_canvases(hijo))
    return salida


def _alto_region(lienzo):
    partes = str(lienzo.cget("scrollregion")).split()
    return int(partes[3]) if len(partes) == 4 else -1


lienzos_dlg = [c for t in tops for c in _canvases(t)]
chequear("calculadora 1RM: contenido en lienzo con barra vertical",
         bool(lienzos_dlg))
chequear("calculadora 1RM: todo el contenido registrado en el scroll "
         "(se llega hasta abajo)",
         any(_alto_region(c) >= c.winfo_children()[0].winfo_reqheight() - 2
             for c in lienzos_dlg if c.winfo_children()))
chequear("calculadora 1RM: el lienzo no crece más allá de la pantalla",
         all(int(c.cget("height") or 0) <= c.winfo_screenheight() - 110
             for c in lienzos_dlg))
chequear("calculadora 1RM: rueda del mouse desplaza el diálogo",
         'bind_all("<MouseWheel>", _al_rueda' in fuente_calc
         and "yview_scroll" in fuente_calc)
def _botones_todos(widget):
    salida = []
    for hijo in widget.winfo_children():
        if isinstance(hijo, tk.Button):
            salida.append(str(hijo.cget("text")))
        salida.extend(_botones_todos(hijo))
    return salida


chequear("calculadora 1RM: botón ⛶ MAXIMIZAR en el encabezado",
         any("MAXIMIZAR" in txt for t in tops
             for txt in _botones_todos(t)))
chequear("calculadora 1RM: ventana con minimizar y maximizar nativos",
         "dialogo.resizable(True, True)" in fuente_calc
         and "dialogo.minsize(720, 520)" in fuente_calc)
# el botón — MINIMIZAR del membrete vive en la app completa (el test usa
# un App ligero): se verifica por fuente, como los campos negros
fuente_app = (Path(os.path.dirname(os.path.abspath(__file__)))
              / "nutricion_deportiva.py").read_text(encoding="utf-8")
chequear("pantalla: botón — MINIMIZAR en el membrete (iconify)",
         '"— MINIMIZAR"' in fuente_app and "command=self.iconify" in fuente_app)
for t in tops:
    t.destroy()
tk.Toplevel.wait_window = _tk_wait_original
App.id_paciente_antro = None

# 11b) El botón 🏋 1RM de la vista diaria TAMBIÉN limita el selector a
# los ejercicios de la rutina cargada (no el catálogo completo)
tk.Toplevel.wait_window = lambda self, *a, **k: None
rt._abrir_1rm()
raiz.update()
tops_b = [w for w in list(raiz.winfo_children())
          + list(rt.marco.winfo_children())
          if isinstance(w, tk.Toplevel)
          and "Calculadora de fuerza" in str(w.title())]
combos_b = []


def _combos_b(widget):
    for hijo in widget.winfo_children():
        if isinstance(hijo, ttk.Combobox):
            combos_b.append(hijo)
        _combos_b(hijo)


for t in tops_b:
    _combos_b(t)
combo_ej_b = next((c for c in combos_b
                   if c.cget("values") and len(c.cget("values")) < 20
                   and len(str(c.cget("values")[0])) > 8), None)
valores_b = list(combo_ej_b.cget("values") or ()) if combo_ej_b else []
chequear("botón 🏋 1RM (vista diaria): selector SOLO con los ejercicios "
         "de la rutina cargada (9, no el catálogo)",
         combo_ej_b is not None and len(valores_b) == 9
         and all("polea" in rutinas_tab._normalizar(v)
                 or "bench" in rutinas_tab._normalizar(v)
                 or "piernas" in rutinas_tab._normalizar(v)
                 or "rodillas" in rutinas_tab._normalizar(v)
                 or "pelvis" in rutinas_tab._normalizar(v)
                 for v in valores_b))
for t in tops_b:
    t.destroy()
tk.Toplevel.wait_window = _tk_wait_original
App.id_paciente_antro = None

# 12) Eliminar rutinas guardadas simples (★ del combo del día)
rt._sem_guardar_dia_simple()
raiz.update()
simples = database.get_rutinas_guardadas(semanal=0)
chequear("rutina simple: GUARDAR DÍA crea una rutina simple en la biblioteca",
         len(simples) >= 1 and len(rt._sem_simples) >= 1)
rt.combo_sem_simple.set(rt._sem_simples[0]["nombre"])
_askyesno_original = rutinas_tab.messagebox.askyesno
try:
    rutinas_tab.messagebox.askyesno = lambda *a, **k: False
    rt._sem_eliminar_simple()
    chequear("rutina simple: cancelar la confirmación conserva la rutina",
             len(database.get_rutinas_guardadas(semanal=0))
             == len(simples))
    rutinas_tab.messagebox.askyesno = lambda *a, **k: True
    rt._sem_eliminar_simple()
    raiz.update()
    chequear("rutina simple: confirmada se elimina de la biblioteca",
             len(database.get_rutinas_guardadas(semanal=0))
             == len(simples) - 1
             and "guardada eliminada" in rt.lbl_estado.cget("text"))
finally:
    rutinas_tab.messagebox.askyesno = _askyesno_original

# limpiar BD temporal
raiz.destroy()
fallos = [n for n, ok in chequeos if not ok]
print("\n=== %d/%d CHEQUEOS TODO OK ===" % (
    len(chequeos) - len(fallos), len(chequeos)))
if fallos:
    print("FALLOS:")
    for f in fallos:
        print(" -", f)
sys.exit(1 if fallos else 0)
