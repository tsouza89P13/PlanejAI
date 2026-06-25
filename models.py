from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text, event
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Equipamento(Base):
    __tablename__ = "equipamentos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String, unique=True, nullable=False)
    descricao = Column(String, nullable=False)
    local = Column(String)
    area = Column(String)
    criticidade = Column(String)
    status = Column(String, default="Ativo")

    planos = relationship("Plano", back_populates="equipamento", cascade="all, delete-orphan")


class Plano(Base):
    __tablename__ = "planos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipamento_id = Column(Integer, ForeignKey("equipamentos.id"))
    nome = Column(String, nullable=False)
    descricao = Column(String)
    tipo_intervencao = Column(String)
    disciplina = Column(String)
    frequencia = Column(String)
    duracao_hh = Column(Float)
    prioridade = Column(Integer)
    grupo_parada = Column(String, nullable=True)
    janela_inicio = Column(Integer, default=1)
    janela_fim = Column(Integer, default=52)
    status = Column(String, default="Ativo")
    data_comissionamento = Column(Date, nullable=True)

    equipamento = relationship("Equipamento", back_populates="planos")
    ocorrencias = relationship("Ocorrencia", back_populates="plano", cascade="all, delete-orphan")


class Ocorrencia(Base):
    __tablename__ = "ocorrencias"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plano_id = Column(Integer, ForeignKey("planos.id"))
    ano = Column(Integer, nullable=False)
    semana = Column(Integer, nullable=False)
    status = Column(String, default="Programado")
    hh_previsto = Column(Float)
    hh_realizado = Column(Float, nullable=True)
    data_realizado = Column(Date, nullable=True)
    observacao = Column(String, nullable=True)

    plano = relationship("Plano", back_populates="ocorrencias")
    historico = relationship("HistoricoAlteracao", back_populates="ocorrencia", cascade="all, delete-orphan")


class HistoricoAlteracao(Base):
    __tablename__ = "historico_alteracoes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ocorrencia_id = Column(Integer, ForeignKey("ocorrencias.id"))
    campo = Column(String)
    valor_anterior = Column(String)
    valor_novo = Column(String)
    alterado_em = Column(DateTime, default=datetime.utcnow)

    ocorrencia = relationship("Ocorrencia", back_populates="historico")


class RestricaoCalendario(Base):
    __tablename__ = "restricoes_calendario"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ano = Column(Integer)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    tipo = Column(String)
    descricao = Column(String)
    bloqueia_execucao = Column(Boolean, default=False)


class CapacidadeEquipe(Base):
    __tablename__ = "capacidade_equipes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ano = Column(Integer)
    disciplina = Column(String)
    num_colaboradores = Column(Integer)
    eficiencia = Column(Float)


class AssistenteHistorico(Base):
    __tablename__ = "assistente_historico"
    id = Column(Integer, primary_key=True, autoincrement=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    provedor = Column(String, nullable=False)
    modelo = Column(String)
    pergunta = Column(Text, nullable=False)
    resposta = Column(Text, nullable=False)
    ferramentas_usadas = Column(Text)
    contexto_json = Column(Text)


@event.listens_for(RestricaoCalendario, "before_insert")
@event.listens_for(RestricaoCalendario, "before_update")
def _set_ano_from_data_inicio(mapper, connection, target):
    if target.data_inicio:
        target.ano = target.data_inicio.year
