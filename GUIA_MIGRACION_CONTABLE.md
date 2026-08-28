# Guía de migración contable Sage → Odoo (familia `maralva_import_*`)

> Consolidado a partir de las migraciones reales de SERINGE MAR SL, UTE NUNSYS y PROASUR (agosto 2026) -- ver `ESTADO.md` para el detalle completo, empresa a empresa, de cada decisión y cada bug real que aquí solo se resume. Esta guía existe porque las tres migraciones se hicieron descubriendo el orden sobre la marcha; el objetivo es que la siguiente empresa no tenga que redescubrirlo.
>
> Convención: cada fase indica **qué hace falta antes de empezarla**, **qué preguntar al usuario si no está ya decidido**, y **qué suele salir mal**. Nada de esto es automático todavía -- son scripts de un solo uso en el scratchpad de cada sesión, validados contra una copia de descarte (`pg_dump`/`pg_restore`) antes de tocar la base real, y solo se mueven al módulo `maralva_import_account` cuando el proceso esté maduro.

## Regla de oro, antes de nada

**Nunca se construye nada directamente contra la base de datos real** sin haberlo validado antes en una copia de descarte (`pg_dump` + `pg_restore` a una BD nueva, filestore aparte si hace falta, se borra al terminar). Esto ha salvado la sesión varias veces (el bug de REPEP en Canarias, el de company_id en Tesorería, etc. se detectaron y corrigieron en copia antes de tocar lo real).

**Nunca se asume una regla genérica sin comprobarla con datos reales de la empresa en curso.** Cada empresa de este grupo ha traído al menos una sorpresa que rompía una regla que había funcionado bien en la anterior (ver "Diferencias entre empresas" al final). Antes de reutilizar una regla de una migración anterior, compruébala contra un puñado de casos reales de la nueva.

---

## Fase 0 -- Descubrimiento y preguntas previas

Antes de tocar ningún fichero, averiguar (o preguntar explícitamente al usuario):

1. **Estructura societaria en Odoo**: ¿la empresa es una compañía única, o hay matriz + sucursales (`branch`, `parent_id`/`root_id`)? Las sucursales **comparten plan de cuentas e impuestos con la matriz** (no tienen cuentas propias) pero **sí tienen diarios propios**. Confirmarlo con SQL/shell antes de asumir nada (`parent_id`/`root_id` de `res.company`).
2. **¿Es una empresa aislada o parte de un grupo?** Si hay grupo (varias empresas que comparten contactos/proveedores reales), los contactos deben quedar **sin restricción de compañía** (`company_id` vacío) salvo que haya un motivo real para restringirlos -- si no, aparecerán bloqueos al facturar desde otra empresa del grupo más adelante y habrá que desrestringirlos uno a uno según van apareciendo.
3. **¿Localización canaria (IGIC) en alguna sucursal?** Si sí, hay que aplicar `maralva_export_import_igic` (impuestos + posiciones fiscales) **antes** de construir ninguna factura de esa sucursal.
4. **¿Contabilidad analítica?** Si sí: qué dimensiones (Proyecto/Departamento/Sección son las vistas hasta ahora), de dónde salen los catálogos, y si hay una categoría de gestión especial tipo "OTROS" (préstamos/leasing/activos/RRHH...) que necesite su propio plan analítico.
5. **Rango de fechas del diario a importar** -- confirmarlo explícitamente y por escrito, no asumir "todo lo disponible" (UTE NUNSYS se importó completo por no haberlo preguntado a tiempo; SERINGE y PROASUR sí llevaron un corte acordado).
6. **Formato real del diario de origen** -- Sage exporta con esquemas distintos según la instalación: columna única `Cuenta`+`De/Ha` explícito (el más simple), o `Cta. Cargo`/`Cta. Abono` con una columna `Importe` (donde hay que deducir con cuidado quién postea de verdad cuando ambas vienen rellenas -- **esta regla ha sido distinta en cada empresa**, ver más abajo). No asumir el esquema de la empresa anterior.
7. **¿Hay una columna explícita de tipo de factura** (`E/R`, `E/R/I`) o hay que deducirlo por patrón Debe/Haber de las cuentas 430/400/410? La columna explícita es mucho más fiable si existe.

