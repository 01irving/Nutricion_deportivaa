"""
Reporte imprimible de menús — formato SMAE (como la página consultada).

Estructura replicada del PDF de midietasmae.com.mx (ImprimirPDF.aspx):

* Portada del menú: franja de color con el nombre del menú, tarjetas de
  "Aportaciones Totales" (Energía · Proteína · Lípidos · H de C),
  gráfica "TOTAL EQUIVALENTES" por subgrupo SMAE-5 y tablas por tiempo
  de comida con columnas
  Alimento/Platillo | Porción | Energía | Proteína | Lípidos | H de C.
* Una ficha por platillo: foto, "1 Porción", tiempo de comida,
  aportaciones por porción, gráfica de equivalentes, tabla de
  ingredientes escalada a 1 / 4 / 6 personas y preparación numerada.
* Pie con las notas oficiales de cálculo de equivalentes.

La lógica de cálculo no cambia: los totales siguen siendo la suma de
(valor del registro × eq_cantidad), igual que en la interfaz.
"""
import io
import json
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    Image,
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


def ruta_temporal_pdf(nombre_paciente):
    """Ruta del PDF temporal de menús para un paciente."""
    return _ruta_temporal_pdf("Menus", nombre_paciente)

# ------------------------------------------------------------------
# Paleta SMAE (tomada del PDF consultado)
# ------------------------------------------------------------------
VINO = colors.HexColor("#BE6E77")          # franja del nombre del menú
ROSA_HEADER = colors.HexColor("#E7B6BC")   # encabezados de tabla
ROSA_FILA = colors.HexColor("#F9ECEE")     # renglón alterno
NARANJA_CARD = colors.HexColor("#F79B6A")  # Energía
NARANJA_FUERTE = colors.HexColor("#F1723B")  # Proteína
VERDE_CLARO = colors.HexColor("#A9CB86")   # Lípidos
VERDE_OSCURO = colors.HexColor("#4C7A2F")  # H de C
TIEMPO_VERDE = colors.HexColor("#7FA653")  # etiqueta del tiempo de comida
AZUL_BADGE_BG = colors.HexColor("#DCEAF7")  # "1 Porción"
AZUL_BADGE_TX = colors.HexColor("#2B6CB0")
GRIS_TEXTO = colors.HexColor("#8A8A8A")
NEGRO = colors.HexColor("#121212")

# Espejo de menu_tab.SUBGRUPOS_CORTO (17 subgrupos SMAE-5). El caller
# puede pasar su propia lista vía el parámetro `subgrupos`.
SUBGRUPOS_DEFECTO = [
    "Verduras", "Frutas", "Cereales s/g", "Cereales c/g", "Leguminosas",
    "AOA MBAG", "AOA BAG", "AOA MAG", "AOA AAG",
    "Leche descrem.", "Leche semidesc.", "Leche entera", "Leche azúcar",
    "Grasas s/prot", "Grasas c/prot", "Azúcares s/g", "Azúcares c/g",
]

# Espejo de menu_tab.SUBGRUPOS (nombres completos, para mapear el campo
# `grupo` de los registros de alimentos a un índice de subgrupo).
SUBGRUPOS_NOMBRE = [
    "Verduras", "Frutas", "Cereales sin grasa", "Cereales con grasa",
    "Leguminosas", "AOA MBAG", "AOA BAG", "AOA MAG", "AOA AAG",
    "Leche descremada", "Leche semidescremada", "Leche entera",
    "Leche con azúcar", "Aceites y grasas",
    "Aceites y grasas con proteina", "Azucares sin grasa",
    "Azucares con grasa",
]

_NOTAS_SMAE = [
    "Los alimentos equivalentes están calculados con base en:",
    "• El peso neto de los alimentos, es decir, sin cáscara, semillas, "
    "ni huesos y espinas.",
    "• El peso de los alimentos cocidos.",
    "• En el caso de los alimentos preparados, de “comida rápida”, en su "
    "preparación lista para consumirse.",
]

_FRACCIONES = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1.0 / 3, "⅔": 2.0 / 3,
               "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875}
