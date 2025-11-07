from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, date, timedelta
import models
import csv
import io

class ReportService:
    """
    Business logic layer for Reports and Analytics (Sprint 4)
    Generates comprehensive reports and data exports
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_license_compliance_report(self) -> Dict:
        """
        Generate comprehensive license compliance report
        Shows: valid, expiring, expired, overused licenses
        """
        all_licenses = self.db.query(models.License).all()
        today = date.today()
        
        valid_licenses = []
        expiring_30_days = []
        expiring_60_days = []
        expired_licenses = []
        overused_licenses = []
        underutilized_licenses = []
        
        for license in all_licenses:
            days_until_expiry = (license.valid_to - today).days
            
            # Get usage count
            usage_count = self.db.query(models.Assignment).filter(
                models.Assignment.license_key == license.license_key
            ).count()
            
            usage_percentage = (usage_count / license.max_usage * 100) if license.max_usage > 0 else 0
            
            license_data = {
                "license_key": license.license_key,
                "software_name": license.software_name,
                "vendor_id": license.vendor_id,
                "valid_from": license.valid_from.isoformat(),
                "valid_to": license.valid_to.isoformat(),
                "days_until_expiry": days_until_expiry,
                "max_usage": license.max_usage,
                "current_usage": usage_count,
                "usage_percentage": round(usage_percentage, 2),
                "license_type": license.license_type.value
            }
            
            # Categorize by expiry
            if days_until_expiry < 0:
                expired_licenses.append(license_data)
            elif days_until_expiry <= 30:
                expiring_30_days.append(license_data)
            elif days_until_expiry <= 60:
                expiring_60_days.append(license_data)
            else:
                valid_licenses.append(license_data)
            
            # Categorize by usage
            if usage_percentage >= 90:
                overused_licenses.append(license_data)
            elif usage_percentage < 30:
                underutilized_licenses.append(license_data)
        
        return {
            "report_date": datetime.utcnow().isoformat(),
            "total_licenses": len(all_licenses),
            "summary": {
                "valid": len(valid_licenses),
                "expiring_30_days": len(expiring_30_days),
                "expiring_60_days": len(expiring_60_days),
                "expired": len(expired_licenses),
                "overused": len(overused_licenses),
                "underutilized": len(underutilized_licenses)
            },
            "valid_licenses": valid_licenses,
            "expiring_30_days": expiring_30_days,
            "expiring_60_days": expiring_60_days,
            "expired_licenses": expired_licenses,
            "overused_licenses": overused_licenses,
            "underutilized_licenses": underutilized_licenses,
            "compliance_rate": round((len(valid_licenses) / len(all_licenses) * 100), 2) if all_licenses else 0
        }
    
    def generate_device_inventory_report(self) -> Dict:
        """
        Generate device inventory report
        Breakdown by location, type, status
        """
        all_devices = self.db.query(models.Device).all()
        
        # Group by status
        status_breakdown = {}
        for status in models.DeviceStatus:
            count = self.db.query(models.Device).filter(
                models.Device.status == status
            ).count()
            status_breakdown[status.value] = count
        
        # Group by location
        location_breakdown = {}
        locations = self.db.query(models.Device.location, func.count(models.Device.device_id)).group_by(models.Device.location).all()
        for location, count in locations:
            location_breakdown[location] = count
        
        # Group by type
        type_breakdown = {}
        types = self.db.query(models.Device.type, func.count(models.Device.device_id)).group_by(models.Device.type).all()
        for device_type, count in types:
            type_breakdown[device_type] = count
        
        # Devices with assignments
        devices_with_licenses = []
        devices_without_licenses = []
        
        for device in all_devices:
            assignment_count = self.db.query(models.Assignment).filter(
                models.Assignment.device_id == device.device_id
            ).count()
            
            device_data = {
                "device_id": device.device_id,
                "type": device.type,
                "location": device.location,
                "ip_address": device.ip_address,
                "status": device.status.value,
                "model": device.model,
                "assigned_licenses": assignment_count
            }
            
            if assignment_count > 0:
                devices_with_licenses.append(device_data)
            else:
                devices_without_licenses.append(device_data)
        
        return {
            "report_date": datetime.utcnow().isoformat(),
            "total_devices": len(all_devices),
            "status_breakdown": status_breakdown,
            "location_breakdown": location_breakdown,
            "type_breakdown": type_breakdown,
            "devices_with_licenses": len(devices_with_licenses),
            "devices_without_licenses": len(devices_without_licenses),
            "device_details": {
                "with_licenses": devices_with_licenses,
                "without_licenses": devices_without_licenses
            }
        }
    
    def generate_vendor_analysis_report(self) -> Dict:
        """
        Generate vendor analysis report
        Shows license distribution by vendor
        """
        vendors = self.db.query(models.Vendor).all()
        vendor_analysis = []
        
        for vendor in vendors:
            licenses = self.db.query(models.License).filter(
                models.License.vendor_id == vendor.vendor_id
            ).all()
            
            total_licenses = len(licenses)
            expired_count = 0
            expiring_30_days = 0
            total_capacity = 0
            total_usage = 0
            
            today = date.today()
            
            for license in licenses:
                days_until_expiry = (license.valid_to - today).days
                
                if days_until_expiry < 0:
                    expired_count += 1
                elif days_until_expiry <= 30:
                    expiring_30_days += 1
                
                total_capacity += license.max_usage
                
                usage = self.db.query(models.Assignment).filter(
                    models.Assignment.license_key == license.license_key
                ).count()
                
                total_usage += usage
            
            vendor_analysis.append({
                "vendor_id": vendor.vendor_id,
                "vendor_name": vendor.vendor_name,
                "support_email": vendor.support_email,
                "total_licenses": total_licenses,
                "expired_licenses": expired_count,
                "expiring_soon": expiring_30_days,
                "total_capacity": total_capacity,
                "total_usage": total_usage,
                "utilization_percentage": round((total_usage / total_capacity * 100), 2) if total_capacity > 0 else 0
            })
        
        # Sort by total licenses (descending)
        vendor_analysis.sort(key=lambda x: x['total_licenses'], reverse=True)
        
        return {
            "report_date": datetime.utcnow().isoformat(),
            "total_vendors": len(vendors),
            "vendor_analysis": vendor_analysis
        }
    
    def generate_assignment_history_report(self, days: int = 30) -> Dict:
        """
        Generate assignment history report
        Shows recent license assignments
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        assignments = self.db.query(models.Assignment).filter(
            models.Assignment.assigned_at >= start_date
        ).order_by(models.Assignment.assigned_at.desc()).all()
        
        assignment_data = []
        for assignment in assignments:
            license = assignment.license
            device = assignment.device
            user = assignment.user
            
            assignment_data.append({
                "assignment_id": assignment.assignment_id,
                "license_key": assignment.license_key,
                "software_name": license.software_name if license else "Unknown",
                "device_id": assignment.device_id,
                "device_type": device.type if device else "Unknown",
                "device_location": device.location if device else "Unknown",
                "assigned_by": user.name if user else "Unknown",
                "assigned_at": assignment.assigned_at.isoformat()
            })
        
        return {
            "report_date": datetime.utcnow().isoformat(),
            "period_days": days,
            "total_assignments": len(assignment_data),
            "assignments": assignment_data
        }
    
    def generate_audit_log_report(self, days: int = 7, entity_type: Optional[str] = None) -> Dict:
        """
        Generate audit log report
        Shows recent system activity
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(models.AuditLog).filter(
            models.AuditLog.timestamp >= start_date
        )
        
        if entity_type:
            query = query.filter(models.AuditLog.entity_type == entity_type)
        
        logs = query.order_by(models.AuditLog.timestamp.desc()).all()
        
        log_data = []
        for log in logs:
            user = log.user
            log_data.append({
                "log_id": log.log_id,
                "user_name": user.name if user else "System",
                "user_email": user.email if user else "system@licensetracker.com",
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "action": log.action,
                "details": log.details,
                "timestamp": log.timestamp.isoformat()
            })
        
        return {
            "report_date": datetime.utcnow().isoformat(),
            "period_days": days,
            "entity_type_filter": entity_type,
            "total_activities": len(log_data),
            "activities": log_data
        }
    
    def export_licenses_to_csv(self) -> str:
        """
        Export all licenses to CSV format
        Returns CSV string
        """
        licenses = self.db.query(models.License).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'License Key', 'Software Name', 'Vendor ID', 'License Type',
            'Valid From', 'Valid To', 'Max Usage', 'Current Usage', 'Notes'
        ])
        
        # Write data
        for license in licenses:
            usage = self.db.query(models.Assignment).filter(
                models.Assignment.license_key == license.license_key
            ).count()
            
            writer.writerow([
                license.license_key,
                license.software_name,
                license.vendor_id,
                license.license_type.value,
                license.valid_from.isoformat(),
                license.valid_to.isoformat(),
                license.max_usage,
                usage,
                license.notes or ''
            ])
        
        return output.getvalue()
    
    def export_devices_to_csv(self) -> str:
        """
        Export all devices to CSV format
        Returns CSV string
        """
        devices = self.db.query(models.Device).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Device ID', 'Type', 'IP Address', 'Location', 'Model', 
            'Status', 'Assigned Licenses', 'Created At'
        ])
        
        # Write data
        for device in devices:
            assignment_count = self.db.query(models.Assignment).filter(
                models.Assignment.device_id == device.device_id
            ).count()
            
            writer.writerow([
                device.device_id,
                device.type,
                device.ip_address,
                device.location,
                device.model or '',
                device.status.value,
                assignment_count,
                device.created_at.isoformat()
            ])
        
        return output.getvalue()
    
    def export_assignments_to_csv(self) -> str:
        """
        Export all assignments to CSV format
        Returns CSV string
        """
        assignments = self.db.query(models.Assignment).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Assignment ID', 'License Key', 'Software Name', 'Device ID',
            'Device Type', 'Location', 'Assigned By', 'Assigned At'
        ])
        
        # Write data
        for assignment in assignments:
            license = assignment.license
            device = assignment.device
            user = assignment.user
            
            writer.writerow([
                assignment.assignment_id,
                assignment.license_key,
                license.software_name if license else 'Unknown',
                assignment.device_id,
                device.type if device else 'Unknown',
                device.location if device else 'Unknown',
                user.name if user else 'Unknown',
                assignment.assigned_at.isoformat()
            ])
        
        return output.getvalue()
    
    def get_utilization_trends(self, days: int = 30) -> Dict:
        """
        Get license utilization trends over time
        Shows how usage has changed
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get assignments created in the period
        assignments = self.db.query(models.Assignment).filter(
            models.Assignment.assigned_at >= start_date
        ).all()
        
        # Group by date
        daily_assignments = {}
        for assignment in assignments:
            date_key = assignment.assigned_at.date().isoformat()
            if date_key not in daily_assignments:
                daily_assignments[date_key] = 0
            daily_assignments[date_key] += 1
        
        # Get current utilization by license
        licenses = self.db.query(models.License).all()
        license_utilization = []
        
        for license in licenses:
            usage = self.db.query(models.Assignment).filter(
                models.Assignment.license_key == license.license_key
            ).count()
            
            license_utilization.append({
                "license_key": license.license_key,
                "software_name": license.software_name,
                "usage": usage,
                "capacity": license.max_usage,
                "utilization_percentage": round((usage / license.max_usage * 100), 2) if license.max_usage > 0 else 0
            })
        
        # Sort by utilization
        license_utilization.sort(key=lambda x: x['utilization_percentage'], reverse=True)
        
        return {
            "report_date": datetime.utcnow().isoformat(),
            "period_days": days,
            "daily_assignments": daily_assignments,
            "license_utilization": license_utilization,
            "total_assignments_in_period": len(assignments)
        }