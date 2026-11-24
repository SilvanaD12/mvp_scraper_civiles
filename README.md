# CENITEG · Referencias de obras civiles

Para el avance de extracción de tablas, montos generales y descargas ZIP/RAR,
ver [Guía de extracción del avance 7](GUIA_EXTRACCION_AVANCE_7.md).

## Procesamiento de PDFs (29 de octubre de 2026)

La pestaña **Procesar PDFs** permite cargar documentos internos o procesar las
descargas del scraper, conservar texto por página y registrar partidas candidatas
en las tablas de revisión de Silvana. Los documentos se priorizan por términos
de costos; los PDFs sin texto se identifican para posible OCR.

Ver **[GUIA_PROCESAMIENTO_PDF.md](GUIA_PROCESAMIENTO_PDF.md)** para la demo,
los formatos admitidos y las limitaciones. Actualizar dependencias con
`.\.venv\Scripts\python.exe -m pip install -r requirements-mvp.txt`.

Aplicación de escritorio para buscar obras en INFOBRAS y procedimientos en SEACE,
consultar documentos y guardar evidencia para el análisis de costos.

## Avance del 16 de octubre de 2026

- Pestañas INFOBRAS, SEACE y Guardados, integradas con los scrapers de Silvana.
- Búsqueda por término/código en INFOBRAS y por término/año en SEACE.
- Consulta de fichas, listado de documentos y descarga con procedencia y SHA-256.
- Historial local: las fichas y descargas guardadas se pueden abrir sin Internet.
- SQLite: procedimientos, documentos, consultas y versiones de descargas.
- Red y navegador fuera del hilo de la interfaz; progreso y errores visibles.
- Verificación del procedimiento y del documento antes de descargar.

**SEACE consulta la primera página de resultados y documentos.**
**Los montos mostrados son datos de las fuentes; aún no se calculan presupuestos.**
El alcance del piloto requiere metrados, APUs y validación civil.

Al consultar SEACE, la aplicación comprueba que sus scripts y controles estén
listos y que la respuesta corresponda a la búsqueda enviada. Una respuesta
HTTP 403 indica que el portal rechazó una solicitud o recurso; HTTP 429 indica
un límite de consultas. En esos casos muestra el motivo y no guarda una búsqueda
vacía como si fuera un resultado nuevo. La app no omite las validaciones del
portal; se debe comprobar el acceso en el navegador y volver a intentar cuando
esté disponible. Las consultas almacenadas siguen accesibles desde Guardados.

## Abrir en este equipo

Doble clic en `INICIAR_MVP.cmd` desde el Explorador. El entorno y el navegador
están preparados en la copia de trabajo de Oscar.
Ver `PRESENTACION_MVP.md` para el recorrido y los resultados comprobados.

## Preparar otro equipo Windows

1. Descargar el proyecto completo y extraer el ZIP a una carpeta local con
   permiso de escritura. No ejecutar los archivos desde dentro del ZIP.
2. Tener instalado Python 3.10 o superior para Windows, con pip y Tcl/Tk.
3. Con conexión a Internet, ejecutar **`PREPARAR_MVP.cmd`** con doble clic.
   Crea `.venv`, instala los paquetes de `requirements-ocr.txt` (que incluye
   `requirements-mvp.txt`), descarga Chromium y comprueba los componentes.
4. Revisar el resultado. Luego abrir **`INICIAR_MVP.cmd`**.

El archivo de preparación no instala Python ni Tesseract en Windows. Si falta
Tesseract o sus idiomas, muestra un aviso; las búsquedas y los PDFs digitales
siguen disponibles si las comprobaciones del entorno base finalizaron bien.
Para activar el OCR, instalar Tesseract con español (`spa`) y/o inglés (`eng`)
siguiendo su [documentación de instalación](https://tesseract-ocr.github.io/tessdoc/Installation.html).
La app busca Tesseract en PATH y en las ubicaciones habituales de Windows.
Para otra ubicación, definir `TESSERACT_CMD` con la ruta al ejecutable.
La lectura de RAR necesita `tar` con soporte RAR (`bsdtar`); ZIP no necesita
un programa externo.

Para repetir solo el diagnóstico, sin instalar ni descargar paquetes:

```powershell
.\PREPARAR_MVP.cmd --verificar
```

El diagnóstico comprueba las importaciones, las dependencias de Python, el
inicio de Chromium con una página local y una ejecución de OCR en una página
de prueba. No consulta los portales ni modifica los documentos o la base de
datos. La conexión y disponibilidad de INFOBRAS/SEACE se prueban desde la app.

Preparación manual equivalente, desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.browsers'
.\.venv\Scripts\python.exe -m playwright install chromium
.\INICIAR_MVP.cmd
```

El lanzador usa `datos_locales/` para SQLite, documentos y logs,
y `.browsers/` para Chromium. Esas carpetas y `.venv/` se excluyen de Git.
Los datos de una computadora no se transfieren con el código.

Los comandos de Silvana siguen disponibles. Sin `CENITEG_DATA_DIR`, usan la
ubicación original `%USERPROFILE%\CenitegSolutions\costos_data`.
Para compartir datos con la interfaz de este lanzador:

```powershell
$env:CENITEG_DATA_DIR = Join-Path (Get-Location) 'datos_locales'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.browsers'
```

## Caso piloto y verificaciones

```powershell
# Consultas reales y descargas públicas; guarda resultados para la interfaz.
.\.venv\Scripts\python.exe -m scripts.preparar_caso_piloto --fuente ambas --descargar --bases

# Pruebas locales, sin acceso a portales.
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Ventana temporal; usa el historial real del caso piloto.
.\.venv\Scripts\python.exe -m scripts.verificar_interfaz
```

El caso de captura usa INFOBRAS 507544 y SEACE
`AS-SM-16-2023-OEC/PERPG-GRMOQ-1` (CAMPAMENTOS, 2023).
La relación de alcance entre proyecto y servicio necesita revisión civil;
no se deduce un precio por m² del monto global del servicio.

## Código

- `sistema_costos/ui/references_app.py`: pantallas y cola de tareas de fondo.
- `sistema_costos/services/references_service.py`: búsqueda, consulta y descarga.
- `sistema_costos/database/references_repository.py`: historial y persistencia.
- `sistema_costos/scrapers/`: conectores, con validación antes de descargar.
- `tests/`: versiones, errores y selección de documentos.

Los módulos anteriores de Sodimac, ETL y exportación se conservan.
`requirements.txt` incluye sus dependencias y las del MVP con OCR.
`requirements-mvp.txt` contiene los paquetes mínimos sin OCR;
`requirements-ocr.txt` incluye esos mínimos y los paquetes Python del OCR.
La instalación de paquetes usa el [formato de requisitos de pip](https://pip.pypa.io/en/stable/user_guide/#requirements-files).
Chromium se prepara por separado con el [instalador de navegadores de Playwright](https://playwright.dev/python/docs/browsers).

## Siguiente entrega

1. Confirmar con el civil qué componente del campamento se va a estimar.
2. Revisar términos de referencia y planos; identificar metrados y APUs.
3. Extraer texto/OCR con documento y página y revisar los valores.
4. Implementar y contrastar un presupuesto por partidas.
5. Añadir paginación SEACE y ampliar referencias cuando el piloto esté estable.