_RE_NUMERO = re.compile(r"(\d+(?:[.,]\d+)?)|([½¼¾⅓⅔⅛⅜⅝⅞])")


def _escapar(texto):
    if texto is None:
        return ""
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _numero_cantidad(texto):
    """Extrae el factor numérico de un texto de cantidad ('½ taza' → 0.5)."""
    if not texto:
        return None
    total, encontrado = 0.0, False
    for m in _RE_NUMERO.finditer(str(texto)):
        encontrado = True
        if m.group(1):
            total += float(m.group(1).replace(",", "."))
        else:
            total += _FRACCIONES.get(m.group(2), 0.0)
    return total if encontrado else None


def _fmt_cantidad(valor):
    if valor is None:
        return ""
    if abs(valor - round(valor)) < 1e-9:
        return f"{int(round(valor))}"
    return f"{valor:.2f}".rstrip("0").rstrip(".")


def _escalar_cantidad(cantidad_txt, veces):
    """Escala un texto de cantidad × veces; si no hay número, repite el texto."""
    factor = _numero_cantidad(cantidad_txt)
    if factor is None:
        return (cantidad_txt or "").strip() or "—"
    resto = _RE_NUMERO.sub("", str(cantidad_txt or "")).strip(" .,")
    return " ".join(p for p in (_fmt_cantidad(factor * veces), resto) if p)


def _estilos():
    base = getSampleStyleSheet()
    return {
        "banner": ParagraphStyle(
            "banner", fontName="Helvetica-Bold", fontSize=15, leading=19,
            textColor=colors.white,
        ),
        "info": ParagraphStyle(
            "info", fontName="Helvetica", fontSize=8.5, leading=11,
            textColor=GRIS_TEXTO,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=15, leading=18, textColor=NEGRO, spaceAfter=2,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=NEGRO,
            spaceBefore=8, spaceAfter=2, keepWithNext=1,
        ),
        "por": ParagraphStyle(
            "por", fontName="Helvetica", fontSize=9.5, leading=12,
            textColor=GRIS_TEXTO, spaceAfter=4,
        ),
        "dia": ParagraphStyle(
            "dia", fontName="Helvetica-Bold", fontSize=11.5, leading=14,
            textColor=NEGRO, spaceBefore=10, spaceAfter=3, keepWithNext=1,
        ),
        "tiempo": ParagraphStyle(
            "tiempo", fontName="Helvetica-Bold", fontSize=10.5, leading=13,
            textColor=TIEMPO_VERDE, spaceBefore=6, spaceAfter=2,
            keepWithNext=1,
        ),
        "badge": ParagraphStyle(
            "badge", fontName="Helvetica", fontSize=9, leading=12,
            textColor=AZUL_BADGE_TX, alignment=TA_CENTER,
            backColor=AZUL_BADGE_BG, borderPadding=(5, 8),
        ),
        "thead": ParagraphStyle(
            "thead", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
            textColor=NEGRO,
        ),
        "celda": ParagraphStyle(
            "celda", fontName="Helvetica", fontSize=8.5, leading=11,
            textColor=NEGRO,
        ),
        "celda_b": ParagraphStyle(
            "celda_b", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
            textColor=NEGRO,
        ),
        "celda_r": ParagraphStyle(
            "celda_r", fontName="Helvetica", fontSize=8.5, leading=11,
            textColor=NEGRO, alignment=TA_RIGHT,
        ),
        "nota": ParagraphStyle(
            "nota", fontName="Helvetica", fontSize=7.5, leading=9.5,
            textColor=GRIS_TEXTO,
        ),
        "pie": ParagraphStyle(
            "pie", fontName="Helvetica-Oblique", fontSize=8, leading=10,
            textColor=GRIS_TEXTO, alignment=TA_CENTER,
        ),
        "prep": ParagraphStyle(
            "prep", fontName="Helvetica", fontSize=9, leading=12.5,
            textColor=NEGRO, leftIndent=14, firstLineIndent=-14,
            spaceAfter=2,
        ),
        "normal": ParagraphStyle(
            "normal", fontName="Helvetica", fontSize=9, leading=12.5,
            textColor=NEGRO, spaceAfter=3,
        ),
    }


