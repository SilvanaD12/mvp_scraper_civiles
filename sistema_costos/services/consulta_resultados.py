"""Consulta y selección de resultados con filtros opcionales."""

import unicodedata


def normalizar_busqueda(valor):
    return "".join(
        caracter
        for caracter in unicodedata.normalize(
            "NFKD", str(valor or "").casefold()
        )
        if not unicodedata.combining(caracter)
    )


class ConsultaResultados:
    def __init__(self, servicio):
        self.servicio = servicio
        self.filas = {}
        self.marcados = set()
        self.guardadas = False

    def actualizar(
        self,
        guardadas=False,
        documento_id=None,
        termino="",
        obra="",
        anio=None,
        lugar="",
    ):
        filtro_obra = normalizar_busqueda(obra).strip()
        filtro_lugar = normalizar_busqueda(lugar).strip()
        filtro_anio = str(anio).strip() if anio is not None else ""

        if filtro_anio and (
            not filtro_anio.isascii()
            or not filtro_anio.isdigit()
            or len(filtro_anio) != 4
        ):
            raise ValueError(
                "El año debe tener cuatro dígitos o quedar vacío."
            )

        palabras = normalizar_busqueda(termino).split()
        filas = self.servicio.listar(guardadas=guardadas)
        visibles = []

        for fila in filas:
            if (
                documento_id is not None
                and fila["documento_id"] != documento_id
            ):
                continue

            obra_resultado = (
                fila.get("obra") or fila.get("obra_clave") or ""
            )

            if filtro_obra not in normalizar_busqueda(obra_resultado):
                continue

            if filtro_lugar not in normalizar_busqueda(
                fila.get("lugar")
            ):
                continue

            if filtro_anio:
                anio_resultado = fila.get("anio")
                if str(anio_resultado or "").strip() != filtro_anio:
                    continue

            texto = normalizar_busqueda(
                " ".join(
                    str(fila.get(campo) or "")
                    for campo in (
                        "descripcion",
                        "obra",
                        "obra_clave",
                        "anio",
                        "lugar",
                        "fuente",
                        "documento_nombre",
                        "unidad",
                        "moneda",
                        "tipo_monto",
                    )
                )
            )

            if all(palabra in texto for palabra in palabras):
                visibles.append(fila)

        self.guardadas = guardadas
        self.filas = {
            fila["id"]: fila
            for fila in visibles
        }
        self.marcados.clear()

        return visibles

    def alternar(self, identificador):
        if self.guardadas or identificador not in self.filas:
            return

        if identificador in self.marcados:
            self.marcados.remove(identificador)
        else:
            self.marcados.add(identificador)

    def seleccionar_todos(self):
        if not self.guardadas:
            self.marcados = set(self.filas)

    def cancelar(self):
        self.marcados.clear()

    def guardar(self):
        if self.guardadas:
            raise ValueError(
                "Esta vista contiene datos que ya están guardados."
            )

        if not self.marcados:
            raise ValueError(
                "Marque al menos un resultado para guardar."
            )

        return self.servicio.guardar_seleccion(
            sorted(self.marcados)
        )