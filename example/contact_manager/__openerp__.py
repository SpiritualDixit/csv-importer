# -*- coding: utf-8 -*-
{
    # App / Module Details
    'name': "Contact Manager",
    'summary': """A simple contact manager""",
    'description': """ Contact Manager """,

    # Author Details 
    'author': "Deepak Dixit",
    'website': "https://github.com/SpiritualDixit",

    # App Technical Details
    'category': 'Tools',
    'version': '1.0.0',
    
    # any module necessary for this one to work correctly
    'depends': ['base','csv_importer'],

    # always loaded
    'data': [
             'views/contact_manager.xml',
    ],
    
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
}
