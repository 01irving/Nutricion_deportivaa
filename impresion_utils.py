"""
Utilidades compartidas de impresión (ReportLab + Windows).

- calcular_edad: edad en años a partir de la fecha de nacimiento.
- abrir_para_imprimir: abre el archivo con la aplicación predeterminada.
- ruta_temporal_pdf: arma la ruta de un PDF temporal con prefijo y paciente.
- estampar_membrete: copia un PDF externo con el membrete institucional.
"""
import io
import os
import re
import subprocess
import tempfile
from datetime import date, datetime

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    Table,
    TableStyle,
)

import database

# ----------------------------------------------------------------------
# Membrete: datos del profesional que encabezan los reportes imprimibles.
# Se guardan en la BD (tabla configuracion), así viajan con la base de
# datos al compartir la app y se personalizan desde ⚙ en el encabezado.
# ----------------------------------------------------------------------
CLAVES_MEMBRETE = ("nombre", "direccion", "telefono", "redes_sociales")

# Datos con los que arranca la app si aún no se ha personalizado nada
DATOS_PREDETERMINADOS = {
    "nombre": "Irving Gualberto Euan Dzul",
    "direccion": "Calle 21 Num 42. Nunkiní, Calkiní, Camp.",
    "telefono": "9961059072",
    "redes_sociales": "facebook: Irving Euan",
}

# Logo heredado: si existe al primer arranque se importa a la BD
RUTA_LOGO = r"C:\Users\hp\Pictures\Saved Pictures\Nutritio-Hominis.png"

_CLAVE_LOGO = "membrete_logo"
_CLAVE_INICIALIZADO = "membrete_inicializado"

# Acrobat (o Acrobat Reader) para abrir el PDF y ajustarlo antes de imprimir
RUTAS_ACROBAT = [
    r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
    r"C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
    r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\Acrobat.exe",
    r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\Acrobat.exe",
    r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
    r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
]

NEGRO = colors.HexColor("#121212")
GRIS = colors.HexColor("#2C2C2C")
NARANJA = colors.HexColor("#FF6D00")
GRIS_TEXTO = colors.HexColor("#444444")


def datos_profesional():
    """
    Datos del profesional que encabezan la app y las impresiones.

    Se leen de la base de datos (van con ella al compartir la app). En el
    primer arranque siembra los valores predeterminados e importa el logo
    heredado de RUTA_LOGO si ese archivo existe.
    """
    if not database.get_config(_CLAVE_INICIALIZADO):
        for clave, valor in DATOS_PREDETERMINADOS.items():
            database.set_config("membrete_" + clave, valor)
        if not logo_bytes() and RUTA_LOGO and os.path.exists(RUTA_LOGO):
            try:
                guardar_logo(imagen_a_png(RUTA_LOGO))
            except Exception:
                pass
        database.set_config(_CLAVE_INICIALIZADO, "1")
    return {
        clave: str(database.get_config("membrete_" + clave, "") or "")
        for clave in CLAVES_MEMBRETE
    }


def guardar_datos_profesional(datos):
    """Guarda nombre, dirección, teléfono y redes en la base de datos."""
    for clave in CLAVES_MEMBRETE:
        database.set_config("membrete_" + clave, str(datos.get(clave, "") or ""))
    database.set_config(_CLAVE_INICIALIZADO, "1")


def logo_bytes():
    """PNG (bytes) del logo institucional guardado en la BD; None si no hay."""
    datos = database.get_config(_CLAVE_LOGO)
    if not datos:
        return None
    return bytes(datos) if isinstance(datos, (bytes, bytearray)) else None


def guardar_logo(imagen_bytes):
    """Guarda el logo (PNG bytes) en la base de datos."""
    database.set_config(_CLAVE_LOGO, bytes(imagen_bytes))


def quitar_logo():
    """Elimina el logo guardado."""
    database.set_config(_CLAVE_LOGO, "")


def imagen_a_png(ruta_o_bytes):
    """Convierte una imagen (ruta o bytes) a PNG para guardarla en la BD."""
    import io

    from PIL import Image

    origen = ruta_o_bytes
    if isinstance(origen, (bytes, bytearray)):
        origen = io.BytesIO(bytes(origen))
    with Image.open(origen) as imagen:
        bufer = io.BytesIO()
        imagen.convert("RGBA").save(bufer, format="PNG")
        return bufer.getvalue()


