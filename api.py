import aiohttp
import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from aiohttp import ClientTimeout

_LOGGER = logging.getLogger(__name__)


class EnviApiError(Exception):
    """Base exception for Envi API errors."""
    pass


class EnviAuthenticationError(EnviApiError):
    """Raised when authentication fails."""
    pass


class EnviDeviceError(EnviApiError):
    """Raised when device operations fail."""
    pass


class EnviTokenError(EnviApiError):
    """Raised when JWT token is invalid or expired."""
    pass


class EnviApiClient:
    """API client for Envi Smart Heater cloud service with JWT authentication."""
    
    def __init__(self, session: aiohttp.ClientSession, username: str, password: str):
        self.session = session
        self.username = username
        self.password = password
        self.base_url = "https://app-apis.enviliving.com/apis/v1"
        self.token: str | None = None
        self.token_expires: datetime | None = None
        self.token_issued: datetime | None = None
        self._refresh_lock = asyncio.Lock()
        self.timeout = ClientTimeout(total=15)
        # Buffer time before expiry to trigger refresh (5 minutes)
        self._refresh_buffer = timedelta(minutes=5)

    @property
    def is_token_valid(self) -> bool:
        """Check if current token is valid and not about to expire."""
        if not self.token or not self.token_expires:
            return False
        return datetime.now(timezone.utc) < self.token_expires - self._refresh_buffer

    @property
    def is_token_expired(self) -> bool:
        """Check if token has fully expired (not just within buffer)."""
        if not self.token or not self.token_expires:
            return True
        return datetime.now(timezone.utc) >= self.token_expires

    async def authenticate(self) -> None:
        """Authenticate with Envi cloud and obtain JWT token."""
        # Generate fresh device_id for each login to avoid conflicts
        fresh_device_id = f"ha_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"

        payload = {
            "username": self.username,
            "password": self.password,
            "login_type": 1,
            "device_id": fresh_device_id,
            "device_type": "homeassistant",
        }

        url = f"{self.base_url}/auth/login"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "HomeAssistant-Envi/1.1",
        }

        _LOGGER.debug("Envi login attempt – device_id: %s", fresh_device_id)

        try:
            async with self.session.post(
                url, json=payload, headers=headers, timeout=self.timeout
            ) as resp:
                resp_text = await resp.text()
                _LOGGER.debug(
                    "Envi login response: %s – %s", 
                    resp.status, 
                    resp_text[:500] if len(resp_text) > 500 else resp_text
                )

                if resp.status != 200:
                    raise EnviAuthenticationError(
                        f"Login failed with HTTP status {resp.status}"
                    )

                data = json.loads(resp_text)
                
                if data.get("status") != "success":
                    error_msg = data.get("msg", data.get("message", "Unknown error"))
                    raise EnviAuthenticationError(f"Envi rejected login: {error_msg}")

                # Extract token from response
                token_data = data.get("data", {})
                new_token = token_data.get("token")
                
                if not new_token:
                    raise EnviAuthenticationError("No token in login response")

                # Validate and parse JWT
                self._set_token(new_token)
                
                _LOGGER.info(
                    "Envi login successful – token valid until %s (issued: %s)",
                    self.token_expires.strftime("%Y-%m-%d %H:%M:%S UTC") if self.token_expires else "unknown",
                    self.token_issued.strftime("%Y-%m-%d %H:%M:%S UTC") if self.token_issued else "unknown",
                )

        except EnviAuthenticationError:
            # Re-raise our own exceptions without wrapping
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during Envi authentication: %s", err)
            raise EnviAuthenticationError(f"Network error: {err}") from err
        except json.JSONDecodeError as err:
            _LOGGER.error("Invalid JSON in Envi login response: %s", err)
            raise EnviAuthenticationError("Invalid response from Envi API") from err
        except Exception as err:
            _LOGGER.error("Unexpected error during Envi authentication: %s", err, exc_info=True)
            raise EnviAuthenticationError(f"Authentication failed: {err}") from err

    def _set_token(self, token: str) -> None:
        """Validate and set the JWT token."""
        # Validate JWT structure (header.payload.signature)
        parts = token.split(".")
        if len(parts) != 3:
            raise EnviTokenError(f"Invalid JWT structure: expected 3 parts, got {len(parts)}")

        # Parse JWT claims
        claims = self._parse_jwt_claims(token)
        
        # Extract expiry
        exp = claims.get("exp")
        if exp:
            self.token_expires = datetime.fromtimestamp(exp, tz=timezone.utc)
        else:
            # Default to 1 year if no expiry in token (conservative estimate)
            _LOGGER.warning("JWT has no 'exp' claim, defaulting to 1 year validity")
            self.token_expires = datetime.now(timezone.utc) + timedelta(days=365)

        # Extract issued-at time
        iat = claims.get("iat")
        if iat:
            self.token_issued = datetime.fromtimestamp(iat, tz=timezone.utc)
        else:
            self.token_issued = datetime.now(timezone.utc)

        # Validate token isn't already expired (check directly, not via property)
        now = datetime.now(timezone.utc)
        if self.token_expires and now >= self.token_expires:
            raise EnviTokenError(
                f"Received already-expired JWT token (exp={self.token_expires}, now={now})"
            )

        # Store the token
        self.token = token
        
        _LOGGER.debug(
            "JWT token set: exp=%s, iat=%s, valid_for=%s",
            self.token_expires,
            self.token_issued,
            self.token_expires - datetime.now(timezone.utc) if self.token_expires else "unknown"
        )

    def _parse_jwt_claims(self, token: str) -> dict[str, Any]:
        """Parse and decode JWT payload claims."""
        try:
            # JWT structure: header.payload.signature
            payload_part = token.split(".")[1]
            
            # Add padding for base64 decoding (JWT uses base64url without padding)
            padding_needed = 4 - (len(payload_part) % 4)
            if padding_needed != 4:
                payload_part += "=" * padding_needed
            
            # Decode and parse
            decoded = base64.urlsafe_b64decode(payload_part)
            claims = json.loads(decoded)
            
            _LOGGER.debug("JWT claims parsed: %s", {k: v for k, v in claims.items() if k not in ('token',)})
            return claims
            
        except (IndexError, ValueError) as e:
            _LOGGER.warning("Failed to parse JWT claims: %s", e)
            return {}
        except json.JSONDecodeError as e:
            _LOGGER.warning("Failed to decode JWT payload as JSON: %s", e)
            return {}

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid token, refreshing if necessary."""
        if self.is_token_valid:
            return

        async with self._refresh_lock:
            # Double-check after acquiring lock (another coroutine may have refreshed)
            if self.is_token_valid:
                return
            
            if self.token and not self.is_token_expired:
                _LOGGER.debug("Token approaching expiry, proactively refreshing")
            else:
                _LOGGER.debug("Token missing or expired, authenticating")
            
            await self.authenticate()

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        Internal request handler with automatic token management.
        
        Handles:
        - Automatic authentication if no token
        - Proactive token refresh before expiry
        - Retry on 401/403 with fresh token
        """
        # Ensure we have a valid token before making request
        await self._ensure_valid_token()

        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        kwargs["headers"] = headers

        url = f"{self.base_url}/{endpoint}"
        
        _LOGGER.debug("API request: %s %s", method.upper(), endpoint)

        try:
            async with self.session.request(
                method.upper(), url, timeout=self.timeout, **kwargs
            ) as resp:
                
                # Handle auth errors with retry
                if resp.status in (401, 403):
                    _LOGGER.warning(
                        "Received %s from API – token may be invalid, refreshing",
                        resp.status
                    )
                    return await self._retry_with_fresh_token(method, url, **kwargs)

                # Handle other HTTP errors
                if resp.status >= 400:
                    error_text = await resp.text()
                    _LOGGER.error("API error %s: %s", resp.status, error_text[:200])
                    
                    if resp.status >= 500:
                        raise EnviApiError(f"Envi server error: {resp.status}")
                    else:
                        raise EnviDeviceError(f"API request failed: {resp.status}")

                return await resp.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during API request: %s", err)
            raise EnviApiError(f"Network error: {err}") from err

    async def _retry_with_fresh_token(self, method: str, url: str, **kwargs) -> dict:
        """Retry a request after refreshing the authentication token."""
        async with self._refresh_lock:
            # Force re-authentication
            self.token = None
            self.token_expires = None
            await self.authenticate()
        
        # Update headers with new token
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        kwargs["headers"] = headers

        _LOGGER.debug("Retrying request with fresh token: %s", url)

        async with self.session.request(
            method.upper(), url, timeout=self.timeout, **kwargs
        ) as retry_resp:
            if retry_resp.status in (401, 403):
                raise EnviAuthenticationError(
                    "Authentication failed even after token refresh"
                )
            
            if retry_resp.status >= 400:
                error_text = await retry_resp.text()
                raise EnviApiError(f"API request failed after retry: {retry_resp.status} - {error_text[:100]}")
            
            return await retry_resp.json()

    # ==========================================================================
    # Public API Methods
    # ==========================================================================

    async def fetch_all_device_ids(self) -> list[str]:
        """Fetch list of all device IDs associated with the account."""
        data = await self._request("GET", "device/list")
        devices = data.get("data", [])
        
        if not devices:
            _LOGGER.warning("No devices found in Envi account")
            return []
        
        device_ids = [str(d["id"]) for d in devices if "id" in d]
        _LOGGER.debug("Found %d devices: %s", len(device_ids), device_ids)
        return device_ids

    async def get_device_state(self, device_id: str) -> dict:
        """Get current state of a specific device."""
        data = await self._request("GET", f"device/{device_id}")
        return data.get("data", {})

    async def update_device(self, device_id: str, payload: dict) -> dict:
        """Update device settings (temperature, state, etc.)."""
        _LOGGER.debug("Updating device %s with: %s", device_id, payload)
        return await self._request(
            "PATCH", 
            f"device/update-temperature/{device_id}", 
            json=payload
        )

    async def test_connection(self) -> bool:
        """Test if the API connection and authentication work."""
        try:
            await self._ensure_valid_token()
            await self.fetch_all_device_ids()
            return True
        except Exception as err:
            _LOGGER.debug("Connection test failed: %s", err)
            return False

    async def get_token_info(self) -> dict:
        """Get information about the current token (for debugging)."""
        await self._ensure_valid_token()
        
        now = datetime.now(timezone.utc)
        return {
            "has_token": bool(self.token),
            "is_valid": self.is_token_valid,
            "is_expired": self.is_token_expired,
            "expires_at": self.token_expires.isoformat() if self.token_expires else None,
            "issued_at": self.token_issued.isoformat() if self.token_issued else None,
            "time_remaining": str(self.token_expires - now) if self.token_expires else None,
        }
