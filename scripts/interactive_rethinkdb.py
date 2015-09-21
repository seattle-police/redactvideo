# run with: ipython -i interactive_rethinkdb.py
import rethinkdb as r
conn = r.connect( "localhost", 28015).repl()
db = r.db('redactvideodotorg')
