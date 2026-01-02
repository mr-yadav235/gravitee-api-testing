# Gravitee HTTP Callout & Parameter Passing Guide

This guide explains how to configure Gravitee APIM to pass path parameters, query parameters, and headers from the Gateway URL to the backend URL.

## Quick Reference

### URL Flow

```
Client Request → Gravitee Gateway → Backend API
     ↓                  ↓                ↓
/petstore/pet/findByStatus?status=available
                    ↓
            (strip context path)
                    ↓
         /pet/findByStatus?status=available
                    ↓
    https://petstore.swagger.io/v2/pet/findByStatus?status=available
```

## Basic Configuration

### 1. Context Path & Backend URL

| Setting | Value | Description |
|---------|-------|-------------|
| **Context Path** | `/petstore` | Gateway path prefix |
| **Backend URL** | `https://petstore.swagger.io/v2` | Target backend |
| **Strip Context Path** | `true` | Remove `/petstore` before forwarding |

### 2. Default Behavior

By default, Gravitee **automatically forwards**:
- ✅ All query parameters (`?status=available&limit=10`)
- ✅ All path segments (`/pet/123`)
- ✅ All headers (except hop-by-hop headers)
- ✅ Request body

## Examples

### Example 1: Simple Proxy (Petstore)

**Gateway URL:**
```
http://localhost:8082/petstore/pet/findByStatus?status=available
```

**Backend URL (auto-generated):**
```
https://petstore.swagger.io/v2/pet/findByStatus?status=available
```

**Configuration:**
```yaml
contextPath: /petstore
endpoint: https://petstore.swagger.io/v2
proxy:
  strip_context_path: true
```

### Example 2: Path Parameter

**Gateway URL:**
```
http://localhost:8082/petstore/pet/12345
```

**Backend URL:**
```
https://petstore.swagger.io/v2/pet/12345
```

The path parameter `12345` is automatically included.

### Example 3: Multiple Query Parameters

**Gateway URL:**
```
http://localhost:8082/petstore/pet/findByStatus?status=available&status=pending
```

**Backend URL:**
```
https://petstore.swagger.io/v2/pet/findByStatus?status=available&status=pending
```

Multiple values for the same parameter are preserved.

## Advanced Configuration

### Using Gravitee Expression Language (EL)

Access request data using EL expressions:

| Expression | Description | Example Value |
|------------|-------------|---------------|
| `{#request.path}` | Full request path | `/petstore/pet/findByStatus` |
| `{#request.paths[0]}` | First path segment after context | `pet` |
| `{#request.paths[1]}` | Second path segment | `findByStatus` |
| `{#request.params['status']}` | Query parameter value | `available` |
| `{#request.params['status'][0]}` | First value of multi-value param | `available` |
| `{#request.headers['Content-Type']}` | Header value | `application/json` |
| `{#request.uri}` | Full URI with query string | `/petstore/pet/findByStatus?status=available` |

### Transform Query Parameters Policy

Add, modify, or remove query parameters:

```yaml
flows:
  - name: "Transform Params"
    path-operator:
      path: /pet/findByStatus
      operator: EQUALS
    pre:
      - name: "Modify Query Params"
        policy: transform-queryparams
        configuration:
          # Add new parameters
          addQueryParameters:
            - name: api_version
              value: "2"
          
          # Override existing parameters
          overrideQueryParameters:
            - name: status
              value: "{#request.params['status'] ?: 'available'}"
          
          # Remove parameters
          removeQueryParameters:
            - debug
            - internal
```

### Transform Headers Policy

Add, modify, or remove headers:

```yaml
flows:
  - name: "Transform Headers"
    pre:
      - name: "Add Backend Auth"
        policy: transform-headers
        configuration:
          scope: REQUEST
          addHeaders:
            - name: X-Backend-Key
              value: "secret-key"
            - name: X-Forwarded-For
              value: "{#request.headers['X-Real-IP']}"
          removeHeaders:
            - X-Debug
```

### Dynamic Endpoint Policy

Route to different backends based on request:

