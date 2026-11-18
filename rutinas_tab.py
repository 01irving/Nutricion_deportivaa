import io
import json
import os
import sqlite3
import re
import unicodedata
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog

try:  # Tk nativo solo decodifica PNG/GIF; Pillow permite leer el JPEG guardado en la BD
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover - entorno sin Pillow
    Image = None
    ImageTk = None

import calentamiento_print
import database
import estiramientos_print
import rutina_print
from estiramientos_tab import DURACIONES, MOMENTOS
from rutas import base_dir

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

RUTA_IMAGENES = os.path.join(base_dir(), "assets", "rutinas")
CATALOGOS_JSON = {
    "hombros": "hombros_ejercicios.json",
    "brazos": "brazos_ejercicios.json",
    "piernas": "piernas_ejercicios.json",
    "espalda": "espalda_ejercicios.json",
    "gluteos": "gluteos_ejercicios.json",
    "pectorales": "pectorales_ejercicios.json",
    "abdominales": "abdominales_ejercicios.json",
}
GRUPOS_PREFERIDOS = ("hombros", "brazos", "pectorales", "espalda", "piernas", "gluteos", "abdominales")
GRUPOS_ETIQUETAS = {"gluteos": "Glúteos"}

TAMANO_IMG_RESPALDO = (560, 380)

# Porcentajes del 1RM ofrecidos para llenar el peso (discos de 2.5 kg)
PORCENTAJES_1RM = tuple(range(50, 101, 5))

# Días de la rutina semanal (mismo orden que la pestaña Menús)
DIAS_SEMANA = (
    "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo",
)

# Opción del desplegable de Sesión que marca el día como descanso.
OPCION_DESCANSO = "— Día de descanso —"

# ----------------------------------------------------------------------
# Plantillas de rutina semanal (patrón del combo "Menú:" de la pestaña
# Menús). Los ejercicios son (grupo, num, marca) del catálogo de
# rutinas_ejercicios; marca "superserie" agrupa pares que se realizan
# sin descanso entre sí. None en la semana = día de descanso.
# ----------------------------------------------------------------------
PLANTILLAS_SEMANA = (
    {
        # Pedersen et al. 2022, BMC Sports Science, Medicine and
        # Rehabilitation 14:87 — Tabla 1, grupo SPLIT: 4 sesiones
        # (2 superiores + 2 inferiores), 3 series de 8-12 RM con
        # ~1 min de descanso entre series.
        "nombre": "Split 4 días · Tren superior / inferior (Pedersen 2022)",
        "series": "3",
        "repeticiones": "8-12",
        "descanso_series": "60",
        "sesiones": {
            "Tren superior": (
                ("espalda", "03", ""),        # Lat pulldown
                ("pectorales", "02", ""),     # Bench press
                ("espalda", "06", ""),        # Cable seated row
                ("brazos", "13", "superserie"),   # Triceps press en cable
                ("brazos", "05", "superserie"),   # Biceps curl en cable
            ),
            "Tren inferior": (
                ("piernas", "06", ""),        # Leg press
                ("espalda", "14", ""),        # Stiff-legged deadlift
                ("piernas", "09", ""),        # Leg extension
                ("gluteos", "06", ""),        # Hip thrust
            ),
        },
        "semana": {
            "Lunes": "Tren superior",
            "Martes": "Tren inferior",
            "Miércoles": None,
            "Jueves": "Tren superior",
            "Viernes": "Tren inferior",
            "Sábado": None,
            "Domingo": None,
        },
    },
    {
        # Pedersen et al. 2022, BMC Sports Science, Medicine and
        # Rehabilitation 14:87 — Tabla 1, grupo FB (cuerpo completo):
        # los mismos ejercicios del brazo SPLIT en 2 sesiones semanales
        # (mínimo 48 h entre sesiones). 3 series con periodización
        # lineal: 12-RM sem. 1-4, 10-RM sem. 5-8 y 8-RM sem. 9-12;
        # ~1 min de descanso entre series.
        "nombre": "Cuerpo completo 2 días · Mujeres no entrenadas (Pedersen 2022)",
        "series": "3",
        "repeticiones": "12-10-8",
        "descanso_series": "60",
        "sesiones": {
            "Cuerpo completo": (
                ("piernas", "06", ""),        # Leg press
                ("espalda", "14", ""),        # Stiff-legged deadlift
                ("piernas", "09", ""),        # Leg extension
                ("gluteos", "06", ""),        # Hip thrust
                ("espalda", "03", ""),        # Lat pulldown
                ("pectorales", "02", ""),     # Bench press
                ("espalda", "06", ""),        # Cable seated row
                ("brazos", "13", "superserie"),   # Triceps press en cable
                ("brazos", "05", "superserie"),   # Biceps curl en cable
            ),
        },
        "semana": {
            "Lunes": "Cuerpo completo",
            "Martes": None,
            "Miércoles": None,
            "Jueves": "Cuerpo completo",
            "Viernes": None,
            "Sábado": None,
            "Domingo": None,
        },
    },
    {
        # Zaroni et al. 2019, J Strength Cond Res — grupo TOTAL: cuerpo
        # completo 5 días consecutivos (lunes a viernes), un ejercicio
        # por grupo muscular por sesión (15 series/sesión; 15 series
        # semanales por músculo). 3 series × 10-12 RM al fallo, 60 s
        # entre series y 120 s entre ejercicios. Fue el grupo con mayor
        # ganancia de espesor muscular (flexores del codo y vasto
        # lateral) frente a la rutina dividida 1 día/semana.
        "nombre": "Total-body 5 días · Alta frecuencia (Zaroni 2019)",
        "series": "3",
        "repeticiones": "10-12",
        "descanso_series": "60",
        "sesiones": {
            "Cuerpo completo A": (
                ("pectorales", "10", ""),     # Incline dumbbell press
                ("brazos", "07", ""),         # Biceps curl (barra)
                ("piernas", "04", ""),        # Parallel back-squat
                ("espalda", "03", ""),        # Lat pull-down
                ("brazos", "13", ""),         # Cable triceps
            ),
            "Cuerpo completo B": (
                ("pectorales", "01", ""),     # Incline bench press
                ("brazos", "03", ""),         # Dumbbell incline curl
                ("piernas", "06", ""),        # Leg press
                ("espalda", "03", ""),        # Machine lat pull-down
                ("brazos", "17", ""),         # Nosebreaker (skullcrusher)
            ),
            "Cuerpo completo C": (
                ("pectorales", "02", ""),     # Bench press
                ("brazos", "08", ""),         # Dumbbell preacher curl
                ("piernas", "05", ""),        # Barbell split squat
                ("espalda", "05", ""),        # Neutral-grip lat pull-down
                ("brazos", "15", ""),         # Cable overhead triceps ext.
            ),
            "Cuerpo completo D": (
                ("pectorales", "05", ""),     # Incline bench press machine
                ("brazos", "09", ""),         # Barbell preacher curl
                ("piernas", "07", ""),        # Hack squat
                ("espalda", "06", ""),        # Machine close-grip seated row
                ("brazos", "14", ""),         # Cable triceps press-down
            ),
            "Cuerpo completo E": (
                ("pectorales", "05", ""),     # Bench press machine
                ("brazos", "04", ""),         # Dumbbell hammer curl
                ("espalda", "16", ""),        # Deadlift
                ("espalda", "07", ""),        # Machine wide-grip seated row
                ("brazos", "20", ""),         # Cable triceps kickback
            ),
        },
        "semana": {
            "Lunes": "Cuerpo completo A",
            "Martes": "Cuerpo completo B",
            "Miércoles": "Cuerpo completo C",
            "Jueves": "Cuerpo completo D",
            "Viernes": "Cuerpo completo E",
            "Sábado": None,
            "Domingo": None,
        },
    },
    {
        # Hamarsland et al. 2022, Frontiers in Physiology 12:789403 —
        # grupo HF (4 sesiones): cuerpo completo pesado con volumen
        # semanal igualado al grupo de 2 sesiones (32 series). Cada
        # sesión son 8 series repartidas en 5 ejercicios; cada ejercicio
        # lleva 2 series en su sesión base y 1 en la otra (el orden se
        # rota semanalmente). Bloques de 3 semanas: 12-RM (sem. 1-3),
        # 10-RM (sem. 4-6) y 8-RM (sem. 7-9), 70% 1RM la primera sesión
        # y 4 min de descanso entre series.
        "nombre": "Cuerpo completo pesado 4 días · 2 vs 4 sesiones (Hamarsland 2022)",
        "series": "1-2",
        "repeticiones": "12-10-8",
        "descanso_series": "240",
        "sesiones": {
            "Cuerpo completo A": (
                ("piernas", "04", ""),        # Squat (2 series)
                ("piernas", "07", ""),        # Hack squat (1 serie)
                ("pectorales", "02", ""),     # Bench press (2 series)
                ("pectorales", "05", ""),     # Chest press máquina (1 serie)
                ("espalda", "03", ""),        # Lat pulldown (2 series)
            ),
            "Cuerpo completo B": (
                ("piernas", "07", ""),        # Hack squat (2 series)
                ("piernas", "04", ""),        # Squat (1 serie)
                ("pectorales", "05", ""),     # Chest press máquina (2 series)
                ("pectorales", "02", ""),     # Bench press (1 serie)
                ("espalda", "06", ""),        # Seated row (2 series)
            ),
        },
        "semana": {
            "Lunes": "Cuerpo completo A",
            "Martes": "Cuerpo completo B",
            "Miércoles": None,
            "Jueves": "Cuerpo completo A",
            "Viernes": "Cuerpo completo B",
            "Sábado": None,
            "Domingo": None,
        },
    },
    {
        # Pedersen et al. 2024, European Journal of Sport Science —
        # grupo HIGH: piernas 4 días/semana, UN ejercicio por sesión
        # (sentadilla, peso muerto, sentadilla dividida y sentadilla
        # búlgara), sin más de 2 días consecutivos. Progresión de 12-RM
        # con 4 series y 2 min de descanso (sem. 1-4) a 6-RM con 5
        # series y 3 min de descanso (sem. 5-8). Ganó más fuerza máxima
        # (1-RM sentadilla) que el mismo volumen en una sola sesión.
        "nombre": "Piernas 4 días · Alta frecuencia (Pedersen 2024)",
        "series": "4-5",
        "repeticiones": "12RM a 6RM",
        "descanso_series": "120-180",
        "sesiones": {
            "Sentadilla trasera": (
                ("piernas", "04", ""),        # Back squat
            ),
            "Peso muerto": (
                ("espalda", "16", ""),        # Deadlift
            ),
            "Sentadilla dividida": (
                ("piernas", "05", ""),        # Split squat
            ),
            "Sentadilla búlgara": (
                ("piernas", "01", ""),        # Bulgarian squat (zancada)
            ),
        },
        "semana": {
            "Lunes": "Sentadilla trasera",
            "Martes": "Peso muerto",
            "Miércoles": None,
            "Jueves": "Sentadilla dividida",
            "Viernes": "Sentadilla búlgara",
            "Sábado": None,
            "Domingo": None,
        },
    },
    {
        # Prieto-González et al. 2020, Arch Med Deporte 37(2):78-83 —
        # grupo FBW (principiantes): cuerpo completo 2 días (lunes y
        # miércoles) con la misma carga semanal que la rutina dividida
        # (tren superior lunes / tren inferior miércoles). 3 series por
        # ejercicio; intensidad creciente cada 2 semanas: 62% (12 reps)
        # → 72% (8 reps) → 78% (6-8 reps); descanso de 1 a 2 min. Ambas
        # estructuras mejoraron fuerza y composición corporal sin
        # diferencias entre ellas.
        "nombre": "Cuerpo completo 2 días · Principiantes (Prieto-González 2020)",
        "series": "3",
        "repeticiones": "12-6",
        "descanso_series": "60-120",
        "sesiones": {
            "Cuerpo completo A": (
                ("pectorales", "02", ""),     # Bench press
                ("hombros", "01", ""),        # Behind the neck jerk
                ("espalda", "06", ""),        # Seated cable row
                ("pectorales", "09", ""),     # Dumbbell fly
                ("hombros", "05", ""),        # Reverse fly
                ("hombros", "06", ""),        # Dumbbell side lateral raise
                ("brazos", "13", ""),         # Triceps extension con polea
                ("brazos", "20", ""),         # Triceps kickback
                ("brazos", "01", ""),         # Dumbbell curl
                ("brazos", "08", ""),         # Scott bench biceps curl
            ),
            "Cuerpo completo B": (
                ("piernas", "06", ""),        # Leg press
                ("piernas", "09", ""),        # Quadriceps extension máquina
                ("piernas", "12", ""),        # Seated leg curl
                ("piernas", "10", ""),        # Lying leg curl
                ("abdominales", "08", ""),    # Ab crunch en máquina
                ("gluteos", "06", ""),        # Pelvic lift
                ("espalda", "19", ""),        # Back extension en máquina
                ("espalda", "18", ""),        # Back extension banco romano
                ("piernas", "20", ""),        # Seated calf raise máquina
                ("piernas", "17", ""),        # Standing calf raise máquina
            ),
        },
        "semana": {
            "Lunes": "Cuerpo completo A",
            "Martes": None,
            "Miércoles": "Cuerpo completo B",
            "Jueves": None,
            "Viernes": None,
            "Sábado": None,
            "Domingo": None,
        },
    },
    {
        # Carneiro et al. 2024, European Journal of Sport Science
        # 24(6):846-854 — grupo full-body (5 días, lunes a viernes):
        # 15 series por sesión (75 semanales, volumen igualado con el
        # grupo dividido); 8-12 RM al 70-80% del 1RM y 90 s de descanso.
        # Dos series para press de banca, remo, femoral, gemelos y
        # lumbar; una serie para press de piernas, sentadilla, curl con
        # barra, tríceps y elevaciones laterales. Perdió más grasa total
        # y regional (DXA) que la rutina dividida.
        "nombre": "Cuerpo completo 5 días · Pérdida de grasa (Carneiro 2024)",
        "series": "1-2",
        "repeticiones": "8-12",
        "descanso_series": "90",
        "sesiones": {
            "Cuerpo completo": (
                ("pectorales", "02", ""),     # Bench press (2 series)
                ("espalda", "06", ""),        # Seated row (2 series)
                ("piernas", "10", ""),        # Hamstring curl (2 series)
                ("piernas", "17", ""),        # Calf standing (2 series)
                ("espalda", "18", ""),        # Lumbar flexores/extensores
                ("piernas", "06", ""),        # Leg press (1 serie)
                ("piernas", "04", ""),        # Back squat (1 serie)
                ("brazos", "07", ""),         # Barbell curl (1 serie)
                ("brazos", "13", ""),         # Elbow extensors (1 serie)
                ("hombros", "06", ""),        # Lateral raises (1 serie)
            ),
        },
        "semana": {
            "Lunes": "Cuerpo completo",
            "Martes": "Cuerpo completo",
            "Miércoles": "Cuerpo completo",
            "Jueves": "Cuerpo completo",
            "Viernes": "Cuerpo completo",
            "Sábado": None,
            "Domingo": None,
        },
    },
)


def _discos_2_5(kg):
    """Redondea al disco cargable más cercano (múltiplos de 2.5 kg)."""
    return round(kg / 2.5) * 2.5


