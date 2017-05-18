from openerp import models, api, fields, SUPERUSER_ID
import pdb

import time
import os

import csv
import cStringIO
import threading
import logging 

from openerp.sql_db import db_connect

_logger = logging.getLogger( "CSV_Importer" )

class CSVManager(models.Model):
	"""
	This class will be used as an interface for developers to interact with this library .
	This is an Odoo model so developers can directly use their functions by creating the environment of it.
	
	_name = "csv.import.manager"

	"""
	
	_name = "csv.import.manager"
	
	def initialize(self, import_operation , import_data, validation_method, 
			caller_class, db_cols_count = 0, debug = None ):
		
		"""	
		This function will be used to initialize the library with required parameters.
		
		import_operation    : [Required] A meaningful name for import operation like as 'import_contact'
		import_data         : [Required] Encoded csv data with 'cp850' followed by 'base64' (default in Odoo)
		validation_method   : [Required] Must be a function in caller_class
		caller_class        : [Required] Odoo model name i.e. _name 
		db_cols_count       : [Optional] Possible number of columns in CSV File
		debug               : [Optional] True to print debug message , False to keep silent
		
		Example :-
		
		class Example(models.Model):
		
			_name = "importer.example"
		
			def method_one (self, decoded_data, task_id):
				
				with api.Environment.manage():
				
					self.env = api.Environment( db_connect( self.env.cr.dbname ).cursor(), self.env.uid, self.env.context )
					
					# ... Import Code ...
					index = 0
					# ... Import Code ...
					
					for row in decoded_data:
					
						index +=1 
						# ... Import Code ...
					
					return True
					
			Note:- We are using threading so validation function must be 
			indented within api.Environment.manage() and should reinitialize 
			environment with api.Environment() .
		"""
		
		self.import_operation = import_operation
		self.import_data = import_data
		self.db_cols_count = db_cols_count
		self.validation_method = validation_method
		self.caller_class = caller_class 
		self.debug = debug
		

	def start_import(self):
		"""
		This function will start the import process if not running already
		"""
		
		if CSVHolder.debug: _logger.info("[ Main ] : CSVManager.start_import called")
		
		caller_class_obj = self.env[self.caller_class] 
		
		if CSVHolder.debug: _logger.info("[ Main ] : Call validation method to verify its working")
		
		method_exist = False
		
		try:
			getattr(caller_class_obj, self.validation_method)
			method_exist = True
		
		except:
			if CSVHolder.debug: _logger.info("Either validation method does not exist or not accessible ")
		
		if not method_exist:
			return False
		
		csv_holder_obj = self.env['csv.import.holder']
		
		if CSVHolder.debug: _logger.info("[ Main ] : Calling CSVHolder.hold_csv with provided details ")
		
		csv_holder_obj.hold_csv(
			self.import_operation, self.import_data, 
			self.db_cols_count, self.caller_class, 
			self.validation_method, self.debug
		)
		
		return True
	
	
