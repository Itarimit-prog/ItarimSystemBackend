#!/usr/bin/env python3
"""Проверка подключения к Supabase"""

try:
    import psycopg2
    
    print("Подключение к Supabase...")
    conn = psycopg2.connect(
        dbname='postgres',
        user='postgres.bsngzqmnzdjnjhnliqma',
        password='CWyy4MdjgXhpdxo5',
        host='aws-1-eu-central-1.pooler.supabase.com',
        port='6543'
    )
    
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
