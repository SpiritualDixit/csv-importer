# -*- coding: utf-8 -*-
{
    # App / Module Details
    'name': "CSV Importer",
    'summary': """ Import your CSV in background """,
    'description': """
    This module enables to import any file into background. 
    You need not to wait till the completion of import for any file.
    """,

    # Author Details 
    'author': "Deepak Dixit",
    'website': "https://github.com/SpiritualDixit",

    # App Technical Details
    'category': 'Tools',
    'version': '1.0.0',
    
    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
             'views/installer.xml',
             'views/csv_importer.xml',
             'views/csv_importer_force.xml',
    ],
    
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
}