# ------------------------------------------------------------------
# Gráfica "TOTAL EQUIVALENTES" (barras verticales, etiquetas rotadas)
# ------------------------------------------------------------------
class GraficaEquivalentes(Flowable):
    """Barras verticales con etiquetas rotadas 90°, como la gráfica
    'TOTAL EQUIVALENTES' del formato SMAE."""

    # Zona bajo el eje: renglón de valores (22 pt) + etiquetas (58 pt)
    _ZONA_BAJO = 80
    _AIRE_TOP = 14

    def __init__(self, valores, etiquetas, alto_barras=88, ancho=7.15 * inch,
                 fuente=5.2):
        Flowable.__init__(self)
        self.valores = [max(0.0, float(v or 0)) for v in valores]
        self.etiquetas = [str(e) for e in etiquetas]
        self.ancho = ancho
        self._alto_barras = alto_barras
        self._fuente = fuente
        self.width = ancho
        self.height = self._ZONA_BAJO + alto_barras + self._AIRE_TOP

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        izq, der = 66, 6
        x0, x1 = izq, self.width - der
        eje_y = self._ZONA_BAJO
        n = max(1, len(self.valores))
        paso = (x1 - x0) / n
        bw = paso * 0.62
        vmax = max(self.valores)
        hmax = self._alto_barras

        c.setLineWidth(0.9)
        c.setStrokeColor(colors.black)
        c.setFillColor(colors.black)
        for i, v in enumerate(self.valores):
            bh = (v / vmax) * hmax if vmax > 0 else 0
            if bh > 0.3:
                bx = x0 + i * paso + (paso - bw) / 2
                c.rect(bx, eje_y, bw, bh, stroke=1, fill=1)

        c.line(x0 - 3, eje_y, x1 + 3, eje_y)

        # Título a la izquierda del eje
        c.setFont("Helvetica-Bold", 7)
        c.setFillGray(0.2)
        ty = eje_y + 2
        for linea in ("TOTAL", "EQUIVALENTES"):
            c.drawString(4, ty, linea)
            ty -= 9
        c.setFillGray(0)

        # Valores bajo el eje + etiquetas rotadas 90° (tope alineado)
        fs = self._fuente
        c.setFont("Helvetica", fs)
        for i, (v, et) in enumerate(zip(self.valores, self.etiquetas)):
            cx = x0 + i * paso + paso / 2
            c.drawCentredString(cx, eje_y - 8, _fmt_cantidad(round(v, 2)))
            largo = 0.56 * fs * len(et)
            c.saveState()
            c.translate(cx + 2, eje_y - 13 - min(largo, self._ZONA_BAJO - 20))
            c.rotate(90)
            c.setFont("Helvetica", fs)
            c.drawString(0, -1.4, et)
            c.restoreState()


# ------------------------------------------------------------------
# Agregados
# ------------------------------------------------------------------
def _totales_lista(registros):
    totales = {
        "energia_kcal": 0.0, "proteina_g": 0.0, "lipidos_g": 0.0, "hc_g": 0.0,
    }
    for reg in registros or []:
        eq = reg.get("eq_cantidad", 1.0) or 1.0
        for clave in totales:
            try:
                totales[clave] += float(reg.get(clave) or 0) * eq
            except (TypeError, ValueError):
                pass
    return totales


def _eq_por_subgrupo(registros, n_subgrupos):
    """Suma eq_cantidad por subgrupo; acepta `grupo` (nombre) o
    `subgrupo_idx` (índice directo)."""
    eqs = [0.0] * n_subgrupos
    for reg in registros or []:
        try:
            eq = float(reg.get("eq_cantidad") or 0)
        except (TypeError, ValueError):
            eq = 0.0
        idx = reg.get("subgrupo_idx")
        if not isinstance(idx, int):
            idx = None
            nombre = (reg.get("grupo") or "").strip().lower()
            for i, sg in enumerate(SUBGRUPOS_NOMBRE[:n_subgrupos]):
                if nombre == sg.lower():
                    idx = i
                    break
            if idx is None and nombre:
                for i, sg in enumerate(SUBGRUPOS_NOMBRE[:n_subgrupos]):
                    if nombre and (nombre in sg.lower() or sg.lower() in nombre):
                        idx = i
                        break
        if idx is not None and 0 <= idx < n_subgrupos:
            eqs[idx] += eq
    return eqs


