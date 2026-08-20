{
    'name': 'Maralva - Importación de contactos',
    'version': '19.0.1.0.0',
    'summary': 'Migración de contactos desde una aplicación externa, con trazabilidad vía maralva_migration_base',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'contacts',
        'maralva_migration_base',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
