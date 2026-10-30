"""Extracción local conservadora. Los resultados siempre requieren revisión civil."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import unicodedata

from ..domain.partida_candidata import PartidaCandidata


def normalizar(texto: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold())
                   if not unicodedata.combining(c))


TERMINOS = {
    'APU': r'\bapus?\b',
    'Análisis de precios unitarios': r'analisis\s+de\s+precios?\s+unitarios?',
    'Precios unitarios': r'precios?\s+unitarios?',
    'Precios de partidas': r'precios\s+de\s+partidas',
    'Presupuesto': r'\bpresupuestos?\b',
    'Metrados': r'\bmetrados?\b',
    'Costo directo': r'costos?\s+directos?',
}


def detectar_terminos(texto: str) -> list[str]:
    texto = normalizar(texto)
    return [nombre for nombre, patron in TERMINOS.items() if re.search(patron, texto)]


NUMERO = r'(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}'
UNIDAD = r'(?:M[23²³]|M|KG|GLB|UND|PZA|PTO|ML|HA|H|DIA|MES|JGO)'
# COSTO: código, descripción, unidad, P.U., M.O., MAT., EQU.
FILA_COSTO = re.compile(
    rf'^\s*(?P<codigo>[A-Z]{{1,3}}\.\d+(?:\.\d+)+\*?)\s+'
    rf'(?P<descripcion>.+?)(?P<unidad>{UNIDAD})\s+'
    rf'(?P<pu>{NUMERO})\s+(?P<mo>{NUMERO})\s+'
    rf'(?P<mat>{NUMERO})\s+(?P<equ>{NUMERO})\s*$', re.I)
# Presupuesto tabular simple, aceptado solo con encabezados explícitos.
FILA_PRESUPUESTO = re.compile(
    rf'^\s*(?P<codigo>\d{{1,3}}(?:\.\d{{1,3}})+)\s+'
    rf'(?P<descripcion>.+?)\s+(?P<unidad>{UNIDAD})\s+'
    rf'(?P<cantidad>{NUMERO})\s+(?P<pu>{NUMERO})\s+(?P<total>{NUMERO})\s*$', re.I)


def numero(texto: str) -> Decimal:
    return Decimal(texto.replace(',', ''))


def extraer_partidas(documento_id: str, pagina: int, texto: str) -> list[PartidaCandidata]:
    """Solo formatos comprobables; no adivina columnas ni completa valores ausentes."""
    cabecera = normalizar(texto)
    es_costo = ('precios de partidas' in cabecera and
                re.search(r'p\s*\.\s*u\s*\.', cabecera) is not None)
    es_presupuesto = ('presupuesto' in cabecera and 'metrado' in cabecera and
                      re.search(r'precio\s+unitario|p\s*\.\s*u\s*\.', cabecera) is not None)
    candidatos = []
    for linea in texto.splitlines():
        coincidencia = FILA_COSTO.fullmatch(linea) if es_costo else None
        tipo = 'costo'
        if coincidencia is None and es_presupuesto:
            coincidencia = FILA_PRESUPUESTO.fullmatch(linea)
            tipo = 'presupuesto'
        if coincidencia is None:
            continue
        campos = coincidencia.groupdict()
        try:
            pu = numero(campos['pu'])
            if tipo == 'costo':
                suma = sum(numero(campos[k]) for k in ('mo', 'mat', 'equ'))
                if abs(pu - suma) > Decimal('0.05'):
                    continue
            elif abs(numero(campos['cantidad']) * pu - numero(campos['total'])) > Decimal('0.05'):
                continue
        except InvalidOperation:
            continue
        candidatos.append(PartidaCandidata(
            documento_id=documento_id, pagina=pagina,
            descripcion=f"{campos['codigo']} {campos['descripcion'].strip()}",
            texto_evidencia=linea.strip(), unidad=campos['unidad'],
            cantidad_texto=campos.get('cantidad'), precio_unitario_texto=campos['pu'],
            moneda='PEN' if re.search(r'S\s*/\.?|soles', texto, re.I) else None,
        ))
    return candidatos


@dataclass
class PaginaExtraida:
    numero: int
    texto: str
    terminos: list[str]


@dataclass
class ResultadoPDF:
    paginas: list[PaginaExtraida] = field(default_factory=list)
    candidatos: list[PartidaCandidata] = field(default_factory=list)
    terminos_titulo: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def estado(self) -> str:
        if not any(p.texto.strip() for p in self.paginas):
            return 'requiere_ocr'
        if self.candidatos:
            return 'candidatos_encontrados'
        return 'sin_partidas_reconocidas'


def procesar_pdf(ruta: Path, documento_id: str, titulo: str) -> ResultadoPDF:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    if ruta.suffix.lower() != '.pdf' or not ruta.is_file():
        raise ValueError('Seleccione un archivo PDF existente. ZIP y RAR deben descomprimirse primero.')
    try:
        lector = PdfReader(ruta)
        if lector.is_encrypted and not lector.decrypt(''):
            raise ValueError('El PDF está protegido. Proporcione una copia accesible para procesarlo.')
        resultado = ResultadoPDF(terminos_titulo=detectar_terminos(titulo))
        for indice, pagina in enumerate(lector.pages, 1):
            texto = pagina.extract_text() or ''
            resultado.paginas.append(PaginaExtraida(indice, texto, detectar_terminos(texto)))
            resultado.candidatos.extend(extraer_partidas(documento_id, indice, texto))
    except (PdfReadError, OSError) as error:
        raise ValueError(f'No se pudo leer el PDF: {error}') from error
    sin_texto = sum(not p.texto.strip() for p in resultado.paginas)
    if sin_texto:
        resultado.avisos.append(f'{sin_texto} páginas sin texto extraíble: pueden requerir OCR o estar vacías.')
    resultado.avisos.append('Extracción preliminar. Los formatos no reconocidos se conservan como texto; no se infieren precios.')
    return resultado