def _normalizar_ingrediente(reg):
    """Uniforma un registro (menú o catálogo) para las fichas."""
    cantidad = reg.get("cantidad_txt")
    if not cantidad:
        cs, un = reg.get("cantidad_sugerida"), reg.get("unidad") or ""
        if cs:
            cantidad = " ".join(p for p in (f"{cs:g}", un) if p)
        elif un:
            cantidad = un
    return {
        "alimento": reg.get("alimento") or "",
        "cantidad_txt": cantidad or "",
        "grupo": reg.get("grupo") or "",
        "subgrupo_idx": reg.get("subgrupo_idx"),
        "eq_cantidad": reg.get("eq_cantidad") or 0,
        "energia_kcal": reg.get("energia_kcal") or 0,
        "proteina_g": reg.get("proteina_g") or 0,
        "lipidos_g": reg.get("lipidos_g") or 0,
        "hc_g": reg.get("hc_g") or 0,
    }


# ------------------------------------------------------------------
# Piezas del formato SMAE
# ------------------------------------------------------------------
def _franja(nombre, estilos):
    tabla = Table(
        [[Paragraph(_escapar(nombre), estilos["banner"])]],
        colWidths=[7.3 * inch], hAlign="LEFT",
    )
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), VINO),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tabla


def _tarjetas_macro(estilos, tot, titulo="Aportaciones Totales", sub="Por menú",
                    ancho_card=1.58 * inch, gap=0.16 * inch, compacto=False):
    """Cuatro tarjetas de color: Energía · Proteína · Lípidos · H de C."""
    base = getSampleStyleSheet()["Normal"]
    f_lbl, f_val, f_uni = (7, 11.5, 7) if compacto else (8, 15, 8)
    st_lbl = ParagraphStyle("t_lbl", parent=base, fontName="Helvetica",
                            fontSize=f_lbl, leading=f_lbl + 2,
                            textColor=colors.white)
    st_val = ParagraphStyle("t_val", parent=base, fontName="Helvetica-Bold",
                            fontSize=f_val, leading=f_val + 2.5,
                            textColor=colors.white, spaceBefore=3,
                            spaceAfter=3)
    st_uni = ParagraphStyle("t_uni", parent=base, fontName="Helvetica",
                            fontSize=f_uni, leading=f_uni + 2,
                            textColor=colors.white)
    tarjetas = [
        (NARANJA_CARD, "Energía", tot.get("energia_kcal", 0), "kCal"),
        (NARANJA_FUERTE, "Proteína", tot.get("proteina_g", 0), "g"),
        (VERDE_CLARO, "Lípidos", tot.get("lipidos_g", 0), "g"),
        (VERDE_OSCURO, "H de C", tot.get("hc_g", 0), "g"),
    ]
    celdas, anchos = [], []
    for i, (bg, etiqueta, valor, unidad) in enumerate(tarjetas):
        celdas.append([
            Paragraph(etiqueta, st_lbl),
            Paragraph(f"{valor:.2f}", st_val),
            Paragraph(unidad, st_uni),
        ])
        anchos.append(ancho_card)
        if i < len(tarjetas) - 1:
            celdas.append("")
            anchos.append(gap)
    tabla = Table([celdas], colWidths=anchos, hAlign="LEFT")
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8 if compacto else 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]
    for i in range(0, len(anchos), 2):
        estilo.append(("BACKGROUND", (i, 0), (i, 0), tarjetas[i // 2][0]))
    tabla.setStyle(TableStyle(estilo))
    return [Paragraph(titulo, estilos["h1"]), Paragraph(sub, estilos["por"]),
            tabla]


def _tabla_tiempo(estilos, platillo, registros, elementos=None):
    """Tabla SMAE: Alimento/Platillo | Porción | Energía | Proteína |
    Lípidos | H de C. Si hay `elementos` [(nombre, regs)], imprime una
    fila por cada uno (platillo, bebida, acompañamiento)."""
    encabezados = [
        "Alimento/Platillo", "Porción", "Energía", "Proteína", "Lípidos",
        "H de C",
    ]
    filas = [[Paragraph(t, estilos["thead"]) for t in encabezados]]
    anchos = [3.0 * inch, 0.75 * inch, 0.95 * inch, 0.88 * inch,
              0.88 * inch, 0.84 * inch]

    if elementos:
        for nombre, regs in elementos:
            tot = _totales_lista(regs)
            filas.append([
                Paragraph(_escapar(nombre), estilos["celda_b"]),
                Paragraph("1", estilos["celda"]),
                Paragraph(f"{tot['energia_kcal']:.2f} kcal",
                          estilos["celda_r"]),
                Paragraph(f"{tot['proteina_g']:.2f} g", estilos["celda_r"]),
                Paragraph(f"{tot['lipidos_g']:.2f} g", estilos["celda_r"]),
                Paragraph(f"{tot['hc_g']:.2f} g", estilos["celda_r"]),
            ])
    else:
        tot = _totales_lista(registros)
        if platillo:
            filas.append([
                Paragraph(_escapar(platillo), estilos["celda_b"]),
                Paragraph("1", estilos["celda"]),
                Paragraph(f"{tot['energia_kcal']:.2f} kcal", estilos["celda_r"]),
                Paragraph(f"{tot['proteina_g']:.2f} g", estilos["celda_r"]),
                Paragraph(f"{tot['lipidos_g']:.2f} g", estilos["celda_r"]),
                Paragraph(f"{tot['hc_g']:.2f} g", estilos["celda_r"]),
            ])
        else:
            for reg in registros or []:
                cs, un = reg.get("cantidad_sugerida"), reg.get("unidad") or ""
                porcion = " ".join(p for p in (f"{cs:g}" if cs else "", un) if p) \
                    or f"{reg.get('eq_cantidad', 0):g}"
                filas.append([
                    Paragraph(_escapar(reg.get("alimento") or ""), estilos["celda"]),
                    Paragraph(_escapar(porcion), estilos["celda"]),
                    Paragraph(f"{float(reg.get('energia_kcal') or 0) * float(reg.get('eq_cantidad') or 1):.2f} kcal",
                              estilos["celda_r"]),
                    Paragraph(f"{float(reg.get('proteina_g') or 0) * float(reg.get('eq_cantidad') or 1):.2f} g",
                              estilos["celda_r"]),
                    Paragraph(f"{float(reg.get('lipidos_g') or 0) * float(reg.get('eq_cantidad') or 1):.2f} g",
                              estilos["celda_r"]),
                    Paragraph(f"{float(reg.get('hc_g') or 0) * float(reg.get('eq_cantidad') or 1):.2f} g",
                              estilos["celda_r"]),
                ])

    tabla = Table(filas, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), ROSA_HEADER),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9A0A8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROSA_FILA]),
    ]
    tabla.setStyle(TableStyle(estilo))
    return tabla


