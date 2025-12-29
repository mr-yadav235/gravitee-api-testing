"""
Contract Tests - Validate API responses against OpenAPI schemas
"""

import pytest
import requests
import yaml
import os
from jsonschema import validate, ValidationError

GATEWAY_URL = os.getenv("GATEWAY_URL", "https://api.example.com")
API_KEY = os.getenv("API_KEY", "")


class TestUsersApiContract:
    """Contract tests for Users API"""
    
    USER_SCHEMA = {
        "type": "object",
        "required": ["id", "email"],
        "properties": {
            "id": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string"},
            "role": {"type": "string", "enum": ["USER", "ADMIN"]},
            "createdAt": {"type": "string", "format": "date-time"}
        }
    }
    
    @pytest.fixture
    def headers(self):
        return {"X-Gravitee-Api-Key": API_KEY}
    
    def test_get_users_returns_array(self, headers):
        """GET /users should return array of users"""
        response = requests.get(f"{GATEWAY_URL}/api/v1/users", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        for user in data[:5]:  # Validate first 5
            validate(instance=user, schema=self.USER_SCHEMA)
    
    def test_get_user_by_id_schema(self, headers):
        """GET /users/:id should match user schema"""
        response = requests.get(f"{GATEWAY_URL}/api/v1/users/test-user", headers=headers)
        
        if response.status_code == 200:
            validate(instance=response.json(), schema=self.USER_SCHEMA)
    
    def test_error_response_schema(self, headers):
        """Error responses should match error schema"""
        ERROR_SCHEMA = {
            "type": "object",
            "required": ["error"],
            "properties": {
                "error": {"type": "string"},
                "code": {"type": "string"},
                "details": {"type": "object"}
            }
        }
        
        response = requests.get(f"{GATEWAY_URL}/api/v1/users/nonexistent", headers=headers)
        
        if response.status_code == 404:
            validate(instance=response.json(), schema=ERROR_SCHEMA)


class TestOrdersApiContract:
    """Contract tests for Orders API"""
    
    ORDER_SCHEMA = {
        "type": "object",
        "required": ["orderId", "customerId", "status"],
        "properties": {
            "orderId": {"type": "string"},
            "customerId": {"type": "string"},
            "status": {"type": "string", "enum": ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED"]},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["productId", "quantity"],
                    "properties": {
                        "productId": {"type": "string"},
                        "quantity": {"type": "integer", "minimum": 1}
                    }
                }
            },
            "total": {"type": "number"},
            "createdAt": {"type": "string", "format": "date-time"}
        }
    }
    
    @pytest.fixture
    def headers(self):
        return {"X-Gravitee-Api-Key": API_KEY, "Content-Type": "application/json"}
    
    def test_create_order_response_schema(self, headers):
        """POST /orders response should match schema"""
        payload = {
            "customerId": "test-customer",
            "items": [{"productId": "prod-1", "quantity": 1}]
        }
        
        response = requests.post(f"{GATEWAY_URL}/api/v1/orders", json=payload, headers=headers)
        
        if response.status_code == 201:
            validate(instance=response.json(), schema=self.ORDER_SCHEMA)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

