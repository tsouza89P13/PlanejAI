from datetime import datetime
from models import HistoricoAlteracao


def registrar_historico(session, ocorrencia_id, campo, valor_anterior, valor_novo):
    """
    Registra uma alteração no histórico.
    Deve ser chamada ANTES de commitar a mudança.
    """
    historico = HistoricoAlteracao(
        ocorrencia_id=ocorrencia_id,
        campo=campo,
        valor_anterior=str(valor_anterior) if valor_anterior is not None else None,
        valor_novo=str(valor_novo) if valor_novo is not None else None,
        alterado_em=datetime.utcnow()
    )
    session.add(historico)