---

## Fase 1 -- Plan de cuentas

1. **Igualar el nº de dígitos** si el plan de Odoo no coincide con el de origen (ej. 6→9 dígitos, rellenando con ceros **al final**, no al principio -- confirmado con datos reales).
2. **Filtrar por movimiento real**: cruzar el plan de cuentas contra los "sumas y saldos" disponibles (normalmente el del cierre del año anterior + el más reciente) -- una cuenta "tiene movimiento" si aparece en cualquiera de los dos, aunque su saldo sea cero. Esto es un filtro de qué se importa, **no borra nada en Odoo**.
3. **Colapsar cuentas "con desarrollo"** (variantes internas de una cuenta base que la empresa usa en Sage sin ser oficiales del PGC) a su base **a 4 dígitos, no a 3** -- error real cometido en SERINGE y corregido: agrupar a 3 dígitos fusiona cuentas oficiales distintas (ej. `2813`/`2814`). Si el origen trae una columna explícita de cuántos dígitos colapsar cuenta a cuenta (como el `COLAPSO` que dio el usuario para PROASUR: 3/4/5/0, siendo `0`="no colapsar, literal"), es más fiable que una regla genérica -- pedirla si no viene dada.
   - Excepciones típicas que **no** se colapsan: bancos/cajas/tarjetas reales (cada una es una cuenta de verdad, no una variante), pólizas de crédito.
   - Cuidado con falsos positivos del agrupamiento automático: una variante puede en realidad ser una cuenta oficial distinta del PGC (ej. `4009` "Proveedores, facturas pendientes de recibir" no es una subcuenta de cliente/proveedor). Contrastar caso a caso, no asumir.
4. **Crear las cuentas que falten**, con `account_type` sacado de la plantilla oficial (`account.account-es_common*.csv` de `l10n_es`) por analogía con la cuenta "hermana" más cercana ya existente en esa familia -- nunca adivinado a ojo. Ejemplo: bancos/caja → `asset_cash`; tarjetas de crédito/pólizas → `liability_current` con `reconcile=True`; etc.
5. **Cuentas de cliente/proveedor**: no calcular el partner por fórmula (prefijo 4300/4000 + código) si se puede evitar -- mejor **cruzar el código de cuenta contra el fichero de CLIENTES/PROVEEDORES** para sacar CIF/razón social real. Cubre tanto el caso normal como las excepciones sin depender de que la fórmula sea siempre cierta.

## Fase 2 -- Contactos (`maralva_import_contacts`)

1. Detectar clientes/proveedores **por contenido, no por nombre de fichero** (columnas con datos reales, no solo presencia de columna -- Sage a veces trae columnas cruzadas vacías, ej. "Cód. cliente" también en el fichero de proveedores).
2. **Fusionar por CIF** cuando el mismo tercero es cliente y proveedor a la vez.
3. **VAT con prefijo de país real** (`ES`/`BE`/... según el país del contacto, deducido de la columna "CIF europeo" si la trae, no fijo a "ES"), validado con **el propio validador de Odoo** (crear dentro de un `savepoint`, capturar `ValidationError`) -- si no es válido o el país no existe en Odoo (casos reales: `XU` Parlamento Europeo, `QU`/`XN`...), se deja en blanco y se crea una actividad de Excepción con el dato original, nunca se descarta en silencio.
4. **VAT duplicado en varias cuentas contables**: crear 1 partner "matriz" (sin propiedades fiscales/de pago) + N hijos `type='invoice'` con `parent_id`=matriz, cada uno con sus propias propiedades según su cuenta de origen -- no fusionar todo en un único partner (se perdería la cuenta a cobrar/pagar específica de cada uno).
5. **Etiquetas por prefijo de cuenta** (ej. `400x`→"Proveedor", `410x`→"Prov. Servicios" en el caso de PROASUR) -- confirmar con el usuario el criterio exacto, no asumir que todos los proveedores llevan la misma etiqueta.
6. **Cuentas a cobrar/pagar y posición fiscal por defecto**: fijar `property_account_receivable_id`/`payable_id` (con `.with_company()`, son `company_dependent`) y una posición fiscal por defecto razonable (ej. "España Península" a nacionales, "Régimen Intracomunitario" a UE, "Régimen Extracomunitario" al resto) **antes** de poder facturar bien -- si no, todas las facturas caen en el impuesto genérico de la compañía.
7. **Contactos compartidos en un grupo de empresas**: si aparece un contacto ya existente pero restringido a una sola compañía del grupo (patrón que se ha repetido en cada empresa nueva: PROA SUR, NAECO FIBERS, VITROCANGA...), quitarle la restricción de compañía en vez de duplicarlo.

