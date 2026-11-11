"""Generador de claves de activación — USO PRIVADO DEL AUTOR.

No se empaqueta en la app (nutricion_deportiva.py no lo importa, así
que PyInstaller nunca lo incluye) y NO va en el zip de distribución.

Uso:
    python generar_licencia.py                # pide el código
    python generar_licencia.py XXXX-XXXX-XXXX-XXXX

Al final pregunta si registrar la licencia en el gestor
(gestor_licencias.py) para llevar el control de quién tiene el
software y qué versión se le entregó.
"""
import sys

import gestor_licencias
import licencia
from version import VERSION


def main():
    if len(sys.argv) > 1:
        codigo = " ".join(sys.argv[1:])
    else:
        codigo = input("Código de instalación del cliente: ").strip()
    if not codigo:
        print("Sin código no hay clave.")
        return
    clave = licencia.clave_para(codigo)
    print()
    print("Código     :", codigo.strip().upper())
    print("Clave      :", clave)
    print()

    registrar = input(
        "¿Registrar en el gestor de licencias? "
        "(nombre del profesional, o ENTER para no registrar): "
    ).strip()
    if registrar:
        contacto = input("Contacto (teléfono/email, opcional): ").strip()
        gestor_licencias.init_bd()
        lic_id = gestor_licencias.registrar_licencia(
            registrar, contacto, codigo, "Registrada desde generar_licencia"
        )
        print()
        print(f"Registrada en el gestor (id {lic_id}) con la versión "
              f"v{VERSION} como entrega inicial.")
    else:
        print("No registrada.")


if __name__ == "__main__":
    main()
