# Definición del proyecto y backlog propuesto

## Nombre

**Estimador preliminar de costos civiles con referencias documentales**

## Definición

Aplicación de escritorio local para preparar estimaciones preliminares de costo directo de tipologías civiles respaldadas por referencias validadas. El usuario selecciona una tipología, ingresa los datos que la plantilla aprobada requiere y obtiene un cálculo reproducible, con desglose disponible, fecha, ubicación, supuestos, exclusiones y fuente documental.

El cálculo se ejecuta con reglas y datos estructurados revisados. La búsqueda documental ayuda a encontrar y verificar evidencia en los suplementos COSTO y, si se incorpora una referencia adecuada, en expedientes técnicos de obra. El modelo de IA no determina ni aprueba precios.

## Problema y usuarios

El área comercial o de presupuestos necesita responder con rapidez cuánto podría costar un proyecto antes de contar con un expediente completo. La búsqueda manual de revistas y expedientes es lenta; extrapolar precios sin mostrar qué incluyen puede inducir a error.

Los usuarios iniciales son el área comercial y el personal de presupuestos, con revisión de un ingeniero civil. El resultado es referencial para evaluación preliminar; no constituye diseño ni presupuesto definitivo de ejecución.

## Fuentes y su función

| Fuente | Uso en el proyecto | Límite |
| --- | --- | --- |
| Suplementos COSTO entregados | Referencias de costo por tipología, presupuestos por partidas, precios unitarios y algunos análisis de precios unitarios. Registrar edición, vigencia, ubicación, unidad y alcance. | No todas las ediciones tienen una tipología pertinente. Algunos valores son de Lima y costo directo, sin gastos generales, utilidad, impuestos ni honorarios. La compatibilidad debe validarla el ingeniero. |
| Buscador público del SEACE | Encontrar expedientes técnicos de obra (ETO). La guía del OECE describe archivos de presupuesto de obra, análisis de precios, recursos requeridos, calendario, estudios y otros documentos del expediente. | El expediente se descarga y debe revisarse y normalizarse. No se debe prometer un scraper estable como dependencia del MVP. |
| INFOBRAS | Ubicar obras y consultar sus datos de ejecución, avance físico y financiero, cronogramas y montos agregados; ayudar a identificar referencias y contrastar su contexto. | No sustituye el presupuesto, metrado o APU. Relacionar una obra con un ETO requiere verificar su identidad, idealmente mediante su CUI y otros datos. |

## Qué cuenta como RAG

RAG **no es el motor de estimación ni un requisito para multiplicar un metrado por un precio aprobado**. Aporta valor cuando un usuario necesita buscar en muchos documentos no estructurados, localizar evidencia y recibir una síntesis con citas comprobables.

Para el MVP, es suficiente una búsqueda local de texto que devuelva documento, página y fragmento. Esto demuestra la recuperación y la trazabilidad sin introducir una API, un modelo local ni una promesa de que una respuesta generada interpretará bien tablas. Si el ingeniero confirma que la consulta semántica o la síntesis ahorra tiempo, se puede añadir un RAG acotado como siguiente etapa.

Los importes se extraen a una base estructurada y pasan por revisión antes de habilitarse para cálculo. El índice documental puede recuperar evidencia; no habilita por sí solo un precio.

## Papel del scraping

El scraping web queda fuera del MVP. Los suplementos COSTO ya son una fuente entregada y los documentos ETO se pueden localizar y descargar con el buscador público del SEACE. Se prioriza la importación asistida y la validación de una muestra real. Una prueba de automatización del SEACE solo se justifica si el proceso manual se vuelve un cuello de botella y la interfaz, los formatos y las condiciones de uso lo permiten.

## Alcance del MVP de ocho semanas

1. Acordar con el ingeniero y el responsable de negocio **una tipología piloto** y el uso previsto del resultado.
2. Cargar una muestra pequeña de referencias de esa tipología, con precio, unidad, fecha de vigencia, ubicación, alcance, documento y página.
3. Implementar una sola ruta de cálculo para el piloto. Para la demo actual, el cálculo escala el costo publicado por m². Si la tipología requiere partidas y metrados para ser útil, usar cantidades de una plantilla aprobada y precios unitarios; no mezclar ambos métodos sin una regla explícita.
4. Mostrar entradas, costo directo, cobertura, supuestos, exclusiones y referencias. Exportar el resultado a CSV o Excel.
5. Buscar en PDFs seleccionados y mostrar los fragmentos con número de página.
6. Comparar al menos un caso con el presupuesto fuente y revisar el comportamiento con el ingeniero.
7. Entregar la app ejecutable desde Python, guía de uso, modelo de datos y casos de validación. Empaquetar instalador si queda capacidad.

## Fuera del MVP

