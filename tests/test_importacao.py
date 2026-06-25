from io import BytesIO
import unittest

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Equipamento, Plano
from services.importacao import importar_equipamentos, importar_planos


def _xlsx(headers, rows):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class ImportacaoTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)

    def test_importa_e_atualiza_equipamento_por_codigo(self):
        session = self.Session()
        arquivo = _xlsx(
            ["Código *", "Descrição *", "Local", "Área", "Criticidade *", "Status *"],
            [
                ["EQ-001", "Bomba", "Sala", "Utilidades", "media", "ativo"],
                ["EQ-001", "Bomba Atualizada", "Sala 2", "Utilidades", "Alta", "Ativo"],
            ],
        )

        resultado = importar_equipamentos(arquivo, session)

        equipamento = session.query(Equipamento).filter_by(codigo="EQ-001").one()
        self.assertEqual(resultado["criados"], 1)
        self.assertEqual(resultado["atualizados"], 1)
        self.assertEqual(equipamento.descricao, "Bomba Atualizada")
        self.assertEqual(equipamento.criticidade, "Alta")
        session.close()

    def test_importa_plano_validando_equipamento_e_campos(self):
        session = self.Session()
        session.add(Equipamento(codigo="EQ-001", descricao="Bomba", criticidade="Alta", status="Ativo"))
        session.commit()
        arquivo = _xlsx(
            [
                "Código Equipamento *",
                "Nome do Plano *",
                "Descrição",
                "Tipo Intervenção *",
                "Disciplina *",
                "Frequência *",
                "Duração (HH) *",
                "Prioridade *",
                "Grupo de Parada",
                "Janela Início *",
                "Janela Fim *",
                "Status *",
            ],
            [["EQ-001", "Inspeção Visual", "Geral", "Inspeção", "Mecânica", "Mensal", 2, 2, "", 1, 52, "Ativo"]],
        )

        resultado = importar_planos(arquivo, session)

        plano = session.query(Plano).one()
        self.assertEqual(resultado["criados"], 1)
        self.assertFalse(resultado["erros"])
        self.assertEqual(plano.frequencia, "Mensal")
        self.assertEqual(plano.disciplina, "Mecânica")
        session.close()


if __name__ == "__main__":
    unittest.main()

