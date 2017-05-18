from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class CSV_Import_Installer(models.Model):
    _name = "csv.import.installer"

    name = fields.Char('Name')
    
    @api.model
    def create(self, vals):
        
        _logger.info("Installing Module csv_importer ...") 
        return super(CSV_Import_Installer,self).create(vals)
    
    def remove_buffer_tables(self, table_name = None):
        
        with api.Environment.manage():
            env = api.Environment(self.pool.cursor(), self.env.uid, self.env.context)
            cur =  env.cr
            
            try:
                if table_name is None:
                    all_buffer_tables = ""
                    query = "select table_name from information_schema.tables where table_name like 'buffer_%'"
                    cur.execute(query)
                    all_buffer_tables = self.env.cr.fetchall()
                    all_buffer_tables = [t[0] for t in all_buffer_tables]
                    
                    for table in all_buffer_tables:
                        cur.execute("DROP TABLE IF EXISTS "+ table)
                else:
                    cur.execute("DROP TABLE IF EXISTS "+ table_name)
                
                cur.commit()
                
            except:
                cur.rollback()
                
            finally:
                if not cur.closed: cur.close()
    
    @api.multi
    def unlink(self):
        
        _logger.info("Uninstalling Module csv_importer ...")
        _logger.info("Removing created tables ...")
        
        self.remove_buffer_tables()
        self.remove_buffer_tables('csv_importer_details')
        
        _logger.info("Done")
        
        return super(CSV_Import_Installer,self).unlink()