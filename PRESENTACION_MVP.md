# Avance para presentar a Miguel · 16 de octubre de 2026

## Qué puedes decir al comenzar

“Integramos la búsqueda y descarga de referencias civiles en una aplicación de
escritorio. Podemos consultar INFOBRAS y SEACE, seleccionar el procedimiento,
descargar documentos y conservar su procedencia. El siguiente paso es convertir
un caso validado en un presupuesto por partidas.”

## Abrir la aplicación

Doble clic en `INICIAR_MVP.cmd`. Se abre una ventana con tres pestañas:
INFOBRAS, SEACE y Guardados. Esta copia ya tiene entorno, navegador y consultas
reales guardadas. No hace falta usar comandos durante la reunión.

## Recorrido de unos cinco minutos

1. En INFOBRAS, dejar el código `507544` y pulsar **Consultar código**.
   Mostrar nombre, CUI, entidad, monto publicado, fuente y documentos.
   La consulta verificada devolvió 11 documentos.
2. Seleccionar la resolución `RGG N°084-2023-GG-PERPG/GR.MOQ` y pulsar
   **Descargar documento**. Cuando termine, usar **Abrir última descarga**.
3. En SEACE, buscar `CAMPAMENTOS`, año `2023`.
   En la comprobación del 16 de octubre aparecieron 12 filas en la primera página.
4. Pulsar **Seleccionar caso piloto**. El procedimiento es
   `AS-SM-16-2023-OEC/PERPG-GRMOQ-1`. Se verifica la selección antes de abrirlo.
5. Mostrar los cinco documentos listados. Descargar **Resumen ejecutivo** o
   **Bases Integradas** y abrir el resultado. Las Bases Integradas son un RAR.
6. En **Guardados**, seleccionar una ficha y pulsar **Reabrir selección**.
   Explicar que es una consulta almacenada con fecha, no una consulta nueva.
   Una descarga guardada se abre localmente desde esa misma pestaña.

La consulta SEACE vuelve a abrir el portal para verificar cada ficha o descarga;
puede tardar varios segundos. El progreso indica que la operación sigue en curso.

## Si el portal falla durante la reunión

Usar **Guardados**: elegir una fila de tipo `ficha` de INFOBRAS o SEACE y
**Reabrir selección**. Para mostrar documentos ya descargados, elegir una fila
de tipo `descarga`. No se necesita Internet para esas dos acciones.

Los botones de búsqueda y descarga sí requieren conexión, incluso si la ficha
se abrió desde el historial. El estado **GUARDADO** evita confundir datos anteriores
con una consulta actualizada.

## Qué se comprobó realmente

- Búsqueda INFOBRAS: 110 coincidencias; 20 filas en la primera página.
- Obra 507544, CUI 2166595; 11 documentos listados.
- Resolución descargada: PDF de 426.971 bytes, abierto con lector PDF de biblioteca,
  cinco páginas sin texto extraíble.
- SEACE: 12 filas para CAMPAMENTOS/2023; identidad del procedimiento verificada.
- Ficha piloto: cinco documentos listados.
- Consultas reales sin coincidencias en ambos portales y segunda página INFOBRAS:
  comprobadas correctamente.
- Resumen ejecutivo: PDF de 225.137 bytes, dos páginas sin texto extraíble.
- Bases Integradas: RAR de 11.638.023 bytes, con 12 planos PDF y un PDF de bases.
- El PDF de bases se extrajo y abrió correctamente: 78 páginas. Las páginas
  técnicas examinadas (23–25 del PDF) contienen imágenes escaneadas; extraer
  sus encabezados no equivale a extraer su contenido técnico.
- Ocho pruebas locales de persistencia, versiones, manejo de respuestas vacías,
  selección de fichas/documentos y metadatos: aprobadas.
- Prueba de integración de la interfaz: cuatro vistas con datos reales,
  operación en segundo plano y recuperación tras un error controlado: aprobada.

Los conteos describen la comprobación de esta fecha; los portales pueden actualizarse.
Los datos reales están en `datos_locales/`, excluidos de Git.

## Lo que aún falta

- SEACE: páginas posteriores de resultados y documentos.
- Obtener/revisar metrados, APUs y composición de mano de obra, materiales y equipos.
- Lectura/OCR de las páginas técnicas, con cotejo humano de las tablas.
- Motor de presupuesto y validación del especialista civil.

La captura es el avance presentado hoy. Los montos de INFOBRAS y SEACE corresponden
a alcances diferentes: el proyecto de campamentos y un servicio concreto.
El monto de SEACE no debe dividirse entre una cantidad de muros para inferir un APU.

## Acuerdos que necesitas llevarte de la reunión

1. Definición del componente a estimar y qué conceptos incluye.
2. Un ejemplo de presupuesto, metrados y APUs que el civil pueda validar.
3. Responsable y fecha de revisión técnica; conservar el objetivo de entrega
   de noviembre y ajustar el alcance con esa disponibilidad.

## Continuación entre Oscar y Silvana

- Oscar: interfaz, persistencia, descarga y trazabilidad del flujo integrado.
- Silvana: inventario de partidas y datos de los documentos del piloto; contraste
  con COSTO y listado de precios/APUs que faltan.
- Miguel: revisión de integración y prioridad de automatización.
- Especialista civil: alcance, unidades, metrados, rendimientos y aceptación del cálculo.

El avance está en la rama local `codex/oscar-integracion-mvp`, basada en
`origin/feature/infobras-campamentos` (`4ab26bf`).