class CSVHolder(models.Model):
	
	"""
	This class is responsible to do actual import operation.
	
	_name = "csv.import.holder"
	
	"""
	
	_name = "csv.import.holder"
	
	debug = False
	val_table_name = "csv_importer_details"
	import_running = False
	
	def set_debug(self, debug_status):
		
		"""
		Set debug status to True or False
		
		"""
		
		CSVHolder.debug = debug_status
		
	def create_validation_table(self):
		"""
		This function will create validation table which will store the initialized data
		"""
		
		if CSVHolder.debug: _logger.info("[ CSVHolder ] : Got request to create csv_importer_details Table " )
		
		with api.Environment.manage():
			
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur = env.cr
			
			try:
				if not self.is_table_exist(CSVHolder.val_table_name):
					
					if CSVHolder.debug: _logger.info("[ CSVHolder ] : Preparing query ") 
					
					query = """
					CREATE TABLE %s 
					(	id serial primary key,
						import_req_id integer UNIQUE NOT NULL,
						import_col_count integer NOT NULL,
						import_class text NOT NULL,
						import_func text NOT NULL
					)
					""" % (CSVHolder.val_table_name,)
					
					if CSVHolder.debug: _logger.info("[ CSVHolder ] : Prepared, executing ... ") 
					cur.execute(query)
					cur.commit()
					
					if CSVHolder.debug: _logger.info("[ CSVHolder ] : Table created successfully ") 
			
			except Exception, e:
				if CSVHolder.debug: _logger.info("[ CSVHolder ] : Error in table creation : " + str(e)) 
				
			finally:
				if not cur.closed : cur.close()
					
	def store_validation_details(self, task_id , val_odoo_class, val_odoo_func, db_cols_count):
		
		"""
		This function will be used to store the initialization data
		"""
		
		if CSVHolder.debug: _logger.info("[ CSVHolder ] : Got request to insert new import task details in csv_importer_details table ") 
		
		with api.Environment.manage():
			
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur = env.cr
			
			try:
				
				if CSVHolder.debug: _logger.info("[ CSVHolder ] : Preparing insert query ...") 
				
				ins_query = """ INSERT INTO %s 
				(import_req_id, import_col_count, import_class, import_func) 
				VALUES (%s,%s,'%s','%s') 
				""" % (CSVHolder.val_table_name,task_id, db_cols_count, val_odoo_class, val_odoo_func)
				
				if CSVHolder.debug: _logger.info("[ CSVHolder ] : Prepared , executing  ") 
				
				cur.execute(ins_query)
				cur.commit()
				
				if CSVHolder.debug: _logger.info("[ CSVHolder ] : Executed  ") 
				
			except Exception, e:
				if CSVHolder.debug: _logger.info("[ CSVHolder ] : Error in task insertion : " + str(e)) 
				
			finally:
				if not cur.closed : cur.close()
	
	def hold_csv(self, import_operation = "", 
				csv_data = "", db_cols_count = "", 
				val_class = "", val_func = "", debug = False):
		
		"""
		This function will store the provided CSV to disk for temporary storage 
		and then will do the import process
		"""
		
		if CSVHolder.debug: _logger.info("[ CSVHolder ] : CSVHolder.hold_csv started ") 
		
		self.import_operation = import_operation
		self.csv_data = csv_data
		self.db_cols_count = db_cols_count
		self.val_class = val_class
		self.val_func =  val_func
		
		CSVHolder.debug = debug
		if (import_operation == "" or csv_data == "" ):
			if debug is None: 
				return False
			else:
				return { 
					"status" : False, 
					msg : "Required parameters have empty values"
				}
		
		self.table_name = 'buffer_' + import_operation
		
		if CSVHolder.debug: _logger.info("[ CSVHolder ] : Got request for new task : " + import_operation) 
		
		if CSVHolder.debug: _logger.info("[ CSVHolder ] : Check whether validation table exist or not") 
		
		if not self.is_table_exist(CSVHolder.val_table_name):
			self.create_validation_table()
		
		if CSVHolder.debug: _logger.info("[ CSVHolder ] : Requesting to write data on disk ") 
		# if CSVHolder.debug: _logger.info(threading.current_thread().name , "Table is not empty "
		threading.Thread( target=self.__write_csv_to_disk, name="[Thread : Write To Disk]" ).start()
		
		if CSVHolder.debug: _logger.info("Importer Running : "+ str(CSVHolder.import_running))
		
		if not CSVHolder.import_running:
			
			if CSVHolder.debug: _logger.info("[ CSVHolder ] : Calling importer simultaneously ")
			
			threading.Thread( target=self.start_data_import, name="[Thread : Start Import]" ).start()
	
	def is_buffer_table_match(self, task_details):
		
		"""
		This function will check current buffer table structure and the structure 
		needed for the task in hand for import purpose
		"""
		
		table_name = "buffer_" + task_details['import_operation']
		table_col_count = task_details['db_count']
		
		with api.Environment.manage():
			
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur = env.cr
			query = "SELECT count(*) FROM information_schema.columns WHERE table_name='%s'" %(table_name,)
			cur.execute(query)
			col_count = int(cur.fetchone()[0])
			
			if not cur.closed: cur.close()
			
			if CSVHolder.debug: _logger.info(" Table Have " + str(col_count - 2) + " columns vs " + str(table_col_count) + " count")
			if table_col_count == ( col_count - 2 ) :
				return True
			else:
				return False
		pass
	
	def remove_buffer_table(self, table_name = None):
		
		"""
		This function will clear the buffer table
		"""
		if CSVHolder.debug: _logger.info("Remove BUffer Table ") 
		with api.Environment.manage():
			
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur = env.cr
			table_name = self.table_name if table_name == None else table_name
			query = "DROP TABLE IF EXISTS " + table_name
			if CSVHolder.debug: _logger.info("Remove Query: " + query) 
			cur.execute("BEGIN")
			cur.execute("LOCK TABLE " + table_name + " IN EXCLUSIVE MODE NOWAIT")
			cur.execute(query)
			cur.commit()
			
			if not cur.closed: cur.close()
		if CSVHolder.debug: _logger.info("Done") 	
	
	@staticmethod
	def remove_csv_file(import_file_name):
		
		"""
		This function will take the file name and remove it.
		"""
		module_name = 'csv_importer'
		complete_path = __file__[:__file__.index(module_name)] + import_file_name 
		os.remove(complete_path)
		
	def start_data_import(self, external_task = None):
		
		"""
		This function will start import process.
		"""
		
		if CSVHolder.debug: _logger.info("[ CSVHolder ] : start_data_import started ... ")
		
		# Mark Import Thread as running 
		CSVHolder.import_running = True 
		
		val_db_count = 0
		
		with api.Environment.manage():
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur = env.cr
			
			join_time = time.time()
			
			if CSVHolder.debug: _logger.info("Join Time : " + str(join_time))
			while True:
				
				pending_imports = self.get_pending_import_request(external_task)
				
				if CSVHolder.debug: 
					print "\n\n[ CSVHolder ] : Here is pending task ", pending_imports
				
				for task in pending_imports:
					if external_task != None and external_task != task['id']:
						continue
						
					id = task['id']
					
					if CSVHolder.debug: _logger.info("[ CSVHolder ] : Picked task with Id : " + str(id))
					task_buff_table = "buffer_" + task['import_operation']
					
					if CSVHolder.debug: _logger.info("Buffer Table for this task is  : " + task_buff_table)
					
					is_buffer_table_exist = self.is_table_exist(task_buff_table)
					if not is_buffer_table_exist :
						
						if CSVHolder.debug: _logger.info("[ CSVHolder ] : But it does not exist, requesting to create it .... ") 
						self.create_buffer_table(task)
						if CSVHolder.debug: _logger.info("[ CSVHolder ] : Now Buffer Table Created " )
					
					else:
						if CSVHolder.debug: _logger.info("Buffer Table Exist ") 
						if CSVHolder.debug: _logger.info(" Before Task Value :" + str(task))
						if not self.is_buffer_table_match(task):
							if CSVHolder.debug: _logger.info(" But Structure did not match ") 
							self.remove_buffer_table(task_buff_table)
							if CSVHolder.debug: _logger.info(" After Task Value :" + str(task))
							self.create_buffer_table(task)
					
					# Clear Buffer Table
					if CSVHolder.debug: _logger.info("[ CSVHolder ] : Cleared Buffer Table to process : "+ str(id))
					self.remove_data_from_buffer_table(task_buff_table)
					
					# MOve this task data to buffer table 
					if CSVHolder.debug: _logger.info("[ CSVHolder ] : Asked to move data to buffer table "+ str(id))
					
					self.move_data_from_disk_to_buff(task)
					
					if CSVHolder.debug: _logger.info("[ CSVHolder ] : Moved CSV File Data TO Buffer Table "+ str(id))
					# Do Import Operation 
					buffer_table_empty = self.is_buffer_table_empty(task_buff_table)
					
					if CSVHolder.debug: _logger.info("[ CSVHolder ] : Is Buffer Table Empty : "+ str(buffer_table_empty)) 
						
					if not buffer_table_empty:
						
						if CSVHolder.debug: _logger.info("[ CSVHolder ] : Now started process: "+ str(id))
						
						data_from_db = []
						
						if CSVHolder.debug: _logger.info("[ CSVHolder ] : Fetching data from Buffer Table"+ str(id))
						
						cur.execute("SELECT * FROM " + task_buff_table)
						recs = cur.fetchall()
						col_to_ignore = ['id','is_imported']
						
						for item in recs:
							data_from_db.append(item[1:-1]) # Ignore 1st and last column value 
					
						if CSVHolder.debug: _logger.info("[ CSVHolder ] : We have now data "+ str(id))
						if CSVHolder.debug: _logger.info("[ CSVHolder ] : Calling Validation Function  "+ str(id))
						
						call_func = getattr(env[task['class']],task['func'])
							
						is_completed = call_func (data_from_db, id)
						
						if CSVHolder.debug: _logger.info("[ CSVHolder ] : Got response  "+ str(is_completed)) 
						
						if is_completed is True:
							
							if CSVHolder.debug: _logger.info("Finished with one import task "+ str(id))
							
							self.update_task_progress(id, 100)
							self.remove_data_from_buffer_table(task_buff_table);
							self.remove_csv_file(task['import_file_name'])
						
						else:
							if CSVHolder.debug: 
								print "[ CSVHolder ] : Got -ve response from user , we will keep ",
								print "the file to do import later ", id
								
					else:
						
						if CSVHolder.debug: _logger.info("Buffer Table is already empty, we can't do anything ")
				
				pending_imports = self.get_pending_import_request(external_task)
				
				complete_time = time.time()
				
				if external_task != None :
					break
				
				if len(pending_imports) == 0 and int(round(complete_time - join_time)) > 2:
					break
			if not cur.closed: cur.close()
			if CSVHolder.debug: _logger.info("Quite Time : "+ str(complete_time))
			CSVHolder.import_running = False
	
	def remove_data_from_buffer_table(self, buffer_table):
		"""
		It will remove data from buffer table
		"""
		if CSVHolder.debug: _logger.info("[ CSVHolder ] : Got request to clear buffer table: "+ str(buffer_table)) 
		
		with api.Environment.manage():
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur = env.cr
			
			try:
				if CSVHolder.debug: _logger.info("Obtaining Lock before Data Removal")
				cur.execute("BEGIN")
				cur.execute("LOCK TABLE " + buffer_table + " IN EXCLUSIVE MODE NOWAIT")
				if CSVHolder.debug: _logger.info("Lock Obtained")
				cur.execute("DELETE FROM "+ buffer_table)
				cur.commit()
			
			except Exception,e :
				cur.rollback()
				if CSVHolder.debug: _logger.info("Exception in clearing table " + str(e))
			
			finally:
				if not cur.closed: cur.close()
		
		if CSVHolder.debug: _logger.info("[ CSVHolder ] : Cleared : "+ str(buffer_table)) 
	
	def update_task_progress(self, task_id, progress_counter):
		
		"""
		It will update the import progress 
		
		Use:-
		
		class Example(models.Model):
		
			_name = "importer.example"
		
			def method_one (self, decoded_data, task_id):
				
				 with api.Environment.manage():
					self.env = api.Environment( db_connect( self.env.cr.dbname ).cursor(), self.env.uid, self.env.context )

					# ... Import Code ...
					index = 0
					csv_holder = self.env['csv.import.holder']
					# ... Import Code ...
					
					for row in decoded_data:
					
						index +=1 
						# ... Import Code ...
						csv_holder.update_task_progress(task_id, index )
						# ... Import Code ...
					
					return True
		"""
		
		progress_counter = 99 if progress_counter > 100 else progress_counter;
		with api.Environment.manage():
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur = env.cr
			
			finished_date = fields.Datetime.now() if progress_counter == 100 else None
			
			csv_import_logger_obj = env['csv.import.logger']
			
			search_data = csv_import_logger_obj.search([('id','=', task_id)])
			search_data.import_progress = progress_counter
			
			if finished_date is not None:
				search_data.import_fdate = finished_date
			
			cur.commit()
			
			if not cur.closed: cur.close()
	
	def move_data_from_disk_to_buff(self, task_details):
		"""
		This function will load data from hard disk to buffer table
		"""
		func_success = False
		
		task_id = task_details['id']
		import_file_name = task_details['import_file_name']
		import_operation = task_details['import_operation']
		db_cols_count = task_details['db_count']
		table_name = "buffer_" + import_operation
		
		module_name = 'csv_importer'
		
		if CSVHolder.debug: _logger.info("Got request to move file from disk to buffer : "+ str(task_id))  
		
		complete_path = __file__[:__file__.index(module_name)] + import_file_name
		
		if CSVHolder.debug: 
			print "File should be on location " , complete_path
			print "Fetched file location ", task_id
		
		file = open(complete_path, "r")
		decoded_data = self.read_encoded_csv_data(file.read())
		
		# pdb.set_trace()
		
		if CSVHolder.debug: _logger.info("Data Loaded from File to Memory"+ str(task_id))  
		
		if CSVHolder.debug: _logger.info(" Insert count  " +  str(db_cols_count))
		  
		
		
		insert_qry = "INSERT INTO %s "+ str(tuple(['col' + str(x) for x in range(1,db_cols_count+1)])).replace("'","")
		insert_qry += " values "  
		insert_qry = insert_qry % (table_name,)
		
		values = []
		
		for row in decoded_data :
			insert_qry += "(" + ("%s," * ( int(db_cols_count)) ).rstrip(",") + "), "
			values.extend(row[:db_cols_count])
		
		insert_qry = insert_qry.rstrip(", ")
		
		if CSVHolder.debug: _logger.info("Insert Query "+ str((values))) 
		
		if CSVHolder.debug: _logger.info("Preparing to insert data "+ str(task_id))  
		
		with api.Environment.manage():
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur =  env.cr
			
			try:
				if CSVHolder.debug: _logger.info("Trying to obtain lock on table " + table_name)
				
				cur.execute("BEGIN")
				cur.execute("LOCK TABLE " + table_name + " IN EXCLUSIVE MODE NOWAIT  ")
				
				if CSVHolder.debug: _logger.info("Success ")
				
				cur.execute(insert_qry, tuple(values))
				cur.commit()
				
				if CSVHolder.debug: _logger.info("Data Inserted for task "+ str(task_id))  
				
				qry = "SELECT count(*) FROM " + table_name
				
				cur.execute(qry)
				
				if CSVHolder.debug: _logger.info(str(cur.fetchone()[0]) + " records inserted" )
				
				func_success = True
			
			except Exception, e:
				
				func_success = False
				if not cur.closed : cur.rollback()
				if CSVHolder.debug: _logger.info("Failed " + str(e))
			
			finally:
				
				if not cur.closed : cur.close() 
			
			return func_success
		
	
	def get_pending_import_request(self, external_task = None):
		"""
		We can get the pending import list using that function 
		"""
		with api.Environment.manage():
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur = env.cr
			try:
				
				data = []
				
				sel_col = 'details.id "details_id",details.import_col_count "db_count"'
				sel_col += ', details.import_class "class", details.import_func "func"'
				sel_col += ', logger.id, logger.import_operation'
				sel_col += ', logger.import_progress'
				sel_col += ', logger.import_sdate, logger.import_fdate'
				sel_col += ', logger.import_file_name'
				from_tab = ' csv_import_logger logger, csv_importer_details details'
				if external_task is not None:
					where_cond = ' logger.id = details.import_req_id  AND logger.id = ' + str(external_task)
				else:
					where_cond = ' logger.id = details.import_req_id  AND logger.import_progress = 0 '
				
				query =  'SELECT ' + sel_col + " FROM " + from_tab + " WHERE "+ where_cond
				
				cur.execute(query)
				
				recs = cur.dictfetchall()
				
			finally:
				
				if not env.cr.closed: env.cr.close()
				
			return recs

	
	def is_buffer_table_empty(self, buffer_table = None):
		"""
		return 
			True  - if buffer table is empty 
			False - if buffer table is not empty
		"""
		with api.Environment.manage():
			
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			
			buffer_table = buffer_table if buffer_table != None else self.table_name;
			env.cr.execute("SELECT count(*) FROM " + buffer_table)
			res = int(env.cr.fetchone()[0])
			
			if not env.cr.closed: env.cr.close()
			
			if res == 0:
				return True
			
			else:
				return False

	def read_file_from_path(self, filename):
		"""
		This function will read the given file and return the content of the file 
		"""
		complete_path = __file__[:__file__.index("csv_importer")] + filename
		
		try:
			file = open(complete_path, "r")
			content = file.read()
		
		finally:
			file.close()
		
		return content
	
	def create_buffer_table(self, task_details):
		"""
		It is responsible to create the buffer table for particular task
		"""
		
		buffer_table_name = "buffer_" + task_details['import_operation']
		buffer_table_col_count = task_details['db_count']
		
		if CSVHolder.debug: _logger.info("Got request to create buffer table for Table %s having %d columns " % (buffer_table_name, buffer_table_col_count))
		if CSVHolder.debug: _logger.info(" Preparing create query ...")
		
		create_query = """CREATE TABLE %s (
			id serial primary key,
			%s
			is_imported integer default -1
			);
		"""
		
		if buffer_table_col_count == 0:
			if CSVHolder.debug: _logger.info(" Validation Table have 0 count")
			csv_rows = self.read_encoded_csv_data(self.read_file_from_path(task_details['import_file_name']))
			# pdb.set_trace()
			for row in csv_rows:
				new_db_cols_count = len(row)
				print row
				break
		
		else:
			new_db_cols_count = buffer_table_col_count
		# pdb.set_trace()
		
		task_details['db_count'] = new_db_cols_count
		
		if CSVHolder.debug: _logger.info(" New Table Count is : " + str(new_db_cols_count))
		
		cols = ""
		
		for i in range(1,new_db_cols_count + 1):
			cols += "col" + str(i) + " text,\n"
		
		create_query = create_query % (buffer_table_name, cols)
		
		_logger.info("Create Query : " + create_query)
		
		if CSVHolder.debug: _logger.info(" Prepared ")
		with api.Environment.manage():
            # As this function is in a new thread, I need to open a new cursor, because the old one may be closed
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur =  env.cr
			
			try:
				if CSVHolder.debug: _logger.info(" Executing prepared create query ...")
				
				cur.execute(create_query)
				cur.commit()
				
				cur.execute("UPDATE csv_importer_details SET import_col_count = " + str(new_db_cols_count) + " WHERE import_req_id = " + str(task_details['id']))
				cur.commit()
				
				if CSVHolder.debug: _logger.info(" Executed ")
			
			finally:
				if not cur.closed: cur.close()

	def is_table_exist(self, table_name = None):
		"""
		return 
		
		    True  - if table exist
		    False - if table does not exist
		"""
		with api.Environment.manage():
			
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur =  env.cr
			table_name = self.table_name if table_name is None else table_name
			
			try:
				cur.execute("select exists(select * from information_schema.tables where table_name=%s)", (table_name,))
				result = cur.fetchone()[0]
				# pdb.set_trace()
			finally:
				if not cur.closed: cur.close()
			
			return result

	def update_log(self, import_operation, file_name):
		"""
		It will write log for the import task
		"""
		if CSVHolder.debug: _logger.info("Function : update_log() start")
		
		result = []
		
		with api.Environment.manage():
			env = api.Environment(self.pool.cursor(), SUPERUSER_ID, self.env.context)
			cur =  env.cr
			
			try:
				
				logger_obj = env['csv.import.logger']
				result = logger_obj.write_log(import_operation, file_name)
			
			except Exception, e:
				if CSVHolder.debug: _logger.info("Error in log updation : " + str(e)) 
			
			finally:
				if not env.cr.closed : env.cr.close()
			
			if CSVHolder.debug: _logger.info("Function : update_log() end")
			return result
	
	def __write_csv_to_disk(self):
		"""
		It will be used to write csv data in a file 
		"""
		if CSVHolder.debug: _logger.info("Got request to write csv to disk")
		
		module_name = 'csv_importer'
		
		file_name = "file" + ('%.6f' % (time.time(), )).replace('.','_')
		upload_dir = "/uploads/"
		filename_for_db = module_name + upload_dir + file_name
		complete_name = __file__[:__file__.index(module_name)] + filename_for_db
		successfully_written = False
		
		try:
			
			file = open(complete_name,"w+")
			file.write(self.csv_data)
			successfully_written = True
		
		except :
			
			file.close()
			complete_name = False
		
		if(type(complete_name) == type("")):
			rec = self.update_log(self.import_operation, filename_for_db)
			
		self.store_validation_details(rec.id, self.val_class, self.val_func, self.db_cols_count)
	
	@staticmethod
	def read_encoded_csv_data(encoded_csv_data):
		"""
		It will be used to return the plain data from a encoded CSV 
		"""
		csv_file = cStringIO.StringIO( encoded_csv_data.decode( 'base64' ).decode( 'cp850' ).encode( 'utf8' ) )
		reader = csv.reader( csv_file, delimiter = '|', quotechar = '"' )
		return reader
	
