# Base de conhecimento do Assistente PlanejAI

Este documento concentra perguntas frequentes, respostas oficiais e orientacoes de uso do PlanejAI.
Ele serve como fonte de consulta para o assistente local e como base para um manual em PDF.

## Escopo do PlanejAI

O PlanejAI e uma aplicacao local em Streamlit para planejamento, capacidade e execucao de manutencao.
O sistema usa banco SQLite local e organiza a rotina PCM em duas frentes:

- Gestao: Dashboard e Mapa de 52 Semanas.
- Inputs: Equipamentos, Planos de Manutencao, Importacao via Excel, Calendario de Restricao, Capacidade de Equipe e Execucao de Ocorrencias.

O assistente do PlanejAI atua somente com ferramentas de leitura. Ele pode consultar dados, explicar telas e orientar o uso, mas nao altera cadastros, ocorrencias ou configuracoes.

## Perguntas sobre o sistema

### O que e o PlanejAI?

O PlanejAI e uma ferramenta local para organizar a carteira de manutencao preventiva, distribuir planos no mapa anual de 52 semanas, acompanhar ocorrencias e analisar capacidade de equipes.

### Para quem o PlanejAI foi criado?

O usuario principal e a equipe tecnica de PCM. O sistema tambem atende gestores e equipes de Engenharia de Manutencao que precisam visualizar carteira, backlog, aderencia, capacidade e distribuicao anual.

### O sistema roda localmente?

Sim. O PlanejAI roda localmente com Streamlit e SQLite. A base de dados fica no computador onde a aplicacao esta sendo executada.

### O sistema precisa de internet?

Para usar as telas principais, nao. Internet so e necessaria se o usuario configurar uma IA externa, como OpenAI, Gemini ou Claude.

### O assistente consegue alterar dados?

Nao. Por seguranca, o assistente foi desenhado inicialmente como ferramenta de consulta e analise. Ele pode ler dados e explicar funcoes, mas nao edita, remove, clona ou reprograma registros.

## Perguntas sobre Dashboard

### Para que serve o Dashboard?

O Dashboard mostra uma visao executiva da carteira PCM, incluindo eficiencia, aderencia, backlog, cancelamento, HH planejado, HH executado, HH cancelado, HH reprogramado, HH atrasado e total de atividades.

### Quais filtros existem no Dashboard?

O Dashboard pode ser filtrado por ano, disciplina, tipo de intervencao e area. Os filtros ajudam a analisar recortes especificos da carteira.

### O que significa backlog?

Backlog representa HH ou ocorrencias que deveriam ter sido executadas, mas continuam pendentes ou atrasadas conforme a semana atual e o status da ocorrencia.

### O que significa aderencia?

Aderencia indica o quanto das atividades planejadas foi efetivamente cumprido no periodo analisado.

### O que significa eficiencia?

Eficiencia compara HH realizado com HH planejado/executado, ajudando a entender se a execucao esta coerente com o esforco previsto.

### Por que alguns graficos podem aparecer vazios?

Graficos podem aparecer vazios quando nao existem ocorrencias no ano filtrado ou quando os filtros selecionados removem todos os registros da analise.

## Perguntas sobre Mapa de 52 Semanas

### Para que serve o Mapa de 52 Semanas?

O Mapa de 52 Semanas mostra a distribuicao anual dos planos de manutencao ao longo das semanas S1 a S52.

### Por que as semanas aparecem como S1, S2 e nao W1, W2?

O PlanejAI usa a nomenclatura em portugues: S significa semana.

### O mapa atualiza quando uma ocorrencia e reprogramada?

Sim. O mapa le as ocorrencias diretamente do banco local. Quando uma ocorrencia e reprogramada na tela de Execucao de Ocorrencias, ela muda de semana no banco e passa a aparecer na nova semana no Mapa de 52 Semanas.

### O mapa recalcula tudo automaticamente quando uma ocorrencia e reprogramada?

Nao. A reprogramacao altera a semana daquela ocorrencia especifica. Ela nao executa uma nova otimizacao completa da carteira anual. Conflitos de capacidade, restricao ou concentracao devem ser analisados pelo usuario.

### O que o filtro por equipamento faz no mapa?

Ele limita a visualizacao do mapa aos planos e ocorrencias vinculados ao equipamento selecionado.

### O que o filtro por disciplina faz no mapa?

Ele limita a visualizacao do mapa aos planos e ocorrencias da disciplina escolhida, como Mecanica, Eletrica ou Lubrificacao.

### O que significa uma semana carregada?

Uma semana carregada e uma semana com alto volume de HH previsto ou grande quantidade de ocorrencias, podendo indicar risco de capacidade ou concentracao excessiva.

## Perguntas sobre Equipamentos

### Para que serve o cadastro de equipamentos?

