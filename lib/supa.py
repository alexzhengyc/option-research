from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPA = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

def _get_table_ref(table):
    """
    Get a table reference, handling schema-prefixed table names.
    
    Args:
        table: Either "table_name" or "schema.table_name"
    
    Returns:
        Supabase table reference
    """
    if "." in table:
        schema, table_name = table.split(".", 1)
        return SUPA.schema(schema).table(table_name)
    return SUPA.table(table)

def upsert_rows(table, rows, on_conflict=None):
    # Supabase upsert automatically handles conflicts based on primary key/unique constraints
    # on_conflict parameter is kept for API compatibility but not used
    return _get_table_ref(table).upsert(rows).execute()

def insert_rows(table, rows):
    return _get_table_ref(table).insert(rows).execute()

def select_rows(table, filters): 
    q = _get_table_ref(table).select("*")
    for k,v in filters.items(): q = q.eq(k, v)
    return q.execute()

