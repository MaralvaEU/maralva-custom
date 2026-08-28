import logging

from odoo import Command
from odoo.addons.account.models.chart_template import TAX_TAG_DELIMITER

_logger = logging.getLogger(__name__)

# 'es_canary_common' es la capa "delta" de Canarias dentro de l10n_es: cuentas,
# grupos e impuestos IGIC específicos, sin arrastrar un plan de cuentas
# completo (a diferencia de 'es_canary_full'/'es_canary_pymes', que la
# combinan con el plan mainland correspondiente). Es justo lo que hace falta
# para añadir IGIC sobre una compañía que ya tiene un plan PGC peninsular.
IGIC_TEMPLATE_CODE = 'es_canary_common'
IGIC_MODULE = 'l10n_es'
NEW_ACCOUNT_PREFIX = 'account_common_canary_'


def post_init_hook(env):
    """Al instalar, carga el IGIC en la compañía activa en ese momento.

    Los impuestos son un dato por compañía (a diferencia de las cuentas, que
    en v19 se comparten con la matriz) y una sucursal recién creada no tiene
    un ID de XML estable al que apuntar desde este módulo -- por eso, a
    falta de un asistente que permita elegir la sucursal destino, hay que
    tener seleccionada la compañía correcta (la sucursal de Canarias) en el
    selector de compañías antes de instalar este módulo. Evolucionar esto a
    un wizard con selección explícita de compañía queda pendiente.
    """
    company = env.company
    apply_igic_configuration(env, company)
    apply_igic_fiscal_positions(env, company)


def _prepare_igic_data(env):
    """Prepara (sin cargar) los datos de cuentas/grupos/impuestos IGIC del
    delta 'es_canary_common', con las mismas transformaciones (filtrado a lo
    genuinamente nuevo, prefijado de ids para no chocar con la matriz,
    sufijo " (IGIC)" en el nombre, mapeo de etiquetas) que necesita cualquier
    carga -- factorizado para que tanto `apply_igic_configuration` como
    `apply_igic_fiscal_positions` (que necesita también las referencias
    `fiscal_position_ids`/`original_tax_ids` de cada impuesto, que la
    primera descarta) parten del mismo resultado.

    Devuelve (new_acc_data, grp_data, tax_data, prefix) -- `tax_data` SÍ
    conserva `fiscal_position_ids`/`original_tax_ids` tal cual vienen del
    template; quien no las necesite (`apply_igic_configuration`, porque las
    posiciones fiscales todavía no existen) debe descartarlas antes de
    cargar.
    """
    ChartTemplate = env['account.chart.template']

    acc_data = ChartTemplate._parse_csv(IGIC_TEMPLATE_CODE, 'account.account', module=IGIC_MODULE)
    grp_data = ChartTemplate._parse_csv(IGIC_TEMPLATE_CODE, 'account.tax.group', module=IGIC_MODULE)
    tax_data = ChartTemplate._parse_csv(IGIC_TEMPLATE_CODE, 'account.tax', module=IGIC_MODULE)

    # Igual que ChartTemplate._deref_account_tags, pero sin pasar por
    # _get_chart_template_mapping (no incluye 'es_canary_common', que no es
    # seleccionable directamente como plantilla completa) -- el país fiscal
    # de las etiquetas del Modelo 420 es España en ambos casos.
    mapper = ChartTemplate._get_tag_mapper(env.ref('base.es').id)
    for tax_values in tax_data.values():
        for field_name in ('repartition_line_ids', 'invoice_repartition_line_ids', 'refund_repartition_line_ids'):
            for element in tax_values.get(field_name, []):
                match element:
                    case int() as command, _, {'tag_ids': str() as tags} as values if command in tuple(Command):
                        values['tag_ids'] = [Command.set(mapper(*tags.split(TAX_TAG_DELIMITER)))]

    # Solo las cuentas realmente nuevas de IGIC; el resto de cuentas
    # referenciadas desde las líneas de reparto (IVA general, retenciones...)
    # ya existen en la matriz y se resuelven solas por el fallback
    # compañía->matriz de ChartTemplate.ref().
    new_acc_data = {k: v for k, v in acc_data.items() if k.startswith(NEW_ACCOUNT_PREFIX)}

    # El delta 'es_canary_common' repite también grupos/impuestos genéricos
    # que ya existen en la matriz con el mismo nombre (retenciones, "Resta
    # Base"/DUA no ligado a IGIC...): crearlos de nuevo dispararía el check
    # de nombre de impuesto único. Nos quedamos solo con lo verdaderamente
    # específico de IGIC; las referencias a lo excluido (ej. el hijo
    # 'account_tax_template_p_iva_isub' de los impuestos de importación DUA)
    # se resuelven solas contra los de la matriz vía el fallback de ref().
    grp_data = {k: v for k, v in grp_data.items() if k.startswith('tax_group_igic_')}
    tax_data = {
        k: v for k, v in tax_data.items()
        if (v.get('tax_group_id') or '').startswith('tax_group_igic_')
    }

    # Varios ids de este delta (ej. 'account_tax_template_p_iva_isub', un
    # impuesto auxiliar de DUA) coinciden con ids ya existentes en la matriz
    # (misma plantilla es_full/es_common). Sin prefijo, ChartTemplate.ref()
    # los resolvería por su fallback compañía->matriz y acabaría escribiendo
    # encima del impuesto YA EXISTENTE de la matriz en vez de crear uno nuevo
    # para la sucursal. Mismo problema (y misma solución) que
    # _instantiate_foreign_taxes en el core.
    prefix = IGIC_TEMPLATE_CODE
    kept_tax_ids = set(tax_data.keys())
    for tax_values in tax_data.values():
        if tax_values.get('tax_group_id'):
            tax_values['tax_group_id'] = f"{prefix}_{tax_values['tax_group_id']}"
        if tax_values.get('amount_type') == 'group' and tax_values.get('children_tax_ids'):
            # Un hijo puede ser IGIC (creado aquí, hay que prefijarlo igual
            # que su propia clave) o un impuesto genérico ya existente en la
            # matriz (excluido más arriba, debe quedar tal cual para que
            # ref() lo resuelva por fallback).
            tax_values['children_tax_ids'] = ','.join(
                f"{prefix}_{child}" if child in kept_tax_ids else child
                for child in tax_values['children_tax_ids'].split(',')
            )
    # 'fiscal_position_ids'/'original_tax_ids' se dejan tal cual (claves de
    # plantilla SIN prefijar) -- `apply_igic_fiscal_positions` los resuelve
    # por nombre, no por xmlid, así que no le hace falta el prefijo.

    # Algunos impuestos IGIC comparten nombre corto genérico con un impuesto
    # de IVA peninsular ya existente en la matriz (ej. "0% G", con el mismo
    # type_tax_use/tax_scope) -- account.tax exige ese nombre único en toda
    # la jerarquía de compañías. Se distingue añadiendo "(IGIC)".
    for tax_values in tax_data.values():
        if tax_values.get('name'):
            tax_values['name'] = f"{tax_values['name']} (IGIC)"

    grp_data = {f"{prefix}_{k}": v for k, v in grp_data.items()}
    tax_data = {f"{prefix}_{k}": v for k, v in tax_data.items()}

    return new_acc_data, grp_data, tax_data, prefix


