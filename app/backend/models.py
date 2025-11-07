from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, Integer, Date, Enum, ForeignKey, DateTime, Text
from datetime import datetime, date
import enum
import uuid

Base = declarative_base()

class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    ENGINEER = "ENGINEER"
    AUDITOR = "AUDITOR"

class DeviceStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    OBSOLETE = "OBSOLETE"
    DECOMMISSIONED = "DECOMMISSIONED"

class LicenseType(enum.Enum):
    PER_USER = "Per User"
    PER_DEVICE = "Per Device"
    ENTERPRISE = "Enterprise"

class User(Base):
    __tablename__ = "users"
    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.ENGINEER)
    created_at = Column(DateTime, default=datetime.utcnow)

class Vendor(Base):
    __tablename__ = "vendors"
    vendor_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_name = Column(String(100), nullable=False)
    support_email = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    licenses = relationship("License", back_populates="vendor")

class Device(Base):
    __tablename__ = "devices"
    device_id = Column(String(50), primary_key=True)
    type = Column(String(50), nullable=False)
    ip_address = Column(String(15), unique=True, nullable=False)
    location = Column(String(100), nullable=False)
    model = Column(String(100))
    status = Column(Enum(DeviceStatus), default=DeviceStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assignments = relationship("Assignment", back_populates="device", cascade="all, delete-orphan")
    software_versions = relationship("SoftwareVersion", back_populates="device", cascade="all, delete-orphan")

class License(Base):
    __tablename__ = "licenses"
    license_key = Column(String(100), primary_key=True)
    software_name = Column(String(200), nullable=False)
    vendor_id = Column(String(36), ForeignKey("vendors.vendor_id"), nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    license_type = Column(Enum(LicenseType), nullable=False)
    max_usage = Column(Integer, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    vendor = relationship("Vendor", back_populates="licenses")
    assignments = relationship("Assignment", back_populates="license", cascade="all, delete-orphan")

class Assignment(Base):
    __tablename__ = "assignments"
    assignment_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    license_key = Column(String(100), ForeignKey("licenses.license_key"), nullable=False)
    device_id = Column(String(50), ForeignKey("devices.device_id"), nullable=False)
    assigned_by = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    license = relationship("License", back_populates="assignments")
    device = relationship("Device", back_populates="assignments")
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    action = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text)
    
    user = relationship("User")

class SoftwareVersion(Base):
    __tablename__ = "software_versions"
    
    sv_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(50), ForeignKey('devices.device_id'), nullable=False)
    software_name = Column(String(100), nullable=False)
    current_version = Column(String(20), nullable=False)
    latest_version = Column(String(20))
    status = Column(String(20), default="UP_TO_DATE")
    last_checked = Column(Date, default=date.today)
    
    device = relationship("Device", back_populates="software_versions")