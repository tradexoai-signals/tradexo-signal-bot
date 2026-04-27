import os
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_KEY']
print(f"KEY: {SUPABASE_KEY[:30]}")