def _nota_pie(estilos, fecha):
    textos = [Paragraph(t, estilos["nota"]) for t in _NOTAS_SMAE]
    textos.append(Spacer(1, 4))
    textos.append(Paragraph(
        f"Elaborado con Nutrición Deportiva — {fecha}",
        estilos["nota"],
    ))
    return textos


def _preparacion_items(modo_preparacion):
    """Elementos de la forma de preparación: pasos numerados si el texto los
    trae; si no, las líneas o párrafos tal cual. Devuelve una lista de
    (texto, numero); numero es None para texto sin numerar."""
    texto = (modo_preparacion or "").strip()
    if not texto:
        return []
    numerados, lineas = [], []
    for linea in texto.splitlines():
        limpio = linea.strip()
        if not limpio:
            continue
        m = re.match(r"^(\d+)\s*[.)\-]\s*(.+)$", limpio)
        if m:
            numerados.append((m.group(2).strip(), int(m.group(1))))
        else:
            lineas.append(limpio)
    if numerados:
        return [(t, i + 1) for i, (t, _n) in enumerate(numerados)]
    return [(t, None) for t in lineas]


def _ingredientes_escalados(estilos, ingredientes):
    """Tabla SMAE de ingredientes: Alimento | No. de personas (1/4/6) |
    Unidad, con las cantidades escaladas."""
    filas = [
        [Paragraph("Alimento", estilos["thead"]),
         Paragraph("No. de personas", estilos["thead"]), "", "",
         Paragraph("Unidad", estilos["thead"])],
        ["", Paragraph("1", estilos["thead"]), Paragraph("4", estilos["thead"]),
         Paragraph("6", estilos["thead"]), ""],
    ]
    for ing in ingredientes:
        texto = ing.get("cantidad_txt") or ""
        unidad = texto
        factor = _numero_cantidad(texto)
        if factor is not None:
            unidad = _RE_NUMERO.sub("", texto).strip(" .,")
        filas.append([
            Paragraph(_escapar(ing.get("alimento") or ""), estilos["celda"]),
            Paragraph(_escapar(_escalar_cantidad(texto, 1)), estilos["celda_r"]),
            Paragraph(_escapar(_escalar_cantidad(texto, 4)), estilos["celda_r"]),
            Paragraph(_escapar(_escalar_cantidad(texto, 6)), estilos["celda_r"]),
            Paragraph(_escapar(unidad or "—"), estilos["celda"]),
        ])
    anchos = [2.5 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 1.1 * inch]
    tabla = Table(filas, colWidths=anchos, repeatRows=2, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 1), ROSA_HEADER),
        ("SPAN", (0, 0), (0, 1)),
        ("SPAN", (1, 0), (3, 0)),
        ("SPAN", (4, 0), (4, 1)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9A0A8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, ROSA_FILA]),
    ]))
    return tabla


