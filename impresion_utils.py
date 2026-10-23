"""
Utilidades compartidas de impresión (ReportLab + Windows).

- calcular_edad: edad en años a partir de la fecha de nacimiento.
- abrir_para_imprimir: abre el archivo con la aplicación predeterminada.
- ruta_temporal_pdf: arma la ruta de un PDF temporal con prefijo y paciente.
"""
import os
import re
import subprocess
import tempfile
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    Table,
    TableStyle,
)

# ----------------------------------------------------------------------
# Membrete: datos del profesional que encabezan los reportes imprimibles
# ----------------------------------------------------------------------
DATOS_PROFESIONAL = {
    "nombre": "Irving Gualberto Euan Dzul",
    "direccion": "Calle 21 Num 42. Nunkiní, Calkiní, Camp.",
    "telefono": "9961059072",
    "redes_sociales": "facebook: Irving Euan",
}

RUTA_LOGO = r"C:\Users\hp\Pictures\Saved Pictures\Nutritio-Hominis.png"

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
    """Logo institucional si el archivo existe; si no, devuelve None."""
    if not RUTA_LOGO or not os.path.exists(RUTA_LOGO):
        return None
    try:
        ancho_px, alto_px = ImageReader(RUTA_LOGO).getSize()
    except Exception:
        return None
    if not ancho_px or not alto_px:
        return None
    escala = ancho / float(ancho_px)
    return RLImage(RUTA_LOGO, width=ancho, height=alto_px * escala)


def crear_membrete(ancho_total=6.3 * inch):
    """
    Flowables del membrete institucional: logo + datos del profesional.

    Devuelve una lista (puede ir vacía si no hay datos configurados).
    """
    datos = DATOS_PROFESIONAL
    if not datos:
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
