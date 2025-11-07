from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
import models

class AlertService:
    """
    Business logic layer for Alert operations (Sprint 3)
    Handles expiring licenses, overused licenses, and devices at risk
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_expiring_licenses(self, days: int = 30) -> List[Dict]:
        """
        Get licenses expiring within specified days
        Returns list of alerts with severity levels
        """
        today = date.today()
        threshold_date = today + timedelta(days=days)
        
        # Query licenses expiring within the threshold
        licenses = self.db.query(models.License).filter(
            models.License.valid_to <= threshold_date,
            models.License.valid_to >= today
        ).all()
        
        alerts = []
        for license in licenses:
            days_until_expiry = (license.valid_to - today).days
            
            # Count how many devices use this license
            assignment_count = self.db.query(models.Assignment).filter(
                models.Assignment.license_key == license.license_key
            ).count()
            
            alerts.append({
                "license_key": license.license_key,
                "software_name": license.software_name,
                "vendor_id": license.vendor_id,
                "valid_to": license.valid_to.isoformat(),
                "days_until_expiry": days_until_expiry,
                "assigned_devices": assignment_count,
                "severity": self._get_expiry_severity(days_until_expiry),
                "message": f"{license.software_name} expires in {days_until_expiry} day{'s' if days_until_expiry != 1 else ''}"
            })
        
        # Sort by days until expiry (most urgent first)
        return sorted(alerts, key=lambda x: x['days_until_expiry'])
    
    def get_overused_licenses(self, threshold_percent: int = 75) -> List[Dict]:
        """
        Get licenses that are at or near capacity
        Default threshold: 75% usage
        """
        licenses = self.db.query(models.License).all()
        
        overused = []
        for license in licenses:
            # Count current assignments
            usage_count = self.db.query(models.Assignment).filter(
                models.Assignment.license_key == license.license_key
            ).count()
            
            # Calculate utilization percentage
            usage_percentage = (usage_count / license.max_usage * 100) if license.max_usage > 0 else 0
            
            # Only include if above threshold
            if usage_percentage >= threshold_percent:
                overused.append({
                    "license_key": license.license_key,
                    "software_name": license.software_name,
                    "vendor_id": license.vendor_id,
                    "current_usage": usage_count,
                    "max_usage": license.max_usage,
                    "available": license.max_usage - usage_count,
                    "usage_percentage": round(usage_percentage, 2),
                    "severity": self._get_usage_severity(usage_percentage),
                    "message": f"{license.software_name} at {usage_percentage:.0f}% capacity"
                })
        
        # Sort by usage percentage (highest first)
        return sorted(overused, key=lambda x: x['usage_percentage'], reverse=True)
    
    def get_devices_at_risk(self, days_threshold: int = 15) -> List[Dict]:
        """
        Get devices with expired or soon-to-expire licenses
        Default: licenses expiring within 15 days
        """
        today = date.today()
        threshold_date = today + timedelta(days=days_threshold)
        
        # Get all active devices
        devices = self.db.query(models.Device).filter(
            models.Device.status == models.DeviceStatus.ACTIVE
        ).all()
        
        at_risk = []
        for device in devices:
            # Get all assignments for this device
            assignments = self.db.query(models.Assignment).filter(
                models.Assignment.device_id == device.device_id
            ).all()
            
            expired_count = 0
            expiring_soon_count = 0
            expired_licenses = []
            expiring_licenses = []
            
            for assignment in assignments:
                license = assignment.license
                
                if license.valid_to < today:
                    expired_count += 1
                    expired_licenses.append(license.software_name)
                elif license.valid_to <= threshold_date:
                    expiring_soon_count += 1
                    expiring_licenses.append({
                        "name": license.software_name,
                        "days_left": (license.valid_to - today).days
                    })
            
            # Only include devices with issues
            if expired_count > 0 or expiring_soon_count > 0:
                at_risk.append({
                    "device_id": device.device_id,
                    "device_type": device.type,
                    "location": device.location,
                    "ip_address": device.ip_address,
                    "expired_licenses": expired_count,
                    "expiring_soon": expiring_soon_count,
                    "expired_license_names": expired_licenses,
                    "expiring_license_details": expiring_licenses,
                    "severity": "CRITICAL" if expired_count > 0 else "WARNING",
                    "message": self._get_device_risk_message(expired_count, expiring_soon_count)
                })
        
        # Sort by severity (CRITICAL first) then by number of expired licenses
        return sorted(at_risk, key=lambda x: (x['severity'] == 'WARNING', -x['expired_licenses']))
    
    def get_dashboard_summary(self) -> Dict:
        """
        Get comprehensive dashboard summary with all key metrics
        """
        # Get alert counts
        expiring_licenses = self.get_expiring_licenses(30)
        overused_licenses = self.get_overused_licenses(75)
        devices_at_risk = self.get_devices_at_risk(15)
        
        # Get device statistics
        total_devices = self.db.query(models.Device).count()
        active_devices = self.db.query(models.Device).filter(
            models.Device.status == models.DeviceStatus.ACTIVE
        ).count()
        maintenance_devices = self.db.query(models.Device).filter(
            models.Device.status == models.DeviceStatus.MAINTENANCE
        ).count()
        decommissioned_devices = self.db.query(models.Device).filter(
            models.Device.status == models.DeviceStatus.DECOMMISSIONED
        ).count()
        
        # Get license statistics
        total_licenses = self.db.query(models.License).count()
        expired_licenses = self.db.query(models.License).filter(
            models.License.valid_to < date.today()
        ).count()
        
        # Count critical alerts (most urgent)
        critical_alerts = (
            len([a for a in expiring_licenses if a['severity'] == 'CRITICAL']) +
            len([o for o in overused_licenses if o['severity'] == 'CRITICAL']) +
            len([d for d in devices_at_risk if d['severity'] == 'CRITICAL'])
        )
        
        return {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "maintenance_devices": maintenance_devices,
            "decommissioned_devices": decommissioned_devices,
            "total_licenses": total_licenses,
            "expired_licenses": expired_licenses,
            "expiring_licenses_count": len(expiring_licenses),
            "overused_licenses_count": len(overused_licenses),
            "devices_at_risk_count": len(devices_at_risk),
            "critical_alerts": critical_alerts,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_expiry_severity(self, days_until_expiry: int) -> str:
        """Determine severity based on days until expiry"""
        if days_until_expiry <= 7:
            return "CRITICAL"
        elif days_until_expiry <= 15:
            return "HIGH"
        elif days_until_expiry <= 30:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_usage_severity(self, usage_percentage: float) -> str:
        """Determine severity based on usage percentage"""
        if usage_percentage >= 95:
            return "CRITICAL"
        elif usage_percentage >= 90:
            return "HIGH"
        elif usage_percentage >= 75:
            return "WARNING"
        else:
            return "NORMAL"
    
    def _get_device_risk_message(self, expired_count: int, expiring_soon: int) -> str:
        """Generate human-readable message for device risk"""
        parts = []
        if expired_count > 0:
            parts.append(f"{expired_count} expired license{'s' if expired_count != 1 else ''}")
        if expiring_soon > 0:
            parts.append(f"{expiring_soon} expiring soon")
        
        return " • ".join(parts)
    
    def get_license_compliance_report(self) -> Dict:
        """
        Generate a compliance report showing license status distribution
        Useful for audit purposes
        """
        all_licenses = self.db.query(models.License).all()
        today = date.today()
        
        valid_count = 0
        expiring_30_days = 0
        expiring_60_days = 0
        expired_count = 0
        overused_count = 0
        
        for license in all_licenses:
            days_until_expiry = (license.valid_to - today).days
            
            # Check usage
            usage = self.db.query(models.Assignment).filter(
                models.Assignment.license_key == license.license_key
            ).count()
            
            if days_until_expiry < 0:
                expired_count += 1
            elif days_until_expiry <= 30:
                expiring_30_days += 1
            elif days_until_expiry <= 60:
                expiring_60_days += 1
            else:
                valid_count += 1
            
            if usage >= license.max_usage * 0.9:  # 90% threshold
                overused_count += 1
        
        return {
            "total_licenses": len(all_licenses),
            "valid_licenses": valid_count,
            "expiring_within_30_days": expiring_30_days,
            "expiring_within_60_days": expiring_60_days,
            "expired_licenses": expired_count,
            "overused_licenses": overused_count,
            "compliance_rate": round((valid_count / len(all_licenses) * 100), 2) if all_licenses else 0,
            "generated_at": datetime.utcnow().isoformat()
        }