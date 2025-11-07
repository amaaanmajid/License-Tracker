"""
MCP Tool Handlers
All database queries for MCP tools
"""

from typing import Dict
from sqlalchemy.orm import Session
from datetime import date, timedelta
import models

class MCPHandlers:
    """Handles all MCP tool calls"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_licenses(self, args: Dict) -> Dict:
        status_filter = args.get("status_filter", "all")
        limit = args.get("limit", 20)
        today = date.today()
        
        query = self.db.query(models.License)
        
        if status_filter == "expired":
            query = query.filter(models.License.valid_to < today)
        elif status_filter == "valid":
            query = query.filter(models.License.valid_to >= today)
        elif status_filter == "expiring_30_days":
            query = query.filter(
                models.License.valid_to >= today,
                models.License.valid_to <= today + timedelta(days=30)
            )
        
        licenses = query.limit(limit).all()
        
        return {
            "total_count": len(licenses),
            "filter_applied": status_filter,
            "licenses": [
                {
                    "license_key": lic.license_key,
                    "software_name": lic.software_name,
                    "vendor_id": lic.vendor_id,
                    "valid_from": lic.valid_from.isoformat(),
                    "valid_to": lic.valid_to.isoformat(),
                    "days_until_expiry": (lic.valid_to - today).days,
                    "max_usage": lic.max_usage,
                    "status": "expired" if lic.valid_to < today else "valid"
                }
                for lic in licenses
            ]
        }
    
    def get_devices(self, args: Dict) -> Dict:
        status = args.get("status", "all")
        location = args.get("location")
        limit = args.get("limit", 20)
        
        query = self.db.query(models.Device)
        
        if status != "all":
            query = query.filter(models.Device.status == models.DeviceStatus[status])
        if location:
            query = query.filter(models.Device.location.ilike(f"%{location}%"))
        
        devices = query.limit(limit).all()
        
        return {
            "total_count": len(devices),
            "devices": [
                {
                    "device_id": dev.device_id,
                    "type": dev.type,
                    "location": dev.location,
                    "ip_address": dev.ip_address,
                    "status": dev.status.value
                }
                for dev in devices
            ]
        }
    
    def get_license_utilization(self, args: Dict) -> Dict:
        threshold = args.get("threshold_percentage", 0)
        licenses = self.db.query(models.License).all()
        
        utilization_data = []
        for lic in licenses:
            usage = self.db.query(models.Assignment).filter(
                models.Assignment.license_key == lic.license_key
            ).count()
            
            percentage = (usage / lic.max_usage * 100) if lic.max_usage > 0 else 0
            
            if percentage >= threshold:
                utilization_data.append({
                    "license_key": lic.license_key,
                    "software_name": lic.software_name,
                    "current_usage": usage,
                    "max_usage": lic.max_usage,
                    "available": lic.max_usage - usage,
                    "utilization_percentage": round(percentage, 2),
                    "status": "CRITICAL" if percentage >= 90 else "WARNING" if percentage >= 75 else "OK"
                })
        
        return {
            "total_licenses": len(utilization_data),
            "utilization": sorted(utilization_data, key=lambda x: x['utilization_percentage'], reverse=True)
        }
    
    def get_expiring_licenses(self, args: Dict) -> Dict:
        days = args.get("days", 30)
        today = date.today()
        threshold_date = today + timedelta(days=days)
        
        licenses = self.db.query(models.License).filter(
            models.License.valid_to <= threshold_date,
            models.License.valid_to >= today
        ).all()
        
        return {
            "days_threshold": days,
            "total_expiring": len(licenses),
            "licenses": [
                {
                    "license_key": lic.license_key,
                    "software_name": lic.software_name,
                    "valid_to": lic.valid_to.isoformat(),
                    "days_until_expiry": (lic.valid_to - today).days,
                    "assigned_devices": self.db.query(models.Assignment).filter(
                        models.Assignment.license_key == lic.license_key
                    ).count()
                }
                for lic in licenses
            ]
        }
    
    def get_devices_at_risk(self, args: Dict) -> Dict:
        days_threshold = args.get("days_threshold", 15)
        today = date.today()
        threshold_date = today + timedelta(days=days_threshold)
        
        devices = self.db.query(models.Device).filter(
            models.Device.status == models.DeviceStatus.ACTIVE
        ).all()
        
        at_risk = []
        for device in devices:
            assignments = self.db.query(models.Assignment).filter(
                models.Assignment.device_id == device.device_id
            ).all()
            
            expired_count = 0
            expiring_soon_count = 0
            
            for assignment in assignments:
                license = assignment.license
                if license.valid_to < today:
                    expired_count += 1
                elif license.valid_to <= threshold_date:
                    expiring_soon_count += 1
            
            if expired_count > 0 or expiring_soon_count > 0:
                at_risk.append({
                    "device_id": device.device_id,
                    "device_type": device.type,
                    "location": device.location,
                    "expired_licenses": expired_count,
                    "expiring_soon": expiring_soon_count
                })
        
        return {
            "days_threshold": days_threshold,
            "total_devices_at_risk": len(at_risk),
            "devices": at_risk
        }
    
    def get_vendor_analysis(self, args: Dict) -> Dict:
        vendors = self.db.query(models.Vendor).all()
        today = date.today()
        
        vendor_data = []
        for vendor in vendors:
            licenses = self.db.query(models.License).filter(
                models.License.vendor_id == vendor.vendor_id
            ).all()
            
            expired_count = sum(1 for lic in licenses if lic.valid_to < today)
            expiring_30_days = sum(
                1 for lic in licenses 
                if today <= lic.valid_to <= today + timedelta(days=30)
            )
            
            vendor_data.append({
                "vendor_id": vendor.vendor_id,
                "vendor_name": vendor.vendor_name,
                "total_licenses": len(licenses),
                "expired_licenses": expired_count,
                "expiring_soon": expiring_30_days
            })
        
        return {
            "total_vendors": len(vendor_data),
            "vendors": sorted(vendor_data, key=lambda x: x['total_licenses'], reverse=True)
        }
    
    def search_licenses(self, args: Dict) -> Dict:
        query_str = args.get("query", "")
        today = date.today()
        
        licenses = self.db.query(models.License).filter(
            models.License.software_name.ilike(f"%{query_str}%") |
            models.License.license_key.ilike(f"%{query_str}%")
        ).all()
        
        return {
            "search_query": query_str,
            "total_results": len(licenses),
            "licenses": [
                {
                    "license_key": lic.license_key,
                    "software_name": lic.software_name,
                    "valid_to": lic.valid_to.isoformat(),
                    "days_until_expiry": (lic.valid_to - today).days
                }
                for lic in licenses
            ]
        }
    
    def search_devices(self, args: Dict) -> Dict:
        query_str = args.get("query", "")
        
        devices = self.db.query(models.Device).filter(
            models.Device.device_id.ilike(f"%{query_str}%") |
            models.Device.type.ilike(f"%{query_str}%") |
            models.Device.location.ilike(f"%{query_str}%")
        ).all()
        
        return {
            "search_query": query_str,
            "total_results": len(devices),
            "devices": [
                {
                    "device_id": dev.device_id,
                    "type": dev.type,
                    "location": dev.location,
                    "status": dev.status.value
                }
                for dev in devices
            ]
        }
    
    def get_dashboard_summary(self, args: Dict) -> Dict:
        today = date.today()
        
        total_devices = self.db.query(models.Device).count()
        active_devices = self.db.query(models.Device).filter(
            models.Device.status == models.DeviceStatus.ACTIVE
        ).count()
        
        total_licenses = self.db.query(models.License).count()
        expired_licenses = self.db.query(models.License).filter(
            models.License.valid_to < today
        ).count()
        expiring_30_days = self.db.query(models.License).filter(
            models.License.valid_to >= today,
            models.License.valid_to <= today + timedelta(days=30)
        ).count()
        
        return {
            "devices": {
                "total": total_devices,
                "active": active_devices
            },
            "licenses": {
                "total": total_licenses,
                "expired": expired_licenses,
                "expiring_30_days": expiring_30_days
            }
        }
    
    def get_assignments_for_device(self, args: Dict) -> Dict:
        device_id = args.get("device_id")
        
        assignments = self.db.query(models.Assignment).filter(
            models.Assignment.device_id == device_id
        ).all()
        
        return {
            "device_id": device_id,
            "total_assignments": len(assignments),
            "assignments": [
                {
                    "license_key": a.license_key,
                    "software_name": a.license.software_name if a.license else "Unknown",
                    "assigned_at": a.assigned_at.isoformat()
                }
                for a in assignments
            ]
        }
    
    def get_assignments_for_license(self, args: Dict) -> Dict:
        license_key = args.get("license_key")
        
        assignments = self.db.query(models.Assignment).filter(
            models.Assignment.license_key == license_key
        ).all()
        
        return {
            "license_key": license_key,
            "total_assignments": len(assignments),
            "assignments": [
                {
                    "device_id": a.device_id,
                    "device_type": a.device.type if a.device else "Unknown",
                    "location": a.device.location if a.device else "Unknown"
                }
                for a in assignments
            ]
        }