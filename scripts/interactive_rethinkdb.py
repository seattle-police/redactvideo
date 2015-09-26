# run with: ipython -i interactive_rethinkdb.py
import rethinkdb as r
conn = r.connect( "localhost", 28015).repl()
db = r.db('redactvideodotorg')

def get_setting(setting):
    try:
        return db.table('settings').get(setting).run(conn)['value']
    except:
        return ''    
