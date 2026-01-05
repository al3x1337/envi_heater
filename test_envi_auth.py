"""
Envi API Authentication Test Script (No dependencies)

Run this script to test your Envi credentials directly against the API.
Uses only Python standard library - no pip install required.

Usage:
    python test_envi_auth.py your_email@example.com your_password
"""

import json
import sys
import uuid
import urllib.request
import urllib.error
import ssl
import base64
from datetime import datetime


def test_login(username: str, password: str):
    """Test authentication with the Envi API."""
    
    base_url = "https://app-apis.enviliving.com/apis/v1"
    
    # Generate a device ID similar to the mobile app
    device_id = f"ha_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    
    # Login payload
    payload = {
        "username": username,
        "password": password,
        "login_type": 1,
        "device_id": device_id,
        "device_type": "homeassistant",
    }
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "HomeAssistant-Envi/1.1",
    }
    
    print("=" * 60)
    print("ENVI API AUTHENTICATION TEST")
    print("=" * 60)
    print(f"\nEndpoint: {base_url}/auth/login")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print(f"Device ID: {device_id}")
    print(f"\nPayload: {json.dumps({**payload, 'password': '***'}, indent=2)}")
    print("\n" + "-" * 60)
    
    try:
        # Create request
        url = f"{base_url}/auth/login"
        data = json.dumps(payload).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        # Create SSL context (allow connections)
        ctx = ssl.create_default_context()
        
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            status = response.getcode()
            resp_text = response.read().decode('utf-8')
            
            print(f"\nHTTP Status: {status}")
            print(f"\nRaw Response:\n{resp_text[:2000]}")
            
            try:
                data = json.loads(resp_text)
                print(f"\nParsed JSON:\n{json.dumps(data, indent=2)}")
                
                if data.get("status") == "success":
                    token = data.get("data", {}).get("token", "")
                    print("\n" + "=" * 60)
                    print("✅ LOGIN SUCCESSFUL!")
                    print("=" * 60)
                    print(f"Token (first 50 chars): {token[:50]}...")
                    
                    # Decode JWT to show expiry
                    if token:
                        try:
                            parts = token.split(".")
                            if len(parts) == 3:
                                payload_part = parts[1]
                                payload_part += "=" * (-len(payload_part) % 4)
                                claims = json.loads(base64.urlsafe_b64decode(payload_part))
                                print(f"\nJWT Claims: {json.dumps(claims, indent=2)}")
                        except Exception as e:
                            print(f"\nCould not decode JWT: {e}")
                else:
                    print("\n" + "=" * 60)
                    print("❌ LOGIN FAILED!")
                    print("=" * 60)
                    print(f"Status: {data.get('status')}")
                    print(f"Message: {data.get('msg', data.get('message', 'No message'))}")
                    print(f"Error code: {data.get('code', 'N/A')}")
                    
            except json.JSONDecodeError as e:
                print(f"\n❌ Failed to parse response as JSON: {e}")
                
    except urllib.error.HTTPError as e:
        print(f"\n❌ HTTP Error: {e.code}")
        print(f"Response: {e.read().decode('utf-8')}")
    except urllib.error.URLError as e:
        print(f"\n❌ URL Error: {e.reason}")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
    
    print("\n" + "=" * 60)
    print("TROUBLESHOOTING TIPS:")
    print("=" * 60)
    print("""
1. Verify credentials work in the official Envi app
2. Check if your email is case-sensitive (try lowercase)
3. Ensure no special characters are causing issues
4. Check if 2FA is enabled on your account
5. Try creating a new password without special characters
6. Make sure your account is verified/activated
""")


def test_alternative_auth(username: str, password: str):
    """Test OAuth2 token endpoint (alternative method)."""
    
    print("\n" + "=" * 60)
    print("TESTING ALTERNATIVE OAUTH2 ENDPOINT")
    print("=" * 60)
    
    # Some APIs use OAuth2 token endpoint
    oauth_url = "https://app-apis.enviliving.com/oauth2/token"
    
    payload = "grant_type=password&client_id=099153c2625149bc8ecb3e85e03f0022&username={}&password={}".format(
        urllib.parse.quote(username),
        urllib.parse.quote(password)
    )
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    print(f"\nEndpoint: {oauth_url}")
    
    try:
        import urllib.parse
        
        req = urllib.request.Request(
            oauth_url, 
            data=payload.encode('utf-8'), 
            headers=headers, 
            method='POST'
        )
        
        ctx = ssl.create_default_context()
        
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            print(f"HTTP Status: {response.getcode()}")
            print(f"Response: {response.read().decode('utf-8')[:1000]}")
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        try:
            print(f"Response: {e.read().decode('utf-8')[:500]}")
        except:
            pass
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import urllib.parse  # Import here to avoid issues
    
    if len(sys.argv) < 3:
        print("=" * 60)
        print("ENVI API AUTHENTICATION TESTER")
        print("=" * 60)
        print("\nUsage: python test_envi_auth.py <email> <password>")
        print("\nExample:")
        print('  python test_envi_auth.py "user@example.com" "mypassword"')
        print("\nNote: Put quotes around values with special characters!")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    test_login(username, password)
    test_alternative_auth(username, password)
