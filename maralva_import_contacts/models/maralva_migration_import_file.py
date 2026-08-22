import base64
import io
import re

from odoo import fields, models
from odoo.exceptions import UserError

try:
    import openpyxl
except ImportError:
    openpyxl = None

SOURCE_APP = 'Sage'

# Un CIF de empresa española empieza por letra (A-W); un NIF (persona física)
# empieza por dígito y un NIE (extranjero) por X/Y/Z.
INDIVIDUAL_VAT_RE = re.compile(r'^[0-9XYZxyz]')

# Un NIF de persona física son siempre 8 dígitos + letra de control. Algunos
# NIF de Sage vienen tecleados sin el cero inicial (ej. '9355112T' en vez de
# '09355112T', confirmado real: la celda es texto, no un problema de Excel) —
# se reconstruye porque la longitud del NIF es un dato fijo, no una
# suposición, pero se deja aviso en el log para que el cliente lo revise.
NIF_RE = re.compile(r'^(\d+)([A-Za-z])$')

# Etiqueta de contacto a añadir según el tipo de hoja — mismo nombre que la
# columna 'Clien./Prov.' del plan de cuentas de Sage, para que el futuro
# módulo de contabilidad pueda reconciliar contra la misma etiqueta. Los
# proveedores no llevan una etiqueta fija: se distinguen por el prefijo de
# su 'Cód. contable' (ver SUPPLIER_ACCOUNT_PREFIX_TAG más abajo).
RANK_FIELD_TAG = {
    'customer_rank': 'Cliente',
}

# Etiqueta de proveedor según el prefijo de su 'Cód. contable': los de
# cuenta 400x (proveedores de compraventa) se etiquetan 'Proveedor'; los de
# cuenta 410x (acreedores por prestación de servicios) se etiquetan
# 'Prov. Servicios' -- a petición explícita del usuario, a tener en cuenta
# en toda futura importación de contactos. Un proveedor cuyo prefijo no sea
# ninguno de los dos (ej. AEAT, 475x) se queda con la etiqueta genérica
# 'Proveedor' por defecto.
SUPPLIER_ACCOUNT_PREFIX_TAG = {
    '400': 'Proveedor',
    '410': 'Prov. Servicios',
}

# Prefijos de 'Cód. contable' (Sage) que identifican la cuenta genérica a
# cobrar/a pagar del contacto. Igual que en el import del diario, una cuenta
# con desarrollo (ej. '430030000') se colapsa siempre a su genérica de 3
# dígitos ('430000000'), nunca a nivel de 4 dígitos -- son familias de
# cuenta distintas, no una sola con más o menos detalle.
RECEIVABLE_ACCOUNT_PREFIXES = ('430', '433')
PAYABLE_ACCOUNT_PREFIXES = ('400', '410')

# Posición fiscal "España Península" en proasurjnma -- se inyecta por
# defecto en todo contacto español que no traiga ya una posición fiscal
# fijada (ver ESTADO.md).
DEFAULT_FISCAL_POSITION_ID = 69


