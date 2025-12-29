"""
API Security Tests for Gravitee APIM Gateway
Tests OWASP API Security Top 10 vulnerabilities
"""

import pytest
import requests
import jwt
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Configuration
GATEWAY_URL = os.getenv("GATEWAY_URL", "https://api.example.com")
API_KEY = os.getenv("API_KEY", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")


class TestAuthenticationSecurity:
    """Test authentication mechanisms"""
    
    def test_missing_api_key_returns_401(self):
        """API should reject requests without authentication"""
        response = requests.get(f"{GATEWAY_URL}/api/v1/users")
        assert response.status_code == 401
        assert "error" in response.json()
    
    def test_invalid_api_key_returns_401(self):
        """API should reject invalid API keys"""
        headers = {"X-Gravitee-Api-Key": "invalid-key-12345"}
        response = requests.get(f"{GATEWAY_URL}/api/v1/users", headers=headers)
        assert response.status_code == 401
    
    def test_expired_jwt_returns_401(self):
        """API should reject expired JWT tokens"""
        # Create an expired token
        expired_payload = {
            "sub": "test-user",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        # Note: In real tests, sign with proper key
        expired_token = jwt.encode(expired_payload, "test-secret", algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = requests.get(f"{GATEWAY_URL}/api/v1/users", headers=headers)
        assert response.status_code == 401
    
    def test_jwt_none_algorithm_rejected(self):
        """API should reject JWT with 'none' algorithm (CVE-2015-9235)"""
        payload = {"sub": "admin", "role": "ADMIN"}
        # Create token with 'none' algorithm
        token = jwt.encode(payload, "", algorithm="none") if hasattr(jwt, 'encode') else ""
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{GATEWAY_URL}/api/v1/admin", headers=headers)
        assert response.status_code in [401, 403]
    
    def test_api_key_not_accepted_in_url(self):
        """API keys should not be accepted in URL parameters"""
        response = requests.get(f"{GATEWAY_URL}/api/v1/users?api_key={API_KEY}")
        # Should either reject or ignore the URL parameter
        assert response.status_code in [401, 403]


class TestAuthorizationSecurity:
    """Test authorization and access control"""
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"X-Gravitee-Api-Key": API_KEY}
    
    def test_idor_user_cannot_access_other_user_data(self, auth_headers):
        """Test for Insecure Direct Object Reference (IDOR)"""
        # Try to access another user's data
        response = requests.get(
            f"{GATEWAY_URL}/api/v1/users/other-user-id/private",
            headers=auth_headers
        )
        # Should be forbidden or not found
        assert response.status_code in [403, 404]
    
    def test_regular_user_cannot_access_admin_endpoints(self, auth_headers):
        """Regular users should not access admin endpoints"""
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/config",
            "/api/v1/admin/logs"
        ]
        
        for endpoint in admin_endpoints:
            response = requests.get(f"{GATEWAY_URL}{endpoint}", headers=auth_headers)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should be protected"
    
    def test_cannot_modify_readonly_fields(self, auth_headers):
        """Test that readonly fields cannot be modified"""
        payload = {
            "id": "hacked-id",  # Should be readonly
            "createdAt": "2020-01-01T00:00:00Z",  # Should be readonly
            "name": "Test"
        }
        
        response = requests.post(
            f"{GATEWAY_URL}/api/v1/users",
            json=payload,
            headers=auth_headers
        )
        
        if response.status_code == 201:
            data = response.json()
            # ID should not be the one we provided
            assert data.get("id") != "hacked-id"


class TestInjectionSecurity:
    """Test for injection vulnerabilities"""
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"X-Gravitee-Api-Key": API_KEY}
    
    def test_sql_injection_in_query_params(self, auth_headers):
        """Test SQL injection in query parameters"""
        malicious_payloads = [
            "' OR '1'='1",
            "1; DROP TABLE users;--",
            "1 UNION SELECT * FROM users--",
            "admin'--"
        ]
        
        for payload in malicious_payloads:
            response = requests.get(
                f"{GATEWAY_URL}/api/v1/users",
                params={"search": payload},
                headers=auth_headers
            )
            # Should not return 500 (indicates SQL error)
            assert response.status_code != 500, f"Potential SQL injection with: {payload}"
            # Should not return all users
            if response.status_code == 200:
                data = response.json()
                assert len(data) < 1000, "Possible SQL injection - too many results"
    
    def test_nosql_injection(self, auth_headers):
        """Test NoSQL injection"""
        malicious_payloads = [
            {"$gt": ""},
            {"$ne": None},
            {"$where": "this.password.length > 0"}
        ]
        
        for payload in malicious_payloads:
            response = requests.get(
                f"{GATEWAY_URL}/api/v1/users",
                params={"filter": str(payload)},
                headers=auth_headers
            )
            assert response.status_code in [200, 400], "NoSQL injection should be blocked"
    
    def test_command_injection(self, auth_headers):
        """Test command injection"""
        malicious_payloads = [
            "; cat /etc/passwd",
            "| ls -la",
            "$(whoami)",
            "`id`"
        ]
        
        for payload in malicious_payloads:
            response = requests.post(
                f"{GATEWAY_URL}/api/v1/users",
                json={"name": payload},
                headers=auth_headers
            )
            # Should not execute commands
            assert response.status_code in [200, 201, 400]