def apply_igic_configuration(env, company):
    """Crea en `company` los grupos e impuestos IGIC (Canarias).

    Reutiliza el parser de CSV de plantillas fiscales del core
    (`account.chart.template._parse_csv`) en vez de volcar los datos a mano,
    para heredar las correcciones que Odoo/OCA vayan aplicando a la
    plantilla oficial. No se usa `_load()`/`_get_chart_template_data()`
    directamente porque están pensados para instalar un plan de cuentas
    completo en una compañía nueva; aquí solo se añade el delta de Canarias
    sobre un plan (ej. PGC Completo peninsular) que la compañía ya tiene.
    """
    if env['account.tax'].search_count([
        ('company_id', '=', company.id),
        ('tax_group_id.name', 'ilike', 'IGIC'),
    ], limit=1):
        _logger.info("La compañía %s ya tiene impuestos IGIC, no se repite la carga.", company.display_name)
        return

    new_acc_data, grp_data, tax_data, prefix = _prepare_igic_data(env)

    # Las posiciones fiscales del template se cargan aparte (ver
    # `apply_igic_fiscal_positions`) -- si se cargaran aquí sin existir
    # todavía, las referencias fiscal_position_ids/original_tax_ids
    # quedarían colgando (igual que account.chart.template._instantiate_
    # foreign_taxes evita ese mismo problema al instanciar impuestos de
    # sucursales extranjeras).
    for tax_values in tax_data.values():
        tax_values.pop('fiscal_position_ids', None)
        tax_values.pop('original_tax_ids', None)

    data = {
        'account.account': new_acc_data,
        'account.tax.group': grp_data,
        'account.tax': tax_data,
    }

    env['account.chart.template'].with_context(
        default_company_id=company.id,
        allowed_company_ids=[company.id],
        tracking_disable=True,
        lang='en_US',
        chart_template_load=True,
    )._load_data(data)

    _logger.info("Cargados %s impuestos IGIC en %s.", len(tax_data), company.display_name)


