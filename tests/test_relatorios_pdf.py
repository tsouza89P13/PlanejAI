import unittest
from datetime import date

from services.relatorios_pdf import (
    gerar_pdf_backlog,
    gerar_pdf_dashboard,
    gerar_pdf_mapa_52w,
    gerar_pdf_ocorrencias_semana,
)


class RelatoriosPDFTest(unittest.TestCase):
    def test_relatorios_principais_geram_pdf_valido(self):
        ano = date.today().year
        semana = date.today().isocalendar()[1]

        relatorios = [
            gerar_pdf_dashboard(ano),
            gerar_pdf_backlog(ano),
            gerar_pdf_mapa_52w(ano),
            gerar_pdf_ocorrencias_semana(ano, semana),
        ]

        for pdf in relatorios:
            self.assertTrue(pdf.startswith(b"%PDF-"))
            self.assertGreater(len(pdf), 1000)


if __name__ == "__main__":
    unittest.main()