def _buscar_en_catalogo(nombre_platillo):
    """Busca el platillo en el catálogo (database). Devuelve el registro
    o None. Tolerante a fallos: si la BD no está disponible devuelve None."""
    if not nombre_platillo:
        return None
    try:
        import database
        objetivo = (nombre_platillo or "").strip().lower()
        for plat in database.get_platillos() or []:
            if (plat.get("nombre") or "").strip().lower() == objetivo:
                return plat
    except Exception:
        return None
    return None


def _ficha_platillo(estilos, nombre_menu, platillo, tiempo, registro, subgrupos):
    """Página de detalle de un platillo, como en la impresión SMAE."""
    elementos = [_franja(nombre_menu, estilos), Spacer(1, 8)]

    nombre = platillo or "(sin nombre)"
    insignia = Table(
        [[Paragraph("1 Porción", estilos["badge"])]],
        colWidths=[1.05 * inch], hAlign="RIGHT",
    )
    insignia.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elementos.append(Table(
        [[Paragraph(_escapar(nombre), estilos["h1"]), insignia]],
        colWidths=[5.4 * inch, 1.9 * inch], hAlign="LEFT",
    ))

    # Ingredientes: catálogo si existe; si no, los del tiempo actual.
    catalogo = _buscar_en_catalogo(platillo)
    ingredientes = []
    foto_blob = None
    preparacion_txt = ""
    if catalogo:
        try:
            crudos = json.loads(catalogo.get("ingredientes") or "[]")
            ingredientes = [_normalizar_ingrediente(r) for r in crudos]
        except (ValueError, TypeError):
            ingredientes = []
        foto_blob = catalogo.get("imagen_blob")
        preparacion_txt = catalogo.get("modo_preparacion") or ""
    if not ingredientes:
        ingredientes = [_normalizar_ingrediente(r) for r in (registro or [])]

    if tiempo:
        elementos.append(Paragraph(_escapar(tiempo), estilos["tiempo"]))

    # Foto + aportaciones por porción
    tot = _totales_lista(ingredientes)
    compacto = bool(foto_blob)
    bloque_tarjetas = [
        Paragraph("Aportaciones Totales", estilos["h2"]),
        Paragraph("Por Porción", estilos["por"]),
        _tarjetas_macro(
            estilos, tot, sub="Por Porción",
            ancho_card=0.9 * inch if compacto else 1.58 * inch,
            gap=0.07 * inch if compacto else 0.16 * inch,
            compacto=compacto,
        )[2],
    ]
    if foto_blob:
        try:
            lector = ImageReader(io.BytesIO(foto_blob))
            iw, ih = lector.getSize()
            ancho = 3.1 * inch
            alto = min(2.3 * inch, ancho * ih / max(1, iw))
            elementos.append(Table(
                [[Image(io.BytesIO(foto_blob), width=ancho, height=alto),
                  bloque_tarjetas]],
                colWidths=[3.35 * inch, 3.95 * inch], hAlign="LEFT",
            ))
        except Exception:
            elementos.extend(bloque_tarjetas)
    else:
        elementos.extend(bloque_tarjetas)

    # Gráfica de equivalentes del platillo
    eqs = _eq_por_subgrupo(ingredientes, len(subgrupos))
    elementos.append(Spacer(1, 6))
    elementos.append(GraficaEquivalentes(
        eqs, subgrupos, alto_barras=62, ancho=7.15 * inch,
    ))
    elementos.append(Spacer(1, 8))

    # Ingredientes escalados
    if ingredientes:
        elementos.append(Paragraph("Ingredientes", estilos["h2"]))
        elementos.append(_ingredientes_escalados(estilos, ingredientes))

    # Forma de preparación (siempre visible, como en el recetario SMAE)
    elementos.append(Paragraph("Forma de preparación", estilos["h2"]))
    items = _preparacion_items(preparacion_txt)
    if items:
        for texto_item, num in items:
            if num is None:
                elementos.append(
                    Paragraph(_escapar(texto_item), estilos["normal"])
                )
            else:
                elementos.append(Paragraph(
                    f"{num}. {_escapar(texto_item)}", estilos["prep"]
                ))
    else:
        elementos.append(Paragraph(
            "Sin preparación registrada para este platillo.",
            estilos["normal"],
        ))

    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph(
        "Este documento es informativo y no sustituye la valoración de un "
        "profesional de la salud.",
        estilos["pie"],
    ))
    return elementos


