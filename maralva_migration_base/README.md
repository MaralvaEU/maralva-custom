# Maralva - Infraestructura de migración de datos

## Descripción

Módulo base común para la familia `maralva_import_*`: cada módulo de
migración de un área de negocio concreta (contactos, y en el futuro
financiero, compras, proyectos...) depende técnicamente de este módulo en
vez de reimplementar su propia trazabilidad.

Objetivo: que cada instalación de Odoo active solo los módulos de las áreas
que esa empresa/BD realmente necesite migrar, compartiendo todos el mismo
mecanismo de lotes, mapeo de IDs y log de incidencias.

## Contenido

- **`maralva.migration.import.file`** (fichero subido) + **`maralva.migration.import.file.target`**
  (tabla destino de ese fichero): registro común de los ficheros que se suben
  para migrar datos, independiente de qué módulo de área los procese.
  Guarda el archivo (descargable), su nombre y tipo (calculado de la
  extensión), la aplicación de origen, una descripción editable y el estado
  de comprobación (`Subido` / `Comprobado con errores` / `Totalmente
  comprobado`). Un mismo fichero puede alimentar varias tablas de Odoo a la
  vez (ej. un CLIENTES.xlsx que crea contactos y, si trae IBAN, también
  cuentas bancarias): cada tabla destino es una línea propia con su nombre
  técnico (`res_model`), su nombre legible (calculado vía `ir.model`) y su
  propio estado de importación (`Sin importar` / `Parcial` / `Total` / `Con
  errores`). Vista de lista en *Ajustes > Técnico > Migraciones Maralva >
  Ficheros subidos*.
  - **Compañía del fichero** (`company_mode`): `Compañía única` (caso normal,
    un solo `company_id` fijo para todo el fichero) o `Multicompañía` — el
    fichero mezcla datos de varias compañías de origen (ej. varias empresas
    dentro del mismo Sage) y hace falta indicar **a mano** en
    `maralva.migration.import.file.company` qué compañía de Odoo corresponde
    a cada código de compañía de origen (ej. el `Cód. empresa` de Sage). Cada
    módulo de área es responsable de leer esa relación fila a fila al
    importar; el modelo base solo guarda la relación, no sabe qué columna del
    fichero es el código de compañía (eso lo decide cada `maralva_import_*`).
- **`maralva.migration.import.group`** (+ `...group.line` para sus tablas
  relacionadas): registro de qué "grupos principales" de importación existen
  — uno por módulo `maralva_import_*` instalado (ej. `contacts` →
  "Contactos") — y qué método de `maralva.migration.import.file` ejecuta la
  importación de ese grupo. Cada módulo de área declara su propio grupo como
  dato (XML), sin que este módulo base necesite conocer nada específico de
  ese área. Las líneas de "tablas relacionadas" (ej. Bancos, Modos de pago
  para el grupo Contactos) son opcionales y quedan vacías hasta que el módulo
  de área las registre con datos reales que las respalden.
- **`maralva.migration.import.wizard`** (+ `...wizard.line`): asistente
  genérico que aparece como acción al seleccionar uno o varios ficheros en
  *Ficheros subidos*. Muestra la aplicación de origen de los seleccionados
  (con aviso si no coincide entre todos) y la lista de grupos de importación
  disponibles, cada uno con su casilla y, si tiene tablas relacionadas
  declaradas, un multi-selección para elegir cuáles importar también. Al
  confirmar, llama dinámicamente al `action_method` de cada grupo/tabla
  relacionada elegidos sobre los ficheros seleccionados.
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
