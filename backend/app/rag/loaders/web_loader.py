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
        raise ScrapingError("DNS resolution failed. The host could not be found.")
        
    ip_obj = ipaddress.ip_address(ip)
    
    # Block internal, private, loopback, and cloud metadata IPs
    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
        raise ScrapingError(f"Security Policy Violation: {ip} is a restricted IP.")
    if str(ip) == "169.254.169.254":
        raise ScrapingError(f"Security Policy Violation: {ip} is a restricted IP.")
            
    return ip, port, hostname

def _process_web_sync(url: str) -> List[Document]:
    import subprocess
    import tempfile
    import urllib.parse
    
    current_url = url
    content = b""
    
    for hop in range(4):
        ip, port, hostname = resolve_and_check(current_url)
            
        retries = [1, 2, 4]
        success = False
        res = None
        
        with tempfile.NamedTemporaryFile() as header_file:
            cmd = [
                "curl", "-s",
                "--max-time", "10",
                "--max-filesize", "5242880", # 5MB limit
                "--resolve", f"{hostname}:{port}:{ip}",
                "-D", header_file.name,
                current_url
            ]
            
            for delay in retries + [0]:
                try:
                    res = subprocess.run(cmd, capture_output=True)
                    if res.returncode == 0:
                        success = True
                        break
                    elif res.returncode == 63: # filesize exceeded
                        raise ScrapingError("Response exceeded max size of 5MB")
                    else:
                        last_error = f"curl error {res.returncode}"
                except Exception as e:
                    if isinstance(e, ScrapingError):
                        raise
                    last_error = str(e)
                    
                if delay == 0:
                    raise ScrapingError(f"Failed to scrape {current_url} after retries.")
                time.sleep(delay)
                
            header_data = header_file.read().decode('utf-8', errors='ignore')
            
        if not success:
            raise ScrapingError(f"Failed to scrape {current_url}")
            
        location = None
        for line in header_data.split('\n'):
            line = line.strip()
            if line.lower().startswith("location:"):
                location = line[9:].strip()
                break
                
        first_line = header_data.split('\n')[0] if header_data else ""
        if any(code in first_line for code in [" 301 ", " 302 ", " 303 ", " 307 ", " 308 "]):
            if location:
                current_url = urllib.parse.urljoin(current_url, location)
                continue
                
        content = res.stdout
        break
    else:
        raise ScrapingError(f"Failed to scrape {url}: too many redirects")
        
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
