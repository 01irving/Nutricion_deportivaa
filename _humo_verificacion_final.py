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