- Tres familias de obra implementadas simultáneamente.
- Lectura automática de planos o generación automática de metrados.
- Scraping programado de SEACE, INFOBRAS o comercios.
- Indexación de todas las publicaciones, OCR de todos los documentos o carga masiva desatendida.
- Chatbot generativo como interfaz principal, modelo propio o dependencia obligatoria de una API/modelo local.
- Diseño estructural, evaluación de seguridad, presupuesto definitivo o promesa de precisión general.
- Ajustes automáticos por zona, antigüedad, flete, tipo de cambio o inflación sin un método aprobado.

## Criterios de aceptación para el piloto

- El ingeniero aprueba la tipología, las características mínimas de entrada, la referencia base y qué conceptos incluye el total.
- Para el caso de referencia, el cálculo de la aplicación coincide con el cálculo manual usando la misma regla y el redondeo acordado.
- Cada costo utilizado muestra fuente, edición/fecha, ubicación, unidad y alcance; no se presenta un total completo si faltan partidas necesarias.
- El usuario puede ubicar una fuente en su PDF desde la pantalla de resultados.
- El cálculo da el mismo resultado con el buscador o el modelo desconectados.
- El usuario ve explícitamente que el resultado es preliminar y qué conceptos no incluye.

## Demo local disponible

La carpeta `costeo_mvp` contiene una primera demo ejecutable. Incluye cuatro referencias resumidas de los PDFs entregados, una proyección lineal por área, el desglose del presupuesto de la losa deportiva publicada en agosto y una búsqueda léxica en PDFs con página de origen. La losa deportiva es un caso de prueba documentado, no una selección definitiva del piloto empresarial.

Ejecutar con `python app.py`; la búsqueda de PDFs requiere `pypdf`. Para verificar el cálculo de muestra: `python app.py --smoke-check`.

## Backlog propuesto

| Orden | Trabajo | Criterio de cierre |
| --- | --- | --- |
| P0 | Validar piloto y alcance con ingeniero y negocio | Tipología única, inputs mínimos, conceptos incluidos/excluidos, referencia base y caso de comparación acordados. |
| P0 | Probar una referencia COSTO de extremo a extremo | Importar una muestra, conservar unidad/vigencia/ubicación/página y cotejar importes contra el PDF. |
| P0 | Confirmar disponibilidad de un ETO de SEACE pertinente | Descargar manualmente un expediente y verificar que contiene presupuesto, metrados o APUs útiles para el piloto. |
| P1 | Normalizar catálogo y precios en SQLite | Datos candidatos y aprobados separados; unidad, moneda, fecha, zona y alcance obligatorios; origen conservado. |
| P1 | Implementar el cálculo único del piloto | Regla validada; resultado repetible; entradas incompatibles o datos faltantes se rechazan o se muestran como cobertura parcial. |
| P1 | Terminar vista de resultados y exportación | Desglose, supuestos, exclusiones, procedencia y exportación reproducible. |
| P1 | Añadir búsqueda documental | Consulta sobre PDFs seleccionados devuelve página y fragmento; los PDFs que requieren OCR se identifican como no indexados. |
| P1 | Validar con casos manuales | Caso base y límites comparados con el ingeniero; defectos críticos corregidos y evidencia guardada. |
| P2 | Automatizar una importación repetitiva | Solo después de identificar una fuente estable, formatos descargables y volumen que justifiquen automatización. |
| P2 | Incorporar RAG generativo | Solo si las pruebas muestran que la síntesis mejora la consulta; citas verificables y abstención ante falta de respaldo. |
| P2 | Soportar otra tipología o empaquetar instalador | Empezar cuando el piloto esté validado y las horas disponibles lo permitan. |

## Cambios puntuales recomendados a los documentos actuales

- **Charter:** conservar la separación entre IA y cálculo, la trazabilidad y el carácter referencial. Cambiar el título para no llamar al proyecto “RAG” como si fuera el producto; registrar una sola tipología como alcance MVP y describir RAG como recuperación documental opcional/condicionada.
- **Backlog:** sustituir el esquema inmediato de tres tipologías por la decisión de un piloto; separar importar/validar datos de extraerlos automáticamente; dejar dos métodos de cálculo como etapas y comenzar por el que corresponda al caso fuente; cambiar la integración obligatoria con LLM/modelo local por búsqueda de evidencia; poner scraping, OCR masivo, segunda tipología y empaquetado avanzado en prioridad posterior.
- Los 102 puntos del backlog actual son una estimación relativa, no horas. No son suficientes para concluir capacidad sin conocer las horas semanales reales; sí muestran que el alcance reúne demasiadas líneas de trabajo para presentarlas todas como MVP comprometido.

## Decisiones para la reunión del viernes

1. ¿Qué tipología de las fuentes entregadas resuelve primero una necesidad real del área?
2. ¿Qué referencia concreta acepta el ingeniero como comparable y qué incluye/excluye su costo?
3. ¿El primer resultado debe ser costo por m² o presupuesto por partidas y metrados?
4. ¿Qué características mínimas debe pedir el formulario para que la estimación sea razonable?
5. ¿Qué fuente o ETO descargado se usará para validar el caso de prueba?
6. ¿Se acepta que la primera demo recupere evidencia por texto y página sin generar respuestas con un LLM?
