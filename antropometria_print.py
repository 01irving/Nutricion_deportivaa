"""
Reportes imprimibles de antropometría deportiva.

Incluye el somatotipo Heath-Carter y el fraccionamiento antropométrico
del peso en 5 componentes (Ross & Kerr), con membrete institucional,
datos del paciente, resultados, gráficas y medidas registradas.
"""
import math
from datetime import datetime

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
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
GRIS_CLARO = colors.HexColor("#EEEEEE")
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


def _numero(valor):
    if valor is None:
        return "-"
    if isinstance(valor, (int, float)):
        return f"{valor:g}"
    return _escapar(valor)


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
            fontSize=8.5, leading=11, textColor=colors.HexColor("#444444"),
        ),
        "centro": ParagraphStyle(
            "centro", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, leading=10, textColor=colors.white, alignment=TA_CENTER,
        ),
        "celda": ParagraphStyle(
            "celda", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=10, textColor=NEGRO,
        ),
        "celda_bold": ParagraphStyle(
            "celda_bold", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, leading=10, textColor=NEGRO,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=8, leading=10, textColor=GRIS_TEXTO, alignment=TA_CENTER,
        ),
    }


def ruta_temporal_pdf_somatotipo(nombre_paciente):
    return _ruta_temporal_pdf("Somatotipo", nombre_paciente)


def ruta_temporal_pdf_componentes(nombre_paciente):
    return _ruta_temporal_pdf("5Componentes", nombre_paciente)


def _pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS_TEXTO)
    canvas.drawString(
        0.6 * inch, 0.35 * inch,
        "Reporte generado automáticamente por Nutrición Deportiva",
    )
    canvas.drawRightString(
        letter[0] - 0.6 * inch, 0.35 * inch, f"Página {doc.page}"
    )
    canvas.restoreState()


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


def _tabla_medidas(estilos, medidas):
    pares = list(medidas or [])
    filas = []
    for i in range(0, len(pares), 2):
        izq = pares[i]
        der = pares[i + 1] if i + 1 < len(pares) else ("", "")
        filas.append(
            [
                Paragraph(_escapar(izq[0]), estilos["etiqueta"]),
                Paragraph(_numero(izq[1]), estilos["celda"]),
                Paragraph(_escapar(der[0]), estilos["etiqueta"]),
                Paragraph(_numero(der[1]), estilos["celda"]),
            ]
        )
    if not filas:
        return Spacer(1, 1)
    tabla = Table(
        filas,
        colWidths=[1.6 * inch, 0.8 * inch, 1.6 * inch, 0.8 * inch],
        hAlign="LEFT",
    )
    tabla.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, FONDO]),
            ]
        )
    )
    return tabla


def _tabla_resultados_somatotipo(estilos, res):
    filas = [
        [
            Paragraph("Parámetro", estilos["centro"]),
            Paragraph("Resultado", estilos["centro"]),
        ],
        [
            Paragraph("Endomorfo", estilos["celda"]),
            Paragraph(
                f"{res['endo']:.1f} ({res.get('nivel_endo', '-')})",
                estilos["celda_bold"],
            ),
        ],
        [
            Paragraph("Mesomorfo", estilos["celda"]),
            Paragraph(
                f"{res['meso']:.1f} ({res.get('nivel_meso', '-')})",
                estilos["celda_bold"],
            ),
        ],
        [
            Paragraph("Ectomorfo", estilos["celda"]),
            Paragraph(
                f"{res['ecto']:.1f} ({res.get('nivel_ecto', '-')})",
                estilos["celda_bold"],
            ),
        ],
        [
            Paragraph("Coordenada X", estilos["celda"]),
            Paragraph(f"{res['x']:+.1f}", estilos["celda"]),
        ],
        [
            Paragraph("Coordenada Y", estilos["celda"]),
            Paragraph(f"{res['y']:+.1f}", estilos["celda"]),
        ],
        [
            Paragraph("HWR", estilos["celda"]),
            Paragraph(
                f"{res['hwr']:.2f} ({_escapar(res.get('rama', '-'))})",
                estilos["celda"],
            ),
        ],
        [
            Paragraph("Suma 3 pliegues", estilos["celda"]),
            Paragraph(
                f"{res['sum3']:.1f} mm (corregida {res['xc']:.1f})",
                estilos["celda"],
            ),
        ],
        [
            Paragraph("Brazo corregido", estilos["celda"]),
            Paragraph(f"{res['cag']:.1f} cm", estilos["celda"]),
        ],
        [
            Paragraph("Pierna corregida", estilos["celda"]),
            Paragraph(f"{res['ccg']:.1f} cm", estilos["celda"]),
        ],
        [
            Paragraph("Clasificación", estilos["celda"]),
            Paragraph(_escapar(res.get("clasificacion", "-")), estilos["celda_bold"]),
        ],
    ]
    tabla = Table(filas, colWidths=[1.65 * inch, 1.55 * inch], hAlign="LEFT")
    estilo = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), GRIS),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, GRIS),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FONDO]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8E8E8")),
        ]
    )
    tabla.setStyle(estilo)
    return tabla


