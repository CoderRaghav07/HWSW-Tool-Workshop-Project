from supabase import create_client

SUPABASE_URL = "https://nhlgbwbpwzdwdefwaurb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5obGdid2Jwd3pkd2RlZndhdXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU5ODg4NzgsImV4cCI6MjA5MTU2NDg3OH0.FzqLky6xrsPtzmjJ0VFoFoljoY2C1AjRrixtkAG3iN8"  # get this from dashboard

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("CONNECTION SUCCESSFUL!")