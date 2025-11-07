from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from services.report_service import ReportService
from typing import List, Optional, Dict, Any
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta, date
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from services.ai_service import AIAssistantService
from sqlalchemy import or_
import re

from database import engine, get_db, Base
import models
from services.audit_service import AuditService
from services.email_service import EmailService

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create tables with error handling
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logging.error(f"Failed to create database tables: {e}")
    raise

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not SECRET_KEY or SECRET_KEY == 'your-secret-key-change-in-production':
    logging.warning("⚠️  Using default JWT secret key! Change this in production!")
    SECRET_KEY = 'your-secret-key-change-in-production'

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="License Tracker API")
api_router = APIRouter(prefix="/api")

# ============ ROLE CONSTANTS (✅ ADDED FOR RBAC) ============
ADMIN = "ADMIN"
ENGINEER = "ENGINEER"
AUDITOR = "AUDITOR"

# ============ IP VALIDATION UTILITY ============

def validate_ip_address(ip: str) -> bool:
    """Validate IP address format (xxx.xxx.xxx.xxx with each octet 0-255)"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    if not re.match(pattern, ip):
        return False
    
    octets = ip.split('.')
    for octet in octets:
        if int(octet) < 0 or int(octet) > 255:
            return False
    
    return True

# ============ PYDANTIC MODELS ============

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: models.UserRole = models.UserRole.ENGINEER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    email: str
    name: str
    role: models.UserRole
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class VendorCreate(BaseModel):
    vendor_name: str
    support_email: Optional[str] = None

class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    vendor_id: str
    vendor_name: str
    support_email: Optional[str]
    created_at: datetime

class DeviceCreate(BaseModel):
    device_id: str
    type: str
    ip_address: str
    location: str
    model: Optional[str] = None
    status: models.DeviceStatus = models.DeviceStatus.ACTIVE

class DeviceUpdate(BaseModel):
    type: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    model: Optional[str] = None
    status: Optional[models.DeviceStatus] = None

class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    device_id: str
    type: str
    ip_address: str
    location: str
    model: Optional[str]
    status: models.DeviceStatus
    created_at: datetime
    assignments: List['AssignmentResponse'] = []

class LicenseCreate(BaseModel):
    license_key: str
    software_name: str
    vendor_id: str
    valid_from: date
    valid_to: date
    license_type: models.LicenseType
    max_usage: int
    notes: Optional[str] = None

class LicenseUpdate(BaseModel):
    software_name: Optional[str] = None
    vendor_id: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    license_type: Optional[models.LicenseType] = None
    max_usage: Optional[int] = None
    notes: Optional[str] = None

class LicenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    license_key: str
    software_name: str
    vendor_id: str
    valid_from: date
    valid_to: date
    license_type: models.LicenseType
    max_usage: int
    notes: Optional[str]
    created_at: datetime

class AssignmentCreate(BaseModel):
    license_key: str
    device_id: str
    assigned_by: str

class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    assignment_id: str
    license_key: str
    device_id: str
    assigned_by: str
    assigned_at: datetime

class AlertsResponse(BaseModel):
    expiring_licenses: List[dict]
    overused_licenses: List[dict]
    devices_at_risk: List[dict]

class DashboardSummary(BaseModel):
    total_devices: int
    active_devices: int
    total_licenses: int
    expiring_licenses_count: int
    overused_licenses_count: int
    devices_at_risk_count: int
    critical_alerts: int

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    log_id: str
    user_id: str
    entity_type: str
    entity_id: str
    action: str
    timestamp: datetime
    details: Optional[str]
    
class AIQueryRequest(BaseModel):
    query: str
    conversation_history: Optional[List[Dict]] = None
    
class SoftwareVersionCreate(BaseModel):
    device_id: str
    software_name: str
    current_version: str
    latest_version: Optional[str] = None
    status: str = "UP_TO_DATE"

class SoftwareVersionUpdate(BaseModel):
    software_name: Optional[str] = None
    current_version: Optional[str] = None
    latest_version: Optional[str] = None
    status: Optional[str] = None

class SoftwareVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    sv_id: str
    device_id: str
    software_name: str
    current_version: str
    latest_version: Optional[str]
    status: str
    last_checked: Optional[date]

class AIQueryResponse(BaseModel):
    success: bool
    query: str
    response: str
    tools_used: Optional[List[str]] = None
    tokens_used: Optional[int] = None
    error: Optional[str] = None

class AISuggestionsResponse(BaseModel):
    suggestions: List[str]

# ============ AUTH UTILITIES ============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# ============ AUTH ROUTES ============

@api_router.post("/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    user = models.User(
        user_id=str(uuid.uuid4()),
        email=user_data.email,
        name=user_data.name,
        password_hash=hashed_password,
        role=user_data.role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    audit = AuditService(db)
    audit.log_action(
        user_id=user.user_id,  # New user is logging their own creation
        entity_type="USER",
        entity_id=user.user_id,
        action="CREATE",
        details=f"User {user.name} ({user.email}) registered with role {user.role.value}"
    )
    
    return user

@api_router.post("/auth/login", response_model=Token)
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": user.user_id, "role": user.role.value})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

# ============ VENDOR ROUTES (✅ RBAC ADDED) ============

@api_router.post("/vendors", response_model=VendorResponse)
async def create_vendor(vendor_data: VendorCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ✅ RBAC: Only ADMIN can add vendors
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can add vendors")
    
    vendor = models.Vendor(
        vendor_id=str(uuid.uuid4()),
        **vendor_data.model_dump()
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="VENDOR",
        entity_id=vendor.vendor_id,
        action="CREATE",
        details=f"Created vendor {vendor.vendor_name}"
    )

    return vendor

@api_router.get("/vendors", response_model=List[VendorResponse])
async def get_vendors(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ✅ All roles can view vendors
    vendors = db.query(models.Vendor).all()
    return vendors

@api_router.put("/vendors/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: str,
    vendor_data: VendorCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN can edit vendors
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can edit vendors")
    
    vendor = db.query(models.Vendor).filter(models.Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    vendor.vendor_name = vendor_data.vendor_name
    vendor.support_email = vendor_data.support_email
    
    db.commit()
    db.refresh(vendor)
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="VENDOR",
        entity_id=vendor.vendor_id,
        action="UPDATE",
        details=f"Updated vendor {vendor.vendor_name}"
    )
    return vendor

@api_router.delete("/vendors/{vendor_id}")
async def delete_vendor(
    vendor_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN can delete vendors
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can delete vendors")
    
    vendor = db.query(models.Vendor).filter(models.Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    vendor_name = vendor.vendor_name
    db.delete(vendor)
    db.commit()
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="VENDOR",
        entity_id=vendor_id,
        action="DELETE",
        details=f"Deleted vendor {vendor_name}"
    )
    return {"message": "Vendor deleted successfully"}

# ============ DEVICE ROUTES (✅ RBAC ADDED) ============

@api_router.post("/devices/validate-ip")
async def validate_device_ip(
    request: dict,
    current_user: models.User = Depends(get_current_user)
):
    """Validate IP address for real-time frontend feedback"""
    ip_address = request.get("ip_address")
    
    if not ip_address:
        return {"valid": False, "message": "IP address required"}
    
    is_valid = validate_ip_address(ip_address)
    
    if is_valid:
        return {
            "valid": True,
            "message": f"Valid IP address: {ip_address}"
        }
    else:
        return {
            "valid": False,
            "message": "Invalid IP format. Expected: xxx.xxx.xxx.xxx (0-255)"
        }

@api_router.post("/devices", response_model=DeviceResponse)
async def create_device(device_data: DeviceCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ✅ RBAC: Only ADMIN and ENGINEER can add devices
    if current_user.role.value not in [ADMIN, ENGINEER]:
        raise HTTPException(status_code=403, detail="Only Admin and Engineer can add devices")
    
    if not validate_ip_address(device_data.ip_address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid IP address: {device_data.ip_address}. Expected format: xxx.xxx.xxx.xxx (0-255 per octet)"
        )
    
    existing = db.query(models.Device).filter(models.Device.device_id == device_data.device_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID already exists"
        )
    
    device = models.Device(**device_data.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    audit = AuditService(db)
    audit.log_action(
    user_id=current_user.user_id,
    entity_type="DEVICE",
    entity_id=device.device_id,
    action="CREATE",
    details=f"Created device {device.device_id} ({device.type})"
    )

    return device

@api_router.get("/devices", response_model=List[DeviceResponse])
async def get_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    location: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[models.DeviceStatus] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view devices
    from sqlalchemy.orm import joinedload
    
    query = db.query(models.Device).options(joinedload(models.Device.assignments).joinedload(models.Assignment.license))
    
    if location:
        query = query.filter(models.Device.location.ilike(f"%{location}%"))
    if type:
        query = query.filter(models.Device.type.ilike(f"%{type}%"))
    if status:
        query = query.filter(models.Device.status == status)
    
    devices = query.offset(skip).limit(limit).all()
    return devices

@api_router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ✅ All roles can view individual device
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@api_router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_data: DeviceUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN and ENGINEER can edit devices
    if current_user.role.value not in [ADMIN, ENGINEER]:
        raise HTTPException(status_code=403, detail="Only Admin and Engineer can edit devices")
    
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    update_data = device_data.model_dump(exclude_unset=True)
    
    if 'ip_address' in update_data:
        if not validate_ip_address(update_data['ip_address']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid IP address: {update_data['ip_address']}"
            )
    
    for key, value in update_data.items():
        setattr(device, key, value)
    
    db.commit()
    db.refresh(device)
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="DEVICE",
        entity_id=device.device_id,
        action="UPDATE",
        details=f"Updated device {device.device_id}"
    )

    return device

@api_router.delete("/devices/{device_id}")
async def delete_device(device_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ✅ RBAC: Only ADMIN can delete devices
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can delete devices")
    
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device_info = f"{device.device_id} ({device.type})"
    db.delete(device)
    db.commit()
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="DEVICE",
        entity_id=device_id,
        action="DELETE",
        details=f"Deleted device {device_info}"
    )

    return {"message": "Device deleted successfully"}

# ============ LICENSE ROUTES (✅ RBAC ADDED) ============

@api_router.post("/licenses", response_model=LicenseResponse)
async def create_license(license_data: LicenseCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ✅ RBAC: Only ADMIN can add licenses
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can add licenses")
    
    existing = db.query(models.License).filter(models.License.license_key == license_data.license_key).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License key already exists"
        )
    
    vendor = db.query(models.Vendor).filter(models.Vendor.vendor_id == license_data.vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor not found"
        )
    
    license = models.License(**license_data.model_dump())
    db.add(license)
    db.commit()
    db.refresh(license)
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="LICENSE",
        entity_id=license.license_key,
        action="CREATE",
        details=f"Created license {license.license_key} for {license.software_name}"
    )
    return license

@api_router.get("/licenses", response_model=List[LicenseResponse])
async def get_licenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    vendor_id: Optional[str] = None,
    software_name: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view licenses
    query = db.query(models.License)
    
    if vendor_id:
        query = query.filter(models.License.vendor_id == vendor_id)
    if software_name:
        query = query.filter(models.License.software_name.ilike(f"%{software_name}%"))
    
    licenses = query.offset(skip).limit(limit).all()
    return licenses

@api_router.get("/licenses/{license_key}", response_model=LicenseResponse)
async def get_license(license_key: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ✅ All roles can view individual license
    license = db.query(models.License).filter(models.License.license_key == license_key).first()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    return license

@api_router.put("/licenses/{license_key}", response_model=LicenseResponse)
async def update_license(
    license_key: str,
    license_data: LicenseUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN can edit licenses
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can edit licenses")
    
    license = db.query(models.License).filter(models.License.license_key == license_key).first()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    
    update_data = license_data.model_dump(exclude_unset=True)
    
    if 'vendor_id' in update_data:
        vendor = db.query(models.Vendor).filter(models.Vendor.vendor_id == update_data['vendor_id']).first()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor not found"
            )
    
    for key, value in update_data.items():
        setattr(license, key, value)
    
    db.commit()
    db.refresh(license)
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="LICENSE",
        entity_id=license.license_key,
        action="UPDATE",
        details=f"Updated license {license.license_key}"
    )
    return license

@api_router.delete("/licenses/{license_key}")
async def delete_license(license_key: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ✅ RBAC: Only ADMIN can delete licenses
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can delete licenses")
    
    license = db.query(models.License).filter(models.License.license_key == license_key).first()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    license_info = f"{license.license_key} ({license.software_name})"
    db.delete(license)
    db.commit()
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="LICENSE",
        entity_id=license_key,
        action="DELETE",
        details=f"Deleted license {license_info}"
    )
    return {"message": "License deleted successfully"}

# ============ ASSIGNMENT ROUTES (✅ RBAC ADDED) ============

@api_router.post("/assignments", response_model=AssignmentResponse)
async def create_assignment(
    assignment_data: AssignmentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN and ENGINEER can assign licenses
    if current_user.role.value not in [ADMIN, ENGINEER]:
        raise HTTPException(status_code=403, detail="Only Admin and Engineer can assign licenses")
    
    from services.assignment_service import AssignmentService
    
    service = AssignmentService(db)
    assignment = service.create_assignment(
        license_key=assignment_data.license_key,
        device_id=assignment_data.device_id,
        assigned_by=assignment_data.assigned_by
    )
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="ASSIGNMENT",
        entity_id=str(assignment.assignment_id),
        action="ASSIGN",
        details=f"Assigned license {assignment.license_key} to device {assignment.device_id}"
    )
    return assignment

@api_router.get("/assignments/by-device/{device_id}", response_model=List[AssignmentResponse])
async def get_device_assignments(
    device_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view assignments
    from services.assignment_service import AssignmentService
    service = AssignmentService(db)
    assignments = service.get_assignments_by_device(device_id)
    return assignments

@api_router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN and ENGINEER can unassign licenses
    if current_user.role.value not in [ADMIN, ENGINEER]:
        raise HTTPException(status_code=403, detail="Only Admin and Engineer can unassign licenses")
    
    from services.assignment_service import AssignmentService
    assignment = db.query(models.Assignment).filter(models.Assignment.assignment_id == assignment_id).first()
    if assignment:
        assignment_info = f"License {assignment.license_key} from device {assignment.device_id}"
    service = AssignmentService(db)
    result = service.delete_assignment(assignment_id)
    if assignment:
        audit = AuditService(db)
        audit.log_action(
            user_id=current_user.user_id,
            entity_type="ASSIGNMENT",
            entity_id=assignment_id,
            action="UNASSIGN",
            details=f"Unassigned {assignment_info}"
        )
    return result

@api_router.get("/licenses/{license_key}/utilization")
async def get_license_utilization(
    license_key: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view utilization
    from services.assignment_service import AssignmentService
    service = AssignmentService(db)
    utilization = service.get_license_utilization(license_key)
    return utilization

# ============ ALERTS ROUTES ============

@api_router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    days: int = Query(30, ge=1, le=365),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view alerts
    from services.alert_service import AlertService
    service = AlertService(db)
    
    return {
        "expiring_licenses": service.get_expiring_licenses(days),
        "overused_licenses": service.get_overused_licenses(),
        "devices_at_risk": service.get_devices_at_risk()
    }

@api_router.get("/alerts/expiring", response_model=List[dict])
async def get_expiring_licenses(
    days: int = Query(30, ge=1, le=365),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view expiring licenses
    from services.alert_service import AlertService
    service = AlertService(db)
    return service.get_expiring_licenses(days)

@api_router.get("/alerts/overused", response_model=List[dict])
async def get_overused_licenses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view overused licenses
    from services.alert_service import AlertService
    service = AlertService(db)
    return service.get_overused_licenses()
@api_router.post("/alerts/send-email")
async def send_email_alerts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger email alerts for expiring and overused licenses
    Only ADMIN and ENGINEER can send alerts
    """
    # RBAC check
    if current_user.role.value not in [ADMIN, ENGINEER]:
        raise HTTPException(status_code=403, detail="Only Admin and Engineer can send email alerts")
    
    from services.alert_service import AlertService
    email_service = EmailService()
    
    if not email_service.enabled:
        return {
            "success": False,
            "message": "Email service not configured. Please set SMTP settings in .env file.",
            "emails_sent": 0
        }
    
    # Get admin emails
    admin_users = db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).all()
    admin_emails = [user.email for user in admin_users]
    
    if not admin_emails:
        return {
            "success": False,
            "message": "No admin users found to send alerts to",
            "emails_sent": 0
        }
    
    alert_service = AlertService(db)
    emails_sent = 0
    
    # Send expiring license alerts
    expiring_licenses = alert_service.get_expiring_licenses(30)
    for license_data in expiring_licenses:
        if email_service.send_license_expiry_alert(license_data, admin_emails):
            emails_sent += 1
    
    # Send overused license alerts
    overused_licenses = alert_service.get_overused_licenses()
    for license_data in overused_licenses:
        if email_service.send_overused_license_alert(license_data, admin_emails):
            emails_sent += 1
    
    return {
        "success": True,
        "message": f"Email alerts sent to {len(admin_emails)} admin(s)",
        "emails_sent": emails_sent,
        "recipients": admin_emails
    }

