# Guía del MVP de scraping civil

## Objetivo actual

Buscar referencias de campamentos en INFOBRAS y SEACE,
consultar sus datos y descargar documentos para su posterior
análisis técnico.

El MVP todavía no calcula presupuestos ni ratios automáticamente.

## Instalación en Windows PowerShell

Se necesita Git y Python 3.10 o superior.

Para una instalación nueva:

```powershell
git clone --branch feature/infobras-campamentos https://github.com/SilvanaD12/mvp_scraper_civiles.git
cd mvp_scraper_civiles
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install beautifulsoup4 playwright
.\.venv\Scripts\python.exe -m playwright install chromium
```

Estas dependencias permiten ejecutar los comandos de scraping
descritos aquí. La interfaz original tiene dependencias adicionales.

## INFOBRAS

Buscar obras:

```powershell
.\.venv\Scripts\python.exe buscar_obras.py --termino campamento
```

Consultar y guardar una ficha en SQLite:

```powershell
.\.venv\Scripts\python.exe consultar_obra.py --codigo 507544
```

Exportar candidatos de dos páginas a CSV:

```powershell
.\.venv\Scripts\python.exe exportar_candidatos.py --termino campamento --paginas 2
```

Listar documentos de la obra:

```powershell
.\.venv\Scripts\python.exe listar_documentos.py --codigo 507544
```

Descargar el primer documento PDF:

```powershell
.\.venv\Scripts\python.exe descargar_documento.py --codigo 507544 --numero 1
```

## SEACE

Consultar la primera página y exportar resultados a JSON:

```powershell
.\.venv\Scripts\python.exe buscar_seace.py --termino "CAMPAMENTOS" --anio 2023
```

Abrir el procedimiento piloto y listar la primera página de documentos:

```powershell
.\.venv\Scripts\python.exe listar_documentos_seace.py --termino "CAMPAMENTOS" --anio 2023 --nomenclatura "AS-SM-16-2023-OEC/PERPG-GRMOQ-1"
```

Descargar el Resumen ejecutivo:

```powershell
.\.venv\Scripts\python.exe descargar_documento_seace.py --termino "CAMPAMENTOS" --anio 2023 --nomenclatura "AS-SM-16-2023-OEC/PERPG-GRMOQ-1" --numero 2
```

Descargar las Bases Integradas:

```powershell
.\.venv\Scripts\python.exe descargar_documento_seace.py --termino "CAMPAMENTOS" --anio 2023 --nomenclatura "AS-SM-16-2023-OEC/PERPG-GRMOQ-1" --numero 4
```

Los números corresponden al listado observado para este procedimiento.
En otros procedimientos se debe consultar primero la lista.

## Archivos generados

La ubicación predeterminada en Windows es:

```text
C:\Users\<usuario>\CenitegSolutions\costos_data
```

- costos.db: fichas INFOBRAS guardadas en SQLite.
- exports: resultados CSV y JSON.
- documentos: archivos descargados y metadatos.
- documentos/seace: descargas de SEACE y metadatos.

Los datos se generan en cada computadora y no se comparten mediante Git.

## Caso piloto

- Código INFOBRAS: 507544.
- Código de inversión: 2166595.
- Proyecto: Campamentos de control y vigilancia de Lomas de Ilo.
- Procedimiento SEACE: AS-SM-16-2023-OEC/PERPG-GRMOQ-1.
- Servicio específico: instalación de estructuras en drywall
  para el campamento Sifón Tumilaca.

La ficha INFOBRAS corresponde al proyecto de campamentos.
El servicio SEACE tiene un alcance específico dentro de ese proyecto.

## Estado comprobado

- Búsqueda y consulta de fichas INFOBRAS.
- Guardado de fichas INFOBRAS en SQLite.
- Exportación de candidatos a CSV.
- Listado y descarga de documentos PDF de INFOBRAS.
- Búsqueda SEACE y exportación a JSON.
- Apertura de ficha SEACE por nomenclatura.
- Lectura de la primera página de documentos.
- Descarga SEACE comprobada con PDF y RAR.
- Guardado de metadatos de las descargas.

## Limitaciones

- SEACE consulta únicamente la primera página de resultados.
- El listado SEACE lee únicamente la primera página de documentos.
- ZIP está contemplado en el código, pero su descarga no se ha probado.
- El límite de 25 MB se comprueba después de completar la descarga.
- Las cabeceras permiten reconocer formatos; no validan todo el archivo.
- Los documentos escaneados requieren OCR para extraer su contenido.
- No se han automatizado los APUs ni validado ratios de costos.
- CAPECO está pendiente de precisar con el ingeniero.

## Continuación propuesta para Óscar

1. Reproducir los comandos del caso piloto en su computadora.
2. Implementar la paginación de resultados y documentos SEACE.
3. Incorporar el registro de procedimientos y documentos en SQLite,
   conservando su fuente y fecha de extracción.
4. Preparar la lectura de PDF y detectar páginas que requieran OCR.

Antes de iniciar cambios, crear su propia rama desde este avance:

```powershell
git switch -c feature/oscar-continuacion
```

Los metrados y costos extraídos deben mantener referencia al documento
y página de origen para su revisión por el ingeniero civil.