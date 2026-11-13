"""Reconoce filas de costos con encabezados explícitos y montos etiquetados."""

from decimal import Decimal
import re
import unicodedata

from ..domain.partida_candidata import PartidaCandidata


def normalizar(texto: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold())
                   if not unicodedata.combining(c))


NUM = r'\d+(?:[.,]\d+)*'
MONEDA = r'(?:S\s*/\.?|PEN\b|US\s*\$|USD\b|\$)'
PRECIO = rf'(?P<moneda>{MONEDA})?\s*(?P<precio>{NUM})'
UNIDAD = r'(?:m[23²³]|m\.l\.|ml|m|kg|t|glb|global|und\.?|unid\.?|u|pza|pto|ha|hh|hm|h|dia|día|mes|jgo|l)'
PU = r'(?:precio\s+unitario|p\s*\.\s*u(?:nit(?:ario)?)?\.?|p\s+unitario)'
CODIGO = r'(?:[A-Z]{1,3}\.)?\d+(?:\.\d+)+\*?'
INICIO_PARTIDA = re.compile(rf'^\s*{CODIGO}\s+', re.I)
FILA = {
    'unitario': re.compile(rf'^(?P<descripcion>.+?)\s+(?P<unidad>{UNIDAD})\s+{PRECIO}$', re.I),
    'metrado': re.compile(rf'^(?P<descripcion>.+?)\s+(?P<unidad>{UNIDAD})\s+(?P<cantidad>{NUM})\s+{PRECIO}$', re.I),
    'parcial': re.compile(rf'^(?P<descripcion>.+?)\s+(?P<unidad>{UNIDAD})\s+(?P<cantidad>{NUM})\s+{PRECIO}\s+(?:{MONEDA}\s*)?(?P<total>{NUM})$', re.I),
}
TIPOS_MONTO = {
    'costo directo': 'costo_directo',
    'presupuesto contractual': 'presupuesto_contractual',
    'monto contractual': 'presupuesto_contractual',
    'monto del contrato': 'presupuesto_contractual',
    'inversion total': 'inversion_total',
    'monto total de inversion': 'inversion_total',
    'presupuesto total': 'presupuesto_total',
    'valor referencial': 'valor_referencial',
}
ETIQUETAS_MONTO = {
    'costo_directo': 'Costo directo',
    'presupuesto_contractual': 'Presupuesto contractual',
    'inversion_total': 'Inversión total',
    'presupuesto_total': 'Presupuesto total',
    'valor_referencial': 'Valor referencial',
}
CONCEPTO = '|'.join(sorted(TIPOS_MONTO, key=len, reverse=True)).replace('inversion', 'inversi[oó]n')
LINEA_MONTO = re.compile(
    rf'^\s*(?P<concepto>{CONCEPTO})\s*[:=\-–]?\s*(?P<valor>.*)$', re.I)
VALOR_MONTO = re.compile(
    rf'^(?P<moneda>{MONEDA})?\s*(?P<valor>{NUM})(?:\s*(?P<posterior>soles|PEN|USD|dólares))?\s*$', re.I)


def decimal_seguro(texto: str, cantidad: bool = False) -> Decimal | None:
    """Acepta punto o coma decimal, y agrupaciones coherentes de miles."""
    if len(texto) > 30 or not re.fullmatch(NUM, texto):
        return None
    signos = set(texto) & {'.', ','}
    if not signos:
        return Decimal(texto)
    separador = ',' if texto.rfind(',') > texto.rfind('.') else '.'
    entero, fraccion = texto.rsplit(separador, 1)
    otro = ',' if separador == '.' else '.'
    if separador in entero:
        if otro not in texto and re.fullmatch(r'\d{1,3}(?:' + re.escape(separador) + r'\d{3})+', texto):
            return Decimal(texto.replace(separador, ''))
        return None
    if otro in entero:
        if not re.fullmatch(r'\d{1,3}(?:' + re.escape(otro) + r'\d{3})+', entero):
            return None
        entero = entero.replace(otro, '')
    elif len(fraccion) == 3 and not cantidad:
        # Un único separador con tres cifras puede representar miles o decimales.
        return None
    if not 1 <= len(fraccion) <= (4 if cantidad else 2):
        return None
    return Decimal(entero + '.' + fraccion)


def moneda_de(texto: str) -> str | None:
    texto = normalizar(texto)
    pen = bool(re.search(r'\bs\s*/|\bpen\b|\bsoles\b', texto))
    usd = bool(re.search(r'\bus\s*\$|\busd\b|\bdolares\b', texto))
    return 'PEN' if pen and not usd else 'USD' if usd and not pen else None


def _columnas(cabecera: str) -> str | None:
    cabecera = normalizar(cabecera)
    m = re.search(rf'\b(?:descripcion|partida|denominacion)\b.{{0,45}}?'
                  rf'\b(?:unidad|und|unid)\b\.?\s+(?P<medio>.*?)\b{PU}', cabecera)
    if not m:
        return None
    # La revista COSTO tiene columnas de componentes, no metrado/parcial.
    resto = cabecera[m.end():]
    if re.search(r'\bm\s*\.\s*o\s*\.|\bequ\s*\.', resto):
        return None
    medio = m['medio'].strip()
    con_cantidad = bool(re.fullmatch(r'(?:metrado|cantidad|cant)\.?\s*', medio))
    if medio and not con_cantidad:
        return None
    con_total = bool(re.search(r'\b(?:parcial|subtotal|total|importe)\b', resto))
    if con_total and not con_cantidad:
        return None
    return 'parcial' if con_total else 'metrado' if con_cantidad else 'unitario'


