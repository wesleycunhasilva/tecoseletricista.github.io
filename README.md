# TecOS - Gerenciador de Ordens de Serviço

TecOS é uma aplicação web em Flask para gerenciar clientes, ordens de serviço e orçamentos de eletricistas e técnicos.

Também possui uma API REST de portfólio com entidades `Profile`, `Project`, `Technology` e `Feedback`.

## Funcionalidades
- Cadastro de clientes
- Criação de ordens de serviço
- Cálculo automático de valor total
- Dashboard com resumo visual
- Filtros por status no dashboard
- Análise de risco com lógica de IA simples
- API REST para perfis, projetos e tecnologias

## Estrutura do projeto
- app.py: inicialização da aplicação
- database.py: conexão e modelos de banco
- rotas.py: definição das rotas
- ia_modulo.py: lógica de análise de risco
- templates/: páginas HTML com Bootstrap
- static/css/style.css: estilos visuais

## Como executar
1. Acesse a pasta do projeto.
2. Instale o Flask, se ainda não estiver instalado:
   `pip install flask`
3. Execute:
   `python app.py`
4. Abra no navegador: `http://127.0.0.1:5000`

## Banco de dados
O projeto usa SQLite e cria o arquivo tecos.db automaticamente na primeira execução.

## API REST

Os endpoints aceitam e retornam JSON:

- `POST /api/profiles` e `GET /api/profiles/<id>`
- `POST /api/technologies` e `GET /api/technologies`
- `POST /api/projects` e `GET /api/projects`

Um projeto exige `profile_id`, `title` e pode receber `technology_ids`, `repository_url` e `demo_url`.
URLs devem usar `http` ou `https`; títulos e nomes não podem ser vazios.
