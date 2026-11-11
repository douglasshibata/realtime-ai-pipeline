# 1. Imagem base oficial do Python 3.12 (versão slim, leve e otimizada)
FROM python:3.12-slim

# 2. Define o diretório de trabalho onde a aplicação vai residir
WORKDIR /app

# 3. Variáveis de ambiente para otimizar o Python em containers:
#    - PYTHONDONTWRITEBYTECODE: impede a criação de arquivos temporários .pyc
#    - PYTHONUNBUFFERED: envia os logs do terminal imediatamente sem retenção em buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. Instala utilitários básicos do sistema operacional
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 5. Copia apenas a lista de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# 6. Instala as dependências contornando a checagem SSL nos domínios oficiais do PyPI
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    -r requirements.txt

# 7. Copia o restante do código-fonte do projeto
COPY . .

# 8. Declara a porta de rede que a aplicação FastAPI utiliza
EXPOSE 8000

# 9. Comando de inicialização do servidor Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]