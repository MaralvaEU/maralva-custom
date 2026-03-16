{
	'name': 'Conta Gdigital',
	'version': '18.0.1.0.0',
	'summary': 'Pack estándard de Contabilidad - GDigital',
	'category': 'Accounting',
	'author': 'Juan N. Martínez -GDigital',
	'website': 'https://gdigital.loc',
	'license': 'AGPL-3',
	'depends': [
			'account',      		# Módulo base de Odoo para contabilidad
			'account_edi',  		# Módulo para la generación de archivos electrónicos de contabilidad
			
	],
	'data': [
		'security/ir.model.access.csv',
		'data/res_company_data.xml',
	],
	'installable': True,
	'auto_install': False,
	'application': True,
	}