def _escapar(texto):
    if texto is None:
        return ""
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _estilos_membrete():
    base = getSampleStyleSheet()
    return {
        "nombre": ParagraphStyle(
            "nombre_profesional", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=13, leading=16, textColor=NEGRO, spaceAfter=1,
        ),
        "dato": ParagraphStyle(
            "dato_profesional", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=11, textColor=GRIS_TEXTO,
        ),
    }


def _logo_flowable(ancho):
    """Logo institucional (de la BD) como flowable; None si no hay."""
    logo = logo_bytes()
    if not logo:
        return None
    try:
        reader = ImageReader(io.BytesIO(logo))
        ancho_px, alto_px = reader.getSize()
    except Exception:
        return None
    if not ancho_px or not alto_px:
        return None
    escala = ancho / float(ancho_px)
    return RLImage(io.BytesIO(logo), width=ancho, height=alto_px * escala)


def crear_membrete(ancho_total=6.3 * inch):
    """
    Flowables del membrete institucional: logo + datos del profesional.

    Devuelve una lista (puede ir vacía si no hay datos configurados).
    """
    datos = datos_profesional()
    if not any(datos.values()):
        return []

    estilos = _estilos_membrete()
    # Nombre en un estilo mayor; el resto en un estilo secundario.
    nombre_p = Paragraph(_escapar(datos.get("nombre", "")), estilos["nombre"])
    resto = [
        Paragraph(_escapar(str(datos[clave])), estilos["dato"])
        for clave in ("direccion", "telefono", "redes_sociales")
        if datos.get(clave)
    ]

    ancho_logo = 1.35 * inch
    logo = _logo_flowable(ancho_logo)
    if logo is not None:
        tabla = Table(
            [[logo, [nombre_p] + resto]],
            colWidths=[ancho_logo, ancho_total - ancho_logo],
            hAlign="LEFT",
        )
    else:
        tabla = Table(
            [[None, [nombre_p] + resto]],
            colWidths=[ancho_logo, ancho_total - ancho_logo],
            hAlign="LEFT",
        )
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return [
        tabla,
        HRFlowable(
            width="100%",
            thickness=1.2,
            color=NARANJA,
            spaceBefore=4,
            spaceAfter=8,
        ),
    ]


# ----------------------------------------------------------------------
# Estampado del membrete sobre PDFs externos (p. ej. recomendaciones)
# ----------------------------------------------------------------------
ENCABEZADO_ALTO = 1.05 * inch  # banda superior que ocupa el membrete


def _overlay_membrete(ancho, alto):
    """Página pypdf con el membrete dibujado en la banda superior."""
    datos = datos_profesional()
    logo = logo_bytes()
    bufer = io.BytesIO()
    lienzo = rl_canvas.Canvas(bufer, pagesize=(ancho, alto))
    margen = 0.6 * inch
    ancho_logo = 1.35 * inch
    tope = alto - 16          # borde superior del bloque de texto
    bloque = 49               # nombre (16) + tres líneas de datos (3×11)
    x_texto = margen + ancho_logo + 8

    lienzo.setFillColor(NEGRO)
    lienzo.setFont("Helvetica-Bold", 13)
    lienzo.drawString(x_texto, tope - 12, datos.get("nombre", ""))

    lienzo.setFillColor(GRIS_TEXTO)
    lienzo.setFont("Helvetica", 8.5)
    y = tope - 25
    for clave in ("direccion", "telefono", "redes_sociales"):
        dato = str(datos.get(clave) or "")
        if dato:
            lienzo.drawString(x_texto, y, dato)
        y -= 11

    if logo:
        try:
            reader = ImageReader(io.BytesIO(logo))
            ancho_px, alto_px = reader.getSize()
        except Exception:
            ancho_px = alto_px = 0
        if ancho_px and alto_px:
            escala = min(ancho_logo / ancho_px, 0.62 * inch / alto_px)
            lienzo.drawImage(
                reader, margen, tope - (bloque + alto_px * escala) / 2,
                width=ancho_px * escala, height=alto_px * escala,
                mask="auto",
            )

    lienzo.setStrokeColor(NARANJA)
    lienzo.setLineWidth(1.2)
    y_linea = alto - ENCABEZADO_ALTO + 2
    lienzo.line(margen, y_linea, ancho - margen, y_linea)

    lienzo.showPage()
    lienzo.save()
    bufer.seek(0)
    return PdfReader(bufer).pages[0]


