# Maralva - Importación de contratos

## Descripción

Cuarto módulo de la familia `maralva_import_*`. Migra únicamente la
**cabecera** de los gastos recurrentes ("contratos" en sentido amplio:
alquileres, seguros, suscripciones, tasas...) detectados por análisis sobre
el diario contable -- el resto (facturación real, vencimientos, líneas de
detalle) se gestiona a mano, no lo cubre este módulo. Depende de
[`maralva_import_account`](../maralva_import_account/README.md) (la
cabecera referencia cuentas/proveedores ya importados) y, a través de él,
de [`maralva_migration_base`](../maralva_migration_base/README.md) para la
trazabilidad de la migración -- mismo patrón que el resto de la familia.

Caso real que lo motiva: PROASUR, tras un análisis de 3 años de diario
(2024-2026) y ocho rondas de depuración manual, deja una lista cerrada de
61 candidatos a contrato (`maralva_import_account/samples/PROASUR/contratos_detectados.xlsx`,
hoja "Contratos candidatos") -- ver `ESTADO.md` para el histórico completo
del análisis.

## Estado

Scaffold sin lógica propia todavía. Pendiente de que el usuario dé la
especificación de campos de la cabecera (tras estudiar el resultado del
análisis) antes de diseñar el modelo -- mismo enfoque que el resto de la
familia: no diseñar el mapeo a ciegas sin especificación confirmada.

## Familia `maralva_import_*`

- `maralva_import_contacts` — contactos (`res.partner`), ya implementado.
- `maralva_import_account` — contabilidad, en curso (SERINGE/UTE NUNSYS/PROASUR).
- `maralva_import_analytic` — contabilidad analítica, scaffold.
- `maralva_import_contract` — este módulo, depende de `maralva_import_account`.
