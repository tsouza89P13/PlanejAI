import unittest

from services.assistente import chave_configurada, modelo_id_por_rotulo, modelos_disponiveis, responder


class AssistenteModelosTest(unittest.TestCase):
    def test_rotulo_amigavel_retorna_id_tecnico(self):
        rotulo = modelos_disponiveis("OpenAI")[0]

        self.assertEqual(modelo_id_por_rotulo("OpenAI", rotulo), "gpt-4.1-mini")

    def test_personalizado_nao_quebra_busca_de_modelo(self):
        self.assertEqual(modelo_id_por_rotulo("Gemini", "Personalizado"), "gemini-2.5-flash")

    def test_jovem_aprendiz_nao_exige_chave(self):
        self.assertTrue(chave_configurada("Jovem Aprendiz (IA Simulada)"))

    def test_jovem_aprendiz_responde_sem_api(self):
        resultado = responder("Como cadastro um equipamento?", "Jovem Aprendiz (IA Simulada)")

        self.assertIn("não usa IA externa", resultado["resposta"])
        self.assertIn("consultar_ajuda_sistema", resultado["ferramentas"])


if __name__ == "__main__":
    unittest.main()