## Fase 3 -- Contabilidad analítica (si aplica)

1. Un plan por dimensión (Proyecto/Departamento/Sección...), filtrando los catálogos de origen por uso real en el diario (igual criterio que las cuentas: solo lo que aparece de verdad).
2. Si se usa `project.project` para los proyectos: Odoo genera la cuenta analítica sola (vía `hr_timesheet`) si no se informa `account_id` en el `create()` -- pero **no rellena el `code`**, hay que fijarlo a mano después para poder cruzarlo con el diario.
3. **Categorías de gestión especial** (préstamos, leasing, activos, RRHH...) que no son ni proyecto ni departamento ni sección: un plan analítico propio (ej. "OTROS"), con una cuenta por cada cuenta contable que lo necesite.

> ### ⚠️ El bug más caro de toda la migración: `analytic_distribution` con claves separadas
>
> Cuando una línea necesita varias dimensiones analíticas a la vez (Proyecto + Departamento + Sección, y "OTROS" si aplica), **hay que usar UNA sola clave combinada** con los ids de las distintas cuentas analíticas unidos por comas: `{"15,24,297": 100.0}`. Escribir una clave separada por cada plan (`{"15": 100.0, "24": 100.0, "297": 100.0}`) **no da error, pero genera 3-4 líneas analíticas independientes en vez de 1 sola con las 3-4 columnas rellenas** -- cualquier informe que cruce dimensiones (ej. "gasto de Proyecto X dentro de la Sección Y") sale vacío o incompleto, sin ningún aviso visible. En PROASUR esto afectó a **todo el diario** (3.818 líneas, 11.427 líneas analíticas rotas) antes de detectarse. Ver memoria `odoo-analytic-distribution-combined-keys` -- probarlo con un asiento de prueba (crear con ambos formatos y comparar `account.analytic.line` generadas) antes de dar por buena la construcción de ninguna línea con analítica múltiple.
>
> Si hay que corregir analítica ya construida y contabilizada: no hace falta despublicar el asiento. Escribir `line.with_context(skip_analytic_sync=True).analytic_distribution = {...}` (evita que Odoo fusione la distribución vieja con la nueva), **antes** hacer `line.analytic_line_ids.unlink()`, y luego `line._create_analytic_lines()`.

## Fase 4 -- Diarios y secuencias

1. Un diario por cada cuenta bancaria/caja/tarjeta/póliza de crédito **real** (no uno genérico) -- necesario para que Tesorería se pueda construir bien (fase 9).
2. Diarios de ventas/compras por serie de facturación real, y **por sucursal** si la empresa tiene ramas (Península/Canarias...) con series propias.
3. **Una sucursal puede usar directamente un diario de la matriz** sin dar error -- no hace falta duplicar diarios de tesorería/generales por rama si la decisión es que esa categoría "vive siempre en la matriz" (ver fase 7).
4. Cada diario con su propia `ir.sequence`, `use_date_range=True` y periodos (`ir.sequence.date_range`) para los años que vayan a necesitarse.
5. Si se cargan diarios desde un Excel con ids externos: revisar el fichero a mano antes de la carga final -- han aparecido erratas reales (id externo duplicado entre dos series, un dígito de más en un código de cuenta).

## Fase 5 -- Productos (para poder construir facturas)

