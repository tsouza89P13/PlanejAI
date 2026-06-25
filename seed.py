from __future__ import annotations

import argparse
from datetime import date

from database import SessionLocal
from models import CapacidadeEquipe, Equipamento, Plano, RestricaoCalendario


def _ano_demo() -> int:
    ano = date.today().year
    return ano if 2025 <= ano <= 2028 else 2026


def _base_tem_dados(session) -> bool:
    return any(
        [
            session.query(Equipamento).first(),
            session.query(Plano).first(),
            session.query(CapacidadeEquipe).first(),
            session.query(RestricaoCalendario).first(),
        ]
    )


def _limpar_base_demo(session) -> None:
    session.query(CapacidadeEquipe).delete()
    session.query(RestricaoCalendario).delete()
    session.query(Plano).delete()
    session.query(Equipamento).delete()
    session.commit()


def _criar_equipamentos() -> list[Equipamento]:
    return [
        Equipamento(codigo="EV-1001", descricao="Bombas Hidráulicas", local="Planta A", area="Mecânica", criticidade="Alta", status="Ativo"),
        Equipamento(codigo="EV-1002", descricao="Painel Elétrico 1", local="Planta A", area="Elétrica", criticidade="Média", status="Ativo"),
        Equipamento(codigo="EV-1003", descricao="Sistema de Lubrificação", local="Planta B", area="Lubrificação", criticidade="Alta", status="Ativo"),
        Equipamento(codigo="EV-1004", descricao="Compressor de Ar", local="Planta B", area="Mecânica", criticidade="Baixa", status="Ativo"),
        Equipamento(codigo="EV-1005", descricao="Motor Elétrico Principal", local="Planta C", area="Elétrica", criticidade="Alta", status="Ativo"),
    ]


def _criar_planos(equipamentos: list[Equipamento]) -> list[Plano]:
    return [
        Plano(equipamento_id=equipamentos[0].id, nome="Inspeção das Bombas", descricao="Inspeção visual e revisão de conexões.", tipo_intervencao="Inspeção", disciplina="Mecânica", frequencia="Mensal", duracao_hh=4.0, prioridade=3, grupo_parada="Parada Mensal", janela_inicio=1, janela_fim=52, status="Ativo"),
        Plano(equipamento_id=equipamentos[0].id, nome="Preventiva das Bombas", descricao="Troca de selos e lubrificação.", tipo_intervencao="Preventiva", disciplina="Lubrificação", frequencia="Trimestral", duracao_hh=6.0, prioridade=2, grupo_parada="Parada Trimestral", janela_inicio=10, janela_fim=45, status="Ativo"),
        Plano(equipamento_id=equipamentos[0].id, nome="Verificação Elétrica das Bombas", descricao="Teste de aterramento e isolação.", tipo_intervencao="Preventiva", disciplina="Elétrica", frequencia="Trimestral", duracao_hh=5.0, prioridade=2, grupo_parada="Parada Trimestral", janela_inicio=10, janela_fim=45, status="Ativo"),
        Plano(equipamento_id=equipamentos[1].id, nome="Inspeção do Painel 1", descricao="Cheque de terminais e ventilação.", tipo_intervencao="Inspeção", disciplina="Elétrica", frequencia="Mensal", duracao_hh=3.0, prioridade=3, janela_inicio=1, janela_fim=52, status="Ativo"),
        Plano(equipamento_id=equipamentos[1].id, nome="Preventiva do Painel 1", descricao="Limpeza e troca de componentes.", tipo_intervencao="Preventiva", disciplina="Elétrica", frequencia="Semestral", duracao_hh=8.0, prioridade=4, janela_inicio=15, janela_fim=40, status="Ativo"),
        Plano(equipamento_id=equipamentos[1].id, nome="Preditiva do Painel 1", descricao="Análise termográfica.", tipo_intervencao="Preditiva", disciplina="Elétrica", frequencia="Anual", duracao_hh=10.0, prioridade=5, janela_inicio=40, janela_fim=52, status="Ativo"),
        Plano(equipamento_id=equipamentos[2].id, nome="Inspeção do Sistema de Lubrificação", descricao="Verificar reservatórios e filtros.", tipo_intervencao="Inspeção", disciplina="Lubrificação", frequencia="Mensal", duracao_hh=4.0, prioridade=3, janela_inicio=1, janela_fim=52, status="Ativo"),
        Plano(equipamento_id=equipamentos[2].id, nome="Preventiva do Sistema de Lubrificação", descricao="Troca de óleo e limpeza.", tipo_intervencao="Preventiva", disciplina="Lubrificação", frequencia="Semestral", duracao_hh=7.0, prioridade=3, janela_inicio=20, janela_fim=50, status="Ativo"),
        Plano(equipamento_id=equipamentos[2].id, nome="Verificação Mecânica do Sistema", descricao="Ajustes mecânicos e inspeção de vedações.", tipo_intervencao="Preventiva", disciplina="Mecânica", frequencia="Trimestral", duracao_hh=5.0, prioridade=3, grupo_parada="Parada Trimestral", janela_inicio=10, janela_fim=45, status="Ativo"),
        Plano(equipamento_id=equipamentos[3].id, nome="Preditiva do Compressor", descricao="Monitoramento de vibração.", tipo_intervencao="Preditiva", disciplina="Mecânica", frequencia="Mensal", duracao_hh=3.5, prioridade=2, janela_inicio=1, janela_fim=52, status="Ativo"),
        Plano(equipamento_id=equipamentos[3].id, nome="Preventiva do Compressor", descricao="Substituição de filtros e correias.", tipo_intervencao="Preventiva", disciplina="Mecânica", frequencia="Semestral", duracao_hh=8.0, prioridade=4, janela_inicio=5, janela_fim=48, status="Ativo"),
        Plano(equipamento_id=equipamentos[3].id, nome="Inspeção de Segurança do Compressor", descricao="Teste de válvulas e sensores.", tipo_intervencao="Inspeção", disciplina="Elétrica", frequencia="Trimestral", duracao_hh=4.0, prioridade=3, janela_inicio=1, janela_fim=52, status="Ativo"),
        Plano(equipamento_id=equipamentos[4].id, nome="Inspeção do Motor Principal", descricao="Exame de rolamentos e balanceamento.", tipo_intervencao="Inspeção", disciplina="Mecânica", frequencia="Mensal", duracao_hh=4.0, prioridade=4, janela_inicio=1, janela_fim=52, status="Ativo"),
        Plano(equipamento_id=equipamentos[4].id, nome="Preventiva do Motor Principal", descricao="Troca de óleo e análise de carga.", tipo_intervencao="Preventiva", disciplina="Elétrica", frequencia="Trimestral", duracao_hh=6.0, prioridade=5, grupo_parada="Parada Trimestral", janela_inicio=10, janela_fim=45, status="Ativo"),
        Plano(equipamento_id=equipamentos[4].id, nome="Preditiva do Motor Principal", descricao="Análise de corrente e vibração.", tipo_intervencao="Preditiva", disciplina="Elétrica", frequencia="Semestral", duracao_hh=9.0, prioridade=4, janela_inicio=20, janela_fim=48, status="Ativo"),
    ]


