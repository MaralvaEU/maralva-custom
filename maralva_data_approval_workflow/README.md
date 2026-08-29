# Maralva - Flujo de aprobación de datos

## Descripción

Depende de `maralva_default_values`, como todos los módulos `maralva_*`. Define
**materias** (Ventas, Compras, Administración, un responsable general...), cada
una con sus responsables (usuarios normales, sin ningún grupo/rol especial) y
los campos que vigila en cualquier modelo instalado. Cuando se crea un registro
o se modifica alguno de esos campos, se genera (o reabre) una línea de
aprobación pendiente para esa materia y se notifica al responsable mediante una
actividad sobre el propio registro -- igual que ya hace Odoo para otros avisos
de revisión en este proyecto (ej. "Excepción").

## Cómo funciona por dentro

Igual que `maralva_default_values`, no reinventa el enganche a los modelos:
cada `maralva.approval.subject` (materia) genera y mantiene sincronizada, por
cada modelo que tenga campos vigilados, una `base.automation` con disparador
`on_create_or_write` y `trigger_field_ids` (para que solo se dispare al crear,
o al escribir alguno de los campos vigilados, no en cualquier guardado). El
código generado es mínimo -- delega toda la lógica real en
`maralva.approval.line` (buscar/crear/reabrir la línea, programar la
actividad), en vez de meter lógica de negocio dentro del código Python que se
ejecuta en el sandbox restringido (`safe_eval`) de `ir.actions.server`.

Cualquier modelo que quiera participar añade el mixin `maralva.approval.mixin`
(`_inherit = ['res.partner', 'maralva.approval.mixin']`, ver `models/res_partner.py`
como primer caso real) -- aporta el estado de aprobación agregado
(`maralva_approval_state`), la lista de líneas de aprobación
(`maralva_approval_line_ids`, mismo patrón que `mail.activity.mixin.activity_ids`:
`res_id` como `Many2oneReference` con `model_field='res_model'`, no un `Integer`
plano -- así funciona como inverso polimórfico de un One2many) y un botón
"Documentos relacionados" que busca en `ir.model.fields` cualquier modelo con
un Many2one/Many2many hacia este registro y lista lo que encuentra, para que el
responsable decida si merece la pena corregir algo ya creado con datos
desactualizados.

## Alcance de esta primera versión (deliberado)

- **Solo notifica y deja trazabilidad** -- no bloquea nada todavía. El bloqueo
  de "confirmar/validar un documento si usa un registro con una materia
  pendiente" (`sale.order.action_confirm`, `account.move` al validar, etc.) se
  valoró en el diseño pero se deja para una segunda iteración: es un puñado de
  overrides puntuales sobre esos métodos concretos, no algo que haya que
  rediseñar aquí -- reutilizaría una tabla materia↔modelo-consumidor que no
  existe todavía.
- Sin cadena de aprobación forzada -- el campo `sequence` de la materia es
  orientativo, no bloquea que se apruebe una materia antes que otra.
- `responsible_ids` es una lista plana de usuarios, sin distinción por
  compañía -- si un grupo Maralva necesita responsables distintos por empresa
  para la misma materia, de momento habría que crear una materia por empresa.
- El botón "Documentos relacionados" es de solo lectura y bajo demanda (no se
  ejecuta en cada `create`/`write` de todo el sistema) -- limitado a modelos
  con `_auto=True` y `limit=200` resultados por modelo referenciador.

## Estado

Implementado y validado por `odoo-bin shell` contra `proasurjnma`: creación de
materia con campo vigilado -> línea pendiente + actividad al crear un contacto
-> aprobar -> reabrir al modificar de nuevo el campo vigilado -> "Documentos
relacionados" encuentra correctamente una factura de venta creada con ese
contacto.