O cadastro de equipamentos registra os ativos que receberao planos de manutencao. Sem equipamento cadastrado, nao e possivel vincular corretamente os planos.

### Quais campos sao importantes em equipamentos?

Codigo, descricao, local, area, criticidade e status. O codigo identifica o ativo e deve ser unico.

### O que acontece ao remover um equipamento?

Ao remover um equipamento, os planos vinculados tambem sao removidos. Como cada plano pode ter ocorrencias, os registros associados a esses planos tambem podem ser apagados. Por isso o sistema deve pedir confirmacao explicita antes da remocao.

### Posso cadastrar equipamento inativo?

Sim. O status indica se o equipamento esta ativo ou inativo. Equipamentos inativos podem ser mantidos para historico ou controle, mas devem ser avaliados antes de receber novos planos.

## Perguntas sobre Planos de Manutencao

### Para que serve o cadastro de planos?

O cadastro de planos define as atividades preventivas ou rotineiras que serao distribuidas no mapa anual.

### O que e frequencia do plano?

Frequencia define a recorrencia da atividade, como semanal, mensal, trimestral, semestral ou anual.

### O que e duracao em HH?

Duracao em HH representa a quantidade de homem-hora prevista para executar o plano.

### O que e disciplina?

Disciplina indica a especialidade responsavel pela execucao, como Mecanica, Eletrica ou Lubrificacao.

### Para que serve janela inicio e janela fim?

Janela inicio e janela fim limitam o intervalo de semanas em que o plano pode ser distribuido no mapa anual. Por exemplo, uma janela S10 a S20 indica que a atividade deve ser planejada entre essas semanas.

### A janela inicio e fim e obrigatoria?

Ela e importante para planos que so podem ocorrer em determinado periodo. Para planos sem restricao de periodo, pode ser usada a janela padrao S1 a S52.

### Para que serve prioridade?

Prioridade registra a importancia relativa do plano. Atualmente ela serve como informacao para analise e organizacao, mas nao deve ser tratada como criterio automatico forte de otimizacao se a regra ainda nao estiver implementada.

### O que e grupo de parada?

Grupo de parada e um identificador usado para agrupar planos que devem ocorrer na mesma parada operacional. Planos do mesmo equipamento com o mesmo grupo podem ser alinhados para execucao conjunta.

### O grupo de parada esta funcional?

Sim, como regra de agrupamento na geracao/distribuicao do mapa anual. Ele ajuda a alinhar atividades relacionadas, mas ainda deve respeitar janelas, restricoes, frequencia e espacamento minimo.

### Quando devo usar grupo de parada?

Use quando varias atividades do mesmo equipamento devem ser realizadas na mesma oportunidade de parada, reduzindo indisponibilidade e melhorando planejamento.

## Perguntas sobre Importacao via Excel

### Para que serve a importacao via Excel?

A importacao permite carregar equipamentos e planos em lote, evitando cadastro manual registro por registro.

### Qual arquivo devo importar primeiro?

Importe equipamentos antes dos planos. Os planos dependem do codigo do equipamento ja cadastrado.

### O que acontece se o plano apontar para um equipamento inexistente?

O sistema deve rejeitar ou sinalizar erro, pois nao e possivel vincular o plano a um equipamento que nao existe.

### Para que serve o template?

O template padroniza colunas, nomes e formatos esperados pelo sistema, reduzindo erros de importacao.

### Quais erros podem acontecer na importacao?

Campos obrigatorios vazios, codigo de equipamento inexistente, frequencia invalida, disciplina invalida, duracao incorreta, janela fora de S1 a S52, prioridade invalida ou status fora do padrao.

## Perguntas sobre Calendario de Restricao

### Para que serve o calendario de restricao?

Ele registra periodos que devem ser considerados no planejamento, como feriados, grandes paradas, ferias coletivas, restricoes operacionais ou eventos especiais.

### O que significa bloquear execucao?

Quando uma restricao bloqueia execucao, o periodo deve ser evitado na distribuicao de ocorrencias do mapa anual.

### Restricoes aparecem no mapa?

Elas influenciam o planejamento e podem ser consultadas pelo usuario. A visibilidade depende da tela e dos filtros aplicados.

## Perguntas sobre Capacidade de Equipe

### Para que serve capacidade de equipe?

Capacidade de equipe registra a disponibilidade de colaboradores por disciplina e ano, permitindo comparar demanda planejada com capacidade semanal.

### O que significa eficiencia na capacidade?

Eficiencia representa o percentual de disponibilidade produtiva da equipe. Por exemplo, 70% considera perdas, rotinas paralelas e indisponibilidades.

### Como saber se uma disciplina esta sobrecarregada?

Compare o HH necessario por semana com o HH disponivel da disciplina. Se a necessidade for maior que a disponibilidade, existe risco de sobrecarga.

