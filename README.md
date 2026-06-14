# contiinia

CLI para procesamiento de CFDI 4.0 (Comprobante Fiscal Digital por Internet).

> README mínimo — se completa en Hito 4.8.

## Privacidad de datos fiscales

Los CFDI reales de contribuyentes son datos fiscales sensibles. Este proyecto sigue el Principio 7:
- Los fixtures sintéticos (RFC ficticios, importes inventados) van en git.
- Los CFDI reales van en `fixtures/reales/` que está en `.gitignore` y **nunca** se versionan.
- El CLI no loguea RFC ni importes sin consentimiento explícito.
