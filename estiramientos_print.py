"""
Generación del reporte imprimible de estiramientos.

Exporta a PDF con ReportLab: membrete institucional, datos del paciente,
resumen de la selección y el detalle de cada estiramiento con su
ilustración, forma de ejecución, músculos estirados, variantes,
observaciones y advertencias.
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

__all__ = [
    "abrir_para_imprimir",
    "calcular_edad",
    "generar_pdf_estiramientos",
    "nombre_pdf",
    "ruta_temporal_pdf",
]

NEGRO = colors.HexColor("#121212")
GRIS_OSCURO = colors.HexColor("#1E1E1E")
GRIS = colors.HexColor("#2C2C2C")
NARANJA = colors.HexColor("#FF6D00")
GRIS_TEXTO = colors.HexColor("#B0B0B0")

RUTA_IMAGENES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "estiramientos_img"
)

MAX_ANCHO_IMAGEN = 3.1 * inch
MAX_ALTO_IMAGEN = 3.4 * inch


def _escapar(texto):
    """Escapa caracteres XML para ReportLab."""
    if texto is None:
        return ""
    texto = str(texto)
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _multi(texto):
    """Escapa el texto y conserva los saltos de línea como <br/>."""
    return _escapar(texto).replace("\n", "<br/>")


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
    """Ruta del PDF temporal de estiramientos para un paciente."""
    return _ruta_temporal_pdf("Estiramientos", nombre_paciente)


def _imagen_flowable(nombre_imagen):
    """Ilustración del ejercicio ajustada a la caja de la página."""
    if not nombre_imagen:
        return None
    ruta = os.path.join(RUTA_IMAGENES, f"{nombre_imagen}.png")
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


def _tabla_resumen(estilos, seleccion):
    resumen = [
        [
            Paragraph("#", estilos["centro"]),
            Paragraph("Estiramiento", estilos["centro"]),
            Paragraph("Grupo", estilos["centro"]),
            Paragraph("Momento", estilos["centro"]),
            Paragraph("Duración", estilos["centro"]),
        ]
    ]
    for i, reg in enumerate(seleccion, start=1):
        resumen.append(
            [
                Paragraph(str(i), estilos["celda"]),
                Paragraph(_escapar(reg.get("nombre", "")), estilos["celda"]),
                Paragraph(_escapar(reg.get("grupo", "")), estilos["celda"]),
                Paragraph(_escapar(reg.get("momento", "")), estilos["celda"]),
                Paragraph(_escapar(reg.get("duracion") or "-"), estilos["celda"]),
            ]
        )
    tabla = Table(
        resumen,
        colWidths=[0.3 * inch, 2.5 * inch, 1.1 * inch, 1.7 * inch, 0.8 * inch],
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


def _bloque_detalle(estilos, reg, ejercicio):
    """Flowables del detalle de un estiramiento (texto + ilustración)."""
    bloque = []

    nombre = ejercicio.get("nombre") if ejercicio else reg.get("nombre", "")
    grupo = ejercicio.get("grupo") if ejercicio else reg.get("grupo", "")
    bloque.append(Paragraph(_escapar(nombre), estilos["ejercicio"]))

    meta = []
    if grupo:
        meta.append(f"Grupo: {_escapar(grupo)}")
    if reg.get("momento"):
        meta.append(f"Momento: {_escapar(reg['momento'])}")
    if reg.get("duracion"):
        meta.append(f"Duración: {_escapar(reg['duracion'])}")
    if meta:
        bloque.append(Paragraph(" | ".join(meta), estilos["normal"]))

    imagen = _imagen_flowable(
        ejercicio.get("imagen") if ejercicio else None
    )
    if imagen is not None:
        bloque.append(imagen)

    if ejercicio:
        secciones = (
            ("Cómo realizarlo", ejercicio.get("descripcion")),
            ("Músculos estirados", ejercicio.get("musculos")),
            ("Variantes", ejercicio.get("variantes")),
            ("Observaciones", ejercicio.get("observaciones")),
            ("Atención", ejercicio.get("atencion")),
            ("Rótulos de la ilustración", ejercicio.get("rotulos")),
        )
        for titulo, contenido in secciones:
            if not contenido:
                continue
            bloque.append(
                Paragraph(
                    f"<b>{titulo}:</b> {_multi(contenido)}", estilos["normal"]
                )
            )
        if ejercicio.get("pagina_original"):
            bloque.append(
                Paragraph(
                    f"<i>Fuente: Estiramientos por grupo muscular, "
                    f"pág. {ejercicio['pagina_original']}.</i>",
                    estilos["normal"],
                )
            )

    if reg.get("notas"):
        bloque.append(
            Paragraph(f"<b>Notas:</b> {_multi(reg['notas'])}", estilos["normal"])
        )
    return bloque


def generar_pdf_estiramientos(
    ruta, paciente, seleccion, momento_impresion=None, estiramientos_por_id=None
):
    """
    Genera el PDF del reporte de estiramientos.

    paciente: dict con nombre, fecha_nacimiento/dob, direccion, telefono.
    seleccion: lista de dicts con id_estiramiento, nombre, grupo, momento,
               duracion y notas.
    estiramientos_por_id: dict con la ficha completa del catálogo.
    """
    estilos = _estilos()
    momento = momento_impresion or datetime.now()
    catalogo = estiramientos_por_id or {}

    doc = SimpleDocTemplate(
        ruta,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Estiramientos — {paciente.get('nombre', '')}",
        author="Nutrición Deportiva",
    )

    elementos = []

    # --- Membrete institucional (logo + datos del profesional) ---
    elementos.extend(crear_membrete())

    # --- Encabezado ---
    elementos.append(Paragraph("REPORTE DE ESTIRAMIENTOS", estilos["titulo"]))
    elementos.append(
        Paragraph(
            "Nutrición Deportiva — Estiramientos por grupo muscular",
            estilos["subtitulo"],
        )
    )

    # --- Datos del paciente ---
    elementos.append(_tabla_datos(estilos, paciente, momento))
    elementos.append(Spacer(1, 0.12 * inch))

    # --- Resumen de la selección ---
    elementos.append(Paragraph("ESTIRAMIENTOS SELECCIONADOS", estilos["seccion"]))
    if not seleccion:
        elementos.append(
            Paragraph("No hay estiramientos seleccionados.", estilos["normal"])
        )
    else:
        elementos.append(_tabla_resumen(estilos, seleccion))

    # --- Detalle por estiramiento ---
    elementos.append(Paragraph("DETALLE Y FORMA DE REALIZACIÓN", estilos["seccion"]))
    for reg in seleccion:
        ejercicio = catalogo.get(reg.get("id_estiramiento"))
        elementos.extend(_bloque_detalle(estilos, reg, ejercicio))
        elementos.append(Spacer(1, 0.14 * inch))

    # --- Pie ---
    elementos.append(Spacer(1, 0.2 * inch))
    elementos.append(
        Paragraph(
            "Este reporte es informativo y no sustituye la valoración de un "
            "profesional de la salud. Realiza los estiramientos de forma "
            "suave, sin rebotes y respetando la técnica descrita.",
            estilos["pie"],
        )
    )

    doc.build(elementos)
    return ruta