## Perguntas sobre Execucao de Ocorrencias

### Para que serve Execucao de Ocorrencias?

Essa tela acompanha as atividades geradas a partir dos planos. Ela permite marcar atividades como realizadas, reprogramar ou cancelar.

### O que acontece ao marcar uma ocorrencia como realizada?

O status passa para realizado, podendo registrar HH realizado, data e observacao conforme a regra da tela.

### O que acontece ao cancelar uma ocorrencia?

O status passa para cancelado e a ocorrencia deixa de contar como atividade planejada executavel, mas permanece como registro historico.

### O que acontece ao reprogramar uma ocorrencia?

A ocorrencia muda para outra semana e passa a aparecer como reprogramada. O historico da alteracao deve registrar a mudanca.

### Reprogramar uma ocorrencia altera o plano original?

Nao necessariamente. A reprogramacao altera a ocorrencia especifica. O plano continua sendo a regra base para geracoes futuras.

## Perguntas sobre dados e seguranca

### Onde os dados ficam salvos?

Os dados ficam em banco SQLite local, no arquivo do projeto. Em uso real, e recomendavel definir estrategia de backup.

### Posso versionar o banco no GitHub?

Nao e recomendado versionar o banco real. Bancos `.db`, `.db-wal`, `.db-shm` e `.db-journal` devem ficar fora do GitHub, pois podem conter dados operacionais.

### O sistema tem login?

Na arquitetura atual, nao ha login/perfis de permissao. Para uso multiusuario real, seria recomendavel implementar autenticacao, autorizacao e auditoria.

### O assistente grava historico?

Sim. As perguntas e respostas do assistente sao salvas no banco local. O usuario pode excluir conversas salvas pela tela do assistente.

## Perguntas sobre IA e custos

### O Jovem Aprendiz usa API paga?

Nao. O Jovem Aprendiz e uma IA simulada/local. Ele nao chama OpenAI, Gemini ou Claude e nao gera custo de API.

### O Jovem Aprendiz e uma IA completa?

Nao. Ele e um modo de validacao local que consulta ferramentas internas e resume resultados. Ele nao deve inventar respostas para perguntas fora do escopo.

### OpenAI, Gemini e Claude podem gerar custo?

Sim. APIs externas normalmente podem gerar custo conforme uso, modelo e conta do provedor.

### Cada usuario precisa colocar sua propria chave API?

Sim, se for usar IA externa. A chave deve ser salva localmente na maquina do usuario e nao deve ser versionada no GitHub.

### Se o usuario escolher Gemini mas colocar chave da OpenAI, funciona?

Nao. Cada provedor usa sua propria API e chave. Uma chave da OpenAI nao funciona como chave do Gemini ou Claude.

## Perguntas que o assistente deve responder com cuidado

### Qual o meu nome?

O assistente nao tem acesso a identidade pessoal do usuario, salvo se essa informacao existir explicitamente em uma base consultavel. A resposta correta e avisar que nao ha informacao suficiente.

### Qual e a maior fragilidade do sistema?

As principais fragilidades atuais sao: ausencia de login/perfis, dependencia de banco local, assistente local limitado a ferramentas cadastradas, reprogramacao sem otimizacao completa automatica e necessidade de backup/controle de dados.

### O sistema esta pronto para uso real?

Ele pode ser usado localmente para controle e validacao operacional, mas para uso corporativo amplo recomenda-se reforcar backup, autenticacao, permissoes, auditoria, testes automatizados e processo de deploy.

### O assistente consegue responder qualquer pergunta?

Nao. Ele responde melhor quando a pergunta esta relacionada aos dados do PlanejAI ou ao uso das telas. Perguntas pessoais, juridicas, financeiras ou fora do escopo devem ser recusadas ou encaminhadas para uma IA externa com contexto adequado.

## Quem criou esse sistema?
O sistema foi criado pelo Engenheiro Mecânico Tiago Oliveira de Souza. 

## Exemplos de perguntas recomendadas

- Quais ocorrencias estao atrasadas em 2026?
- Qual equipamento tem maior backlog?
- Qual equipamento tem mais planos cadastrados?
- Quais equipamentos estao sem plano?
- Existe alguma disciplina sobrecarregada?
- Quais semanas estao mais carregadas?
- Como cadastro um equipamento?
- Como importo planos via Excel?
- Para que serve grupo de parada?
- Janela inicio e janela fim funcionam para que?
- A prioridade do plano influencia a programacao?
- O que acontece se eu apagar um equipamento?
- O mapa atualiza quando eu reprogramo uma ocorrencia?
- Como funciona o calendario de restricao?
- Onde os dados ficam salvos?
- O Jovem Aprendiz usa API paga?
- Quais sao as limitacoes do sistema?

