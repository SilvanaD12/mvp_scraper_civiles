# Sistema Escalable de Web Scraping para Costos Civiles

MVP local de Ceniteg Solutions para extraer precios de proveedores de materiales, normalizar unidades de obra, consolidar estadistica descriptiva y exportar reportes `.xlsx`.

## Alcance de la Fase 1

- SQLite local con Foreign Keys, indices y un modelo normalizado en 3FN.
- Scrapers desacoplados mediante una interfaz ABC con reintentos y logging.
- Implementacion inicial de Sodimac con Playwright para renderizado y BeautifulSoup4 para parseo.
- ETL con pandas: limpieza de precios, normalizacion de unidades APU y consolidacion por producto/unidad.
- Exportacion Excel con hojas `Precios`, `Consolidado` y `Resumen`.
- GUI de escritorio en modo oscuro con customtkinter.
- Estructura preparada para PyInstaller.

No se incluyen APIs web, servicios en la nube, tareas cron, scraping estatal avanzado ni Machine Learning.

## Estructura

```text
mvp_scraper_civiles/
├── sistema_costos/
│   ├── config/           # Rutas, parametros y logging estructurado
│   ├── database/         # Conexion SQLite, esquema y repositorios
│   ├── scrapers/         # Contrato base y bots por proveedor
│   ├── services/         # ETL y exportacion Excel
│   ├── ui/               # Ventana y componentes customtkinter
│   └── main.py
├── mapeo_selectores.md   # Selectores candidatos por proveedor
├── main.py               # Launcher de desarrollo y PyInstaller
├── requirements.txt
└── README.md
```

## Instalacion

Requiere Python 3.10 o superior.

```powershell
cd mvp_scraper_civiles
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

## Ejecucion

Desde la raiz del repositorio:

```powershell
python -m sistema_costos.main
```

Tambien se puede usar el launcher raiz:

```powershell
python main.py
```

La primera ejecucion crea los datos en `%USERPROFILE%\CenitegSolutions\costos_data`, incluyendo `costos.db`, `exports/` y `logs/`. Para cambiar la ubicacion se puede definir `CENITEG_DATA_DIR`.

La GUI solicita una URL de Sodimac. El extractor actual es un MVP y sus selectores deben mantenerse junto con los cambios del sitio proveedor.

## Empaquetado futuro

```powershell
pyinstaller --noconfirm --windowed --name CenitegCostos `
  --add-data "sistema_costos/database/schema.sql;database" `
  main.py
```

## Siguientes incrementos sugeridos

1. Agregar adapters para Aceros Arequipa, CAPECO e INEI respetando `BaseScraper`.
2. Incorporar pruebas unitarias de parseo, normalizacion y repositorios con una base temporal.
3. Extraer selectores por proveedor a configuracion versionada y agregar control de cambios.
4. Crear instalador Windows y politica de actualizacion local.
