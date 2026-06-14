#!/usr/bin/env bash
# build.sh — Build reproducible de contiinia con Docker multi-stage
set -euo pipefail

VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
IMAGE="contiinia:${VERSION}"
BUILDER_IMAGE="contiinia-builder:${VERSION}"

echo "==> Building contiinia v${VERSION}"

# 1. Build de la imagen completa (ambos stages)
docker build \
  --target runtime \
  --tag "${IMAGE}" \
  --tag "contiinia:latest" \
  .

echo "==> Image built: ${IMAGE}"

# 2. Extraer el binario del stage builder para distribución local
echo "==> Extracting binary to dist/"
mkdir -p dist

# Construir solo el stage builder para extraer el binario
docker build \
  --target builder \
  --tag "${BUILDER_IMAGE}" \
  .

# Extraer binario sin correr el contenedor
CONTAINER_ID=$(docker create "${BUILDER_IMAGE}")
docker cp "${CONTAINER_ID}:/build/dist/contiinia" ./dist/contiinia
docker rm "${CONTAINER_ID}"

echo "==> Binary extracted to dist/contiinia/"
echo "    Size: $(du -sh dist/contiinia/ | cut -f1)"

# 3. Smoke test del binario extraído (sin Python/venv activo)
echo "==> Smoke test (binary without venv)..."
env -i PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  ./dist/contiinia/contiinia version

echo "==> Smoke test del binario con fixture XML..."
env -i PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  ./dist/contiinia/contiinia xml fixtures/cfdi_ingreso.xml | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK tipo=' + d['tipo_de_comprobante'] + ' total=' + d['total'])"

echo "==> Smoke test --schema..."
env -i PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  ./dist/contiinia/contiinia xml --schema | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK schema title=' + d.get('title','(sin titulo)'))"

echo ""
echo "==> Build completo"
echo "    Imagen Docker:   ${IMAGE}"
echo "    Binario local:   dist/contiinia/contiinia"
echo "    Version:         ${VERSION}"