Se crea **un `product.product` por cada cuenta de ingreso/gasto** (6xx/7xx) que aparece en facturas reales -- así las líneas de factura se construyen solo con `product_id` + cantidad + importe, sin tocar `account_id`/`tax_ids` a mano (el producto ya lleva la cuenta y el impuesto por defecto; la posición fiscal del contacto añade la retención si corresponde).

- Nombre: `"<cuenta ORIGEN de Sage> - <descripción>"` (la cuenta de origen, no la ya colapsada -- así dos subcuentas que colapsan a la misma cuenta Odoo pueden seguir siendo productos distintos).
- Si hay analítica por sección: la clave del producto pasa a ser **cuenta + sección** (no solo cuenta) -- varias cuentas pueden tener más de un producto/sección, cuidado con buscar el producto correcto exigiendo coincidencia exacta de sección, no solo el prefijo del nombre (bug real en PROASUR: no afectó a cuentas/importes, solo dejó mal etiquetado qué producto aparecía en algunas facturas).
- `600/601/602/700/701/702` = bienes (`type='consu'`); el resto = servicio. `6xx` solo compra (`purchase_ok`), `7xx` solo venta (`sale_ok`).

> ### ⚠️ Segundo bug caro: la cuenta del producto no llega a las ramas
>
> `property_account_income_id`/`property_account_expense_id` de `product.template` son campos **por compañía** (jsonb). Si el producto se crea con la compañía matriz activa, la cuenta queda grabada **solo bajo la clave de la matriz** -- y a diferencia de `account.account.code` (que sí tiene un mecanismo especial de fallback a la compañía raíz), **este campo no hace ningún fallback** cuando se lee desde una sucursal sin su propia clave: Odoo cae en la cuenta genérica de la categoría del producto, sin ningún aviso. En PROASUR esto afectó a **1.716 líneas de 1.662 facturas ya contabilizadas** en Península/Canarias antes de detectarse. Ver memoria `odoo-company-dependent-fields-no-branch-fallback`.
>
> **Mitigación**: al crear productos que se van a usar desde una sucursal, escribir la cuenta explícitamente para cada compañía relevante (`product.with_company(company_id).write({'property_account_income_id': ...})`), no solo para la matriz. Si ya se ha corregido en real: extender la clave del jsonb con el mismo valor de la matriz, y corregir `account_id` en las líneas ya contabilizadas (no hace falta tocar importes/impuestos, solo la cuenta).

## Fase 6 -- Asiento de apertura

1. Se construye **aparte, desde el fichero de "sumas y saldos" del cierre del año anterior** -- nunca reutilizando un asiento de apertura que pueda venir embebido dentro del propio diario del periodo a importar (puede estar incompleto o tener discrepancias reales frente al saldo oficial; excluir esas filas del diario si aparecen).
2. Mismo mecanismo de colapso de cuentas y resolución de partner que el resto del proceso.
3. **Odoo puede exigir distribución analítica obligatoria en las líneas de cuentas 6/7** aunque sea un asiento de apertura -- el "sumas y saldos" no trae esa analítica. Pedir al usuario un valor por defecto razonable (Proyecto/Departamento/Sección "genéricos", ej. los usados para PROASUR: `0010`/`7`/`0231`) antes de intentar publicar, o el asiento se bloqueará al validar.
4. Las cuentas de Hacienda Pública (470/475) suelen necesitar partner AEAT (u otro organismo -- **no asumir que siempre es AEAT**, verificar el organismo real de cada subcuenta).

## Fase 7 -- Clasificación del diario del periodo

