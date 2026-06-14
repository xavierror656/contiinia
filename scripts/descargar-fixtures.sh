#!/usr/bin/env bash
# descargar-fixtures.sh
# Script placeholder — instrucciones para obtener CFDIs reales del SAT para pruebas manuales.
# Este script NO descarga nada automáticamente.

set -euo pipefail

cat <<'EOF'
=============================================================
  INSTRUCCIONES: Obtener CFDIs reales del SAT para pruebas
=============================================================

Este proyecto usa fixtures sintéticos en fixtures/*.xml para
las pruebas automatizadas. Para pruebas manuales con CFDIs
reales, sigue estas instrucciones:

------------------------------------------------------------
OPCIÓN 1 — Portal del SAT (Buzón Tributario)
------------------------------------------------------------
1. Accede a https://www.sat.gob.mx/personas/buzon-tributario
2. Inicia sesión con tu RFC + contraseña o e.firma.
3. Ve a "Mis documentos digitales" o "Consulta CFDI".
4. Descarga los XML de los CFDIs que desees usar como prueba.
5. Colócalos en el directorio fixtures/ con nombres descriptivos,
   p. ej.: cfdi_real_ingreso.xml, cfdi_real_pago.xml, etc.

------------------------------------------------------------
OPCIÓN 2 — Verificador de CFDI (consulta puntual)
------------------------------------------------------------
1. Accede a https://verificacfdi.facturaelectronica.sat.gob.mx/
2. Ingresa el UUID (folio fiscal) del CFDI que tienes.
3. Descarga el XML desde el resultado de la consulta.

------------------------------------------------------------
OPCIÓN 3 — Descarga masiva (SAT WS)
------------------------------------------------------------
El SAT provee servicios web para descarga masiva de CFDIs:
- Autenticación: https://cfdidescargamasiva.clouda.sat.gob.mx/
- Documentación oficial: https://www.sat.gob.mx/cs/Satellite?blobcol=urldata&blobkey=id&blobtable=MungoBlobs&blobwhere=1461173418583

Herramientas de terceros que facilitan este proceso:
  - satcfdi (Python): https://github.com/josuemtzmo/satcfdi
  - descargasat (Python): buscar en PyPI

------------------------------------------------------------
NOTA IMPORTANTE
------------------------------------------------------------
Los CFDIs reales contienen datos fiscales sensibles (RFC,
montos, conceptos). NO los incluyas en el repositorio.
Agrega a .gitignore:
  fixtures/cfdi_real_*.xml

=============================================================
EOF
