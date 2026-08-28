# Maralva - Avales/fianzas de venta

## Estado

Cascarón del módulo: manifest y dependencias (`sale`, `maralva_bank_guarantees`)
ya fijadas, sin modelos todavía. Pendiente de que se acuerde la
especificación funcional completa (relación con el pedido/proyecto de
venta, tipo de fianza, importe, vencimiento) antes de diseñar nada.

## Dependencias

- `sale`: el aval/fianza de este módulo nace ligado a una venta.
- `maralva_bank_guarantees`: reutiliza la infraestructura común de gestión
  de avales bancarios (no reimplementa su propio modelo de aval).
