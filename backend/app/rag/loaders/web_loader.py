import asyncio
import hashlib
import time
from datetime import datetime, timezone
from typing import List
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from app.core.exceptions import ScrapingError

def _process_web_sync(url: str) -> List[Document]:
    retries = [1, 2, 4]
    response = None
    
    for delay in retries + [0]:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            break
        except requests.RequestException as e:
            if delay == 0:
                raise ScrapingError(f"Failed to scrape {url} after retries: {e}")
            time.sleep(delay)
            
    if not response:
        raise ScrapingError(f"Failed to scrape {url}")
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove unwanted tags
    for tag in soup(['nav', 'footer', 'script', 'style']):
        tag.decompose()
        
    text = soup.get_text(separator='\n', strip=True)
    title = soup.title.string if soup.title else "Unknown"
    page_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    metadata = {
        "url": url,
        "title": title,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "web",
        "hash": page_hash
    }
    
    return [Document(page_content=text, metadata=metadata)]

async def load_web(url: str) -> List[Document]:
    """Asynchronously load a web page and extract text with exponential backoff."""
    return await asyncio.to_thread(_process_web_sync, url)
