.POSIX:
.SILENT:

MAKEFLAGS += --no-print-directory -s

# ----------------------------------------------------------------
# ENVIRONMENT & TOOLCHAIN CONFIGURATION
# ----------------------------------------------------------------

PYTHON != [ -x ".venv/bin/python" ] && echo ".venv/bin/python -B" || echo "python3 -B"
PACKAGES = moderngl glfw PyGLM numpy
DEV_PACKAGES = ruff pyright

export PYTHONDONTWRITEBYTECODE = 1
export RUFF_CACHE_DIR = /tmp/ruff-cache

.PHONY: all run debug release setup env venv install install-dev test check lint clean clean-builds purge fmt format fmt-md prettier fmt-check check-fmt help

all: run

### ================================
### HELP & DOCUMENTATION
### ================================

help:
	cmd() { printf "    \033[36mmake %-18s\033[0m %s\n" "$$1" "$$2"; }; \
	sec() { printf "\n  \033[1;33m%s\033[0m\n" "$$1"; }; \
	printf "\n  \033[1;37mMaix que um Circuito — Jogo 3D em ModernGL (Max-Cut)\033[0m\n"; \
	printf "  ============================================================\n"; \
	sec "Execução & Modos:"; \
	cmd "run"            "Executa o jogo em modo padrão (debug)"; \
	cmd "debug"          "Executa o jogo explicitamente em modo Debug"; \
	cmd "release"        "Executa o jogo em modo Release (--release)"; \
	sec "Ambiente & Dependências:"; \
	cmd "venv, setup"    "Cria .venv isolada (uv ou python3 -m venv) e instala pacotes"; \
	cmd "install"        "Instala os pacotes necessários (moderngl, glfw, PyGLM, numpy)"; \
	cmd "install-dev"    "Instala também ferramentas de análise (ruff, pyright)"; \
	sec "Testes & Qualidade:"; \
	cmd "test"           "Executa a validação dos módulos (grafo.py e camera.py)"; \
	cmd "check"          "Verifica sintaxe/estilo (Ruff) e tipagem estática (Pyright)"; \
	cmd "lint"           "Alias para 'make check'"; \
	sec "Formatação Markdown (Prettier):"; \
	cmd "fmt, format"    "Formata recursivamente todos os .md com Prettier (ignora . e __)"; \
	cmd "fmt-check"      "Verifica a conformidade de formatação dos .md"; \
	sec "Manutenção, Builds & Limpeza:"; \
	cmd "clean"          "Remove caches Python e resíduos LaTeX"; \
	cmd "clean-builds"   "Remove artefatos de build e empacotamento (dist, build, *.zip)"; \
	cmd "purge"          "Executa clean + clean-builds e remove ambientes (.venv, .conda)"; \
	echo ""

### ================================
### ENVIRONMENT & PACKAGE SETUP
### ================================

setup env venv:
	echo "🐍 Configurando ambiente virtual (.venv)..."
	if command -v uv >/dev/null 2>&1; then \
		uv venv --system-site-packages .venv; \
	else \
		python3 -m venv --system-site-packages .venv; \
	fi
	$(MAKE) install
	echo "✅ Ambiente virtual configurado com sucesso!"

install:
	echo "📦 Instalando dependências do projeto..."
	if [ ! -d ".venv" ]; then \
		if command -v uv >/dev/null 2>&1; then \
			uv venv --system-site-packages .venv; \
		else \
			python3 -m venv --system-site-packages .venv; \
		fi; \
	fi
	if command -v uv >/dev/null 2>&1; then \
		if [ -f "requirements.txt" ]; then \
			uv pip install --python .venv/bin/python -r requirements.txt; \
		else \
			uv pip install --python .venv/bin/python $(PACKAGES); \
		fi; \
	else \
		.venv/bin/python -m pip install --upgrade pip; \
		if [ -f "requirements.txt" ]; then \
			.venv/bin/python -m pip install -r requirements.txt; \
		else \
			.venv/bin/python -m pip install $(PACKAGES); \
		fi; \
	fi
	echo "✅ Pacotes instalados com sucesso!"

install-dev: install
	echo "🛠️  Instalando ferramentas de desenvolvimento (Ruff & Pyright)..."
	if command -v uv >/dev/null 2>&1; then \
		uv pip install --python .venv/bin/python $(DEV_PACKAGES); \
	else \
		.venv/bin/python -m pip install $(DEV_PACKAGES); \
	fi
	echo "✅ Ferramentas de desenvolvimento instaladas!"

### ================================
### EXECUTION & TESTING
### ================================

run: debug

debug:
	$(PYTHON) main.py

release:
	$(PYTHON) main.py --release

test:
	echo "🧪 Executando testes dos módulos (grafo.py e camera.py)..."
	$(PYTHON) grafo.py
	$(PYTHON) camera.py
	$(MAKE) clean
	echo "✅ Testes dos módulos concluídos com sucesso!"

