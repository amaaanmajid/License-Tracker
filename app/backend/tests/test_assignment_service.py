import pytest
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException
from services.assignment_service import AssignmentService
import models
from datetime import datetime, date

@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock()

@pytest.fixture
def assignment_service(mock_db):
    """Assignment service with mocked database"""
    return AssignmentService(mock_db)

@pytest.fixture
def sample_license():
    """Sample license for testing"""
    license = models.License(
        license_key="LIC-001",
        software_name="Adobe Photoshop",
        vendor_id="vendor-123",
        valid_from=date(2025, 1, 1),
        valid_to=date(2025, 12, 31),
        license_type=models.LicenseType.PER_USER,
        max_usage=5
    )
    return license

@pytest.fixture
def sample_device():
    """Sample device for testing"""
    device = models.Device(
        device_id="DEV-001",
        type="Workstation",
        ip_address="192.168.1.10",
        location="Office A",
        status=models.DeviceStatus.ACTIVE
    )
    return device

@pytest.fixture
def sample_assignment():
    """Sample assignment for testing"""
    assignment = models.Assignment(
        assignment_id="ASSIGN-001",
        license_key="LIC-001",
        device_id="DEV-001",
        assigned_by="user-123",
        assigned_at=datetime.now()
    )
    return assignment

class TestAssignmentService:
    
    def test_create_assignment_success(self, assignment_service, mock_db, sample_license, sample_device):
        """Test successful assignment creation"""
        # Arrange
        mock_db.query().filter().first.side_effect = [sample_license, sample_device, None]  # License exists, device exists, no existing assignment
        mock_db.query().filter().count.return_value = 2  # Current usage < max_usage
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Act
        result = assignment_service.create_assignment("LIC-001", "DEV-001", "user-123")
        
        # Assert
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_create_assignment_license_not_found(self, assignment_service, mock_db):
        """Test assignment creation with non-existent license"""
        # Arrange
        mock_db.query().filter().first.return_value = None  # License doesn't exist
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            assignment_service.create_assignment("INVALID-LIC", "DEV-001", "user-123")
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail
    
    def test_create_assignment_max_usage_exceeded(self, assignment_service, mock_db, sample_license, sample_device):
        """Test assignment creation when max usage is exceeded"""
        # Arrange
        mock_db.query().filter().first.side_effect = [sample_license, sample_device, None]
        mock_db.query().filter().count.return_value = 5  # Current usage = max_usage
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            assignment_service.create_assignment("LIC-001", "DEV-001", "user-123")
        
        assert exc_info.value.status_code == 400
        assert "maximum usage" in exc_info.value.detail
    
    def test_create_assignment_duplicate(self, assignment_service, mock_db, sample_license, sample_device, sample_assignment):
        """Test assignment creation with duplicate assignment"""
        # Arrange
        mock_db.query().filter().first.side_effect = [sample_license, sample_device, sample_assignment]  # Existing assignment
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            assignment_service.create_assignment("LIC-001", "DEV-001", "user-123")
        
        assert exc_info.value.status_code == 400
        assert "already assigned" in exc_info.value.detail
    
    def test_get_assignments_by_device(self, assignment_service, mock_db, sample_assignment):
        """Test getting assignments by device"""
        # Arrange
        mock_db.query().filter().all.return_value = [sample_assignment]
        
        # Act
        result = assignment_service.get_assignments_by_device("DEV-001")
        
        # Assert
        assert len(result) == 1
        assert result[0] == sample_assignment
    
    def test_get_license_utilization(self, assignment_service, mock_db, sample_license):
        """Test license utilization calculation"""
        # Arrange
        mock_db.query().filter().first.return_value = sample_license
        mock_db.query().filter().count.return_value = 3  # 3 out of 5 used
        
        # Act
        result = assignment_service.get_license_utilization("LIC-001")
        
        # Assert
        assert result["max_usage"] == 5
        assert result["current_usage"] == 3
        assert result["available"] == 2
        assert result["utilization_percent"] == 60.0
        assert result["status"] == "OK"
    
    def test_delete_assignment_success(self, assignment_service, mock_db, sample_assignment):
        """Test successful assignment deletion"""
        # Arrange
        mock_db.query().filter().first.return_value = sample_assignment
        mock_db.delete = Mock()
        mock_db.commit = Mock()
        
        # Act
        result = assignment_service.delete_assignment("ASSIGN-001")
        
        # Assert
        assert "deleted successfully" in result["message"]
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()