1. Determinar el esquema de columnas exacto de este diario (fase 0, punto 6) y cómo se marca una factura (columna explícita `E/R`/`E/R/I` si existe; si no, patrón Debe/Haber de 430/400/410 -- y confirmar con el usuario si hace falta comparar contra libros de IVA como validación cruzada).
2. **La regla de qué cuenta postea de verdad cuando ambas `Cta. Cargo`/`Cta. Abono` vienen rellenas en la misma fila HA SIDO DISTINTA en cada empresa** -- en UTE NUNSYS solo postea la que indica el flag `Cargo/Abono` de esa fila; en PROASUR, en facturas, `Cta. Cargo` postea siempre y `Cta. Abono` es solo informativa (salvo en las intracomunitarias, donde es al revés); en Operaciones varias del propio PROASUR, **ambas postean si ambas están rellenas**. Verificar esto cuadrando un lote de asientos completos antes de escribir ningún código de construcción, no asumir la regla de la empresa anterior.
3. **Categorías**: Ventas, Compras, Tesorería (cualquier apunte que toque una cuenta de banco/caja/tarjeta -- salvo las cuentas de control que no cuentan como movimiento real, ej. "pendiente de conciliación bancaria"), Operaciones varias (el resto).
4. **Reparto por sucursal** (si aplica): normalmente solo las **facturas** se reparten Península/Canarias; Tesorería y Operaciones varias suelen quedarse **siempre en la matriz** -- confirmarlo explícitamente, no asumirlo. Señales típicas de "es de Canarias": serie de factura específica, cuentas de IVA específicas de Canarias, proyecto de una lista conocida -- tratarlas como OR entre sí, y dejar aparte (sin asignar rama por defecto) los asientos cuya única señal sea un dato ambiguo, para que el usuario decida.
5. **Asientos mixtos** (factura + su propio pago/cobro en el mismo asiento, o varias líneas de banco a la vez): partirlos en dos o más movimientos independientes -- la primera línea de banco suele marcar el corte entre "lo que es factura" y "lo que es tesorería"; casos donde la propia línea de factura postea directo contra el banco (sin cuenta 400/410/430 intermedia) van a una lista de excepciones aparte, no se fuerza ninguna regla genérica sobre ellos.
6. **Vigilar "juegos contables" de Sage que no son lo que parecen**: el caso real de las adquisiciones intracomunitarias en PROASUR (un apunte de gasto marcado "Recibida" + el mismo importe marcado "Emitida" a IVA repercutido, solo para que ambas cifras caigan en las casillas correctas del modelo de IVA, sin representar ninguna venta real) se coló al principio en "facturas emitidas" por una clasificación demasiado simple. Cuando algo no encaja con el patrón esperado, mirar el conjunto completo del asiento antes de forzar una clasificación.
7. Cuando un mismo nº de asiento de Sage contiene varias sub-facturas o rectificativas distintas (combinaciones cliente+nº de factura distintas bajo el mismo asiento), construir **una factura Odoo por cada combinación**, no una sola con todas las líneas juntas.

## Fase 8 -- Facturas de venta y compra

1. Construir como `account.move` real (`out_invoice`/`in_invoice`, o sus rectificativas), **nunca** como asiento genérico -- las líneas son solo `product_id` + cantidad + importe (el producto ya resuelve cuenta e impuesto por defecto), el impuesto real lo calcula la posición fiscal del contacto.
2. **Rectificativas: importe siempre en positivo**, aunque el origen las traiga en negativo -- al marcar `move_type` como refund, Odoo ya invierte el efecto solo; replicar el signo negativo de origen lo invertiría dos veces.
3. **Retención (IRPF)**: como un **segundo impuesto en la misma línea**, no como una línea aparte -- confirmar con el usuario qué posiciones fiscales de retención existen (19% arrendamientos, 15%/7% profesionales...) y qué las dispara (puede depender de la cuenta de ingreso/gasto, no de la serie ni del cliente).
4. **Desglose del IVA/IGIC cuando el diario no lo da explícito**: si hay una sola línea de ingreso/gasto agregada y hace falta deducir el tipo por diferencia, buscar por fuerza bruta qué combinación de tipos REALES existentes en la compañía reproduce exactamente el importe -- nunca aceptar un tipo "inventado" que no exista como impuesto real. Si hay más de una posible combinación (o ninguna), no forzar: crear con el mejor reparto aproximado y marcar con una actividad de Excepción para revisión manual. Si existe una fuente más fiable con el desglose real (ej. un "Libro de IVA/IGIC" que el cliente pueda exportar de Sage), usarla en vez de inferir -- confirmado en PROASUR Canarias que el diario agregaba en una sola línea facturas que en realidad llevaban 2 tipos de IGIC distintos, invisibles sin el libro.
5. **Numeración**: en ventas, si hace falta fijar el `name` explícito para que coincida con la secuencia de origen, construirlo por serie (con el mapeo real de prefijos de diario, que puede no coincidir literalmente con lo que trae el Excel). En compras, el número del proveedor va al campo `ref`, `name` lo asigna la secuencia automática de Odoo.
6. **Cuentas especiales de empresas del grupo** (ej. "acreedores por operaciones en común y de UTEs"): confirmar con el usuario si una cuenta de proveedor concreta representa en realidad a otra empresa del mismo grupo antes de tratarla como un proveedor externo normal.
7. **Nunca reutilizar, para una posición fiscal nueva, un impuesto "exento" que ya sea destino de otra posición fiscal existente** -- `original_tax_ids` es una propiedad del propio registro de impuesto, no de la posición fiscal; reutilizarlo cambia también lo que calculan TODAS las demás posiciones que ya usaban ese mismo impuesto de destino, en silencio. Bug real: reutilizar `EXEMPT PO/S (IGIC)` para la posición REPEP de PROASUR puso a cero el IGIC de 13 facturas ya creadas con "Régimen Islas Canarias", varias sin ninguna señal de aviso. Crear siempre un impuesto exento dedicado por posición fiscal nueva.
8. **Activos fijos / leasing**: si el diario trae asientos de inmovilizado, construirlos como factura normal contra la cuenta de activo pero marcarlos con Excepción -- la lógica real de gestión de activos/leasing se deja para un módulo aparte (`account_loan` de OCA es un buen candidato para preparar, ver más abajo), no se improvisa aquí.