class TestInputValidation:
    """Test input validation"""
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"X-Gravitee-Api-Key": API_KEY}
    
    def test_oversized_payload_rejected(self, auth_headers):
        """Large payloads should be rejected"""
        large_payload = {"data": "x" * 10_000_000}  # 10MB
        
        response = requests.post(
            f"{GATEWAY_URL}/api/v1/users",
            json=large_payload,
            headers=auth_headers
        )
        assert response.status_code in [400, 413]
    
    def test_invalid_content_type_rejected(self, auth_headers):
        """Invalid content types should be rejected"""
        headers = {**auth_headers, "Content-Type": "application/xml"}
        
        response = requests.post(
            f"{GATEWAY_URL}/api/v1/users",
            data="<user><name>test</name></user>",
            headers=headers
        )
        assert response.status_code in [400, 415]
    
    def test_xss_payload_sanitized(self, auth_headers):
        """XSS payloads should be sanitized"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            response = requests.post(
                f"{GATEWAY_URL}/api/v1/users",
                json={"name": payload},
                headers=auth_headers
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                # Script tags should be sanitized
                assert "<script>" not in str(data)


class TestSecurityHeaders:
    """Test security headers"""
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"X-Gravitee-Api-Key": API_KEY}
    
    def test_security_headers_present(self, auth_headers):
        """Required security headers should be present"""
        response = requests.get(f"{GATEWAY_URL}/api/v1/users", headers=auth_headers)
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Cache-Control"
        ]
        
        for header in required_headers:
            assert header in response.headers, f"Missing security header: {header}"
    
    def test_no_sensitive_headers_exposed(self, auth_headers):
        """Sensitive server information should not be exposed"""
        response = requests.get(f"{GATEWAY_URL}/api/v1/users", headers=auth_headers)
        
        sensitive_headers = [
            "Server",
            "X-Powered-By",
            "X-AspNet-Version"
        ]
        
        for header in sensitive_headers:
            if header in response.headers:
                # If present, should not reveal specific version
                value = response.headers[header]
                assert "version" not in value.lower()
    
    def test_cors_headers_configured(self, auth_headers):
        """CORS should be properly configured"""
        # Preflight request
        response = requests.options(
            f"{GATEWAY_URL}/api/v1/products",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # Should have CORS headers
        assert "Access-Control-Allow-Origin" in response.headers


class TestRateLimiting:
    """Test rate limiting"""
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"X-Gravitee-Api-Key": API_KEY}
    
    def test_rate_limit_headers_present(self, auth_headers):
        """Rate limit headers should be present"""
        response = requests.get(f"{GATEWAY_URL}/api/v1/users", headers=auth_headers)
        
        rate_limit_headers = [
            "X-Rate-Limit-Limit",
            "X-Rate-Limit-Remaining"
        ]
        
        for header in rate_limit_headers:
            assert header in response.headers, f"Missing rate limit header: {header}"
    
    @pytest.mark.skipif(ENVIRONMENT == "prod", reason="Skip rate limit test in production")
    def test_rate_limit_enforced(self, auth_headers):
        """Rate limiting should be enforced"""
        # Make many requests quickly
        responses = []
        for _ in range(150):  # Exceed typical rate limit
            response = requests.get(
                f"{GATEWAY_URL}/api/v1/users",
                headers=auth_headers
            )
            responses.append(response.status_code)
            if response.status_code == 429:
                break
        
        # Should eventually get rate limited
        assert 429 in responses, "Rate limiting not enforced"


class TestDataExposure:
    """Test for excessive data exposure"""
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"X-Gravitee-Api-Key": API_KEY}
    
    def test_passwords_not_in_response(self, auth_headers):
        """Passwords should never be in API responses"""
        response = requests.get(f"{GATEWAY_URL}/api/v1/users", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            data_str = str(data).lower()
            
            assert "password" not in data_str or "password\":null" in data_str
            assert "secret" not in data_str
    
    def test_sensitive_fields_masked(self, auth_headers):
        """Sensitive fields should be masked"""
        response = requests.get(
            f"{GATEWAY_URL}/api/v1/users/123",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # SSN should be masked if present
            if "ssn" in data:
                assert data["ssn"].startswith("***")
            
            # Credit card should be masked if present
            if "creditCard" in data:
                assert data["creditCard"].startswith("****")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

