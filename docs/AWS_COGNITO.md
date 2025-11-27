# AWS Cognito Authentication

This template supports AWS Cognito for JWT-based authentication.

## Configuration

Cognito can be configured using either environment variables or Docker secrets (recommended for production).

### Environment Variables

```bash
AWS_REGION=eu-central-1
COGNITO_USER_POOL_ID=eu-central-1_XXXXXXXXX
COGNITO_APP_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### Docker Secrets (Production)

For production deployments using Docker Swarm, configuration values are read from Docker secrets:

```yaml
environment:
  AWS_REGION: eu-central-1
  COGNITO_USER_POOL_ID_FILE: /run/secrets/YOUR_STACK_COGNITO_USER_POOL_ID
  COGNITO_APP_CLIENT_ID_FILE: /run/secrets/YOUR_STACK_COGNITO_APP_CLIENT_ID
  AWS_ACCESS_KEY_ID_FILE: /run/secrets/YOUR_STACK_AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY_FILE: /run/secrets/YOUR_STACK_AWS_SECRET_ACCESS_KEY
secrets:
  - YOUR_STACK_COGNITO_USER_POOL_ID
  - YOUR_STACK_COGNITO_APP_CLIENT_ID
  - YOUR_STACK_AWS_ACCESS_KEY_ID
  - YOUR_STACK_AWS_SECRET_ACCESS_KEY
```

## Settings API

The application provides getter methods in `app/api/settings.py` that automatically handle reading from either environment variables or Docker secret files:

```python
from api.settings import settings

# These methods check for _FILE variants first, then fall back to env vars
user_pool_id = settings.get_cognito_user_pool_id()
app_client_id = settings.get_cognito_app_client_id()
access_key_id = settings.get_aws_access_key_id()
secret_access_key = settings.get_aws_secret_access_key()
```

### Available Getter Methods

- `get_cognito_user_pool_id()` - Returns Cognito User Pool ID
- `get_cognito_app_client_id()` - Returns Cognito App Client ID
- `get_aws_access_key_id()` - Returns AWS Access Key ID (for admin operations)
- `get_aws_secret_access_key()` - Returns AWS Secret Access Key (for admin operations)

## JWT Token Verification

The template includes a FastAPI dependency for verifying Cognito-issued JWT tokens:

```python
from fastapi import Depends
from backend.auth_dependency import verify_jwt_token_dependency, get_user_id_from_token

@app.get("/protected")
async def protected_route(user_info = Depends(verify_jwt_token_dependency)):
    # user_info contains: sub, user_id, email, username, claims
    return {"message": f"Hello {user_info['username']}"}

# Or just get the user ID:
@app.get("/user-data")
async def user_data(user_id: str = Depends(get_user_id_from_token)):
    return {"user_id": user_id}
```

## Required Values

### Minimum Configuration

For JWT verification (most common use case):
- `AWS_REGION` - AWS region where your Cognito user pool is located
- `COGNITO_USER_POOL_ID` - Your Cognito User Pool ID
- `COGNITO_APP_CLIENT_ID` - Your Cognito App Client ID (optional if not validating audience)

### Admin Operations

If your application needs to perform Cognito admin operations (user management, etc.), also provide:
- `AWS_ACCESS_KEY_ID` - IAM user access key with Cognito permissions
- `AWS_SECRET_ACCESS_KEY` - IAM user secret access key

## How It Works

1. **JWT Verification Flow**:
   - Client sends request with `Authorization: Bearer <jwt-token>` header
   - Dependency fetches JWKS from Cognito
   - Token signature is verified using public keys
   - Token claims are validated (issuer, audience, expiry)
   - User information is extracted and returned

2. **Secret File Reading**:
   - Settings check if `*_FILE` environment variable is set
   - If file exists at that path, read and return the content
   - Otherwise, fall back to the direct environment variable
   - This allows seamless transition between local dev and production

## Security Notes

- **Never commit credentials to version control**
- Use Docker secrets in production deployments
- AWS credentials are only needed for admin operations (user management)
- JWT verification only requires public information (region, pool ID, client ID)
- The `AWS_REGION` remains as a plain environment variable (not sensitive)
- All other Cognito values are stored as Docker secrets in production

## Local Development

For local development, create a `.env` file:

```bash
# .env
AWS_REGION=eu-central-1
COGNITO_USER_POOL_ID=eu-central-1_XXXXXXXXX
COGNITO_APP_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
# Only if you need admin operations locally:
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret
```

## Deployment

When deploying with the swarm deployment scripts, Cognito configuration is handled automatically:

1. Run setup wizard or quick-start option 9
2. Provide your Cognito configuration values
3. Docker secrets are created automatically
4. Stack file is updated with secret references
5. Application reads secrets at runtime

See the swarm deployment documentation for details.
