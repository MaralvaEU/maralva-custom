# Maralva - Importación de contabilidad

## Descripción

Segundo módulo de la familia `maralva_import_*` (el primero fue
[`maralva_import_contacts`](../maralva_import_contacts/README.md)): migración
de datos contables (`account.account`, y lo que se defina) desde una
aplicación externa. Depende técnicamente de
[`maralva_migration_base`](../maralva_migration_base/README.md) para la
trazabilidad de la migración (registro de ficheros subidos, wizard genérico
de importación, lotes, mapeo de IDs externos, log de incidencias) en vez de
implementarla por su cuenta — mismo patrón que `maralva_import_contacts`.

## Estado

Scaffold sin lógica propia todavía. Pendiente de definir, con datos reales de
la aplicación de origen: qué entidades contables importar exactamente (plan
contable, cuentas, asientos de apertura, cuentas bancarias...), en qué
formato llegan los datos y el mapeo de campos concreto — mismo enfoque que se
siguió con `maralva_import_contacts`: no diseñar el mapeo a ciegas sin un
caso real.

## Familia `maralva_import_*`

- `maralva_import_contacts` — contactos (`res.partner`), ya implementado.
- `maralva_import_account` — este módulo.
- `maralva_import_analytic` — contabilidad analítica, depende de este módulo.
