import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from models import Base

DB_FILENAME = "pcm_planner.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_FILENAME)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def _migrate_restricoes_calendario() -> None:
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(restricoes_calendario)"))
        columns = [row[1] for row in result.fetchall()]
        if "data_inicio" not in columns:
            conn.execute(text("ALTER TABLE restricoes_calendario ADD COLUMN data_inicio DATE"))
        if "data_fim" not in columns:
            conn.execute(text("ALTER TABLE restricoes_calendario ADD COLUMN data_fim DATE"))
        conn.commit()


def _migrate_indexes() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_planos_equipamento_id ON planos (equipamento_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ocorrencias_ano ON ocorrencias (ano)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ocorrencias_plano_ano ON ocorrencias (plano_id, ano)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_capacidade_ano_disciplina ON capacidade_equipes (ano, disciplina)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_restricoes_ano ON restricoes_calendario (ano)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_planos_equipamento_nome ON planos (equipamento_id, nome)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_capacidade_ano_disciplina ON capacidade_equipes (ano, disciplina)"))
        conn.commit()


def init_db() -> None:
    """Cria o banco de dados e todas as tabelas se ainda não existirem."""
    Base.metadata.create_all(bind=engine)
    _migrate_restricoes_calendario()
    _migrate_indexes()


# Inicializa automaticamente no import
init_db()