@api_router.post("/alerts/send-daily-summary")
async def send_daily_summary_email(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send daily summary email
    Only ADMIN can send daily summaries
    """
    # RBAC check
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can send daily summaries")
    
    from services.alert_service import AlertService
    email_service = EmailService()
    
    if not email_service.enabled:
        return {
            "success": False,
            "message": "Email service not configured. Please set SMTP settings in .env file."
        }
    
    # Get admin emails
    admin_users = db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).all()
    admin_emails = [user.email for user in admin_users]
    
    if not admin_emails:
        return {
            "success": False,
            "message": "No admin users found to send summary to"
        }
    
    # Get summary data
    alert_service = AlertService(db)
    dashboard = alert_service.get_dashboard_summary()
    
    summary_data = {
        "total_devices": dashboard.total_devices,
        "active_licenses": dashboard.total_licenses,
        "expiring_soon": dashboard.expiring_licenses_count,
        "overused": dashboard.overused_licenses_count
    }
    
    success = email_service.send_daily_summary(summary_data, admin_emails)
    
    return {
        "success": success,
        "message": f"Daily summary sent to {len(admin_emails)} admin(s)" if success else "Failed to send daily summary",
        "recipients": admin_emails if success else []
    }

@api_router.get("/alerts/email-status")
async def get_email_status(
    current_user: models.User = Depends(get_current_user)
):
    """Check if email service is configured"""
    email_service = EmailService()
    
    return {
        "configured": email_service.enabled,
        "smtp_host": email_service.smtp_host if email_service.enabled else "Not configured",
        "smtp_user": email_service.smtp_user if email_service.enabled else "Not configured",
        "message": "Email service is ready" if email_service.enabled else "Configure SMTP settings in .env to enable email alerts"
    }


@api_router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view dashboard
    from services.alert_service import AlertService
    service = AlertService(db)
    return service.get_dashboard_summary()

# ============ AUDIT LOG ROUTES (✅ RBAC ADDED) ============

@api_router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN and AUDITOR can view audit logs
    if current_user.role.value not in [ADMIN, AUDITOR]:
        raise HTTPException(status_code=403, detail="Only Admin and Auditor can view audit logs")
    
    query = db.query(models.AuditLog)
    
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(models.AuditLog.entity_id == entity_id)
    
    logs = query.order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs

# ============ HEALTH CHECK ============

@api_router.get("/")
async def root():
    return {"message": "License Tracker API", "version": "Sprint 3 - Complete with RBAC"}

@api_router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

# ============ REPORTS ROUTES ============

@api_router.get("/reports/license-compliance")
async def get_license_compliance_report(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view reports
    service = ReportService(db)
    return service.generate_license_compliance_report()

@api_router.get("/reports/device-inventory")
async def get_device_inventory_report(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view reports
    service = ReportService(db)
    return service.generate_device_inventory_report()

@api_router.get("/reports/vendor-analysis")
async def get_vendor_analysis_report(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view reports
    service = ReportService(db)
    return service.generate_vendor_analysis_report()

@api_router.get("/reports/assignment-history")
async def get_assignment_history_report(
    days: int = Query(30, ge=1, le=365),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view reports
    service = ReportService(db)
    return service.generate_assignment_history_report(days)

@api_router.get("/reports/audit-logs")
async def get_audit_log_report(
    days: int = Query(7, ge=1, le=90),
    entity_type: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view reports
    service = ReportService(db)
    return service.generate_audit_log_report(days, entity_type)

@api_router.get("/reports/utilization-trends")
async def get_utilization_trends(
    days: int = Query(30, ge=7, le=365),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view reports
    service = ReportService(db)
    return service.get_utilization_trends(days)

# ============ EXPORT ROUTES ============

@api_router.get("/export/licenses")
async def export_licenses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can export
    service = ReportService(db)
    csv_data = service.export_licenses_to_csv()
    
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=licenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@api_router.get("/export/devices")
async def export_devices(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can export
    service = ReportService(db)
    csv_data = service.export_devices_to_csv()
    
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@api_router.get("/export/assignments")
async def export_assignments(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can export
    service = ReportService(db)
    csv_data = service.export_assignments_to_csv()
    
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

# ============ AI ASSISTANT ROUTES ============

@api_router.post("/ai/query", response_model=AIQueryResponse)
async def process_ai_query(
    request: AIQueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can use AI assistant
    try:
        service = AIAssistantService(db)
        result = service.process_query(
            user_query=request.query,
            conversation_history=request.conversation_history or []
        )
        return AIQueryResponse(**result)
    
    except Exception as e:
        logging.error(f"AI query error: {str(e)}")
        return AIQueryResponse(
            success=False,
            query=request.query,
            response="I encountered an error processing your request. Please try again.",
            error=str(e)
        )

@api_router.get("/ai/suggestions", response_model=AISuggestionsResponse)
async def get_ai_suggestions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can get AI suggestions
    service = AIAssistantService(db)
    suggestions = service.get_suggested_queries()
    return AISuggestionsResponse(suggestions=suggestions)

@api_router.get("/ai/health")
async def check_ai_health(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can check AI health
    try:
        service = AIAssistantService(db)
        tools = service.get_available_tools()
        
        return {
            "status": "healthy" if tools else "degraded",
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
            "mcp_tools_available": len(tools),
            "tools": [tool["function"]["name"] for tool in tools]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ============ SOFTWARE VERSION ROUTES (✅ RBAC ADDED) ============

@api_router.post("/software-versions", response_model=SoftwareVersionResponse)
async def create_software_version(
    version_data: SoftwareVersionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN and ENGINEER can add software versions
    if current_user.role.value not in [ADMIN, ENGINEER]:
        raise HTTPException(status_code=403, detail="Only Admin and Engineer can add software versions")
    
    device = db.query(models.Device).filter(models.Device.device_id == version_data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    valid_statuses = ["UP_TO_DATE", "OUTDATED", "CRITICAL"]
    if version_data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")
    
    version = models.SoftwareVersion(
        sv_id=str(uuid.uuid4()),
        **version_data.model_dump()
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="SOFTWARE_VERSION",
        entity_id=version.sv_id,
        action="CREATE",
        details=f"Added {version.software_name} v{version.current_version} to device {version.device_id}"
    )
    return version

@api_router.get("/software-versions/device/{device_id}", response_model=List[SoftwareVersionResponse])
async def get_device_software_versions(
    device_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view software versions
    versions = db.query(models.SoftwareVersion).filter(
        models.SoftwareVersion.device_id == device_id
    ).all()
    return versions

@api_router.get("/software-versions", response_model=List[SoftwareVersionResponse])
async def get_all_software_versions(
    status: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view software versions
    query = db.query(models.SoftwareVersion)
    
    if status:
        valid_statuses = ["UP_TO_DATE", "OUTDATED", "CRITICAL"]
        if status.upper() not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")
        query = query.filter(models.SoftwareVersion.status == status.upper())
    
    versions = query.all()
    return versions

@api_router.put("/software-versions/{sv_id}", response_model=SoftwareVersionResponse)
async def update_software_version(
    sv_id: str,
    version_data: SoftwareVersionUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN and ENGINEER can edit software versions
    if current_user.role.value not in [ADMIN, ENGINEER]:
        raise HTTPException(status_code=403, detail="Only Admin and Engineer can edit software versions")
    
    version = db.query(models.SoftwareVersion).filter(models.SoftwareVersion.sv_id == sv_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Software version not found")
    
    update_data = version_data.model_dump(exclude_unset=True)
    
    if 'status' in update_data:
        valid_statuses = ["UP_TO_DATE", "OUTDATED", "CRITICAL"]
        if update_data['status'] not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")
    
    for key, value in update_data.items():
        setattr(version, key, value)
    
    version.last_checked = date.today()
    
    db.commit()
    db.refresh(version)
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="SOFTWARE_VERSION",
        entity_id=version.sv_id,
        action="UPDATE",
        details=f"Updated {version.software_name} on device {version.device_id}"
    )
    return version

@api_router.delete("/software-versions/{sv_id}")
async def delete_software_version(
    sv_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN can delete software versions
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can delete software versions")
    
    version = db.query(models.SoftwareVersion).filter(models.SoftwareVersion.sv_id == sv_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Software version not found")
    version_info = f"{version.software_name} on device {version.device_id}"
    db.delete(version)
    db.commit()
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="SOFTWARE_VERSION",
        entity_id=sv_id,
        action="DELETE",
        details=f"Deleted software version {version_info}"
    )
    return {"message": "Software version deleted successfully"}

@api_router.get("/software-versions/outdated-count")
async def get_outdated_count(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ All roles can view count
    outdated = db.query(models.SoftwareVersion).filter(
        models.SoftwareVersion.status == "OUTDATED"
    ).count()
    
    critical = db.query(models.SoftwareVersion).filter(
        models.SoftwareVersion.status == "CRITICAL"
    ).count()
    
    return {
        "outdated": outdated,
        "critical": critical,
        "total": outdated + critical
    }

# ============ USER MANAGEMENT ROUTES (✅ RBAC ADDED) ============

@api_router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN can view users
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can view users")
    
    users = db.query(models.User).all()
    return users

@api_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN can view individual users
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can view users")
    
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN can edit users
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can edit users")
    
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.email = user_data.email
    user.name = user_data.name
    user.role = user_data.role
    
    if user_data.password:
        user.password_hash = get_password_hash(user_data.password)
    
    db.commit()
    db.refresh(user)
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="USER",
        entity_id=user.user_id,
        action="UPDATE",
        details=f"Updated user {user.name}"
    )
    return user

@api_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN can delete users
    if current_user.role.value != ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can delete users")
    
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_info = f"{user.name} ({user.email})"

    db.delete(user)
    db.commit()
    audit = AuditService(db)
    audit.log_action(
        user_id=current_user.user_id,
        entity_type="USER",
        entity_id=user_id,
        action="DELETE",
        details=f"Deleted user {user_info}"
    )
    return {"message": "User deleted successfully"}

# ============ BULK UPLOAD ROUTES (✅ RBAC ADDED) ============

from fastapi import File, UploadFile
import csv
import io

@api_router.post("/devices/bulk-upload")
async def bulk_upload_devices(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ RBAC: Only ADMIN and ENGINEER can bulk upload
    if current_user.role.value not in [ADMIN, ENGINEER]:
        raise HTTPException(status_code=403, detail="Only Admin and Engineer can bulk upload devices")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        contents = await file.read()
        csv_data = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        success_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                required_fields = ['device_id', 'type', 'ip_address', 'location']
                missing_fields = [field for field in required_fields if not row.get(field)]
                
                if missing_fields:
                    errors.append({
                        "row": row_num,
                        "error": f"Missing required fields: {', '.join(missing_fields)}"
                    })
                    error_count += 1
                    continue
                
                if not validate_ip_address(row['ip_address']):
                    errors.append({
                        "row": row_num,
                        "error": f"Invalid IP address: {row['ip_address']}"
                    })
                    error_count += 1
                    continue
                
                existing = db.query(models.Device).filter(
                    models.Device.device_id == row['device_id']
                ).first()
                
                if existing:
                    errors.append({
                        "row": row_num,
                        "error": f"Device {row['device_id']} already exists"
                    })
                    error_count += 1
                    continue
                
                device = models.Device(
                    device_id=row['device_id'],
                    type=row['type'],
                    ip_address=row['ip_address'],
                    location=row['location'],
                    model=row.get('model', ''),
                    status=models.DeviceStatus[row.get('status', 'ACTIVE').upper()]
                )
                
                db.add(device)
                audit = AuditService(db)
                audit.log_action(
                    user_id=current_user.user_id,
                    entity_type="DEVICE",
                    entity_id=device.device_id,
                    action="CREATE",
                    details=f"Bulk uploaded device {device.device_id}"
                )
                success_count += 1
                
            except Exception as e:
                errors.append({
                    "row": row_num,
                    "error": str(e)
                })
                error_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "total_processed": success_count + error_count,
            "successful": success_count,
            "failed": error_count,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

@api_router.get("/devices/download-template")
async def download_device_template(current_user: models.User = Depends(get_current_user)):
    # ✅ All roles can download template
    csv_content = "device_id,type,ip_address,location,model,status\n"
    csv_content += "RTR-BLR-001,Router,192.168.1.1,Bangalore,Cisco 9300,ACTIVE\n"
    csv_content += "SW-DEL-002,Switch,192.168.1.2,Delhi,Juniper EX4300,ACTIVE\n"
    csv_content += "FW-MUM-003,Firewall,192.168.1.3,Mumbai,Palo Alto PA-220,ACTIVE\n"
    
    csv_file = io.StringIO(csv_content)
    
    return StreamingResponse(
        iter([csv_file.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=device_upload_template.csv",
            "Cache-Control": "no-cache"
        }
    )

# ==================== MCP SERVER ROUTES ====================

class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class MCPToolResponse(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None

class MCPListToolsResponse(BaseModel):
    tools: List[Dict[str, Any]]

@app.get("/mcp")
async def mcp_health():
    return {"status": "ok", "service": "License Tracker MCP", "version": "1.0.0"}

@app.get("/mcp/tools", response_model=MCPListToolsResponse)
async def list_mcp_tools():
    tools = [
        {
            "name": "get_licenses",
            "description": "Get all licenses or filter by status (valid, expired, expiring)",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "enum": ["valid", "expired", "expiring_30_days", "all"],
                        "description": "Filter by license status"
                    },
                    "limit": {"type": "integer", "default": 20}
                }
            }
        },
        {
            "name": "get_devices",
            "description": "Get all devices or filter by status and location",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["ACTIVE", "MAINTENANCE", "DECOMMISSIONED", "all"]},
                    "location": {"type": "string"},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        },
        {
            "name": "get_license_utilization",
            "description": "Get license utilization statistics",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold_percentage": {"type": "number", "default": 0}
                }
            }
        },
        {
            "name": "get_expiring_licenses",
            "description": "Get licenses expiring within specified days",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 30}
                }
            }
        },
        {
            "name": "get_devices_at_risk",
            "description": "Get devices with expired or expiring licenses",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_threshold": {"type": "integer", "default": 15}
                }
            }
        },
        {
            "name": "get_vendor_analysis",
            "description": "Get vendor analysis and license distribution",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "search_licenses",
            "description": "Search licenses by software name or license key",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        },
        {
            "name": "search_devices",
            "description": "Search devices by ID, type, or location",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        },
        {
            "name": "get_dashboard_summary",
            "description": "Get comprehensive dashboard summary",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "get_assignments_for_device",
            "description": "Get all license assignments for a specific device",
            "parameters": {
                "type": "object",
                "properties": {"device_id": {"type": "string"}},
                "required": ["device_id"]
            }
        },
        {
            "name": "get_assignments_for_license",
            "description": "Get all device assignments for a specific license",
            "parameters": {
                "type": "object",
                "properties": {"license_key": {"type": "string"}},
                "required": ["license_key"]
            }
        }
    ]
    
    return MCPListToolsResponse(tools=tools)

@app.post("/mcp/call", response_model=MCPToolResponse)
async def call_mcp_tool(
    tool_call: MCPToolCall,
    db: Session = Depends(get_db)
):
    try:
        tool_name = tool_call.name
        args = tool_call.arguments
        
        from services.mcp_handlers import MCPHandlers
        handlers = MCPHandlers(db)
        
        if tool_name == "get_licenses":
            result = handlers.get_licenses(args)
        elif tool_name == "get_devices":
            result = handlers.get_devices(args)
        elif tool_name == "get_license_utilization":
            result = handlers.get_license_utilization(args)
        elif tool_name == "get_expiring_licenses":
            result = handlers.get_expiring_licenses(args)
        elif tool_name == "get_devices_at_risk":
            result = handlers.get_devices_at_risk(args)
        elif tool_name == "get_vendor_analysis":
            result = handlers.get_vendor_analysis(args)
        elif tool_name == "search_licenses":
            result = handlers.search_licenses(args)
        elif tool_name == "search_devices":
            result = handlers.search_devices(args)
        elif tool_name == "get_dashboard_summary":
            result = handlers.get_dashboard_summary(args)
        elif tool_name == "get_assignments_for_device":
            result = handlers.get_assignments_for_device(args)
        elif tool_name == "get_assignments_for_license":
            result = handlers.get_assignments_for_license(args)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        return MCPToolResponse(success=True, data=result)
    
    except Exception as e:
        return MCPToolResponse(success=False, data=None, error=str(e))

# ==================== END MCP ROUTES ====================

app.include_router(api_router)

# CORS Configuration
cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
if '*' in cors_origins:
    logging.warning("⚠️  CORS is set to allow all origins. This is insecure for production!")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)