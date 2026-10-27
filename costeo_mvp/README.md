# Costeo Civil MVP

Aplicación de escritorio local para demostrar dos flujos basados en documentos de costos:

1. Estimar costo directo a partir de una referencia COSTO publicada por m².
2. Buscar texto en PDFs y mostrar documento y página para revisar la evidencia original.

En la pestaña **Estimar**, el resultado se actualiza al cambiar el área o seleccionar otra referencia.

## Ejecutar

Requiere Python 3.10 o posterior y Tkinter. Para buscar dentro de PDFs, instalar `pypdf`:

```powershell
python -m pip install -r requirements.txt
python app.py
```

El cálculo usa datos curados en `data/cost_references.json`; no descarga datos de Internet. En la pestaña **Buscar en PDFs**, selecciona manualmente los suplementos COSTO o expedientes ETO descargados de SEACE.

## Límites de esta demo

- Los importes son costos directos referenciales con fecha y ubicación indicadas; no incluyen gastos generales, utilidad, impuestos ni honorarios cuando la fuente así lo señala.
- La estimación escala linealmente una referencia por área. No genera metrados de diseño ni ajusta por sistema estructural, altura, suelo, transporte o especificaciones distintas.
- La búsqueda es léxica con recuperación de páginas; no hay generación con LLM ni extracción automática de importes desde tablas.
- Los resultados requieren revisión de un profesional antes de usarlos para una decisión comercial o de ejecución.

## Verificación rápida

```powershell
python app.py --smoke-check
```