def run_seed(reset: bool = False, yes: bool = False) -> None:
    session = SessionLocal()
    try:
        if _base_tem_dados(session):
            if not reset:
                print("A base ja possui dados. Seed cancelado para evitar perda de informacoes.")
                print("Para recriar a base demo, use: python seed.py --reset --yes")
                return
            if not yes:
                print("Reset solicitado sem confirmacao. Use: python seed.py --reset --yes")
                return
            _limpar_base_demo(session)

        ano = _ano_demo()
        equipamentos = _criar_equipamentos()
        session.add_all(equipamentos)
        session.commit()

        planos = _criar_planos(equipamentos)
        session.add_all(planos)

        capacidades = [
            CapacidadeEquipe(ano=ano, disciplina="Mecânica", num_colaboradores=4, eficiencia=0.70),
            CapacidadeEquipe(ano=ano, disciplina="Elétrica", num_colaboradores=3, eficiencia=0.70),
            CapacidadeEquipe(ano=ano, disciplina="Lubrificação", num_colaboradores=2, eficiencia=0.80),
        ]
        session.add_all(capacidades)

        restricoes = [
            RestricaoCalendario(data_inicio=date(ano, 1, 1), data_fim=date(ano, 1, 1), tipo="Feriado", descricao="Ano Novo", bloqueia_execucao=True),
            RestricaoCalendario(data_inicio=date(ano, 7, 20), data_fim=date(ano, 7, 25), tipo="Grande Parada", descricao="Parada programada da planta", bloqueia_execucao=True),
            RestricaoCalendario(data_inicio=date(ano, 12, 20), data_fim=date(ano, 12, 31), tipo="Férias", descricao="Férias coletivas", bloqueia_execucao=True),
        ]
        session.add_all(restricoes)
        session.commit()

        print(
            f"Base demo criada para {ano}: "
            f"{len(equipamentos)} equipamentos, {len(planos)} planos, "
            f"{len(capacidades)} capacidades e {len(restricoes)} restricoes."
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria dados demo seguros para o PlanejAI.")
    parser.add_argument("--reset", action="store_true", help="Apaga dados demo/atuais antes de recriar a base.")
    parser.add_argument("--yes", action="store_true", help="Confirma explicitamente o reset destrutivo.")
    args = parser.parse_args()
    run_seed(reset=args.reset, yes=args.yes)


if __name__ == "__main__":
    main()
