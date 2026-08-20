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

# Configuración específica de cada hoja de origen: qué columna identifica el
# fichero como clientes o proveedores (para autodetectarlo por cabecera, sin
# que el usuario tenga que indicarlo), qué columna es el ID externo y qué
# columna usar como calle. En el export de Sage el mismo nombre de columna
# ('Dom. recibo') no significa lo mismo en clientes (ahí es un indicador, no
# texto) que en proveedores (ahí sí es la dirección).
SHEET_CONFIG = {
    'clientes': {'code_field': 'Cód. cliente', 'street_field': 'Domicilio', 'rank_field': 'customer_rank'},
    'proveedores': {'code_field': 'Cód. proveedor', 'street_field': 'Dom. recibo', 'rank_field': 'supplier_rank'},
}


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

        header = [str(cell).strip() if cell else '' for cell in rows[0]]
        source_model = self._detect_sage_source_model(header, rows)
        if not source_model or 'Razón social' not in header:
            batch.log_error(
                f"El fichero '{self.filename}' no tiene columnas de clientes ni de "
                f"proveedores de Sage reconocibles.")
            self.check_state = 'checked_error'
            return

        config = SHEET_CONFIG[source_model]
        code_field = config['code_field']
        has_error = False

        for row in rows[1:]:
            data = {header[i]: row[i] for i in range(len(header)) if header[i]}
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
        partner_model = self.env['res.partner']

        res_id = id_map.get_res_id(SOURCE_APP, source_model, code, 'res.partner')
        partner = partner_model.browse(res_id) if res_id else partner_model

        vat = self._sage_clean(data.get('CIF/DNI'))
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

        vals = self._build_sage_partner_vals(company, data, name, vat, config)

        if partner:
            partner.write(vals)
        else:
            partner = partner_model.create(vals)

        id_map.set_mapping(SOURCE_APP, source_model, code, 'res.partner', partner.id, batch=batch)

        if vals.get('state_id') is False and self._sage_clean(data.get('Provincia')):
            batch.log_warning(
                f"No se encontró la provincia '{data.get('Provincia')}' en España.",
                res_model='res.partner', source_id=code)

    def _build_sage_partner_vals(self, company, data, name, vat, config):
        vals = {
            'name': name,
            'company_id': company.id,
            config['rank_field']: 1,
        }
        if vat:
            vals['vat'] = vat
            vals['company_type'] = 'person' if INDIVIDUAL_VAT_RE.match(vat) else 'company'

        phone = self._sage_clean(data.get('Teléfono'))
        if phone:
            vals['phone'] = phone
        email = self._sage_clean(data.get('Correo Electrónico1'))
        if email:
            vals['email'] = email
        city = self._sage_clean(data.get('Municipio'))
        if city:
            vals['city'] = city
        street = self._sage_clean(data.get(config['street_field']))
        if street:
            vals['street'] = street
        zip_code = self._sage_clean(data.get('Cód. postal'))
        if zip_code:
            vals['zip'] = zip_code

        provincia = self._sage_clean(data.get('Provincia'))
        if provincia:
            spain = self.env.ref('base.es')
            # 'ilike' (contiene), no exacto: varias provincias de Odoo llevan
            # nombre doble, ej. "A Coruña (La Coruña)", "Bizkaia (Vizcaya)".
            state = self.env['res.country.state'].search([
                ('country_id', '=', spain.id),
                ('name', 'ilike', provincia),
            ], limit=1)
            vals['country_id'] = spain.id
            vals['state_id'] = state.id if state else False

        return vals

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
    def _detect_sage_source_model(header, rows):
        """Detecta si la hoja es de clientes o de proveedores mirando qué columna de
        código tiene realmente datos, no solo si la columna existe: Sage incluye en
        cada hoja una columna de referencia cruzada con el nombre de la otra ('Cód.
        cliente' también aparece, vacía, en el export de proveedores, y viceversa)."""
        best_model, best_count = None, 0
        for key, cfg in SHEET_CONFIG.items():
            code_field = cfg['code_field']
            if code_field not in header:
                continue
            idx = header.index(code_field)
            non_empty = sum(
                1 for row in rows[1:] if idx < len(row) and row[idx] not in (None, ''))
            if non_empty > best_count:
                best_model, best_count = key, non_empty
        return best_model

    @staticmethod
    def _sage_clean(value):
        if value in (None, ''):
            return False
        text = str(value).strip()
        return text or False
