"""
Reporte imprimible de antecedentes (patológicos y no patológicos).

Membrete institucional + datos del paciente + detalle de antecedentes.
"""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from antecedentes_defs import (
    SECCION_NOPATOLOGICOS_HABITOS,
    SECCION_NOPATOLOGICOS_TEXTO,
    SECCION_PATOLOGICOS,
)
from impresion_utils import (
    abrir_para_imprimir,
    calcular_edad,
    crear_membrete,
    nombre_pdf,
)
from impresion_utils import ruta_temporal_pdf as _ruta_temporal_pdf

NEGRO = colors.HexColor("#121212")
GRIS = colors.HexColor("#2C2C2C")
NARANJA = colors.HexColor("#FF6D00")
GRIS_TEXTO = colors.HexColor("#B0B0B0")


def _escapar(texto):
    if texto is None:
        return ""
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=17, leading=21, textColor=NEGRO, spaceAfter=2,
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
        "campo": ParagraphStyle(
            "campo", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=NEGRO, spaceAfter=1,
        ),
        "valor": ParagraphStyle(
            "valor", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=13, textColor=NEGRO, alignment=TA_LEFT,
        ),
        "etiqueta": ParagraphStyle(
            "etiqueta", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=colors.HexColor("#444444"),
        ),
        "centro": ParagraphStyle(
            "centro", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=colors.white, alignment=TA_CENTER,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=8, leading=10, textColor=GRIS_TEXTO, alignment=TA_CENTER,
        ),
    }


def ruta_temporal_pdf(nombre_paciente):
    """Ruta del PDF temporal de antecedentes para un paciente."""
    return _ruta_temporal_pdf("Antecedentes", nombre_paciente)


def _tabla_paciente(estilos, paciente, momento):
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
                Paragraph(_escapar(valor), estilos["valor"]),
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


def _bloque_campo(estilos, etiqueta, valor):
    return [
        Paragraph(_escapar(etiqueta), estilos["campo"]),
        Paragraph(_escapar(valor) if valor else "-", estilos["valor"]),
        Spacer(1, 0.10 * inch),
    ]


def generar_pdf_antecedentes(ruta, paciente, antecedentes, momento_impresion=None):
    """
    Genera el PDF con la historia de antecedentes del paciente.

    paciente: dict con nombre, fecha_nacimiento/dob, direccion, telefono.
    antecedentes: dict con los campos pat_* y nopat_*.
    """
    estilos = _estilos()
    momento = momento_impresion or datetime.now()
    datos = antecedentes or {}

    doc = SimpleDocTemplate(
        ruta,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Antecedentes — {paciente.get('nombre', '')}",
        author="Nutrición Deportiva",
    )

    elementos = []

    # --- Membrete institucional (logo + datos del profesional) ---
    elementos.extend(crear_membrete())

    # --- Encabezado ---
    elementos.append(Paragraph("HISTORIA CLÍNICA - ANTECEDENTES", estilos["titulo"]))
    elementos.append(
        Paragraph(
            "Nutrición Deportiva — Antecedentes patológicos y no patológicos",
            estilos["subtitulo"],
        )
    )

    # --- Datos del paciente ---
    elementos.append(_tabla_paciente(estilos, paciente, momento))
    elementos.append(Spacer(1, 0.12 * inch))

    # --- Antecedentes patológicos ---
    elementos.append(Paragraph("ANTECEDENTES PATOLÓGICOS", estilos["seccion"]))
    for clave, etiqueta in SECCION_PATOLOGICOS:
        elementos.extend(_bloque_campo(estilos, etiqueta, datos.get(clave)))

    # --- Antecedentes no patológicos: hábitos ---
    elementos.append(Paragraph("ANTECEDENTES NO PATOLÓGICOS", estilos["seccion"]))
    elementos.append(Paragraph("Hábitos", estilos["campo"]))
    filas = [
        [
            Paragraph(_escapar(etiqueta), estilos["centro"]),
            Paragraph(
                _escapar(datos.get(clave)) if datos.get(clave) else "-",
                estilos["valor"],
            ),
        ]
        for clave, etiqueta in SECCION_NOPATOLOGICOS_HABITOS
    ]
    tabla_habitos = Table(
        filas, colWidths=[1.6 * inch, 4.6 * inch], hAlign="LEFT"
    )
    tabla_habitos.setStyle(
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
    elementos.append(tabla_habitos)
    elementos.append(Spacer(1, 0.10 * inch))

    for clave, etiqueta in SECCION_NOPATOLOGICOS_TEXTO:
        elementos.extend(_bloque_campo(estilos, etiqueta, datos.get(clave)))

    # --- Pie ---
    elementos.append(Spacer(1, 0.2 * inch))
    elementos.append(
        Paragraph(
            "Este documento es informativo y no sustituye la valoración de un "
            "profesional de la salud.",
            estilos["pie"],
        )
    )

    doc.build(elementos)
    return ruta


def abrir_para_imprimir_antecedentes(ruta):
    abrir_para_imprimir(ruta)


__all__ = [
    "abrir_para_imprimir",
    "calcular_edad",
    "generar_pdf_antecedentes",
    "nombre_pdf",
    "ruta_temporal_pdf",
]
