# Packages Endpoint Documentation

The `/packages` endpoints provide information about installed Python packages in the running application. These endpoints are **secured with API key authentication** to prevent unauthorized access to potentially sensitive system information.

## Security

All `/packages` endpoints require authentication via the `X-API-Key` header.

### Configuration

Set the `ADMIN_API_KEY` in your `.env` file:

```bash
ADMIN_API_KEY=your-secure-random-key-here
```

**Security Best Practices:**

1. **Generate a strong key** for production:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Never commit** the actual API key to version control

3. **Use different keys** for different environments (dev, staging, production)

4. **Rotate keys regularly** in production environments

## Endpoints

### 1. List All Packages

**GET** `/packages/list`

Lists all installed Python packages with their versions.

**Headers:**
```
X-API-Key: your-api-key-here
```

**Response:**
```json
{
  "total_packages": 36,
  "python_version": "3.13.0",
  "packages": [
    {
      "name": "fastapi",
      "version": "0.121.0"
    },
    {
      "name": "uvicorn",
      "version": "0.38.0"
    }
  ]
}
```

**Example (PowerShell):**
```powershell
$headers = @{
    "X-API-Key" = "dev-key-12345"
}
Invoke-RestMethod -Uri "http://localhost:8081/packages/list" -Headers $headers
```

**Example (curl):**
```bash
curl -H "X-API-Key: dev-key-12345" http://localhost:8081/packages/list
```

### 2. Get Package Details

**GET** `/packages/info/{package_name}`

Get detailed information about a specific package.

**Headers:**
```
X-API-Key: your-api-key-here
```

**Response:**
```json
{
  "name": "fastapi",
  "version": "0.121.0",
  "summary": "FastAPI framework, high performance, easy to learn...",
  "home_page": "https://github.com/tiangolo/fastapi",
  "author": "Sebastián Ramírez",
  "license": "MIT",
  "requires_python": ">=3.8",
  "dependencies": [
    "starlette>=0.37.2",
    "pydantic>=1.7.4",
    "typing-extensions>=4.8.0"
  ]
}
```

**Example (PowerShell):**
```powershell
$headers = @{
    "X-API-Key" = "dev-key-12345"
}
Invoke-RestMethod -Uri "http://localhost:8081/packages/info/fastapi" -Headers $headers
```

**Example (curl):**
```bash
curl -H "X-API-Key: dev-key-12345" http://localhost:8081/packages/info/fastapi
```

## Error Responses

### Missing API Key (401)
```json
{
  "detail": "Missing API key. Please provide X-API-Key header."
}
```

### Invalid API Key (403)
```json
{
  "detail": "Invalid API key"
}
```

### API Key Not Configured (503)
```json
{
  "detail": "Admin API key not configured. Please set ADMIN_API_KEY in environment variables."
}
```

### Package Not Found (200 with error field)
```json
{
  "error": "Package 'nonexistent' not found",
  "available_packages": ["fastapi", "uvicorn", "..."]
}
```

## Use Cases

1. **Verify PDM Installation**: Check if packages installed by PDM match expectations
2. **Dependency Auditing**: List all dependencies for security audits
3. **Version Verification**: Confirm specific package versions in production
4. **Troubleshooting**: Debug dependency-related issues by checking installed versions

## Integration with PDM

These endpoints show the actual installed packages in the running container, which should match your `pdm.lock` file. Use this to verify that:

- All dependencies from `pdm.lock` are installed
- Package versions match what PDM specified
- No unexpected packages are present

Compare the API output with:
```bash
# Inside the container
pdm list
```

## Security Considerations

**Why is this endpoint secured?**

1. **System Information Disclosure**: Package lists can reveal:
   - Technology stack and versions
   - Potential vulnerabilities in specific versions
   - Internal dependencies and architecture

2. **Attack Surface**: Knowing exact package versions helps attackers:
   - Target known CVEs in specific versions
   - Craft exploits for discovered vulnerabilities
   - Plan more sophisticated attacks

3. **Best Practice**: Administrative/diagnostic endpoints should always require authentication

**Additional Security Measures:**

- Consider IP whitelisting for production
- Use HTTPS in production (never send API keys over HTTP)
- Monitor API key usage and failed authentication attempts
- Implement rate limiting for these endpoints
- Consider using more sophisticated auth (JWT, OAuth2) for production
