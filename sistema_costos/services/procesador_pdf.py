"""Extracción local conservadora. Los resultados siempre requieren revisión civil."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from ..domain.partida_candidata import PartidaCandidata
from .extraccion_costos import (
    extraer_montos_generales, extraer_tablas, limpiar_columnas_ocr, moneda_de, normalizar,
)
from .ocr_pdf import ErrorOCR, LectorOCR


TERMINOS = {
    'APU': r'\bapus?\b',
    'Análisis de precios unitarios': r'analisis\s+de\s+precios?\s+unitarios?',
    'Precios unitarios': r'precios?\s+unitarios?',
    'Precios de partidas': r'precios\s+de\s+partidas',
    'Presupuesto': r'\bpresupuestos?\b',
    'Metrados': r'\bmetrados?\b',
    'Costo directo': r'costos?\s+directos?',
    'Inversión total': r'inversion\s+total',
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


def _filas_costo_ocr(documento_id: str, pagina: int, texto: str) -> list[PartidaCandidata]:
    """Recupera filas OE en páginas de COSTO con dos columnas leídas juntas."""
    candidatos = []
    for linea in texto.splitlines():
        inicios = [m.start() for m in re.finditer(r'(?<!\w)[O0]E\.\d+(?:\.\d+)+\*?', linea, re.I)]
        for inicio, fin in zip(inicios, inicios[1:] + [len(linea)]):
            evidencia = linea[inicio:fin].strip()
            limpia = re.sub(r'^0E(?=\.)', 'OE', limpiar_columnas_ocr(evidencia), flags=re.I)
            m = FILA_COSTO.fullmatch(limpia)
            if m is None:
                continue
            # Exigir una unidad en su propia celda. Evita convertir "H=1 M"
            # de la descripción en unidad cuando la celda de unidad no se leyó.
            celda_unidad = rf'(?:[|\[\]{{}}]\s*|\s{{2,}})_?{re.escape(m["unidad"])}\s*[|\[\]{{}}]'
            if not re.search(celda_unidad, evidencia, re.I):
                continue
            if re.search(rf'\b{NUMERO}\s+{NUMERO}\b', m['descripcion']):
                continue
            total = sum(numero(m[k]) for k in ('mo', 'mat', 'equ'))
            if abs(numero(m['pu']) - total) > Decimal('0.05'):
                continue
            candidatos.append(PartidaCandidata(
                documento_id, pagina, f"{m['codigo']} {m['descripcion'].strip()}", evidencia,
                unidad=m['unidad'], precio_unitario_texto=m['pu'], moneda=moneda_de(texto),
                monto_texto=m['pu'], tipo_monto='precio_unitario',
            ))
    # Si la cabecera es ilegible, exigir más de una fila coherente de la serie OE.
    return candidatos if len(candidatos) >= 2 else []


def extraer_partidas(documento_id: str, pagina: int, texto: str, *, ocr=False) -> list[PartidaCandidata]:
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
            monto_texto=campos['pu'], tipo_monto='precio_unitario',
            moneda='PEN' if re.search(r'S\s*/\.?|soles', texto, re.I) else None,
        ))
    existentes = {(normalizar(c.descripcion), c.unidad.casefold(), c.precio_unitario_texto)
                  for c in candidatos}
    nuevas = extraer_tablas(documento_id, pagina, texto, ocr=ocr)
    if ocr:
        nuevas.extend(_filas_costo_ocr(documento_id, pagina, texto))
    for candidato in nuevas:
        clave = (normalizar(candidato.descripcion), candidato.unidad.casefold(),
                 candidato.precio_unitario_texto)
        if clave not in existentes:
            existentes.add(clave)
            candidatos.append(candidato)
    return candidatos


@dataclass
class PaginaExtraida:
    numero: int
    texto: str
    terminos: list[str]
    metodo: str = "texto_pdf"


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
    ocr = None
    ocr_no_disponible = False
    try:
        lector = PdfReader(ruta)
        if lector.is_encrypted and not lector.decrypt(''):
            raise ValueError('El PDF está protegido. Proporcione una copia accesible para procesarlo.')
        resultado = ResultadoPDF(terminos_titulo=detectar_terminos(titulo))
        for indice, pagina in enumerate(lector.pages, 1):
            texto = pagina.extract_text() or ''
            metodo = 'texto_pdf'
            if not texto.strip() and not ocr_no_disponible:
                try:
                    if ocr is None:
                        ocr = LectorOCR(ruta)
                        if ocr.idioma == 'eng':
                            resultado.avisos.append('OCR con idioma inglés; instala español (spa) para mejorar acentos y términos.')
                    texto = ocr.leer_pagina(indice)
                    metodo = 'ocr' if texto.strip() else 'sin_texto'
                except ErrorOCR as error:
                    resultado.avisos.append(str(error))
                    if ocr is None:
                        ocr_no_disponible = True
                    metodo = 'sin_texto'
            elif not texto.strip():
                metodo = 'sin_texto'
            resultado.paginas.append(PaginaExtraida(indice, texto, detectar_terminos(texto), metodo))
            partidas = extraer_partidas(documento_id, indice, texto, ocr=metodo == 'ocr')
            montos = extraer_montos_generales(documento_id, indice, texto, ocr=metodo == 'ocr')
            # En PDFs digitales, la representación espacial puede recomponer
            # columnas que el orden interno del PDF separa en líneas.
            if metodo == 'texto_pdf' and not partidas and (resultado.terminos_titulo or detectar_terminos(texto)):
                try:
                    texto_tabular = pagina.extract_text(extraction_mode='layout') or ''
                    partidas = extraer_partidas(documento_id, indice, texto_tabular)
                    if not montos:
                        montos = extraer_montos_generales(documento_id, indice, texto_tabular)
                except (PdfReadError, ValueError):
                    resultado.avisos.append(f'Página {indice}: no se pudo recomponer la tabla digital.')
            resultado.candidatos.extend(partidas + montos)
    except (PdfReadError, OSError) as error:
        raise ValueError(f'No se pudo leer el PDF: {error}') from error
    finally:
        if ocr is not None:
            ocr.cerrar()
    paginas_ocr = [p.numero for p in resultado.paginas if p.metodo == 'ocr']
    if paginas_ocr:
        resultado.avisos.append('Texto recuperado por OCR en páginas: ' + ', '.join(map(str, paginas_ocr)) + '. La lectura puede contener errores.')
    sin_texto = sum(not p.texto.strip() for p in resultado.paginas)
    if sin_texto:
        resultado.avisos.append(f'{sin_texto} páginas sin texto extraíble: pueden requerir OCR o estar vacías.')
    resultado.avisos.append('Extracción preliminar. Los formatos no reconocidos se conservan como texto; no se infieren precios.')
    return resultado
