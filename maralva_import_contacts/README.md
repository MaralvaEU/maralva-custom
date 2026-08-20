# Maralva - Importación de contactos

## Descripción

Primer módulo de la familia `maralva_import_*`: migración de contactos
(`res.partner`) desde una aplicación externa. Depende técnicamente de
[`maralva_migration_base`](../maralva_migration_base/README.md) para la
trazabilidad de la migración (lotes, mapeo de IDs externos, log de
incidencias) en vez de implementarla por su cuenta.

## Estado

Implementado y validado el caso real de origen **Sage**. No tiene wizard de
subida propio: se engancha al asistente genérico de `maralva_migration_base`
(`maralva.migration.import.wizard`) registrando el grupo de importación
**"Contactos"** (`data/maralva_migration_import_group_data.xml`) y añadiendo
el método `action_import_sage_contacts` a `maralva.migration.import.file`.
Flujo real: subir el/los XLSX (clientes, proveedores, o ambos a la vez) en
*Ajustes > Técnico > Migraciones Maralva > Ficheros subidos*, seleccionarlos
y lanzar la acción **"Importar"** — el wizard genérico muestra "Contactos"
como grupo disponible (es el único mientras no haya más módulos
`maralva_import_*` instalados); al marcarlo y confirmar, crea/actualiza
`res.partner`.

**Multicompañía**: si un fichero mezcla varias compañías de origen (el
`Cód. empresa` de Sage), marca `company_mode = 'multi'` en el fichero y
declara en su pestaña "Relación de compañías" a qué compañía de Odoo
corresponde cada código — la importación resuelve la compañía fila a fila
contra esa relación manual, y si una fila trae un código sin relación
declarada, esa fila se registra como error en el log del lote (no se
adivina). Con `company_mode = 'single'` (caso normal) sigue habiendo un único
`company_id` fijo para todo el fichero, como antes.

El fichero se identifica como clientes o proveedores **por contenido, no por
nombre**: mira qué columna de código (`Cód. cliente` / `Cód. proveedor`)
tiene realmente valores no vacíos en las filas. Esto importa porque Sage
incluye en cada hoja, vacía, la columna de código de la otra hoja (ej.
`PROVEEDORES.xlsx` trae también una columna `Cód. cliente`, de referencia
cruzada, siempre vacía en la práctica) — detectar solo por presencia de la
columna clasificaba mal el fichero.

### Mapeo de campos (Sage → `res.partner`)

| Sage | `res.partner` | Notas |
|---|---|---|
| `Cód. cliente` / `Cód. proveedor` | — | Solo se usa como ID externo en `maralva.migration.id.map`, no se guarda en el partner. |
| `Razón social` | `name` | |
| `CIF/DNI` | `vat` | Tal cual, sin prefijo de país (así se valida un CIF/NIF español nativo en Odoo). |
| `CIF/DNI` (1er carácter) | `company_type` | Dígito o `X`/`Y`/`Z` → persona física; letra → empresa (NIF/NIE vs. CIF). |
| `Teléfono` | `phone` | |
| `Correo Electrónico1` | `email` | |
| `Municipio` | `city` | |
| `Provincia` | `state_id` | Busca en `res.country.state` de España por `ilike` (no exacto, por nombres dobles tipo "A Coruña (La Coruña)"). |
| `Domicilio` (clientes) / `Dom. recibo` (proveedores) | `street` | Mismo nombre de columna ("Dom. recibo") significa cosas distintas en cada hoja de Sage; ver Decisiones. |
| `Cód. postal` | `zip` | |
| — | `country_id` | Fijo España (la columna `Nación` de Sage no trae datos en el caso real). |
| — (fichero de origen) | `customer_rank` / `supplier_rank` | A 1 según se importe desde el fichero de clientes o de proveedores. |

Columnas de Sage explícitamente **no mapeadas** (decisión del usuario): `Nombre 3`
(sin uso real en Sage en este caso), direcciones/contactos secundarios de Sage
(la empresa no los usa), y cualquier dato contable/comercial (código contable,
tarifas, comisiones...) — fuera del alcance de un módulo de *contactos*.

### Deduplicación cliente/proveedor

Si el mismo CIF/DNI aparece en ambos ficheros (caso real: la propia empresa
aparece como cliente y como proveedor a la vez), se fusiona en un único
`res.partner` con `customer_rank` y `supplier_rank` marcados, en vez de crear
dos registros — decisión explícita del usuario, y comportamiento nativo de
Odoo. La búsqueda de "¿ya existe?" mira primero `maralva.migration.id.map`
(para no duplicar entre relanzamientos) y, si no hay mapeo previo, busca por
`vat` en la compañía.

Filas sin código externo o sin razón social se omiten con un aviso en el log
del lote, sin abortar el resto de la importación.

### Prerrequisito técnico

Depende de la librería Python `openpyxl` (ya presente en el venv de Odoo) y
del módulo `account` de Odoo — únicamente porque `customer_rank`/
`supplier_rank` viven ahí, no en `base`/`contacts`.

## Pendiente

- Soporte de CSV (por ahora solo XLSX, único formato real usado hasta hoy).
- Acción de "comprobar" (validar sin escribir en Odoo) todavía no existe;
  por ahora `check_state` del fichero se actualiza como efecto secundario de
  la propia acción de importar (`checked_ok`/`checked_error` según si hubo
  errores), a falta de que el usuario defina la comprobación como paso
  independiente.
- "Tablas relacionadas" del grupo Contactos (Bancos, Modos de pago, Plazos de
  pago...) sin implementar todavía: en los ficheros reales de Sage esas
  columnas (`I.B.A.N.`, `Forma de pago`) están vacías, así que no hay datos
  reales contra los que diseñar ese mapeo por ahora.
