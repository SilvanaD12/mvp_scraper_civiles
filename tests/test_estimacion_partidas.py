from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from costeo_mvp.partidas import calcular_partida, subtotales_por_moneda
from sistema_costos.database.candidatos_repository import CandidatosRepository
from sistema_costos.database.partidas_seleccionadas_repository import PartidasSeleccionadasRepository
from sistema_costos.services.extraccion_costos import extraer_montos_generales
from sistema_costos.services.procesador_pdf import extraer_partidas
from sistema_costos.services.revision_candidatos import RevisionCandidatosService


class EstimacionPartidasTests(unittest.TestCase):
    def test_hallazgos_guardados_alimentan_el_calculo_con_su_procedencia(self):
        tabla = (
            "Presupuesto en soles\nÍtem Descripción Unidad Metrado Precio unitario Parcial\n"
            "01.01 BASE GRANULAR m3 4,50 S/ 100,00 450,00\n"
            "Costo directo: S/ 450,00"
        )
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "costos.db"
            candidatos = CandidatosRepository(ruta)
            candidatos.registrar_documento("doc", "presupuesto.pdf", "presupuesto.pdf", "SEACE", None)
            for fila in extraer_partidas("doc", 3, tabla) + extraer_montos_generales("doc", 3, tabla):
                candidatos.guardar(fila)
            revision = RevisionCandidatosService(candidatos, PartidasSeleccionadasRepository(ruta))
            revision.guardar_seleccion([fila["id"] for fila in revision.listar()])
            filas = {fila["tipo_monto"]: fila for fila in revision.listar(guardadas=True)}

        partida = calcular_partida(filas["precio_unitario"], "2,75")
        self.assertEqual(partida["parcial"], Decimal("275.00"))
        self.assertEqual((partida["documento_nombre"], partida["pagina"], partida["fuente"]),
                         ("presupuesto.pdf", 3, "SEACE"))
        with self.assertRaisesRegex(ValueError, "precio unitario"):
            calcular_partida(filas["costo_directo"], "2")
        with self.assertRaisesRegex(ValueError, "moneda"):
            calcular_partida({**filas["precio_unitario"], "moneda": None}, "2")
        with self.assertRaisesRegex(ValueError, "metrado"):
            calcular_partida(filas["precio_unitario"], "0")

        usd = calcular_partida({**filas["precio_unitario"], "moneda": "USD"}, "0,1234")
        self.assertEqual(subtotales_por_moneda([partida, usd]),
                         {"PEN": Decimal("275.00"), "USD": Decimal("12.34")})
