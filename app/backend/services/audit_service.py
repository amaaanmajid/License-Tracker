# ========================================
# AUDIT LOGGING SERVICE
# File: backend/services/audit_service.py
# ========================================

from sqlalchemy.orm import Session
import models
import uuid
from datetime import datetime

class AuditService:
    def __init__(self, db: Session):
        self.db = db
    
    def log_action(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        details: str = None
    ):
        """
        Log an audit entry
        
        Args:
            user_id: ID of user performing action
            entity_type: Type of entity (DEVICE, LICENSE, VENDOR, etc.)
            entity_id: ID of the entity
            action: Action performed (CREATE, UPDATE, DELETE, ASSIGN, etc.)
            details: Optional additional details
        """
        try:
            audit_log = models.AuditLog(
                log_id=str(uuid.uuid4()),
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                timestamp=datetime.utcnow(),
                details=details
            )
            
            self.db.add(audit_log)
            self.db.commit()
            
        except Exception as e:
            print(f"Audit logging error: {e}")
            # Don't fail the main operation if audit logging fails
            self.db.rollback()