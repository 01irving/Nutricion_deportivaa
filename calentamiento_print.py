"""
Generación del reporte imprimible de calentamiento.

Exporta a PDF con ReportLab: membrete institucional, datos del paciente,
resumen ordenado del calentamiento y el detalle de cada ejercicio con su
ilustración, ejecución, músculos trabajados y comentarios.
"""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from impresion_utils import (
    abrir_para_imprimir,
    calcular_edad,
    crear_membrete,
    nombre_pdf,
)
from impresion_utils import ruta_temporal_pdf as _ruta_temporal_pdf
from rutas import base_dir

__all__ = [
    "abrir_para_imprimir",
    "calcular_edad",
    "generar_pdf_calentamiento",
    "nombre_pdf",
    "ruta_temporal_pdf",
]

NEGRO = colors.HexColor("#121212")
GRIS_OSCURO = colors.HexColor("#1E1E1E")
GRIS = colors.HexColor("#2C2C2C")
NARANJA = colors.HexColor("#FF6D00")
GRIS_TEXTO = colors.HexColor("#B0B0B0")

RUTA_IMAGENES = os.path.join(base_dir(), "assets", "rutinas", "calentamiento")

MAX_ANCHO_IMAGEN = 3.1 * inch
MAX_ALTO_IMAGEN = 3.4 * inch

ZONAS = {
    "movilidad": "Movilidad",
    "activacion": "Activación",
    "neural": "Activación neural",
    "especifico": "Específico con barra",
}


def _escapar(texto):
    """Escapa caracteres XML para ReportLab."""
    if texto is None:
        return ""
    texto = str(texto)
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _multi(texto):
    """Escapa el texto y conserva los saltos de línea como <br/>."""
    return _escapar(texto).replace("\n", "<br/>")


def _zona_etiqueta(zona):
    """Etiqueta legible de la zona del calentamiento."""
    zona = str(zona or "")
    return ZONAS.get(zona, zona.capitalize())


def _duracion_segundos(texto):
    """Convierte una duración ('45 s', '2 min') a segundos; None si no aplica."""
    partes = str(texto or "").strip().lower().split()
    if len(partes) != 2:
        return None
    try:
        valor = float(partes[0])
    except ValueError:
        return None
    if partes[1].startswith("s"):
        return valor
    if partes[1].startswith("min"):
        return valor * 60
    return None


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=18, leading=22, textColor=NEGRO, spaceAfter=2,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"], fontName="Helvetica",
            fontSize=10, leading=13, textColor=GRIS_TEXTO, spaceAfter=8,
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=NARANJA,
            spaceBefore=10, spaceAfter=4,
        ),
        "ejercicio": ParagraphStyle(
            "ejercicio", parent=base["Heading3"], fontName="Helvetica-Bold",
            fontSize=11.5, leading=15, textColor=NEGRO, spaceAfter=2,
            keepWithNext=1,
        ),
        "normal": ParagraphStyle(
            "normal", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=12, textColor=NEGRO, alignment=TA_LEFT,
        ),
        "etiqueta": ParagraphStyle(
            "etiqueta", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=colors.HexColor("#444444"),
        ),
        "centro": ParagraphStyle(
            "centro", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8.5, leading=11, textColor=colors.white, alignment=TA_CENTER,
        ),
        "celda": ParagraphStyle(
            "celda", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=11, textColor=NEGRO, alignment=TA_LEFT,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=8, leading=10, textColor=GRIS_TEXTO, alignment=TA_CENTER,
        ),
    }


def ruta_temporal_pdf(nombre_paciente):
    """Ruta del PDF temporal de calentamiento para un paciente."""
    return _ruta_temporal_pdf("Calentamiento", nombre_paciente)


def _imagen_flowable(nombre_imagen):
    """Ilustración del ejercicio ajustada a la caja de la página."""
    if not nombre_imagen:
        return None
    ruta = os.path.join(RUTA_IMAGENES, f"cal_{nombre_imagen}.jpeg")
    if not os.path.exists(ruta):
        return None
    try:
        ancho_px, alto_px = ImageReader(ruta).getSize()
    except Exception:
        return None
    if not ancho_px or not alto_px:
        return None
    escala = min(MAX_ANCHO_IMAGEN / ancho_px, MAX_ALTO_IMAGEN / alto_px)
    ancho = ancho_px * escala
    alto = alto_px * escala
    imagen = RLImage(ruta, width=ancho, height=alto)
    imagen.hAlign = "CENTER"
    return imagen


def _tabla_datos(estilos, paciente, momento):
    fecha_nac = paciente.get("fecha_nacimiento") or paciente.get("dob") or ""
    edad = calcular_edad(fecha_nac)
    datos = [
        ("Nombre", paciente.get("nombre") or "-"),
        ("Edad", f"{edad} años" if edad is not None else "-"),
        ("Dirección", paciente.get("direccion") or "-"),
        ("Teléfono", paciente.get("telefono") or "-"),
        ("Fecha de impresión", momento.strftime("%d/%m/%Y %H:%M")),
    ]
    tabla = Table(
        [
            [
                Paragraph(f"{etiqueta}:", estilos["etiqueta"]),
                Paragraph(_escapar(valor), estilos["normal"]),
            ]
            for etiqueta, valor in datos
        ],
        colWidths=[1.6 * inch, 4.6 * inch],
        hAlign="LEFT",
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), GRIS),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tabla


