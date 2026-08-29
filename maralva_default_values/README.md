# Maralva - Campos obligatorios y valores por defecto

## Descripción

Módulo independiente de `maralva_migration_base` (no depende de él, y viceversa) --
pensado para ser útil tanto en migraciones de datos como en implantaciones **desde
cero, sin ninguna migración de por medio**: define reglas condicionales de dos
tipos sobre cualquier modelo/campo instalado en Odoo:

- **Obligatorio**: bloquea el guardado (creación o edición) si el campo queda
  vacío y la condición se cumple.
- **Fijar valor por defecto**: si el campo está vacío y la condición se cumple,
  se rellena automáticamente con el valor indicado.

Ambas acciones son **condicionales** (no un simple booleano fijo por campo) --
la condición se define como un dominio Odoo, con el mismo widget que un filtro
avanzado (`widget="domain"`), incluyendo operadores como "empieza por"
(necesario para reglas sobre datos contables por prefijo de cuenta).

## Cómo funciona por dentro

Cada `maralva.default.rule` genera y mantiene sincronizada una regla de
automatización nativa de Odoo (`base.automation`, módulo core `base_automation`)
con un único `ir.actions.server` de tipo "Código Python" que, sobre los
registros que cumplen la condición (`filter_domain`), aplica el valor por
defecto y/o lanza `UserError` si el campo obligatorio sigue vacío. No hay
lógica propia de "escucha" de creación/edición -- se apoya por completo en el
motor de automatización ya existente en Odoo (disparador `on_create_or_write`),
en vez de reinventar un mecanismo de enganche a todos los modelos.

## Menú

Primer módulo en usar la convención nueva: menú raíz **"Maralva"**
(`menu_maralva_root`), restringido a `base.group_system` (administrador) --
pensado para agrupar ahí todos los temas técnicos/configuración de los
módulos `maralva_*` futuros, a diferencia de menús de operativa normal
(ej. "Avales" de `maralva_bank_guarantees`, que se queda en Facturación/
Contabilidad). **Pendiente**: si un segundo módulo también necesita este
menú raíz, sacar su definición a un módulo común mínimo (para no duplicar
el `menuitem` en dos sitios) -- de momento se define aquí porque es el
primer caso real.

## Estado

Implementado y validado por `odoo-bin shell`: regla obligatoria (bloquea
crear un registro sin el campo cuando la condición se cumple), regla de
valor por defecto (con casteo por tipo de campo: booleano, entero,
many2one, fecha/fecha-hora, texto/selección), y sincronización de la
`base.automation` al editar/borrar la regla.

## Pendiente

- Tipos de campo soportados por ahora: char/text/html/selection, boolean,
  integer/float/monetary, many2one, date/datetime. No cubre
  many2many/one2many (no tiene sentido "obligatorio"/"valor por defecto"
  simple sobre una colección).
- Sin UI para construir el valor por defecto de forma tipada (hoy es un
  `Char` con el valor en texto, casteado según el tipo del campo) --
  suficiente para el primer caso de uso, se puede mejorar con un widget
  más amigable más adelante si hace falta.
