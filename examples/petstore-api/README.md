# Petstore API Example

This example demonstrates how to configure Gravitee APIM to pass path parameters and query parameters from the Gateway URL to the backend URL.

## Backend API

- **Base URL**: `https://petstore.swagger.io/v2`
- **Documentation**: [Swagger Petstore](https://petstore.swagger.io/)

## URL Mapping

| Gateway URL | Backend URL |
|-------------|-------------|
| `http://localhost:8082/petstore/pet/findByStatus?status=available` | `https://petstore.swagger.io/v2/pet/findByStatus?status=available` |
| `http://localhost:8082/petstore/pet/123` | `https://petstore.swagger.io/v2/pet/123` |
| `http://localhost:8082/petstore/store/inventory` | `https://petstore.swagger.io/v2/store/inventory` |

## How It Works

### 1. Context Path Stripping

When `strip_context_path: true` is set:
- Gateway receives: `/petstore/pet/findByStatus?status=available`
- Backend receives: `/pet/findByStatus?status=available`

### 2. Query Parameters

Query parameters are **automatically forwarded** to the backend:
- `?status=available` → passed as-is
- `?status=available&limit=10` → passed as-is

### 3. Path Parameters

Path parameters are **automatically forwarded**:
- `/pet/123` → `123` is passed to backend as part of the path
- `/pet/:petId` pattern matches any value

## Deploy to Gravitee

### Using kubectl (with GKO installed)

```bash
kubectl apply -f api-definition.yaml
```

### Using Gravitee Console

1. Go to **APIs** → **+ Add API**
2. Select **Import from OpenAPI**
3. Use URL: `https://petstore.swagger.io/v2/swagger.json`
4. Configure the context path as `/petstore`
5. Publish the API

## Test the API

After deployment, test with curl:

```bash
# Find pets by status
curl "http://localhost:8082/petstore/pet/findByStatus?status=available"

# Get pet by ID
curl "http://localhost:8082/petstore/pet/1"

# Get store inventory
curl "http://localhost:8082/petstore/store/inventory"

# Add a new pet (POST)
curl -X POST "http://localhost:8082/petstore/pet" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 12345,
    "name": "TestDog",
    "status": "available"
  }'
```

## Advanced: Dynamic Parameter Handling

### Using Gravitee Expression Language (EL)

You can use EL expressions to manipulate parameters:

```yaml
# Access query parameters
{#request.params['status']}
{#request.params['limit'][0]}

# Access path parameters
{#request.paths[0]}  # First path segment after context path
{#request.paths[1]}  # Second path segment

# Access headers
{#request.headers['Authorization']}

# Full request path
{#request.path}

# Full request URI with query string
{#request.uri}
```

### Transform Query Parameters

To modify or add query parameters, use a **Transform Headers** policy:

```yaml
flows:
  - name: "Add Default Status"
    path-operator:
      path: /pet/findByStatus
      operator: EQUALS
    pre:
      - name: "Transform Query Params"
        policy: transform-queryparams
        configuration:
          addQueryParameters:
            - name: limit
              value: "100"
          # Or override existing
          overrideQueryParameters:
            - name: status
              value: "{#request.params['status'] ?: 'available'}"
```

### Transform Path

To modify the path before sending to backend:

```yaml
flows:
  - name: "Rewrite Path"
    path-operator:
      path: /v1/pets
      operator: STARTS_WITH
    pre:
      - name: "Rewrite to v2"
        policy: transform-headers
        configuration:
          scope: REQUEST
          overrideRequestPath: "/v2/pet{#request.path.substring(8)}"
```

## Common Patterns

### 1. Pass All Parameters (Default Behavior)

No special configuration needed - Gravitee forwards all query parameters and path segments automatically.

### 2. Add API Key to Backend

```yaml
pre:
  - name: "Add Backend API Key"
    policy: transform-headers
    configuration:
      addHeaders:
        - name: X-API-Key
          value: "your-backend-api-key"
```

### 3. Filter Query Parameters

```yaml
pre:
  - name: "Remove Sensitive Params"
    policy: transform-queryparams
    configuration:
      removeQueryParameters:
        - debug
        - internal_token
```

### 4. Map Query Parameter Names

```yaml
pre:
  - name: "Map Parameter Names"
    policy: transform-queryparams
    configuration:
      overrideQueryParameters:
        - name: pet_status  # Backend expects this name
          value: "{#request.params['status']}"
      removeQueryParameters:
        - status  # Remove original
```

## Troubleshooting

### Parameters Not Reaching Backend

1. Check if `strip_context_path` is set correctly
2. Verify the flow path pattern matches your request
3. Check for policies that might be modifying the request

### Debug with Logging

Enable request/response logging:

```yaml
flows:
  - name: "Debug Flow"
    pre:
      - name: "Log Request"
        policy: groovy
        configuration:
          script: |
            println "Request Path: " + request.path()
            println "Query Params: " + request.parameters()
            println "Headers: " + request.headers()
```

### Check Gateway Logs

```bash
kubectl logs deployment/gravitee-apim-gateway -n gravitee --tail=100
```