def apply_igic_fiscal_positions(env, company):
    """Crea en `company` las posiciones fiscales de Canarias del template
    'es_canary_common' (Régimen Islas Canarias, Régimen Extracomunitario
    Islas Canarias, retenciones IRPF/arrendamiento Islas Canarias, Recargo
    de Equivalencia, ISP, Régimen Minoristas, DUA) y reconecta cada impuesto
    IGIC ya creado por `apply_igic_configuration` con las posiciones a las
    que pertenece según el template oficial.

    Comprobado contra PS CULTURAL (empresa Canarias real ya configurada en
    esta base) y contra los propios datos del template: casi todos los
    mapeos de 'Régimen Islas Canarias' son de un tipo IGIC a **sí mismo**
    (origen=destino), NO una traducción de tipos IVA peninsulares a IGIC --
    el template oficial no define esa traducción. Su función real es que
    Odoo la auto-aplique (`auto_apply`, restringida por provincia
    `state_ids`=Las Palmas/Sta Cruz de Tenerife) a los partners residentes
    en Canarias, para que tengan una posición fiscal coherente en vez de
    quedar sin ninguna.
    """
    if env['account.fiscal.position'].search_count([('company_id', '=', company.id)], limit=1):
        _logger.info("La compañía %s ya tiene posiciones fiscales, no se repite la carga.", company.display_name)
        return
    if not env['account.tax'].search_count([
        ('company_id', '=', company.id),
        ('tax_group_id.name', 'ilike', 'IGIC'),
    ], limit=1):
        raise ValueError(
            "No hay impuestos IGIC en %s todavía -- ejecuta primero apply_igic_configuration()."
            % company.display_name
        )

    ChartTemplate = env['account.chart.template']
    _new_acc_data, _grp_data, tax_data, prefix = _prepare_igic_data(env)

    fp_data_raw = ChartTemplate._parse_csv(IGIC_TEMPLATE_CODE, 'account.fiscal.position', module=IGIC_MODULE)
    fp_name_by_key = {}
    for fp_key, fp_values in fp_data_raw.items():
        # Nombre en castellano (el que trae el propio template, igual que
        # usa PS CULTURAL) en vez del inglés por defecto.
        if fp_values.get('name@es'):
            fp_values['name'] = fp_values.pop('name@es')
        fp_name_by_key[fp_key] = fp_values['name']
    fp_data = {f"{prefix}_{k}": v for k, v in fp_data_raw.items()}

    # Solo se carga 'account.fiscal.position' aquí -- recargar 'account.tax'
    # completo (con sus repartition_line_ids ya existentes) a través de
    # _load_data provoca un ValidationError ("... should each contain
    # exactly one line for the base"), porque _load_records_write escribe
    # las líneas de reparto encima de las que ya creó apply_igic_
    # configuration. En vez de eso, se enlaza cada impuesto YA EXISTENTE con
    # sus posiciones fiscales con un write() puntual solo de ese campo.
    ChartTemplate.with_context(
        default_company_id=company.id,
        allowed_company_ids=[company.id],
        tracking_disable=True,
        lang='en_US',
        chart_template_load=True,
    )._load_data({'account.fiscal.position': fp_data})

    fp_by_name = {
        fp.name: fp for fp in env['account.fiscal.position'].search([('company_id', '=', company.id)])
    }

    enlazados = 0
    sin_resolver = []
    for tax_values in tax_data.values():
        fp_keys = [k for k in (tax_values.get('fiscal_position_ids') or '').split(',') if k]
        if not fp_keys:
            continue
        fps = env['account.fiscal.position']
        for k in fp_keys:
            fp = fp_by_name.get(fp_name_by_key.get(k))
            if fp:
                fps |= fp

        tax = env['account.tax'].search([
            ('company_id', '=', company.id),
            ('name', '=', tax_values['name']),
            ('type_tax_use', '=', tax_values.get('type_tax_use', 'none')),
        ], limit=1)
        if not tax:
            sin_resolver.append(tax_values['name'])
            continue
        tax.fiscal_position_ids = fps
        enlazados += 1

    _logger.info(
        "Cargadas %s posiciones fiscales IGIC en %s, %s impuestos enlazados (%s sin resolver).",
        len(fp_data), company.display_name, enlazados, len(sin_resolver),
    )
    if sin_resolver:
        _logger.warning("Impuestos IGIC no encontrados al enlazar posiciones fiscales: %s", sin_resolver)

