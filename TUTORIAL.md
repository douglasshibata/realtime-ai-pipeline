# 🚀 Guia Passo a Passo: Real-Time AI Intelligence & Ingestion Pipeline

Este tutorial guia você na execução, testes e visualização do sistema de ingestão de dados em tempo real com **FastAPI**, **Celery**, **Redis**, **OpenSearch** e **Server-Sent Events (SSE)**.

---

## 📋 Pré-requisitos

1. **Docker e Docker Compose** instalados.
2. **Python 3.12+** (para execução de testes locais).
3. **Navegador Web** (Chrome, Firefox ou Edge).

---

## 🛠️ Passo 1: Subir a Infraestrutura com Docker Compose

Suba todos os contêineres do sistema com o comando:

```bash
cd realtime-ai-pipeline
docker-compose up --build -d
```

Verifique o estado dos contêineres:
```bash
docker-compose ps
```

Deverão estar rodando 5 serviços:
- `realtime_redis` (Porta 6379)
- `realtime_opensearch` (Porta 9200, 9600)
- `realtime_dashboards` (Porta 5601)
- `realtime_fastapi` (Porta 8000)
- `realtime_celery_worker`

---

## 🧪 Passo 2: Executar Testes Automatizados

Para rodar os testes unitários e de integração do backend:

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/ -v
```

---

## 🌐 Passo 3: Interagir com o Painel Frontend e SSE

1. Abra o arquivo `frontend/index.html` em seu navegador web.
2. Insira um texto de exemplo na caixa de texto. Exemplo:
   > *"Reclamação de cliente sobre cobrança indevida no cartão referente à fatura mensal. Solicito estorno imediato."*
3. Selecione a fonte (ex: `Customer Feedback`).
4. Clique em **Ingest & Track Live**.

O painel exibirá em tempo real as transições de status capturadas via SSE:
1. `Queued`: Tarefa enviada para a fila Celery/Redis.
2. `LLM Extraction`: Extração de sentimentos, categorias e entidades.
3. `OpenSearch`: Documento indexado no índice `insights_index`.
4. `Completed`: Resultado final exibido com badge de sentimento e sumário.

---

## 📊 Passo 4: Configurar o OpenSearch Dashboards

1. Acesse o **OpenSearch Dashboards** em `http://localhost:5601`.
2. Vá em **Management** > **Stack Management** > **Index Patterns**.
3. Clique em **Create index pattern**.
4. Digite `insights_index` e clique em **Next step**.
5. Em *Timestamp field*, selecione `timestamp` e clique em **Create index pattern**.
6. Vá em **Discover** no menu lateral para visualizar os documentos processados e indexados em tempo real!

---

## 🔍 Passo 5: Teste via cURL

### Ingestão de Texto:
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Erro de timeout na API de pagamento ao processar pedido #8821.", "source": "security_logs"}'
```

Resposta (retorna o `task_id` imediatamente):
```json
{"task_id":"<SEU_TASK_ID>","status":"queued","message":"Task queued for asynchronous AI processing and search indexing."}
```

### Inscrição no Stream SSE:
```bash
curl -N http://localhost:8000/api/stream/<SEU_TASK_ID>
```

---

## 🛠️ Solução de Problemas

* **Erro de memória no OpenSearch:** Certifique-se de que o Docker possui pelo menos 4GB de RAM alocados.
* **OpenSearch com plugin de segurança habilitado:** O `docker-compose.yml` inclui a variável `DISABLE_SECURITY_PLUGIN=true` para facilitar o desenvolvimento local sem autenticação SSL pesada.
