"""Estado de consulta y selección; no depende de la interfaz ni cambia el esquema SQL."""
import unicodedata


def normalizar_busqueda(valor):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(valor or '').casefold())
                   if not unicodedata.combining(c))


class ConsultaResultados:
    def __init__(self, servicio):
        self.servicio = servicio
        self.filas = {}
        self.marcados = set()
        self.guardadas = False

    def actualizar(self, guardadas=False, documento_id=None, termino=''):
        filas = self.servicio.listar(guardadas=guardadas)
        palabras = normalizar_busqueda(termino).split()
        visibles = []
        for fila in filas:
            if documento_id is not None and fila['documento_id'] != documento_id:
                continue
            texto = normalizar_busqueda(' '.join(str(fila.get(k) or '') for k in
                ('descripcion', 'obra_clave', 'fuente', 'documento_nombre', 'unidad', 'moneda')))
            if all(palabra in texto for palabra in palabras):
                visibles.append(fila)
        self.guardadas = guardadas
        self.filas = {f['id']: f for f in visibles}
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
            raise ValueError('Esta vista contiene datos que ya están guardados.')
        if not self.marcados:
            raise ValueError('Marque al menos un resultado para guardar.')
        return self.servicio.guardar_seleccion(sorted(self.marcados))