### ================================
### STATIC ANALYSIS & LINTING
### ================================

check:
	echo "🔍 [1/2] Verificando sintaxe e estilo com Ruff..."
	if [ -x ".venv/bin/ruff" ]; then \
		.venv/bin/ruff check --cache-dir /tmp/ruff-cache --select E,F,W --ignore E501 . && echo "  ✅ Ruff: nenhuma violação de sintaxe encontrada."; \
	elif command -v ruff >/dev/null 2>&1; then \
		ruff check --cache-dir /tmp/ruff-cache --select E,F,W --ignore E501 . && echo "  ✅ Ruff: nenhuma violação de sintaxe encontrada."; \
	else \
		echo "  ⚠️  Ruff não encontrado. Rode 'make install-dev' ou instale ruff."; \
	fi
	echo "🔍 [2/2] Verificando tipagem estática com Pyright..."
	if [ -x ".venv/bin/pyright" ]; then \
		.venv/bin/pyright . && echo "  ✅ Pyright: 0 erros de tipagem encontrados."; \
	elif command -v pyright >/dev/null 2>&1; then \
		pyright . && echo "  ✅ Pyright: 0 erros de tipagem encontrados."; \
	elif command -v npx >/dev/null 2>&1; then \
		npx --yes pyright . && echo "  ✅ Pyright: 0 erros de tipagem encontrados."; \
	else \
		echo "  ⚠️  Pyright/npx não encontrado. Rode 'make install-dev' ou instale pyright."; \
	fi
	$(MAKE) clean
	echo "✨ Verificação concluída com sucesso!"

lint: check

### ================================
### CLEANUP (AUTO-HEALING & BUILDS)
### ================================

clean:
	echo "🧹 Limpando caches temporários e resíduos LaTeX..."
	find . -type d \( -name "__pycache__" -o -name ".ruff_cache" -o -name ".pytest_cache" -o -name ".mypy_cache" \) -exec rm -rf {} + 2>/dev/null || true
	find . -type f \( -name "*.py[cod]" -o -name "*$$py.class" -o -name "*.aux" -o -name "*.log" -o -name "*.out" -o -name "*.toc" -o -name "*.lof" -o -name "*.lot" -o -name "*.fls" -o -name "*.fdb_latexmk" -o -name "*.synctex.gz" -o -name "*.bbl" -o -name "*.blg" -o -name "*.tmp" -o -name "*.bak" -o -name "*~" \) -delete 2>/dev/null || true
	echo "✅ Caches e resíduos limpos com sucesso!"

clean-builds:
	echo "📦 Removendo artefatos de build e empacotamento..."
	find . -type d \( -name "build" -o -name "dist" -o -name "*.egg-info" \) -exec rm -rf {} + 2>/dev/null || true
	find . -maxdepth 2 -type f \( -name "*.zip" -o -name "*.tar.gz" \) -delete 2>/dev/null || true
	echo "✅ Artefatos de build removidos com sucesso!"

purge: clean clean-builds
	echo "🗑️  Removendo ambientes virtuais (.venv, venv, env, .conda)..."
	find . -type d \( -name ".venv" -o -name "venv" -o -name "env" -o -name ".conda" \) -exec rm -rf {} + 2>/dev/null || true
	echo "✅ Ambientes virtuais e builds removidos com sucesso!"

### ================================
### CODE FORMATTING & PRETTIER
### ================================

fmt format fmt-md prettier:
	echo "✨ Formatando arquivos Markdown (.md) com Prettier..."
	if command -v prettier >/dev/null 2>&1; then \
		PRETTIER="prettier"; \
	elif command -v npx >/dev/null 2>&1; then \
		PRETTIER="npx --yes prettier"; \
	else \
		echo "  ⚠️  Prettier não encontrado. Instale Node.js/npx ou prettier globalmente."; \
		exit 1; \
	fi; \
	find . -type d \( -name ".*" ! -name "." -o -name "__*" \) -prune -o -type f -name "*.md" -exec $$PRETTIER --write {} +
	echo "✅ Arquivos Markdown formatados com sucesso!"

fmt-check check-fmt:
	echo "🔍 Verificando formatação dos arquivos Markdown (.md) com Prettier..."
	if command -v prettier >/dev/null 2>&1; then \
		PRETTIER="prettier"; \
	elif command -v npx >/dev/null 2>&1; then \
		PRETTIER="npx --yes prettier"; \
	else \
		echo "  ⚠️  Prettier não encontrado. Instale Node.js/npx ou prettier globalmente."; \
		exit 1; \
	fi; \
	find . -type d \( -name ".*" ! -name "." -o -name "__*" \) -prune -o -type f -name "*.md" -exec $$PRETTIER --check {} +
	echo "✅ Verificação de formatação Markdown aprovada!"
