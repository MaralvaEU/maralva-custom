# Maralva - Importación de impuestos IGIC (Canarias)

## Descripción

Añade la configuración oficial de impuestos IGIC (localización de Canarias)
a una compañía/sucursal que ya tiene instalada una localización española
peninsular (ej. PGC Completo). Pensado para el caso de una empresa con sede
en Península y una sucursal en Canarias (modelo de "ramas" de Odoo 17+),
donde cada sucursal necesita su propio régimen fiscal.

## Cómo funciona

Al instalar el módulo (`post_init_hook`), se crean en la **compañía activa
en ese momento** (`env.company`):

- Los ~8 grupos/cuentas específicos de IGIC que no existen ya en el plan
  peninsular (ej. `4727`/`4777`, IGIC soportado/repercutido).
- Los impuestos IGIC (venta, compra, recargo de equivalencia, importación
  DUA...), reutilizando el parser de plantillas fiscales del core
  (`account.chart.template._parse_csv` sobre `es_canary_common`, la capa
  "delta" de Canarias en `l10n_es`) en vez de una copia estática — así se
  heredan las correcciones que Odoo/OCA vayan aplicando a la plantilla
  oficial.

Los conceptos genéricos que ya existen en la matriz con el mismo nombre
(retenciones, "Resta Base"/DUA no ligado a IGIC) **no se duplican**: las
referencias a ellos se resuelven solas contra los de la matriz.

## Importante: compañía activa al instalar

Los impuestos son un dato por compañía, y una sucursal recién creada no
tiene un ID de XML estable al que este módulo pueda apuntar directamente.
Por eso, **hay que tener seleccionada la sucursal de Canarias en el
selector de compañías antes de instalar este módulo** — el hook aplica la
configuración a la compañía activa en ese momento, no a una sucursal
concreta por nombre.

**Pendiente de evolución**: sustituir esta instalación automática por un
asistente (wizard) que permita elegir explícitamente la compañía/sucursal
destino y repetir la carga a demanda, sin depender de qué compañía esté
activa en el selector.
