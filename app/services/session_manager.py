"""CPCC session management service."""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.core.exceptions import CPCCSessionError, CPCCAuthenticationError, CPCCRequestError
from app.core.logging import LoggerMixin
from app.models.cpcc_responses import CPCCSession


class CPCCSessionManager(LoggerMixin):
    """Manages CPCC authentication sessions."""
    
    def __init__(self):
        self._current_session: Optional[CPCCSession] = None
        self._session_lock = asyncio.Lock()
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_http_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_http_client()
    
    async def _ensure_http_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.cpcc_timeout_seconds),
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                }
            )
    
    async def _close_http_client(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def get_valid_session(self) -> CPCCSession:
        """Get a valid CPCC session, creating one if necessary."""
        async with self._session_lock:
            # Check if current session is valid
            if self._current_session and self._current_session.is_valid:
                self.logger.debug("Using existing valid session")
                return self._current_session
            
            # Create new session
            self.logger.info("Creating new CPCC session")
            self._current_session = await self._initialize_session()
            return self._current_session
    
    async def _initialize_session(self) -> CPCCSession:
        """Initialize a new CPCC session."""
        await self._ensure_http_client()
        
        try:
            # Visit the course catalog page to get cookies and tokens
            url = f"{settings.cpcc_base_url}/Student/Courses"
            
            self.log_request("GET", url)
            start_time = datetime.utcnow()
            
            response = await self._http_client.get(url)
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            self.log_response(response.status_code, response_time)
            
            if response.status_code != 200:
                raise CPCCRequestError(
                    f"Failed to access CPCC course catalog: {response.status_code}",
                    status_code=response.status_code
                )
            
            # Extract cookies
            cookies = dict(response.cookies)
            if not cookies.get('.ColleagueSelfServiceAntiforgery'):
                raise CPCCAuthenticationError(
                    "Failed to obtain required authentication cookie"
                )
            
            # Parse HTML to extract CSRF token
            csrf_token = self._extract_csrf_token(response.text)
            if not csrf_token:
                raise CPCCAuthenticationError(
                    "Failed to extract CSRF token from response"
                )
            
            # Create session object
            session = CPCCSession(
                cookies=cookies,
                csrf_token=csrf_token,
                expires_at=datetime.utcnow() + timedelta(seconds=settings.session_ttl_seconds)
            )
            
            self.logger.info("Successfully initialized CPCC session")
            return session
            
        except httpx.RequestError as e:
            self.log_error(e, "session initialization")
            raise CPCCSessionError(f"Network error during session initialization: {str(e)}")
        except Exception as e:
            self.log_error(e, "session initialization")
            raise CPCCSessionError(f"Unexpected error during session initialization: {str(e)}")
    
    def _extract_csrf_token(self, html_content: str) -> Optional[str]:
        """Extract CSRF token from HTML content."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for the token in various possible locations
            
            # Method 1: Look for __RequestVerificationToken input field
            token_input = soup.find('input', {'name': '__RequestVerificationToken'})
            if token_input and token_input.get('value'):
                return token_input['value']
            
            # Method 2: Look for token in meta tag
            token_meta = soup.find('meta', {'name': '__RequestVerificationToken'})
            if token_meta and token_meta.get('content'):
                return token_meta['content']
            
            # Method 3: Look for token in script tags (sometimes embedded in JavaScript)
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    # Look for patterns like __RequestVerificationToken: "token_value"
                    token_match = re.search(
                        r'__RequestVerificationToken["\']?\s*:\s*["\']([^"\']+)["\']',
                        script.string
                    )
                    if token_match:
                        return token_match.group(1)
            
            # Method 4: Look for token in form data
            forms = soup.find_all('form')
            for form in forms:
                token_input = form.find('input', {'name': '__RequestVerificationToken'})
                if token_input and token_input.get('value'):
                    return token_input['value']
            
            self.logger.warning("Could not find CSRF token in HTML content")
            return None
            
        except Exception as e:
            self.log_error(e, "CSRF token extraction")
            return None
    
    async def refresh_session(self) -> CPCCSession:
        """Force refresh the current session."""
        async with self._session_lock:
            self.logger.info("Refreshing CPCC session")
            self._current_session = await self._initialize_session()
            return self._current_session
    
    async def validate_session(self, session: CPCCSession) -> bool:
        """Validate if a session is still working."""
        if not session.is_valid:
            return False
        
        try:
            await self._ensure_http_client()
            
            # Make a simple request to test the session
            url = f"{settings.cpcc_base_url}/Student/Courses"
            
            response = await self._http_client.get(
                url,
                cookies=session.cookies
            )
            
            # If we get redirected to login or get 401/403, session is invalid
            if response.status_code in [401, 403]:
                return False
            
            # Check if response contains login form (indicates session expired)
            if "login" in response.text.lower() or "sign in" in response.text.lower():
                return False
            
            return True
            
        except Exception as e:
            self.log_error(e, "session validation")
            return False
    
    async def get_authenticated_client(self) -> httpx.AsyncClient:
        """Get an HTTP client configured with current session."""
        session = await self.get_valid_session()
        await self._ensure_http_client()
        
        # Update client cookies
        self._http_client.cookies.update(session.cookies)
        
        # Add CSRF token to default headers
        self._http_client.headers.update({
            "__RequestVerificationToken": session.csrf_token,
            "__IsGuestUser": "true",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": settings.cpcc_base_url,
            "Referer": f"{settings.cpcc_base_url}/Student/Courses"
        })
        
        return self._http_client
    
    def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current session."""
        if not self._current_session:
            return None
        
        return {
            "created_at": self._current_session.created_at.isoformat(),
            "expires_at": self._current_session.expires_at.isoformat(),
            "is_valid": self._current_session.is_valid,
            "is_expired": self._current_session.is_expired,
            "has_cookies": bool(self._current_session.cookies),
            "has_csrf_token": bool(self._current_session.csrf_token)
        }


# Global session manager instance
session_manager = CPCCSessionManager()

# Alias for backward compatibility
SessionManager = CPCCSessionManager