def _somatochart(res, ancho=2.85 * inch, alto=2.55 * inch):
    dibujo = Drawing(ancho, alto)
    margen = 16
    x_min, x_max = -8.0, 8.0
    y_min, y_max = -8.0, 14.0

    escala_y = min(
        (ancho - 2 * margen) / ((x_max - x_min) * math.sqrt(3)),
        (alto - 2 * margen) / (y_max - y_min),
    )
    escala_x = escala_y * math.sqrt(3)
    margen_x = (ancho - (x_max - x_min) * escala_x) / 2
    margen_y = (alto - (y_max - y_min) * escala_y) / 2

    def px(valor):
        return margen_x + (valor - x_min) * escala_x

    def py(valor):
        return margen_y + (y_max - valor) * escala_y

    for valor in range(-8, 15, 4):
        dibujo.add(
            Line(
                px(valor), py(y_min), px(valor), py(y_max),
                strokeColor=colors.HexColor("#E0E0E0"), strokeWidth=0.4,
            )
        )
    for valor in range(-8, 15, 4):
        dibujo.add(
            Line(
                px(x_min), py(valor), px(x_max), py(valor),
                strokeColor=colors.HexColor("#E0E0E0"), strokeWidth=0.4,
            )
        )

    dibujo.add(
        Line(
            px(x_min), py(0), px(x_max), py(0),
            strokeColor=GRIS_TEXTO, strokeWidth=0.7,
        )
    )
    dibujo.add(
        Line(
            px(0), py(y_min), px(0), py(y_max),
            strokeColor=GRIS_TEXTO, strokeWidth=0.7,
        )
    )

    v_endo = (px(-6), py(-6))
    v_ecto = (px(6), py(-6))
    v_meso = (px(0), py(12))
    for inicio, fin in (
        (v_endo, v_ecto), (v_ecto, v_meso), (v_meso, v_endo)
    ):
        dibujo.add(
            Line(
                inicio[0], inicio[1], fin[0], fin[1],
                strokeColor=NARANJA, strokeWidth=1.2,
            )
        )

    dibujo.add(
        String(
            v_endo[0], v_endo[1] - 13, "ENDO",
            fontName="Helvetica-Bold", fontSize=7, fillColor=GRIS,
            textAnchor="middle",
        )
    )
    dibujo.add(
        String(
            v_ecto[0], v_ecto[1] - 13, "ECTO",
            fontName="Helvetica-Bold", fontSize=7, fillColor=GRIS,
            textAnchor="middle",
        )
    )
    dibujo.add(
        String(
            v_meso[0], v_meso[1] + 4, "MESO",
            fontName="Helvetica-Bold", fontSize=7, fillColor=GRIS,
            textAnchor="middle",
        )
    )

    cx, cy = px(res["x"]), py(res["y"])
    dibujo.add(
        Circle(
            cx, cy, 5,
            fillColor=NARANJA, strokeColor=colors.white, strokeWidth=1.2,
        )
    )
    etiqueta = f"{res['endo']:.1f}-{res['meso']:.1f}-{res['ecto']:.1f}"
    alinear = "end" if cx > ancho * 0.68 else "start"
    dx = -8 if alinear == "end" else 8
    dibujo.add(
        String(
            cx + dx, cy + 2, etiqueta,
            fontName="Helvetica-Bold", fontSize=7.5, fillColor=NEGRO,
            textAnchor=alinear,
        )
    )
    dibujo.add(
        String(
            cx + dx, cy - 8, f"X {res['x']:+.1f}  Y {res['y']:+.1f}",
            fontName="Helvetica", fontSize=6.5, fillColor=colors.HexColor("#555555"),
            textAnchor=alinear,
        )
    )
    return dibujo


