{
    'name': 'Maralva - Infraestructura de migración de datos',
    'version': '19.0.1.0.0',
    'summary': 'Módulo base común para la familia maralva_import_*: lotes de migración, mapeo de IDs externos y log de incidencias',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'category': 'Technical Settings',
    'depends': [
        'base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/maralva_migration_batch_views.xml',
    ],
    'installable': True,
    'application': False,
}
