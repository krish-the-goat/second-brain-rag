import asyncio
import hashlib
import time
import socket
import ipaddress
from urllib.parse import urlparse
from datetime import datetime, timezone
from typing import List
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from app.core.exceptions import ScrapingError

def is_safe_url(url: str) -> bool:
    """FAANG-level SSRF Protection: Resolve hostname and block private/local IPs."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
            
        hostname = parsed.hostname
        if not hostname:
            return False
            
        # Resolve hostname to all IPs
        for info in socket.getaddrinfo(hostname, None):
            ip_addr = info[4][0]
            ip = ipaddress.ip_address(ip_addr)
            
            # Block internal, private, loopback, and cloud metadata IPs
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
                return False
            if str(ip) == "169.254.169.254":
                return False
                
        return True
    except Exception:
        return False

def _process_web_sync(url: str) -> List[Document]:
    if not is_safe_url(url):
        raise ScrapingError(f"Security Policy Violation: URL {url} is not permitted (SSRF protection).")
        
    retries = [1, 2, 4]
    response = None
    MAX_RESPONSE_BYTES = 5 * 1024 * 1024
    content = b""
    
    for delay in retries + [0]:
        try:
            response = requests.get(url, timeout=10, allow_redirects=False, stream=True)
            response.raise_for_status()
            
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_RESPONSE_BYTES:
                raise ScrapingError("Response too large")
                
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > MAX_RESPONSE_BYTES:
                    raise ScrapingError("Response exceeded max size")
            break
        except requests.RequestException as e:
            if delay == 0:
                raise ScrapingError(f"Failed to scrape {url} after retries: {e}")
            time.sleep(delay)
            
    if not response:
        raise ScrapingError(f"Failed to scrape {url}")
        
    soup = BeautifulSoup(content, 'html.parser')
    
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