```yaml
flows:
  - name: "Dynamic Routing"
    pre:
      - name: "Route by Region"
        policy: dynamic-routing
        configuration:
          rules:
            - pattern: "{#request.headers['X-Region'] == 'EU'}"
              url: "https://eu.petstore.swagger.io/v2{#request.pathInfo}"
            - pattern: "{#request.headers['X-Region'] == 'US'}"
              url: "https://us.petstore.swagger.io/v2{#request.pathInfo}"
```

### HTTP Callout Policy

Make additional HTTP calls during request processing:

```yaml
flows:
  - name: "Enrich Request"
    pre:
      - name: "Fetch User Details"
        policy: http-callout
        configuration:
          method: GET
          url: "https://api.example.com/users/{#request.headers['X-User-ID']}"
          headers:
            - name: Authorization
              value: "Bearer {#context.attributes['token']}"
          variables:
            - name: userDetails
              value: "{#jsonPath(#calloutResponse.content, '$.data')}"
```

## Console UI Configuration

### Step-by-Step: Create Petstore API

1. **Create New API**
   - Go to **APIs** → **+ Add API** → **Create from scratch**
   - Name: `Petstore API`
   - Version: `1.0`
   - Context Path: `/petstore`

2. **Configure Backend**
   - Go to **Endpoints** → **Backend services**
   - Click **+ Add endpoint group**
   - Name: `Petstore Backend`
   - Add endpoint: `https://petstore.swagger.io/v2`

3. **Configure Proxy Settings**
   - Go to **Proxy** → **Entrypoints**
   - Enable **Strip context path**: ✅

4. **Create Plan**
   - Go to **Plans** → **+ Add plan**
   - Name: `Open Plan`
   - Security: `Keyless`
   - Publish the plan

5. **Deploy API**
   - Go to **Deployments** → **Deploy API**

### Test the API

```bash
# Test with curl
curl "http://localhost:8082/petstore/pet/findByStatus?status=available"

# Expected: JSON array of available pets from Petstore API
```

## Common Issues & Solutions

### Issue: Query Parameters Not Forwarded

**Symptom:** Backend receives request without query parameters

**Solution:** Check if any policy is stripping parameters
```yaml
# Verify no removeQueryParameters in your flows
flows:
  - pre:
      - policy: transform-queryparams
        configuration:
          removeQueryParameters: []  # Should be empty or not present
```

### Issue: Path Not Matching

**Symptom:** 404 errors on Gateway

**Solution:** Check path operator configuration
```yaml
# Use STARTS_WITH for prefix matching
path-operator:
  path: /pet
  operator: STARTS_WITH  # Not EQUALS

# Or use regex for complex patterns
path-operator:
  path: /pet/[0-9]+
  operator: REGEX
```

### Issue: Backend Receives Wrong Path

**Symptom:** Backend gets `/petstore/pet/...` instead of `/pet/...`

**Solution:** Enable strip context path
```yaml
proxy:
  strip_context_path: true  # Must be true
```

### Issue: Headers Not Forwarded

**Symptom:** Backend doesn't receive certain headers

**Solution:** Check if headers are in the blocked list
```yaml
# Some headers are not forwarded by default (hop-by-hop)
# Add them explicitly if needed
flows:
  - pre:
      - policy: transform-headers
        configuration:
          addHeaders:
            - name: X-Custom-Header
              value: "{#request.headers['X-Custom-Header']}"
```

## Debug Tips

### Enable Request Logging

```yaml
logging:
  mode: CLIENT_PROXY
  content: HEADERS_PAYLOADS
  scope: REQUEST_RESPONSE
```

### Check Gateway Logs

```bash
kubectl logs deployment/gravitee-apim-gateway -n gravitee -f | grep -i "petstore"
```

### Test Backend Directly

```bash
# Verify backend is accessible
curl "https://petstore.swagger.io/v2/pet/findByStatus?status=available"
```

## Reference Links

- [Gravitee Expression Language](https://docs.gravitee.io/apim/3.x/apim_publisherguide_expression_language.html)
- [Transform Query Params Policy](https://docs.gravitee.io/apim/3.x/apim_policies_transform_query_params.html)
- [Transform Headers Policy](https://docs.gravitee.io/apim/3.x/apim_policies_transform_headers.html)
- [HTTP Callout Policy](https://docs.gravitee.io/apim/3.x/apim_policies_http_callout.html)
- [Swagger Petstore API](https://petstore.swagger.io/)

