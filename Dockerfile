# syntax=docker/dockerfile:1
# Stage 1: builder — instala deps y genera binario con PyInstaller
FROM python:3.11-slim AS builder

WORKDIR /build

# binutils es requerido por PyInstaller en Linux (objdump)
RUN apt-get update && apt-get install -y --no-install-recommends binutils && rm -rf /var/lib/apt/lists/*

# Instala uv
RUN pip install --no-cache-dir uv==0.4.29

# Copia manifiestos primero para aprovechar cache de capas
COPY pyproject.toml uv.lock ./

# Instala solo dependencias (sin el paquete propio) para cachear esta capa
RUN uv sync --frozen --no-install-project --extra dev

# Copia el código fuente y fixtures
COPY contiinia/ ./contiinia/
COPY fixtures/ ./fixtures/

# Instala el paquete propio en el venv ya creado
RUN uv sync --frozen --extra dev

# Build binario con PyInstaller en modo --onedir
RUN uv run pyinstaller \
    --onedir \
    --name contiinia \
    --distpath dist \
    --noconfirm \
    --hidden-import lxml.etree \
    --hidden-import lxml._elementpath \
    --hidden-import pandas \
    --hidden-import openpyxl \
    --hidden-import pdfplumber \
    --hidden-import typer \
    --hidden-import pydantic \
    --collect-all typer \
    --collect-all pydantic \
    contiinia/cli.py

# Verifica que el binario funciona dentro del builder
RUN ./dist/contiinia/contiinia version

# Stage 2: runtime — imagen mínima con solo el binario y fixtures
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copia el directorio compilado desde el builder
COPY --from=builder /build/dist/contiinia ./contiinia/
COPY --from=builder /build/fixtures ./fixtures/

# Verifica en la imagen final
RUN /app/contiinia/contiinia version

ENTRYPOINT ["/app/contiinia/contiinia"]
CMD ["--help"]
