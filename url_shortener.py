from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import hashlib
import sqlite3
from cachetools import TTLCache
from datetime import timedelta

app = FastAPI()

# Initialize SQLite database
conn = sqlite3.connect('url_shortener.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY AUTOINCREMENT, long_url TEXT, short_url TEXT)')
conn.commit()

class URL(BaseModel):
    url: str

# Cache setup (in-memory cache with a TTL of 10 minutes)
cache = TTLCache(maxsize=1000, ttl=600)

def generate_short_url(long_url: str) -> str:
    # Generate a hash for the long URL
    hash_object = hashlib.sha256(long_url.encode())
    hex_dig = hash_object.hexdigest()[:8]  # Take first 8 characters of hexadecimal digest
    return hex_dig

@app.post('/shorten/')
async def shorten_url(url: URL):
    # Generate a short URL based on the long URL
    short_url = generate_short_url(url.url)

    # Store the URL mapping in the database
    cursor.execute('INSERT INTO urls (long_url, short_url) VALUES (?, ?)', (url.url, short_url))
    conn.commit()

    # Add to cache
    cache[short_url] = url.url

    return {'short_url': f'http://localhost:8000/{short_url}'}

@app.get('/{short_url}')
async def redirect_url(short_url: str):
    # Check cache first
    if short_url in cache:
        long_url = cache[short_url]
    else:
        # Retrieve the long URL from the database
        cursor.execute('SELECT long_url FROM urls WHERE short_url = ?', (short_url,))
        result = cursor.fetchone()

        if result:
            long_url = result[0]
            # Add to cache
            cache[short_url] = long_url
        else:
            raise HTTPException(status_code=404, detail="URL not found")

    return RedirectResponse(url=long_url)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