def _normalizar(texto):
    """Minúsculas y sin acentos, para emparejar nombres de ejercicios."""
    texto = (texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")

# ----------------------------------------------------------------------
# Pestaña Progresión — Position Stand del ACSM: "Progression Models in
# Resistance Training for Healthy Adults" (Med Sci Sports Exerc,
# 2009;41(3):687-708). Tres ramas: principiantes, intermedios, avanzados.
# ----------------------------------------------------------------------
CONTENIDO_INTRO_PROGRESION = """TITULO: MODELO DE PROGRESIÓN (ACSM 2009)

Elige tu nivel en el árbol de la izquierda.

◆ Principiantes — sin experiencia o desentrenados por años
◆ Intermedios — alrededor de 6 meses de entrenamiento constante
◆ Avanzados — años de entrenamiento con cargas

Regla que atraviesa todos los niveles: cuando el atleta complete
1-2 repeticiones más que las objetivo con su carga actual, se
aumenta el peso entre 2% y 10%.
"""

CONTENIDO_PROGRESION = {
    "principiantes": """TITULO: 🟢 PRINCIPIANTES

Sin experiencia en pesas o desentrenados durante varios años.

◆ Frecuencia
2-3 días por semana, entrenando cada grupo muscular en cada
sesión (rutina de cuerpo completo).

◆ Carga y repeticiones
Cargas que permitan 8-12 repeticiones máximas (RM) por
ejercicio.

◆ Series
1-3 series por ejercicio; empezar conservador y sumar series
según se adapte.

◆ Velocidad de ejecución
Moderada: 1-2 segundos la fase concéntrica (subida) y 1-2
segundos la excéntrica (bajada).

◆ Descanso
1-2 minutos entre series; 2-3 minutos en multiarticulares
pesadas.

◆ Selección de ejercicios
Multiarticulares antes que unilaterales; grandes grupos
musculares antes que los pequeños.

◆ Progresión
Al completar 1-2 repeticiones por encima del rango objetivo,
aumentar la carga 2-10%.
""",
    "intermedios": """TITULO: 🟡 INTERMEDIOS

Alrededor de 6 meses de entrenamiento de fuerza constante.

◆ Frecuencia
3-4 días por semana.

◆ Carga y repeticiones
Rango más amplio: 1-12 RM usado EN FORMA PERIODIZADA, con
énfasis en cargas pesadas (1-6 RM).

◆ Series
Múltiples series por ejercicio; variar el volumen por ciclos.

◆ Velocidad de ejecución
Moderada: 1-2 segundos concéntrico, 1-2 segundos excéntrico.

◆ Descanso
3-5 minutos entre series con cargas pesadas multiarticulares;
1-2 minutos si el objetivo de la serie es hipertrofia.

◆ Periodización
Entrenar en forma periodizada (lineal u ondulante): alternar
bloques de volumen e intensidad para seguir progresando.

◆ Progresión
2-10% de aumento de carga al superar el rango objetivo;
manipular también series y frecuencia entre microciclos.
""",
    "avanzados": """TITULO: 🔴 AVANZADOS

Años de entrenamiento de fuerza sistemático.

◆ Frecuencia
4-5 días por semana (rutinas divididas por grupos musculares).

◆ Carga y repeticiones
1-12 RM periodizado, progresando con énfasis hacia 1-6 RM.

◆ Series y volumen
Alto volumen planificado: múltiples series y ejercicios por
grupo, manipulados por mesociclo.

◆ Velocidad de ejecución
Moderada para fuerza; para potencia, cargas ligeras movidas a
máxima velocidad: 0-60% de 1RM en tren inferior y 30-60% de
1RM en tren superior, 3-5 series por ejercicio.

◆ Descanso
3-5 minutos entre series pesadas y de potencia.

◆ Periodización
Plan anual completo: macrociclo, mesociclos y microciclos,
alternando fuerza, potencia y picos.

◆ Progresión
Además del 2-10% de carga, progresar manipulando volumen,
intensidad, frecuencia y descansos; incluir acciones
concéntricas, excéntricas e isométricas, trabajo bilateral y
unilateral.
""",
}

REGLAS_GENERALES_PROGRESION = (
    "Reglas generales (todos los niveles): sube la carga 2-10% al "
    "completar 1-2 reps más que el objetivo · grandes músculos antes "
    "que pequeños y multiarticulares antes que unilaterales · "
    "hipertrofia: 6-12 RM con 1-2 min de descanso y varias series · "
    "resistencia muscular: 40-60% de 1RM, >15 reps, descanso <90 s · "
    "potencia: cargas ligeras a máxima velocidad con 3-5 min de "
    "descanso · intermedios y avanzados entrenan en forma periodizada."
)


class RutinasTab:
    def __init__(self, app):
        self.app = app
        self.paciente_id = None
        self.grupo = "hombros"
        self.grupos = []
        self.ejercicios = []
        self.est_catalogo = []
        self.est_actual = None
        self.est_seleccion = []
        self._est_foto = None
        self._cargar_ejercicios()
        self.imagen_actual = None
        self._img_origen = None
        self._img_fuente = ""
        self._tam_panel = TAMANO_IMG_RESPALDO
        self._img_after = None
        self.ejercicio_seleccionado = None
        # último 1RM calculado en el diálogo (cualquier método) y lista
        # de referencias 1RM para llenar el peso por porcentaje
        self.rm_sesion = None
        self._rm_lista = []
        # día de la semana que se está editando de la rutina semanal
        self.dia_actual = DIAS_SEMANA[0]
        self.dia_buttons = {}

    def _abrir_1rm(self):
        """Calculadora de 1RM por ejercicio (ramas de árbol)."""
        import calculadora_1rm

        resultado = calculadora_1rm.abrir_dialogo_1rm(self.marco, self.app)
        if resultado:
            self.rm_sesion = resultado
        self._recargar_referencias_1rm()
        if resultado:
            self._mensaje(
                f"1RM activo: {resultado['ejercicio']} {resultado['resultado']} kg"
            )

    # ------------------------------------------------------------------
    # Rutinas semanales en TABLAS (sub-pestaña «Semana»): la rutina
    # semanal se elige en una tabla, se carga por días empezando en
    # Lunes y cada ejercicio se edita en su propia fila (ejercicio,
    # series, repeticiones, descansos y peso). Sin cuadros de diálogo:
    # nueva, cargar (estudio/guardada/paciente), modificar, guardar,
    # aplicar y eliminar ocurren aquí mismo.
    # ------------------------------------------------------------------

    def _semanales_guardadas(self):
        """Rutinas semanales guardadas por el usuario (lista vacía si la
        tabla aún no existe por una BD muy vieja)."""
        try:
            return database.get_rutinas_guardadas(semanal=1)
        except Exception:
            return []

    def _plantilla_de_guardada(self, guardada):
        """Convierte una rutina semanal guardada en la estructura que
        consumen el cuadro y la aplicación de plantillas: semana (dia ->
        sesión o None) y sesiones (nombre -> fichas con su propia
        prescripción). La sesión es la nota guardada con cada ejercicio;
        si un día no tiene nota, el propio nombre del día hace de sesión."""
        rutina = database.get_rutina_guardada(guardada["id_rutina_guardada"])
        semana = {dia: None for dia in DIAS_SEMANA}
        sesiones = {}
        for e in rutina["ejercicios"]:
            if e.get("descanso"):
                continue
            sesion = (e.get("notas") or "").strip() or (e.get("dia") or "")
            semana[e["dia"]] = sesion
            sesiones.setdefault(sesion, []).append(dict(e))
        return {
            "nombre": rutina["nombre"],
            "guardada": True,
            "semana": semana,
            "sesiones": {s: tuple(fs) for s, fs in sesiones.items()},
            "series": "",
            "repeticiones": "",
            "descanso_series": "",
        }

    def _fichas_plantilla(self, plantilla):
        """Fichas del catálogo por sesión de la plantilla (copia editable
        para la tabla) y lista de entradas sin ficha en el catálogo."""
        sesiones = {}
        faltan = []
        for sesion, ejercicios in plantilla["sesiones"].items():
            filas = []
            for grupo, num, marca in ejercicios:
                try:
                    ficha = database.get_rutina_ejercicio(grupo, num)
                except Exception:
                    ficha = None
                if ficha is None:
                    faltan.append(f"{grupo} #{num}")
                    ficha = {"nombre": f"{grupo} #{num}", "equipo": ""}
                ficha = dict(ficha)
                ficha["marca"] = marca
                filas.append(ficha)
            sesiones[sesion] = filas
        return sesiones, faltan

    def _sem_ficha_con_prescripcion(self, ficha, plantilla=None):
        """Copia editable de una ficha con su prescripción: la que ya
        trae, o los valores de la plantilla del estudio, o un 3×12 por
        defecto listo para editar en la tabla."""
        ficha = dict(ficha)
        ficha.setdefault("grupo", None)
        ficha.setdefault("num", None)
        ficha.setdefault("series", (plantilla or {}).get("series") or "3")
        ficha.setdefault(
            "repeticiones", (plantilla or {}).get("repeticiones") or "12"
        )
        ficha.setdefault("descanso_rep", "")
        ficha.setdefault(
            "descanso_series",
            (plantilla or {}).get("descanso_series") or "60",
        )
        ficha.setdefault("peso", "")
        return ficha

    def _sem_semana_vacia(self):
        return {
            dia: {"sesion": None, "ejercicios": []} for dia in DIAS_SEMANA
        }

    # ------------------------------------------------------------------
    # Construcción de la sub-pestaña «Semana»
    # ------------------------------------------------------------------
    def _crear_panel_semana(self):
        """Tablas de la rutina semanal, integradas en la sub-pestaña
        Rutina: el botón «ABRIR RUTINA SEMANAL» las muestra sobre la
        vista diaria y las vuelve a ocultar (sin pestaña aparte ni
        cuadros de diálogo).""",
        marco = ttk.Frame(self.interior_rut, style="Gym.TFrame")
        self.marco_sem = marco

        # estado del editor semanal (se llena al cargar una rutina)
        self._sem_datos = self._sem_semana_vacia()
        self._sem_dia = DIAS_SEMANA[0]
        self._sem_origen = "nueva"
        self._sem_guardada_id = None
        self._sem_catalogo = []
        self._sem_opciones = {}
        self._sem_simples = []
        self._sem_editor = None

        cuerpo = ttk.Frame(marco, style="Gym.TFrame")
        cuerpo.pack(fill="both", expand=True, padx=8, pady=(4, 2))

        # ---------- izquierda: tabla para ELEGIR la rutina semanal ------
        izquierdo = ttk.LabelFrame(
            cuerpo,
            text="Rutinas semanales disponibles (doble clic = cargar)",
            padding=4,
        )
        izquierdo.pack(side="left", fill="y", padx=(0, 6))
        cols_sel = ("nombre", "origen", "dias", "ejercicios")
        self.tree_sem_selector = ttk.Treeview(
            izquierdo, columns=cols_sel, show="headings", height=14,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("nombre", "Rutina", 185, "w"),
            ("origen", "Origen", 66, "center"),
            ("dias", "Días", 42, "center"),
            ("ejercicios", "Ejerc.", 50, "center"),
        ):
            self.tree_sem_selector.heading(col, text=texto, anchor=alineacion)
            self.tree_sem_selector.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion
            )
        self.tree_sem_selector.pack(side="top", fill="both", expand=True)
        barra_sel = ttk.Scrollbar(
            izquierdo, orient="vertical",
            command=self.tree_sem_selector.yview,
        )
        self.tree_sem_selector.configure(yscrollcommand=barra_sel.set)
        self.tree_sem_selector.bind(
            "<Double-1>", lambda _e: self._sem_cargar_seleccionada()
        )
        botones_sel = ttk.Frame(izquierdo, style="Gym.TFrame")
        botones_sel.pack(side="bottom", fill="x", pady=(4, 0))
        tk.Button(
            botones_sel, text="⟳ REFRESCAR",
            command=self._sem_refrescar_selector,
            font=("Segoe UI", 8, "bold"), fg=NEON, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side="left")
        tk.Button(
            botones_sel, text="🗑 ELIMINAR GUARDADA",
            command=self._sem_eliminar_guardada,
            font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side="left", padx=(6, 0))

        # ---------- derecha: nombre + acciones ---------------------------
        derecho = ttk.Frame(cuerpo, style="Gym.TFrame")
        derecho.pack(side="left", fill="both", expand=True)

        fila_acciones = ttk.Frame(derecho, style="Gym.TFrame")
        fila_acciones.pack(fill="x", pady=(0, 4))
        tk.Label(
            fila_acciones, text="Nombre:",
            font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left")
        self.entrada_sem_nombre = tk.Entry(
            fila_acciones, width=32, font=("Segoe UI", 9),
            fg=BLANCO, bg=GRIS, relief="flat", insertbackground=NEON,
        )
        self.entrada_sem_nombre.pack(side="left", padx=(4, 10), ipady=2)
        for texto, comando, destacado in (
            ("NUEVA", self._sem_nueva, False),
            ("⤓ SEMANA DEL PACIENTE", self._sem_cargar_paciente, False),
            ("💾 GUARDAR", self._sem_guardar, False),
            ("✔ APLICAR AL PACIENTE", self._sem_aplicar, True),
            ("🖨 IMPRIMIR SEMANA", self._abrir_menu_sem_imprimir, False),
        ):
            boton = tk.Button(
                fila_acciones, text=texto, command=comando,
                font=("Segoe UI", 8, "bold"),
                fg=NEGRO if destacado else NEON,
                bg=NEON if destacado else GRIS,
                activebackground=NARANJA, activeforeground=BLANCO,
                relief="flat", padx=10, pady=3, cursor="hand2",
            )
            boton.pack(side="left", padx=(0, 5))
            if texto == "🖨 IMPRIMIR SEMANA":
                self.btn_sem_imprimir = boton

        # despliegue de impresión de la semana: solo la tabla, solo las
        # descripciones o ambas, cada una con su versión de Guardar PDF
        # (patrón del menú IMPRIMIR RUTINA)
        self.menu_sem_imprimir = tk.Menu(
            self.btn_sem_imprimir, tearoff=0, font=("Segoe UI", 9)
        )
        self.menu_sem_imprimir.add_command(
            label="Tabla semanal", command=lambda: self._sem_imprimir("tabla")
        )
        self.menu_sem_imprimir.add_command(
            label="Descripciones de ejercicios",
            command=lambda: self._sem_imprimir("descripcion"),
        )
        self.menu_sem_imprimir.add_command(
            label="Tabla + descripciones (todo)",
            command=lambda: self._sem_imprimir("todo"),
        )
        self.menu_sem_imprimir.add_separator()
        menu_guardar_sem = tk.Menu(
            self.menu_sem_imprimir, tearoff=0, font=("Segoe UI", 9)
        )
        menu_guardar_sem.add_command(
            label="Tabla semanal",
            command=lambda: self._sem_imprimir("tabla", guardar=True),
        )
        menu_guardar_sem.add_command(
            label="Descripciones de ejercicios",
            command=lambda: self._sem_imprimir("descripcion", guardar=True),
        )
        menu_guardar_sem.add_command(
            label="Tabla + descripciones (todo)",
            command=lambda: self._sem_imprimir("todo", guardar=True),
        )
        self.menu_sem_imprimir.add_cascade(
            label="💾 Guardar PDF…", menu=menu_guardar_sem
        )

        # ---------- tabla de la semana (7 días, Lunes primero) -----------
        marco_semana = ttk.LabelFrame(
            derecho,
            text="Semana — doble clic en Sesión: despliega opciones o "
                 "escribe el nombre; doble clic en Ejercicios: cuántos "
                 "campos generar",
            padding=4,
        )
        marco_semana.pack(fill="x")
        cols_sem = ("dia", "sesion", "total")
        self.tree_sem_semana = ttk.Treeview(
            marco_semana, columns=cols_sem, show="headings", height=7,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("dia", "Día", 90, "w"),
            ("sesion", "Sesión", 250, "w"),
            ("total", "Ejercicios", 90, "center"),
        ):
            self.tree_sem_semana.heading(col, text=texto, anchor=alineacion)
            self.tree_sem_semana.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion
            )
        self.tree_sem_semana.pack(side="left", fill="x", expand=True)
        self.tree_sem_semana.bind(
            "<Double-1>", self._sem_editar_semana_celda
)
        self.tree_sem_semana.bind(
            "<<TreeviewSelect>>", self._sem_elegir_dia
        )

        # ---------- funciones de la sesión, entre Semana y Ejercicios ----
        # (rutina simple guardada, catálogo, quitar y reordenar: todo lo
        # que estaba al pie de la tabla de ejercicios, pedido del autor)
        fila_funciones = ttk.Frame(derecho, style="Gym.TFrame")
        fila_funciones.pack(fill="x", pady=(6, 0))

        fila_guardada = ttk.Frame(fila_funciones, style="Gym.TFrame")
        fila_guardada.pack(fill="x")
        tk.Label(
            fila_guardada, text="Rutina guardada simple:",
            font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left")
        self.combo_sem_simple = ttk.Combobox(
            fila_guardada, values=[], state="readonly", width=36,
            style="Gym.TCombobox",
        )
        self.combo_sem_simple.pack(side="left", padx=(4, 6))
        tk.Button(
            fila_guardada, text="⤒ AGREGAR AL DÍA",
            command=self._sem_agregar_guardada_al_dia,
            font=("Segoe UI", 8, "bold"), fg=NEON, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side="left")
        tk.Button(
            fila_guardada, text="💾 GUARDAR DÍA COMO NUEVA",
            command=self._sem_guardar_dia_simple,
            font=("Segoe UI", 8, "bold"), fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        fila_ej = ttk.Frame(fila_funciones, style="Gym.TFrame")
        fila_ej.pack(fill="x", pady=(4, 0))
        tk.Label(
            fila_ej, text="Añadir del catálogo:",
            font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left")
        self.combo_sem_anadir = ttk.Combobox(
            fila_ej, values=[], state="readonly", width=32,
            style="Gym.TCombobox",
        )
        self.combo_sem_anadir.pack(side="left", padx=(4, 6))
        tk.Button(
            fila_ej, text="＋ AÑADIR AL DÍA",
            command=self._sem_agregar_ejercicio,
            font=("Segoe UI", 8, "bold"), fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side="left")
        tk.Button(
            fila_ej, text="✕ QUITAR",
            command=self._sem_quitar_ejercicio,
            font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            fila_ej, text="↑", command=lambda: self._sem_mover(-1),
            font=("Segoe UI", 8, "bold"), fg=NEON, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=6, pady=2, cursor="hand2",
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            fila_ej, text="↓", command=lambda: self._sem_mover(1),
            font=("Segoe UI", 8, "bold"), fg=NEON, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=6, pady=2, cursor="hand2",
        ).pack(side="left", padx=(2, 0))
        self.lbl_sem_dia = tk.Label(
            fila_ej,
            text="",
            font=("Segoe UI", 8, "italic"), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        )
        self.lbl_sem_dia.pack(side="left", padx=(10, 0))

        # ---------- tabla editable de ejercicios del día ------------------
        marco_ej = ttk.LabelFrame(
            derecho,
            text="Ejercicios del día — doble clic en # añade; en Ejercicio "
                 "elige grupo (p. ej. Hombros) y luego el ejercicio; "
                 "series, repeticiones, descansos y peso se editan directo",
            padding=4,
        )
        marco_ej.pack(fill="both", expand=True, pady=(6, 0))
        cols_ej = (
            "num", "ejercicio", "series", "repeticiones", "descanso_rep",
            "descanso_series", "peso", "equipo",
        )
        self.tree_sem_ej = ttk.Treeview(
            marco_ej, columns=cols_ej, show="headings", height=9,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("num", "#", 30, "center"),
            ("ejercicio", "Ejercicio", 250, "w"),
            ("series", "Series", 52, "center"),
            ("repeticiones", "Reps", 62, "center"),
            ("descanso_rep", "Desc. reps", 70, "center"),
            ("descanso_series", "Desc. series", 76, "center"),
            ("peso", "Peso", 60, "center"),
            ("equipo", "Equipo", 105, "w"),
        ):
            self.tree_sem_ej.heading(col, text=texto, anchor=alineacion)
            self.tree_sem_ej.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion
            )
        self.tree_sem_ej.pack(side="top", fill="both", expand=True)
        barra_ej = ttk.Scrollbar(
            marco_ej, orient="vertical", command=self.tree_sem_ej.yview
        )
        self.tree_sem_ej.configure(yscrollcommand=barra_ej.set)
        self.tree_sem_ej.bind("<Double-1>", self._sem_editar_celda_evento)

        # ---------- historial de rutinas guardadas del paciente ----------
        marco_hist = ttk.LabelFrame(
            derecho,
            text="Rutinas guardadas del paciente (doble clic = cargar para "
                 "editar o volver a aplicar)",
            padding=4,
        )
        marco_hist.pack(fill="x", pady=(6, 0))
        cols_hist = ("semana", "fecha", "ejercicios", "dias")
        self.tree_sem_historial = ttk.Treeview(
            marco_hist, columns=cols_hist, show="headings", height=4,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("semana", "Rutina semanal", 300, "w"),
            ("fecha", "Fecha guardada", 130, "center"),
            ("ejercicios", "Ejerc.", 60, "center"),
            ("dias", "Días", 50, "center"),
        ):
            self.tree_sem_historial.heading(
                col, text=texto, anchor=alineacion
            )
            self.tree_sem_historial.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion
            )
        self.tree_sem_historial.pack(side="left", fill="x", expand=True)
        barra_hist = ttk.Scrollbar(
            marco_hist, orient="vertical",
            command=self.tree_sem_historial.yview,
        )
        self.tree_sem_historial.configure(yscrollcommand=barra_hist.set)
        self.tree_sem_historial.bind(
            "<Double-1>", lambda _e: self._sem_cargar_historial()
        )

        # catálogo para la lista Añadir y los desplegables de celda
        self._sem_cargar_catalogo()
        self.combo_sem_anadir.configure(values=list(self._sem_opciones))
        self._sem_refrescar_selector()
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()

        # las tablas de la rutina semanal abren automáticamente, sin
        # necesidad del botón (este queda solo para cerrar/abrir)
        self.contenedor_rut.pack_forget()
        self.marco_sem.pack(fill="both", expand=True)
        self._sem_visible = True
        self.btn_ver_semana.configure(
            text="✕ CERRAR SEMANA", fg=BLANCO, bg=NARANJA,
        )

    def _alternar_panel_semana(self):
        """Muestra u oculta las tablas de la rutina semanal dentro de
        la sub-pestaña Rutina: al abrirse reemplazan la vista diaria
        para dar espacio a las tablas y al cerrarse se restaura."""
        if getattr(self, "_sem_visible", False):
            self._sem_cerrar_panel()
            self._mensaje("Vista diaria restaurada.")
            return
        self.contenedor_rut.pack_forget()
        self.marco_sem.pack(fill="both", expand=True)
        self._sem_visible = True
        self.btn_ver_semana.configure(
            text="✕ CERRAR SEMANA", fg=BLANCO, bg=NARANJA,
        )
        self._sem_refrescar_selector()
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self._sem_refrescar_historial()
        self._mensaje(
            "Rutina semanal en tablas: elige una rutina (doble clic), "
            "edita en celdas y guarda o aplica."
        )

    def _sem_cerrar_panel(self):
        """Oculta las tablas semanales y restaura la vista diaria."""
        self._sem_cerrar_editor()
        if getattr(self, "_sem_visible", False):
            self.marco_sem.pack_forget()
            self.contenedor_rut.pack(
                fill="both", expand=True, padx=10, pady=(2, 6)
            )
            self._sem_visible = False
        if hasattr(self, "btn_ver_semana"):
            self.btn_ver_semana.configure(
                text="📅 ABRIR RUTINA SEMANAL", fg=NEON, bg=GRIS,
            )

    # ------------------------------------------------------------------
    # Tabla selector y carga de la rutina semanal
    # ------------------------------------------------------------------
    def _sem_refrescar_selector(self):
        """Tabla selector: plantillas fijas del estudio + rutinas
        semanales guardadas. También llena el combo de rutinas simples."""
        if not hasattr(self, "tree_sem_selector"):
            return
        self._sem_selector_map = {}
        for iid in self.tree_sem_selector.get_children():
            self.tree_sem_selector.delete(iid)
        for idx, p in enumerate(PLANTILLAS_SEMANA):
            dias = sum(1 for v in p["semana"].values() if v)
            ejercicios = sum(len(e) for e in p["sesiones"].values())
            iid = f"f{idx}"
            self.tree_sem_selector.insert(
                "", "end", iid=iid,
                values=(p["nombre"], "Estudio", dias, ejercicios),
            )
            self._sem_selector_map[iid] = ("fija", idx)
        for r in self._semanales_guardadas():
            iid = f"g{r['id_rutina_guardada']}"
            self.tree_sem_selector.insert(
                "", "end", iid=iid,
                values=(
                    r["nombre"], "Guardada",
                    r.get("dias") if r.get("dias") else "—",
                    r.get("ejercicios") if r.get("ejercicios") else "—",
                ),
            )
            self._sem_selector_map[iid] = ("guardada", r["id_rutina_guardada"])
        # rutinas guardadas simples para agregar al día seleccionado
        try:
            self._sem_simples = database.get_rutinas_guardadas(semanal=0)
        except Exception:
            self._sem_simples = []
        if hasattr(self, "combo_sem_simple"):
            self.combo_sem_simple.configure(
                values=[r["nombre"] for r in self._sem_simples]
            )
            if self._sem_simples:
                self.combo_sem_simple.current(0)
            else:
                self.combo_sem_simple.set("— sin rutinas guardadas —")

    def _sem_cargar_seleccionada(self):
        """Carga en las tablas la rutina semanal elegida en el selector:
        una fija del estudio o una guardada; los ejercicios quedan por día
        empezando en Lunes, listos para editar, guardar o aplicar."""
        sel = self.tree_sem_selector.selection()
        if not sel or sel[0] not in getattr(self, "_sem_selector_map", {}):
            self._mensaje("Elige una rutina semanal en la tabla de la izquierda.")
            return
        origen, clave = self._sem_selector_map[sel[0]]
        self._sem_datos = self._sem_semana_vacia()
        if origen == "fija":
            plantilla = PLANTILLAS_SEMANA[clave]
            sesiones, faltan = self._fichas_plantilla(plantilla)
            for dia in DIAS_SEMANA:
                sesion = plantilla["semana"].get(dia)
                if not sesion:
                    continue
                self._sem_datos[dia]["sesion"] = sesion
                self._sem_datos[dia]["ejercicios"] = [
                    self._sem_ficha_con_prescripcion(f, plantilla)
                    for f in sesiones.get(sesion, [])
                ]
            self._sem_nombre = plantilla["nombre"]
            self._sem_origen = "fija"
            self._sem_guardada_id = None
            if faltan:
                self._mensaje(
                    "No están en el catálogo: "
                    + ", ".join(dict.fromkeys(faltan))
                )
        else:
            try:
                guardada = database.get_rutina_guardada(clave)
            except Exception:
                guardada = None
            if not guardada:
                self._mensaje("No se pudo leer la rutina guardada.")
                return
            conv = self._plantilla_de_guardada(guardada)
            for dia in DIAS_SEMANA:
                sesion = conv["semana"].get(dia)
                if not sesion:
                    continue
                self._sem_datos[dia]["sesion"] = sesion
                self._sem_datos[dia]["ejercicios"] = [
                    self._sem_ficha_con_prescripcion(f)
                    for f in conv["sesiones"].get(sesion, [])
                ]
            self._sem_nombre = conv["nombre"]
            self._sem_origen = "guardada"
            self._sem_guardada_id = clave
        # el día activo arranca en Lunes (o el primer día entrenable)
        self._sem_dia = next(
            (d for d in DIAS_SEMANA if self._sem_datos[d]["sesion"]),
            DIAS_SEMANA[0],
        )
        self.entrada_sem_nombre.delete(0, tk.END)
        self.entrada_sem_nombre.insert(0, self._sem_nombre)
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self._mensaje(
            f"Rutina semanal cargada en la tabla: «{self._sem_nombre}» "
            f"(día {self._sem_dia})."
        )

    def _sem_nueva(self):
        """Vacía el editor para crear una rutina semanal nueva."""
        self._sem_datos = self._sem_semana_vacia()
        self._sem_nombre = "Nueva rutina semanal"
        self._sem_origen = "nueva"
        self._sem_guardada_id = None
        self._sem_dia = DIAS_SEMANA[0]
        self.entrada_sem_nombre.delete(0, tk.END)
        self.entrada_sem_nombre.insert(0, self._sem_nombre)
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self._mensaje("Nueva rutina semanal: añade ejercicios por día en la tabla.")

    def _sem_cargar_paciente(self):
        """Trae a las tablas la semana actual del paciente para
        modificarla (misma estructura que la edición semanal previa)."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            self._mensaje("Selecciona un paciente antes de cargar su semana.")
            return
        self._cargar_rutina()
        self._sem_datos = self._sem_semana_vacia()
        for e in [r for r in getattr(self, "rutina", []) if not r.get("descanso")]:
            dia = e.get("dia") or "Lunes"
            if dia not in self._sem_datos:
                continue
            sesion = (e.get("notas") or "").strip() or dia
            self._sem_datos[dia]["sesion"] = sesion
            self._sem_datos[dia]["ejercicios"].append(
                self._sem_ficha_con_prescripcion(dict(e))
            )
        nombre_semana = next(
            (r.get("nombre_semana") for r in getattr(self, "rutina", [])
             if r.get("nombre_semana")),
            "",
        )
        self._sem_nombre = nombre_semana or "Semana del paciente"
        self._sem_origen = "paciente"
        self._sem_guardada_id = None
        self._sem_dia = next(
            (d for d in DIAS_SEMANA if self._sem_datos[d]["sesion"]),
            DIAS_SEMANA[0],
        )
        self.entrada_sem_nombre.delete(0, tk.END)
        self.entrada_sem_nombre.insert(0, self._sem_nombre)
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self._mensaje(
            f"Semana del paciente cargada en la tabla: "
            f"{sum(len(d['ejercicios']) for d in self._sem_datos.values())} ejercicios."
        )

    # ------------------------------------------------------------------
    # Pintado y edición en celda de las tablas
    # ------------------------------------------------------------------
    def _sem_pintar_semana(self):
        tree = self.tree_sem_semana
        for iid in tree.get_children():
            tree.delete(iid)
        for dia in DIAS_SEMANA:
            info = self._sem_datos[dia]
            if info["sesion"]:
                tree.insert(
                    "", "end", iid=dia,
                    values=(dia, info["sesion"], len(info["ejercicios"])),
                )
            else:
                tree.insert(
                    "", "end", iid=dia,
                    values=(dia, "— descanso —", "—"),
                )
        if self._sem_dia in DIAS_SEMANA:
            tree.selection_set(self._sem_dia)
            tree.see(self._sem_dia)

    def _sem_elegir_dia(self, _event=None):
        sel = self.tree_sem_semana.selection()
        if sel and sel[0] in self._sem_datos:
            self._sem_dia = sel[0]
        self._sem_pintar_ejercicios()

    def _sem_pintar_ejercicios(self):
        tree = self.tree_sem_ej
        for iid in tree.get_children():
            tree.delete(iid)
        ejercicios = self._sem_datos[self._sem_dia]["ejercicios"]
        for i, ej in enumerate(ejercicios):
            tree.insert(
                "", "end", iid=str(i),
                values=(
                    i + 1,
                    ej.get("nombre")
                    or f"{ej.get('grupo') or '?'} #{ej.get('num') or '?'}",
                    ej.get("series") or "—",
                    ej.get("repeticiones") or "—",
                    ej.get("descanso_rep") or "—",
                    ej.get("descanso_series") or "—",
                    ej.get("peso") or "—",
                    ej.get("equipo") or "-",
                ),
            )
        if not ejercicios:
            # día sin ejercicios (sesión nueva o descanso): fila de
            # invitación cuyo doble clic despliega el catálogo
            tree.insert(
                "", "end", iid="nuevo",
                values=(
                    1,
                    "— doble clic aquí para añadir el primer ejercicio "
                    "del catálogo —",
                    "—", "—", "—", "—", "—", "-",
                ),
            )
        self.lbl_sem_dia.configure(
            text=f"Día: {self._sem_dia} · Sesión: "
                 f"{self._sem_datos[self._sem_dia]['sesion'] or 'descanso'}"
        )

    def _sem_cerrar_editor(self):
        """Cierra el editor en celda (Entry/Combobox superpuesto)."""
        if getattr(self, "_sem_editor", None) is not None:
            try:
                self._sem_editor.destroy()
            except Exception:
                pass
            self._sem_editor = None

    def _sem_opciones_sesion(self, dia):
        """Opciones del desplegable de Sesión para un día: descanso,
        las sesiones ya presentes en la semana, las rutinas guardadas
        simples (★) y las sesiones de las rutinas semanales guardadas
        y de las plantillas del estudio (◆). Devuelve (valores, mapa).
        """
        valores = [OPCION_DESCANSO]
        mapa = {OPCION_DESCANSO: ("descanso",)}
        # sesiones ya presentes en la semana (copian sus ejercicios)
        vistas = []
        for d in DIAS_SEMANA:
            ses = self._sem_datos[d]["sesion"]
            if ses and ses not in vistas:
                vistas.append(ses)
                if d != dia:
                    valores.append(ses)
                    mapa[ses] = ("semana", d)
        # rutinas guardadas simples de la biblioteca (★)
        try:
            simples = database.get_rutinas_guardadas(semanal=0)
        except Exception:
            simples = []
        for r in simples:
            etiqueta = f"★ {r['nombre']}"
            valores.append(etiqueta)
            mapa[etiqueta] = ("simple", r["id_rutina_guardada"])
        # sesiones de las plantillas del estudio (◆)
        for idx, p in enumerate(PLANTILLAS_SEMANA):
            for sesion in p["sesiones"]:
                etiqueta = f"◆ {sesion} — {p['nombre']}"
                valores.append(etiqueta)
                mapa[etiqueta] = ("fija", idx, sesion)
        # sesiones de las rutinas semanales guardadas (◆)
        for r in self._semanales_guardadas():
            try:
                rutina = database.get_rutina_guardada(r["id_rutina_guardada"])
            except Exception:
                continue
            sesiones = []
            for e in rutina.get("ejercicios", []):
                ses = (e.get("notas") or "").strip()
                if e.get("descanso") or not ses or ses in sesiones:
                    continue
                sesiones.append(ses)
            for ses in sesiones:
                etiqueta = f"◆ {ses} — {r['nombre']}"
                valores.append(etiqueta)
                mapa[etiqueta] = ("semanal", r["id_rutina_guardada"], ses)
        return valores, mapa

    def _sem_editar_semana_celda(self, event=None):
        """Doble clic en la tabla Semana: en Sesión despliega las
        opciones o renombra; en Ejercicios escribe cuántos campos de
        ejercicio tendrá el día y la tabla genera las filas."""
        tree = self.tree_sem_semana
        sel = tree.selection()
        if not sel or sel[0] not in self._sem_datos:
            return
        if event is not None:
            col = tree.identify_column(event.x)
        else:
            col = "#2"
        if not col or not col.startswith("#"):
            return
        indice = int(col[1:]) - 1
        columnas = tree["columns"]
        if not 0 <= indice < len(columnas):
            return
        if columnas[indice] == "sesion":
            self._sem_editar_sesion()
        elif columnas[indice] == "total":
            self._sem_editar_total()

    def _sem_editar_total(self, _event=None):
        """Doble clic en la columna Ejercicios: escribe cuántos
        ejercicios tendrá el día (0-30) y la tabla genera las filas
        vacías para rellenar (o recorta las que sobren)."""
        tree = self.tree_sem_semana
        sel = tree.selection()
        if not sel or sel[0] not in self._sem_datos:
            return
        dia = sel[0]
        caja = tree.bbox(dia, "total")
        if not caja:
            return
        self._sem_cerrar_editor()
        editor = tk.Entry(tree, justify="center")
        editor.insert(0, str(len(self._sem_datos[dia]["ejercicios"])))
        editor.place(x=caja[0], y=caja[1], w=caja[2], h=caja[3])
        self._sem_editor = editor

        def commit(_event=None):
            try:
                texto = editor.get().strip()
            except Exception:
                return
            self._sem_cerrar_editor()
            try:
                total = max(0, min(30, int(texto)))
            except ValueError:
                return
            self._sem_fijar_total(dia, total)

        editor.bind("<Return>", commit)
        editor.bind("<FocusOut>", commit)
        editor.bind("<Escape>", lambda _e: self._sem_cerrar_editor())
        editor.focus_set()

    def _sem_fijar_total(self, dia, total):
        """Deja el día con exactamente `total` filas: recorta las que
        sobren o añade campos '(elige grupo y ejercicio)' para
        rellenar con el editor de dos niveles."""
        info = self._sem_datos[dia]
        if total > 0 and not info["sesion"]:
            info["sesion"] = f"Sesión {dia}"
        actuales = info["ejercicios"]
        if total < len(actuales):
            info["ejercicios"] = actuales[:total]
        else:
            while len(info["ejercicios"]) < total:
                info["ejercicios"].append(
                    self._sem_ficha_con_prescripcion(
                        {
                            "grupo": None,
                            "num": None,
                            "nombre": "(elige grupo y ejercicio)",
                            "equipo": "",
                        }
                    )
                )
        self._sem_dia = dia
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self._mensaje(f"{dia}: {total} campos de ejercicio para rellenar.")

    def _sem_editar_sesion(self, _event=None):
        """Doble clic en la columna Sesión: despliega las opciones
        disponibles para el día — descanso, las sesiones ya presentes
        en la semana, las rutinas guardadas simples (★) y las sesiones
        de las rutinas semanales guardadas y de las plantillas del
        estudio (◆) — o escribe un nombre nuevo para la sesión."""
        tree = self.tree_sem_semana
        sel = tree.selection()
        if not sel or sel[0] not in self._sem_datos:
            return
        dia = sel[0]
        caja = tree.bbox(dia, "sesion")
        if not caja:
            return
        valores, mapa = self._sem_opciones_sesion(dia)
        self._sem_cerrar_editor()
        # combobox editable: elige de la lista o escribe el nombre
        editor = ttk.Combobox(tree, values=valores)
        editor.set(self._sem_datos[dia]["sesion"] or "")
        editor.place(x=caja[0], y=caja[1], w=max(caja[2], 240), h=caja[3])
        self._sem_editor = editor

        def commit(_event=None):
            try:
                elegido = editor.get().strip()
            except Exception:
                return
            self._sem_cerrar_editor()
            self._sem_aplicar_sesion(dia, elegido, mapa)

        editor.bind("<Return>", commit)
        editor.bind("<FocusOut>", commit)
        editor.bind("<<ComboboxSelected>>", commit)
        editor.bind("<Escape>", lambda _e: self._sem_cerrar_editor())
        editor.focus_set()

    def _sem_aplicar_sesion(self, dia, elegido, mapa):
        """Aplica la opción elegida en el desplegable de Sesión:
        descanso, copia de una sesión de la semana, carga de una
        rutina guardada o de una sesión de plantilla, o renombrado
        con texto libre (vacío deja el día como descanso)."""
        if not elegido:
            self._sem_datos[dia]["sesion"] = None
            self._sem_datos[dia]["ejercicios"] = []
            self._sem_dia = dia
            self._sem_pintar_semana()
            self._sem_pintar_ejercicios()
            self._mensaje(f"{dia}: día de descanso.")
            return
        origen = mapa.get(elegido)
        if origen is None:
            # texto libre: renombra la sesión (o la crea si descansaba)
            self._sem_datos[dia]["sesion"] = elegido
            self._sem_dia = dia
            self._sem_pintar_semana()
            self._sem_pintar_ejercicios()
            return
        tipo = origen[0]
        if tipo == "descanso":
            self._sem_datos[dia]["sesion"] = None
            self._sem_datos[dia]["ejercicios"] = []
            self._sem_dia = dia
            self._sem_pintar_semana()
            self._sem_pintar_ejercicios()
            self._mensaje(f"{dia}: día de descanso.")
            return
        ejercicios = []
        nombre_sesion = elegido
        if tipo == "semana":
            _, dia_origen = origen
            nombre_sesion = self._sem_datos[dia_origen]["sesion"] or elegido
            ejercicios = [
                self._sem_ficha_con_prescripcion(dict(f))
                for f in self._sem_datos[dia_origen]["ejercicios"]
            ]
        elif tipo == "simple":
            try:
                rutina = database.get_rutina_guardada(origen[1])
            except Exception:
                rutina = None
            nombre_sesion = (rutina or {}).get("nombre") or elegido[2:]
            ejercicios = [
                self._sem_ficha_con_prescripcion(dict(e))
                for e in (rutina or {}).get("ejercicios", [])
                if not e.get("descanso")
            ]
        elif tipo == "fija":
            _, idx, sesion = origen
            plantilla = PLANTILLAS_SEMANA[idx]
            sesiones, _faltan = self._fichas_plantilla(plantilla)
            nombre_sesion = sesion
            ejercicios = [
                self._sem_ficha_con_prescripcion(f, plantilla)
                for f in sesiones.get(sesion, [])
            ]
        elif tipo == "semanal":
            _, id_rutina, sesion = origen
            try:
                rutina = database.get_rutina_guardada(id_rutina)
            except Exception:
                rutina = None
            nombre_sesion = sesion
            ejercicios = [
                self._sem_ficha_con_prescripcion(dict(e))
                for e in (rutina or {}).get("ejercicios", [])
                if not e.get("descanso")
                and (e.get("notas") or "").strip() == sesion
            ]
        self._sem_datos[dia]["sesion"] = nombre_sesion
        self._sem_datos[dia]["ejercicios"] = ejercicios
        self._sem_dia = dia
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self._mensaje(
            f"{dia}: «{nombre_sesion}» con {len(ejercicios)} ejercicios."
        )

    def _sem_editar_celda_evento(self, event=None):
        """Doble clic en la tabla de ejercicios: edita la celda (ejercicio
        desde el catálogo, o texto libre en series, repeticiones,
        descansos y peso)."""
        tree = self.tree_sem_ej
        sel = tree.selection()
        if sel and sel[0] == "nuevo":
            # día vacío: despliega el catálogo para el primer ejercicio
            self._sem_anadir_primero(event)
            return
        if not sel or not sel[0].isdigit():
            return
        idx = int(sel[0])
        ejercicios = self._sem_datos[self._sem_dia]["ejercicios"]
        if not 0 <= idx < len(ejercicios):
            return
        if event is not None:
            col = tree.identify_column(event.x)
        else:
            col = "#2"
        if not col or not col.startswith("#"):
            return
        indice = int(col[1:]) - 1
        columnas = tree["columns"]
        if not 0 <= indice < len(columnas):
            return
        col_nombre = columnas[indice]
        editables = (
            "num", "ejercicio", "series", "repeticiones", "descanso_rep",
            "descanso_series", "peso",
        )
        if col_nombre not in editables:
            return
        caja = tree.bbox(sel[0], col_nombre)
        if not caja:
            return
        valor = tree.item(sel[0], "values")[indice]
        self._sem_cerrar_editor()
        if col_nombre in ("num", "ejercicio"):
            # doble clic en # o en Ejercicio: editor de dos niveles
            # (Grupo ▼ y Ejercicio ▼ filtrado por grupo) para AÑADIR
            # un ejercicio nuevo (#) o REEMPLAZAR el de la fila
            if col_nombre == "num":
                def al_elegir(elegido):
                    self._sem_insertar_ejercicio(idx, elegido)
            else:
                def al_elegir(elegido):
                    self._sem_aplicar_celda(idx, "ejercicio", elegido)
                    self._sem_pintar_ejercicios()
            self._sem_editor_ejercicio(tree, caja, valor, al_elegir)
            return
        editor = tk.Entry(tree, justify="center")
        if valor != "—":
            editor.insert(0, valor)
        editor.place(x=caja[0], y=caja[1], w=caja[2], h=caja[3])
        self._sem_editor = editor

        def commit(_event=None):
            try:
                nuevo = editor.get().strip()
            except Exception:
                return
            self._sem_cerrar_editor()
            self._sem_aplicar_celda(idx, col_nombre, nuevo)
            self._sem_pintar_ejercicios()

        editor.bind("<Return>", commit)
        editor.bind("<FocusOut>", commit)
        editor.bind("<Escape>", lambda _e: self._sem_cerrar_editor())
        editor.focus_set()

    def _sem_aplicar_celda(self, idx, col, nuevo):
        """Escribe en el editor el valor de una celda editada."""
        ejercicios = self._sem_datos[self._sem_dia]["ejercicios"]
        if not 0 <= idx < len(ejercicios):
            return
        ej = ejercicios[idx]
        if col == "ejercicio":
            destino = self._sem_opciones.get(nuevo)
            if not destino:
                self._mensaje("Ese ejercicio no está en el catálogo.")
                return
            try:
                ficha = database.get_rutina_ejercicio(
                    destino["grupo"], destino["num"]
                )
            except Exception:
                ficha = None
            ej["grupo"] = destino["grupo"]
            ej["num"] = destino["num"]
            if ficha:
                ej["nombre"] = ficha.get("nombre") or nuevo
                ej["equipo"] = ficha.get("equipo") or ""
            else:
                ej["nombre"] = nuevo
        else:
            ej[col] = nuevo

    def _sem_editor_ejercicio(self, tree, caja, valor_actual, al_elegir):
        """Editor en celda de dos niveles: Grupo ▼ (Hombros, Brazos…)
        y Ejercicio ▼ con la lista filtrada por el grupo; al elegir el
        ejercicio se ejecuta al_elegir(etiqueta) y se cierra."""
        self._sem_cargar_catalogo()
        grupos = []
        for f in self._sem_catalogo:
            if f["grupo"] not in grupos:
                grupos.append(f["grupo"])
        etiqueta_grupo = {
            g: GRUPOS_ETIQUETAS.get(g, g.capitalize()) for g in grupos
        }
        marco = ttk.Frame(tree, style="Gym.TFrame")
        combo_g = ttk.Combobox(
            marco,
            values=["Todos"] + [etiqueta_grupo[g] for g in grupos],
            state="readonly", width=11,
        )
        combo_g.current(0)
        combo_e = ttk.Combobox(
            marco, values=list(self._sem_opciones), state="readonly",
            width=44,
        )
        if valor_actual and valor_actual in self._sem_opciones:
            combo_e.set(valor_actual)
        combo_g.pack(side="left", padx=(0, 3))
        combo_e.pack(side="left")
        marco.place(
            x=caja[0], y=caja[1], w=max(caja[2], 430), h=caja[3]
        )
        self._sem_editor = marco
        bruto = {etiqueta_grupo[g]: g for g in grupos}

        def filtrar(_event=None):
            elegido = bruto.get(combo_g.get())
            if elegido is None:
                combo_e.configure(values=list(self._sem_opciones))
            else:
                combo_e.configure(values=[
                    v for v in self._sem_opciones
                    if f" — {elegido} #" in v
                ])
            combo_e.set("")

        combo_g.bind("<<ComboboxSelected>>", filtrar)

        def commit(_event=None):
            elegido = combo_e.get().strip()
            if not elegido or elegido not in self._sem_opciones:
                self._sem_cerrar_editor()
                return
            self._sem_cerrar_editor()
            al_elegir(elegido)

        combo_e.bind("<<ComboboxSelected>>", commit)
        combo_e.bind("<Return>", commit)
        for combo in (combo_g, combo_e):
            combo.bind("<Escape>", lambda _e: self._sem_cerrar_editor())
        combo_e.focus_set()

    def _sem_anadir_primero(self, event=None):
        """Fila de invitación de un día sin ejercicios: despliega el
        editor de dos niveles (grupo y ejercicio) para añadir el
        primero de la sesión; si el día descansaba, la sesión se crea
        con el nombre del día."""
        tree = self.tree_sem_ej
        caja = tree.bbox("nuevo", "ejercicio")
        if not caja:
            return
        self._sem_cerrar_editor()

        def al_elegir(elegido):
            self._sem_insertar_ejercicio(-1, elegido)

        self._sem_editor_ejercicio(tree, caja, "", al_elegir)

    def _sem_cargar_catalogo(self):
        """Catálogo completo de ejercicios para la celda Ejercicio:
        etiqueta «nombre — grupo #num» → (grupo, num)."""
        if self._sem_catalogo:
            return
        filas = []
        try:
            conn = database.get_connection()
            try:
                conn.row_factory = sqlite3.Row
                filas = conn.execute(
                    "SELECT grupo, num, nombre, equipo FROM rutinas_ejercicios "
                    "ORDER BY grupo, CAST(num AS INTEGER)"
                ).fetchall()
            finally:
                conn.close()
            filas = [dict(f) for f in filas]
        except Exception:
            filas = []
        self._sem_catalogo = filas
        for f in filas:
            etiqueta = f"{f['nombre']} — {f['grupo']} #{f['num']}"
            self._sem_opciones[etiqueta] = {
                "grupo": f["grupo"], "num": f["num"],
            }

    # ------------------------------------------------------------------
    # Añadir, quitar, reordenar y traer rutinas guardadas al día
    # ------------------------------------------------------------------
    def _sem_agregar_ejercicio(self):
        """Añade a la tabla del día el ejercicio elegido en la lista
        'Añadir del catálogo' (con 3×12 y 60 s para editar en
        celda); funciona también en sesiones nuevas y vacías."""
        info = self._sem_datos[self._sem_dia]
        if not info["sesion"]:
            info["sesion"] = f"Sesión {self._sem_dia}"
        etiqueta = self.combo_sem_anadir.get()
        destino = self._sem_opciones.get(etiqueta)
        if not destino:
            self._mensaje(
                "Elige un ejercicio en la lista «Añadir del catálogo»."
            )
            return
        try:
            ficha = database.get_rutina_ejercicio(
                destino["grupo"], destino["num"]
            )
        except Exception:
            ficha = None
        info["ejercicios"].append(
            self._sem_ficha_con_prescripcion(
                {
                    "grupo": destino["grupo"],
                    "num": destino["num"],
                    "nombre": (ficha or {}).get("nombre") or etiqueta,
                    "equipo": (ficha or {}).get("equipo") or "",
                }
            )
        )
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self.tree_sem_ej.see(str(len(info["ejercicios"]) - 1))

    def _sem_insertar_ejercicio(self, idx, etiqueta):
        """Añade un ejercicio nuevo del catálogo debajo de la fila
        idx de la tabla (doble clic en #): crea la sesión si el día
        descansaba y deja 3×12 con 60 s para editar en la celda."""
        destino = self._sem_opciones.get(etiqueta)
        if not destino:
            self._mensaje("Ese ejercicio no está en el catálogo.")
            return
        info = self._sem_datos[self._sem_dia]
        if not info["sesion"]:
            info["sesion"] = f"Sesión {self._sem_dia}"
        try:
            ficha = database.get_rutina_ejercicio(
                destino["grupo"], destino["num"]
            )
        except Exception:
            ficha = None
        nuevo = self._sem_ficha_con_prescripcion(
            {
                "grupo": destino["grupo"],
                "num": destino["num"],
                "nombre": (ficha or {}).get("nombre") or etiqueta,
                "equipo": (ficha or {}).get("equipo") or "",
            }
        )
        ejercicios = info["ejercicios"]
        posicion = min(idx + 1, len(ejercicios))
        ejercicios.insert(posicion, nuevo)
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self.tree_sem_ej.selection_set(str(posicion))
        self.tree_sem_ej.see(str(posicion))
        self._mensaje(
            f"Ejercicio añadido en {self._sem_dia}: "
            f"{nuevo['nombre']} (posición {posicion + 1})."
        )

    def _sem_quitar_ejercicio(self):
        sel = self.tree_sem_ej.selection()
        if not sel or not sel[0].isdigit():
            return
        idx = int(sel[0])
        ejercicios = self._sem_datos[self._sem_dia]["ejercicios"]
        if 0 <= idx < len(ejercicios):
            ejercicios.pop(idx)
            self._sem_pintar_semana()
            self._sem_pintar_ejercicios()

    def _sem_mover(self, delta):
        sel = self.tree_sem_ej.selection()
        if not sel or not sel[0].isdigit():
            return
        idx = int(sel[0])
        ejercicios = self._sem_datos[self._sem_dia]["ejercicios"]
        destino = idx + delta
        if not 0 <= idx < len(ejercicios) or not 0 <= destino < len(ejercicios):
            return
        ejercicios[idx], ejercicios[destino] = (
            ejercicios[destino], ejercicios[idx],
        )
        self._sem_pintar_ejercicios()
        self.tree_sem_ej.selection_set(str(destino))
        self.tree_sem_ej.see(str(destino))

    def _sem_agregar_guardada_al_dia(self):
        """Agrega al día seleccionado los ejercicios de una rutina simple
        guardada en la biblioteca (con su prescripción)."""
        etiqueta = self.combo_sem_simple.get()
        guardada = next(
            (r for r in getattr(self, "_sem_simples", [])
             if r["nombre"] == etiqueta),
            None,
        )
        if not guardada:
            self._mensaje("Elige una rutina guardada de la lista.")
            return
        try:
            rutina = database.get_rutina_guardada(guardada["id_rutina_guardada"])
        except Exception:
            rutina = None
        ejercicios = [
            e for e in (rutina or {}).get("ejercicios", [])
            if not e.get("descanso")
        ]
        if not ejercicios:
            self._mensaje("La rutina guardada está vacía.")
            return
        info = self._sem_datos[self._sem_dia]
        if not info["sesion"]:
            info["sesion"] = guardada["nombre"]
        for e in ejercicios:
            info["ejercicios"].append(self._sem_ficha_con_prescripcion(dict(e)))
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self._mensaje(
            f"Agregados {len(ejercicios)} ejercicios de "
            f"«{guardada['nombre']}» al día {self._sem_dia}."
        )

    def _sem_guardar_dia_simple(self):
        """Guarda los ejercicios del día seleccionado como una rutina
        simple NUEVA en la biblioteca (upsert por nombre): usa el
        nombre del campo Nombre o, si está vacío, el de la sesión del
        día; queda disponible en el desplegable ★ y en el combo."""
        ejercicios = self._sem_datos[self._sem_dia]["ejercicios"]
        if not ejercicios:
            self._mensaje("El día no tiene ejercicios para guardar.")
            return
        nombre = self.entrada_sem_nombre.get().strip()
        if not nombre:
            nombre = (self._sem_datos[self._sem_dia]["sesion"]
                      or f"Rutina {self._sem_dia}")
        filas = []
        for i, ej in enumerate(ejercicios, start=1):
            filas.append(
                {
                    "dia": "", "orden": i, "descanso": 0,
                    "grupo": ej.get("grupo"), "num": ej.get("num"),
                    "nombre": ej.get("nombre"), "equipo": ej.get("equipo"),
                    "series": ej.get("series") or "",
                    "repeticiones": ej.get("repeticiones") or "",
                    "descanso_rep": ej.get("descanso_rep") or "",
                    "descanso_series": ej.get("descanso_series") or "",
                    "peso": ej.get("peso") or "",
                    "notas": "",
                }
            )
        try:
            database.guardar_rutina_guardada(nombre, 0, filas)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo guardar la rutina:\n{error}"
            )
            return
        self._sem_refrescar_selector()
        self._mensaje(
            f"Rutina nueva guardada: «{nombre}» "
            f"({len(ejercicios)} ejercicios del {self._sem_dia})."
        )

    # ------------------------------------------------------------------
    # Guardar, aplicar y eliminar la rutina semanal
    # ------------------------------------------------------------------
    def _sem_guardar(self):
        """Guarda la semana de las tablas como rutina semanal con nombre
        (upsert por nombre): sesiones, descansos y la prescripción de cada
        ejercicio quedan en la biblioteca."""
        nombre = self.entrada_sem_nombre.get().strip()
        if not nombre:
            self._mensaje("Escribe un nombre para guardar la rutina semanal.")
            return
        total = sum(len(d["ejercicios"]) for d in self._sem_datos.values())
        if not total:
            self._mensaje("La semana está vacía: añade ejercicios antes de guardar.")
            return
        filas = []
        for dia in DIAS_SEMANA:
            info = self._sem_datos[dia]
            if not info["sesion"]:
                filas.append(
                    {
                        "dia": dia, "orden": 1, "descanso": 1,
                        "grupo": None, "num": None, "nombre": "Descanso",
                        "equipo": "", "series": "", "repeticiones": "",
                        "descanso_rep": "", "descanso_series": "", "peso": "",
                        "notas": "",
                    }
                )
                continue
            for i, ej in enumerate(info["ejercicios"], start=1):
                filas.append(
                    {
                        "dia": dia, "orden": i, "descanso": 0,
                        "grupo": ej.get("grupo"), "num": ej.get("num"),
                        "nombre": ej.get("nombre"), "equipo": ej.get("equipo"),
                        "series": ej.get("series") or "",
                        "repeticiones": ej.get("repeticiones") or "",
                        "descanso_rep": ej.get("descanso_rep") or "",
                        "descanso_series": ej.get("descanso_series") or "",
                        "peso": ej.get("peso") or "",
                        "notas": info["sesion"],
                    }
                )
        try:
            database.guardar_rutina_guardada(nombre, True, filas)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo guardar la rutina semanal:\n{error}"
            )
            return
        self._sem_nombre = nombre
        self._sem_origen = "guardada"
        self._sem_refrescar_selector()
        # la semana recien guardada aparece como base en Ciclos
        self._cic_refrescar_bases()
        # guarda para el paciente: aplica la semana de las tablas
        if self._sem_aplicar_al_paciente(nombre):
            self.dia_actual = next(
                (d for d in DIAS_SEMANA if self._sem_datos[d]["sesion"]),
                DIAS_SEMANA[0],
            )
            self._cargar_rutina()
            self._marcar_rutina_guardada()
            self._mensaje(
                f"Rutina semanal guardada y aplicada al paciente: "
                f"«{nombre}» ({total} ejercicios)."
            )
        else:
            self._mensaje(
                f"Rutina semanal guardada en la biblioteca: «{nombre}» "
                f"({total} ejercicios). Sin paciente seleccionado para "
                "aplicarla."
            )

    def _sem_aplicar_al_paciente(self, nombre):
        """Escribe la semana de las tablas en la rutina del paciente:
        borra su semana actual, inserta ejercicios y descansos y
        etiqueta la semana aplicada. True si se escribió en la BD.
        (Núcleo común de GUARDAR y APLICAR AL PACIENTE.)"""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            return False
        try:
            database.delete_rutinas_paciente(paciente_id)
            for dia in DIAS_SEMANA:
                info = self._sem_datos[dia]
                if not info["sesion"] or not info["ejercicios"]:
                    database.marcar_descanso(paciente_id, dia)
                    continue
                for ej in info["ejercicios"]:
                    database.insert_rutina_paciente(
                        {
                            "paciente_id": paciente_id,
                            "dia": dia,
                            "grupo": ej.get("grupo"),
                            "num": ej.get("num"),
                            "nombre": ej.get("nombre"),
                            "equipo": ej.get("equipo"),
                            "series": ej.get("series") or "",
                            "repeticiones": ej.get("repeticiones") or "",
                            "descanso_rep": ej.get("descanso_rep") or "",
                            "descanso_series": ej.get("descanso_series") or "",
                            "peso": ej.get("peso") or "",
                            "notas": info["sesion"],
                        }
                    )
            database.marcar_semana_aplicada(paciente_id, nombre)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo aplicar la rutina semanal:\n{error}"
            )
            return False
        # historial: copia de la semana guardada del paciente con fecha
        detalle = json.dumps(
            [
                {
                    "dia": dia,
                    "sesion": self._sem_datos[dia]["sesion"] or "",
                    "ejercicios": [
                        {
                            k: ej.get(k)
                            for k in (
                                "grupo", "num", "nombre", "equipo",
                                "series", "repeticiones", "descanso_rep",
                                "descanso_series", "peso",
                            )
                        }
                        for ej in self._sem_datos[dia]["ejercicios"]
                    ],
                }
                for dia in DIAS_SEMANA
            ],
            ensure_ascii=False,
        )
        try:
            database.guardar_rutina_historial(paciente_id, nombre, detalle)
            self._sem_refrescar_historial()
            self._refrescar_historial_pac()
        except Exception:
            pass   # el historial no debe impedir la aplicación
        return True

    def _sem_aplicar(self):
        """Aplica la semana de las tablas a la rutina del paciente:
        reemplaza sus 7 días (ejercicios y descansos), carga el primer
        día entrenable en la sub-pestaña Rutina y cierra las tablas.
        (Para guardar además en la biblioteca, usa GUARDAR.)"""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            self._mensaje(
                "Selecciona un paciente antes de aplicar la rutina semanal."
            )
            return
        nombre = (
            self.entrada_sem_nombre.get().strip()
            or self._sem_nombre
            or "Semana del paciente"
        )
        if not self._sem_aplicar_al_paciente(nombre):
            return
        self.dia_actual = next(
            (d for d in DIAS_SEMANA if self._sem_datos[d]["sesion"]),
            DIAS_SEMANA[0],
        )
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje(f"Rutina semanal aplicada: «{nombre}».")
        # cierra las tablas semanales y muestra la semana aplicada
        self._sem_cerrar_panel()
        try:
            self.notebook_rut.select(1)   # sub-pestaña Rutina
        except Exception:
            pass

    def _sem_refrescar_historial(self):
        """Tabla del historial: las rutinas semanales guardadas del
        paciente con su fecha, la más reciente primero."""
        if not hasattr(self, "tree_sem_historial"):
            return
        for iid in self.tree_sem_historial.get_children():
            self.tree_sem_historial.delete(iid)
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            self.tree_sem_historial.insert(
                "", "end", iid="sin",
                values=("Sin paciente seleccionado", "—", "—", "—"),
            )
            return
        try:
            entradas = database.get_rutinas_historial(paciente_id)
        except Exception:
            entradas = []
        if not entradas:
            self.tree_sem_historial.insert(
                "", "end", iid="sin",
                values=(
                    "Aún no hay rutinas guardadas para este paciente",
                    "—", "—", "—",
                ),
            )
            return
        for e in entradas:
            self.tree_sem_historial.insert(
                "", "end", iid=str(e["id_historial"]),
                values=(
                    e["nombre_semana"], e["fecha"],
                    e["ejercicios"], e["dias"],
                ),
            )

    def _sem_cargar_historial(self):
        """Carga en las tablas la rutina guardada del paciente elegida
        en el historial (doble clic): restaura los 7 días con su
        sesión y ejercicios y deja el nombre en el campo Nombre, lista
        para editarla y volver a aplicar o guardar."""
        tree = self.tree_sem_historial
        sel = tree.selection()
        if not sel or not sel[0].isdigit():
            self._mensaje(
                "Elige una rutina guardada del paciente en el historial."
            )
            return
        try:
            entrada = database.get_rutina_historial(int(sel[0]))
        except Exception:
            entrada = None
        if not entrada:
            self._mensaje("No se pudo leer la rutina guardada del paciente.")
            return
        self._sem_datos = self._sem_semana_vacia()
        for d in entrada.get("dias", []):
            dia = d.get("dia") or "Lunes"
            if dia not in self._sem_datos:
                continue
            sesion = (d.get("sesion") or "").strip() or None
            self._sem_datos[dia]["sesion"] = sesion
            self._sem_datos[dia]["ejercicios"] = [
                self._sem_ficha_con_prescripcion(dict(e))
                for e in d.get("ejercicios", [])
            ]
        self._sem_nombre = entrada.get("nombre_semana") or "Rutina del paciente"
        self._sem_origen = "paciente"
        self._sem_guardada_id = None
        self.entrada_sem_nombre.delete(0, tk.END)
        self.entrada_sem_nombre.insert(0, self._sem_nombre)
        self._sem_dia = next(
            (d for d in DIAS_SEMANA if self._sem_datos[d]["sesion"]),
            DIAS_SEMANA[0],
        )
        self._sem_pintar_semana()
        self._sem_pintar_ejercicios()
        self._mensaje(
            f"Rutina del paciente cargada: «{self._sem_nombre}» "
            f"(guardada {entrada.get('fecha') or '—'})."
        )

    def _abrir_menu_sem_imprimir(self):
        """Despliega las opciones de impresión de la semana debajo del
        botón IMPRIMIR SEMANA."""
        boton = self.btn_sem_imprimir
        self.menu_sem_imprimir.tk_popup(
            boton.winfo_rootx(),
            boton.winfo_rooty() + boton.winfo_height(),
        )

    def _sem_imprimir(self, modo="todo", guardar=False):
        """Genera el PDF de la rutina semanal tal como está en las
        tablas (vista de la semana, tabla por día y detalle con
        ilustraciones del catálogo) en el modo elegido ("tabla", solo
        el plan y las tablas; "descripcion", solo el detalle; "todo",
        ambos) y lo abre; funciona con o sin paciente seleccionado. Con
        guardar=True pide carpeta y nombre y el PDF se escribe ahí."""
        plan = []
        for dia in DIAS_SEMANA:
            info = self._sem_datos[dia]
            if not info["sesion"]:
                # los días de descanso entran como fila marcada
                plan.append(
                    {
                        "dia": dia, "orden": 1, "descanso": 1,
                        "nombre": "Descanso", "equipo": "",
                        "series": "", "repeticiones": "",
                        "descanso_rep": "", "descanso_series": "",
                        "peso": "", "notas": "",
                        "grupo": None, "num": None,
                    }
                )
                continue
            for i, ej in enumerate(info["ejercicios"], start=1):
                fila = {
                    "dia": dia,
                    "orden": i,
                    "descanso": 0,
                    "grupo": ej.get("grupo"),
                    "num": ej.get("num"),
                    "nombre": ej.get("nombre"),
                    "equipo": ej.get("equipo"),
                    "series": ej.get("series") or "",
                    "repeticiones": ej.get("repeticiones") or "",
                    "descanso_rep": ej.get("descanso_rep") or "",
                    "descanso_series": ej.get("descanso_series") or "",
                    "peso": ej.get("peso") or "",
                    "notas": info["sesion"],
                }
                try:
                    ficha = database.get_rutina_ejercicio(
                        fila["grupo"], fila["num"]
                    )
                except Exception:
                    ficha = None
                if ficha:
                    for campo in ("descripcion", "imagen_blob",
                                  "imagen_nombre"):
                        fila[campo] = ficha.get(campo)
                plan.append(fila)
        if not any(not f.get("descanso") for f in plan):
            self._mensaje(
                "La semana está vacía: añade ejercicios antes de imprimir."
            )
            return
        paciente_id = self._paciente_actual()
        paciente = {}
        if paciente_id is not None:
            try:
                paciente = database.obtener_paciente(paciente_id) or {}
            except Exception:
                paciente = {}
        nombre = (
            self.entrada_sem_nombre.get().strip()
            or self._sem_nombre
            or "Rutina semanal"
        )
        if paciente.get("nombre"):
            nombre = f"{nombre} — {paciente['nombre']}"
        if guardar:
            # el usuario elige carpeta y nombre; cancelar no genera nada
            ruta = rutina_print.pedir_guardar_pdf(
                "Rutina", nombre, parent=self.marco.winfo_toplevel()
            )
            if not ruta:
                return
        else:
            ruta = rutina_print.ruta_temporal_pdf(nombre)
        try:
            rutina_print.generar_pdf_rutina(ruta, paciente, plan, modo=modo)
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return
        try:
            rutina_print.abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showerror(
                "Imprimir",
                f"Se generó el PDF en:\n{ruta}\n\n"
                f"No se pudo abrir automáticamente: {error}",
            )
            return
        self._mensaje(
            f"PDF guardado: {ruta}"
            if guardar
            else "Rutina semanal: PDF en Documentos\\Nutrición Deportiva."
        )

    def _sem_eliminar_guardada(self):
        """Elimina de la biblioteca la rutina semanal guardada
        seleccionada en la tabla (las fijas del estudio no se borran)."""
        sel = self.tree_sem_selector.selection()
        if not sel or sel[0] not in getattr(self, "_sem_selector_map", {}):
            self._mensaje(
                "Elige en la tabla la rutina guardada que quieras eliminar."
            )
            return
        origen, clave = self._sem_selector_map[sel[0]]
        if origen != "guardada":
            self._mensaje(
                "Las rutinas fijas del estudio no se pueden eliminar."
            )
            return
        try:
            database.delete_rutina_guardada(clave)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo eliminar la rutina guardada:\n{error}"
            )
            return
        self._sem_refrescar_selector()
        self._mensaje("Rutina semanal guardada eliminada.")
    def _recargar_referencias_1rm(self):
        """Llena el combo "1RM de referencia": el último calculado en la
        sesión y los guardados del paciente activo; preselecciona el del
        ejercicio mostrado."""
        if not hasattr(self, "combo_rm_ref"):
            return
        referencias = []
        if self.rm_sesion:
            referencias.append(
                {
                    "rm": self.rm_sesion.get("resultado") or 0,
                    "ejercicio": self.rm_sesion.get("ejercicio") or "",
                    "etiqueta": (
                        f"Sesión · {self.rm_sesion['ejercicio']} — "
                        f"{self.rm_sesion['resultado']:g} kg"
                    ),
                }
            )
        paciente_id = self._paciente_actual()
        if paciente_id is not None:
            try:
                registros = database.get_uno_rm(paciente_id)
            except Exception:
                registros = []
            for reg in registros:
                if not reg.get("resultado"):
                    continue
                # la fecha se guarda AAAA-MM-DD y se muestra DD/MM/AAAA
                fecha = str(reg.get("fecha") or "—")
                try:
                    if fecha != "—":
                        fecha = f"{fecha[8:10]}/{fecha[5:7]}/{fecha[0:4]}"
                except Exception:
                    pass
                referencias.append(
                    {
                        "rm": reg["resultado"],
                        "ejercicio": reg.get("ejercicio") or "",
                        "etiqueta": (
                            f"{fecha} · {reg.get('ejercicio')} — "
                            f"{reg['resultado']:g} kg"
                        ),
                    }
                )
        self._rm_lista = referencias
        self.combo_rm_ref.configure(values=[r["etiqueta"] for r in referencias])

        # preselección: el 1RM del ejercicio mostrado o la primera referencia
        self.combo_rm_ref.set(self._buscar_ref_ejercicio() or (referencias[0]["etiqueta"] if referencias else ""))
        self._llenar_pct_1rm()

    def _buscar_ref_ejercicio(self):
        """Etiqueta de la primera referencia 1RM cuyo ejercicio coincida
        (ignorando mayúsculas y acentos) con el ejercicio mostrado."""
        nombre = _normalizar((self.ejercicio_seleccionado or {}).get("nombre"))
        if not nombre:
            return None
        for ref in self._rm_lista:
            if _normalizar(ref.get("ejercicio")) == nombre:
                return ref["etiqueta"]
        return None

    def _rm_actual(self):
        """Referencia 1RM elegida en el combo (None si no hay ninguna)."""
        texto = self.combo_rm_ref.get()
        for ref in self._rm_lista:
            if ref["etiqueta"] == texto:
                return ref
        return None

    def _llenar_pct_1rm(self):
        """Porcentajes del 1RM elegido con el peso ya calculado y
        redondeado a discos de 2.5 kg."""
        self.combo_rm_pct.set("")
        ref = self._rm_actual()
        if not ref or not ref.get("rm"):
            self.combo_rm_pct.configure(values=[])
            return
        self.combo_rm_pct.configure(
            values=[
                f"{pct}% → {_discos_2_5(ref['rm'] * pct / 100.0):g} kg"
                for pct in PORCENTAJES_1RM
            ]
        )

    # ------------------------------------------------------------------
    # Pestaña Progresión (ACSM 2009: principiantes / intermedios / avanzados)
    # ------------------------------------------------------------------
    def _crear_tab_progresion(self):
        marco = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        self.notebook_rut.add(marco, text="  Progresión  ")

        # ----- ramas de árbol a la izquierda -----
        marco_nivel = ttk.LabelFrame(
            marco, text=" Nivel de entrenamiento ", padding=6,
            style="Gym.TLabelframe",
        )
        marco_nivel.pack(side="left", fill="y", padx=(8, 4), pady=8)

        arbol = ttk.Treeview(
            marco_nivel, show="tree", selectmode="browse", height=6,
            style="Gym.Treeview",
        )
        raiz = arbol.insert("", "end", iid="raiz", open=True,
                            text="🏋 Modelos de progresión")
        arbol.insert(raiz, "end", iid="principiantes",
                     text="🟢 Principiantes")
        arbol.insert(raiz, "end", iid="intermedios",
                     text="🟡 Intermedios")
        arbol.insert(raiz, "end", iid="avanzados", text="🔴 Avanzados")
        arbol.pack(fill="both", expand=True)

        tk.Label(
            marco_nivel, text="Basado en el Position Stand del ACSM "
            "(Med Sci Sports Exerc, 2009).", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO, wraplength=200, justify="left",
        ).pack(anchor="w", pady=(8, 0))

        # ----- panel de contenido a la derecha -----
        marco_detalle = ttk.LabelFrame(
            marco, text=" Recomendaciones ", padding=6,
            style="Gym.TLabelframe",
        )
        marco_detalle.pack(side="left", fill="both", expand=True,
                           padx=(4, 8), pady=8)

        panel = tk.Text(
            marco_detalle, bg=GRIS_OSCURO, fg=BLANCO, relief="flat",
            font=("Segoe UI", 10), wrap="word", padx=14, pady=10,
            height=18,
        )
        panel.pack(side="left", fill="both", expand=True)
        barra_sc = ttk.Scrollbar(marco_detalle, command=panel.yview)
        barra_sc.pack(side="right", fill="y")
        panel.configure(yscrollcommand=barra_sc.set)
        panel.tag_configure("titulo", font=("Impact", 14), foreground=NEON)
        panel.tag_configure("seccion", font=("Segoe UI", 10, "bold"),
                            foreground=NARANJA)
        panel.tag_configure("normal", font=("Segoe UI", 10), foreground=BLANCO,
                            spacing3=4)
        panel.tag_configure("nota", font=("Segoe UI", 9),
                            foreground=GRIS_TEXTO)

        # ----- reglas generales + cita al pie -----
        pie = tk.Label(
            marco, text=REGLAS_GENERALES_PROGRESION
            + "\nAmerican College of Sports Medicine. Progression Models "
            "in Resistance Training for Healthy Adults. Med Sci Sports "
            "Exerc. 2009;41(3):687-708.",
            font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
            wraplength=760, justify="left",
        )
        pie.pack(fill="x", padx=8, pady=(0, 8))

        def mostrar_nivel(_evento=None):
            sel = arbol.selection()
            if not sel or sel[0] == "raiz":
                contenido = CONTENIDO_INTRO_PROGRESION
            else:
                contenido = CONTENIDO_PROGRESION.get(sel[0], "")
            panel.configure(state="normal")
            panel.delete("1.0", "end")
            panel.insert("1.0", contenido, "normal")
            # resalta los renglones que empiezan con ◆ como secciones
            linea = 1
            for renglon in contenido.split("\n"):
                if renglon.startswith("◆ "):
                    panel.delete(f"{linea}.0", f"{linea}.end")
                    panel.insert(f"{linea}.0", renglon[2:], "seccion")
                elif renglon.startswith("TITULO: "):
                    panel.delete(f"{linea}.0", f"{linea}.end")
                    panel.insert(f"{linea}.0", renglon[8:], "titulo")
                linea += 1
            panel.configure(state="disabled")

        arbol.bind("<<TreeviewSelect>>", mostrar_nivel)
        arbol.selection_set("principiantes")
        mostrar_nivel()


    def _cargar_ejercicios(self, grupo=None):
        """Lee los ejercicios del catálogo: TODOS los grupos si no se
        pide uno concreto (el selector diario ya no filtra por grupo)."""
        if grupo:
            self.grupo = grupo
        try:
            if grupo:
                filas = database.get_rutinas_ejercicios(self.grupo)
                if filas:
                    self.ejercicios = filas
                    return
            else:
                todos = []
                for g in GRUPOS_PREFERIDOS:
                    try:
                        todos.extend(database.get_rutinas_ejercicios(g) or [])
                    except Exception:
                        pass
                if todos:
                    self.ejercicios = todos
                    return
        except Exception:
            pass
        # Respaldo: JSON locales de los grupos pedidos
        self.ejercicios = []
        claves = [grupo] if grupo else list(GRUPOS_PREFERIDOS)
        for g in claves:
            nombre_json = CATALOGOS_JSON.get(g, "")
            ruta_json = os.path.join(base_dir(), nombre_json) if nombre_json else ""
            for codificacion in ("utf-8-sig", "utf-8"):
                try:
                    with open(ruta_json, "r", encoding=codificacion) as f:
                        self.ejercicios.extend(json.load(f))
                    break
                except Exception:
                    continue

    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  Rutinas  ")

        fila_titulo = ttk.Frame(self.marco, style="Gym.TFrame")
        fila_titulo.pack(fill="x", pady=(2, 0))

        self.titulo = tk.Label(
            fila_titulo,
            text="RUTINAS",
            font=("Impact", 15),
            fg=NEON,
            bg=GRIS_OSCURO,
        )


        # Calculadora 1RM (por ejercicio, ramas de árbol) a la derecha
        tk.Button(
            fila_titulo,
            text="🏋 1RM",
            command=self._abrir_1rm,
            font=("Impact", 12),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        self.titulo.pack(side="left", fill="x", expand=True)

        self.lbl_estado = ttk.Label(
            self.marco,
            text="Rutinas: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 4))

        self.notebook_rut = ttk.Notebook(self.marco)
        self.notebook_rut.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self._crear_tab_calentamiento()
        self._crear_tab_rutina()
        self._crear_panel_semana()
        self._crear_tab_estiramiento()
        self._crear_tab_progresion()
        self._crear_tab_ciclos()
        self.notebook_rut.bind("<<NotebookTabChanged>>", self._al_cambiar_subpestana)
        self.cargar(getattr(self.app, "id_paciente_antro", None))

    def _crear_tab_calentamiento(self):
        marco = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        self.notebook_rut.add(marco, text="  Calentamiento  ")

        self.calent_items = self._cargar_catalogo_calentamiento()
        self.calent_paciente = {}
        self.calent_actual = None
        self.calent_foto = None

        self.lbl_calent = tk.Label(
            marco,
            text=f"Calentamiento dinámico · {len(self.calent_items)} fichas",
            font=("Segoe UI", 10),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        )
        self.lbl_calent.pack(anchor="w", padx=10, pady=(8, 4))

        contenedor = ttk.Frame(marco, style="Gym.TFrame")
        contenedor.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        izq = ttk.Frame(contenedor, style="Gym.TFrame")
        izq.pack(side="left", fill="both", padx=(0, 10))

        self.calent_tree = ttk.Treeview(
            izq, columns=("orden", "nombre", "dur"), show="headings",
            height=13, style="Gym.Treeview",
        )
        self.calent_tree.heading("orden", text="#")
        self.calent_tree.heading("nombre", text="Ejercicio")
        self.calent_tree.heading("dur", text="Duración")
        self.calent_tree.column("orden", width=36, anchor="center", stretch=False)
        self.calent_tree.column("nombre", width=268, anchor="w")
        self.calent_tree.column("dur", width=80, anchor="center", stretch=False)
        self.calent_tree.pack(fill="both", expand=True)
        self.calent_tree.bind("<<TreeviewSelect>>", self._al_seleccionar_calent)

        caja = ttk.LabelFrame(izq, text="Orden y duración", padding=6)
        caja.pack(fill="x", pady=(6, 0))

        tk.Label(
            caja, text="Orden:", font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO
        ).grid(row=0, column=0, sticky="w")
        self.calent_orden_var = tk.StringVar()
        self.calent_orden = tk.Spinbox(
            caja, from_=1, to=40, width=4, textvariable=self.calent_orden_var,
            bg=GRIS, fg=BLANCO, insertbackground=BLANCO, relief="flat",
        )
        self.calent_orden.grid(row=0, column=1, padx=(4, 14))

        tk.Label(
            caja, text="Duración:", font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO
        ).grid(row=0, column=2, sticky="w")
        self.calent_dur_var = tk.StringVar()
        self.calent_dur = ttk.Combobox(
            caja, textvariable=self.calent_dur_var, width=8, state="readonly",
            values=["30 s", "45 s", "60 s", "75 s", "90 s", "2 min", "3 min"],
            style="Gym.TCombobox",
        )
        self.calent_dur.grid(row=0, column=3, padx=(4, 14))

        ttk.Button(caja, text="GUARDAR", command=self._guardar_calent).grid(row=0, column=4)
        tk.Button(
            caja,
            text="IMPRIMIR",
            command=self._imprimir_calent,
            font=("Impact", 9),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=9,
            pady=3,
            cursor="hand2",
        ).grid(row=0, column=5, padx=(10, 0))

        der = ttk.Frame(contenedor, style="Gym.TFrame")
        der.pack(side="left", fill="both", expand=True)

        self.calent_img = tk.Label(
            der, text="Selecciona un ejercicio", bg=GRIS_OSCURO, fg=GRIS_TEXTO
        )
        self.calent_img.pack(fill="x")

        marco_desc = ttk.Frame(der, style="Gym.TFrame")
        marco_desc.pack(fill="both", expand=True, pady=(6, 0))
        self.calent_desc = tk.Text(
            marco_desc, height=10, wrap="word", bg=GRIS, fg=BLANCO, relief="flat",
            padx=8, pady=6, font=("Segoe UI", 9),
        )
        barra = ttk.Scrollbar(
            marco_desc, orient="vertical", command=self.calent_desc.yview
        )
        self.calent_desc.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.calent_desc.pack(side="left", fill="both", expand=True)
        self.calent_desc.configure(state="disabled")

        self._render_calentamiento()

    # ------------------------------------------------------------------
    # Calentamiento dinámico: catálogo, selección y orden del paciente
    # ------------------------------------------------------------------
    def _cargar_catalogo_calentamiento(self):
        ruta = os.path.join(base_dir(), "calentamiento_powerlifting.json")
        try:
            with open(ruta, encoding="utf-8") as fh:
                datos = json.load(fh)
        except Exception:
            return []
        return sorted(datos, key=lambda d: (int(d.get("orden", 0)), str(d.get("num", ""))))

    def _cargar_calentamiento_paciente(self):
        if not hasattr(self, "calent_tree"):
            return
        paciente_id = getattr(self, "paciente_id", None) or getattr(
            self.app, "id_paciente_antro", None
        )
        if paciente_id is None:
            self.calent_paciente = {}
        else:
            try:
                self.calent_paciente = database.get_calentamiento_paciente(paciente_id) or {}
            except Exception:
                self.calent_paciente = {}
        self._render_calentamiento()

    def _ficha_calentamiento(self, num):
        for ficha in getattr(self, "calent_items", []):
            if str(ficha.get("num")) == str(num):
                return ficha
        return None

    def _render_calentamiento(self):
        if not hasattr(self, "calent_tree"):
            return
        seleccion = self.calent_tree.selection()
        for item in self.calent_tree.get_children():
            self.calent_tree.delete(item)

        filas = []
        for ficha in getattr(self, "calent_items", []):
            num = str(ficha.get("num"))
            ajuste = (getattr(self, "calent_paciente", {}) or {}).get(num, {})
            orden = ajuste.get("orden", ficha.get("orden", 0))
            duracion = ajuste.get("duracion", ficha.get("duracion", ""))
            filas.append((int(orden), num, ficha.get("nombre", ""), duracion))
        filas.sort(key=lambda f: (f[0], f[1]))

        for orden, num, nombre, duracion in filas:
            self.calent_tree.insert("", "end", iid=num, values=(orden, nombre, duracion))

        if not seleccion:
            hijos = self.calent_tree.get_children()
            if hijos:
                self.calent_tree.selection_set(hijos[0])
                self.calent_tree.focus(hijos[0])
                self._al_seleccionar_calent()
            return

        for num in seleccion:
            if self.calent_tree.exists(num):
                self.calent_tree.selection_set(num)
                break

    def _al_seleccionar_calent(self, event=None):
        seleccion = self.calent_tree.selection()
        if not seleccion:
            return
        num = seleccion[0]
        ficha = self._ficha_calentamiento(num)
        if not ficha:
            return
        self.calent_actual = num

        ajuste = (getattr(self, "calent_paciente", {}) or {}).get(num, {})
        self.calent_orden_var.set(str(ajuste.get("orden", ficha.get("orden", ""))))
        self.calent_dur_var.set(str(ajuste.get("duracion", ficha.get("duracion", ""))))

        texto = f"{ficha.get('nombre', '')}\n\n{ficha.get('descripcion', '')}"
        self.calent_desc.configure(state="normal")
        self.calent_desc.delete("1.0", "end")
        self.calent_desc.insert("1.0", texto)
        self.calent_desc.configure(state="disabled")

        self._cargar_imagen_calent(ficha)

    def _cargar_imagen_calent(self, ficha):
        if ImageTk is None:
            self.calent_img.configure(image="", text="Sin vista previa (Pillow no disponible)")
            return
        ruta = os.path.join(
            RUTA_IMAGENES, "calentamiento", "cal_%s.jpeg" % ficha.get("imagen", "")
        )
        try:
            with Image.open(ruta) as imagen:
                copia = imagen.convert("RGB")
                copia.thumbnail((320, 250))
                self.calent_foto = ImageTk.PhotoImage(copia)
        except Exception:
            self.calent_foto = None
            self.calent_img.configure(image="", text="Sin ilustración")
            return
        self.calent_img.configure(image=self.calent_foto, text="")

    def _guardar_calent(self):
        num = getattr(self, "calent_actual", None)
        if not num:
            messagebox.showinfo("Calentamiento", "Selecciona un ejercicio de la lista.")
            return
        try:
            orden = int(str(self.calent_orden_var.get()).strip())
        except Exception:
            messagebox.showwarning("Calentamiento", "El orden debe ser un número entero.")
            return
        duracion = str(self.calent_dur_var.get()).strip()
        if not duracion:
            messagebox.showwarning("Calentamiento", "Elige una duración.")
            return

        self.calent_paciente[num] = {"orden": orden, "duracion": duracion}
        paciente_id = getattr(self, "paciente_id", None) or getattr(
            self.app, "id_paciente_antro", None
        )
        if paciente_id is not None:
            try:
                database.guardar_calentamiento_item(paciente_id, num, orden, duracion)
            except Exception as exc:
                messagebox.showerror("Calentamiento", "No se pudo guardar:\n%s" % exc)
                return
        self._render_calentamiento()
        self._mensaje("Calentamiento: orden %s, %s" % (orden, duracion))

    def _plan_calentamiento(self):
        """Fichas del calentamiento en el orden fijado para el paciente."""
        plan = []
        for ficha in getattr(self, "calent_items", []):
            num = str(ficha.get("num"))
            ajuste = (getattr(self, "calent_paciente", {}) or {}).get(num, {})
            plan.append(
                {
                    "num": num,
                    "nombre": ficha.get("nombre", ""),
                    "zona": ficha.get("zona", ""),
                    "equipo": ficha.get("equipo", ""),
                    "orden": int(ajuste.get("orden", ficha.get("orden", 0)) or 0),
                    "duracion": ajuste.get("duracion", ficha.get("duracion", "")),
                    "imagen": ficha.get("imagen", ""),
                    "descripcion": ficha.get("descripcion", ""),
                }
            )
        plan.sort(key=lambda f: (f["orden"], f["num"]))
        return plan

    def _imprimir_calent(self):
        """Genera el PDF del calentamiento y lo abre para impresión."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Calentamiento", "Selecciona un paciente antes de imprimir."
            )
            return
        plan = self._plan_calentamiento()
        if not plan:
            messagebox.showwarning(
                "Calentamiento", "No hay ejercicios de calentamiento para imprimir."
            )
            return

        paciente = database.obtener_paciente(paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{paciente_id}"
        ruta = calentamiento_print.ruta_temporal_pdf(nombre)
        try:
            calentamiento_print.generar_pdf_calentamiento(ruta, paciente, plan)
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            calentamiento_print.abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showerror(
                "Imprimir",
                f"Se generó el PDF en:\n{ruta}\n\n"
                f"No se pudo abrir automáticamente: {error}",
            )
            return

        self._mensaje("Calentamiento: reporte generado.")

    def _crear_tab_rutina(self):
        self.marco_rut = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        marco = self.marco_rut
        self.notebook_rut.add(marco, text="  Rutina  ")

        # contenedor con scroll vertical: en pantallas donde el contenido
        # no cabe (1366x768 con la vista diaria o las tablas abiertas) la
        # barra llega hasta el fondo en vez de cortar el historial y la
        # barra de días
        lienzo = tk.Canvas(
            marco, bg=GRIS_OSCURO, highlightthickness=0, yscrollincrement=48
        )
        scroll_rut = ttk.Scrollbar(
            marco, orient="vertical", command=lienzo.yview
        )
        lienzo.configure(yscrollcommand=scroll_rut.set)
        lienzo.pack(side="left", fill="both", expand=True)
        scroll_rut.pack(side="right", fill="y")
        interior = ttk.Frame(lienzo, style="Gym.TFrame")
        self.interior_rut = interior
        ventana_rut = lienzo.create_window((0, 0), window=interior, anchor="nw")

        def _ajustar_region(_evento=None):
            lienzo.configure(scrollregion=lienzo.bbox("all"))

        def _ajustar_ancho(evento):
            lienzo.itemconfigure(ventana_rut, width=evento.width)

        def _rueda_lienzo(evento):
            bajo = marco.winfo_toplevel().winfo_containing(
                evento.x_root, evento.y_root
            )
            if bajo is None:
                return
            # solo cuando el puntero está sobre el contenido de Rutina
            dentro = False
            w = bajo
            while w is not None:
                if w is lienzo:
                    dentro = True
                    break
                w = getattr(w, "master", None)
            if not dentro:
                return
            if isinstance(bajo, (ttk.Treeview, tk.Text)):
                return   # los widgets con scroll propio mandan
            paso = -1 * (evento.delta // 120)
            if paso:
                lienzo.yview_scroll(paso, "units")
                return "break"

        interior.bind("<Configure>", _ajustar_region)
        lienzo.bind("<Configure>", _ajustar_ancho)
        marco.bind_all("<MouseWheel>", _rueda_lienzo, add="+")

        # botón que muestra/oculta las tablas de la rutina semanal
        # dentro de esta sub-pestaña (sin cuadros de diálogo)
        fila_sem = ttk.Frame(interior, style="Gym.TFrame")
        fila_sem.pack(side="top", fill="x", padx=10, pady=(4, 0))
        tk.Label(
            fila_sem,
            text="Rutina semanal:",
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(side="left")
        self.btn_ver_semana = tk.Button(
            fila_sem,
            text="📅 ABRIR RUTINA SEMANAL",
            command=self._alternar_panel_semana,
            font=("Segoe UI", 8, "bold"),
            fg=NEON,
            bg=GRIS,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
        )
        self.btn_ver_semana.pack(side="left", padx=(6, 0))

        self.contenedor_rut = ttk.Frame(interior, style="Gym.TFrame")
        contenedor_principal = self.contenedor_rut
        contenedor_principal.pack(fill="both", expand=True, padx=10, pady=(2, 6))

        superior = ttk.Frame(contenedor_principal, style="Gym.TFrame")

        panel_sel = ttk.LabelFrame(superior, text="Seleccionar ejercicio", padding=6)
        self.panel_sel = panel_sel
        panel_sel.pack(side="left", fill="y", padx=(0, 6))

        self.combo_ej = ttk.Combobox(
            panel_sel, values=[], width=46, state="readonly", style="Gym.TCombobox"
        )
        self.combo_ej.pack(pady=(4, 0))
        self.combo_ej.bind("<<ComboboxSelected>>", self._al_seleccionar_combo)
        # agrega el ejercicio seleccionado a la rutina/sesion elegida en
        # el arbol (o al dia activo), con prescripcion inicial 3x12
        tk.Button(
            panel_sel,
            text="＋ AGREGAR A LA RUTINA",
            command=self._agregar_ejercicio_seleccionado,
            font=("Impact", 10),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
        ).pack(fill="x", pady=(4, 0))

        self.lbl_catalogo = tk.Label(
            panel_sel,
            text="",
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
            justify="left",
        )
        self.lbl_catalogo.pack(anchor="w", pady=(6, 0))

        marco_desc = ttk.LabelFrame(
            panel_sel, text="Descripción guardada en la base de datos", padding=4
        )
        marco_desc.pack(fill="both", expand=True, pady=(10, 0))

        self.txt_preview_desc = tk.Text(
            marco_desc,
            width=32,
            height=6,
            wrap="word",
            bg=GRIS_OSCURO,
            fg=BLANCO,
            relief="flat",
            padx=6,
            pady=4,
            font=("Segoe UI", 9),
            highlightthickness=0,
        )
        self.txt_preview_desc.configure(state="disabled")
        barra_desc = ttk.Scrollbar(marco_desc, orient="vertical", command=self.txt_preview_desc.yview)
        self.txt_preview_desc.configure(yscrollcommand=barra_desc.set)
        self.txt_preview_desc.pack(side="left", fill="both", expand=True)
        barra_desc.pack(side="right", fill="y")

        panel_der = ttk.LabelFrame(
            superior,
            text="Previsualización (imagen desde la base de datos)",
            padding=6,
        )
        self.panel_der = panel_der
        panel_der.pack(side="right", fill="both", expand=True)

        self.lbl_preview_titulo = tk.Label(
            panel_der,
            text="Selecciona un ejercicio de la lista desplegable",
            font=("Segoe UI", 10, "bold"),
            fg=NEON,
            bg=GRIS_OSCURO,
            anchor="w",
            justify="left",
        )
        self.lbl_preview_titulo.pack(fill="x")

        cont_img = ttk.Frame(panel_der, style="Gym.TFrame")
        cont_img.pack(fill="both", expand=True, pady=(4, 2))
        cont_img.bind("<Configure>", self._al_redimensionar)
        self._contenedor_img = cont_img

        self.lbl_preview_img = tk.Label(
            cont_img,
            bg=GRIS_OSCURO,
            text="",
            fg=GRIS_TEXTO,
            font=("Segoe UI", 9),
        )
        self.lbl_preview_img.pack(expand=True)

        self.lbl_preview_fuente = tk.Label(
            panel_der,
            text="",
            font=("Segoe UI", 7),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
            anchor="w",
        )
        self.lbl_preview_fuente.pack(fill="x")

        # --- Rutina acumulada del paciente ---
        marco_rutina_pac = ttk.LabelFrame(
            contenedor_principal, text="Rutina del paciente", padding=6
        )

        cols = ("nombre", "equipo", "series", "reps", "desc_rep", "desc_serie", "peso")
        self.tree_rutina = ttk.Treeview(
            marco_rutina_pac,
            columns=cols,
            show="tree headings",
            height=12,
            selectmode="browse",
            style="Gym.Treeview.Compacta",
        )
        # columna #0: jerarquia semana -> dia/sesion -> ejercicios
        self.tree_rutina.heading("#0", text="Semana / Día", anchor="w")
        self.tree_rutina.column(
            "#0", width=250, minwidth=250, anchor="w", stretch=False
        )
        self.tree_rutina.tag_configure("activa", foreground=NEON)
        for col, texto, ancho, alineacion in (
            ("nombre", "Ejercicio", 170, "w"),
            ("equipo", "Equipo", 90, "w"),
            ("series", "Series", 48, "center"),
            ("reps", "Reps", 48, "center"),
            ("desc_rep", "Desc. ej. (s)", 88, "center"),
            ("desc_serie", "Desc. serie (s)", 92, "center"),
            ("peso", "Peso (kg)", 64, "center"),
        ):
            self.tree_rutina.heading(col, text=texto, anchor=alineacion)
            self.tree_rutina.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion,
                stretch=(col == "nombre"),
            )
        barra_rutina = ttk.Scrollbar(
            marco_rutina_pac, orient="vertical", command=self.tree_rutina.yview
        )
        self.tree_rutina.configure(yscrollcommand=barra_rutina.set)
        self.tree_rutina.pack(side="left", fill="both", expand=True)
        barra_rutina.pack(side="left", fill="y")

        acciones = ttk.Frame(marco_rutina_pac, style="Gym.TFrame")
        acciones.pack(side="left", fill="y", padx=(8, 0))
        tk.Button(
            acciones,
            text="Quitar seleccionado",
            command=self._quitar_ejercicio,
            font=("Segoe UI", 8, "bold"),
            fg=BLANCO,
            bg=GRIS,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
        ).pack(fill="x", pady=(0, 4))
        tk.Button(
            acciones,
            text="Vaciar rutina",
            command=self._vaciar_rutina,
            font=("Segoe UI", 8, "bold"),
            fg=BLANCO,
            bg=GRIS,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
        ).pack(fill="x")
        # cambiar la sesion del dia seleccionado en el arbol: sesiones de
        # la semana, rutinas guardadas con estrella o descanso
        tk.Label(
            acciones,
            text="Sesión del día:",
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", pady=(10, 0))
        self.combo_sesion_dia = ttk.Combobox(
            acciones, state="readonly", width=22, style="Gym.TCombobox"
        )
        self.combo_sesion_dia.pack(fill="x")
        self.combo_sesion_dia.bind(
            "<<ComboboxSelected>>", self._al_elegir_sesion_dia
        )
        self._actualizar_sesion_dia()
        self.btn_imprimir_rutina = tk.Button(
            acciones,
            text="IMPRIMIR RUTINA",
            command=self._abrir_menu_imprimir,
            font=("Impact", 9),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
        )
        self.btn_imprimir_rutina.pack(fill="x", pady=(6, 0))
        self.menu_imprimir = tk.Menu(self.tree_rutina, tearoff=0, font=("Segoe UI", 9))
        self.menu_imprimir.add_command(
            label="Tabla semanal", command=lambda: self._imprimir_rutina("tabla")
        )
        self.menu_imprimir.add_command(
            label="Descripciones de ejercicios",
            command=lambda: self._imprimir_rutina("descripcion"),
        )
        self.menu_imprimir.add_separator()
        self.menu_imprimir.add_command(
            label="Tabla + descripciones (todo)",
            command=lambda: self._imprimir_rutina("todo"),
        )
        # guardar sin pasar por Acrobat: elige carpeta y nombre y el PDF
        # se escribe ahí directo (misma elección tabla/descripciones/todo)
        self.menu_imprimir.add_separator()
        menu_guardar = tk.Menu(self.menu_imprimir, tearoff=0, font=("Segoe UI", 9))
        menu_guardar.add_command(
            label="Tabla semanal",
            command=lambda: self._imprimir_rutina("tabla", guardar=True),
        )
        menu_guardar.add_command(
            label="Descripciones de ejercicios",
            command=lambda: self._imprimir_rutina("descripcion", guardar=True),
        )
        menu_guardar.add_command(
            label="Tabla + descripciones (todo)",
            command=lambda: self._imprimir_rutina("todo", guardar=True),
        )
        self.menu_imprimir.add_cascade(
            label="💾 Guardar PDF…", menu=menu_guardar
        )
        # clic derecho sobre la rutina: editar / quitar el ejercicio;
        # doble clic edita, igual que en Menús
        self.tree_rutina.bind("<Button-3>", self._menu_rutina_contextual)
        self.tree_rutina.bind("<Double-1>", self._editar_ejercicio_rutina)
        # la tabla manda: clic en una fila muestra ese ejercicio en el
        # selector y en la previsualizacion (que viven al fondo)
        self.tree_rutina.bind("<<TreeviewSelect>>", self._al_seleccionar_fila_rutina)
        self.menu_rutina_ctx = tk.Menu(self.tree_rutina, tearoff=0, font=("Segoe UI", 9))
        self.menu_rutina_ctx.add_command(
            label="✏ Editar ejercicio", command=self._editar_ejercicio_rutina
        )
        self.menu_rutina_ctx.add_separator()
        self.menu_rutina_ctx.add_command(
            label="🗑 Quitar de la rutina", command=self._quitar_ejercicio
        )
        self.menu_rutina_ctx.add_command(label="Cancelar")
        self.lbl_rutina_total = ttk.Label(
            acciones, text="0 ejercicios", style="Estado.TLabel"
        )
        self.lbl_rutina_total.pack(anchor="w", pady=(8, 0))
        # la rutina se guarda sola en la BD con cada cambio; este letrero
        # lo hace visible ("Guardada en la BD ✓ HH:MM" tras cada escritura)
        self.lbl_rutina_guardada = ttk.Label(
            acciones,
            text="",
            style="Estado.TLabel",
            font=("Segoe UI", 8),
            foreground=GRIS_TEXTO,
        )
        self.lbl_rutina_guardada.pack(anchor="w")


        # --- Barra de días de la rutina semanal (patrón de Menús) ---
        barra_dias = ttk.Frame(contenedor_principal, style="Gym.TFrame")
        tk.Label(
            barra_dias, text="Día:", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left", padx=(6, 6))
        for dia in DIAS_SEMANA:
            btn = tk.Button(
                barra_dias, text=dia,
                command=lambda d=dia: self._cambiar_dia(d),
                font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
                activebackground=NARANJA, activeforeground=BLANCO,
                relief="flat", padx=8, pady=3, cursor="hand2",
            )
            btn.pack(side="left", padx=2)
            self.dia_buttons[dia] = btn
        self.btn_descanso = tk.Button(
            barra_dias, text="MARCAR DÍA DE DESCANSO",
            command=self._alternar_descanso,
            font=("Impact", 9), fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=10, pady=3, cursor="hand2",
        )
        self.btn_descanso.pack(side="right", padx=(6, 0))

        # --- Historial del paciente: rutinas semanales guardadas con
        # fecha (cada GUARDAR/APLICAR deja una copia; doble clic la
        # recupera como rutina actual del paciente) ---
        marco_historial_pac = ttk.LabelFrame(
            contenedor_principal,
            text="Historial del paciente — doble clic: recuperar esta "
                 "rutina fechada",
            padding=4,
            style="Gym.TLabelframe",
        )
        cols_hist = ("nombre", "fecha", "ejercicios", "dias")
        self.tree_historial_pac = ttk.Treeview(
            marco_historial_pac, columns=cols_hist, show="headings",
            height=3, selectmode="browse", style="Gym.Treeview.Compacta",
        )
        for col, texto, ancho, alineacion in (
            ("nombre", "Rutina guardada", 340, "w"),
            ("fecha", "Guardada", 150, "w"),
            ("ejercicios", "Ejercicios", 90, "center"),
            ("dias", "Días", 60, "center"),
        ):
            self.tree_historial_pac.heading(col, text=texto, anchor=alineacion)
            self.tree_historial_pac.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion,
                stretch=(col == "nombre"),
            )
        self.tree_historial_pac.pack(side="left", fill="both", expand=True)
        barra_hist_pac = ttk.Scrollbar(
            marco_historial_pac, orient="vertical",
            command=self.tree_historial_pac.yview,
        )
        self.tree_historial_pac.configure(yscrollcommand=barra_hist_pac.set)
        barra_hist_pac.pack(side="right", fill="y")
        self.tree_historial_pac.bind(
            "<Double-1>", lambda _e: self._aplicar_historial_pac()
        )
        self.marco_historial_pac = marco_historial_pac

        # orden vertical con prioridad: barra de días (arriba) y el
        # historial del paciente (abajo) se empaquetan primero; la tabla
        # del árbol y el selector con su previsualización comparten el
        # resto en un Panedwindow con separador arrastrable: la tabla se
        # puede abrir más o menos a voluntad y, si la ventana no alcanza,
        # los dos paneles ceden proporcionalmente sin desaparecer
        barra_dias.pack(side="top", fill="x", pady=(6, 0))
        self.marco_historial_pac.pack(side="bottom", fill="x", pady=(6, 0))
        panes = ttk.Panedwindow(contenedor_principal, orient="vertical")
        panes.add(marco_rutina_pac, weight=2)
        panes.add(superior, weight=1)
        panes.pack(fill="both", expand=True)
        # reparto inicial: la tabla del árbol se lleva ~68% del cuadro y
        # se recalcula en cada cambio de tamaño hasta que el usuario
        # arrastra el separador (a partir de ahí se respeta su elección)
        reparto = {"ratio": 0.68, "tocado": False}

        def reparto_inicial(_evento=None):
            alto = panes.winfo_height()
            if alto > 60 and not reparto["tocado"]:
                # la tabla se lleva ~68% dejando al panel de abajo lo
                # justo para el combo y AGREGAR A LA RUTINA (>= 82px)
                panes.sashpos(0, min(int(alto * reparto["ratio"]), alto - 82))

        def separador_tocado(evento):
            if "sash" in str(panes.identify(evento.x, evento.y)):
                reparto["tocado"] = True

        panes.bind("<Configure>", reparto_inicial)
        panes.bind("<ButtonPress-1>", separador_tocado)

        self.marco_rutina_pac = marco_rutina_pac

        self._poblar_combo_ejercicios()

    def _poblar_combo_ejercicios(self):
        opciones = [
            f"{ej.get('num','')}. {ej.get('nombre','')} ({ej.get('equipo') or '-'})"
            for ej in self.ejercicios
        ]
        self.combo_ej.configure(values=opciones)
        self.lbl_catalogo.configure(
            text=f"{len(self.ejercicios)} ejercicios · {database.DB_PATH.name}"
        )
        if self.ejercicios:
            self.combo_ej.current(0)
            self._al_seleccionar_combo()
        else:
            self.ejercicio_seleccionado = None
            self.combo_ej.set("")
            self.lbl_preview_titulo.configure(
                text=f"Sin ejercicios cargados para {self.grupo}"
            )
            self._mostrar_descripcion({})
            self.lbl_preview_img.configure(image="", text="")
            self.lbl_preview_fuente.configure(text="")


    def _subpestana_actual(self):
        try:
            return self.notebook_rut.index("current")
        except Exception:
            return 1

    def _al_cambiar_subpestana(self, event=None):
        """En Estiramientos y Progresión el título y el filtro cambian;
        al entrar a Ciclos se refrescan las semanas base disponibles y al
        cambiar de sub-pestaña se restablece la barra de estado para que
        no queden mensajes viejos pegados."""
        sub = self._subpestana_actual()
        self.lbl_estado.configure(
            text=getattr(self, "_estado_base", "") or "Rutinas")
        if sub == 2:
            self.titulo.configure(text="ESTIRAMIENTOS")
            self._cargar_est_paciente()
        elif sub == 3:
            self.titulo.configure(text="PROGRESIÓN · MODELO ACSM 2009")
        elif sub == 4:
            self.titulo.configure(text="RUTINAS · CICLOS")
            self._cic_refrescar_bases()
        else:
            self.titulo.configure(text="RUTINAS")

    def _al_seleccionar_combo(self, event=None):
        idx = self.combo_ej.current()
        if idx < 0 or idx >= len(self.ejercicios):
            return
        ej = self.ejercicios[idx]
        self.ejercicio_seleccionado = ej
        self._mostrar_ejercicio(ej)

    def _al_seleccionar_fila_rutina(self, _event=None):
        """Clic en una fila de la rutina del paciente: lleva el ejercicio
        al selector y la previsualización muestra su título,
        descripción e imagen; el combo Sesión del día se sincroniza
        con el día de la fila."""
        self._actualizar_sesion_dia()
        seleccion = self.tree_rutina.selection()
        if not seleccion or not seleccion[0].isdigit():
            return
        fila = next(
            (r for r in getattr(self, "rutina", [])
             if str(r["id_rutina"]) == seleccion[0]),
            None,
        )
        if not fila:
            return
        num = str(fila.get("num") or "")
        indice = self._indice_ejercicio_combo(fila, num)
        if indice is not None:
            self.combo_ej.current(indice)
            self._al_seleccionar_combo()
        else:
            # el catalogo cambio y ya no esta: muestra al menos el nombre
            self.lbl_preview_titulo.configure(
                text=f"{fila.get('nombre','')}  |  Equipo: "
                f"{fila.get('equipo') or '-'}"
            )

    def _indice_ejercicio_combo(self, fila, num):
        """Índice del ejercicio de la fila en el combo completo (por
        grupo y número; si el catálogo se renumeró, por nombre)."""
        grupo = (fila.get("grupo") or "").strip()
        for indice, ej in enumerate(self.ejercicios):
            if (
                num
                and str(ej.get("num") or "") == num
                and (not grupo or (ej.get("grupo") or "").strip() == grupo)
            ):
                return indice
        for indice, ej in enumerate(self.ejercicios):
            if fila.get("nombre") and ej.get("nombre") == fila.get("nombre"):
                return indice
        return None

    def _dia_destino_rutina(self):
        """Día de la rutina que recibirá el ejercicio añadido: el nodo
        elegido en el árbol (día/sesión o ejercicio) o, si no hay ninguno,
        el día activo."""
        seleccion = self.tree_rutina.selection()
        if seleccion:
            iid = seleccion[0]
            if iid.startswith("dia:"):
                return iid.split(":", 1)[1]
            if iid.isdigit():
                fila = next(
                    (r for r in getattr(self, "rutina", [])
                     if str(r["id_rutina"]) == iid),
                    None,
                )
                if fila:
                    return fila.get("dia") or DIAS_SEMANA[0]
        return getattr(self, "dia_actual", DIAS_SEMANA[0])

    def _agregar_ejercicio_seleccionado(self):
        """Añade el ejercicio del combo a la rutina seleccionada en el
        árbol (su día/sesión conserva la nota) o al día activo; la
        prescripción arranca 3×12 y se ajusta editando la fila. Si el día
        estaba de descanso, pregunta antes de quitar la marca."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas", "Selecciona un paciente antes de añadir ejercicios."
            )
            return
        ej = getattr(self, "ejercicio_seleccionado", None)
        if not ej:
            messagebox.showwarning(
                "Rutinas", "Selecciona un ejercicio de la lista."
            )
            return
        dia = self._dia_destino_rutina()
        filas_dia = [
            r for r in getattr(self, "rutina", [])
            if (r.get("dia") or "Lunes") == dia
        ]
        notas = next((r.get("notas") for r in filas_dia if r.get("notas")), "")
        if any(r.get("descanso") for r in filas_dia) and not messagebox.askyesno(
            "Rutinas",
            f"{dia} está marcado como día de descanso.\n"
            "¿Quitar el descanso y añadir el ejercicio?",
        ):
            return
        if any(r.get("descanso") for r in filas_dia):
            try:
                database.quitar_descanso(paciente_id, dia)
            except Exception as error:
                messagebox.showerror(
                    "Rutinas", f"No se pudo quitar el descanso:\n{error}"
                )
                return
        try:
            database.insert_rutina_paciente(
                {
                    "paciente_id": paciente_id,
                    "dia": dia,
                    "grupo": ej.get("grupo") or self.grupo,
                    "num": ej.get("num"),
                    "nombre": ej.get("nombre"),
                    "equipo": ej.get("equipo"),
                    "series": "3",
                    "repeticiones": "12",
                    "notas": notas,
                }
            )
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo añadir el ejercicio:\n{error}"
            )
            return
        self.dia_actual = dia
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje(f"Añadido a {dia}: {ej.get('nombre')}")

    # ------------------------------------------------------------------
    # Sesión del día: cambiar los ejercicios del día seleccionado en el
    # árbol por los de una rutina guardada, de otra sesión de la semana,
    # o marcarlo como descanso.
    # ------------------------------------------------------------------

    def _sesiones_disponibles(self):
        """Sesiones que se pueden asignar a un día: las de la semana del
        paciente y las rutinas guardadas con nombre (prefijo estrella)."""
        sesiones_semana = sorted({
            (r.get("notas") or "").strip()
            for r in getattr(self, "rutina", [])
            if r.get("notas") and not r.get("descanso")
        })
        try:
            guardadas = database.get_rutinas_guardadas(semanal=0)
        except Exception:
            guardadas = []
        return sesiones_semana, ["★ " + g["nombre"] for g in guardadas]

    def _sesion_del_dia(self, dia):
        """Sesión actual del día (su nota) o None si está de descanso;
        cadena vacía si el día está vacío."""
        filas = [
            r for r in getattr(self, "rutina", [])
            if (r.get("dia") or "Lunes") == dia
        ]
        if any(r.get("descanso") for r in filas):
            return None
        return next(
            ((r.get("notas") or "").strip() for r in filas if r.get("notas")),
            "",
        )

    def _actualizar_sesion_dia(self):
        """Llena el combo Sesión del día según la selección del árbol y
        deja marcada la sesión actual del día."""
        if not hasattr(self, "combo_sesion_dia"):
            return
        dia = self._dia_destino_rutina()
        sesiones_semana, rutinas_guardadas = self._sesiones_disponibles()
        self.combo_sesion_dia.configure(
            values=sesiones_semana + rutinas_guardadas + ["Día de descanso"]
        )
        actual = self._sesion_del_dia(dia)
        if actual is None:
            self.combo_sesion_dia.set("Día de descanso")
        elif actual and actual in sesiones_semana + rutinas_guardadas:
            self.combo_sesion_dia.set(actual)
        else:
            self.combo_sesion_dia.set("")

    def _al_elegir_sesion_dia(self, _event=None):
        """Cambio en el combo Sesión del día: reemplaza los ejercicios
        del día seleccionado en el árbol por los de la rutina o sesión
        elegida, o lo marca como descanso; pide confirmación si el día
        tenía ejercicios."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas", "Selecciona un paciente antes de cambiar sesiones."
            )
            return
        dia = self._dia_destino_rutina()
        eleccion = self.combo_sesion_dia.get()
        if not eleccion:
            return
        filas_dia = [
            r for r in getattr(self, "rutina", [])
            if (r.get("dia") or "Lunes") == dia
        ]
        con_ejercicios = [r for r in filas_dia if not r.get("descanso")]
        actual = self._sesion_del_dia(dia)
        if (actual or "") == eleccion or (
            actual is None and eleccion == "Día de descanso"
        ):
            return
        if eleccion == "Día de descanso":
            if con_ejercicios and not messagebox.askyesno(
                "Rutinas",
                f"{dia} tiene {len(con_ejercicios)} ejercicio(s).\n"
                "¿Borrarlos y marcar el día como descanso?",
            ):
                return
            database.marcar_descanso(paciente_id, dia)
            self.dia_actual = dia
            self._cargar_rutina()
            self._marcar_rutina_guardada()
            self._mensaje(f"{dia}: día de descanso.")
            return
        if eleccion.startswith("★ "):
            guardada = database.get_rutina_guardada(
                next(
                    g["id_rutina_guardada"]
                    for g in database.get_rutinas_guardadas(semanal=0)
                    if "★ " + g["nombre"] == eleccion
                )
            )
            fichas = [
                dict(e) for e in guardada["ejercicios"]
                if not e.get("descanso")
            ]
            notas = guardada["nombre"]
        else:
            fichas = [
                dict(r) for r in getattr(self, "rutina", [])
                if (r.get("notas") or "").strip() == eleccion
                and not r.get("descanso")
            ]
            notas = eleccion
        if not fichas:
            messagebox.showinfo(
                "Rutinas", "La sesión elegida no tiene ejercicios."
            )
            return
        if con_ejercicios and not messagebox.askyesno(
            "Rutinas",
            f"{dia} tiene {len(con_ejercicios)} ejercicio(s) de "
            f"«{actual or 'otra sesión'}».\n"
            f"¿Reemplazarlos por «{notas}»?",
        ):
            return
        try:
            database.delete_rutina_dia(paciente_id, dia)
            for ficha in fichas:
                database.insert_rutina_paciente(
                    {
                        "paciente_id": paciente_id,
                        "dia": dia,
                        "grupo": ficha.get("grupo"),
                        "num": ficha.get("num"),
                        "nombre": ficha.get("nombre"),
                        "equipo": ficha.get("equipo"),
                        "series": ficha.get("series"),
                        "repeticiones": ficha.get("repeticiones"),
                        "descanso_rep": ficha.get("descanso_rep"),
                        "descanso_series": ficha.get("descanso_series"),
                        "peso": ficha.get("peso"),
                        "notas": notas,
                    }
                )
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo cambiar la sesión:\n{error}"
            )
            return
        self.dia_actual = dia
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje(f"{dia}: sesión cambiada a «{notas}».")

    def _mostrar_ejercicio(self, ej):
        self.lbl_preview_titulo.configure(
            text=f"{ej.get('num','')}. {ej.get('nombre','')}  |  Equipo: {ej.get('equipo') or '-'}"
        )
        self._mostrar_descripcion(ej)
        self._cargar_imagen(ej)

    def _mostrar_descripcion(self, ej):
        texto = (ej.get("descripcion") or "").strip()
        if not texto:
            texto = "Este ejercicio no tiene descripción guardada en la base de datos."
        self.txt_preview_desc.configure(state="normal")
        self.txt_preview_desc.delete("1.0", "end")
        self.txt_preview_desc.insert("1.0", texto)
        self.txt_preview_desc.configure(state="disabled")

    def _cargar_imagen(self, ej):
        """Usa el blob guardado en la BD y, si faltara, el archivo del disco."""
        self._img_origen = None
        self.imagen_actual = None
        self._img_fuente = ""
        self.lbl_preview_img.configure(image="", text="")
        self.lbl_preview_fuente.configure(text="")

        if Image is None:
            self.lbl_preview_img.configure(
                text="Pillow no está instalado: no se pueden mostrar las imágenes JPEG."
            )
            return

        blob = ej.get("imagen_blob")
        if blob:
            try:
                with Image.open(io.BytesIO(blob)) as imagen:
                    self._img_origen = imagen.convert("RGB")
                self._img_fuente = f"BD · imagen_blob ({len(blob) / 1024:.0f} KB)"
            except Exception:
                self._img_origen = None

        if self._img_origen is None:
            nombre = ej.get("imagen_nombre") or ej.get("imagen") or ""
            ruta = os.path.join(
                RUTA_IMAGENES, ej.get("grupo") or self.grupo, nombre
            ) if nombre else ""
            if ruta and os.path.exists(ruta):
                try:
                    with Image.open(ruta) as imagen:
                        self._img_origen = imagen.convert("RGB")
                    self._img_fuente = f"archivo · {nombre}"
                except Exception:
                    self._img_origen = None

        if self._img_origen is None:
            self.lbl_preview_img.configure(text="Sin imagen asociada a este ejercicio")
            return

        ancho, alto = self._img_origen.size
        self.lbl_preview_fuente.configure(
            text=f"Imagen desde {self._img_fuente} · original {ancho}x{alto} px"
        )
        self._render_imagen()

    def _al_redimensionar(self, event):
        if event.width < 40 or event.height < 40:
            return
        self._tam_panel = (event.width, event.height)
        self.lbl_preview_titulo.configure(wraplength=max(event.width - 20, 200))
        if self._img_after is not None:
            try:
                self.lbl_preview_img.after_cancel(self._img_after)
            except Exception:
                pass
        self._img_after = self.lbl_preview_img.after(140, self._render_imagen)

    def _render_imagen(self):
        self._img_after = None
        if self._img_origen is None:
            return
        if not self.lbl_preview_img.winfo_exists():
            return
        if ImageTk is None:
            self.lbl_preview_img.configure(
                image="", text="Pillow no está instalado: no se pueden mostrar las imágenes JPEG."
            )
            return
        ancho, alto = self._tam_panel
        ancho = max(int(ancho) - 12, 120)
        alto = max(int(alto) - 12, 120)
        copia = self._img_origen.copy()
        copia.thumbnail((ancho, alto), Image.LANCZOS)
        self.imagen_actual = ImageTk.PhotoImage(copia)
        self.lbl_preview_img.configure(image=self.imagen_actual, text="")

    def _crear_tab_estiramiento(self):
        marco = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        self.notebook_rut.add(marco, text="  Estiramiento  ")

        contenedor = ttk.Frame(marco, style="Gym.TFrame")
        contenedor.pack(fill="both", expand=True, padx=10, pady=(2, 6))

        # --- Filtros ---
        filtros = ttk.Frame(contenedor, style="Gym.TFrame")
        tk.Label(
            filtros, text="Grupo:", font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO
        ).pack(side="left")
        self.est_grupo_var = tk.StringVar(value="Todos")
        self.est_grupo_combo = ttk.Combobox(
            filtros, textvariable=self.est_grupo_var, state="readonly", width=14,
            style="Gym.TCombobox",
        )
        self.est_grupo_combo.pack(side="left", padx=(6, 12))
        self.est_grupo_combo.bind("<<ComboboxSelected>>", self._al_cambiar_grupo_est)

        tk.Label(
            filtros, text="Estiramiento:", font=("Segoe UI", 8), fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(side="left")
        self.est_combo = ttk.Combobox(filtros, state="readonly", style="Gym.TCombobox")
        self.est_combo.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.est_combo.bind("<<ComboboxSelected>>", self._al_seleccionar_est)

        # --- Vista previa ---
        superior = ttk.Frame(contenedor, style="Gym.TFrame")

        panel_desc = ttk.LabelFrame(superior, text="Cómo realizarlo", padding=4)
        panel_desc.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.est_txt = tk.Text(
            panel_desc, width=40, height=8, wrap="word", bg=GRIS_OSCURO, fg=BLANCO,
            relief="flat", padx=6, pady=4, font=("Segoe UI", 9), highlightthickness=0,
        )
        self.est_txt.configure(state="disabled")
        barra_desc = ttk.Scrollbar(panel_desc, orient="vertical", command=self.est_txt.yview)
        self.est_txt.configure(yscrollcommand=barra_desc.set)
        self.est_txt.pack(side="left", fill="both", expand=True)
        barra_desc.pack(side="right", fill="y")

        panel_img = ttk.LabelFrame(superior, text="Ilustración", padding=4)
        panel_img.pack(side="right", fill="both", expand=True)
        self.est_lbl_img = tk.Label(
            panel_img, bg=GRIS_OSCURO, fg=GRIS_TEXTO, font=("Segoe UI", 9), text=""
        )
        self.est_lbl_img.pack(expand=True, fill="both")
        self.est_lbl_fuente = ttk.Label(panel_img, text="", style="Estado.TLabel")
        self.est_lbl_fuente.pack(anchor="w")

        # --- Selección del paciente ---
        marco_pac = ttk.LabelFrame(
            contenedor, text="Estiramientos del paciente", padding=6
        )
        cols = ("nombre", "grupo", "momento", "duracion")
        self.est_tree = ttk.Treeview(
            marco_pac, columns=cols, show="headings", height=3,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("nombre", "Estiramiento", 300, "w"),
            ("grupo", "Grupo", 100, "w"),
            ("momento", "Momento", 190, "w"),
            ("duracion", "Duración", 90, "center"),
        ):
            self.est_tree.heading(col, text=texto, anchor=alineacion)
            self.est_tree.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion,
                stretch=(col == "nombre"),
            )
        barra_pac = ttk.Scrollbar(marco_pac, orient="vertical", command=self.est_tree.yview)
        self.est_tree.configure(yscrollcommand=barra_pac.set)
        self.est_tree.pack(side="left", fill="both", expand=True)
        barra_pac.pack(side="left", fill="y")

        acciones = ttk.Frame(marco_pac, style="Gym.TFrame")
        acciones.pack(side="left", fill="y", padx=(8, 0))
        tk.Button(
            acciones, text="Quitar seleccionado", command=self._quitar_est,
            font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO, relief="flat",
            padx=8, pady=2, cursor="hand2",
        ).pack(fill="x", pady=(0, 4))
        tk.Button(
            acciones, text="Vaciar selección", command=self._vaciar_est,
            font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO, relief="flat",
            padx=8, pady=2, cursor="hand2",
        ).pack(fill="x")
        tk.Button(
            acciones,
            text="IMPRIMIR ESTIRAMIENTOS",
            command=self._imprimir_est,
            font=("Impact", 9),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
        ).pack(fill="x", pady=(6, 0))
        self.est_lbl_total = ttk.Label(acciones, text="0 estiramientos", style="Estado.TLabel")
        self.est_lbl_total.pack(anchor="w", pady=(8, 0))

        # --- Alta ---
        marco_alta = ttk.LabelFrame(
            contenedor, text="Añadir a la selección del paciente", padding=6
        )
        tk.Label(
            marco_alta, text="Momento:", font=("Segoe UI", 8), fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(side="left")
        self.est_momento_var = tk.StringVar(value=MOMENTOS[0])
        ttk.Combobox(
            marco_alta, textvariable=self.est_momento_var, values=MOMENTOS,
            state="readonly", width=26, style="Gym.TCombobox",
        ).pack(side="left", padx=(6, 12))
        tk.Label(
            marco_alta, text="Duración:", font=("Segoe UI", 8), fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(side="left")
        self.est_duracion_var = tk.StringVar(value=DURACIONES[3])
        ttk.Combobox(
            marco_alta, textvariable=self.est_duracion_var, values=DURACIONES,
            state="readonly", width=12, style="Gym.TCombobox",
        ).pack(side="left", padx=(6, 12))
        tk.Button(
            marco_alta, text="+ AÑADIR ESTIRAMIENTO", command=self._anadir_est,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=3, cursor="hand2",
        ).pack(side="left")

        filtros.pack(fill="x", pady=(0, 6))
        marco_pac.pack(side="bottom", fill="both", pady=(6, 0))
        marco_alta.pack(side="bottom", fill="x", pady=(6, 0))
        superior.pack(fill="both", expand=True)

        self._cargar_grupos_est()

    # ------------------------------------------------------------------
    # Estiramientos: catálogo y selección del paciente
    # ------------------------------------------------------------------
    def _cargar_grupos_est(self):
        try:
            grupos = database.get_estiramientos_grupos()
        except Exception:
            grupos = []
        self.est_grupo_combo["values"] = ["Todos"] + grupos
        self.est_grupo_combo.current(0)
        self._cargar_catalogo_est()

    def _al_cambiar_grupo_est(self, event=None):
        self._cargar_catalogo_est()

    def _cargar_catalogo_est(self):
        grupo = self.est_grupo_var.get()
        try:
            self.est_catalogo = database.get_estiramientos(
                None if grupo.lower().startswith("todos") else grupo
            )
        except Exception:
            self.est_catalogo = []
        opciones = []
        for est in self.est_catalogo:
            numero = est.get("numero")
            prefijo = f"{int(numero):02d}. " if isinstance(numero, int) else ""
            opciones.append(prefijo + (est.get("nombre") or ""))
        self.est_combo["values"] = opciones
        if opciones:
            self.est_combo.current(0)
            self._al_seleccionar_est()
        else:
            self.est_combo.set("")
            self.est_actual = None
            self._mostrar_est({})

    def _al_seleccionar_est(self, event=None):
        idx = self.est_combo.current()
        if idx < 0 or idx >= len(self.est_catalogo):
            return
        self.est_actual = self.est_catalogo[idx]
        self._mostrar_est(self.est_actual)

    def _mostrar_est(self, est):
        partes = []
        for titulo, clave in (
            ("CÓMO REALIZARLO", "descripcion"),
            ("MÚSCULOS ESTIRADOS", "musculos"),
            ("VARIANTES", "variantes"),
            ("OBSERVACIONES", "observaciones"),
            ("ATENCIÓN", "atencion"),
        ):
            valor = (est.get(clave) or "").strip()
            if valor:
                partes.append(f"{titulo}\n{valor}")
        texto = "\n\n".join(partes) or "Selecciona un estiramiento del catálogo."
        self.est_txt.configure(state="normal")
        self.est_txt.delete("1.0", "end")
        self.est_txt.insert("1.0", texto)
        self.est_txt.configure(state="disabled")
        self._cargar_imagen_est(est)

    def _cargar_imagen_est(self, est):
        self.est_lbl_img.configure(image="", text="")
        self.est_lbl_fuente.configure(text="")
        self._est_foto = None
        if Image is None:
            self.est_lbl_img.configure(text="Pillow no está instalado")
            return

        origen = None
        fuente = ""
        blob = est.get("imagen_blob")
        if blob:
            try:
                with Image.open(io.BytesIO(blob)) as imagen:
                    origen = imagen.convert("RGB")
                fuente = f"BD · imagen_blob ({len(blob) / 1024:.0f} KB)"
            except Exception:
                origen = None
        if origen is None:
            nombre = est.get("imagen") or ""
            if nombre:
                for ext in (".png", ".jpg", ".jpeg"):
                    ruta = os.path.join(
                        base_dir(),
                        "estiramientos_img", nombre + ext,
                    )
                    if os.path.exists(ruta):
                        try:
                            with Image.open(ruta) as imagen:
                                origen = imagen.convert("RGB")
                            fuente = f"archivo · {nombre}{ext}"
                        except Exception:
                            origen = None
                        break
        if origen is None:
            self.est_lbl_img.configure(text="Sin ilustración guardada")
            return

        copia = origen.copy()
        copia.thumbnail((460, 320), Image.LANCZOS)
        self._est_foto = ImageTk.PhotoImage(copia)
        self.est_lbl_img.configure(image=self._est_foto, text="")
        ancho, alto = origen.size
        self.est_lbl_fuente.configure(
            text=f"Imagen desde {fuente} · original {ancho}x{alto} px"
        )

    def _anadir_est(self):
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un paciente antes de añadir."
            )
            return
        est = self.est_actual
        if not est:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un estiramiento del catálogo."
            )
            return
        try:
            database.insert_estiramiento_paciente(
                {
                    "paciente_id": paciente_id,
                    "id_estiramiento": est.get("id_estiramiento"),
                    "grupo": est.get("grupo"),
                    "nombre": est.get("nombre"),
                    "momento": self.est_momento_var.get(),
                    "duracion": self.est_duracion_var.get(),
                    "notas": "",
                }
            )
        except Exception as error:
            messagebox.showerror(
                "Estiramientos", f"No se pudo añadir el estiramiento:\n{error}"
            )
            return
        self._cargar_est_paciente()
        self._mensaje(f"Añadido: {est.get('nombre')}")

    def _quitar_est(self):
        seleccion = self.est_tree.selection()
        if not seleccion:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un estiramiento de la lista."
            )
            return
        try:
            database.delete_estiramiento_paciente(int(seleccion[0]))
        except Exception as error:
            messagebox.showerror(
                "Estiramientos", f"No se pudo quitar:\n{error}"
            )
            return
        self._cargar_est_paciente()
        self._mensaje("Estiramiento quitado de la selección.")

    def _vaciar_est(self):
        paciente_id = self._paciente_actual()
        if paciente_id is None or not getattr(self, "est_seleccion", []):
            return
        if not messagebox.askyesno(
            "Estiramientos", "¿Vaciar todos los estiramientos de este paciente?"
        ):
            return
        try:
            database.delete_estiramientos_paciente(paciente_id)
        except Exception as error:
            messagebox.showerror("Estiramientos", f"No se pudo vaciar:\n{error}")
            return
        self._cargar_est_paciente()
        self._mensaje("Selección de estiramientos vaciada.")

    def _cargar_est_paciente(self):
        if not hasattr(self, "est_tree"):
            return
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            self.est_seleccion = []
        else:
            try:
                self.est_seleccion = database.get_estiramientos_paciente(paciente_id)
            except Exception:
                self.est_seleccion = []
        self._render_est_paciente()

    def _render_est_paciente(self):
        for item in self.est_tree.get_children():
            self.est_tree.delete(item)
        for registro in getattr(self, "est_seleccion", []):
            self.est_tree.insert(
                "",
                "end",
                iid=str(registro.get("id_seleccion")),
                values=(
                    registro.get("nombre") or "-",
                    registro.get("grupo") or "-",
                    registro.get("momento") or "-",
                    registro.get("duracion") or "-",
                ),
            )
        total = len(getattr(self, "est_seleccion", []))
        self.est_lbl_total.configure(
            text=f"{total} estiramiento" + ("" if total == 1 else "s")
        )

    def _imprimir_est(self):
        """Genera el PDF de los estiramientos seleccionados (resumen +
        detalle con ilustración y descripción) y lo abre para impresión."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un paciente antes de imprimir."
            )
            return
        seleccion = getattr(self, "est_seleccion", None)
        if not seleccion:
            messagebox.showwarning(
                "Estiramientos",
                "No hay estiramientos seleccionados para imprimir.",
            )
            return

        # la selección ya trae el catálogo unido (descripcion, imagen,
        # imagen_blob); se indexa por id para el detalle del reporte
        catalogo = {}
        for reg in seleccion:
            catalogo[reg.get("id_estiramiento")] = reg

        paciente = database.obtener_paciente(paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{paciente_id}"
        ruta = estiramientos_print.ruta_temporal_pdf(nombre)
        try:
            estiramientos_print.generar_pdf_estiramientos(
                ruta, paciente, seleccion, estiramientos_por_id=catalogo
            )
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            estiramientos_print.abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showerror(
                "Imprimir",
                f"Se generó el PDF en:\n{ruta}\n\n"
                f"No se pudo abrir automáticamente: {error}",
            )
            return

        self._mensaje("Estiramientos: reporte generado.")

    # ------------------------------------------------------------------
    # Rutina del paciente (alta, listado y borrado)
    # ------------------------------------------------------------------
    def _mensaje(self, texto):
        """Muestra una confirmación breve en la barra de estado."""
        base = getattr(self, "_estado_base", "") or "Rutinas"
        self.lbl_estado.configure(text=f"{base}  ·  {texto}")

    def _paciente_actual(self):
        if self.paciente_id is not None:
            return self.paciente_id
        return getattr(self.app, "id_paciente_antro", None)

    def _quitar_ejercicio(self):
        seleccion = self.tree_rutina.selection()
        if not seleccion:
            messagebox.showwarning(
                "Rutinas", "Selecciona un ejercicio de la rutina del paciente."
            )
            return
        iid = seleccion[0]
        if iid.startswith("dia:"):
            # el nodo de un día de descanso también se quita aquí
            dia = iid.split(":", 1)[1]
            paciente_id = self._paciente_actual()
            filas = [
                r for r in getattr(self, "rutina", [])
                if (r.get("dia") or "Lunes") == dia
            ]
            if not any(r.get("descanso") for r in filas):
                messagebox.showinfo(
                    "Rutinas",
                    f"«{dia}» no está de descanso: selecciona un ejercicio "
                    "concreto para quitarlo.",
                )
                return
            try:
                database.quitar_descanso(paciente_id, dia)
            except Exception as error:
                messagebox.showerror(
                    "Rutinas", f"No se pudo quitar el descanso:\n{error}"
                )
                return
            self.dia_actual = dia
            self._cargar_rutina()
            self._marcar_rutina_guardada()
            self._mensaje(f"{dia}: día de descanso quitado.")
            return
        if not iid.isdigit():
            # nodo raíz de la semana: no se quita
            return
        try:
            database.delete_rutina_paciente(int(iid))
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo quitar el ejercicio:\n{error}"
            )
            return
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje("Ejercicio quitado de la rutina.")

    def _menu_rutina_contextual(self, event):
        """Clic derecho sobre la rutina (misma lógica que Menús):
        selecciona la fila y ofrece editarla o quitarla; solo los
        ejercicios tienen menú (días y raíz de la semana no se editan).
        El editar también queda al alcance del doble clic."""
        fila = self.tree_rutina.identify_row(event.y)
        if not fila or not fila.isdigit():
            return "break"
        self.tree_rutina.selection_set(fila)
        self.tree_rutina.focus(fila)
        try:
            self.menu_rutina_ctx.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_rutina_ctx.grab_release()
        return "break"

    def _refrescar_historial_pac(self):
        """Tabla del historial en la sub-pestaña Rutina: las rutinas
        semanales guardadas del paciente con su fecha, la más reciente
        primero; doble clic restaura esa copia como su rutina actual."""
        if not hasattr(self, "tree_historial_pac"):
            return
        for iid in self.tree_historial_pac.get_children():
            self.tree_historial_pac.delete(iid)
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            self.tree_historial_pac.insert(
                "", "end", iid="sin",
                values=("Sin paciente seleccionado", "—", "—", "—"),
            )
            return
        try:
            entradas = database.get_rutinas_historial(paciente_id)
        except Exception:
            entradas = []
        if not entradas:
            self.tree_historial_pac.insert(
                "", "end", iid="sin",
                values=(
                    "Aún no hay rutinas guardadas para este paciente",
                    "—", "—", "—",
                ),
            )
            return
        for e in entradas:
            self.tree_historial_pac.insert(
                "", "end", iid=str(e["id_historial"]),
                values=(
                    e["nombre_semana"], e["fecha"],
                    e["ejercicios"], e["dias"],
                ),
            )

    def _aplicar_historial_pac(self):
        """Doble clic en el historial de la sub-pestaña Rutina: restaura
        esa copia fechada como la rutina actual del paciente (pide
        confirmación porque reemplaza su semana; la copia queda en el
        historial y puede recuperarse otra vez)."""
        sel = self.tree_historial_pac.selection()
        if not sel or not sel[0].isdigit():
            self._mensaje(
                "Elige una rutina guardada del paciente en el historial."
            )
            return
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas",
                "Selecciona un paciente antes de recuperar una rutina.",
            )
            return
        try:
            entrada = database.get_rutina_historial(int(sel[0]))
        except Exception:
            entrada = None
        if not entrada:
            self._mensaje("No se pudo leer la rutina guardada del paciente.")
            return
        dias = entrada.get("dias") or []
        total = sum(len(d.get("ejercicios") or []) for d in dias)
        paciente = database.obtener_paciente(paciente_id) or {}
        nombre_paciente = paciente.get("nombre") or f"paciente {paciente_id}"
        if not messagebox.askyesno(
            "Rutinas",
            f"¿Recuperar «{entrada.get('nombre_semana')}» "
            f"({total} ejercicios, guardada el "
            f"{entrada.get('fecha') or '—'}) como la rutina actual de "
            f"{nombre_paciente}? Reemplaza su rutina actual.",
        ):
            return
        try:
            database.delete_rutinas_paciente(paciente_id)
            for d in dias:
                dia = d.get("dia") or "Lunes"
                sesion = (d.get("sesion") or "").strip()
                ejercicios = d.get("ejercicios") or []
                if not sesion or not ejercicios:
                    database.marcar_descanso(paciente_id, dia)
                    continue
                for ej in ejercicios:
                    database.insert_rutina_paciente(
                        {
                            "paciente_id": paciente_id,
                            "dia": dia,
                            "grupo": ej.get("grupo"),
                            "num": ej.get("num"),
                            "nombre": ej.get("nombre"),
                            "equipo": ej.get("equipo"),
                            "series": ej.get("series") or "",
                            "repeticiones": ej.get("repeticiones") or "",
                            "descanso_rep": ej.get("descanso_rep") or "",
                            "descanso_series": ej.get("descanso_series") or "",
                            "peso": ej.get("peso") or "",
                            "notas": sesion,
                        }
                    )
            database.marcar_semana_aplicada(
                paciente_id, entrada.get("nombre_semana") or ""
            )
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo recuperar la rutina:\n{error}"
            )
            return
        # deja activo el primer día entrenable de la copia recuperada
        self.dia_actual = next(
            (
                d.get("dia") or "Lunes"
                for d in dias
                if d.get("sesion") and d.get("ejercicios")
            ),
            DIAS_SEMANA[0],
        )
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje(
            f"Rutina recuperada del historial: "
            f"«{entrada.get('nombre_semana')}» "
            f"({entrada.get('fecha') or '—'})."
        )

    def _renombrar_semana_paciente(self):
        """Doble clic sobre el nombre de la semana (nodo raíz del árbol
        de la rutina del paciente): pide el nombre nuevo y lo guarda como
        nombre_semana del paciente activo; la biblioteca y las plantillas
        no se tocan."""
        if not getattr(self, "rutina", []):
            messagebox.showinfo(
                "Rutinas",
                "La rutina está vacía: añade ejercicios antes de "
                "renombrar la semana.",
            )
            return
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas",
                "Selecciona un paciente antes de renombrar la semana.",
            )
            return
        actual = next(
            (
                r.get("nombre_semana")
                for r in self.rutina
                if r.get("nombre_semana")
            ),
            "Semana del paciente",
        )
        nuevo = simpledialog.askstring(
            "Rutinas",
            "Nombre de la semana:",
            initialvalue=actual,
            parent=self.marco.winfo_toplevel(),
        )
        nuevo = (nuevo or "").strip()
        if not nuevo or nuevo == actual:
            return
        try:
            database.marcar_semana_aplicada(paciente_id, nuevo)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo renombrar la semana:\n{error}"
            )
            return
        # recarga las filas desde la BD: la raíz del árbol y el marco
        # muestran el nombre nuevo
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje(f"Semana renombrada: «{nuevo}».")

    def _editar_ejercicio_rutina(self, _event=None):
        """Cuadro para editar la prescripción de un ejercicio de la rutina
        (doble clic o clic derecho > Editar, como el edit de equivalentes
        en Menús). Al guardar, el cambio queda solo en la rutina del
        paciente activo: la plantilla semanal y las rutinas de los demás
        pacientes no se tocan. Doble clic sobre la raíz de la semana
        renombra la semana del paciente."""
        seleccion = self.tree_rutina.selection()
        if seleccion and seleccion[0] == "semana":
            self._renombrar_semana_paciente()
            return
        if not seleccion or not seleccion[0].isdigit():
            return
        paciente_id = self._paciente_actual()
        id_rutina = int(seleccion[0])
        registro = next(
            (
                r for r in getattr(self, "rutina", [])
                if r.get("id_rutina") == id_rutina
            ),
            None,
        )
        if registro is None or paciente_id is None:
            return

        dialogo = tk.Toplevel(self.marco)
        dialogo.title("Editar ejercicio")
        dialogo.configure(bg=GRIS_OSCURO)
        dialogo.transient(self.marco)
        dialogo.grab_set()

        tk.Label(
            dialogo,
            text=(registro.get("nombre") or "").upper(),
            font=("Impact", 12),
            fg=NEON,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12, pady=(10, 0))
        tk.Label(
            dialogo,
            text=f"{getattr(self, 'dia_actual', '')} · {registro.get('equipo') or '-'}",
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        campos = (
            ("Series", "series"),
            ("Repeticiones", "repeticiones"),
            ("Descanso entre ejercicios (seg)", "descanso_rep"),
            ("Descanso entre series (seg)", "descanso_series"),
            ("Peso (kg)", "peso"),
        )
        entradas = {}
        for texto, clave in campos:
            f = tk.Frame(dialogo, bg=GRIS_OSCURO)
            f.pack(fill="x", padx=12, pady=2)
            tk.Label(
                f, text=texto, font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO
            ).pack(anchor="w")
            e = ttk.Entry(f, width=14, style="Gym.TEntry")
            e.pack(anchor="w")
            e.insert(0, registro.get(clave) or "")
            entradas[clave] = e

        def guardar():
            datos = {clave: entradas[clave].get().strip() for _, clave in campos}
            if not datos["series"] and not datos["repeticiones"]:
                messagebox.showwarning(
                    "Rutinas", "Indica al menos las series o las repeticiones."
                )
                return
            try:
                database.actualizar_rutina_paciente(id_rutina, paciente_id, datos)
            except Exception as error:
                messagebox.showerror(
                    "Rutinas", f"No se pudo guardar el cambio:\n{error}"
                )
                return
            self._cargar_rutina()
            self._marcar_rutina_guardada()
            self._mensaje(f"Actualizado: {registro.get('nombre')}")
            dialogo.destroy()

        botones = tk.Frame(dialogo, bg=GRIS_OSCURO)
        botones.pack(fill="x", padx=12, pady=(10, 12))
        tk.Button(
            botones,
            text="GUARDAR",
            command=guardar,
            font=("Impact", 10),
            fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=14, pady=4, cursor="hand2",
        ).pack(side="left")
        tk.Button(
            botones,
            text="CANCELAR",
            command=dialogo.destroy,
            font=("Impact", 10),
            fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=14, pady=4, cursor="hand2",
        ).pack(side="right")

        dialogo.wait_window()

    def _vaciar_rutina(self):
        paciente_id = self._paciente_actual()
        if paciente_id is None or not getattr(self, "rutina", []):
            return
        if not messagebox.askyesno(
            "Rutinas",
            "¿Vaciar toda la rutina de este paciente (todos los días de la semana)?",
        ):
            return
        try:
            database.delete_rutinas_paciente(paciente_id)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo vaciar la rutina:\n{error}"
            )
            return
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje("Rutina vaciada.")

    def _abrir_menu_imprimir(self):
        """Despliega las opciones de impresión debajo del botón."""
        boton = self.btn_imprimir_rutina
        self.menu_imprimir.tk_popup(
            boton.winfo_rootx(),
            boton.winfo_rooty() + boton.winfo_height(),
        )

    def _imprimir_rutina(self, modo="todo", guardar=False):
        """Genera el PDF de la rutina en el modo elegido ("tabla" = solo
        plan semanal y tablas por día; "descripcion" = solo el detalle
        con imagen y descripción; "todo" = ambos) y lo abre. Con
        guardar=True pide carpeta y nombre (el PDF se escribe ahí en
        lugar de la carpeta de reportes de Documentos)."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas", "Selecciona un paciente antes de imprimir."
            )
            return
        rutina = getattr(self, "rutina", None)
        if not rutina:
            messagebox.showwarning(
                "Rutinas", "No hay ejercicios en la rutina para imprimir."
            )
            return

        # el plan enriquece cada fila con la descripción y la ilustración
        # del catálogo para el detalle del reporte (las filas de descanso
        # no están en el catálogo)
        plan = []
        for fila in rutina:
            fila = dict(fila)
            if not fila.get("descanso"):
                try:
                    ficha = database.get_rutina_ejercicio(
                        fila.get("grupo"), fila.get("num")
                    )
                except Exception:
                    ficha = None
                if ficha:
                    for campo in ("descripcion", "imagen_blob", "imagen_nombre"):
                        fila[campo] = ficha.get(campo)
            plan.append(fila)

        paciente = database.obtener_paciente(paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{paciente_id}"
        if guardar:
            # el usuario elige carpeta y nombre; cancelar no genera nada
            ruta = rutina_print.pedir_guardar_pdf(
                "Rutina", nombre, parent=self.marco.winfo_toplevel()
            )
            if not ruta:
                return
        else:
            ruta = rutina_print.ruta_temporal_pdf(nombre)
        try:
            rutina_print.generar_pdf_rutina(ruta, paciente, plan, modo=modo)
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            rutina_print.abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showerror(
                "Imprimir",
                f"Se generó el PDF en:\n{ruta}\n\n"
                f"No se pudo abrir automáticamente: {error}",
            )
            return

        self._mensaje(
            f"PDF guardado: {ruta}" if guardar else "Rutina: reporte generado."
        )

    def _cargar_rutina(self):
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            self.rutina = []
        else:
            try:
                self.rutina = database.get_rutinas_paciente(paciente_id)
            except Exception:
                self.rutina = []
        self._render_rutina()

    def _marcar_rutina_guardada(self):
        """Enciende el letrero de guardado tras una escritura exitosa."""
        hora = datetime.now().strftime("%H:%M")
        self.lbl_rutina_guardada.configure(
            text=f"Guardada en la BD ✓ {hora}", foreground=NEON,
        )

    def _render_rutina(self):
        if not hasattr(self, "tree_rutina"):
            return
        for item in self.tree_rutina.get_children():
            self.tree_rutina.delete(item)
        semana = getattr(self, "rutina", [])
        dia_activo = getattr(self, "dia_actual", DIAS_SEMANA[0])
        self._resaltar_dia()
        filas_activas = [
            r for r in semana if (r.get("dia") or "Lunes") == dia_activo
        ]
        descanso_activo = any(r.get("descanso") for r in filas_activas)
        if hasattr(self, "btn_descanso"):
            self.btn_descanso.configure(
                text="✓ QUITAR DESCANSO" if descanso_activo else "MARCAR DÍA DE DESCANSO",
                bg=NARANJA if descanso_activo else GRIS,
                fg=NEGRO if descanso_activo else BLANCO,
            )
        # nivel raíz: la rutina semanal aplicada (guardada con las filas
        # en nombre_semana); sin nombre queda "Semana del paciente"
        nombre_semana = next(
            (r.get("nombre_semana") for r in semana if r.get("nombre_semana")),
            "",
        )
        if hasattr(self, "marco_rutina_pac"):
            self.marco_rutina_pac.configure(
                text="Rutina del paciente · "
                + (nombre_semana or "semana del paciente")
            )
        raiz = "semana"
        self.tree_rutina.insert(
            "", "end", iid=raiz, open=True,
            text=nombre_semana or "Semana del paciente",
            values=("", "", "", "", "", "", ""),
        )
        total_semana = 0
        for dia in DIAS_SEMANA:
            filas = [r for r in semana if (r.get("dia") or "Lunes") == dia]
            descanso = any(r.get("descanso") for r in filas)
            ejercicios = [r for r in filas if not r.get("descanso")]
            total_semana += len(ejercicios)
            sesion = next((r.get("notas") for r in filas if r.get("notas")), "")
            if descanso:
                texto_dia = f"{dia} · DESCANSO"
            else:
                texto_dia = (
                    f"{dia} · {len(ejercicios)} ejercicio"
                    + ("" if len(ejercicios) == 1 else "s")
                )
                if sesion:
                    texto_dia = (
                        f"{dia} · {sesion} · "
                        f"{len(ejercicios)} ejercicio"
                        + ("" if len(ejercicios) == 1 else "s")
                    )
            # la semana se abre entera de una sola vez: todos los días
            # con sus ejercicios a la vista al entrar en la subpestaña
            nodo = self.tree_rutina.insert(
                raiz, "end", iid="dia:" + dia,
                open=True,
                text=texto_dia,
                tags=("activa",) if dia == dia_activo else (),
            )
            for posicion, registro in enumerate(ejercicios, start=1):
                self.tree_rutina.insert(
                    nodo, "end", iid=str(registro["id_rutina"]),
                    text=f"{posicion}.",
                    values=(
                        registro["nombre"],
                        registro["equipo"] or "-",
                        registro["series"] or "-",
                        registro["repeticiones"] or "-",
                        registro["descanso_rep"] or "-",
                        registro["descanso_series"] or "-",
                        registro["peso"] or "-",
                    ),
                )
        total_dia = len([r for r in filas_activas if not r.get("descanso")])
        self.lbl_rutina_total.configure(
            text=f"{total_dia} ejercicio" + ("" if total_dia == 1 else "s")
            + f" · semana: {total_semana}"
        )
        # deja visible y seleccionado el día activo
        if "dia:" + dia_activo in self.tree_rutina.get_children(raiz):
            self.tree_rutina.see("dia:" + dia_activo)
            self.tree_rutina.selection_set("dia:" + dia_activo)
        self._actualizar_sesion_dia()
        # estado neutro del letrero: lo que se ve viene de la BD; los
        # escritos lo encienden en neón con la hora (_marcar_rutina_guardada)
        if hasattr(self, "lbl_rutina_guardada"):
            self.lbl_rutina_guardada.configure(
                text="Guardada en la BD ✓" if semana else "Rutina vacía",
                foreground=GRIS_TEXTO,
            )

    # ------------------------------------------------------------------
    # Rutina semanal: día en edición y días de descanso
    # ------------------------------------------------------------------

    def _cambiar_dia(self, dia):
        if dia == self.dia_actual:
            return
        self.dia_actual = dia
        self._render_rutina()

    def _resaltar_dia(self):
        for dia, btn in getattr(self, "dia_buttons", {}).items():
            seleccionado = dia == self.dia_actual
            btn.configure(
                bg=NEON if seleccionado else GRIS,
                fg=NEGRO if seleccionado else BLANCO,
            )

    def _alternar_descanso(self):
        """Marca el día actual como descanso (borrando sus ejercicios,
        con confirmación) o quita la marca si ya era descanso."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas", "Selecciona un paciente antes de marcar descansos."
            )
            return
        dia = self.dia_actual
        filas = [
            r for r in getattr(self, "rutina", [])
            if (r.get("dia") or "Lunes") == dia
        ]
        if any(r.get("descanso") for r in filas):
            try:
                database.quitar_descanso(paciente_id, dia)
            except Exception as error:
                messagebox.showerror(
                    "Rutinas", f"No se pudo quitar el descanso:\n{error}"
                )
                return
            self._cargar_rutina()
            self._mensaje(f"{dia}: día de descanso quitado.")
            return
        ejercicios = [r for r in filas if not r.get("descanso")]
        if ejercicios and not messagebox.askyesno(
            "Rutinas",
            f"{dia} tiene {len(ejercicios)} ejercicio(s).\n"
            f"¿Borrarlos y marcar el día como descanso?",
        ):
            return
        try:
            database.marcar_descanso(paciente_id, dia)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo marcar el descanso:\n{error}"
            )
            return
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje(f"{dia}: marcado como día de descanso.")

    def cargar(self, paciente_id):
        self.paciente_id = paciente_id
        if paciente_id is None:
            self._estado_base = "Rutinas: sin paciente seleccionado"
            self.lbl_estado.configure(text=self._estado_base)
        else:
            nombre = ""
            try:
                paciente = database.obtener_paciente(paciente_id)
                nombre = (paciente or {}).get("nombre") or ""
            except Exception:
                nombre = ""
            if nombre:
                texto = f"Rutina de {nombre} (ID {paciente_id})"
            else:
                texto = f"Rutina del paciente {paciente_id}"
            self._estado_base = texto
            self.lbl_estado.configure(text=texto)
        self._cargar_rutina()
        self._cargar_est_paciente()
        self._cargar_calentamiento_paciente()
        self._recargar_referencias_1rm()
        if hasattr(self, "tree_sem_historial"):
            self._sem_refrescar_historial()
        self._refrescar_historial_pac()

    def refrescar_estado(self):
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id != self.paciente_id:
            self.cargar(paciente_id)
            return
        # Mismo paciente: refresca la selección de estiramientos por si cambió
        # desde la pestaña Estiramientos.
        self._cargar_est_paciente()


    def _crear_tab_ciclos(self):
        """Sub-pestaña Ciclos: mesociclos de 4 semanas (3 de carga
        progresiva + deloading en la cuarta) y macrociclos de 1 a 3
        bloques encadenados a partir de una semana base."""
        marco = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        self.notebook_rut.add(marco, text="  Ciclos  ")
        self.marco_cic = marco

        self._cic_datos = None
        self._cic_nombre_base = ""
        self._cic_guardada_id = None

        contenedor = ttk.Frame(marco, style="Gym.TFrame")
        contenedor.pack(fill="both", expand=True, padx=8, pady=(4, 2))

        izquierdo = ttk.LabelFrame(
            contenedor, text="Semana base (doble clic = elegir)", padding=4)
        izquierdo.pack(side="left", fill="y", padx=(0, 6))
        cols_base = ("nombre", "origen", "dias", "ejercicios")
        self.tree_cic_base = ttk.Treeview(
            izquierdo, columns=cols_base, show="headings", height=13,
            selectmode="browse", style="Gym.Treeview")
        for col, texto, ancho in (
            ("nombre", "Rutina", 170), ("origen", "Origen", 78),
            ("dias", "Días", 40), ("ejercicios", "Ejerc.", 48)):
            self.tree_cic_base.heading(col, text=texto)
            self.tree_cic_base.column(col, width=ancho, minwidth=ancho,
                anchor="w" if col == "nombre" else "center")
        self.tree_cic_base.pack(side="top", fill="both", expand=True)
        self.tree_cic_base.bind("<Double-1>",
                                lambda _e: self._cic_elegir_base())
        tk.Label(izquierdo, text="La semana elegida siembra el ciclo; "
                 "las semanas generadas se aplican al historial de Semana.",
                 font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
                 wraplength=290, justify="left").pack(
            side="bottom", fill="x", pady=(4, 0))
        self._cic_refrescar_bases()

        derecho = ttk.Frame(contenedor, style="Gym.TFrame")
        derecho.pack(side="left", fill="both", expand=True)

        fila_ctrl = ttk.Frame(derecho, style="Gym.TFrame")
        fila_ctrl.pack(fill="x", pady=(0, 3))
        tk.Label(fila_ctrl, text="Nombre:", font=("Segoe UI", 8),
                 fg=GRIS_TEXTO, bg=GRIS_OSCURO).pack(side="left")
        self.entrada_cic_nombre = tk.Entry(fila_ctrl, width=26,
                                           font=("Segoe UI", 9))
        self.entrada_cic_nombre.pack(side="left", padx=(4, 10))
        tk.Label(fila_ctrl, text="Objetivo:", font=("Segoe UI", 8),
                 fg=GRIS_TEXTO, bg=GRIS_OSCURO).pack(side="left")
        self.cic_objetivo_var = tk.StringVar(value="Hipertrofia")
        ttk.Combobox(fila_ctrl, textvariable=self.cic_objetivo_var,
                     values=tuple(CIC_SECUENCIAS), state="readonly",
                     width=12, style="Gym.TCombobox").pack(
            side="left", padx=(4, 10))
        tk.Label(fila_ctrl, text="Mesociclos:", font=("Segoe UI", 8),
                 fg=GRIS_TEXTO, bg=GRIS_OSCURO).pack(side="left")
        self.cic_n_var = tk.StringVar(value="2")
        ttk.Spinbox(fila_ctrl, from_=1, to=3, width=3,
                    textvariable=self.cic_n_var,
                    style="Gym.TSpinbox").pack(side="left", padx=(4, 10))
        tk.Button(fila_ctrl, text="⚙ GENERAR", command=self._cic_generar,
                  font=("Impact", 10), fg=NEGRO, bg=NEON,
                  activebackground=NARANJA, activeforeground=BLANCO,
                  relief="flat", padx=12, pady=3, cursor="hand2").pack(
            side="left", padx=(0, 8))

        fila_acciones = ttk.Frame(derecho, style="Gym.TFrame")
        fila_acciones.pack(fill="x", pady=(0, 4))
        tk.Label(fila_acciones, text="Ver mesociclo:", font=("Segoe UI", 8),
                 fg=GRIS_TEXTO, bg=GRIS_OSCURO).pack(side="left")
        self.cic_ver_var = tk.StringVar()
        self.cic_ver_combo = ttk.Combobox(fila_acciones,
            textvariable=self.cic_ver_var, state="disabled", width=30,
            style="Gym.TCombobox")
        self.cic_ver_combo.pack(side="left", padx=(4, 6))
        self.cic_ver_combo.bind("<<ComboboxSelected>>",
                                lambda _e: self._cic_pintar())
        for texto, comando in (
            ("💾 GUARDAR", self._cic_guardar),
            ("📂 CARGAR", self._cic_cargar_guardada),
            ("🗑 ELIMINAR", self._cic_eliminar),
            ("➡ APLICAR AL PACIENTE", self._cic_aplicar),
            ("🖨 IMPRIMIR PDF", self._cic_imprimir)):
            tk.Button(fila_acciones, text=texto, command=comando,
                      font=("Segoe UI", 8, "bold"), fg=NEON, bg=GRIS,
                      activebackground=NARANJA, activeforeground=BLANCO,
                      relief="flat", padx=8, pady=2, cursor="hand2").pack(
                side="left", padx=(4, 0))

        self.lbl_cic_info = tk.Label(derecho, text="Genera un ciclo desde "
            "una semana base: cada mesociclo son 4 semanas (3 de carga "
            "progresiva y la semana 4 de deloading: mitad de series y "
            "carga -10 %).", font=("Segoe UI", 8), fg=GRIS_TEXTO,
            bg=GRIS_OSCURO, wraplength=620, justify="left", anchor="w")
        self.lbl_cic_info.pack(fill="x", pady=(0, 3))

        cols = ("dia", "ejercicio", "s1", "s2", "s3", "s4")
        self.tree_cic = ttk.Treeview(derecho, columns=cols, show="headings",
            height=16, selectmode="browse", style="Gym.Treeview")
        for col, texto, ancho in (
            ("dia", "Día", 78), ("ejercicio", "Ejercicio", 218),
            ("s1", "Semana 1", 118), ("s2", "Semana 2", 118),
            ("s3", "Semana 3", 118), ("s4", "Semana 4 · deload", 118)):
            self.tree_cic.heading(col, text=texto)
            self.tree_cic.column(col, width=ancho, minwidth=ancho,
                anchor="w" if col in ("dia", "ejercicio") else "center")
        barra_cic = ttk.Scrollbar(derecho, orient="vertical",
                                  command=self.tree_cic.yview)
        self.tree_cic.configure(yscrollcommand=barra_cic.set)
        barra_cic.pack(side="right", fill="y")
        self.tree_cic.pack(side="left", fill="both", expand=True)
        self.tree_cic.tag_configure("deload", background="#3A2410",
                                    foreground="#FFB74D")
        self.tree_cic.tag_configure("dia", background=GRIS)
        self._cic_refrescar_bases()

    def _cic_refrescar_bases(self):
        """Llena el arbol de bases: solo la semana cargada en Semana y
        las semanales guardadas por el usuario."""
        self.tree_cic_base.delete(*self.tree_cic_base.get_children())
        n_sem = sum(len(d.get("ejercicios") or [])
                    for d in (self._sem_datos or {}).values())
        if n_sem:
            dias_con = sum(1 for d in (self._sem_datos or {}).values()
                           if d.get("ejercicios"))
            self.tree_cic_base.insert(
                "", tk.END, iid="__actual__",
                values=("Semana actual", "Semana", dias_con, n_sem))
        for g in self._semanales_guardadas():
            self.tree_cic_base.insert(
                "", tk.END, iid=str(g["id_rutina_guardada"]),
                values=(g["nombre"], "Guardada", g.get("dias") or 0,
                        g.get("ejercicios") or 0))

    def _cic_elegir_base(self):
        sel = self.tree_cic_base.selection()
        if not sel:
            return
        iid = sel[0]
        if iid == "__actual__":
            self._cic_nombre_base = "Semana actual"
        else:
            guardada = next((g for g in self._semanales_guardadas()
                             if str(g["id_rutina_guardada"]) == iid), None)
            self._cic_nombre_base = guardada["nombre"] if guardada else ""
        self._cic_guardada_id = None
        self._mensaje(f"Base del ciclo: {self._cic_nombre_base}")

    def _cic_obtener_base(self):
        """{dia: [ficha]} de la semana base elegida (la semana cargada en
        Semana o una semanal guardada)."""
        if self._cic_nombre_base == "Semana actual":
            return {dia: list(d.get("ejercicios") or [])
                    for dia, d in (self._sem_datos or {}).items()
                    if d.get("ejercicios")}
        guardadas = {g["nombre"]: g for g in self._semanales_guardadas()}
        guardada = guardadas.get(self._cic_nombre_base)
        if not guardada:
            return {}
        conv = self._plantilla_de_guardada(guardada)
        base = {}
        for dia, sesion in conv["semana"].items():
            if not sesion:
                continue
            base[dia] = [self._sem_ficha_con_prescripcion(f)
                         for f in conv["sesiones"].get(sesion, [])]
        return base

    @staticmethod
    def _cic_num_peso(texto):
        """Kg numericos del texto de peso ('50 kg' -> 50.0); None si no hay."""
        m = re.search(r"(\d+(?:[.,]\d+)?)", str(texto or ""))
        return float(m.group(1).replace(",", ".")) if m else None

    def _cic_peso_texto(self, peso_base, mult):
        """Peso escalado por mult y redondeado a discos de 2.5 kg."""
        kg = self._cic_num_peso(peso_base)
        if kg is None or kg <= 0:
            return str(peso_base or "")
        escalado = _discos_2_5(kg * mult)
        return f"{escalado:g} kg"

    def _cic_generar(self):
        if not self._cic_nombre_base:
            messagebox.showwarning(
                "Ciclos", "Elige primero una semana base (doble clic en la "
                "lista de la izquierda).", parent=self.marco_cic)
            return
        try:
            n_mesos = max(1, min(3, int(self.cic_n_var.get())))
        except ValueError:
            n_mesos = 2
        objetivo = self.cic_objetivo_var.get()
        base = self._cic_obtener_base()
        if not base:
            messagebox.showwarning("Ciclos", "La semana base no tiene "
                                   "ejercicios.", parent=self.marco_cic)
            return
        secuencia = CIC_SECUENCIAS[objetivo][:n_mesos]
        bloques = []
        for spec in secuencia:
            ramp = spec["ramp"]
            semanas = []
            for wi, mult in enumerate(ramp, start=1):
                semanas.append({"n": wi, "tipo": "Carga", "peso_mult": mult,
                                "series_extra": 1 if wi == 3 else 0})
            semanas.append({"n": 4, "tipo": "Deload",
                            "peso_mult": CIC_DELOAD_PESO, "series_extra": 0})
            dias = {}
            for dia, fichas in base.items():
                filas = []
                for f in fichas:
                    filas.append({
                        "nombre": f.get("nombre") or "",
                        "equipo": f.get("equipo") or "",
                        "grupo": f.get("grupo"),
                        "num": f.get("num"),
                        "series_base": str(f.get("series") or "3"),
                        "reps_base": str(f.get("repeticiones") or "12"),
                        "descanso_rep": f.get("descanso_rep") or "",
                        "descanso_series": spec["descanso"],
                        "peso_base": str(f.get("peso") or ""),
                    })
                if filas:
                    dias[dia] = filas
            bloques.append({
                "objetivo": spec["objetivo"], "reps": spec["reps"],
                "descanso": spec["descanso"], "semanas": semanas,
                "dias": dias,
            })
        nombre = (self.entrada_cic_nombre.get() or "").strip() or (
            f"Ciclo {objetivo} · {self._cic_nombre_base}")
        self._cic_datos = {
            "base": self._cic_nombre_base, "objetivo": objetivo,
            "mesociclos": n_mesos, "notas": list(CIC_NOTAS),
            "bloques": bloques,
        }
        self._cic_guardada_id = None
        opciones = [f"Mesociclo {i + 1} · {b['objetivo']}"
                    for i, b in enumerate(bloques)]
        self.cic_ver_combo.configure(state="readonly", values=opciones)
        self.cic_ver_var.set(opciones[0])
        self.lbl_cic_info.configure(text=(
            f"Ciclo generado: {n_mesos} mesociclos × 4 semanas "
            f"({sum(len(b['semanas']) for b in bloques)} semanas totales). "
            "Semana 4 = deloading (mitad de series, carga -10 %). "
            "APLICAR AL PACIENTE deja cada semana en el historial de Semana."))
        self._cic_pintar()

    def _cic_bloque_actual(self):
        if not self._cic_datos:
            return None
        texto = self.cic_ver_var.get()
        for i, b in enumerate(self._cic_datos["bloques"]):
            if texto == f"Mesociclo {i + 1} · {b['objetivo']}":
                return b
        return (self._cic_datos["bloques"] or [None])[0]

    def _cic_pintar(self):
        bloque = self._cic_bloque_actual()
        self.tree_cic.delete(*self.tree_cic.get_children())
        if not bloque:
            return
        semanas = bloque["semanas"]
        for dia in DIAS_SEMANA:
            fichas = bloque["dias"].get(dia) or []
            if not fichas:
                continue
            self.tree_cic.insert("", tk.END,
                values=(dia, "", "", "", "", ""), tags=("dia",))
            for f in fichas:
                m = re.search(r"\d+", f["series_base"] or "")
                series = int(m.group()) if m else 3
                celdas = [dia, f["nombre"]]
                tags = ()
                for s in semanas:
                    if s["tipo"] == "Deload":
                        series_d = max(1, round(series * CIC_DELOAD_SERIES))
                    elif s.get("series_extra"):
                        series_d = series + s["series_extra"]
                    else:
                        series_d = series
                    peso = self._cic_peso_texto(f["peso_base"],
                                                s["peso_mult"])
                    celdas.append(f"{series_d}×{bloque['reps']} · {peso}")
                self.tree_cic.insert("", tk.END, values=tuple(celdas),
                                     tags=tags)

    def _cic_guardar(self):
        if not self._cic_datos:
            messagebox.showwarning("Ciclos", "Genera o carga un ciclo antes "
                                   "de guardar.", parent=self.marco_cic)
            return
        nombre = (self.entrada_cic_nombre.get() or "").strip()
        if not nombre:
            messagebox.showwarning("Ciclos", "Ponle nombre al ciclo.",
                                   parent=self.marco_cic)
            return
        id_ciclo = database.guardar_rutina_ciclo(
            nombre, self._cic_datos,
            self.paciente_id if self.paciente_id else None)
        self._cic_guardada_id = id_ciclo
        self._mensaje(f"Ciclo guardado: {nombre}")

    def _cic_cargar_guardada(self):
        lista = database.get_rutinas_ciclos(
            self.paciente_id if self.paciente_id else None)
        if not lista:
            messagebox.showinfo("Ciclos", "Todavía no hay ciclos guardados.",
                                parent=self.marco_cic)
            return
        ventana = tk.Toplevel(self.marco_cic)
        ventana.title("Ciclos guardados")
        ventana.configure(bg=GRIS_OSCURO)
        ventana.transient(self.marco.winfo_toplevel())
        ventana.geometry("560x360")
        tree = ttk.Treeview(ventana, columns=("nombre", "objetivo", "bloques",
                                              "semanas", "base"),
                            show="headings", height=12, style="Gym.Treeview")
        for col, texto, ancho in (
            ("nombre", "Ciclo", 190), ("objetivo", "Objetivo", 118),
            ("bloques", "Mesos", 44), ("semanas", "Semanas", 56),
            ("base", "Base", 120)):
            tree.heading(col, text=texto)
            tree.column(col, width=ancho, anchor="w" if col in
                        ("nombre", "base") else "center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        for c in lista:
            tree.insert("", tk.END, iid=str(c["id_ciclo"]), values=(
                c["nombre"], c["objetivo"], c["bloques"], c["semanas"],
                c["base"]))

        def abrir(_e=None):
            sel = tree.selection()
            if not sel:
                return
            ciclo = database.get_rutina_ciclo(int(sel[0]))
            self._cic_datos = ciclo["detalle"]
            self._cic_guardada_id = ciclo["id_ciclo"]
            self.entrada_cic_nombre.delete(0, tk.END)
            self.entrada_cic_nombre.insert(0, ciclo["nombre"])
            opciones = [f"Mesociclo {i + 1} · {b['objetivo']}"
                        for i, b in enumerate(
                            self._cic_datos.get("bloques") or [])]
            self.cic_ver_combo.configure(state="readonly", values=opciones)
            if opciones:
                self.cic_ver_var.set(opciones[0])
            self._cic_pintar()
            ventana.destroy()

        tree.bind("<Double-1>", abrir)
        tk.Button(ventana, text="CARGAR", command=abrir,
                  font=("Impact", 10), fg=NEGRO, bg=NEON,
                  activebackground=NARANJA, activeforeground=BLANCO,
                  relief="flat", padx=14, pady=3, cursor="hand2").pack(
            pady=(0, 8))

    def _cic_eliminar(self):
        lista = database.get_rutinas_ciclos(
            self.paciente_id if self.paciente_id else None)
        if not lista:
            messagebox.showinfo("Ciclos", "No hay ciclos guardados.",
                                parent=self.marco_cic)
            return
        ventana = tk.Toplevel(self.marco_cic)
        ventana.title("Eliminar ciclo")
        ventana.configure(bg=GRIS_OSCURO)
        ventana.transient(self.marco.winfo_toplevel())
        ventana.geometry("520x320")
        tree = ttk.Treeview(ventana, columns=("nombre", "objetivo"),
                            show="headings", height=11, style="Gym.Treeview")
        tree.heading("nombre", text="Ciclo")
        tree.heading("objetivo", text="Objetivo")
        tree.column("nombre", width=280, anchor="w")
        tree.column("objetivo", width=180, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        for c in lista:
            tree.insert("", tk.END, iid=str(c["id_ciclo"]),
                        values=(c["nombre"], c["objetivo"]))

        def borrar(_e=None):
            sel = tree.selection()
            if not sel:
                return
            database.delete_rutina_ciclo(int(sel[0]))
            ventana.destroy()
            self._mensaje("Ciclo eliminado.")

        tree.bind("<Double-1>", borrar)
        tk.Button(ventana, text="🗑 ELIMINAR", command=borrar,
                  font=("Impact", 10), fg=BLANCO, bg=GRIS,
                  activebackground=NARANJA, activeforeground=BLANCO,
                  relief="flat", padx=14, pady=3, cursor="hand2").pack(
            pady=(0, 8))

    def _cic_aplicar(self):
        """Deja cada semana del ciclo en el historial de Semana del
        paciente (semanas reales, cargables una a una)."""
        if not self._cic_datos:
            messagebox.showwarning("Ciclos", "Genera o carga un ciclo antes "
                                   "de aplicar.", parent=self.marco_cic)
            return
        if not self.paciente_id:
            messagebox.showwarning("Ciclos", "Selecciona un paciente antes "
                                   "de aplicar.", parent=self.marco_cic)
            return
        nombre = (self.entrada_cic_nombre.get() or "").strip() or "Ciclo"
        semanas = 0
        for bi, bloque in enumerate(self._cic_datos["bloques"], start=1):
            for s in bloque["semanas"]:
                dias = []
                for dia, fichas in (bloque["dias"] or {}).items():
                    ejercicios = []
                    for f in fichas:
                        m = re.search(r"\d+", f["series_base"] or "")
                        series = int(m.group()) if m else 3
                        if s["tipo"] == "Deload":
                            series = max(1, round(series * CIC_DELOAD_SERIES))
                        elif s.get("series_extra"):
                            series += s["series_extra"]
                        ejercicios.append({
                            "dia": dia, "sesion": (
                                f"{bloque['objetivo']} · Semana {s['n']}"),
                            "nombre": f["nombre"], "equipo": f["equipo"],
                            "grupo": f.get("grupo"), "num": f.get("num"),
                            "series": str(series),
                            "repeticiones": bloque["reps"],
                            "descanso_rep": f.get("descanso_rep") or "",
                            "descanso_series": f.get("descanso_series") or "",
                            "peso": self._cic_peso_texto(f["peso_base"],
                                                         s["peso_mult"]),
                            "notas": "",
                        })
                    dias.append({"dia": dia,
                                 "sesion": (f"{bloque['objetivo']} · "
                                            f"Semana {s['n']}"),
                                 "ejercicios": ejercicios})
                database.guardar_rutina_historial(
                    self.paciente_id,
                    f"{nombre} · Mesociclo {bi} ({bloque['objetivo']}) · "
                    f"Semana {s['n']} ({s['tipo']})",
                    json.dumps(dias, ensure_ascii=False))
                semanas += 1
        self._mensaje(f"Ciclo aplicado: {semanas} semanas en el historial "
                      "de Semana.")

    def _cic_imprimir(self):
        """PDF del ciclo: una tabla por dia con las 4 semanas del
        mesociclo (la de deloading sombreada) y notas cientificas."""
        if not self._cic_datos:
            messagebox.showwarning("Ciclos", "Genera o carga un ciclo antes "
                                   "de imprimir.", parent=self.marco_cic)
            return
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (PageBreak, Paragraph,
                                        SimpleDocTemplate, Spacer, Table,
                                        TableStyle)
        nombre = (self.entrada_cic_nombre.get() or "").strip() or "Ciclo"
        ruta = rutina_print.ruta_temporal_pdf(nombre)
        base_est = getSampleStyleSheet()
        h1 = ParagraphStyle("ciclo_h1", parent=base_est["Heading1"],
                            textColor=rl_colors.HexColor("#7A1F1F"),
                            fontSize=15)
        h2 = ParagraphStyle("ciclo_h2", parent=base_est["Heading2"],
                            textColor=rl_colors.HexColor("#7A1F1F"),
                            fontSize=12)
        normal = ParagraphStyle("ciclo_n", parent=base_est["Normal"],
                                fontSize=8.5)
        chico = ParagraphStyle("ciclo_c", parent=base_est["Normal"],
                               fontSize=7.2,
                               textColor=rl_colors.HexColor("#444444"))
        elementos = [
            Paragraph("CICLO DE ENTRENAMIENTO", h1),
            Paragraph(f"{nombre} · objetivo {self._cic_datos['objetivo']} · "
                      f"{self._cic_datos.get('mesociclos', 1)} mesociclos × "
                      "4 semanas (3 de carga progresiva + deloading en la "
                      "4.ª semana)", normal),
            Spacer(1, 8),
        ]
        ancho_ej = 3.3 * inch
        ancho_sem = (7.2 * inch - ancho_ej) / 4.0
        deload_bg = rl_colors.HexColor("#FDEBD0")
        for bi, bloque in enumerate(self._cic_datos["bloques"], start=1):
            if bi > 1:
                elementos.append(PageBreak())
            else:
                elementos.append(Spacer(1, 2))
            elementos.append(Paragraph(
                f"MESOCICLO {bi} · {bloque['objetivo']} "
                f"({bloque['reps']} reps · descanso {bloque['descanso']} s)",
                h2))
            for dia in DIAS_SEMANA:
                fichas = bloque["dias"].get(dia) or []
                if not fichas:
                    continue
                elementos.append(Spacer(1, 6))
                elementos.append(Paragraph(dia, normal))
                fila_head = [Paragraph("<b>Ejercicio</b>", normal),
                             Paragraph("<b>S1 · carga</b>", normal),
                             Paragraph("<b>S2 · carga</b>", normal),
                             Paragraph("<b>S3 · carga</b>", normal),
                             Paragraph("<b>S4 · deload</b>", normal)]
                tabla_filas = [fila_head]
                estilos_extra = []
                for fi, f in enumerate(fichas, start=1):
                    m = re.search(r"\d+", f["series_base"] or "")
                    n_series = int(m.group()) if m else 3
                    celdas = [Paragraph(f["nombre"], normal)]
                    for s in bloque["semanas"]:
                        if s["tipo"] == "Deload":
                            series = max(1,
                                         round(n_series * CIC_DELOAD_SERIES))
                        elif s.get("series_extra"):
                            series = n_series + s["series_extra"]
                        else:
                            series = n_series
                        celdas.append(Paragraph(
                            f"{series}×{bloque['reps']}<br/>"
                            f"{self._cic_peso_texto(f['peso_base'],
                                                    s['peso_mult'])}", normal))
                    tabla_filas.append(celdas)
                tabla = Table(tabla_filas, colWidths=[
                    ancho_ej, ancho_sem, ancho_sem, ancho_sem, ancho_sem])
                tabla.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.5,
                     rl_colors.HexColor("#BBBBBB")),
                    ("BACKGROUND", (0, 0), (-1, 0),
                     rl_colors.HexColor("#F2D7D5")),
                    ("BACKGROUND", (4, 1), (4, -1), deload_bg),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]))
                elementos.append(tabla)
        elementos.append(Spacer(1, 10))
        elementos.append(Paragraph("BASE CIENTÍFICA DEL DISEÑO", h2))
        for nota in self._cic_datos.get("notas") or CIC_NOTAS:
            elementos.append(Paragraph("• " + nota, chico))
        doc = SimpleDocTemplate(
            ruta, pagesize=letter, rightMargin=0.55 * inch,
            leftMargin=0.55 * inch, topMargin=0.5 * inch,
            bottomMargin=0.55 * inch, title=f"Ciclo — {nombre}",
            author="Nutrición Deportiva")
        doc.build(elementos)
        os.startfile(ruta)
