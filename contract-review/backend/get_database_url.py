#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL', '')
project_ref = url.replace('https://', '').replace('.supabase.co', '')
db_password = os.getenv('SUPABASE_DB_PASSWORD', '')

if db_password:
    print(f'postgresql://postgres.{project_ref}:{db_password}@aws-0-us-west-1.pooler.supabase.com:6543/postgres')
else:
    print('ERROR: No SUPABASE_DB_PASSWORD in .env')
