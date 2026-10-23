"""
Reporte imprimible de equivalentes (cuadro dietosintético + distribución).

Membrete institucional + datos del paciente + cuadro dietosintético,
equivalentes por subgrupo SMAE-5 y distribución por día y tiempo.
"""
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
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

NEGRO = colors.HexColor("#121212")
GRIS = colors.HexColor("#2C2C2C")
NARANJA = colors.HexColor("#FF6D00")
GRIS_TEXTO = colors.HexColor("#B0B0B0")
FONDO = colors.HexColor("#F2F2F2")


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
            spaceBefore=10, spaceAfter=4, keepWithNext=1,
        ),
        "normal": ParagraphStyle(
            "normal", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=12, textColor=NEGRO,
        ),
        "etiqueta": ParagraphStyle(
            "etiqueta", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=colors.HexColor("#444444"),
        ),
        "centro": ParagraphStyle(
            "centro", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, leading=10, textColor=colors.white, alignment=TA_CENTER,
        ),
        "celda": ParagraphStyle(
            "celda", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=10, textColor=NEGRO,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=8, leading=10, textColor=GRIS_TEXTO, alignment=TA_CENTER,
        ),
    }


def ruta_temporal_pdf(nombre_paciente):
    """Ruta del PDF temporal de equivalentes para un paciente."""
    return _ruta_temporal_pdf("Equivalentes", nombre_paciente)


def _estilo_base_tabla(estilos, alineacion="CENTER"):
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), GRIS),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, GRIS),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FONDO]),
        ]
    )


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


def _cuadro_dietosintetico(estilos, plan):
    gramos = plan.get("gramos") or {}
    peso = plan.get("peso") or 0
    filas = [
        [
            Paragraph("Macronutriente", estilos["centro"]),
            Paragraph("%", estilos["centro"]),
            Paragraph("kcal", estilos["centro"]),
            Paragraph("Gramos", estilos["centro"]),
            Paragraph("g/kg peso", estilos["centro"]),
        ]
    ]
    for etiqueta, pct, gramo in (
        ("Carbohidratos", plan.get("pct_carb", 0), gramos.get("carbohidratos", 0)),
        ("Proteína", plan.get("pct_prot", 0), gramos.get("proteina", 0)),
        ("Grasa", plan.get("pct_grasa", 0), gramos.get("grasa", 0)),
    ):
        kcal = gramo * (4 if etiqueta != "Grasa" else 9)
        filas.append(
            [
                Paragraph(etiqueta, estilos["celda"]),
                Paragraph(f"{pct:g}", estilos["celda"]),
                Paragraph(f"{kcal:.1f}", estilos["celda"]),
                Paragraph(f"{gramo:.1f}", estilos["celda"]),
                Paragraph(f"{gramo / peso:.2f}" if peso else "-", estilos["celda"]),
            ]
        )
    total_g = (
        gramos.get("carbohidratos", 0)
        + gramos.get("proteina", 0)
        + gramos.get("grasa", 0)
    )
    filas.append(
        [
            Paragraph("TOTAL", estilos["centro"]),
            Paragraph(
                f"{plan.get('pct_carb', 0) + plan.get('pct_prot', 0) + plan.get('pct_grasa', 0):g}",
                estilos["celda"],
            ),
            Paragraph(f"{plan.get('tee', 0):.1f}", estilos["celda"]),
            Paragraph(f"{total_g:.1f}", estilos["celda"]),
            Paragraph("-", estilos["celda"]),
        ]
    )
    tabla = Table(
        filas,
        colWidths=[1.7 * inch, 0.7 * inch, 1.1 * inch, 1.1 * inch, 1.4 * inch],
        hAlign="LEFT",
    )
    estilo = _estilo_base_tabla(estilos)
    estilo.add("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8E8E8"))
    estilo.add("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")
    tabla.setStyle(estilo)
    return tabla


def _tabla_equivalentes(estilos, filas_equivalentes):
    encabezados = [
        "Grupo", "Subgrupo", "kcal/u", "Eq.", "kcal", "Prot (g)",
        "Líp (g)", "HC (g)",
    ]
    filas = [[Paragraph(t, estilos["centro"]) for t in encabezados]]
    for grupo, subgrupo, kcal, prot, lip, hc, eq in filas_equivalentes:
        nombre = grupo if subgrupo == "-" else f"{grupo} ({subgrupo})"
        filas.append(
            [
                Paragraph(_escapar(nombre), estilos["celda"]),
                Paragraph(_escapar(subgrupo), estilos["celda"]),
                Paragraph(f"{kcal:g}", estilos["celda"]),
                Paragraph(f"{eq:g}", estilos["celda"]),
                Paragraph(f"{kcal * eq:.1f}", estilos["celda"]),
                Paragraph(f"{prot * eq:.1f}", estilos["celda"]),
                Paragraph(f"{lip * eq:.1f}", estilos["celda"]),
                Paragraph(f"{hc * eq:.1f}", estilos["celda"]),
            ]
        )
    tabla = Table(
        filas,
        colWidths=[1.6 * inch, 1.25 * inch, 0.55 * inch, 0.5 * inch,
                   0.65 * inch, 0.65 * inch, 0.65 * inch, 0.6 * inch],
        repeatRows=1,
        hAlign="LEFT",
    )
    tabla.setStyle(_estilo_base_tabla(estilos))
    return tabla


