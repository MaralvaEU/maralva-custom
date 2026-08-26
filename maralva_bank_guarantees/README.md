# Maralva - Gestión de avales bancarios

## Contenido

`maralva.bank.guarantee` (menú *Facturación/Contabilidad > Avales > Avales
bancarios* -- "Avales" como sección propia dentro de la app de Contabilidad,
al mismo nivel que "Contabilidad"/"Informes"/etc., igual que hace el
módulo OCA `account_loan` con "Préstamos" (`parent="account.menu_finance_entries"`);
vistas de lista, formulario, actividades y pivote):
un registro por aval, con chatter completo (mensajes, seguidores, adjuntos,
envío de correo) vía `mail.thread`/`mail.activity.mixin`.

Campos principales:

- **Referencia** (`name`): numeración automática por secuencia (`AVAL/<año>/nnnn`).
- **Fecha** (`date`): fecha de alta del registro en Odoo.
- **Fecha concesión** (`date_concession`): fecha real en que la entidad concedió el aval.
- **Nº de póliza** (`policy_number`).
- **Empresa concesionaria del aval** (`issuer_id`, `res.partner`): la entidad (banco/asegurador) que otorga el aval.
- **Cuenta contable de gasto** (`account_expense_id`, `account.account`) y **Diario de tesorería** (`treasury_journal_id`, `account.journal`, solo diarios de tipo banco): los asientos de comisión se contabilizan al debe de la cuenta de gasto contra la cuenta por defecto de este diario, no contra una cuenta de tesorería elegida a mano.
- **Comisión de apertura (%)** y **Comisión de liquidación (%)**: porcentajes sobre el importe inicial del aval, no importes fijos.
- **Importe mínimo comisión de apertura**: suelo en euros, solo aplica a la comisión de apertura (`max(importe_inicial × % , mínimo)`).
- **Periodicidad liquidación comisión**: Mensual/Trimestral/Semestral/Anual.
- **Empresa avalada** (`guaranteed_partner_id`, `res.partner`): modelada como `Many2one` (una sola empresa por aval) a petición explícita del usuario -- **pendiente valorar si algún caso real necesitará varias empresas avaladas a la vez**, lo que requeriría pasar a `Many2many`.
- **Finalidad del aval** (`purpose`): texto libre, sin catálogo cerrado por ahora.
- **Importe inicial** (`initial_amount`): base de cálculo de ambas comisiones; tras una renovación con condiciones modificadas, es el importe vigente el que se usa (no el original).
- **Indefinido** (`is_indefinite`, booleano) + **Fecha de vencimiento** (`date_expiration`): si indefinido es verdadero, la fecha de vencimiento debe quedar vacía; si es falso, es obligatoria (validado con `@api.constrains`, y se limpia automáticamente al marcar "Indefinido" en el formulario).
- **Responsable** (`responsible_id`, `res.users`).
- **Contabilizar liquidaciones automáticamente** (`auto_post_settlements`, booleano): por defecto apagado (cada liquidación se contabiliza a mano con su botón); si se activa, el cron diario la contabiliza sola en su fecha.
- **Observaciones** (`notes`).

## Estado y flujo

`state` (Borrador / Aprobado / Confirmado / Cancelado): campo de solo
lectura, no editable directamente -- solo cambia a través de los botones
del formulario:

- **Aprobar** (`action_approve`): Borrador → Aprobado.
- **Confirmar** (`action_confirm`): Aprobado → Confirmado. Además:
  1. si hay comisión de apertura (% y/o mínimo > 0), contabiliza un asiento
     en el diario de tesorería: debe la cuenta de gasto, haber la cuenta
     por defecto del diario, por `max(importe_inicial × %, mínimo)`.
  2. genera la tabla de previsión de liquidaciones (`settlement_ids`,
     modelo `maralva.bank.guarantee.settlement`) desde la fecha de
     concesión, una línea por periodo según la periodicidad, hasta la
     fecha de vencimiento (o, si el aval es indefinido, hasta dentro de un
     año -- ver más abajo). Cada línea trae el importe calculado
     (`importe_inicial × comisión de liquidación %`), **editable** antes
     de contabilizarla.
- **Renovar** (`action_open_renew_wizard`): solo desde Confirmado, abre un
  asistente (`maralva.bank.guarantee.renew.wizard`) que pide la nueva fecha
  de vencimiento y, si se marca "Modificar condiciones", también nuevo
  importe, periodicidad de liquidación y comisión de liquidación. También
  pregunta si la renovación **lleva comisión de apertura** propia: si se
  marca, pide su % (y mínimo), la contabiliza igual que al confirmar (con
  la referencia "... por renovación ...") y **además actualiza los campos
  de comisión de apertura del aval** (para que una renovación futura con
  las mismas condiciones no haya que repetirlo). Al confirmar el asistente:
  actualiza el aval (se queda en Confirmado, sin estado propio "Renovado"),
  marca el booleano `renewed` a verdadero, **cancela las liquidaciones
  todavía pendientes** (no contabilizadas) y regenera la tabla de
  previsión para el nuevo periodo, y registra todo en el histórico de
  renovaciones (ver más abajo) además de en el chatter.
- **Cancelar** (`action_cancel`): disponible desde cualquier estado salvo
  Cancelado. Cancela también las liquidaciones pendientes que quedaran.

## Previsión de liquidaciones (`maralva.bank.guarantee.settlement`)

Una línea por periodo previsto (Pendiente / Contabilizada / Cancelada).
Cada línea pendiente tiene un botón **Contabilizar**
(`action_post_settlement`) que genera el mismo tipo de asiento que la
comisión de apertura (debe cuenta de gasto, haber cuenta del diario de
tesorería), pero con la referencia "Comisión de liquidación aval ... -
vencimiento ..." en vez de "... de apertura ...", para poder distinguirlas
en el diario. El importe de la línea es editable mientras esté pendiente,
por si hay que ajustarlo respecto al previsto antes de contabilizar.

**Avales indefinidos**: como no hay fecha de vencimiento donde detener la
generación, se crea solo la previsión del **próximo año** al confirmar; un
`ir.cron` diario (`_cron_extend_indefinite_settlement_forecasts`) añade
periódicamente la siguiente liquidación para mantener siempre ese horizonte
de un año por delante, sin necesidad de intervención manual.

Un segundo `ir.cron` diario (`_cron_post_pending_settlements`) contabiliza
automáticamente las liquidaciones pendientes de la fecha de hoy o anterior,
pero **solo** en los avales con `auto_post_settlements` activado -- por
defecto esto no ocurre, hay que pulsar "Contabilizar" a mano.

## Histórico de renovaciones (`maralva.bank.guarantee.renewal`)

Una línea por cada renovación confirmada (no solo un mensaje de chatter):
fecha, vencimiento anterior/nuevo, si se modificaron condiciones y
cuáles (importe, periodicidad, comisión de liquidación, antes/después), si
llevó comisión de apertura y con qué %/mínimo/importe contabilizado, y el
asiento contable generado si lo hubo. Se ve como pestaña de solo lectura
en el propio formulario del aval.

## Aviso automático de vencimiento

`ir.cron` diario (`_cron_notify_expiring_guarantees`): busca los avales no
indefinidos cuya fecha de vencimiento cae exactamente 30 días después de
hoy, y crea una actividad de tipo "Todo" para el responsable de cada uno.

## Pendiente

- Confirmar si `guaranteed_partner_id` necesitará alguna vez varias empresas avaladas a la vez.
- Sin `ir.rule` de multicompañía todavía (solo el campo `company_id` + dominio de cuentas/diarios por compañía en la vista) -- añadir si se detecta necesidad real.