class MaralvaMigrationImportFile(models.Model):
    _inherit = 'maralva.migration.import.file'

    def action_import_sage_contacts(self):
        """Acción sobre uno o varios ficheros seleccionados en la lista: los importa como
        clientes/proveedores de Sage, detectando por sus cabeceras cuál es cuál."""
        if openpyxl is None:
            raise UserError("Falta la librería Python 'openpyxl' en el entorno de Odoo.")
        if not self:
            raise UserError("Selecciona al menos un fichero.")

        batch = self.env['maralva.migration.batch'].create({
            'name': 'Importación de contactos (Sage)',
            'source_app': SOURCE_APP,
            'company_id': self.env.company.id,
            'state': 'in_progress',
        })

        for record in self:
            record._import_sage_contacts_file(batch)

        batch.date_end = fields.Datetime.now()
        batch.state = 'error' if batch.log_ids.filtered(lambda log: log.level == 'error') else 'done'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'maralva.migration.batch',
            'res_id': batch.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _import_sage_contacts_file(self, batch):
        self.ensure_one()
        workbook = openpyxl.load_workbook(io.BytesIO(base64.b64decode(self.file)), data_only=True)
        rows = list(workbook.worksheets[0].iter_rows(values_only=True))
        if not rows:
            batch.log_warning(f"El fichero '{self.filename}' está vacío.")
            self.check_state = 'checked_error'
            return

        sheet_configs = self.env['maralva.migration.contacts.sheet.config'].search([])

        header = [str(cell).strip() if cell else '' for cell in rows[0]]
        config = self._detect_sage_sheet_config(header, rows, sheet_configs)
        if not config or 'Razón social' not in header:
            batch.log_error(
                f"El fichero '{self.filename}' no tiene columnas de clientes ni de "
                f"proveedores de Sage reconocibles.")
            self.check_state = 'checked_error'
            return

        source_model = config.source_model
        code_field = config.code_field
        has_error = False

        for row in rows[1:]:
            # Sage repite alguna cabecera dos veces en el mismo export (visto
            # real en 'Cód. contable' de PROVEEDORES.xlsx: aparece en dos
            # columnas, la segunda siempre vacía) -- si se construyera el
            # diccionario sin más, la columna vacía pisaría a la que sí trae
            # dato por venir después. Se queda con el primer valor no vacío
            # que aparezca para cada nombre de columna repetido.
            data = {}
            for i, key in enumerate(header):
                if not key:
                    continue
                value = row[i] if i < len(row) else None
                if key not in data or (data[key] in (None, '') and value not in (None, '')):
                    data[key] = value
            code = self._sage_clean(data.get(code_field))
            name = self._sage_clean(data.get('Razón social'))
            if not code or not name:
                batch.log_warning("Fila sin código o razón social, omitida.", res_model='res.partner')
                continue
            try:
                self._import_sage_contact_row(batch, data, source_model, config, code, name)
            except Exception as exc:  # noqa: BLE001 - una fila mal formada no debe abortar el lote
                has_error = True
                batch.log_error(
                    f"Error importando {source_model} {code}: {exc}",
                    res_model='res.partner', source_id=code)

        self.check_state = 'checked_error' if has_error else 'checked_ok'
        self._set_target_import_state('res.partner', 'error' if has_error else 'done')

    def _import_sage_contact_row(self, batch, data, source_model, config, code, name):
        company = self._resolve_sage_row_company(data)

        id_map = self.env['maralva.migration.id.map']
        # company_dependent (property_account_receivable_id/payable_id/
        # property_account_position_id): hay que leerlos y escribirlos en el
        # contexto de la compañía correcta, o se lee/escribe el valor de la
        # compañía activa del entorno, no el de esta fila.
        partner_model = self.env['res.partner'].with_company(company)

        res_id = id_map.get_res_id(SOURCE_APP, source_model, code, 'res.partner')
        partner = partner_model.browse(res_id) if res_id else partner_model

        plain_vat = self._normalize_sage_vat(batch, code, data.get('CIF/DNI'))
        # El prefijo internacional del NIF depende del país del partner, no es
        # un "ES" fijo -- hoy el país siempre se resuelve a España (ver más
        # abajo), así que en la práctica coincide, pero queda ligado al país
        # en vez de hardcodeado aparte. Sin el prefijo, no se puede fusionar
        # con partners ya existentes en formato internacional (ej. el AEAT
        # que traen los módulos OCA de Hacienda, "ESQ2826000H").
        country = self.env.ref('base.es')
        vat = f"{country.code}{plain_vat}" if plain_vat else False
        if not partner and vat:
            partner = partner_model.search([
                ('vat', '=', vat),
                ('company_id', 'in', [company.id, False]),
            ], limit=1)
            if partner:
                batch.log_info(
                    f"CIF {vat} ya existe como {partner.display_name} "
                    f"(id {partner.id}); se fusiona en vez de duplicar.",
                    res_model='res.partner', source_id=code)

        vals = self._build_sage_partner_vals(company, data, name, vat, plain_vat, country, config)

        if partner:
            partner.write(vals)
        else:
            partner = partner_model.create(vals)

        id_map.set_mapping(SOURCE_APP, source_model, code, 'res.partner', partner.id, batch=batch)

        self._apply_sage_partner_property_accounts(partner, company, data, batch, code)

        if vals.get('state_id') is False and self._sage_clean(data.get('Provincia')):
            batch.log_warning(
                f"No se encontró la provincia '{data.get('Provincia')}' en España.",
                res_model='res.partner', source_id=code)

    def _build_sage_partner_vals(self, company, data, name, vat, plain_vat, country, config):
        # Se escriben todos los campos que vienen en el origen, vacíos
        # incluidos (igual que el importador estándar de Odoo): si un campo
        # ya tenía valor y el fichero reenviado lo trae vacío, se vacía.
        vals = {
            'name': name,
            'company_id': company.id,
            config.rank_field: 1,
            'vat': vat,
            'country_id': country.id,
            'phone': self._sage_clean(data.get('Teléfono')),
            'email': self._sage_clean(data.get('Correo Electrónico1')),
            'city': self._sage_clean(data.get('Municipio')),
            'street': self._sage_clean(data.get(config.street_field)),
            'zip': self._sage_clean(data.get('Cód. postal')),
        }
        if plain_vat:
            # La detección persona/empresa mira el NIF/CIF sin el prefijo de
            # país -- con el prefijo puesto, el primer carácter sería siempre
            # la letra del país y la detección saldría siempre "empresa".
            vals['company_type'] = 'person' if INDIVIDUAL_VAT_RE.match(plain_vat) else 'company'

        tag_name = self._resolve_sage_partner_tag_name(config, data)
        if tag_name:
            category_ops = []
            if config.rank_field == 'supplier_rank':
                # 'Proveedor' y 'Prov. Servicios' son mutuamente excluyentes
                # (dependen del prefijo de cuenta, que puede cambiar entre
                # reimportaciones) -- hay que quitar la etiqueta que ya no
                # corresponda, no solo añadir la nueva.
                for other_tag in set(SUPPLIER_ACCOUNT_PREFIX_TAG.values()) - {tag_name}:
                    other_category = self.env['res.partner']._maralva_get_or_create_category(other_tag)
                    category_ops.append((3, other_category.id))
            category = self.env['res.partner']._maralva_get_or_create_category(tag_name)
            category_ops.append((4, category.id))
            vals['category_id'] = category_ops

        provincia = self._sage_clean(data.get('Provincia'))
        state = False
        if provincia:
            # 'ilike' (contiene), no exacto: varias provincias de Odoo llevan
            # nombre doble, ej. "A Coruña (La Coruña)", "Bizkaia (Vizcaya)".
            state = self.env['res.country.state'].search([
                ('country_id', '=', country.id),
                ('name', 'ilike', provincia),
            ], limit=1)
        vals['state_id'] = state.id if state else False

        return vals

    def _resolve_sage_partner_tag_name(self, config, data):
        if config.rank_field == 'supplier_rank':
            account_code = self._sage_clean(data.get('Cód. contable'))
            prefix = account_code[:3] if account_code else None
            return SUPPLIER_ACCOUNT_PREFIX_TAG.get(prefix, 'Proveedor')
        return RANK_FIELD_TAG.get(config.rank_field)

    def _apply_sage_partner_property_accounts(self, partner, company, data, batch, code):
        """Fija la cuenta a cobrar/a pagar (colapsada a la genérica de 3
        dígitos) y, por defecto, la posición fiscal 'España Península' de
        todo contacto español que no traiga ya una -- ver comentario de las
        constantes RECEIVABLE_/PAYABLE_ACCOUNT_PREFIXES y
        DEFAULT_FISCAL_POSITION_ID más arriba."""
        account_code = self._sage_clean(data.get('Cód. contable'))
        if account_code:
            if account_code.startswith(RECEIVABLE_ACCOUNT_PREFIXES):
                target_field = 'property_account_receivable_id'
            elif account_code.startswith(PAYABLE_ACCOUNT_PREFIXES):
                target_field = 'property_account_payable_id'
            else:
                target_field = None
            if target_field:
                generic_code = account_code[:3] + '0' * 6
                account = self.env['account.account'].with_company(company).search([
                    ('company_ids', 'in', company.id),
                ]).filtered(lambda a: a.code == generic_code)
                if account:
                    partner[target_field] = account[0].id
                else:
                    batch.log_warning(
                        f"No existe en Odoo la cuenta {generic_code} (compañía "
                        f"{company.display_name}) para fijar {target_field} de "
                        f"{partner.display_name}.",
                        res_model='res.partner', source_id=code)

        if partner.country_id.code == 'ES' and not partner.property_account_position_id:
            partner.property_account_position_id = DEFAULT_FISCAL_POSITION_ID

    def _resolve_sage_row_company(self, data):
        self.ensure_one()
        if self.company_mode == 'single':
            return self.company_id

        source_code = self._sage_clean(data.get('Cód. empresa'))
        if not source_code:
            raise ValueError(
                "fichero multicompañía sin 'Cód. empresa' en la fila; no se puede "
                "saber a qué compañía de Odoo pertenece.")
        mapping = self.company_line_ids.filtered(
            lambda line: line.source_company_code == source_code)
        if not mapping:
            raise ValueError(
                f"no hay ninguna compañía de Odoo relacionada con el código de "
                f"compañía de origen '{source_code}' (revisa la pestaña 'Relación "
                f"de compañías' del fichero).")
        return mapping.company_id

    def _set_target_import_state(self, res_model, import_state):
        self.ensure_one()
        line = self.target_line_ids.filtered(lambda l: l.res_model == res_model)
        if line:
            line.import_state = import_state
        else:
            self.env['maralva.migration.import.file.target'].create({
                'file_id': self.id,
                'res_model': res_model,
                'import_state': import_state,
            })

    @staticmethod
    def _detect_sage_sheet_config(header, rows, sheet_configs):
        """Detecta qué configuración de hoja (clientes/proveedores, ver
        maralva.migration.contacts.sheet.config) corresponde al fichero,
        mirando qué columna de ID externo tiene realmente datos, no solo si
        la columna existe: Sage incluye en cada hoja una columna de
        referencia cruzada con el nombre de la otra ('Cód. cliente' también
        aparece, vacía, en el export de proveedores, y viceversa)."""
        best_config, best_count = None, 0
        for config in sheet_configs:
            code_field = config.code_field
            if code_field not in header:
                continue
            idx = header.index(code_field)
            non_empty = sum(
                1 for row in rows[1:] if idx < len(row) and row[idx] not in (None, ''))
            if non_empty > best_count:
                best_config, best_count = config, non_empty
        return best_config

    @staticmethod
    def _sage_clean(value):
        if value in (None, ''):
            return False
        text = str(value).strip()
        return text or False

    def _normalize_sage_vat(self, batch, code, value):
        text = self._sage_clean(value)
        if not text:
            return text
        match = NIF_RE.match(text)
        if match:
            digits, letter = match.groups()
            if len(digits) < 8:
                corrected = f"{digits.zfill(8)}{letter.upper()}"
                batch.log_warning(
                    f"NIF '{text}' corregido a '{corrected}' (le faltaba el cero "
                    f"inicial: un NIF español tiene siempre 8 dígitos) — revisar el "
                    f"dato de origen.",
                    res_model='res.partner', source_id=code)
                text = corrected
        return text