def _tabla_componentes(estilos, res):
    total = res.get("total") or 1.0
    filas = [
        [
            Paragraph("Componente", estilos["centro"]),
            Paragraph("kg", estilos["centro"]),
            Paragraph("% total", estilos["centro"]),
        ]
    ]
    for nombre, clave in (
        ("Piel (cutánea)", "piel"),
        ("Tejido adiposo", "adiposa"),
        ("Músculo", "muscular"),
        ("Hueso", "osea"),
        ("Tejido residual", "residual"),
    ):
        valor = res.get(clave, 0.0)
        filas.append(
            [
                Paragraph(nombre, estilos["celda"]),
                Paragraph(f"{valor:.2f}", estilos["celda"]),
                Paragraph(f"{100 * valor / total:.1f}", estilos["celda"]),
            ]
        )
    filas.append(
        [
            Paragraph("Total predictivo", estilos["celda_bold"]),
            Paragraph(f"{total:.2f}", estilos["celda_bold"]),
            Paragraph("100.0", estilos["celda_bold"]),
        ]
    )
    tabla = Table(
        filas, colWidths=[1.55 * inch, 0.75 * inch, 0.8 * inch], hAlign="LEFT"
    )
    estilo = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), GRIS),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, GRIS),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, FONDO]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8E8E8")),
        ]
    )
    tabla.setStyle(estilo)
    return tabla


def _bar_chart(res, ancho=2.75 * inch, alto=2.1 * inch):
    dibujo = Drawing(ancho, alto)
    total = res.get("total") or 1.0
    items = [
        ("Piel", res.get("piel", 0.0)),
        ("Adiposo", res.get("adiposa", 0.0)),
        ("Músculo", res.get("muscular", 0.0)),
        ("Hueso", res.get("osea", 0.0)),
        ("Residual", res.get("residual", 0.0)),
    ]
    izquierda = 46
    derecha = 34
    arriba = 8
    abajo = 8
    alto_fila = (alto - arriba - abajo) / len(items)
    alto_barra = alto_fila * 0.55
    disponible = ancho - izquierda - derecha
    for i, (nombre, valor) in enumerate(items):
        pct = 100 * valor / total
        y = alto - arriba - (i + 1) * alto_fila + (alto_fila - alto_barra) / 2
        dibujo.add(
            Rect(
                izquierda, y, disponible, alto_barra,
                fillColor=GRIS_CLARO, strokeColor=None,
            )
        )
        dibujo.add(
            Rect(
                izquierda, y, disponible * pct / 100.0, alto_barra,
                fillColor=NARANJA, strokeColor=None,
            )
        )
        dibujo.add(
            String(
                0, y + alto_barra / 2 - 2.5, nombre,
                fontName="Helvetica", fontSize=7, fillColor=NEGRO,
            )
        )
        dibujo.add(
            String(
                ancho - derecha + 3, y + alto_barra / 2 - 2.5, f"{pct:.1f}%",
                fontName="Helvetica-Bold", fontSize=7, fillColor=NEGRO,
            )
        )
    return dibujo


