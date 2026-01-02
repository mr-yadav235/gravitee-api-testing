# Keycloak Authorization Server Integration with Gravitee APIM

This guide explains how to set up Keycloak as an OAuth2/OpenID Connect Authorization Server and integrate it with Gravitee APIM for securing APIs.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Keycloak Setup](#keycloak-setup)
4. [Gravitee Integration](#gravitee-integration)
5. [Securing APIs with OAuth2](#securing-apis-with-oauth2)
6. [Testing the Integration](#testing-the-integration)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Client    │────▶│    Keycloak     │     │   Backend API   │
│  (Application)  │     │  (Auth Server)  │     │    (Service)    │
└────────┬────────┘     └────────┬────────┘     └────────▲────────┘
         │                       │                       │
         │  1. Get Token         │                       │
         │◀──────────────────────│                       │
         │                       │                       │
         │  2. Call API with Token                       │
         │───────────────────────┼───────────────────────│
         │                       │                       │
         │              ┌────────▼────────┐              │
         │              │    Gravitee     │              │
         │              │    Gateway      │──────────────┘
         │              │  (Validates     │  3. Forward Request
         │              │   Token)        │
         │              └─────────────────┘
         │                       │
         │  4. API Response      │
         │◀──────────────────────│
```

### Components

| Component | Purpose | Port |
|-----------|---------|------|
| **Keycloak** | OAuth2/OIDC Authorization Server | 8180 |
| **Gravitee Gateway** | API Gateway (validates tokens) | 8082 |
| **Gravitee Console** | Management UI | 8080 |

### Pre-configured Clients

| Client ID | Purpose | Secret |
|-----------|---------|--------|
| `gravitee-gateway` | Resource server for token validation | `gravitee-gateway-secret` |
| `gravitee-console` | SSO for Gravitee Console | `gravitee-console-secret` |
| `api-client` | Sample API consumer application | `api-client-secret` |

### Pre-configured Users

| Username | Password | Roles |
|----------|----------|-------|
| `apiuser` | `apiuser123` | user |
| `apiadmin` | `apiadmin123` | user, admin |

---

## Quick Start

### Step 1: Deploy Keycloak

```bash
# Apply Keycloak manifests
kubectl apply -f gravitee-setup/manifests/keycloak/keycloak.yaml

# Wait for Keycloak to be ready (takes ~2 minutes)
kubectl wait --for=condition=ready pod -l app=keycloak -n gravitee --timeout=300s

# Check status
kubectl get pods -n gravitee | grep keycloak
```

### Step 2: Port Forward Keycloak

```bash
# Start port forwarding
kubectl port-forward svc/keycloak 8180:8080 -n gravitee &

echo "Keycloak available at: http://localhost:8180"
echo "Admin Console: http://localhost:8180/admin"
echo "Credentials: admin / admin123"
```

### Step 3: Verify Keycloak is Running

```bash
# Check Keycloak health
curl -s http://localhost:8180/health/ready

# Get OpenID Configuration
curl -s http://localhost:8180/realms/gravitee/.well-known/openid-configuration | jq .
```

### Step 4: Get an Access Token

```bash
# Using Password Grant (for testing)
curl -s -X POST "http://localhost:8180/realms/gravitee/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-client" \
  -d "client_secret=api-client-secret" \
  -d "username=apiuser" \
  -d "password=apiuser123" \
  -d "grant_type=password" | jq .
```

---

## Keycloak Setup

### Access Keycloak Admin Console

1. Open: http://localhost:8180/admin
2. Login with: `admin` / `admin123`
3. Select the **gravitee** realm from the dropdown

### Realm Configuration

The `gravitee` realm is pre-configured with:

- **Clients**: For Gravitee Gateway, Console, and API consumers
- **Users**: Test users with different roles
- **Roles**: `user` and `admin` realm roles
- **Token Settings**: Access token lifetime of 5 minutes

### Creating Additional Clients

To add a new API client:

1. Go to **Clients** → **Create client**
2. Set **Client ID** (e.g., `my-app`)
3. Enable **Client authentication**
4. Set **Valid redirect URIs** (e.g., `http://localhost:3000/*`)
5. Save and copy the **Client secret** from the Credentials tab

---

## Gravitee Integration

### Option 1: OAuth2 Resource (JWT Validation)

This is the recommended approach for validating JWT tokens at the Gateway.

#### Configure in Gravitee Console

1. Go to **APIs** → Select your API → **Policy Studio**
2. Add **JWT** policy to the request flow
3. Configure:

```yaml
# JWT Policy Configuration
name: JWT Validation
policy: jwt
configuration:
  signature: RSA_RS256
  publicKeyResolver: JWKS_URL
  resolverParameter: http://keycloak.gravitee.svc.cluster.local:8080/realms/gravitee/protocol/openid-connect/certs
  useSystemProxy: false
  extractClaims: true
  propagateAuthHeader: true
```

#### Using API Definition CRD

```yaml
apiVersion: gravitee.io/v1alpha1
kind: ApiDefinition
metadata:
  name: secured-api
  namespace: gravitee
spec:
  name: Secured API
  version: 1.0.0
  contextPath: /secured
  proxy:
    virtualHosts:
      - path: /secured
    groups:
      - name: default
        endpoints:
          - name: backend
            target: http://backend-service:8080
  flows:
    - name: JWT Validation
      pre:
        - name: JWT
          policy: jwt
          configuration:
            signature: RSA_RS256
            publicKeyResolver: JWKS_URL
            resolverParameter: http://keycloak.gravitee.svc.cluster.local:8080/realms/gravitee/protocol/openid-connect/certs
            extractClaims: true
```

### Option 2: OAuth2 Introspection

For opaque tokens or additional validation:

```yaml
# OAuth2 Resource Configuration
name: Keycloak OAuth2
type: oauth2
configuration:
  authorizationServerUrl: http://keycloak.gravitee.svc.cluster.local:8080/realms/gravitee
  introspectionEndpoint: /protocol/openid-connect/token/introspect
  introspectionEndpointMethod: POST
  clientId: gravitee-gateway
  clientSecret: gravitee-gateway-secret
  useClientAuthorizationHeader: true
  tokenIsSuppliedByQueryParam: false
  tokenIsSuppliedByHttpHeader: true
  tokenHeaderName: Authorization
  tokenTypeHint: access_token
```

### Option 3: Console SSO (Single Sign-On)

To enable SSO for Gravitee Console with Keycloak:

Update Gravitee Helm values:

```yaml
api:
  security:
    providers:
      - type: oidc
        id: keycloak
        clientId: gravitee-console
        clientSecret: gravitee-console-secret
        tokenEndpoint: http://keycloak.gravitee.svc.cluster.local:8080/realms/gravitee/protocol/openid-connect/token
        authorizeEndpoint: http://localhost:8180/realms/gravitee/protocol/openid-connect/auth
        userInfoEndpoint: http://keycloak.gravitee.svc.cluster.local:8080/realms/gravitee/protocol/openid-connect/userinfo
        logoutEndpoint: http://localhost:8180/realms/gravitee/protocol/openid-connect/logout
        scopes:
          - openid
          - profile
          - email
        userMapping:
          id: sub
          email: email
          firstname: given_name
          lastname: family_name
```

---

## Securing APIs with OAuth2

### Step 1: Create an API Plan with OAuth2

In Gravitee Console:

1. Go to **APIs** → Select API → **Plans**
2. Click **Add new plan**
3. Select **OAuth2** security type
4. Configure:
   - **Name**: OAuth2 Plan
   - **OAuth2 Resource**: Select your configured Keycloak resource
   - **Required Scopes**: (optional) e.g., `openid`, `profile`
5. Publish the plan

### Step 2: Subscribe to the Plan

1. Go to **Developer Portal** (http://localhost:8085)
2. Find your API
3. Subscribe to the OAuth2 plan
4. Note: No API key needed - tokens come from Keycloak

### Step 3: Call the API with Token

```bash
# 1. Get access token
TOKEN=$(curl -s -X POST "http://localhost:8180/realms/gravitee/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-client" \
  -d "client_secret=api-client-secret" \
  -d "username=apiuser" \
  -d "password=apiuser123" \
  -d "grant_type=password" | jq -r '.access_token')

echo "Token: $TOKEN"

# 2. Call API with Bearer token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8082/your-api-path
```

---

## Testing the Integration

### Test Script

```bash
#!/bin/bash
# test-oauth2.sh

KEYCLOAK_URL="http://localhost:8180"
GATEWAY_URL="http://localhost:8082"
REALM="gravitee"

echo "=== OAuth2 Integration Test ==="

# 1. Get Token
echo -e "\n1. Getting access token..."
TOKEN_RESPONSE=$(curl -s -X POST "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-client" \
  -d "client_secret=api-client-secret" \
  -d "username=apiuser" \
  -d "password=apiuser123" \
  -d "grant_type=password")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
EXPIRES_IN=$(echo $TOKEN_RESPONSE | jq -r '.expires_in')

if [ "$ACCESS_TOKEN" != "null" ] && [ -n "$ACCESS_TOKEN" ]; then
  echo "✅ Token obtained successfully (expires in ${EXPIRES_IN}s)"
else
  echo "❌ Failed to get token"
  echo $TOKEN_RESPONSE | jq .
  exit 1
fi

# 2. Decode Token (for debugging)
echo -e "\n2. Token Claims:"
echo $ACCESS_TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .

# 3. Test API Call (update path to your API)
echo -e "\n3. Calling API with token..."
API_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "${GATEWAY_URL}/your-api-path")

HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
BODY=$(echo "$API_RESPONSE" | sed '$d')

echo "HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" == "200" ]; then
  echo "✅ API call successful"
  echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
  echo "❌ API call failed"
  echo "$BODY"
fi

# 4. Test without token (should fail)
echo -e "\n4. Testing without token (should fail)..."
UNAUTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${GATEWAY_URL}/your-api-path")
UNAUTH_CODE=$(echo "$UNAUTH_RESPONSE" | tail -n1)

if [ "$UNAUTH_CODE" == "401" ]; then
  echo "✅ Correctly rejected unauthorized request (401)"
else
  echo "⚠️  Unexpected response: $UNAUTH_CODE"
fi

echo -e "\n=== Test Complete ==="
```

### Verify Token Introspection

```bash
# Introspect a token
curl -s -X POST "http://localhost:8180/realms/gravitee/protocol/openid-connect/token/introspect" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "gravitee-gateway:gravitee-gateway-secret" \
  -d "token=$TOKEN" | jq .
```

---

## Advanced Configuration

### Client Credentials Grant (Machine-to-Machine)

For service accounts without user interaction:

```bash
# Get token using client credentials
curl -s -X POST "http://localhost:8180/realms/gravitee/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-client" \
  -d "client_secret=api-client-secret" \
  -d "grant_type=client_credentials" | jq .
```

### Role-Based Access Control

Extract roles from JWT and use in policies:

```yaml
# Gravitee Policy to check roles
- name: Check Admin Role
  policy: groovy
  configuration:
    script: |
      def claims = context.getAttribute('jwt.claims')
      def roles = claims?.realm_access?.roles ?: []
      
      if (!roles.contains('admin')) {
        return result.state(PolicyResult.State.FAILURE)
                     .code(403)
                     .message('Admin role required')
      }
```

### Custom Scopes

1. In Keycloak, go to **Client scopes** → **Create client scope**
2. Add scope to your client
3. Configure Gravitee plan to require the scope:

```yaml
plans:
  - name: Premium API Access
    security: OAUTH2
    securityDefinition:
      oauthResource: keycloak-oauth2
      requiredScopes:
        - premium
        - read:data
```

### Rate Limiting by User

```yaml
# Rate limit based on JWT subject
- name: User Rate Limit
  policy: rate-limit
  configuration:
    key: "{#context.attributes['jwt.claims']['sub']}"
    rate:
      limit: 100
      periodTime: 1
      periodTimeUnit: MINUTES
```

---

## Troubleshooting

### Common Issues

#### 1. Token Validation Fails

**Error**: `Invalid token` or `Token signature verification failed`

**Solutions**:
- Verify JWKS URL is accessible from Gateway:
  ```bash
  kubectl exec -it deployment/gravitee-apim-gateway -n gravitee -- \
    curl -s http://keycloak.gravitee.svc.cluster.local:8080/realms/gravitee/protocol/openid-connect/certs
  ```
- Check token hasn't expired
- Verify correct realm name

#### 2. CORS Issues

**Error**: Browser blocks requests due to CORS

**Solution**: Add CORS policy in Gravitee:
```yaml
- name: CORS
  policy: cors
  configuration:
    allowOrigin: "*"
    allowMethods:
      - GET
      - POST
      - PUT
      - DELETE
    allowHeaders:
      - Authorization
      - Content-Type
```

#### 3. Keycloak Pod Not Starting

```bash
# Check logs
kubectl logs deployment/keycloak -n gravitee

# Check events
kubectl describe pod -l app=keycloak -n gravitee
```

#### 4. Connection Refused from Gateway to Keycloak

Ensure using internal service name:
```
http://keycloak.gravitee.svc.cluster.local:8080
```

Not `localhost:8180` (that's only for port-forwarding).

### Debug Token Claims

```bash
# Decode JWT without validation
echo $TOKEN | cut -d'.' -f2 | base64 -d | jq .
```

### Check Keycloak Logs

```bash
kubectl logs -f deployment/keycloak -n gravitee
```

---

## Service URLs Summary

### Internal (Kubernetes)

| Service | URL |
|---------|-----|
| Keycloak | `http://keycloak.gravitee.svc.cluster.local:8080` |
| JWKS Endpoint | `http://keycloak.gravitee.svc.cluster.local:8080/realms/gravitee/protocol/openid-connect/certs` |
| Token Endpoint | `http://keycloak.gravitee.svc.cluster.local:8080/realms/gravitee/protocol/openid-connect/token` |
| Introspect Endpoint | `http://keycloak.gravitee.svc.cluster.local:8080/realms/gravitee/protocol/openid-connect/token/introspect` |

### External (Port-Forwarded)

| Service | URL |
|---------|-----|
| Keycloak Admin | `http://localhost:8180/admin` |
| Token Endpoint | `http://localhost:8180/realms/gravitee/protocol/openid-connect/token` |
| OIDC Discovery | `http://localhost:8180/realms/gravitee/.well-known/openid-configuration` |

---

## Quick Reference

### Get Token (Copy-Paste Ready)

```bash
# Password Grant
curl -s -X POST "http://localhost:8180/realms/gravitee/protocol/openid-connect/token" \
  -d "client_id=api-client" \
  -d "client_secret=api-client-secret" \
  -d "username=apiuser" \
  -d "password=apiuser123" \
  -d "grant_type=password" | jq -r '.access_token'
```

### Call API with Token

```bash
TOKEN=$(curl -s -X POST "http://localhost:8180/realms/gravitee/protocol/openid-connect/token" \
  -d "client_id=api-client" -d "client_secret=api-client-secret" \
  -d "username=apiuser" -d "password=apiuser123" \
  -d "grant_type=password" | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" http://localhost:8082/your-api
```


