# Extracción de partidas, montos y archivos comprimidos

El trabajo se apoya en la pantalla unificada y los filtros de SQLite de Silvana.
La rama `feature/extraccion-tablas-montos-archivos` parte de `main` con esos cambios.

## Cómo comprobar el flujo

1. Abra `INICIAR_MVP.cmd`. En **Procesar PDFs**, cargue un suplemento COSTO
   y pulse **Procesar**. En un documento guardado, **Ver documentos** permite
   seleccionarlo para procesarlo de nuevo.
2. Consulte las columnas **Precio unitario** y **Monto general**. Las partidas
   muestran su unidad y precio; los montos generales muestran su concepto en
   la descripción y no se guardan como precios unitarios.
3. En **Guardados**, seleccione una descarga PDF, ZIP o RAR y pulse
   **Procesar descarga**. Si está marcado **Procesar al descargar**, también
   se ejecuta tras la descarga. Los PDFs del comprimido aparecen como
   documentos independientes; el estado muestra cuántos se procesaron.
4. Use los filtros de obra, año y lugar cuando exista ese contexto. Los campos
   ausentes quedan vacíos en la base.

Si un documento no produce hallazgos, la tabla de resultados lo indica.
Para liberar espacio, seleccione un archivo en **Guardados → Eliminar
descarga**. La confirmación incluye sus datos procesados asociados.
Las fichas y búsquedas del portal se conservan para volver a descargar
el documento cuando sea necesario.

Para OCR se necesitan `requirements-ocr.txt` y Tesseract, de preferencia con
español. Para RAR se usa `tar` con soporte RAR (el bsdtar de Windows verificado).
ZIP no necesita un descompresor externo. Se extraen solo PDFs con cabecera
válida, con un límite de 40 PDFs y 400 MiB por archivo comprimido; los archivos
protegidos o entradas incompatibles pueden quedar sin procesar.

## Datos que entrega el extractor

| Campo | Regla |
|---|---|
| Documento, fuente y página | Identificador y ruta local de la evidencia. En ZIP/RAR se conserva el archivo y nombre de la entrada. |
| Obra, año y lugar | Campos explícitos del PDF o metadatos disponibles de la fuente. Cuando solo se dispone de la fecha de publicación, el año es el de publicación. |
| Descripción, unidad y cantidad | En partidas se conservan los valores reconocidos en columnas. Los montos generales no tienen unidad o cantidad. |
| Monto y tipo | `precio_unitario`, `costo_directo`, `presupuesto_contractual`, `inversion_total`, `presupuesto_total` o `valor_referencial`, según el concepto de la fuente. |
| Evidencia | Texto extraído del PDF o del OCR, incluyendo las líneas que se asociaron a la fila. |

Para las filas con metrado y parcial se contrasta cantidad × precio. Para
las filas de COSTO se contrasta la suma de componentes. El OCR conserva
el texto leído y descarta filas ambiguas; las columnas ilegibles y los
formatos no admitidos siguen requiriendo cotejo manual. Los montos generales
se extraen de etiquetas explícitas y nunca se usan para inferir un precio.

## Comprobación local

- Suplementos digitales de enero y febrero de 2026: 687 precios unitarios y
  un costo directo identificados en cada suplemento.
- Página 6 del suplemento de enero, procesada como imagen por Tesseract:
  se recuperaron cuatro filas. Se cotejaron código, unidad y precio con el
  texto del PDF digital; las demás filas requieren otra estrategia o revisión.
- Descargas reales de SEACE: un ZIP con un PDF y un RAR con trece PDFs.
  El flujo conservó la procedencia y procesó los catorce PDFs. En esos
  documentos no se reconocieron partidas de costos.
- Pruebas locales para filas con coma decimal, OCR, separación de montos,
  filtros y procesamiento de ZIP.

Los datos siguen siendo candidatos. Conectar el estimador y comprobar un
caso con partidas validadas es una actividad conjunta posterior.

## Estimar por partidas guardadas

1. En **Procesar PDFs**, guarda las partidas cuyos precios quieras usar.
2. Abre **Datos guardados**, selecciona una fila y pulsa **Enviar al estimador**.
3. Coteja el precio y la unidad con el documento y la página indicados.
   Ingresa el metrado de tu proyecto en esa unidad.
4. En **Estimador → Por partidas**, revisa los parciales y el subtotal por
   moneda. Puedes quitar una fila o volver a enviarla para cambiar el metrado.

Cada parcial se redondea a dos decimales antes de sumarlo. El cálculo usa
precios unitarios con unidad y moneda registrada, y conserva la referencia
del documento. La lista de cálculo dura lo que dura la sesión. El cálculo
por m² sigue disponible en la pestaña **Estimar**.