def estampar_membrete(ruta_pdf, destino=None):
    """
    Copia un PDF con el membrete institucional estampado arriba de la
    primera página; el original no se modifica.

    El contenido de la primera página se reduce y centra dentro del espacio
    restante para que no quede encimado con el membrete. Devuelve la ruta
    de la copia (en la carpeta temporal si no se indica destino).
    """
    if destino is None:
        base, _ext = os.path.splitext(os.path.basename(str(ruta_pdf)))
        base = re.sub(r"[^\w\s-]", "", base).strip() or "documento"
        destino = os.path.join(
            tempfile.gettempdir(), f"{base}_con_membrete.pdf")

    lector = PdfReader(str(ruta_pdf))
    if not lector.pages:
        raise ValueError("El PDF no tiene páginas.")
    escritor = PdfWriter()
    escritor.append(lector)

    pagina = escritor.pages[0]
    if pagina.get("/Rotate", 0):
        pagina.transfer_rotation_to_content()
    caja = pagina.mediabox
    x0, y0 = float(caja.left), float(caja.bottom)
    ancho, alto = float(caja.width), float(caja.height)
    escala = (alto - ENCABEZADO_ALTO) / alto
    pagina.add_transformation(
        Transformation()
        .translate(-x0, -y0)
        .scale(escala, escala)
        .translate((ancho - ancho * escala) / 2, 0)
        .translate(x0, y0)
    )
    pagina.merge_transformed_page(
        _overlay_membrete(ancho, alto), Transformation().translate(x0, y0))

    with open(destino, "wb") as archivo:
        escritor.write(archivo)
    return destino


def calcular_edad(fecha_nacimiento, referencia=None):
    """Edad en años a partir de la fecha de nacimiento (texto o date)."""
    if not fecha_nacimiento:
        return None
    referencia = referencia or date.today()
    if isinstance(fecha_nacimiento, (date, datetime)):
        nacimiento = (
            fecha_nacimiento.date()
            if isinstance(fecha_nacimiento, datetime)
            else fecha_nacimiento
        )
    else:
        texto = str(fecha_nacimiento).strip()
        formatos = (
            "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d",
            "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d %H:%M:%S",
        )
        nacimiento = None
        for fmt in formatos:
            try:
                nacimiento = datetime.strptime(texto, fmt).date()
                break
            except ValueError:
                continue
        if nacimiento is None:
            solo = texto.split(" ")[0]
            for fmt in formatos:
                try:
                    nacimiento = datetime.strptime(solo, fmt).date()
                    break
                except ValueError:
                    continue
        if nacimiento is None:
            return None
    edad = referencia.year - nacimiento.year - (
        (referencia.month, referencia.day) < (nacimiento.month, nacimiento.day)
    )
    return edad if edad >= 0 else None


def ruta_acrobat():
    """Ruta del ejecutable de Acrobat, si está instalado."""
    for ruta in RUTAS_ACROBAT:
        if os.path.exists(ruta):
            return ruta
    return None


def abrir_para_imprimir(ruta):
    """
    Abre el PDF en Acrobat para revisarlo/ajustarlo antes de imprimir.

    Si Acrobat no está instalado, recurre a la aplicación predeterminada.
    """
    ejecutable = ruta_acrobat()
    if ejecutable:
        subprocess.Popen([ejecutable, ruta])  # noqa: S603
        return ejecutable
    os.startfile(ruta)  # noqa: S606  (Windows)
    return None


def nombre_pdf(prefijo, nombre_paciente):
    """Nombre de archivo PDF: '<prefijo>_<paciente>_<YYYYMMDD>.pdf'."""
    base = re.sub(r"[^\w\s-]", "", str(nombre_paciente or "paciente")).strip()
    base = re.sub(r"[\s_]+", "_", base) or "paciente"
    return f"{prefijo}_{base}_{date.today():%Y%m%d}.pdf"


def ruta_temporal_pdf(prefijo, nombre_paciente):
    return os.path.join(tempfile.gettempdir(), nombre_pdf(prefijo, nombre_paciente))
