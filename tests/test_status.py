from datetime import date
import unittest

from services.status import status_ocorrencia


class StatusOcorrenciaTest(unittest.TestCase):
    def test_programado_passado_vira_atrasado_no_ano_atual(self):
        hoje = date(2026, 6, 24)

        self.assertEqual(status_ocorrencia("Programado", 2026, 1, hoje), "Atrasado")

    def test_status_fechado_nao_vira_atrasado(self):
        hoje = date(2026, 6, 24)

        self.assertEqual(status_ocorrencia("Realizado", 2026, 1, hoje), "Realizado")
        self.assertEqual(status_ocorrencia("Cancelado", 2026, 1, hoje), "Cancelado")

    def test_outro_ano_nao_vira_atrasado(self):
        hoje = date(2026, 6, 24)

        self.assertEqual(status_ocorrencia("Programado", 2025, 1, hoje), "Programado")


if __name__ == "__main__":
    unittest.main()

