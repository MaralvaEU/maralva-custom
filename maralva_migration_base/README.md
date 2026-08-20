# Maralva - Infraestructura de migración de datos

## Descripción

Módulo base común para la familia `maralva_import_*`: cada módulo de
migración de un área de negocio concreta (contactos, y en el futuro
financiero, compras, proyectos...) depende técnicamente de este módulo en
vez de reimplementar su propia trazabilidad.

Objetivo: que cada instalación de Odoo active solo los módulos de las áreas
que esa empresa/BD realmente necesite migrar, compartiendo todos el mismo
mecanismo de lotes, mapeo de IDs y log de incidencias.

## Contenido (v1)

Esta primera versión cubre solo la infraestructura de datos; el asistente
(wizard) genérico de carga queda pendiente para cuando exista un primer caso
real que lo use (`maralva_import_contacts`) y pueda dar forma a su diseño.

- **`maralva.migration.batch`** (lote de migración): agrupa una ejecución de
  migración — aplicación de origen, compañía destino, estado y fecha — y da
  acceso a sus mapeos e incidencias asociados. Incluye `log_info()`,
  `log_warning()` y `log_error()` para que un módulo concreto registre
  incidencias sin tener que conocer el modelo `maralva.migration.log`.
- **`maralva.migration.id.map`** (mapeo de IDs externos): relaciona el ID de
  un registro en el sistema de origen (`source_app` + `source_model` +
  `source_id`) con el registro de Odoo creado a partir de él (`res_model` +
  `res_id`). La búsqueda (`get_res_id()`) es intencionadamente independiente
  del lote que creó el mapeo: si se repite una migración en un lote nuevo,
  debe seguir encontrando lo ya importado en lotes anteriores para no
  duplicarlo. `set_mapping()` crea el mapeo o actualiza el existente si ya
  había uno para ese mismo origen.
- **`maralva.migration.log`** (log de incidencias): un mensaje con nivel
  (información/aviso/error) ligado a un lote, y opcionalmente al modelo/ID de
  origen que lo originó.

Vistas mínimas bajo *Ajustes > Técnico > Migraciones Maralva* para inspeccionar
lotes, sus mapeos y sus incidencias.

## Cómo lo usa un módulo concreto (ej. `maralva_import_contacts`)

```python
batch = env['maralva.migration.batch'].create({
    'name': 'Contactos - carga inicial',
    'source_app': 'CRM antiguo',
})

res_id = env['maralva.migration.id.map'].get_res_id(
    'CRM antiguo', 'clientes', external_id, 'res.partner')
if not res_id:
    partner = env['res.partner'].create({...})
    env['maralva.migration.id.map'].set_mapping(
        'CRM antiguo', 'clientes', external_id, 'res.partner', partner.id, batch=batch)

if algo_fallo:
    batch.log_error("motivo del fallo", res_model='res.partner', source_id=external_id)
```
