from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import date
import models

class LicenseService:
    """Business logic layer for License operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_license(self, license_data: dict) -> models.License:
        """
        Create a new license
        Business rules:
        - License key must be unique
        - Vendor must exist
        - valid_to must be after valid_from
        """
        # Check if license already exists
        existing = self.db.query(models.License).filter(
            models.License.license_key == license_data['license_key']
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"License key {license_data['license_key']} already exists"
            )
        
        # Verify vendor exists
        vendor = self.db.query(models.Vendor).filter(
            models.Vendor.vendor_id == license_data['vendor_id']
        ).first()
        
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vendor {license_data['vendor_id']} not found"
            )
        
        # Validate dates
        if license_data['valid_to'] <= license_data['valid_from']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="valid_to must be after valid_from"
            )
        
        # Create license
        license = models.License(**license_data)
        self.db.add(license)
        self.db.commit()
        self.db.refresh(license)
        return license
    
    def get_license_by_key(self, license_key: str) -> models.License:
        """Get license by key"""
        license = self.db.query(models.License).filter(
            models.License.license_key == license_key
        ).first()
        
        if not license:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"License {license_key} not found"
            )
        
        return license
    
    def get_all_licenses(
        self,
        skip: int = 0,
        limit: int = 100,
        vendor_id: Optional[str] = None,
        software_name: Optional[str] = None,
        expired_only: bool = False
    ) -> List[models.License]:
        """Get all licenses with filters"""
        query = self.db.query(models.License)
        
        # Apply filters
        if vendor_id:
            query = query.filter(models.License.vendor_id == vendor_id)
        if software_name:
            query = query.filter(models.License.software_name.ilike(f"%{software_name}%"))
        if expired_only:
            query = query.filter(models.License.valid_to < date.today())
        
        # Apply pagination
        licenses = query.offset(skip).limit(limit).all()
        return licenses
    
    def update_license(self, license_key: str, update_data: dict) -> models.License:
        """Update license"""
        license = self.get_license_by_key(license_key)
        
        # Validate vendor if being updated
        if 'vendor_id' in update_data and update_data['vendor_id']:
            vendor = self.db.query(models.Vendor).filter(
                models.Vendor.vendor_id == update_data['vendor_id']
            ).first()
            if not vendor:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vendor not found"
                )
        
        # Update fields
        for key, value in update_data.items():
            if value is not None:
                setattr(license, key, value)
        
        self.db.commit()
        self.db.refresh(license)
        return license
    
    def delete_license(self, license_key: str) -> dict:
        """Delete license"""
        license = self.get_license_by_key(license_key)
        self.db.delete(license)
        self.db.commit()
        return {"message": f"License {license_key} deleted successfully"}
    
    def get_expiring_licenses(self, days: int = 30) -> List[models.License]:
        """Get licenses expiring within specified days"""
        from datetime import timedelta
        expiry_date = date.today() + timedelta(days=days)
        
        licenses = self.db.query(models.License).filter(
            models.License.valid_to <= expiry_date,
            models.License.valid_to >= date.today()
        ).all()
        
        return licenses
    
    def count_licenses(
        self,
        vendor_id: Optional[str] = None,
        software_name: Optional[str] = None
    ) -> int:
        """Count total licenses (for pagination)"""
        query = self.db.query(models.License)
        
        if vendor_id:
            query = query.filter(models.License.vendor_id == vendor_id)
        if software_name:
            query = query.filter(models.License.software_name.ilike(f"%{software_name}%"))
        
        return query.count()