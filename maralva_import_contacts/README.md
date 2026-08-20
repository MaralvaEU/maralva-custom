# Maralva - Importación de contactos

## Descripción

Primer módulo de la familia `maralva_import_*`: migración de contactos
(`res.partner`) desde una aplicación externa. Depende técnicamente de
[`maralva_migration_base`](../maralva_migration_base/README.md) para la
trazabilidad de la migración (lotes, mapeo de IDs externos, log de
incidencias) en vez de implementarla por su cuenta.

## Estado

Scaffold sin lógica propia todavía — solo la dependencia de
`maralva_migration_base` está enganchada. Pendiente de definir, con datos
reales de la aplicación de origen: formato de los datos a importar (CSV,
XLSX...), qué campos de contacto mapear y el asistente (wizard) de carga.
