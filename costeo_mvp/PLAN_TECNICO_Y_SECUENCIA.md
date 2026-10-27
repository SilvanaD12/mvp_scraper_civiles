# Plan técnico y secuencia de trabajo

## Producto que vamos a construir

Aplicación de escritorio para Windows que prepara estimaciones preliminares de costo directo usando referencias documentales verificadas. Para cada resultado mostrará tipología, entradas, fórmula, unidad, fecha, ubicación, documento y página, desglose disponible, supuestos y exclusiones.

El alcance inicial se limita a una tipología que el ingeniero elija entre las referencias que realmente pueden validar. La demo ya permite ensayar el flujo con cuatro ratios de COSTO y el presupuesto desglosado de la losa deportiva; eso no significa que la empresa haya elegido esa tipología como piloto.

## Papel de cada tecnología

- **Tkinter:** interfaz de escritorio local y formularios.
- **Python:** validación de entradas y cálculos deterministas. El modelo de lenguaje no calcula importes.
- **SQLite:** catálogo de partidas, referencias, fuentes y estimaciones guardadas en la versión del MVP.
- **PDF:** pypdf extrae texto por página para permitir búsquedas y conservar citas. Los precios que se usan en cálculos se revisan y aprueban antes de almacenarse.
- **Búsqueda/RAG:** localizar evidencia en documentos y mostrar página. La búsqueda actual es léxica. RAG semántico y síntesis con LLM se añaden solo si el piloto prueba que aportan valor y el ingeniero acepta el modo de verificar citas.
- **Scraping:** fuera del flujo crítico. Las fuentes se descargan o seleccionan manualmente durante el MVP; los importes se normalizan y revisan.
- **Exportación:** CSV para la demo; Excel puede añadirse como entregable después de validar el formato de presupuesto.

## Arquitectura objetivo

```text
┌──────────────────────────────────────────────────────┐
│ Presentación: Tkinter                                │
│ Formularios · resultados · búsqueda de evidencia     │
└──────────────────────┬───────────────────────────────┘
                       │ llama casos de uso
┌──────────────────────▼───────────────────────────────┐
│ Aplicación                                           │
│ Estimar · buscar evidencia · importar · exportar     │
└──────────────┬───────────────────────┬───────────────┘
               │                       │
┌──────────────▼────────────┐  ┌───────▼────────────────┐
│ Dominio                   │  │ Puertos/contratos      │
│ Reglas, unidades,         │  │ Repositorio, lector    │
│ validación, costo         │  │ PDF, buscador, export. │
└───────────────────────────┘  └───────┬────────────────┘
                                       │ adaptadores
                         ┌─────────────▼─────────────────┐
                         │ Infraestructura               │
                         │ SQLite · pypdf · índice local │
                         │ CSV/Excel · LLM opcional      │
                         └───────────────────────────────┘
```

La interfaz no contiene fórmulas ni SQL. Los casos de uso coordinan el flujo. El dominio valida unidades y ejecuta cálculos con datos aprobados. Los adaptadores leen/escriben SQLite, extraen texto por página y exportan. Esto permite probar el cálculo sin abrir la ventana ni conectar un modelo.

## Estructura de código objetivo

```text
costeo_mvp/
  app.py                         # punto de entrada Tkinter
  config.py                      # rutas y opciones locales
  domain/
    entities.py                  # Reference, CostItem, Estimate
    units.py                     # unidades y conversiones permitidas
    estimator.py                 # ratios o partidas aprobadas
    validation.py                # entradas, vigencia, cobertura
  application/
    estimate_project.py          # caso de uso de estimación
    search_evidence.py           # caso de uso de búsqueda
    import_document.py           # ingesta y revisión de candidatos
    export_estimate.py           # salida CSV/Excel
  infrastructure/
    sqlite_repository.py
    pdf_reader.py
    lexical_search.py            # primero; semantic_search.py opcional
    csv_exporter.py
  ui/
    main_window.py
    estimate_view.py
    evidence_view.py
  data/
    app.db                       # se crea al ejecutar; no versionar datos privados
    seed_references.json         # datos de demo únicamente
  docs/
    data_dictionary.md
    validation_cases.md
```

La demo actual está concentrada en `app.py` y `data/cost_references.json`. No conviene modularizar todo antes de acordar el piloto. Al terminar esa decisión, se separan primero dominio/cálculo, búsqueda PDF y vista Tkinter, conservando la demo mientras se migra.

## Flujo de datos y cálculo

