import rethinkdb as r
r.connect( "localhost", 28015).repl()
try:
    r.db_create("redactvideodotorg").run()
except:
    pass
try:
    r.db("redactvideodotorg").table_create("accounts_to_verify").run()
except:
    pass
try:
    r.db("redactvideodotorg").table_create("two_factor_codes").run()
except:
    pass
try:
    r.db("redactvideodotorg").table_create("settings").run()
except:
    pass
try:
    r.db("redactvideodotorg").table_create("sessions").run()
except:
    pass
try:
    r.db("redactvideodotorg").table_create("users").run()
except:
    pass