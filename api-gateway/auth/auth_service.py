import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import secrets

security = HTTPBearer(auto_error=False)

class User(BaseModel):
    id: str
    email: str
    name: str
    tenant_id: str
    roles: List[str]
    permissions: List[str]
    is_active: bool
    last_login: Optional[datetime] = None

class Tenant(BaseModel):
    id: str
    name: str
    domain: str
    subscription_tier: str
    max_users: int
    max_resources: int
    features: List[str]
    is_active: bool
    created_at: datetime

class Permission:
    # Resource-level permissions
    VIEW_VIOLATIONS = "view:violations"
    MANAGE_VIOLATIONS = "manage:violations"
    VIEW_POLICIES = "view:policies"
    MANAGE_POLICIES = "manage:policies"
    VIEW_RESOURCES = "view:resources"
    MANAGE_RESOURCES = "manage:resources"
    VIEW_ATTACK_PATHS = "view:attack_paths"
    VIEW_COMPLIANCE = "view:compliance"
    MANAGE_COMPLIANCE = "manage:compliance"
    VIEW_CI_CD = "view:ci_cd"
    MANAGE_CI_CD = "manage:ci_cd"
    VIEW_ML = "view:ml"
    MANAGE_ML = "manage:ml"
    
    # System-level permissions
    MANAGE_USERS = "manage:users"
    MANAGE_TENANT = "manage:tenant"
    VIEW_AUDIT_LOG = "view:audit_log"
    EXPORT_DATA = "export:data"
    
    # Action permissions
    OVERRIDE_EVALUATIONS = "override:evaluations"
    SUPPRESS_VIOLATIONS = "suppress:violations"
    FORCE_REMEDIATION = "force:remediation"

class Role:
    # Built-in roles with predefined permissions
    SUPER_ADMIN = {
        "name": "super_admin",
        "description": "Full system access across all tenants",
        "permissions": [p for p in dir(Permission) if not p.startswith('_')]
    }
    
    TENANT_ADMIN = {
        "name": "tenant_admin",
        "description": "Full access within a tenant",
        "permissions": [
            Permission.VIEW_VIOLATIONS,
            Permission.MANAGE_VIOLATIONS,
            Permission.VIEW_POLICIES,
            Permission.MANAGE_POLICIES,
            Permission.VIEW_RESOURCES,
            Permission.MANAGE_RESOURCES,
            Permission.VIEW_ATTACK_PATHS,
            Permission.VIEW_COMPLIANCE,
            Permission.MANAGE_COMPLIANCE,
            Permission.VIEW_CI_CD,
            Permission.MANAGE_CI_CD,
            Permission.VIEW_ML,
            Permission.MANAGE_ML,
            Permission.MANAGE_USERS,
            Permission.MANAGE_TENANT,
            Permission.VIEW_AUDIT_LOG,
            Permission.EXPORT_DATA,
            Permission.OVERRIDE_EVALUATIONS,
            Permission.SUPPRESS_VIOLATIONS,
            Permission.FORCE_REMEDIATION
        ]
    }
    
    SECURITY_ENGINEER = {
        "name": "security_engineer",
        "description": "Security operations and policy management",
        "permissions": [
            Permission.VIEW_VIOLATIONS,
            Permission.MANAGE_VIOLATIONS,
            Permission.VIEW_POLICIES,
            Permission.MANAGE_POLICIES,
            Permission.VIEW_RESOURCES,
            Permission.VIEW_ATTACK_PATHS,
            Permission.VIEW_COMPLIANCE,
            Permission.VIEW_CI_CD,
            Permission.VIEW_ML,
            Permission.OVERRIDE_EVALUATIONS,
            Permission.SUPPRESS_VIOLATIONS,
            Permission.FORCE_REMEDIATION
        ]
    }
    
    PLATFORM_ENGINEER = {
        "name": "platform_engineer",
        "description": "Infrastructure and CI/CD management",
        "permissions": [
            Permission.VIEW_VIOLATIONS,
            Permission.VIEW_POLICIES,
            Permission.VIEW_RESOURCES,
            Permission.MANAGE_RESOURCES,
            Permission.VIEW_CI_CD,
            Permission.MANAGE_CI_CD,
            Permission.OVERRIDE_EVALUATIONS
        ]
    }
    
    READ_ONLY = {
        "name": "read_only",
        "description": "View-only access",
        "permissions": [
            Permission.VIEW_VIOLATIONS,
            Permission.VIEW_POLICIES,
            Permission.VIEW_RESOURCES,
            Permission.VIEW_ATTACK_PATHS,
            Permission.VIEW_COMPLIANCE,
            Permission.VIEW_CI_CD,
            Permission.VIEW_ML
        ]
    }

