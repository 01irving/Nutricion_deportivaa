# -*- coding: utf-8 -*-
"""Utilidades compartidas para automatizar midietasmae.com.mx con sesion
persistente (perfil de Edge) y re-login asistido si la sesion expira."""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
PERFIL = BASE / '_smae_perfil_edge'
MAX_ESPERA_LOGIN_SEG = 15 * 60


class SesionSMAE:
    def __init__(self):
        self._p = sync_playwright().start()
        ctx = None
        for canal in ('msedge', 'chrome'):
            try:
                ctx = self._p.chromium.launch_persistent_context(
                    user_data_dir=str(PERFIL), channel=canal,
                    headless=False,
                    viewport={'width': 1400, 'height': 900})
                self.canal = canal
                break
            except Exception:
                ctx = None
        if ctx is None:
            raise RuntimeError('No hay Edge ni Chrome disponibles')
        self.ctx = ctx
        self.pagina = ctx.pages[0] if ctx.pages else ctx.new_page()

    CRED = BASE / '_smae_credenciales.txt'

    def login_automatico(self):
        """Inicia sesion con las credenciales locales si el archivo existe."""
        if not self.CRED.exists():
            return False
        lineas = [l.strip() for l in self.CRED.read_text(
            encoding='utf-8').splitlines() if l.strip()]
        if len(lineas) < 2:
            return False
        correo, contrasena = lineas[0], lineas[1]
        pag = self.pagina
        campo_correo = pag.locator(
            'input[type="email"], input[type="text"]:below(input[type="password"]), '
            'input[id*="ail"], input[name*="ail"], input[id*="orreo"], '
            'input[name*="orreo"]').first
        try:
            campo_correo.fill(correo, timeout=8000)
        except Exception:
            return False
        pag.locator('input[type="password"]').first.fill(contrasena)
        boton = pag.locator(
            'button:has-text("Ingresar"), input[value="Ingresar"], '
            'a:has-text("Ingresar")').first
        try:
            boton.click(timeout=8000)
        except Exception:
            pag.keyboard.press('Enter')
        pag.wait_for_timeout(4000)
        return pag.locator('input[type="password"]').count() == 0

    def ir(self, url, selector_espera='a[href*="Salir"]', timeout_sel=60000):
        """Navega y espera un elemento que solo existe con sesion iniciada
        (el enlace Salir del encabezado); si reaparece el login, intenta
        iniciar sesion con las credenciales locales y reintenta."""
        for intento in range(3):
            self.pagina.goto(url, wait_until='domcontentloaded', timeout=45000)
            try:
                self.pagina.wait_for_selector(selector_espera,
                                              state='visible',
                                              timeout=timeout_sel)
                return
            except Exception:
                hay_password = self.pagina.locator(
                    'input[type="password"]').count() > 0
                if not hay_password:
                    raise
                if self.login_automatico():
                    print('(re-login automatico OK)', flush=True)
                    continue
                print('SESION EXPIRADA y sin credenciales automaticas: '
                      'inicia sesion en la ventana de Edge.', flush=True)
                inicio = time.time()
                while time.time() - inicio < MAX_ESPERA_LOGIN_SEG:
                    if self.pagina.locator(
                            'input[type="password"]').count() == 0:
                        break
                    self.pagina.wait_for_timeout(3000)
                else:
                    raise RuntimeError('Login no completado a tiempo')

    def buscar(self, termino, ms=3000):
        """Escribe en el buscador global y espera el autocompletado."""
        buscador = self.pagina.locator('#txtBuscar')
        buscador.click()
        buscador.fill(termino)
        self.pagina.wait_for_timeout(ms)
        return self.pagina.locator('#resultadosBusqueda li')

    def cerrar(self):
        try:
            self.ctx.close()
        finally:
            self._p.stop()
