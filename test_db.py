#!/usr/bin/env python3
"""Проверка подключения к Supabase"""

try:
    import os
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()

    print("Подключение к Supabase...")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    print("✅ Connected!")
    
    # Проверим версию
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"PostgreSQL version: {version[0][:50]}...")
    cur.close()
    
    conn.close()
    print("✅ Connection closed")
    
except Exception as e:
    print(f"❌ Error: {e}")
