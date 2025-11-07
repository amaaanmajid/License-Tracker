from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import models
import uuid

class AssignmentService:
    """
    Business logic layer for Assignment operations (Sprint 2)
    Handles license-to-device mapping with usage validation
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_assignment(self, license_key: str, device_id: str, assigned_by: str) -> models.Assignment:
        """
        Assign a license to a device
        Business rules:
        - License must exist
        - Device must exist
        - Check max_usage before assignment (prevent overuse)
        - Prevent duplicate assignments
        """
        # Verify license exists
        license = self.db.query(models.License).filter(
            models.License.license_key == license_key
        ).first()
        
        if not license:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"License {license_key} not found"
            )
        
        # Verify device exists
        device = self.db.query(models.Device).filter(
            models.Device.device_id == device_id
        ).first()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        
        # Check if already assigned
        existing = self.db.query(models.Assignment).filter(
            models.Assignment.license_key == license_key,
            models.Assignment.device_id == device_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"License {license_key} already assigned to device {device_id}"
            )
        
        # CRITICAL: Check max usage limit
        current_usage = self.db.query(models.Assignment).filter(
            models.Assignment.license_key == license_key
        ).count()
        
        if current_usage >= license.max_usage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"License {license_key} has reached maximum usage ({license.max_usage}). Currently assigned to {current_usage} devices."
            )
        
        # Create assignment
        assignment = models.Assignment(
            assignment_id=str(uuid.uuid4()),
            license_key=license_key,
            device_id=device_id,
            assigned_by=assigned_by
        )
        
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment
    
    def get_assignment_by_id(self, assignment_id: str) -> models.Assignment:
        """Get assignment by ID"""
        assignment = self.db.query(models.Assignment).filter(
            models.Assignment.assignment_id == assignment_id
        ).first()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment {assignment_id} not found"
            )
        
        return assignment
    
    def get_assignments_by_device(self, device_id: str) -> List[models.Assignment]:
        """Get all licenses assigned to a specific device"""
        assignments = self.db.query(models.Assignment).filter(
            models.Assignment.device_id == device_id
        ).all()
        
        return assignments
    
    def get_assignments_by_license(self, license_key: str) -> List[models.Assignment]:
        """Get all devices assigned to a specific license"""
        assignments = self.db.query(models.Assignment).filter(
            models.Assignment.license_key == license_key
        ).all()
        
        return assignments
    def delete_assignment(self, assignment_id: str) -> dict:
        """Unassign a license from a device"""
        assignment = self.get_assignment_by_id(assignment_id)
        self.db.delete(assignment)
        self.db.commit()
        return {
            "message": f"Assignment {assignment_id} deleted successfully",
            "license_key": assignment.license_key,
            "device_id": assignment.device_id
        }
    
    def get_license_utilization(self, license_key: str) -> dict:
        """
        Get utilization statistics for a license
        Returns:
        - max_usage
        - current_usage
        - available
        - utilization_percent
        - status (OK, WARNING, CRITICAL)
        """
        # Verify license exists
        license = self.db.query(models.License).filter(
            models.License.license_key == license_key
        ).first()
        
        if not license:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"License {license_key} not found"
            )
        
        # Count current assignments
        current_usage = self.db.query(models.Assignment).filter(
            models.Assignment.license_key == license_key
        ).count()
        
        max_usage = license.max_usage
        available = max_usage - current_usage
        utilization_percent = round((current_usage / max_usage) * 100, 2) if max_usage > 0 else 0
        
        # Determine status for color-coding
        if utilization_percent >= 90:
            status_label = "CRITICAL"
        elif utilization_percent >= 70:
            status_label = "WARNING"
        else:
            status_label = "OK"
        
        return {
            "license_key": license_key,
            "software_name": license.software_name,
            "max_usage": max_usage,
            "current_usage": current_usage,
            "available": available,
            "utilization_percent": utilization_percent,
            "status": status_label
        }
    
    def get_all_utilizations(self) -> List[dict]:
        """Get utilization stats for all licenses"""
        licenses = self.db.query(models.License).all()
        utilizations = []
        
        for license in licenses:
            utilizations.append(
                self.get_license_utilization(license.license_key)
            )
        
        return utilizations