{
    'name': 'Maralva - Importación de contactos',
    'version': '19.0.1.0.0',
    'summary': 'Migración de contactos desde una aplicación externa, con trazabilidad vía maralva_migration_base',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'contacts',
        'account',
        'maralva_migration_base',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/maralva_migration_import_group_data.xml',
    ],
    'installable': True,
    'application': False,
}
