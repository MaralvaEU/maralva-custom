{
    'name': 'Maralva - Campos obligatorios y valores por defecto',
    'version': '19.0.1.0.0',
    'summary': 'Reglas condicionales de campo obligatorio y valor por defecto, para cualquier modelo instalado',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'category': 'Technical Settings',
    'depends': [
        'base',
        'base_automation',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/maralva_default_rule_views.xml',
    ],
    'installable': True,
    'application': False,
}
