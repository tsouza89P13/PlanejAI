# PlanejAI

Aplicação local para Planejamento e Controle da Manutenção (PCM), com cadastro de equipamentos e planos, importação via Excel, mapa de planejamento de 52 semanas com nivelamento e balanceamento automáticos, capacidade de equipes, execução de ocorrências, dashboard executivo, relatórios em PDF e assistente IA com consultas locais ao banco.


![PlanejAI](imagens/fst.png)

---

## Tecnologias utilizadas

| Tecnologia | Finalidade |
|------------|------------|
| Python 3.11+ | Linguagem principal |
| Streamlit | Interface web |
| SQLite | Banco de dados local |
| SQLAlchemy | ORM |
| Pandas | Importação e manipulação de dados |
| OpenPyXL | Leitura e escrita de arquivos Excel |
| ReportLab | Geração de relatórios em PDF |
| Plotly | Dashboards e gráficos |
| OpenAI / Gemini / Claude | Integração opcional com IA |

---

## Principais recursos

- Dashboard executivo com indicadores da carteira de PCM.
- Mapa de planejamento de 52 semanas com filtros por equipamento e disciplina.
- Cadastro de equipamentos, planos de manutenção, calendário de restrições e capacidade das equipes.
- Importação via Excel com templates oficiais.
- Execução de ocorrências com realização, reprogramação, cancelamento e histórico.
- Geração de relatórios em PDF para dashboard, backlog, ocorrências e mapa anual.
- Assistente PlanejAI com modo local **"Jovem Aprendiz (IA Simulada)"**.
- Integração opcional com OpenAI, Gemini ou Claude utilizando a chave de API do usuário.

---

## Requisitos

- Python 3.11 ou superior.
- Git (opcional, para clonar o repositório).

---

## Instalação

Você pode clonar o projeto ou baixá-lo em formato ZIP pelo GitHub.

### Clone o repositório

```bash
git clone https://github.com/tsouza89P13/PlanejAI.git
cd PlanejAI
```

### Crie um ambiente virtual

```bash
python -m venv .venv
```

### Ative o ambiente virtual

**Windows**

```bash
.venv\Scripts\activate
```

**macOS/Linux**

```bash
source .venv/bin/activate
```

### Instale as dependências

```bash
pip install -r requirements.txt
```

### Execute a aplicação

```bash
streamlit run app.py
```

O sistema será aberto automaticamente no navegador. Caso isso não aconteça, acesse:

```text
http://localhost:8501
```

---

## Banco de dados

O PlanejAI utiliza **SQLite** como banco de dados local.

Na primeira execução, o arquivo `pcm_planner.db` é criado automaticamente na pasta do projeto.

Os seguintes arquivos são ignorados pelo Git:

```text
*.db
*.db-wal
*.db-shm
*.db-journal
*.sqlite
*.sqlite3
```

---

## Dados de demonstração

O arquivo `seed.py` cria uma base de dados de demonstração para testes.

Para popular uma base vazia:

```bash
python seed.py
```

Caso a base já possua dados, a execução será cancelada para evitar perda acidental de informações.

Para apagar completamente a base e recriar os dados de demonstração:

```bash
python seed.py --reset --yes
```

> **Atenção:** essa operação remove equipamentos, planos, capacidades e restrições antes de recriar os dados de demonstração.

---

## Assistente IA

O assistente possui dois modos de funcionamento:

- **Jovem Aprendiz (IA Simulada):** funcionamento totalmente local, gratuito e sem chamadas para APIs externas.
- **OpenAI, Gemini ou Claude:** modos opcionais que utilizam uma chave de API fornecida pelo próprio usuário.

Para configurar uma IA externa, copie:

```text
.streamlit/secrets.example.toml
```

para:

```text
.streamlit/secrets.toml
```

Depois, preencha a chave da API desejada.

> **Nunca publique o arquivo `.streamlit/secrets.toml`.**

---

## Relatórios em PDF

O sistema gera relatórios em PDF diretamente nas seguintes telas:

- Dashboard Executivo;
- Backlog e Atrasos;
- Ocorrências filtradas;
- Mapa de 52 Semanas.

Os PDFs são gerados localmente em memória apenas no momento do download.

---

## Estrutura do projeto

```text
.
├── app.py
├── database.py
├── models.py
├── requirements.txt
├── seed.py
├── componentes/
├── services/
├── imagens/
├── docs/
├── tests/
└── .streamlit/
    ├── config.toml
    └── secrets.example.toml
```

---

## Executando os testes

```bash
python -m unittest discover -s tests
```

---

## Roadmap

Funcionalidades previstas para versões futuras:

- Autenticação de usuários.
- Controle de permissões por perfil.
- Backup automático do banco de dados.
- Implantação para ambientes multiusuário.
- Geração de ordens de serviço.
- Indicadores avançados de manutenção.
- Integração com sistemas ERP/CMMS.
- Exportação de dashboards.

---

## Avisos importantes

- O PlanejAI é uma aplicação local desenvolvida para auxiliar no Planejamento e Controle da Manutenção (PCM).
- O uso de APIs externas (OpenAI, Gemini e Claude) pode gerar custos conforme a política de cobrança de cada provedor.
- O modo **Jovem Aprendiz** não utiliza APIs externas e responde exclusivamente com base nas ferramentas locais e na base de conhecimento disponível no sistema.