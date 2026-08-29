{
    'name': 'Maralva - Flujo de aprobación de datos',
    'version': '19.0.1.0.0',
    'summary': 'Aprobación condicional por materias (ventas, compras, administración...) '
               'de campos de cualquier modelo, con notificación al responsable',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'category': 'Technical Settings',
    'depends': ['base', 'mail', 'base_automation', 'maralva_default_values'],
    'data': [
        'security/ir.model.access.csv',
        'views/maralva_approval_subject_views.xml',
        'views/maralva_approval_line_views.xml',
        'views/maralva_approval_related_doc_wizard_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
}
