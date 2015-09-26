import rethinkdb as r
r.connect( "localhost", 28015).repl()
try:
    r.db_create("redactvideodotorg").run()
except:
    pass
db = r.db("redactvideodotorg")
tables_needed = ["random_ids_for_users", "accounts_to_verify", "two_factor_codes", "settings", "sessions", "users", "track_status", "upperbody_detections"]
existing_tables = db.table_list().run()
tables_to_create = set(tables_needed) - set(existing_tables) # remove existing tables from what we need
for table in tables_to_create:
    db.table_create(table).run()