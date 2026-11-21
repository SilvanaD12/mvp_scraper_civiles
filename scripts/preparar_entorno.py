"""Prepara el entorno local de Windows y comprueba sus dependencias."""

import argparse
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


RAIZ = Path(__file__).resolve().parent.parent
PYTHON_ENTORNO = RAIZ / '.venv' / 'Scripts' / 'python.exe'
sys.path.insert(0, str(RAIZ))


def ejecutar(argumentos):
    subprocess.run([str(valor) for valor in argumentos], cwd=RAIZ, check=True)


def verificar():
    errores = []
    avisos = []
    if Path(sys.prefix).resolve() != (RAIZ / '.venv').resolve():
        print('[ERROR] Falta preparar el entorno .venv de esta copia.')
        print('Ejecute PREPARAR_MVP.cmd sin argumentos.')
        return 1

    print('\nComprobando esta copia de la aplicacion...')
    for modulo in ('tkinter', 'sqlite3', 'bs4', 'customtkinter', 'pypdf',
                   'PIL', 'pypdfium2', 'playwright.sync_api', 'sistema_costos.main'):
        try:
            importlib.import_module(modulo)
            print(f'[OK] {modulo}')
        except Exception as error:
            errores.append(f'{modulo}: {error}')

    try:
        ejecutar([sys.executable, '-m', 'pip', 'check'])
    except subprocess.CalledProcessError:
        errores.append('Hay dependencias de Python ausentes o incompatibles.')

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            navegador = playwright.chromium.launch(headless=True, timeout=20_000)
            try:
                pagina = navegador.new_page()
                pagina.set_content('<title>CENITEG</title>')
                if pagina.title() != 'CENITEG':
                    raise RuntimeError('No se pudo comprobar la pagina local.')
            finally:
                navegador.close()
        print('[OK] Chromium inicia y abre una pagina local sin Internet.')
    except Exception as error:
        errores.append(f'Chromium: {error}')

    try:
        from pypdf import PdfWriter
        from sistema_costos.services.ocr_pdf import LectorOCR

        with tempfile.TemporaryDirectory(prefix='ceniteg_verificacion_') as temporal:
            ruta = Path(temporal) / 'verificacion.pdf'
            with PdfWriter() as documento:
                documento.add_blank_page(width=300, height=300)
                documento.write(ruta)
            lector = LectorOCR(ruta)
            try:
                lector.leer_pagina(1)
                print(f'[OK] OCR ejecutado en pagina de prueba; idiomas: {lector.idioma}.')
            finally:
                lector.cerrar()
    except Exception as error:
        avisos.append(f'OCR no disponible: {error}')

    tar = shutil.which('tar')
    if tar:
        resultado = subprocess.run([tar, '--version'], capture_output=True,
                                   text=True, errors='replace', timeout=15)
        if resultado.returncode == 0 and 'bsdtar' in resultado.stdout.lower():
            print('[OK] bsdtar detectado para RAR; ZIP usa la biblioteca de Python.')
        else:
            avisos.append('No se detecto bsdtar. La lectura de RAR puede no funcionar; ZIP sigue disponible.')
    else:
        avisos.append('No se encontro tar/bsdtar para RAR; ZIP sigue disponible.')

    for aviso in avisos:
        print(f'[AVISO] {aviso}')
    for error in errores:
        print(f'[ERROR] {error}')
    if errores:
        print('\nCorrija los errores y vuelva a ejecutar PREPARAR_MVP.cmd.')
        return 1

    print('\nEntorno base listo. Abra INICIAR_MVP.cmd.')
    if avisos:
        print('Hay funciones opcionales pendientes. Revise los avisos anteriores.')
        print('Para Tesseract e idiomas: https://tesseract-ocr.github.io/tessdoc/Installation.html')
    print('Este diagnostico no comprueba la disponibilidad de INFOBRAS o SEACE.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verificar', action='store_true',
                        help='Comprueba el entorno existente sin instalar paquetes.')
    argumentos = parser.parse_args()
    if os.name != 'nt' or sys.version_info < (3, 10):
        print('Se necesita Windows y Python 3.10 o superior.')
        return 1

    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(RAIZ / '.browsers')
    if argumentos.verificar:
        return verificar()

    print('CENITEG - Preparacion local. Se necesita conexion a Internet.', flush=True)
    if not PYTHON_ENTORNO.is_file():
        if (RAIZ / '.venv').exists():
            print('La carpeta .venv existe pero no contiene un Python valido.')
            print('No se modifico. Revise esa carpeta antes de volver a preparar.')
            return 1
        print('[1/4] Creando entorno .venv...', flush=True)
        ejecutar([sys.executable, '-m', 'venv', RAIZ / '.venv'])
    else:
        print('[1/4] Reutilizando el entorno .venv existente.', flush=True)

    ejecutar([PYTHON_ENTORNO, '-c',
              'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'])
    print('[2/4] Instalando paquetes de Python (incluye lectura de PDF y OCR)...', flush=True)
    ejecutar([PYTHON_ENTORNO, '-m', 'pip', 'install', '-r', 'requirements-ocr.txt'])
    print('[3/4] Preparando Chromium para el scraper...', flush=True)
    ejecutar([PYTHON_ENTORNO, '-m', 'playwright', 'install', 'chromium'])
    print('[4/4] Verificando componentes...', flush=True)
    ejecutar([PYTHON_ENTORNO, Path(__file__).resolve(), '--verificar'])
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.SubprocessError) as error:
        print(f'\n[ERROR] No se completo la preparacion: {error}')
        print('Revise la conexion, los permisos y el mensaje del componente que fallo.')
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nPreparacion cancelada. Puede volver a ejecutar PREPARAR_MVP.cmd.')
        sys.exit(1)