def _tabla_distribucion(estilos, dia, info, filas_equivalentes):
    nombres = info.get("nombres") or []
    valores = info.get("valores") or []
    num_t = max(len(nombres), 1)
    encabezados = ["Subgrupo"] + list(nombres) + ["Total"]
    filas = [[Paragraph(t, estilos["centro"]) for t in encabezados]]
    for idx, (grupo, subgrupo, *_resto) in enumerate(filas_equivalentes):
        nombre = grupo if subgrupo == "-" else f"{grupo} ({subgrupo})"
        fila_valores = valores[idx] if idx < len(valores) else []
        celdas = [Paragraph(_escapar(nombre), estilos["celda"])]
        suma = 0.0
        for t in range(num_t):
            try:
                valor = float(fila_valores[t]) if t < len(fila_valores) else 0.0
            except (TypeError, ValueError):
                valor = 0.0
            suma += valor
            celdas.append(Paragraph(f"{valor:g}", estilos["celda"]))
        celdas.append(Paragraph(f"{suma:g}", estilos["celda"]))
        filas.append(celdas)

    ancho_tiempo = 0.85
    tabla = Table(
        filas,
        colWidths=[2.2 * inch] + [ancho_tiempo * inch] * num_t + [0.7 * inch],
        repeatRows=1,
        hAlign="LEFT",
    )
    tabla.setStyle(_estilo_base_tabla(estilos))
    return tabla


def generar_pdf_equivalentes(ruta, paciente, plan, momento_impresion=None):
    """
    Genera el PDF del plan de equivalentes.

    plan: dict con tee, peso, pct_*, gramos, totales, filas_equivalentes
    y dias ({día: {"nombres": [...], "valores": [[...]]}}).
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
        title=f"Equivalentes — {paciente.get('nombre', '')}",
        author="Nutrición Deportiva",
    )

    elementos = []
    elementos.extend(crear_membrete())

    elementos.append(
        Paragraph("CUADRO DIETOSINTÉTICO Y EQUIVALENTES", estilos["titulo"])
    )
    elementos.append(
        Paragraph(
            "Nutrición Deportiva — Equivalentes SMAE-5 y distribución por tiempos",
            estilos["subtitulo"],
        )
    )
    elementos.append(_tabla_paciente(estilos, paciente, momento))
    elementos.append(Spacer(1, 0.12 * inch))

    # --- Cuadro dietosintético ---
    elementos.append(Paragraph("CUADRO DIETOSINTÉTICO", estilos["seccion"]))
    elementos.append(_cuadro_dietosintetico(estilos, plan))

    # --- Equivalentes por subgrupo ---
    elementos.append(Paragraph("EQUIVALENTES POR SUBGRUPO", estilos["seccion"]))
    filas_equivalentes = plan.get("filas_equivalentes") or []
    if filas_equivalentes:
        elementos.append(_tabla_equivalentes(estilos, filas_equivalentes))
    else:
        elementos.append(
            Paragraph("No hay equivalentes calculados.", estilos["normal"])
        )

    # --- Distribución por día ---
    elementos.append(
        Paragraph("DISTRIBUCIÓN DE EQUIVALENTES POR DÍA Y TIEMPO", estilos["seccion"])
    )
    dias = plan.get("dias") or {}
    if dias:
        for dia, info in dias.items():
            elementos.append(Paragraph(_escapar(dia), estilos["seccion"]))
            elementos.append(_tabla_distribucion(estilos, dia, info, filas_equivalentes))
            elementos.append(Spacer(1, 0.12 * inch))
    else:
        elementos.append(
            Paragraph("No hay distribución por tiempos.", estilos["normal"])
        )

    elementos.append(PageBreak())
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


__all__ = [
    "abrir_para_imprimir",
    "calcular_edad",
    "generar_pdf_equivalentes",
    "nombre_pdf",
    "ruta_temporal_pdf",
]
