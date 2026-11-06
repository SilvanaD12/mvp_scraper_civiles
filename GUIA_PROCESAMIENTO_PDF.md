# Avance: documentos de costos y partidas candidatas

Esta versión conecta el scraper y la carga manual con la extracción local de
texto, el registro SQLite y la pantalla de selección desarrollada por Silvana.
No genera todavía presupuestos de obras nuevas ni utiliza un LLM o RAG generativo.

## Abrir

Ejecutar `INICIAR_MVP.cmd` desde la carpeta del repositorio. Para preparar otro
equipo, seguir el README e instalar `requirements-mvp.txt` actualizado (incluye
`pypdf`). El código de esta entrega está en `feature/procesamiento-pdf`.

## Recorrido de presentación

1. En INFOBRAS o SEACE, consultar una obra y mostrar los documentos. Se priorizan
   los títulos con APU, análisis de precios unitarios, presupuesto o metrados.
   La casilla **Solo títulos de costos** limita la lista por nombre. Un documento
   sin señales en el título también puede contener costos: puede descargarse y
   procesarse normalmente desactivando la casilla.
2. Descargar un PDF. Con **Procesar al descargar** activado, la aplicación extrae
   el texto en segundo plano y cambia a **Procesar PDFs**. El historial también
   permite elegir una descarga anterior y pulsar **Procesar PDF guardado**.
3. Para mostrar información de precios con una fuente conocida, abrir **Procesar
   PDFs → Cargar PDF** y seleccionar un suplemento COSTO proporcionado por la
   empresa. Las cargas manuales se copian a la carpeta local de documentos.
4. Seleccionar el documento procesado. Mostrar las páginas con palabras clave,
   consultar una página y buscar una palabra dentro del texto extraído.
5. Pulsar **Revisar hallazgos**. Se abre la pantalla de Silvana contra la misma
   base. Seleccionar una partida, consultar su evidencia y abrir el PDF original.
   **Guardar seleccionados** incorpora los hallazgos a una lista de consulta;
   no constituye una aprobación técnica del precio.

En este equipo se preparó una carga real del suplemento de enero de 2026. Los
PDFs y los datos locales no se suben a GitHub: Silvana debe cargar sus archivos.

La comprobación local produjo 687 candidatos en ese suplemento de 59 páginas;
todos siguen pendientes de revisión. Un resumen ejecutivo descargado de SEACE
se procesó sin reconocer partidas; un memorando de INFOBRAS sin texto extraíble
quedó señalado para posible OCR. Estos resultados permiten mostrar tanto un
caso de extracción como los límites del sistema sin simular precios.

## Qué se extrae

- Texto completo por página y términos detectados en título y contenido.
- Filas COSTO con encabezado de precios de partidas y columnas P.U., M.O., MAT.
  y EQU. Se conserva el P.U. como texto; los componentes quedan en la evidencia.
  Se exige que su suma coincida con el precio, con tolerancia de cinco céntimos.
- Presupuestos simples con encabezados de presupuesto, metrado y precio unitario,
  y una fila con código, descripción, unidad, cantidad, P.U. y parcial. Se comprueba
  la multiplicación. Ambos formatos requieren números con punto decimal y dos
  decimales (se admite coma como separador de miles).
- Documento, página física del PDF (empieza en 1), descripción y evidencia original
  en el modelo `PartidaCandidata` de Silvana. Los datos ingresan como pendientes.

No se interpretan tablas arbitrarias ni filas partidas entre varias líneas.
La moneda solo se registra cuando la página incluye una indicación reconocible
de soles. Los montos totales de procedimientos no se convierten en partidas.

## Dónde queda la información

El lanzador usa `datos_locales/costos.db`. Las tablas existentes de búsquedas y
descargas se conservan. La extracción usa las tablas de revisión de Silvana y
añade `procesamiento_pdf` (resumen del procesamiento) y `paginas_pdf` (texto,
número de página y palabras clave). El archivo y su huella SHA-256 quedan
relacionados con la evidencia. Reprocesar una misma entrada no duplica los
candidatos ni elimina revisiones existentes.

## Límites que deben explicarse

- Una coincidencia de palabras indica relevancia posible, no calidad del costo.
- Las páginas sin texto se señalan para posible OCR. OCR aún no se ejecuta.
  Hay documentos de INFOBRAS escaneados entre las descargas de este equipo.
- Un PDF digital puede procesarse sin producir candidatos: su tabla puede usar
  otro formato. El texto se conserva para consulta y futuras mejoras.
- Año, región, alcance, vigencia, impuestos y comparabilidad requieren validación
  civil antes de usar los precios para estimar una obra.
- La integración actual es de fuentes y procesamiento; la demo anterior de costeo
  conserva sus referencias curadas, sin sustituirlas automáticamente por hallazgos.

## Ejecutar desde consola

```powershell
$env:CENITEG_DATA_DIR = Join-Path (Get-Location) 'datos_locales'
.\.venv\Scripts\python.exe -m scripts.procesar_pdf "C:\ruta\documento.pdf" --obra "Referencia del documento"
```
