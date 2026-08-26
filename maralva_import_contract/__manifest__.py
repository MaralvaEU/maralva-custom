{
    'name': 'Maralva - Importación de contratos',
    'version': '19.0.1.0.0',
    'summary': 'Migración de la cabecera de gastos recurrentes (contratos) detectados en el diario, con trazabilidad vía maralva_migration_base',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'account',
        'maralva_migration_base',
        'maralva_import_account',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
