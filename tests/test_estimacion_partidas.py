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
    def test_metrado_decimal_y_rechazo_de_vacio_cero_o_negativo(self):
        fila = {"unidad": "m3", "moneda": "PEN", "precio_unitario_texto": "9,99"}
        calculada = calcular_partida(fila, " 2,75 ")
        self.assertEqual(calculada["metrado"], Decimal("2.75"))
        self.assertEqual(calculada["parcial"], Decimal("27.47"))
        for valor in ("", "   ", "0", "0,0000", "-2", "-0,25"):
            with self.subTest(metrado=valor), self.assertRaisesRegex(ValueError, "metrado"):
                calcular_partida(fila, valor)

    def test_fuente_preserva_documento_y_pagina_si_desaparece_pdf(self):
        with TemporaryDirectory() as directorio:
            base = Path(directorio)
            pdf = base / "Presupuesto obra.PDF"
            pdf.write_bytes(b"%PDF-1.7")
            repo = CandidatosRepository(base / "costos.db")
            repo.registrar_documento("doc", pdf.name, str(pdf), "SEACE")
            candidato = extraer_montos_generales("doc", 3, "Costo directo: S/ 450,00")[0]
            identificador = repo.guardar(candidato)
            revision = RevisionCandidatosService(repo, PartidasSeleccionadasRepository(repo.path))
            revision.guardar_seleccion([identificador])
            fila = revision.listar(guardadas=True)[0]

            fuente = revision.describir_fuente(fila)
            self.assertEqual((fuente.documento, fuente.pagina, fuente.ruta_local),
                             (pdf.name, 3, pdf.resolve()))
            self.assertTrue(fuente.disponible)
            self.assertEqual(revision.obtener_ruta_pdf(identificador), pdf.resolve())

            pdf.unlink()
            fuente = revision.describir_fuente(fila)
            self.assertEqual(fuente.estado, "no_disponible")
            self.assertFalse(fuente.disponible)
            self.assertEqual((fuente.documento, fuente.pagina, fuente.ruta_local), (pdf.name, 3, pdf))
            with self.assertRaisesRegex(FileNotFoundError, "ya no está disponible"):
                revision.obtener_ruta_pdf(identificador)

    def test_fuente_distingue_ruta_ausente_y_archivo_de_otro_tipo(self):
        servicio = RevisionCandidatosService
        self.assertEqual(servicio.describir_fuente({}).estado, "sin_ruta")
        self.assertEqual(servicio.describir_fuente({"ruta_local": "expediente.zip"}).estado, "no_es_pdf")

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