1. Seleccionar un PDF local o importar un registro ya revisado.
2. Extraer texto y páginas; conservar título de la fuente, edición, vigencia, ubicación y ruta/página.
3. Registrar los valores como **candidatos**. Una persona revisa nombre, precio, unidad, moneda, alcance, inclusión de flete, impuestos y vigencia contra la página original.
4. El ingeniero aprueba la referencia; solo entonces pasa al catálogo habilitado para cálculo.
5. El usuario ingresa los parámetros que la plantilla validada exige.
6. Python verifica unidades, tipología y cobertura, y calcula por la regla acordada: cantidad × precio unitario, o un ratio compatible × su cantidad base. No sumar dos veces un costo global y sus partidas.
7. Mostrar resultado, desglose sustentado, referencias, fecha, supuestos y faltantes. Si falta una partida requerida, rotular como cobertura parcial.
8. Guardar la versión de la estimación y exportarla. La copia guardada conserva qué datos y versiones de referencia se usaron.

RAG, cuando se incorpore, solo recupera fragmentos para explicar o localizar evidencia. El resultado numérico sale del catálogo estructurado, no de texto generado.

## Secuencia recomendada

| Etapa | Trabajo | Resultado verificable |
| --- | --- | --- |
| Antes/durante la reunión del viernes | Ejecutar la demo; mostrar búsqueda con PDF/página y cálculo de una referencia conocida. Pedir al ingeniero que elija una tipología, confirme entradas, alcance del costo y referencia de validación. | Acta breve de decisiones y un caso manual que la aplicación debe reproducir. |
| Semana 1 | Delimitar el piloto y auditar la fuente; escoger un ETO de SEACE solo si es comparable y se puede descargar. Definir unidad, fecha, zona, componentes y exclusiones. | Especificación del piloto y tabla de datos de muestra cotejada. |
| Semana 2 | Separar el código en dominio, aplicación, infraestructura y UI. Crear SQLite, migración inicial y carga de datos aprobados. | La app carga el catálogo persistido; la fórmula se prueba sin UI. |
| Semanas 3-4 | Implementar la ruta de cálculo única del piloto y los formularios con las variables aprobadas. Agregar manejo de unidades, errores y datos faltantes. | Un cálculo completo y reproducible con desglose trazable. |
| Semana 5 | Implementar importación asistida y búsqueda local de PDFs con cita de página. Evaluar si la consulta léxica basta; decidir si hace falta recuperación semántica. | Evidencia de consultas conocidas y lista de formatos que requieren OCR/revisión manual. |
| Semana 6 | Completar resultado, historial de estimaciones y exportación elegida con negocio. | La exportación coincide con la pantalla y conserva fuentes/supuestos. |
| Semana 7 | Validación con el ingeniero: caso base, unidades, referencia incompatible, faltantes, fechas, costos indirectos y redondeos. | Matriz de casos, defectos priorizados y aprobación de comportamiento esperado. |
| Semana 8 | Corregir, preparar instalación local y documentación/demostración. Solo empaquetar instalador si no pone en riesgo la validación. | Entrega reproducible en el equipo objetivo, guía breve y límites conocidos. |

Los hitos se reordenan según la disponibilidad semanal real y las revisiones del ingeniero. Si la capacidad es baja, se conserva un flujo completo de una tipología y se aplazan historial avanzado, segunda tipología, OCR masivo, RAG generativo y empaquetado.

## Decisiones para cerrar con el ingeniero

1. Tipología piloto y usuario que tomará decisiones con el resultado.
2. Qué datos hacen comparable una referencia; qué datos son obligatorios al estimar.
3. Si la primera regla es costo directo por m² o cantidad por precio unitario/APU.
4. Si se requiere desglosar mano de obra, materiales y equipos o solo partidas.
5. Qué conceptos incluye el total: gastos generales, utilidad, IGV, flete y honorarios.
6. Caso real de validación, método de comparación y tolerancia aceptable.
7. Si la búsqueda con cita de página es suficiente para la demo o RAG generativo es requisito institucional.

## Cómo explicar la demo actual

La interfaz `app.py` es una ventana Tkinter. **Sí está implementada para abrirse e interactuar localmente** con `python app.py`. El chequeo no gráfico confirmó Tkinter, el cálculo de S/ 119,269.64 para la referencia publicada de 540 m² y que el desglose cuadra; una consulta al PDF de agosto recupera la página 2. La demo no contiene un modelo generativo ni usa scraping. Para probarla:

```powershell
cd "C:\Users\SEBASTIAN\Documents\ChatGPT\practicas pre profesionales\costeo_mvp"
python -m pip install -r requirements.txt
python app.py
```

