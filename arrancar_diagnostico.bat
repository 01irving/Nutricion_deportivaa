@echo off
title Nutrición Deportiva (consola de diagnóstico)
cd /d "D:\Biblioteca\Nutrición_deportiva"
echo ===============================================
echo  Nutrición Deportiva - arranque con consola
echo  Si la app se cierra sola, el error quedará
echo  visible aquí. NO cierres esta ventana.
echo ===============================================
"venv\Scripts\python.exe" nutricion_deportiva.py 2>&1 | more
echo.
echo ===============================================
echo  La app terminó. Si viste un traceback arriba,
echo  cópialo y envíalo para diagnóstico.
echo ===============================================
pause
