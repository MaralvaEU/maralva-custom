# Maralva - Gestión de avales bancarios

## Estado

Cascarón del módulo: manifest y dependencia (`account`) ya fijados, sin
modelos todavía. Pendiente de que se acuerde la especificación funcional
completa (qué es un aval en este contexto, campos, estados, relación con
cuentas/pólizas, vencimientos, renovación) antes de diseñar nada.

## Dependencias

- `account`: un aval bancario es, en esencia, una garantía asociada a la
  contabilidad de la empresa (cuenta de orden, coste financiero, entidad
  avalista como partner contable).
