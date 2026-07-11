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

def resolve_and_check(url: str) -> tuple[str, int, str]:
    """FAANG-level SSRF Protection: Resolve hostname and block private/local IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScrapingError("Security Policy Violation: URL scheme is not permitted.")
        
    hostname = parsed.hostname
    if not hostname:
        raise ScrapingError("Security Policy Violation: No hostname provided.")
        
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    
    try:
        # Resolve hostname to IPv4
        info = socket.getaddrinfo(hostname, port, socket.AF_INET, socket.SOCK_STREAM)
        ip = info[0][4][0]
    except Exception as e:
        raise ScrapingError(f"DNS resolution failed: {e}")
        
    ip_obj = ipaddress.ip_address(ip)
    
    # Block internal, private, loopback, and cloud metadata IPs
    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
        raise ScrapingError(f"Security Policy Violation: {ip} is a restricted IP.")
    if str(ip) == "169.254.169.254":
        raise ScrapingError(f"Security Policy Violation: {ip} is a restricted IP.")
            
    return ip, port, hostname

def _process_web_sync(url: str) -> List[Document]:
    import subprocess
    ip, port, hostname = resolve_and_check(url)
        
    retries = [1, 2, 4]
    content = b""
    
    cmd = [
        "curl", "-sL",
        "--max-time", "10",
        "--max-filesize", "5242880", # 5MB limit
        "--resolve", f"{hostname}:{port}:{ip}",
        url
    ]
    
    for delay in retries + [0]:
        try:
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode == 0:
                content = res.stdout
                break
            elif res.returncode == 63: # curl error 63 is filesize exceeded
                raise ScrapingError("Response exceeded max size of 5MB")
            else:
                last_error = f"curl error {res.returncode}"
        except Exception as e:
            if isinstance(e, ScrapingError):
                raise
            last_error = str(e)
            
        if delay == 0:
            raise ScrapingError(f"Failed to scrape {url} after retries: {last_error}")
        time.sleep(delay)
            
    if not content:
        raise ScrapingError(f"Failed to scrape {url}: no content returned")
        
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
