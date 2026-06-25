EXECUCOES_POR_ANO = {
    "Diaria": 365,
    "Diária": 365,
    "Diária": 365,
    "Semanal": 52,
    "Quinzenal": 26,
    "Mensal": 12,
    "Bimestral": 6,
    "Trimestral": 4,
    "Quadrimestral": 3,
    "Semestral": 2,
    "Anual": 1,
}

ORDEM_DISTRIBUICAO = [
    "Semanal", "Quinzenal", "Mensal", "Bimestral",
    "Trimestral", "Quadrimestral", "Semestral", "Anual"
]


def calcular_espacamento_minimo(frequencia: str) -> int:
    """
    Retorna a quantidade minima de semanas vazias entre duas ocorrencias.

    Exemplo:
    - Mensal: 12 ocorrencias no ano -> 3 semanas vazias entre ocorrencias.
    - Semestral: 2 ocorrencias no ano -> 25 semanas vazias, ou distancia
      minima de 26 semanas entre uma ocorrencia e outra.
    """
    import math

    n = EXECUCOES_POR_ANO.get(frequencia, 1)
    if n <= 1:
        return 0
    return max(0, math.floor(52 / n) - 1)


def quantidade_esperada_no_mapa(frequencia: str, janela_inicio: int = 1, janela_fim: int = 52) -> int:
    """
    Retorna quantas ocorrencias cabem no mapa semanal respeitando a janela
    e o espacamento minimo. Frequencias menores que semanal, como diaria,
    ficam limitadas a uma ocorrencia por semana no mapa de 52 semanas.
    """
    janela_inicio = max(1, int(janela_inicio))
    janela_fim = min(52, int(janela_fim))
    total_semanas = janela_fim - janela_inicio + 1
    if total_semanas <= 0:
        return 0

    n_desejado = min(EXECUCOES_POR_ANO.get(frequencia, 1), total_semanas)
    espacamento_minimo = calcular_espacamento_minimo(frequencia)
    if espacamento_minimo <= 0:
        return n_desejado

    maximo_com_espacamento = 1 + ((total_semanas - 1) // (espacamento_minimo + 1))
    return min(n_desejado, maximo_com_espacamento)


def distribuir_semanas(
    frequencia: str,
    janela_inicio: int,
    janela_fim: int
) -> list[int]:
    """
    Distribui ocorrencias uniformemente dentro da janela, mantendo:
    1. limite de ocorrencias que cabe no mapa semanal;
    2. espacamento minimo entre ocorrencias consecutivas;
    3. semanas sem duplicidade;
    4. todas as semanas dentro de [janela_inicio, janela_fim].
    """
    janela_inicio = max(1, int(janela_inicio))
    janela_fim = min(52, int(janela_fim))
    total_semanas = janela_fim - janela_inicio + 1
    if total_semanas <= 0:
        return []

    n = quantidade_esperada_no_mapa(frequencia, janela_inicio, janela_fim)
    if n <= 0:
        return []
    if n == 1:
        return [janela_inicio + total_semanas // 2]

    espacamento_minimo = calcular_espacamento_minimo(frequencia)
    distancia_minima = espacamento_minimo + 1

    semanas = []
    usadas = set()
    for i in range(n):
        posicao = i / (n - 1)
        semana = janela_inicio + round(posicao * (total_semanas - 1))

        if semanas:
            semana = max(semana, semanas[-1] + distancia_minima)
        semana = min(semana, janela_fim)

        while semana in usadas and semana <= janela_fim:
            semana += 1

        if semana <= janela_fim:
            semanas.append(semana)
            usadas.add(semana)

    if len(semanas) == n:
        return sorted(semanas)

    # Preenche eventuais lacunas sem violar a distancia minima.
    for semana in range(janela_inicio, janela_fim + 1):
        if semana in usadas:
            continue
        if all(abs(semana - existente) >= distancia_minima for existente in semanas):
            semanas.append(semana)
            usadas.add(semana)
            if len(semanas) == n:
                break

    return sorted(semanas)