def _tabla_resumen(estilos, plan):
    resumen = [
        [
            Paragraph("#", estilos["centro"]),
            Paragraph("Ejercicio", estilos["centro"]),
            Paragraph("Zona", estilos["centro"]),
            Paragraph("Duración", estilos["centro"]),
        ]
    ]
    for ficha in plan:
        resumen.append(
            [
                Paragraph(str(ficha.get("orden", "")), estilos["celda"]),
                Paragraph(_escapar(ficha.get("nombre", "")), estilos["celda"]),
                Paragraph(
                    _escapar(_zona_etiqueta(ficha.get("zona"))), estilos["celda"]
                ),
                Paragraph(
                    _escapar(ficha.get("duracion") or "-"), estilos["celda"]
                ),
            ]
        )
    tabla = Table(
        resumen,
        colWidths=[0.35 * inch, 3.6 * inch, 1.6 * inch, 0.85 * inch],
        repeatRows=1,
        hAlign="LEFT",
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GRIS_OSCURO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#F2F2F2")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabla


def _bloque_detalle(estilos, ficha):
    """Flowables del detalle de un ejercicio (texto + ilustración)."""
    bloque = []

    bloque.append(Paragraph(_escapar(ficha.get("nombre", "")), estilos["ejercicio"]))

    meta = []
    zona = _zona_etiqueta(ficha.get("zona"))
    if zona:
        meta.append(f"Zona: {_escapar(zona)}")
    if ficha.get("equipo"):
        meta.append(f"Equipo: {_escapar(ficha['equipo'])}")
    if ficha.get("duracion"):
        meta.append(f"Duración: {_escapar(ficha['duracion'])}")
    if meta:
        bloque.append(Paragraph(" | ".join(meta), estilos["normal"]))

    imagen = _imagen_flowable(ficha.get("imagen"))
    if imagen is not None:
        bloque.append(imagen)

    if ficha.get("descripcion"):
        bloque.append(Paragraph(_multi(ficha["descripcion"]), estilos["normal"]))

    return bloque


def generar_pdf_calentamiento(ruta, paciente, plan, momento_impresion=None):
    """
    Genera el PDF del reporte de calentamiento.

    paciente: dict con nombre, fecha_nacimiento/dob, direccion, telefono.
    plan: lista de fichas del calentamiento ya ordenadas, cada una con
          num, nombre, zona, equipo, orden, duracion, imagen y descripcion.
    """
    estilos = _estilos()
    momento = momento_impresion or datetime.now()

    doc = SimpleDocTemplate(
        ruta,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Calentamiento — {paciente.get('nombre', '')}",
        author="Nutrición Deportiva",
    )

    elementos = []

    # --- Membrete institucional (logo + datos del profesional) ---
    elementos.extend(crear_membrete())

    # --- Encabezado ---
    elementos.append(Paragraph("REPORTE DE CALENTAMIENTO", estilos["titulo"]))
    elementos.append(
        Paragraph(
            "Nutrición Deportiva — Calentamiento dinámico previo al entrenamiento",
            estilos["subtitulo"],
        )
    )

    # --- Datos del paciente ---
    elementos.append(_tabla_datos(estilos, paciente, momento))
    elementos.append(Spacer(1, 0.12 * inch))

    # --- Resumen en orden ---
    elementos.append(Paragraph("CALENTAMIENTO EN ORDEN", estilos["seccion"]))
    if not plan:
        elementos.append(
            Paragraph("No hay ejercicios de calentamiento.", estilos["normal"])
        )
    else:
        elementos.append(_tabla_resumen(estilos, plan))
        duraciones = [_duracion_segundos(f.get("duracion")) for f in plan]
        if duraciones and all(d is not None for d in duraciones):
            total = sum(duraciones)
            elementos.append(
                Paragraph(
                    f"Duración total aproximada: {int(round(total / 60))} min.",
                    estilos["normal"],
                )
            )

    # --- Detalle por ejercicio ---
    elementos.append(Paragraph("DETALLE Y FORMA DE REALIZACIÓN", estilos["seccion"]))
    for ficha in plan:
        elementos.extend(_bloque_detalle(estilos, ficha))
        elementos.append(Spacer(1, 0.14 * inch))

    # --- Pie ---
    elementos.append(Spacer(1, 0.2 * inch))
    elementos.append(
        Paragraph(
            "Este reporte es informativo y no sustituye la valoración de un "
            "profesional de la salud. Realiza el calentamiento de forma "
            "progresiva, sin rebotes y respetando la técnica descrita.",
            estilos["pie"],
        )
    )

    doc.build(elementos)
    return ruta