class ImportLogger(models.Model):
	"""
	This class will be used to store the requested import task as a log..
	
	_name = "csv.import.logger"
	"""
	_name = "csv.import.logger"
	
	import_operation = fields.Char('Import Operation',  required=True)
	import_sdate = fields.Datetime('Requested Date', default = lambda self: fields.Datetime.now(), required = True)
	import_fdate = fields.Datetime('Finished Date', default = None)
	import_progress = fields.Integer('Progress ', default = 0)
	import_file_name = fields.Char('Import File Name ', default = None)
	
	def write_log(self, import_operation = '', import_file_name = ''):
		"""
		This function will write log for a task.
		"""
		if CSVHolder.debug: _logger.info("Got request to write new log ")
		
		with api.Environment.manage():
			
			self.env = api.Environment( db_connect( self.env.cr.dbname ).cursor(), self.env.uid, self.env.context )
			if CSVHolder.debug: _logger.info(" Finally came to write log")
			try:	
				data = {
					'import_operation' : import_operation,
					'import_file_name' : import_file_name
				}
				
				rec = self.create(data)
				self.env.cr.commit()
				if CSVHolder.debug: _logger.info(" Done write log" + str(rec))
			except Exception,e:
				if CSVHolder.debug: _logger.info(" Error in write_log() " + str(e)) 
			
			finally:
				if not self.env.cr.closed: self.env.cr.close()
			
			return rec
		
	@api.multi
	def name_get(self):
		"""
		It will be used to get the name for each import task in form view
		"""
		
		rec = super(ImportLogger, self).name_get()
		rec [0] = (rec[0][0], "Task "+ str(rec[0][0]))
		return rec	
	
	@api.one
	def start_import(self):
		"""
		User can manually start import process for a pending task using 
		that function 
		"""
		task_id = self.id
		
		csv_holder_obj = self.env['csv.import.holder']
		_logger.info(" Going to start import for task : " + str(task_id))
		csv_holder_obj.set_debug(True)
		is_done = csv_holder_obj.start_data_import(task_id)
		_logger.info(" Done import : " + str(task_id))
	
	@api.multi
	def unlink(self):
		"""
		It will be called when user will remove task(s) from UI.
		"""
		# pdb.set_trace()
		ids = [row.id for row in self]
		
		resp = super(ImportLogger, self).unlink()
		if isinstance(ids, (int, long)):
			ids = [ids]
			
		_logger.info(" Got request to delete : " + str(ids))
		self.remove_imported_records(ids)
		_logger.info(" Response from super : " + str(resp))
		
		return resp
		
	def remove_imported_records(self, ids):
		
		with api.Environment.manage():
			
			env = api.Environment( db_connect( self.env.cr.dbname ).cursor(), SUPERUSER_ID, self.env.context )
			
			try:	
				query = "DELETE FROM csv_importer_details WHERE import_req_id in (" + ','.join([str(id) for id in ids]) + ")"
				env.cr.execute(query)
				env.cr.commit()
			
			except Exception,e:
				if CSVHolder.debug: _logger.info(" Error in delete query " + str(e)) 
			
			finally:
				if not env.cr.closed: env.cr.close()
		