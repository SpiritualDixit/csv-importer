from openerp import models, api, fields
from openerp.sql_db import db_connect

class ContactManager(models.Model):
	
	_name = "contact.manager"
	
	name = fields.Char('Contact Name', required = True)
	address = fields.Char('Address')
	phone = fields.Char('Mobile')
	age = fields.Date('DOB')
	
class ContactImporter(models.Model):
	
	_name = "contact.importer"
	
	csv_data = fields.Binary( 'CSV File', default = '')
	
	@api.multi
	def do_import(self):
		
		csv_manager = self.env['csv.import.manager']
			
		csv_manager.initialize(
            import_operation = 'contact_import',
            import_data = self.csv_data, 
            db_cols_count = 5 , 
            validation_method = 'import_validator',
            caller_class = ContactImporter._name,
            debug = True
        )
		started = csv_manager.start_import()
		
	
	def import_validator(self, csv_import_data, task_id = None):
		
		with api.Environment.manage():
			new_cr = db_connect( self.env.cr.dbname ).cursor()
			self.env = api.Environment( new_cr, self.env.uid, self.env.context )
			total_records = 0
			
			obj_csv_manager = self.env['contact.manager']
			
			for row in csv_import_data:
				total_records += 1
				data = {
						'name': row[1],
						'age': row[2],
						'address': row[3],
						'phone':row[4]
					}
					
				obj_csv_manager.create(data)
				self.env.cr.commit()
			
			print str(total_records) + "  records inserted"
			
			if not self.env.cr.closed: self.env.cr.close()
			
			return True