def _tabla_indices(estilos, res):
    imc = (
        res["peso"] / (res["estatura"] / 100.0) ** 2
        if res.get("estatura") else 0.0
    )
    if imc < 18.5:
        clasificacion_imc = "bajo peso"
    elif imc < 25.0:
        clasificacion_imc = "normal"
    elif imc < 30.0:
        clasificacion_imc = "sobrepeso"
    else:
        clasificacion_imc = "obesidad"
    imo = (
        res.get("muscular", 0.0) / res["osea"]
        if res.get("osea") else 0.0
    )
    diferencia = res.get("total", 0.0) - res.get("peso", 0.0)
    diferencia_pct = (
        100 * diferencia / res["peso"] if res.get("peso") else 0.0
    )
    pares = [
        ("Peso real", f"{res.get('peso', 0.0):.2f} kg"),
        ("Masa predictiva", f"{res.get('total', 0.0):.2f} kg"),
        (
            "Diferencia",
            f"{diferencia:+.2f} kg ({diferencia_pct:+.1f} %)",
        ),
        ("IMC", f"{imc:.1f} kg/m² ({clasificacion_imc})"),
        ("IMO (músculo/óseo)", f"{imo:.2f}"),
        ("Superficie corporal", f"{res.get('superficie', 0.0):.3f} m²"),
        ("Suma 6 pliegues", f"{res.get('suma_adiposa', 0.0):.1f} mm"),
        (
            "Suma 5 perímetros corregidos",
            f"{res.get('suma_muscular', 0.0):.1f} cm",
        ),
        ("Brazo corregido", f"{res.get('brazo_corr', 0.0):.1f} cm"),
        ("Tórax corregido", f"{res.get('torax_corr', 0.0):.1f} cm"),
        ("Muslo corregido", f"{res.get('muslo_corr', 0.0):.1f} cm"),
        ("Pantorrilla corregida", f"{res.get('pantorrilla_corr', 0.0):.1f} cm"),
        ("Suma diámetros óseos", f"{res.get('suma_osea', 0.0):.1f} cm"),
        ("Masa ósea cabeza", f"{res.get('osea_cabeza', 0.0):.2f} kg"),
        ("Masa ósea cuerpo", f"{res.get('osea_cuerpo', 0.0):.2f} kg"),
        ("Suma residual", f"{res.get('suma_residual', 0.0):.1f} cm"),
        ("Cintura corregida", f"{res.get('cintura_corr', 0.0):.1f} cm"),
        ("Z adiposo", f"{res.get('z_adiposa', 0.0):+.2f}"),
        ("Z muscular", f"{res.get('z_muscular', 0.0):+.2f}"),
        ("Z óseo cuerpo", f"{res.get('z_osea_cuerpo', 0.0):+.2f}"),
        ("Z óseo cabeza", f"{res.get('z_osea_cabeza', 0.0):+.2f}"),
        ("Z residual", f"{res.get('z_residual', 0.0):+.2f}"),
    ]
    filas = [
        [
            Paragraph("Indicador", estilos["centro"]),
            Paragraph("Valor", estilos["centro"]),
            Paragraph("Indicador", estilos["centro"]),
            Paragraph("Valor", estilos["centro"]),
        ]
    ]
    for i in range(0, len(pares), 2):
        izq = pares[i]
        der = pares[i + 1] if i + 1 < len(pares) else ("", "")
        filas.append(
            [
                Paragraph(_escapar(izq[0]), estilos["etiqueta"]),
                Paragraph(_escapar(izq[1]), estilos["celda"]),
                Paragraph(_escapar(der[0]), estilos["etiqueta"]),
                Paragraph(_escapar(der[1]), estilos["celda"]),
            ]
        )
    tabla = Table(
        filas,
        colWidths=[1.85 * inch, 1.05 * inch, 1.85 * inch, 1.05 * inch],
        hAlign="LEFT",
    )
    tabla.setStyle(
        TableStyle(
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
    )
    return tabla


def generar_pdf_somatotipo(ruta, paciente, resultado, momento_impresion=None):
    """Genera el PDF del reporte de somatotipo Heath-Carter."""
    estilos = _estilos()
    momento = momento_impresion or datetime.now()
    doc = SimpleDocTemplate(
        ruta,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Somatotipo - {paciente.get('nombre', '')}",
        author="Nutrición Deportiva",
    )

    elementos = []
    elementos.extend(crear_membrete())
    elementos.append(Paragraph("REPORTE DE SOMATOTIPO", estilos["titulo"]))
    elementos.append(
        Paragraph(
            "Método Heath-Carter  |  Nutrición Deportiva", estilos["subtitulo"]
        )
    )
    elementos.append(_tabla_paciente(estilos, paciente, momento))

    elementos.append(Paragraph("Resultados", estilos["seccion"]))
    tabla = _tabla_resultados_somatotipo(estilos, resultado)
    chart = _somatochart(resultado)
    fila = Table(
        [[tabla, chart]], colWidths=[3.25 * inch, 3.05 * inch], hAlign="LEFT"
    )
    fila.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 10),
            ]
        )
    )
    elementos.append(fila)

    elementos.append(Paragraph("Medidas registradas", estilos["seccion"]))
    elementos.append(_tabla_medidas(estilos, resultado.get("medidas")))
    elementos.append(Spacer(1, 8))
    elementos.append(
        Paragraph(
            "Las medidas se expresan en las unidades indicadas en cada "
            "etiqueta. El somatotipo se calcula con el método Heath-Carter.",
            estilos["pie"],
        )
    )

    doc.build(elementos, onFirstPage=_pie, onLaterPages=_pie)
    return ruta


