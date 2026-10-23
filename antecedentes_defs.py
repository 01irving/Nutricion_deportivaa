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
)

ETIQUETA_HABITOS = {
    clave: f"{etiqueta}:" for clave, etiqueta in SECCION_NOPATOLOGICOS_HABITOS
}
