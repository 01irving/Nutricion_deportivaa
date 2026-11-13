"""
Definiciones compartidas de la pestaña Antecedentes.

Fuente única para la base de datos, la interfaz y el reporte imprimible:
si se agrega un campo, queda disponible en los tres lugares.
"""

SECCION_PATOLOGICOS = [
    ("pat_familiares", "Antecedentes familiares"),
    ("pat_personales", "Antecedentes personales"),
    ("pat_alergia_alimentaria", "Alergia alimentaria"),
    ("pat_quirurgicos", "Antecedentes quirúrgicos"),
]

SECCION_NOPATOLOGICOS_HABITOS = [
    ("nopat_tabaco", "Tabaco"),
    ("nopat_alcohol", "Alcohol"),
    ("nopat_drogas", "Drogas"),
    ("nopat_cafe", "Café"),
]

SECCION_NOPATOLOGICOS_TEXTO = [
    ("nopat_medicamentos", "Medicamentos"),
    ("nopat_actividad_fisica", "Actividad física"),
    ("nopat_problemas_intestinales", "Problemas intestinales"),
]

# Evaluación del cliente para el ejercicio (valoración de client
# assessment: condiciones médicas, medicamentos, lesiones y
# banderas rojas).
SECCION_EVALUACION_SELECCION = [
    ("eval_condiciones_medicas", "Condiciones médicas"),
    ("eval_banderas_rojas", "Indicaciones de alerta (banderas rojas)"),
]

SECCION_EVALUACION_TEXTO = [
    ("eval_historial_lesiones", "Historial de lesiones"),
]

# Estilo de vida: ocupación, horario y preferencias de entrenamiento
# (contexto para armar el plan de ejercicio).
SECCION_ESTILO_TEXTO = [
    ("estilo_ocupacion", "Ocupación (¿trabaja o estudia?)"),
    ("estilo_horario", "Horario"),
    ("estilo_ejercicios_gustan", "Ejercicios que le gustan"),
    ("estilo_ejercicios_no_gustan", "Ejercicios que NO le gustan"),
]

SECCION_ESTILO_SELECCION = [
    ("estilo_lugar_entrenamiento", "Lugar de entrenamiento"),
]

OPCIONES_ESTILO = {
    "estilo_lugar_entrenamiento": [
        "Casa", "Gimnasio", "Casa y gimnasio", "Ninguno todavía",
    ],
}

OPCIONES_SELECCION = {
    "eval_condiciones_medicas": [
        "Ninguna", "Diabetes", "Hipertensión", "Enfermedad cardíaca",
        "Asma", "Obesidad", "Artritis", "Colesterol alto",
        "Problemas de tiroides", "Epilepsia", "Embarazo", "Otra",
    ],
    "eval_banderas_rojas": [
        "Ninguna", "Dolor en el pecho", "Mareo o desmayo",
        "Dificultad inusual para respirar", "Palpitaciones",
        "Dolor articular agudo", "Dolor de cabeza severo",
        "Fatiga inusual", "Hinchazón en los tobillos",
    ],
}

HABITOS_OPCIONES = {
    "nopat_tabaco": ["No", "Sí", "Ex-fumador", "Ocasional", "A diario"],
    "nopat_alcohol": ["No", "Sí", "Social", "Diario", "Ex-alcoholista"],
    "nopat_drogas": ["No", "Sí", "Uso pasado"],
    "nopat_cafe": ["No", "Sí", "Ocasional", "Diario", "Descafeinado"],
}

ANTECEDENTES_CAMPOS = (
    [clave for clave, _ in SECCION_PATOLOGICOS]
    + [clave for clave, _ in SECCION_NOPATOLOGICOS_HABITOS]
    + [clave for clave, _ in SECCION_NOPATOLOGICOS_TEXTO]
    + [clave for clave, _ in SECCION_EVALUACION_SELECCION]
    + [clave for clave, _ in SECCION_EVALUACION_TEXTO]
    + [clave for clave, _ in SECCION_ESTILO_SELECCION]
    + [clave for clave, _ in SECCION_ESTILO_TEXTO]
)

ETIQUETA_HABITOS = {
    clave: f"{etiqueta}:" for clave, etiqueta in SECCION_NOPATOLOGICOS_HABITOS
}