## Fase 9 -- Tesorería

1. Se construye como **extracto bancario real** (`account.bank.statement`/`account.bank.statement.line`), nunca como asiento manual -- el diario de cada línea se detecta por la cuenta de tesorería asociada a su `default_account_id`.
2. `account.bank.statement.company_id` **sigue siempre al de su diario** (campo relacionado) -- no se puede forzar independientemente. Decidir de antemano si toda la tesorería va a nivel de matriz o se reparte por rama, y aplicarlo desde el principio (corregirlo a posteriori significa mover diarios y sus secuencias).
3. **Técnica de conciliación automática, sin trabajo manual posterior**: en vez de crear un asiento aparte (transitoria↔contrapartida) y conciliarlo luego contra el extracto, **modificar directamente el asiento que autogenera la propia línea de extracto**: quitarle la línea de cuenta "outstanding" (pendiente de cobro/pago) o transitoria, e inyectarle la contrapartida real (cuenta + partner) en su lugar. Esto es justo lo que hace Odoo al conciliar de verdad, así que la línea de extracto queda `is_reconciled=True` sin ningún paso manual. Las cuentas "outstanding" no se adivinan por código fijo -- se resuelven dinámicamente vía `account.chart.template.ref('account_journal_payment_debit_account_id'|'..._credit_account_id')`, y en la práctica Odoo puede haber usado la cuenta transitoria genérica en vez de la configurada -- reconocer varias cuentas candidatas, no solo una.
4. **Asientos con varias líneas de banco a la vez** (extracto completo de un mes metido en un solo asiento de Sage): emparejar cada línea de banco con su contrapartida exacta por importe (y por texto de comentario si hay ambigüedad de fecha/importe repetidos) y extraer cada pareja como su propia línea de extracto -- nunca asumir una sola línea de banco por asiento.
5. **Transferencias entre 2+ cuentas de tesorería propias**: cada cuenta genera su propia línea de extracto, sin sugerir partner -- se compensan solas contra la cuenta de transferencias internas de la compañía, sin necesitar un tercer movimiento.
6. **Bug reproducible del shell de Odoo, específico de este framework**: crear un `account.bank.statement` (con `line_ids` anidadas) dentro de una función Python (`def`) del script de shell puede fallar con `NotNullViolation` en `journal_id`, con el mismo código funcionando perfectamente fuera de la función. **Ejecutar siempre la creación real a nivel superior del script**, nunca dentro de un `def`.
7. **Revisar sistemáticamente si algún asiento de "Operaciones varias" toca en realidad una cuenta de tesorería** -- ha pasado en más de una migración que asientos que debían ser extracto se quedaron como asiento genérico por error de clasificación temprano. Los "simples" (una sola línea de banco) se migran directo; los "complejos" (varias líneas o varias cuentas) casi siempre resultan ser 2+ operaciones independientes agrupadas por Sage bajo el mismo número de asiento -- emparejar y partir, nunca tratarlos como una unidad indivisible sin comprobarlo primero con el usuario.

