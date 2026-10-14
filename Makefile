SHELL := /bin/bash

# Diretorio raiz do projeto (caminho absoluto)
ROOT_DIR            := $(CURDIR)

# Configuracoes de Portas
BACKEND_PORT        ?= 8000
FRONTEND_PORT       ?= 5173
SUPABASE_STUDIO_PORT?= 54323

# Diretorio do venv Python
VENV_DIR            := $(ROOT_DIR)/backend/venv

# Deteccao de SO para executaveis do venv
ifeq ($(OS),Windows_NT)
    VENV_BIN    := $(VENV_DIR)/Scripts
    PYTHON      := $(VENV_BIN)/python.exe
    UVICORN     := $(VENV_BIN)/uvicorn.exe
    PIP         := $(VENV_BIN)/pip.exe
    SYS_PYTHON  := python
else
    VENV_BIN    := $(VENV_DIR)/bin
    PYTHON      := $(VENV_BIN)/python
    UVICORN     := $(VENV_BIN)/uvicorn
    PIP         := $(VENV_BIN)/pip
    SYS_PYTHON  := python3
endif

# Fallback se o venv estiver no padrao Unix (bin)
ifeq ($(wildcard $(VENV_DIR)/bin/python),$(VENV_DIR)/bin/python)
    VENV_BIN    := $(VENV_DIR)/bin
    PYTHON      := $(VENV_BIN)/python
    UVICORN     := $(VENV_BIN)/uvicorn
    PIP         := $(VENV_BIN)/pip
endif

.PHONY: all help setup dev run stop down db-start db-stop db-reset db-status backend frontend docs test test-backend clean check-env check-backend check-frontend

# Alvo padrao: exibe ajuda com os comandos disponiveis
all: help

# ------------------------------------------------------------------------------
# Ajuda e Documentacao
# ------------------------------------------------------------------------------
help:
	@echo ""
	@echo "======================================================================"
	@echo " Agenda UnB - Comandos de Automacao (Make)"
	@echo "======================================================================"
	@echo "  make dev          - Sobe Banco (Supabase), Backend e Frontend juntos"
	@echo "  make setup        - Instala todas as dependencias e configura o .env"
	@echo "  make stop         - Encerra os containers do banco de dados (Supabase)"
	@echo ""
	@echo " Comandos Individuais:"
	@echo "  make backend      - Executa apenas a API FastAPI"
	@echo "  make frontend     - Executa apenas o servidor Vite do Frontend"
	@echo "  make docs         - Executa o servidor local de documentacao MkDocs"
	@echo ""
	@echo " Banco de Dados (Supabase Local):"
	@echo "  make db-start     - Inicia os containers do Supabase (PostgreSQL/Auth)"
	@echo "  make db-stop      - Para os containers do Supabase"
	@echo "  make db-reset     - Reaplica todas as migracoes e o seed inicial"
	@echo "  make db-status    - Exibe o status e URLs dos servicos Supabase"
	@echo ""
	@echo " Qualidade e Testes:"
	@echo "  make test         - Executa a suite de testes automatizados"
	@echo "  make clean        - Limpa caches (__pycache__, pytest, dist)"
	@echo "======================================================================"
	@echo ""

# ------------------------------------------------------------------------------
# Verificacoes de Pre-requisitos
# ------------------------------------------------------------------------------
check-env:
	@if [ ! -f "$(ROOT_DIR)/.env" ]; then \
		echo "[INFO] Arquivo .env nao encontrado. Copiando de .env.example..."; \
		cp "$(ROOT_DIR)/.env.example" "$(ROOT_DIR)/.env"; \
	fi

check-backend:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "[INFO] Criando ambiente virtual em $(VENV_DIR)..."; \
		$(SYS_PYTHON) -m venv $(VENV_DIR) || python -m venv $(VENV_DIR); \
		echo "[INFO] Instalando dependencias do Backend..."; \
		$(PIP) install -r $(ROOT_DIR)/backend/requirements.txt; \
		if [ -f "$(ROOT_DIR)/backend/requirements-dev.txt" ]; then \
			$(PIP) install -r $(ROOT_DIR)/backend/requirements-dev.txt; \
		fi \
	fi

check-frontend:
	@if [ ! -d "$(ROOT_DIR)/frontend/node_modules" ]; then \
		echo "[INFO] Instalando dependencias do Frontend..."; \
		cd "$(ROOT_DIR)/frontend" && npm install; \
	fi