class AuthService:
    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256"):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        
    def create_access_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token for user"""
        to_encode = {
            "sub": user.id,
            "email": user.email,
            "tenant_id": user.tenant_id,
            "roles": user.roles,
            "permissions": user.permissions
        }
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=1)
            
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            self.jwt_secret, 
            algorithm=self.jwt_algorithm
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def create_api_key(self, user_id: str, tenant_id: str, permissions: List[str]) -> Tuple[str, str]:
        """Create API key for programmatic access"""
        # Generate key ID and secret
        key_id = f"sk_{secrets.token_urlsafe(16)}"
        key_secret = secrets.token_urlsafe(32)
        
        # Hash secret for storage (not implemented here)
        key_hash = self._hash_secret(key_secret)
        
        # Return both key_id and secret (secret only shown once)
        return key_id, key_secret
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        # This would query a database in production
        # For MVP, we'll use a mock implementation
        mock_users = {
            "admin@skysentinel.io": {
                "id": "user_001",
                "email": "admin@skysentinel.io",
                "name": "Admin User",
                "tenant_id": "tenant_001",
                "password_hash": "$2b$12$...",  # Hashed password
                "roles": ["tenant_admin"],
                "permissions": Role.TENANT_ADMIN["permissions"],
                "is_active": True
            }
        }
        
        if email in mock_users:
            user_data = mock_users[email]
            # Verify password (simplified for MVP)
            if self._verify_password(password, user_data["password_hash"]):
                return User(**{k: v for k, v in user_data.items() if k != "password_hash"})
        
        return None
    
    def authorize_user(self, user: User, permission: str, resource_id: Optional[str] = None) -> bool:
        """Check if user has permission to access resource"""
        # Check if user has permission
        if permission not in user.permissions:
            return False
        
        # For tenant-scoped resources, verify user belongs to same tenant
        if resource_id and hasattr(resource_id, 'tenant_id'):
            # This would check if resource belongs to user's tenant
            pass
        
        return True
    
    def get_user_by_api_key(self, key_id: str) -> Optional[User]:
        """Get user by API key ID"""
        # This would query database for API key
        # For MVP, return mock user
        return User(
            id="api_user_001",
            email="api@skysentinel.io",
            name="API User",
            tenant_id="tenant_001",
            roles=["api_user"],
            permissions=Role.SECURITY_ENGINEER["permissions"],
            is_active=True
        )
    
    def _hash_secret(self, secret: str) -> str:
        """Hash secret for storage"""
        import hashlib
        return hashlib.sha256(secret.encode()).hexdigest()
    
    def _verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash"""
        # Simplified for MVP
        return True

# FastAPI Dependency for Authentication
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Dependency to get current authenticated user"""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_service = AuthService(jwt_secret="your-secret-key")
    
    try:
        # Check if it's a JWT token
        if credentials.scheme == "Bearer" and len(credentials.credentials) > 100:
            # Assume JWT token
            payload = auth_service.verify_token(credentials.credentials)
            
            # Create user object from token payload
            user = User(
                id=payload.get("sub"),
                email=payload.get("email"),
                name=payload.get("name", ""),
                tenant_id=payload.get("tenant_id"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                is_active=True
            )
            
            return user
            
        # Check if it's an API key
        elif credentials.scheme == "Bearer" and credentials.credentials.startswith("sk_"):
            # Assume API key
            user = auth_service.get_user_by_api_key(credentials.credentials)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            return user
            
        else:
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
            
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# FastAPI Dependency for Authorization
async def require_permission(permission: str):
    """Dependency factory for requiring specific permission"""
    async def permission_dependency(
        current_user: User = Depends(get_current_user)
    ):
        auth_service = AuthService(jwt_secret="your-secret-key")
        
        if not auth_service.authorize_user(current_user, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission}"
            )
        
        return current_user
    
    return permission_dependency

# Example usage in FastAPI routes
from fastapi import APIRouter

router = APIRouter()

@router.get("/violations")
async def get_violations(
    current_user: User = Depends(require_permission(Permission.VIEW_VIOLATIONS))
):
    """Get violations (requires VIEW_VIOLATIONS permission)"""
    return {"message": "Access granted to violations"}

@router.post("/policies")
async def create_policy(
    policy_data: Dict,
    current_user: User = Depends(require_permission(Permission.MANAGE_POLICIES))
):
    """Create policy (requires MANAGE_POLICIES permission)"""
    return {"message": "Policy created"}
