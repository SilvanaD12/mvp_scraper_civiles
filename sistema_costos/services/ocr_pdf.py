"""OCR local opcional con PDFium y Tesseract, sin enviar documentos a servicios externos."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


class ErrorOCR(RuntimeError):
    """El OCR no está instalado o no pudo completar una página."""


class LectorOCR:
    def __init__(self, ruta: Path):
        self.documento = None
        try:
            import pypdfium2 as pdfium
        except ImportError as error:
            raise ErrorOCR('Faltan dependencias OCR. Ejecuta: python -m pip install pypdfium2 Pillow') from error
        opciones = [os.environ.get('TESSERACT_CMD'), shutil.which('tesseract'),
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    str(Path.home() / 'AppData/Local/Programs/Tesseract-OCR/tesseract.exe')]
        self.ejecutable = next((str(p) for p in opciones if p and Path(p).is_file()), None)
        if not self.ejecutable:
            raise ErrorOCR('No se encontró Tesseract OCR. Instálalo y vuelve a procesar el documento.')
        try:
            respuesta = subprocess.run([self.ejecutable, '--list-langs'], capture_output=True,
                                      timeout=15, **self._opciones())
            idiomas = respuesta.stdout.decode('utf-8', errors='replace').splitlines()
            disponibles = {linea.strip() for linea in idiomas}
            self.idioma = 'spa+eng' if {'spa', 'eng'} <= disponibles else (
                'spa' if 'spa' in disponibles else 'eng' if 'eng' in disponibles else None)
            if respuesta.returncode or self.idioma is None:
                raise ErrorOCR('Tesseract no tiene los idiomas español (spa) o inglés (eng) disponibles.')
            self.documento = pdfium.PdfDocument(str(ruta))
        except ErrorOCR:
            raise
        except Exception as error:
            raise ErrorOCR(f'No se pudo iniciar OCR: {error}') from error

    @staticmethod
    def _opciones():
        return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}

    def leer_pagina(self, numero: int) -> str:
        pagina = bitmap = None
        try:
            pagina = self.documento[numero - 1]
            ancho, alto = pagina.get_size()
            # 300 dpi habituales; limita la memoria para páginas de gran formato.
            escala = min(300 / 72, (25_000_000 / max(ancho * alto, 1)) ** .5)
            bitmap = pagina.render(scale=escala)
            with tempfile.TemporaryDirectory(prefix='ceniteg_ocr_') as temp:
                imagen = Path(temp) / 'pagina.png'
                with bitmap.to_pil() as captura:
                    captura.save(imagen)
                respuesta = subprocess.run(
                    [self.ejecutable, str(imagen), 'stdout', '-l', self.idioma, '--psm', '6'],
                    capture_output=True, timeout=90, **self._opciones())
                if respuesta.returncode:
                    detalle = respuesta.stderr.decode('utf-8', errors='replace').strip()
                    raise ErrorOCR(f'Tesseract no pudo leer la página {numero}: {detalle[:250]}')
                return respuesta.stdout.decode('utf-8', errors='replace').strip()
        except subprocess.TimeoutExpired as error:
            raise ErrorOCR(f'El OCR superó 90 segundos en la página {numero}.') from error
        except ErrorOCR:
            raise
        except Exception as error:
            raise ErrorOCR(f'No se pudo leer por OCR la página {numero}: {error}') from error
        finally:
            if bitmap is not None:
                bitmap.close()
            if pagina is not None:
                pagina.close()

    def cerrar(self):
        if self.documento is not None:
            self.documento.close()
            self.documento = None
