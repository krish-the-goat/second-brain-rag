import sqlite3
import re

conn = sqlite3.connect(':memory:')
conn.execute("CREATE VIRTUAL TABLE corpus USING fts5(text);")
conn.execute("INSERT INTO corpus (text) VALUES ('This is Acme Corp mission.');")
conn.commit()

query = "What is the core mission of Acme Corp?"
words = [w for w in re.split(r'\W+', query) if w]
safe_query = " OR ".join(words)

try:
    cursor = conn.execute("SELECT * FROM corpus WHERE corpus MATCH ?", (safe_query,))
    print("Success:", cursor.fetchall())
except Exception as e:
    print("Error:", e)