## Fase 10 -- Operaciones varias

Asiento genérico (`entry`), línea a línea, con las mismas reglas de cuentas/partner/analítica ya establecidas.

- **La regla de signo puede ser distinta de la de facturas** (ver fase 7, punto 2) -- verificar cuadrando un lote real antes de construir nada.
- **Deduplicar filas exactamente repetidas** si el origen las trae dos veces (visto en pagos con tarjeta) -- comprobarlo cuadrando los asientos antes/después de deduplicar.

## Fase 11 -- Desglose de efectos de cobro/pago pendientes

El asiento de apertura solo trae el saldo agregado por cliente/proveedor -- si el negocio necesita ver cada efecto individual (nº de efecto, fecha de vencimiento), se desglosa aparte: un asiento nuevo (fecha de cierre del ejercicio anterior, diario general), con una línea que revierte el agregado por (cuenta colapsada, partner) y una línea por cada efecto individual, sin cambiar el saldo neto. Comparar la suma de efectos contra el saldo de apertura antes de dar cada bloque por bueno -- las discrepancias son frecuentes (contactos muy antiguos sin línea en la apertura filtrada) y se marcan con Excepción, no se fuerzan a cuadrar.

## Fase 12 -- Contratos (gastos recurrentes)

Análisis puro sobre el diario (sin construir nada en Odoo hasta el final), pensado para terminar en el módulo `maralva_import_contract`:

1. **Filtrar candidatos a nivel de LÍNEA, no de asiento** -- un asiento puede agrupar varios cargos independientes (extracto de tarjeta/banco completo metido de una vez); filtrar el asiento entero por tener alguna línea excluible pierde gastos recurrentes reales que van mezclados con ruido en el mismo asiento.
2. Rondas iterativas de exclusión, con **clave estable persistida entre rondas** (tipo + proveedor/código/concepto normalizado + cuenta + sección -- nunca por número de fila, que cambia entre rondas), en un fichero de configuración versionado en el repo, no solo en el scratchpad.
3. Agrupar por (proveedor o concepto normalizado, cuenta, sección), clasificar periodicidad por la mediana de días entre apariciones consecutivas.
4. Resolver proveedor: por CIF cruzando el plan de cuentas filtrado contra `res.partner.vat` (quitando el prefijo de país si `vat` lo lleva y el origen no), reforzado por `res.partner.ref` si trae el código de cuenta embebido -- confirmar el formato real de `vat` en la BD antes de asumir si lleva o no prefijo de país (ha sido distinto entre sesiones/documentación).
5. Casos de fusión (mismo gasto, concepto mal escrito o partido) y casos de "varios contratos reales bajo el mismo proveedor/mes" (aglutinar en Odoo en un único registro con varias líneas cuando corresponda) son decisiones humanas -- no intentar automatizarlas por heurística, dejar que el usuario las marque explícitamente sobre el Excel de candidatos.
6. Al crear las cabeceras reales: reutilizar el modelo `contract.contract`/`contract.line` de OCA (`/opt/odoo/19/oca/contract`), no un modelo propio desde cero -- confirmar `contract_type` ('sale' vs 'purchase', el valor por defecto es 'sale' y hay que fijarlo explícitamente si son contratos de proveedor), `journal_id`, y que `recurring_next_date` de cabecera es un compute `store=True, readonly=False` -- se puede escribir directamente encima sin líneas, el compute no lo pisa si no hay `contract_line_ids`.

## Notas transversales (aplican a todas las fases)

