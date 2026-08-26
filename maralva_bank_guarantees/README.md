# Maralva - Gestión de avales bancarios

## Contenido

`maralva.bank.guarantee` (menú *Contabilidad > Avales > Avales bancarios*,
vistas de lista, formulario, actividades y pivote):
un registro por aval, con chatter completo (mensajes, seguidores, adjuntos,
envío de correo) vía `mail.thread`/`mail.activity.mixin`.

Campos principales:

- **Referencia** (`name`): numeración automática por secuencia (`AVAL/<año>/nnnn`).
- **Fecha** (`date`): fecha de alta del registro en Odoo.
- **Fecha concesión** (`date_concession`): fecha real en que la entidad concedió el aval.
- **Nº de póliza** (`policy_number`).
- **Empresa concesionaria del aval** (`issuer_id`, `res.partner`): la entidad (banco/asegurador) que otorga el aval.
- **Cuenta contable de gasto** / **Cuenta contable de tesorería** (`account_expense_id`/`account_treasury_id`, `account.account`), filtradas por la compañía del registro.
- **Comisión de apertura (%)** y **Comisión de liquidación (%)**: porcentajes, no importes fijos.
- **Importe mínimo comisión de apertura**: suelo en euros para la comisión de apertura.
- **Periodicidad liquidación comisión**: Mensual/Trimestral/Semestral/Anual.
- **Empresa avalada** (`guaranteed_partner_id`, `res.partner`): modelada como `Many2one` (una sola empresa por aval) a petición explícita del usuario -- **pendiente valorar si algún caso real necesitará varias empresas avaladas a la vez**, lo que requeriría pasar a `Many2many`.
- **Finalidad del aval** (`purpose`): texto libre, sin catálogo cerrado por ahora.
- **Importe inicial** (`initial_amount`).
- **Indefinido** (`is_indefinite`, booleano) + **Fecha de vencimiento** (`date_expiration`): si indefinido es verdadero, la fecha de vencimiento debe quedar vacía; si es falso, es obligatoria (validado con `@api.constrains`, y se limpia automáticamente al marcar "Indefinido" en el formulario).
- **Responsable** (`responsible_id`, `res.users`).
- **Observaciones** (`notes`).

## Estado y flujo

`state` (Borrador / Aprobado / Confirmado / Cancelado): campo de solo
lectura, no editable directamente -- solo cambia a través de los botones
del formulario:

- **Aprobar** (`action_approve`): Borrador → Aprobado.
- **Confirmar** (`action_confirm`): Aprobado → Confirmado.
- **Renovar** (`action_open_renew_wizard`): solo desde Confirmado, abre un
  asistente (`maralva.bank.guarantee.renew.wizard`) que pide la nueva fecha
  de vencimiento y, si se marca "Modificar condiciones", también nuevo
  importe, periodicidad de liquidación y comisión de liquidación. Al
  confirmar, actualiza el aval (se queda en Confirmado, sin estado propio
  "Renovado"), marca el booleano `renewed` a verdadero y deja constancia en
  el chatter del valor anterior y el nuevo de cada campo tocado.
- **Cancelar** (`action_cancel`): disponible desde cualquier estado salvo
  Cancelado.

## Aviso automático de vencimiento

`ir.cron` diario (`_cron_notify_expiring_guarantees`): busca los avales no
indefinidos cuya fecha de vencimiento cae exactamente 30 días después de
hoy, y crea una actividad de tipo "Todo" para el responsable de cada uno.

## Pendiente

- Confirmar si `guaranteed_partner_id` necesitará alguna vez varias empresas avaladas a la vez.
- Sin `ir.rule` de multicompañía todavía (solo el campo `company_id` + dominio de cuentas por compañía en la vista) -- añadir si se detecta necesidad real.