def limpiar_columnas_ocr(linea: str) -> str:
    # El OCR suele leer los bordes de las celdas como barras y corchetes.
    # Se apartan solo al interpretar la fila, sin alterar la evidencia guardada.
    return ' '.join(re.sub(r'[|\[\]{}_]', ' ', linea).split())


def extraer_tablas(documento_id: str, pagina: int, texto: str, *, ocr=False) -> list[PartidaCandidata]:
    """Interpreta tablas simples, incluidas descripciones partidas en varias líneas."""
    originales = [l.strip() for l in texto.splitlines() if l.strip()]
    lineas = [limpiar_columnas_ocr(l) for l in originales] if ocr else originales
    candidatos = []
    esquema = None
    encabezado = ''
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        if re.search(r'\b(?:descripci[oó]n|partida|denominaci[oó]n)\b', linea, re.I):
            # Se permite que el encabezado ocupe hasta tres líneas, sin absorber filas.
            bloque = [linea]
            for siguiente in lineas[i+1:i+3]:
                if re.search(r'\d', siguiente) or not re.match(
                        r'^(?:unidad|und|unid|metrado|cantidad|precio|p\s*\.|parcial|total|importe)\b',
                        normalizar(siguiente)):
                    break
                bloque.append(siguiente)
            nuevo = _columnas(' '.join(bloque))
            if nuevo:
                esquema, encabezado = nuevo, ' '.join(bloque)
                i += len(bloque)
                continue
        if not esquema:
            i += 1
            continue
        if re.match(r'^(?:sub\s*total|total|costo directo|presupuesto total|inversión total)\b', linea, re.I):
            esquema = None
            i += 1
            continue
        evidencia = [originales[i]]
        partes = [linea]
        m = FILA[esquema].fullmatch(linea)
        if m is None and INICIO_PARTIDA.match(linea):
            for j in range(i + 1, min(i + 3, len(lineas))):
                siguiente = lineas[j]
                if INICIO_PARTIDA.match(siguiente) or re.match(
                        r'^(?:total|subtotal|costo directo|presupuesto|fecha|página)\b', siguiente, re.I):
                    break
                evidencia.append(originales[j])
                partes.append(siguiente)
                m = FILA[esquema].fullmatch(' '.join(partes))
                if m:
                    break
        if m is not None:
            campos = m.groupdict()
            precio = decimal_seguro(campos['precio'])
            cantidad = decimal_seguro(campos['cantidad'], True) if campos.get('cantidad') else None
            total = decimal_seguro(campos['total']) if campos.get('total') else None
            valido = precio is not None and (esquema == 'unitario' or cantidad is not None)
            if esquema == 'parcial':
                valido = valido and total is not None and abs(cantidad * precio - total) <= Decimal('0.05')
            if valido and re.search(r'[A-Za-zÁÉÍÓÚÑáéíóúñ]', campos['descripcion']):
                candidatos.append(PartidaCandidata(
                    documento_id, pagina, ' '.join(campos['descripcion'].split()), '\n'.join(evidencia),
                    unidad=campos['unidad'], cantidad_texto=campos.get('cantidad'),
                    precio_unitario_texto=campos['precio'], monto_texto=campos['precio'],
                    tipo_monto='precio_unitario',
                    moneda=moneda_de(campos['moneda'] or encabezado),
                ))
                i += len(evidencia)
                continue
        i += 1
    return candidatos


def extraer_montos_generales(documento_id: str, pagina: int, texto: str, *, ocr=False) -> list[PartidaCandidata]:
    originales = [l.strip() for l in texto.splitlines() if l.strip()]
    lineas = [limpiar_columnas_ocr(l) for l in originales] if ocr else originales
    candidatos = []
    for i, linea in enumerate(lineas):
        concepto = LINEA_MONTO.fullmatch(linea)
        if not concepto:
            continue
        valor = concepto['valor'].strip()
        evidencia = originales[i]
        if not valor and i + 1 < len(lineas):
            valor = lineas[i+1]
            evidencia += '\n' + originales[i+1]
        importe = VALOR_MONTO.fullmatch(valor)
        if not importe or decimal_seguro(importe['valor']) is None:
            continue
        tipo = TIPOS_MONTO[normalizar(concepto['concepto'])]
        candidatos.append(PartidaCandidata(
            documento_id, pagina, ETIQUETAS_MONTO[tipo], evidencia,
            moneda=moneda_de(importe['moneda'] or importe['posterior'] or ''),
            monto_texto=importe['valor'], tipo_monto=tipo,
        ))
    return candidatos


def contexto_textual(texto: str) -> dict:
    """Solo infiere contexto desde campos explícitos y sin valores contradictorios."""
    etiquetas = {
        'obra': r'(?:obra|proyecto|nombre del proyecto)',
        'lugar': r'(?:ubicaci[oó]n|lugar)',
        'anio': r'(?:año(?: fiscal| del presupuesto)?)',
    }
    resultado = {}
    for campo, patron in etiquetas.items():
        valores = {m.strip() for m in re.findall(rf'^\s*{patron}\s*:\s*([^\r\n]{{1,250}})$',
                                               texto, re.I | re.M) if m.strip()}
        if len(valores) == 1:
            valor = valores.pop()
            if campo == 'anio':
                if not re.fullmatch(r'(?:19|20)\d{2}', valor):
                    continue
                valor = int(valor)
            resultado[campo] = valor
    return resultado