# ------------------------------------------------------------------------------
# Setup Completo
# ------------------------------------------------------------------------------
setup: check-env
	@echo "[SETUP] Iniciando configuracao completa do ambiente..."
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "[SETUP] Criando venv do Python..."; \
		$(SYS_PYTHON) -m venv $(VENV_DIR) || python -m venv $(VENV_DIR); \
	fi
	@echo "[SETUP] Instalando dependencias do Backend..."
	@$(PIP) install -r $(ROOT_DIR)/backend/requirements.txt
	@if [ -f "$(ROOT_DIR)/backend/requirements-dev.txt" ]; then \
		$(PIP) install -r $(ROOT_DIR)/backend/requirements-dev.txt; \
	fi
	@echo "[SETUP] Instalando dependencias do Frontend..."
	@cd "$(ROOT_DIR)/frontend" && npm install
	@echo "[SETUP] Inicializando banco de dados Supabase..."
	@npx supabase start
	@echo ""
	@echo "[OK] Setup concluido com sucesso!"
	@echo "Execute: make dev"

# ------------------------------------------------------------------------------
# Execucao Principal (Back + Front + Banco em 1 comando)
# ------------------------------------------------------------------------------
run: dev

dev: check-env check-backend check-frontend db-start
	@echo ""
	@echo "======================================================================"
	@echo " Agenda UnB - Servicos em Execucao"
	@echo "======================================================================"
	@echo " Frontend:        http://localhost:$(FRONTEND_PORT)"
	@echo " Backend API:     http://localhost:$(BACKEND_PORT)"
	@echo " Swagger / Docs:  http://localhost:$(BACKEND_PORT)/docs"
	@echo " Health Check:    http://localhost:$(BACKEND_PORT)/health"
	@echo " Supabase Studio: http://localhost:$(SUPABASE_STUDIO_PORT)"
	@echo "======================================================================"
	@echo " Pressione [Ctrl+C] para encerrar o Backend e o Frontend."
	@echo "======================================================================"
	@echo ""
	@bash -c '\
		(cd "$(ROOT_DIR)/backend" && $(UVICORN) src.main:app --reload --port $(BACKEND_PORT)) & \
		BACK_PID=$$!; \
		(cd "$(ROOT_DIR)/frontend" && npm run dev -- --port $(FRONTEND_PORT)) & \
		FRONT_PID=$$!; \
		trap "echo \"\"; echo \"[INFO] Encerrando Backend e Frontend...\"; kill $$BACK_PID $$FRONT_PID 2>/dev/null; exit 0" INT TERM EXIT; \
		wait $$BACK_PID $$FRONT_PID'

# ------------------------------------------------------------------------------
# Servicos Individuais
# ------------------------------------------------------------------------------
backend: check-env check-backend
	@echo "[INFO] Iniciando Backend FastAPI na porta $(BACKEND_PORT)..."
	@cd "$(ROOT_DIR)/backend" && $(UVICORN) src.main:app --reload --port $(BACKEND_PORT)

frontend: check-frontend
	@echo "[INFO] Iniciando Frontend React na porta $(FRONTEND_PORT)..."
	@cd "$(ROOT_DIR)/frontend" && npm run dev -- --port $(FRONTEND_PORT)

docs:
	@echo "[INFO] Iniciando servidor MkDocs em http://127.0.0.1:8008..."
	@mkdocs serve -a 127.0.0.1:8008

# ------------------------------------------------------------------------------
# Banco de Dados (Supabase)
# ------------------------------------------------------------------------------
db-start:
	@echo "[INFO] Verificando / Iniciando Supabase..."
	@npx supabase start

db-stop:
	@echo "[INFO] Parando containers do Supabase..."
	@npx supabase stop

db-reset:
	@echo "[INFO] Resetando banco e reaplicando migracoes/seed..."
	@npx supabase db reset

db-status:
	@npx supabase status

stop: db-stop
	@echo "[OK] Todos os servicos foram paralisados."

down: stop

# ------------------------------------------------------------------------------
# Testes e Qualidade
# ------------------------------------------------------------------------------
test: test-backend

test-backend: check-backend
	@echo "[TEST] Executando suite de testes do Backend..."
	@cd "$(ROOT_DIR)/backend" && $(PYTHON) -m pytest tests/ 2>/dev/null || \
		(cd "$(ROOT_DIR)/backend" && $(PYTHON) -m pytest tests/) || \
		(echo "[DICA] Certifique-se de instalar as dependencias de teste com: $(PIP) install -r $(ROOT_DIR)/backend/requirements-dev.txt" && exit 1)

clean:
	@echo "[CLEAN] Limpando caches e arquivos temporarios..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf frontend/dist 2>/dev/null || true
	@echo "[OK] Limpeza concluida!"
