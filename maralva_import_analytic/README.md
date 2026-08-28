# Maralva - Importación de contabilidad analítica

## Descripción

Tercer módulo de la familia `maralva_import_*`. Migración de datos de
contabilidad analítica (planes/cuentas analíticas) desde una aplicación
externa. Depende de [`maralva_import_account`](../maralva_import_account/README.md)
(lo analítico se apoya en la contabilidad/cuentas ya importadas) y, a través
de él, de [`maralva_migration_base`](../maralva_migration_base/README.md)
para la trazabilidad de la migración — mismo patrón que el resto de la
familia.

## Estado

Scaffold sin lógica propia todavía. Pendiente de definir, con datos reales de
la aplicación de origen: qué entidades analíticas importar (planes,
cuentas/centros de coste...), en qué formato llegan los datos y el mapeo de
campos concreto — mismo enfoque que `maralva_import_contacts`: no diseñar el
mapeo a ciegas sin un caso real.

## Familia `maralva_import_*`

- `maralva_import_contacts` — contactos (`res.partner`), ya implementado.
- `maralva_import_account` — contabilidad, scaffold.
- `maralva_import_analytic` — este módulo, depende de `maralva_import_account`.
