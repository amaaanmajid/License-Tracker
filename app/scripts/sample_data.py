#!/usr/bin/env python3
"""
Sample Data Generator
Populates database with realistic test data

USAGE: 
  cd backend
  python ../scripts/sample_data.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import uuid

# ✅ ABSOLUTE FIX: Navigate to backend directory
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent / "backend"

# Add backend to Python path
sys.path.insert(0, str(BACKEND_DIR))

# Change working directory to backend
os.chdir(BACKEND_DIR)

# NOW imports will work
from database import SessionLocal
import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_sample_data():
    """Create sample data for testing"""
    
    print("🌱 Creating sample data...")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Create sample users
        print("👥 Creating sample users...")
        
        users = [
            {
                "email": "engineer@licensetracker.com",
                "name": "John Engineer",
                "password": "Engineer@123",
                "role": models.UserRole.ENGINEER
            },
            {
                "email": "auditor@licensetracker.com",
                "name": "Jane Auditor",
                "password": "Auditor@123",
                "role": models.UserRole.AUDITOR
            }
        ]
        
        for user_data in users:
            existing = db.query(models.User).filter(
                models.User.email == user_data["email"]
            ).first()
            
            if not existing:
                user = models.User(
                    user_id=str(uuid.uuid4()),
                    email=user_data["email"],
                    name=user_data["name"],
                    password_hash=pwd_context.hash(user_data["password"]),
                    role=user_data["role"]
                )
                db.add(user)
                print(f"  ✓ Created: {user_data['name']} ({user_data['role'].value})")
            else:
                print(f"  ⊙ Exists: {user_data['name']}")
        
        db.commit()
        
        # Create sample vendors
        print("\n🏢 Creating sample vendors...")
        
        vendors_data = [
            {"name": "Cisco Systems", "email": "support@cisco.com"},
            {"name": "Palo Alto Networks", "email": "support@paloaltonetworks.com"},
            {"name": "Juniper Networks", "email": "support@juniper.net"},
            {"name": "Fortinet", "email": "support@fortinet.com"},
            {"name": "VMware", "email": "support@vmware.com"}
        ]
        
        created_vendors = []
        for vendor_data in vendors_data:
            existing = db.query(models.Vendor).filter(
                models.Vendor.vendor_name == vendor_data["name"]
            ).first()
            
            if not existing:
                vendor = models.Vendor(
                    vendor_id=str(uuid.uuid4()),
                    vendor_name=vendor_data["name"],
                    support_email=vendor_data["email"]
                )
                db.add(vendor)
                created_vendors.append(vendor)
                print(f"  ✓ Created: {vendor_data['name']}")
            else:
                created_vendors.append(existing)
                print(f"  ⊙ Exists: {vendor_data['name']}")
        
        db.commit()
        
        # Create sample devices
        print("\n💻 Creating sample devices...")
        
        devices_data = [
            {"id": "RTR-BLR-001", "type": "Router", "ip": "192.168.1.1", "location": "Bangalore", "model": "Cisco ISR 4451"},
            {"id": "RTR-DEL-001", "type": "Router", "ip": "192.168.2.1", "location": "Delhi", "model": "Cisco ASR 1001-X"},
            {"id": "SW-BLR-001", "type": "Switch", "ip": "192.168.1.10", "location": "Bangalore", "model": "Cisco Catalyst 9300"},
            {"id": "SW-MUM-001", "type": "Switch", "ip": "192.168.3.10", "location": "Mumbai", "model": "Juniper EX4300"},
            {"id": "FW-BLR-001", "type": "Firewall", "ip": "192.168.1.254", "location": "Bangalore", "model": "Palo Alto PA-5220"},
            {"id": "FW-DEL-001", "type": "Firewall", "ip": "192.168.2.254", "location": "Delhi", "model": "Fortinet FortiGate 600E"},
            {"id": "FW-MUM-001", "type": "Firewall", "ip": "192.168.3.254", "location": "Mumbai", "model": "Palo Alto PA-3220"},
            {"id": "SW-CHE-001", "type": "Switch", "ip": "192.168.4.10", "location": "Chennai", "model": "Cisco Nexus 9000"},
            {"id": "RTR-HYD-001", "type": "Router", "ip": "192.168.5.1", "location": "Hyderabad", "model": "Juniper MX204"},
            {"id": "FW-HYD-001", "type": "Firewall", "ip": "192.168.5.254", "location": "Hyderabad", "model": "Fortinet FortiGate 400E"}
        ]
        
        created_devices = []
        for device_data in devices_data:
            existing = db.query(models.Device).filter(
                models.Device.device_id == device_data["id"]
            ).first()
            
            if not existing:
                device = models.Device(
                    device_id=device_data["id"],
                    type=device_data["type"],
                    ip_address=device_data["ip"],
                    location=device_data["location"],
                    model=device_data["model"],
                    status=models.DeviceStatus.ACTIVE
                )
                db.add(device)
                created_devices.append(device)
                print(f"  ✓ Created: {device_data['id']} ({device_data['type']})")
            else:
                created_devices.append(existing)
                print(f"  ⊙ Exists: {device_data['id']}")
        
        db.commit()
        
        # Create sample licenses
        print("\n🔑 Creating sample licenses...")
        
        today = datetime.now().date()
        
        licenses_data = [
            {
                "key": "CSCO-IOS-2024-001",
                "software": "Cisco IOS XE",
                "vendor": "Cisco Systems",
                "valid_from": today - timedelta(days=365),
                "valid_to": today + timedelta(days=365),
                "type": models.LicenseType.SUBSCRIPTION,
                "max_usage": 10
            },
            {
                "key": "PALO-PANOS-2024-001",
                "software": "PAN-OS",
                "vendor": "Palo Alto Networks",
                "valid_from": today - timedelta(days=180),
                "valid_to": today + timedelta(days=545),
                "type": models.LicenseType.PERPETUAL,
                "max_usage": 5
            },
            {
                "key": "JNPR-JUNOS-2024-001",
                "software": "Junos OS",
                "vendor": "Juniper Networks",
                "valid_from": today - timedelta(days=200),
                "valid_to": today + timedelta(days=165),
                "type": models.LicenseType.SUBSCRIPTION,
                "max_usage": 8
            },
            {
                "key": "FORT-FOS-2024-001",
                "software": "FortiOS",
                "vendor": "Fortinet",
                "valid_from": today - timedelta(days=300),
                "valid_to": today + timedelta(days=65),
                "type": models.LicenseType.SUBSCRIPTION,
                "max_usage": 6
            },
            {
                "key": "VMW-ESXI-2024-001",
                "software": "VMware ESXi",
                "vendor": "VMware",
                "valid_from": today - timedelta(days=400),
                "valid_to": today - timedelta(days=35),
                "type": models.LicenseType.PERPETUAL,
                "max_usage": 20
            }
        ]
        
        created_licenses = []
        for license_data in licenses_data:
            vendor = next((v for v in created_vendors if v.vendor_name == license_data["vendor"]), None)
            
            if vendor:
                existing = db.query(models.License).filter(
                    models.License.license_key == license_data["key"]
                ).first()
                
                if not existing:
                    license = models.License(
                        license_key=license_data["key"],
                        software_name=license_data["software"],
                        vendor_id=vendor.vendor_id,
                        valid_from=license_data["valid_from"],
                        valid_to=license_data["valid_to"],
                        license_type=license_data["type"],
                        max_usage=license_data["max_usage"]
                    )
                    db.add(license)
                    created_licenses.append(license)
                    
                    status = "✓"
                    if license_data["valid_to"] < today:
                        status = "⚠️ EXPIRED"
                    elif license_data["valid_to"] < today + timedelta(days=30):
                        status = "⚠️ EXPIRING SOON"
                    
                    print(f"  {status} Created: {license_data['key']}")
                else:
                    created_licenses.append(existing)
                    print(f"  ⊙ Exists: {license_data['key']}")
        
        db.commit()
        
        # Create sample assignments
        print("\n🔗 Creating sample license assignments...")
        
        assignments_created = 0
        for i, device in enumerate(created_devices[:5]):
            if i < len(created_licenses):
                license = created_licenses[i]
                
                existing = db.query(models.Assignment).filter(
                    models.Assignment.device_id == device.device_id,
                    models.Assignment.license_key == license.license_key
                ).first()
                
                if not existing:
                    assignment = models.Assignment(
                        assignment_id=str(uuid.uuid4()),
                        license_key=license.license_key,
                        device_id=device.device_id,
                        assigned_by="admin@licensetracker.com"
                    )
                    db.add(assignment)
                    assignments_created += 1
                    print(f"  ✓ Assigned {license.software_name} → {device.device_id}")
                else:
                    print(f"  ⊙ Exists: {license.software_name} → {device.device_id}")
        
        db.commit()
        
        # Create sample software versions
        print("\n📦 Creating sample software versions...")
        
        versions_data = [
            {"device": "RTR-BLR-001", "software": "Cisco IOS XE", "current": "17.6.1", "latest": "17.9.2", "status": "OUTDATED"},
            {"device": "FW-BLR-001", "software": "PAN-OS", "current": "10.2.3", "latest": "10.2.3", "status": "UP_TO_DATE"},
            {"device": "SW-BLR-001", "software": "Cisco IOS", "current": "15.2.7", "latest": "16.12.5", "status": "CRITICAL"},
            {"device": "FW-DEL-001", "software": "FortiOS", "current": "7.0.5", "latest": "7.2.3", "status": "OUTDATED"},
            {"device": "SW-MUM-001", "software": "Junos OS", "current": "21.4R3", "latest": "22.2R1", "status": "OUTDATED"}
        ]
        
        for version_data in versions_data:
            device_id = version_data["device"]
            device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
            
            if device:
                existing = db.query(models.SoftwareVersion).filter(
                    models.SoftwareVersion.device_id == device_id,
                    models.SoftwareVersion.software_name == version_data["software"]
                ).first()
                
                if not existing:
                    version = models.SoftwareVersion(
                        sv_id=str(uuid.uuid4()),
                        device_id=device_id,
                        software_name=version_data["software"],
                        current_version=version_data["current"],
                        latest_version=version_data["latest"],
                        status=version_data["status"],
                        last_checked=today
                    )
                    db.add(version)
                    
                    status_icon = "✓" if version_data["status"] == "UP_TO_DATE" else "⚠️"
                    print(f"  {status_icon} {device_id}: {version_data['software']} v{version_data['current']}")
                else:
                    print(f"  ⊙ Exists: {device_id}: {version_data['software']}")
        
        db.commit()
        
        print("\n" + "=" * 60)
        print("✅ Sample data created successfully!")
        print("=" * 60)
        print()
        print("📊 Summary:")
        print(f"  • Users: 3 (1 Admin, 1 Engineer, 1 Auditor)")
        print(f"  • Vendors: {len(vendors_data)}")
        print(f"  • Devices: {len(devices_data)}")
        print(f"  • Licenses: {len(licenses_data)}")
        print(f"  • Assignments: {assignments_created}")
        print(f"  • Software Versions: {len(versions_data)}")
        print()
        print("🔐 Test User Credentials:")
        print("  Admin:    admin@licensetracker.com / Admin@123")
        print("  Engineer: engineer@licensetracker.com / Engineer@123")
        print("  Auditor:  auditor@licensetracker.com / Auditor@123")
        print()
        
    except Exception as e:
        print(f"\n❌ Error creating sample data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data()