# ------------------------------------------------------------------
# Documento principal
# ------------------------------------------------------------------
def _pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(GRIS_TEXTO)
    canvas.drawString(
        0.6 * inch, 0.38 * inch,
        "Equivalentes calculados con base en el peso neto, el peso cocido y "
        "la preparación lista para consumirse.",
    )
    canvas.drawRightString(
        letter[0] - 0.6 * inch, 0.38 * inch, f"Página {doc.page}",
    )
    canvas.restoreState()


def generar_pdf_menus(ruta, paciente, tiempos, dias, momento_impresion=None,
                      subgrupos=None, nombre_menu=None):
    """
    Genera el PDF del menú con el formato SMAE.

    tiempos: lista de nombres de tiempo de comida.
    dias: dict día -> {"platillos": {idx: texto}, "alimentos": {idx: [regs]}}.
    subgrupos: nombres cortos de los 17 subgrupos SMAE-5 (opcional).
    nombre_menu: texto de la franja de la portada (opcional).
    """
    estilos = _estilos()
    momento = momento_impresion or datetime.now()
    subgrupos = list(subgrupos or SUBGRUPOS_DEFECTO)
    fecha = momento.strftime("%d/%m/%Y %H:%M")

    nombre = nombre_menu or paciente.get("nombre") or "Menú semanal"

    doc = SimpleDocTemplate(
        ruta,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.65 * inch,
        title=f"Menú — {paciente.get('nombre', '')}",
        author="Nutrición Deportiva",
    )

    elementos = []
    elementos.extend(crear_membrete())
    elementos.append(Spacer(1, 6))
    elementos.append(_franja(nombre, estilos))
    elementos.append(Spacer(1, 4))

    # Línea de paciente (discreta): la app imprime por paciente.
    fecha_nac = paciente.get("fecha_nacimiento") or paciente.get("dob") or ""
    edad = calcular_edad(fecha_nac)
    partes = []
    if paciente.get("nombre"):
        partes.append(f"Paciente: {paciente['nombre']}")
    if edad is not None:
        partes.append(f"Edad: {edad} años")
    partes.append(f"Fecha de impresión: {fecha}")
    elementos.append(Paragraph(" · ".join(partes), estilos["info"]))
    elementos.append(Spacer(1, 8))

    # Totales del menú completo (todas las listas de todos los días)
    todos = []
    for info in (dias or {}).values():
        for lista in (info.get("alimentos") or {}).values():
            todos.extend(lista or [])
    n_dias = sum(
        1 for info in (dias or {}).values()
        if any(info.get("alimentos") or {}.values())
    )
    tot_menu = _totales_lista(todos)
    if n_dias > 1:
        tot_tarjetas = {k: v / n_dias for k, v in tot_menu.items()}
        sub_tarjetas = f"Promedio por día · {n_dias} días"
    else:
        tot_tarjetas = tot_menu
        sub_tarjetas = "Por menú"
    elementos.extend(_tarjetas_macro(estilos, tot_tarjetas, sub=sub_tarjetas))
    elementos.append(Spacer(1, 6))

    # Gráfica TOTAL EQUIVALENTES: promedio por día con datos
    eqs = _eq_por_subgrupo(todos, len(subgrupos))
    if n_dias > 1:
        eqs = [e / n_dias for e in eqs]
    etiqueta_sub = (
        "Promedio de equivalentes por día"
        if n_dias > 1 else "Total de equivalentes del menú"
    )
    elementos.append(GraficaEquivalentes(eqs, subgrupos, alto_barras=88))
    elementos.append(Paragraph(etiqueta_sub, estilos["nota"]))
    elementos.append(Spacer(1, 4))

    # Tablas por día y tiempo de comida
    for dia, info in (dias or {}).items():
        platillos = info.get("platillos") or {}
        alimentos = info.get("alimentos") or {}
        if not any(alimentos.get(t_idx) for t_idx in range(len(tiempos or []))) \
                and not any(platillos.values()):
            continue
        elementos.append(Paragraph(_escapar(dia), estilos["dia"]))
        for t_idx, nombre_tiempo in enumerate(tiempos or []):
            registros = alimentos.get(t_idx) or alimentos.get(str(t_idx)) or []
            platillo = platillos.get(t_idx) or platillos.get(str(t_idx)) or ""
            elems = ((info.get("elementos") or {}).get(t_idx)
                     or (info.get("elementos") or {}).get(str(t_idx))
                     or [])
            elems = [(n, r) for n, r in elems if r]
            if not registros and not platillo and not elems:
                continue
            elementos.append(
                Paragraph(_escapar(nombre_tiempo), estilos["tiempo"])
            )
            elementos.append(_tabla_tiempo(estilos, platillo, registros, elems))
            elementos.append(Spacer(1, 4))

    # Notas oficiales de cálculo (como el pie del PDF de SMAE)
    elementos.append(Spacer(1, 8))
    elementos.extend(_nota_pie(estilos, fecha))

    # Fichas de platillo (una por platillo único del menú)
    vistos = set()
    for info in (dias or {}).values():
        platillos = info.get("platillos") or {}
        alimentos = info.get("alimentos") or {}
        for t_idx, platillo in platillos.items():
            if not platillo or platillo in vistos:
                continue
            vistos.add(platillo)
            registros = alimentos.get(t_idx) or alimentos.get(str(t_idx)) or []
            tiempo = tiempos[t_idx] if isinstance(t_idx, int) and tiempos \
                and t_idx < len(tiempos) else (
                tiempos[int(t_idx)] if str(t_idx).isdigit()
                and tiempos and int(t_idx) < len(tiempos) else ""
            )
            elementos.append(PageBreak())
            elementos.extend(
                _ficha_platillo(estilos, nombre, platillo, tiempo, registros,
                                subgrupos)
            )

    doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    return ruta


__all__ = [
    "abrir_para_imprimir",
    "calcular_edad",
    "generar_pdf_menus",
    "nombre_pdf",
    "ruta_temporal_pdf",
]