def generar_pdf_componentes(ruta, paciente, resultado, momento_impresion=None):
    """Genera el PDF del reporte de 5 componentes (Ross & Kerr)."""
    estilos = _estilos()
    momento = momento_impresion or datetime.now()
    doc = SimpleDocTemplate(
        ruta,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"5 Componentes - {paciente.get('nombre', '')}",
        author="Nutrición Deportiva",
    )

    elementos = []
    elementos.extend(crear_membrete())
    elementos.append(
        Paragraph("REPORTE DE COMPOSICIÓN CORPORAL", estilos["titulo"])
    )
    elementos.append(
        Paragraph(
            "Fraccionamiento antropométrico en 5 componentes - "
            "Ross & Kerr (1993) / Kerr (1988)",
            estilos["subtitulo"],
        )
    )
    elementos.append(_tabla_paciente(estilos, paciente, momento))

    elementos.append(Paragraph("Resultados por componente", estilos["seccion"]))
    tabla = _tabla_componentes(estilos, resultado)
    chart = _bar_chart(resultado)
    fila = Table(
        [[tabla, chart]], colWidths=[3.2 * inch, 3.1 * inch], hAlign="LEFT"
    )
    fila.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 10),
            ]
        )
    )
    elementos.append(fila)

    elementos.append(
        Paragraph("Índices y proporcionalidad", estilos["seccion"])
    )
    elementos.append(_tabla_indices(estilos, resultado))

    elementos.append(Paragraph("Medidas registradas", estilos["seccion"]))
    elementos.append(_tabla_medidas(estilos, resultado.get("medidas")))
    elementos.append(Spacer(1, 8))
    elementos.append(
        Paragraph(
            "Método de Ross & Kerr (1993) / Kerr (1988). Las medidas se "
            "expresan en las unidades indicadas en cada etiqueta.",
            estilos["pie"],
        )
    )

    doc.build(elementos, onFirstPage=_pie, onLaterPages=_pie)
    return ruta
