# Validación del extractor y de la fuente de las partidas

Revisión del 18 de noviembre de 2026. Las muestras se procesaron localmente;
sus resultados no se incorporaron a la base del usuario.

| Muestra | Recuperado | Campos sin dato o límite observado |
| --- | --- | --- |
| Suplemento COSTO de marzo de 2026, PDF original de 59 páginas | 58 páginas por texto directo y una por OCR. Un costo directo en la página 4, con descripción, monto original `117,938.53`, tipo, página y evidencia. | La moneda quedó sin identificar para ese monto. No se detectaron precios unitarios, aunque el documento sí contiene tablas: por ejemplo, la tabla visible de la página 6. El reconocimiento de esas tablas digitales queda pendiente. |
| Página 6 del mismo suplemento rasterizada a 216 ppp en un PDF de una página sin texto digital, para simular un escaneo | OCR en la única página y 26 precios unitarios candidatos con descripción, unidad, precio, moneda, página y evidencia. Se cotejaron visualmente tres partidas de muros de sostenimiento: los precios 607.51, 627.12 y 720.30 por M3 coinciden con la tabla. | No se extrajeron cantidades y no se reconocieron todas las filas. No se validaron las 26 cifras individualmente. La página registrada es la 1 del PDF de prueba, correspondiente a la 6 del original. |
| SEACE, `04 Estructuras Tumilaca E34.pdf`, lámina E-34 | Se leyó el texto digital breve «GRMPERPG» y no se generaron hallazgos de costos. | La lámina contiene dibujos y notas sin una tabla de precios. La presencia de texto breve impidió activar OCR; es un límite para páginas mixtas (imagen y texto). |

En las muestras, no se identificaron automáticamente campos de obra, año y
lugar con el formato admitido. En una descarga, esos campos también pueden
venir de los metadatos del portal cuando estén disponibles. Las cifras
recuperadas requieren revisión contra la fuente antes de usarlas para estimar.

## Comprobaciones del backend

- Datos guardados y Estimador comparten la consulta de fuente: nombre original
  registrado, ruta local y página. Si falta el PDF, la interfaz conserva la
  referencia, muestra el aviso y deshabilita **Abrir PDF**.
- Se reutilizó el cálculo del estimador. La prueba verifica que `2,75 × 9,99`
  produzca `27,47`, y que se rechacen metrado vacío, cero y valores negativos.

Ejecutar las pruebas desde el repositorio:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
