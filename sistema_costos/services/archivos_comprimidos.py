"""Extrae únicamente PDFs de ZIP/RAR a nombres locales controlados."""

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import stat
import subprocess
from threading import Event, Timer
from zipfile import BadZipFile, ZipFile


MAX_PDFS = 40
MAX_PDF_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 400 * 1024 * 1024
MAX_LISTADO_BYTES = 2 * 1024 * 1024


@dataclass
class ExtraccionArchivo:
    pdfs: list[tuple[str, Path]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _nombre_valido(nombre: str) -> bool:
    posix = PurePosixPath(nombre.replace('\\', '/'))
    windows = PureWindowsPath(nombre)
    return (len(nombre) <= 1024 and bool(posix.name) and
            not posix.is_absolute() and not windows.drive and
            '..' not in posix.parts and not any(ord(c) < 32 for c in nombre))


def _guardar_pdf(flujo, destino: Path, nombre: str, limite: int) -> tuple[Path, int]:
    # El nombre interno no se utiliza como ruta del sistema de archivos.
    final = destino / (sha256(nombre.encode('utf-8')).hexdigest() + '.pdf')
    temporal = final.with_suffix('.part')
    try:
        with temporal.open('wb') as salida:
            cabecera = flujo.read(8)
            if len(cabecera) > limite:
                raise ValueError('se alcanzó el límite total de extracción')
            if not cabecera.startswith(b'%PDF-'):
                raise ValueError('el contenido no tiene cabecera PDF')
            total = len(cabecera)
            salida.write(cabecera)
            while bloque := flujo.read(65536):
                total += len(bloque)
                if total > limite:
                    raise ValueError('el PDF supera el límite de extracción')
                salida.write(bloque)
        return temporal, total
    except BaseException:
        temporal.unlink(missing_ok=True)
        raise


@contextmanager
def _tar_flujo(argumentos, segundos):
    import os
    ejecutable = shutil.which('tar')
    if not ejecutable:
        raise ValueError('Para abrir RAR se necesita tar con soporte RAR (bsdtar).')
    opciones = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    vencido = Event()
    with subprocess.Popen([ejecutable, *argumentos], stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **opciones) as proceso:
        def expirar():
            vencido.set()
            if proceso.poll() is None:
                proceso.kill()

        reloj = Timer(segundos, expirar)
        reloj.daemon = True
        reloj.start()
        try:
            yield proceso.stdout
            codigo = proceso.wait(timeout=5)
            if vencido.is_set():
                raise ValueError('se agotó el tiempo de lectura del RAR')
            if codigo:
                raise ValueError('RAR no compatible, protegido o dañado; compruebe el archivo.')
        finally:
            reloj.cancel()
            if proceso.poll() is None:
                proceso.kill()


def _patron_literal(nombre: str) -> str:
    # bsdtar usa patrones glob para escoger miembros, incluso con "--".
    escapes = {'[': '[[]', '*': '[*]', '?': '[?]'}
    return ''.join(escapes.get(c, c) for c in nombre)


def _extraer_miembros(nombres, abrir, destino: Path) -> ExtraccionArchivo:
    resultado = ExtraccionArchivo()
    pdfs = [n for n in nombres if n.casefold().endswith('.pdf')]
    repetidos = Counter(pdfs)
    bytes_restantes = MAX_TOTAL_BYTES
    if len(pdfs) > MAX_PDFS:
        resultado.avisos.append(f'Se procesan como máximo {MAX_PDFS} PDFs por archivo.')
    for nombre in pdfs[:MAX_PDFS]:
        temporal = None
        if not _nombre_valido(nombre) or repetidos[nombre] > 1:
            resultado.avisos.append('Se omitió una entrada PDF con ruta inválida o repetida.')
            continue
        try:
            if bytes_restantes <= 0:
                resultado.avisos.append('Se alcanzó el límite total de extracción.')
                break
            with abrir(nombre) as flujo:
                temporal, tamano = _guardar_pdf(flujo, destino, nombre, min(MAX_PDF_BYTES, bytes_restantes))
            final = temporal.with_suffix('.pdf')
            temporal.replace(final)
            bytes_restantes -= tamano
            resultado.pdfs.append((nombre, final))
        except (OSError, RuntimeError, ValueError, BadZipFile, subprocess.TimeoutExpired) as error:
            resultado.avisos.append(f'{nombre}: {error}')
        finally:
            if temporal is not None:
                temporal.unlink(missing_ok=True)
    return resultado


def extraer_pdfs(ruta: Path, destino: Path) -> ExtraccionArchivo:
    if not ruta.is_file():
        raise ValueError('No se encontró el archivo comprimido.')
    destino.mkdir(parents=True, exist_ok=True)
    if ruta.suffix.lower() == '.zip':
        try:
            with ZipFile(ruta) as archivo:
                miembros = {i.filename: i for i in archivo.infolist() if not i.is_dir()}

                def abrir(nombre):
                    info = miembros[nombre]
                    if stat.S_ISLNK(info.external_attr >> 16):
                        raise ValueError('se omitió un enlace')
                    if info.file_size > MAX_PDF_BYTES:
                        raise ValueError('el PDF supera el límite de extracción')
                    return archivo.open(info)

                nombres = [i.filename for i in archivo.infolist() if not i.is_dir()]
                return _extraer_miembros(nombres, abrir, destino)
        except BadZipFile as error:
            raise ValueError('No se pudo abrir el ZIP: archivo inválido o dañado.') from error
    if ruta.suffix.lower() == '.rar':
        ruta = ruta.resolve()
        with _tar_flujo(['-tf', str(ruta)], 30) as flujo:
            listado = flujo.read(MAX_LISTADO_BYTES + 1)
            if len(listado) > MAX_LISTADO_BYTES:
                raise ValueError('El RAR contiene demasiadas entradas para procesarlo.')
        nombres = listado.decode('utf-8', errors='replace').splitlines()
        return _extraer_miembros(
            nombres, lambda n: _tar_flujo(['-xOf', str(ruta), '--', _patron_literal(n)], 120), destino)
    raise ValueError('Formato de archivo no compatible. Seleccione ZIP o RAR.')
