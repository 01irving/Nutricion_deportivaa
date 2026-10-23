"""
Reporte imprimible de menús semanales.

Membrete institucional + datos del paciente + platillos y alimentos por
tiempo de comida, con totales nutrimentales por tiempo y por día.
"""
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
        "tiempo": ParagraphStyle(
            "tiempo", parent=base["Heading3"], fontName="Helvetica-Bold",
            fontSize=10, leading=13, textColor=NEGRO, spaceBefore=6,
            spaceAfter=2, keepWithNext=1,
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
    """Ruta del PDF temporal de menús para un paciente."""
    return _ruta_temporal_pdf("Menus", nombre_paciente)


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


def _estilo_base_tabla(estilos):
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


def _tabla_alimentos(estilos, registros):
    encabezados = [
        "Alimento", "Grupo", "Eq.", "kcal", "Prot (g)", "HC (g)", "Líp (g)",
    ]
    filas = [[Paragraph(t, estilos["centro"]) for t in encabezados]]
    for reg in registros:
        filas.append(
            [
                Paragraph(_escapar(reg.get("alimento", "")), estilos["celda"]),
                Paragraph(_escapar(reg.get("grupo", "")), estilos["celda"]),
                Paragraph(f"{reg.get('eq_cantidad', 0):g}", estilos["celda"]),
                Paragraph(f"{reg.get('energia_kcal', 0):.1f}", estilos["celda"]),
                Paragraph(f"{reg.get('proteina_g', 0):.1f}", estilos["celda"]),
                Paragraph(f"{reg.get('hc_g', 0):.1f}", estilos["celda"]),
                Paragraph(f"{reg.get('lipidos_g', 0):.1f}", estilos["celda"]),
            ]
        )
    tabla = Table(
        filas,
        colWidths=[1.85 * inch, 1.15 * inch, 0.5 * inch, 0.65 * inch,
                   0.65 * inch, 0.6 * inch, 0.6 * inch],
        repeatRows=1,
        hAlign="LEFT",
    )
    tabla.setStyle(_estilo_base_tabla(estilos))
    return tabla


def _tabla_totales(estilos, etiqueta, totales):
    filas = [
        [
            Paragraph("Totales", estilos["centro"]),
            Paragraph("kcal", estilos["centro"]),
            Paragraph("Prot (g)", estilos["centro"]),
            Paragraph("HC (g)", estilos["centro"]),
            Paragraph("Líp (g)", estilos["centro"]),
            Paragraph("Fibra (g)", estilos["centro"]),
        ],
        [
            Paragraph(_escapar(etiqueta), estilos["celda"]),
            Paragraph(f"{totales['energia_kcal']:.1f}", estilos["celda"]),
            Paragraph(f"{totales['proteina_g']:.1f}", estilos["celda"]),
            Paragraph(f"{totales['hc_g']:.1f}", estilos["celda"]),
            Paragraph(f"{totales['lipidos_g']:.1f}", estilos["celda"]),
            Paragraph(f"{totales['fibra_g']:.1f}", estilos["celda"]),
        ],
    ]
    tabla = Table(
        filas,
        colWidths=[1.85 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch,
                   0.85 * inch, 0.9 * inch],
        hAlign="LEFT",
    )
    estilo = _estilo_base_tabla(estilos)
    estilo.add("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E8E8E8"))
    estilo.add("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold")
    tabla.setStyle(estilo)
    return tabla


def generar_pdf_menus(ruta, paciente, tiempos, dias, momento_impresion=None):
    """
    Genera el PDF del menú semanal.

    tiempos: lista de nombres de tiempo de comida.
    dias: dict día -> {"platillos": {idx: texto}, "alimentos": {idx: [regs]}}.
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
        title=f"Menú — {paciente.get('nombre', '')}",
        author="Nutrición Deportiva",
    )

    elementos = []
    elementos.extend(crear_membrete())

    elementos.append(Paragraph("MENÚ SEMANAL", estilos["titulo"]))
    elementos.append(
        Paragraph(
            "Nutrición Deportiva — Plan alimentario por tiempos de comida",
            estilos["subtitulo"],
        )
    )
    elementos.append(_tabla_paciente(estilos, paciente, momento))
    elementos.append(Spacer(1, 0.12 * inch))

    for dia, info in (dias or {}).items():
        elementos.append(Paragraph(_escapar(dia), estilos["seccion"]))
        platillos = info.get("platillos") or {}
        alimentos = info.get("alimentos") or {}

        for t_idx, nombre_tiempo in enumerate(tiempos or []):
            registros = alimentos.get(t_idx) or alimentos.get(str(t_idx)) or []
            platillo = platillos.get(t_idx) or platillos.get(str(t_idx)) or ""
            encabezado = nombre_tiempo
            if platillo:
                encabezado = f"{nombre_tiempo} — {platillo}"
            elementos.append(Paragraph(_escapar(encabezado), estilos["tiempo"]))

            if registros:
                elementos.append(_tabla_alimentos(estilos, registros))
            else:
                elementos.append(
                    Paragraph("Sin alimentos registrados.", estilos["normal"])
                )

            totales = {clave: 0.0 for clave in (
                "energia_kcal", "proteina_g", "hc_g", "lipidos_g", "fibra_g"
            )}
            for reg in registros:
                eq = reg.get("eq_cantidad", 1.0) or 1.0
                for clave in totales:
                    try:
                        totales[clave] += float(reg.get(clave) or 0) * eq
                    except (TypeError, ValueError):
                        pass
            elementos.append(Spacer(1, 0.05 * inch))
            elementos.append(_tabla_totales(estilos, "Total del tiempo", totales))
            elementos.append(Spacer(1, 0.12 * inch))

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
    "generar_pdf_menus",
    "nombre_pdf",
    "ruta_temporal_pdf",
]