# ----------------------------------------------------------------------
# Ciclos de entrenamiento (mesociclos y macrociclos). Diseno con base
# cientifica: mesociclo de 4 semanas = 3 de carga progresiva + 1 de
# deloading (Issurin 2010; Lorenz 2015); el deloading reduce el VOLUMEN
# ~50 % (mitad de series) manteniendo intensidad y frecuencia, la
# reduccion optima documentada es 41-60 % del volumen (Bosquet et al.
# 2007, meta-analisis de tapering; Rogerson et al. 2024, practicas de
# atletas: mismos sesiones, menos series/repeticiones). La carga progresiva
# suma ~2.5-5 % por semana (sobrecarga progresiva). El macrociclo encadena
# bloques Hipertrofia -> Fuerza (secuencia de Bompa; potentiation de
# bloques y efectos residuales de Issurin). Las semanas generadas son
# semanas REALES de la app: APLICAR AL PACIENTE las deja en el historial
# de la pestana Semana listas para cargar una a una.
# ----------------------------------------------------------------------
CIC_SECUENCIAS = {
    "Hipertrofia": [
        {"objetivo": "Hipertrofia · volumen", "reps": "10-12",
         "descanso": "60-90", "ramp": (1.00, 1.025, 1.05)},
        {"objetivo": "Hipertrofia · intensiva", "reps": "8-10",
         "descanso": "90", "ramp": (1.00, 1.025, 1.05)},
        {"objetivo": "Fuerza", "reps": "4-6",
         "descanso": "150-180", "ramp": (1.00, 1.05, 1.10)},
    ],
    "Fuerza": [
        {"objetivo": "Hipertrofia · base", "reps": "8-12",
         "descanso": "90", "ramp": (1.00, 1.025, 1.05)},
        {"objetivo": "Fuerza", "reps": "4-6",
         "descanso": "150-180", "ramp": (1.00, 1.05, 1.10)},
        {"objetivo": "Fuerza · pesada", "reps": "3-5",
         "descanso": "180-210", "ramp": (1.00, 1.05, 1.10)},
    ],
    "General": [
        {"objetivo": "General · adaptación", "reps": "8-12",
         "descanso": "90", "ramp": (1.00, 1.025, 1.05)},
        {"objetivo": "General · progresión", "reps": "8-12",
         "descanso": "90", "ramp": (1.025, 1.05, 1.075)},
    ],
}
CIC_DELOAD_SERIES = 0.5     # mitad de series (volumen -50 %)
CIC_DELOAD_PESO = 0.90      # carga -10 % por prudencia (intensidad similar)
CIC_NOTAS = (
    "Mesociclo de 4 semanas: 3 de carga progresiva + 1 de deloading "
    "(Issurin 2010; Lorenz 2015).",
    "Deloading: se reduce el volumen ~50 % (mitad de series) y la carga "
    "-10 %, manteniendo sesiones y ejercicios; la reduccion optima "
    "documentada es 41-60 % del volumen con intensidad estable "
    "(Bosquet et al. 2007, meta-analisis).",
    "Progresion de carga ~2.5-5 % por semana dentro del bloque "
    "(sobrecarga progresiva; redondeo a discos de 2.5 kg).",
    "Macrociclo: bloques encadenados Hipertrofia -> Fuerza; el bloque "
    "previo potencia al siguiente (efectos residuales, Issurin 2010).",
    "El deloading cada 4-8 semanas es la practica habitual; Coleman et "
    "al. 2024 sugiere autorregularlo segun fatiga y rendimiento.",
)
