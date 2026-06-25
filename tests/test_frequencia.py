import unittest

from services.frequencia import calcular_espacamento_minimo, distribuir_semanas, quantidade_esperada_no_mapa


class FrequenciaTest(unittest.TestCase):
    def test_frequencia_diaria_acentuada_cabe_no_mapa(self):
        self.assertEqual(quantidade_esperada_no_mapa("Diária", 1, 52), 52)
        self.assertEqual(calcular_espacamento_minimo("Diária"), 0)

    def test_distribuicao_respeita_janela_e_sem_duplicidade(self):
        semanas = distribuir_semanas("Mensal", 10, 20)

        self.assertTrue(semanas)
        self.assertEqual(len(semanas), len(set(semanas)))
        self.assertTrue(all(10 <= semana <= 20 for semana in semanas))


if __name__ == "__main__":
    unittest.main()

