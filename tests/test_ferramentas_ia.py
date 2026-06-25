import unittest

from services.ferramentas_ia import selecionar_e_executar_ferramentas


class FerramentasIATest(unittest.TestCase):
    def test_pergunta_de_backlog_usa_ferramentas_de_atraso(self):
        resultados = selecionar_e_executar_ferramentas("Qual equipamento tem maior backlog em 2026?")
        nomes = {resultado["nome"] for resultado in resultados}

        self.assertIn("consultar_ocorrencias_atrasadas", nomes)
        self.assertIn("consultar_backlog_por_equipamento", nomes)

    def test_pergunta_de_capacidade_usa_ferramenta_de_capacidade(self):
        resultados = selecionar_e_executar_ferramentas("Existe alguma disciplina sobrecarregada em 2026?")
        nomes = {resultado["nome"] for resultado in resultados}

        self.assertIn("consultar_capacidade_por_disciplina", nomes)

    def test_pergunta_de_uso_usa_ajuda_do_sistema(self):
        resultados = selecionar_e_executar_ferramentas("Como cadastro um equipamento?")
        nomes = {resultado["nome"] for resultado in resultados}

        self.assertIn("consultar_ajuda_sistema", nomes)

    def test_pergunta_de_mais_planos_usa_ranking_de_planos(self):
        resultados = selecionar_e_executar_ferramentas("Qual equipamento com mais planos?")
        nomes = {resultado["nome"] for resultado in resultados}

        self.assertIn("consultar_ranking_planos_por_equipamento", nomes)
        self.assertNotIn("consultar_planos_por_equipamento", nomes)

    def test_pergunta_de_fragilidade_usa_limitacoes_do_sistema(self):
        resultados = selecionar_e_executar_ferramentas("Qual fragilidade desse sistema?")
        nomes = {resultado["nome"] for resultado in resultados}

        self.assertIn("consultar_limitacoes_sistema", nomes)
        self.assertNotIn("consultar_resumo_dashboard", nomes)

    def test_pergunta_fora_de_escopo_nao_usa_dashboard_generico(self):
        resultados = selecionar_e_executar_ferramentas("Qual o meu nome?")
        nomes = {resultado["nome"] for resultado in resultados}

        self.assertIn("consultar_base_conhecimento", nomes)
        self.assertNotIn("consultar_resumo_dashboard", nomes)
        self.assertNotIn("consultar_concentracao_por_semana", nomes)

    def test_pergunta_sobre_pdf_ou_manual_usa_base_conhecimento(self):
        resultados = selecionar_e_executar_ferramentas("Para que serve grupo de parada?")
        nomes = {resultado["nome"] for resultado in resultados}

        self.assertIn("consultar_base_conhecimento", nomes)


if __name__ == "__main__":
    unittest.main()
