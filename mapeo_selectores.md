# Mapeo de Selectores DOM - Semana 2

Este documento define selectores candidatos para el MVP. Los selectores deben
validarse con Playwright antes de usarse en produccion, porque ambos sitios
pueden cambiar su estructura DOM.

## 1. Sodimac

* **URL de prueba:** https://www.sodimac.com.pe/sodimac-pe/category/cat10064/cemento
* **Contenedor principal:** `[data-testid*="product"]`
* **Contenedores alternativos:** `[class*="product-card"]`, `[class*="product-item"]`, `article`
* **Selector del precio:** `span[data-testid="price-value"]`
* **Selector principal del nombre:** `h1.product-name`
* **Selectores alternativos del nombre:** `[data-testid*="product-name"]`, `.product-name`, `h2`, `h3`
* **Selector de enlace del producto:** `a[href]`
* **SKU:** pendiente de confirmar en el DOM
* **Unidad de venta:** pendiente de confirmar en el DOM

> El selector del contenedor no debe ser el mismo selector del precio. El
> scraper debe recorrer cada contenedor y buscar dentro sus campos.

## 2. Promart

* **URL de prueba:** https://www.promart.pe/buscar?q=cemento
* **Contenedor principal:** `div.container__item--product`
* **Selector del nombre:** `h2.item__productName a`
* **Selector del precio:** `span.js-pp`
* **Selector de enlace del producto:** `h2.item__productName a[href]`
* **SKU:** pendiente de confirmar en el DOM
* **Unidad de venta:** pendiente de confirmar en el DOM

## Reglas de implementacion

1. Esperar a que el contenido dinamico termine de renderizarse antes de parsear.
2. Extraer nombre y precio desde el mismo contenedor de producto.
3. Ignorar y registrar los contenedores que no tengan nombre o precio valido.
4. Guardar la URL de origen y la fecha de extraccion junto con cada resultado.
5. Mantener selectores alternativos y registrar cual fue utilizado.

## Estado de validacion

* **Sodimac:** mapeo inicial; falta validar en ejecucion real.
* **Promart:** mapeo inicial; falta validar en ejecucion real.

