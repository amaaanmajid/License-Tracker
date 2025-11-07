from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import models
from pydantic import BaseModel

class DeviceService:
    """Business logic layer for Device operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_device(self, device_data: dict) -> models.Device:
        """
        Create a new device
        Business rules:
        - Device ID must be unique
        - IP address format validation
        """
        # Check if device already exists
        existing = self.db.query(models.Device).filter(
            models.Device.device_id == device_data['device_id']
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Device with ID {device_data['device_id']} already exists"
            )
        
        # Create device
        device = models.Device(**device_data)
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device
    
    def get_device_by_id(self, device_id: str) -> models.Device:
        """Get device by ID"""
        device = self.db.query(models.Device).filter(
            models.Device.device_id == device_id
        ).first()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        
        return device
    
    def get_all_devices(
        self, 
        skip: int = 0, 
        limit: int = 100,
        location: Optional[str] = None,
        device_type: Optional[str] = None,
        status_filter: Optional[models.DeviceStatus] = None
    ) -> List[models.Device]:
        """
        Get all devices with filters
        Supports pagination and filtering
        """
        query = self.db.query(models.Device)
        
        # Apply filters
        if location:
            query = query.filter(models.Device.location.ilike(f"%{location}%"))
        if device_type:
            query = query.filter(models.Device.type.ilike(f"%{device_type}%"))
        if status_filter:
            query = query.filter(models.Device.status == status_filter)
        
        # Apply pagination
        devices = query.offset(skip).limit(limit).all()
        return devices
    
    def update_device(self, device_id: str, update_data: dict) -> models.Device:
        """Update device"""
        device = self.get_device_by_id(device_id)
        
        # Update fields
        for key, value in update_data.items():
            if value is not None:
                setattr(device, key, value)
        
        self.db.commit()
        self.db.refresh(device)
        return device
    
    def delete_device(self, device_id: str) -> dict:
        """Delete device"""
        device = self.get_device_by_id(device_id)
        self.db.delete(device)
        self.db.commit()
        return {"message": f"Device {device_id} deleted successfully"}
    
    def count_devices(
        self,
        location: Optional[str] = None,
        device_type: Optional[str] = None,
        status_filter: Optional[models.DeviceStatus] = None
    ) -> int:
        """Count total devices (for pagination)"""
        query = self.db.query(models.Device)
        
        if location:
            query = query.filter(models.Device.location.ilike(f"%{location}%"))
        if device_type:
            query = query.filter(models.Device.type.ilike(f"%{device_type}%"))
        if status_filter:
            query = query.filter(models.Device.status == status_filter)
        
        return query.count()