- **Actividad "Excepción"** (`mail.mail_activity_data_warning`, tipo nativo de Odoo, icono de aviso): se crea sobre cualquier registro con alguna anomalía -- descuadre de redondeo (aunque sea de 1 céntimo), analítica completada con valor por defecto, posición fiscal a revisar, dato de origen dudoso, cualquier caso "especial" que el usuario señale. **Regla explícita del usuario: crearla siempre que haya alguna diferencia, por pequeña que sea** -- no solo ante problemas sustantivos (ver memoria `maralva-excepcion-activity-rule`). Responsable = primer usuario de `account.group_account_manager` que no sea `base.user_admin` (si no hay ninguno más, se le asigna al propio admin); nota con el motivo y, si aplica, el volcado de los datos de origen relevantes.
- **Campos `company_dependent`** (`property_account_*`, `code` de cuenta, modos de pago...): siempre `.with_company(...)` al leer/escribir. Solo `account.account.code` tiene fallback especial a la compañía raíz -- **ningún otro campo lo tiene**, incluidos los de producto (ver fase 5). Si una empresa tiene sucursales, cualquier dato de este tipo que un script cree hay que escribirlo explícitamente para cada compañía relevante, no solo para la matriz.
- **Este checkout de `maralva-custom` es el `addons_path` real del servidor de desarrollo** -- cambiar de rama (`git checkout`) borra del disco los ficheros que no estén trackeados en la rama destino, y puede romper el servidor en caliente si tenía módulos cargados de la rama que se abandona. No cambiar de rama en este checkout sin comprobar antes qué hay instalado y en uso.
- **Los scripts de cada fase viven en el scratchpad de la sesión, no en el repo, hasta que el proceso esté maduro** -- esto significa que **un reinicio de máquina los borra** (ya ha pasado). Si algo se queda a medio migrar y hay que parar la sesión, valorar mover al menos los scripts ya validados al repo (aunque sea a una carpeta `samples`/`scripts` temporal) antes de un reinicio previsto, o documentar en `ESTADO.md` con suficiente detalle para reconstruirlos (como se hizo con "Contratos").
- **Todo bug real encontrado se corrige con carácter general**, no solo para el caso concreto que lo destapó (ej. el `!= 0` en vez de `> 0` al detectar rectificativas, el colapso a 4 dígitos en vez de 3) -- si un caso real rompe una regla, asumir que puede repetirse y arreglar la regla, no parchear el caso.

## Diferencias reales entre empresas (para no asumir que la próxima será igual)

| Aspecto | SERINGE | UTE NUNSYS | PROASUR |
|---|---|---|---|
| Estructura societaria | Compañía única | Compañía única | Matriz + 2 sucursales (Península/Canarias) |
| Analítica | No | No | Sí (Proyecto/Departamento/Sección + "OTROS") |
| Esquema del diario | `Cuenta`+`Debe`/`Haber`, cabecera fila 6 | `Cta. Cargo`/`Cta. Abono`+`Importe`, cabecera fila 1 | Igual que UTE NUNSYS |
| Señal de factura | Patrón Debe/Haber de 430/400/410 | Columna explícita `E/R` | Columna explícita `E/R/I` (con valor adicional "Informativa") |
| Regla de doble columna rellena | N/A (una sola columna) | Postea la que indique el flag `Cargo/Abono` | Postea siempre `Cta. Cargo` en facturas; ambas postean en Operaciones varias; al revés en intracomunitarias |
| Rango importado | Acotado (ene-jun 2026) | Completo (sin acotar, por no preguntarlo a tiempo) | Acotado (ene-jun 2026) |
| Fecha de factura vs fecha contable | Una sola columna `Fecha` | Una sola columna `Fecha` | Dos columnas distintas (`Fecha`/`F. Expedición`) |
| IGIC / Canarias | No | No | Sí, en la sucursal Canarias |

---

*Última actualización: 2026-08-26, tras cerrar (provisionalmente) la migración contable de PROASUR y la primera tanda de "Contratos". Mantener esta guía al día cuando aparezca un patrón nuevo en la próxima empresa -- es más valiosa si se seguirá corrigiendo que si se trata como un documento cerrado.*
