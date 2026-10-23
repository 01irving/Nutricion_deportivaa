"""
Generación del reporte imprimible de suplementos.

Exporta a PDF con ReportLab: datos del paciente (nombre, edad, dirección),
fecha de impresión y el detalle de cada suplemento (posología, para qué
sirve y cuidados).
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

from impresion_utils import (
    abrir_para_imprimir,
    calcular_edad,
    crear_membrete,
    nombre_pdf,
)
from impresion_utils import ruta_temporal_pdf as _ruta_temporal_pdf

__all__ = [
    "abrir_para_imprimir",
    "calcular_edad",
    "generar_pdf_suplementos",
    "nombre_pdf",
    "ruta_temporal_pdf",
]


NEGRO = colors.HexColor("#121212")
GRIS_OSCURO = colors.HexColor("#1E1E1E")
GRIS = colors.HexColor("#2C2C2C")
NEON = colors.HexColor("#C6FF00")
NARANJA = colors.HexColor("#FF6D00")
BLANCO = colors.HexColor("#F5F5F5")
GRIS_TEXTO = colors.HexColor("#B0B0B0")


def _escapar(texto):
    """Escapa caracteres XML para ReportLab."""
    if texto is None:
        return ""
    texto = str(texto)
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return texto


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=18, leading=22, textColor=NEON, spaceAfter=2,
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
        "suplemento": ParagraphStyle(
            "suplemento", parent=base["Heading3"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, textColor=NEGRO, spaceAfter=2,
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
            fontSize=9, leading=12, textColor=colors.white, alignment=TA_CENTER,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=8, leading=10, textColor=GRIS_TEXTO, alignment=TA_CENTER,
        ),
    }


def _nombre_archivo(nombre_paciente):
    return nombre_pdf("Suplementos", nombre_paciente)


def ruta_temporal_pdf(nombre_paciente):
    """Ruta del PDF temporal de suplementos para un paciente."""
    return _ruta_temporal_pdf("Suplementos", nombre_paciente)


def generar_pdf_suplementos(
    ruta, paciente, seleccion, momento_impresion=None, supplements_por_id=None
):
    """
    Genera el PDF del reporte de suplementos.

    paciente: dict con nombre, fecha_nacimiento/dob, direccion, telefono, etc.
    seleccion: lista de dicts con nombre, categoria, momento, dosis, notas.
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
        title=f"Suplementos — {paciente.get('nombre', '')}",
        author="Nutrición Deportiva",
    )

    elementos = []

    # --- Membrete institucional (logo + datos del profesional) ---
    elementos.extend(crear_membrete())

    # --- Encabezado ---
    elementos.append(Paragraph("REPORTE DE SUPLEMENTOS", estilos["titulo"]))
    elementos.append(
        Paragraph(
            "Nutrición Deportiva — Plan de suplementación", estilos["subtitulo"]
        )
    )

    # --- Datos del paciente ---
    fecha_nac = paciente.get("fecha_nacimiento") or paciente.get("dob") or ""
    edad = calcular_edad(fecha_nac)
    datos = [
        ("Nombre", paciente.get("nombre") or "-"),
        ("Edad", f"{edad} años" if edad is not None else "-"),
        ("Dirección", paciente.get("direccion") or "-"),
        ("Teléfono", paciente.get("telefono") or "-"),
        ("Fecha de impresión", momento.strftime("%d/%m/%Y %H:%M")),
    ]
    tabla_datos = Table(
        [
            [Paragraph(f"{etiqueta}:", estilos["etiqueta"]),
             Paragraph(_escapar(valor), estilos["normal"])]
            for etiqueta, valor in datos
        ],
        colWidths=[1.6 * inch, 4.6 * inch],
        hAlign="LEFT",
    )
    tabla_datos.setStyle(
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
    elementos.append(tabla_datos)

    # --- Resumen de la selección ---
    elementos.append(Paragraph("SUPLEMENTOS SELECCIONADOS", estilos["seccion"]))
    if not seleccion:
        elementos.append(
            Paragraph("No hay suplementos seleccionados.", estilos["normal"])
        )
    else:
        resumen = [
            [
                Paragraph("Suplemento", estilos["centro"]),
                Paragraph("Categoría", estilos["centro"]),
                Paragraph("Momento", estilos["centro"]),
                Paragraph("Dosis", estilos["centro"]),
            ]
        ]
        for reg in seleccion:
            resumen.append(
                [
                    Paragraph(_escapar(reg.get("nombre", "")), estilos["normal"]),
                    Paragraph(_escapar(reg.get("categoria", "")), estilos["normal"]),
                    Paragraph(_escapar(reg.get("momento", "")), estilos["normal"]),
                    Paragraph(_escapar(reg.get("dosis") or "-"), estilos["normal"]),
                ]
            )
        tabla_resumen = Table(
            resumen,
            colWidths=[1.7 * inch, 2.1 * inch, 1.7 * inch, 0.9 * inch],
            repeatRows=1,
            hAlign="LEFT",
        )
        tabla_resumen.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GRIS_OSCURO),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, GRIS),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#F2F2F2")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        elementos.append(tabla_resumen)

    # --- Detalle por suplemento ---
    elementos.append(Paragraph("DETALLE Y POSOLOGÍA", estilos["seccion"]))
    catalogo = supplements_por_id or {}
    for reg in seleccion:
        bloque = [Paragraph(_escapar(reg.get("nombre", "")), estilos["suplemento"])]
        meta = []
        if reg.get("categoria"):
            meta.append(f"Categoría: {_escapar(reg['categoria'])}")
        if reg.get("momento"):
            meta.append(f"Momento: {_escapar(reg['momento'])}")
        if reg.get("dosis"):
            meta.append(f"Dosis: {_escapar(reg['dosis'])}")
        if meta:
            bloque.append(Paragraph(" | ".join(meta), estilos["normal"]))

        sup = catalogo.get(reg.get("id_suplemento"))
        if sup:
            bloque.append(
                Paragraph(
                    f"<b>Posología:</b> {_escapar(sup.get('posologia', ''))}",
                    estilos["normal"],
                )
            )
            bloque.append(
                Paragraph(
                    f"<b>Para qué sirve:</b> "
                    f"{_escapar(sup.get('para_que_sirve', ''))}",
                    estilos["normal"],
                )
            )
            bloque.append(
                Paragraph(
                    f"<b>Cuidados:</b> {_escapar(sup.get('cuidados', ''))}",
                    estilos["normal"],
                )
            )
        elif reg.get("posologia"):
            bloque.append(
                Paragraph(
                    f"<b>Posología:</b> {_escapar(reg['posologia'])}",
                    estilos["normal"],
                )
            )
        if reg.get("notas"):
            bloque.append(
                Paragraph(
                    f"<b>Notas:</b> {_escapar(reg['notas'])}", estilos["normal"]
                )
            )
        # Se agregan los flowables por separado: KeepTogether puede descartar
        # contenido cuando el bloque no cabe completo en la página.
        elementos.extend(bloque)
        elementos.append(Spacer(1, 0.12 * inch))

    # --- Pie ---
    elementos.append(Spacer(1, 0.2 * inch))
    elementos.append(
        Paragraph(
            "Este reporte es informativo y no sustituye la valoración de un "
            "profesional de la salud. Verifica dosis, interacciones y "
            "contraindicaciones antes de iniciar la suplementación.",
            estilos["pie"],
        )
    )

    doc.build(elementos)
    return ruta
