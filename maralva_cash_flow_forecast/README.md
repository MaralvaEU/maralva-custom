# Maralva - Previsión de tesorería

## Estado

Cascarón del módulo: manifest y dependencias (`account_payment`,
`spreadsheet_account`, `spreadsheet_dashboard_account`) ya fijadas, sin
modelos/hoja de cálculo todavía. Pendiente de que se acuerde la
especificación funcional completa antes de diseñar nada.

## Visión funcional (de partida, 2026-08-31)

Una hoja de cálculo (`spreadsheet_account`/`spreadsheet_dashboard_account`)
que filtre datos de las distintas aplicaciones instaladas para construir
una previsión de tesorería, identificando siempre de qué fuente sale cada
dato. Fuentes previstas:

- **Contabilidad**: partidas sin conciliar, filtradas por tipo de cuenta.
  **Pendiente**: el usuario indicará qué tipos de cuenta contable hay que
  coger — no asumir ningún filtro hasta entonces.
- **Pedidos de compra y de venta.**
- **Proyectos.**
- **Préstamos** (`account_loan`, OCA).
- **`maralva_bank_guarantees`** (avales).
- **Medias calculadas de gastos de personal.**
- **Movimientos contables**, filtrados por categoría de producto, producto
  o cuenta analítica.

Pensado para el caso real de `proasurjnma`, pero como módulo general/
reutilizable (mismo criterio que `maralva_bank_guarantees`/
`maralva_sale_guarantees_bond`) — por eso vive en `19.0-JNMA`, no en
`19.0-proa`.

## Dependencias

- `account_payment`: pagos/cobros ligados a facturas ya conciliadas o
  pendientes.
- `spreadsheet_account`: integración de hoja de cálculo con datos
  contables (Odoo 19).
- `spreadsheet_dashboard_account`: dashboards de hoja de cálculo sobre
  datos contables.
