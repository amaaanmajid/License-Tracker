import pytest
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException
from services.device_service import DeviceService
import models

@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock()

@pytest.fixture
def device_service(mock_db):
    """Device service with mocked database"""
    return DeviceService(mock_db)

@pytest.fixture
def sample_device():
    """Sample device for testing"""
    device = models.Device(
        device_id="DEV001",
        type="Router",
        ip_address="192.168.1.1",
        location="Building A",
        model="Cisco 2960",
        status=models.DeviceStatus.ACTIVE
    )
    return device

class TestDeviceService:
    
    def test_create_device_success(self, device_service, mock_db, sample_device):
        """Test successful device creation"""
        # Arrange
        device_data = {
            "device_id": "DEV001",
            "type": "Router",
            "ip_address": "192.168.1.1",
            "location": "Building A",
            "model": "Cisco 2960",
            "status": models.DeviceStatus.ACTIVE
        }
        
        mock_db.query().filter().first.return_value = None  # No existing device
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Act
        result = device_service.create_device(device_data)
        
        # Assert
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_create_device_duplicate_id(self, device_service, mock_db, sample_device):
        """Test device creation with duplicate ID"""
        # Arrange
        device_data = {
            "device_id": "DEV001",
            "type": "Router",
            "ip_address": "192.168.1.1",
            "location": "Building A"
        }
        
        # Mock existing device
        mock_db.query().filter().first.return_value = sample_device
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            device_service.create_device(device_data)
        
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail
    
    def test_get_device_by_id_success(self, device_service, mock_db, sample_device):
        """Test getting device by ID"""
        # Arrange
        mock_db.query().filter().first.return_value = sample_device
        
        # Act
        result = device_service.get_device_by_id("DEV001")
        
        # Assert
        assert result == sample_device
        assert result.device_id == "DEV001"
    
    def test_get_device_by_id_not_found(self, device_service, mock_db):
        """Test getting non-existent device"""
        # Arrange
        mock_db.query().filter().first.return_value = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            device_service.get_device_by_id("NONEXISTENT")
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail
    
    def test_get_all_devices_with_filters(self, device_service, mock_db):
        """Test getting devices with location filter"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        # Act
        result = device_service.get_all_devices(
            skip=0, 
            limit=10, 
            location="Building A"
        )
        
        # Assert
        assert isinstance(result, list)
        mock_query.filter.assert_called()
    
    def test_update_device_success(self, device_service, mock_db, sample_device):
        """Test updating device"""
        # Arrange
        mock_db.query().filter().first.return_value = sample_device
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        update_data = {"location": "Building B"}
        
        # Act
        result = device_service.update_device("DEV001", update_data)
        
        # Assert
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_delete_device_success(self, device_service, mock_db, sample_device):
        """Test deleting device"""
        # Arrange
        mock_db.query().filter().first.return_value = sample_device
        mock_db.delete = Mock()
        mock_db.commit = Mock()
        
        # Act
        result = device_service.delete_device("DEV001")
        
        # Assert
        assert "deleted successfully" in result["message"]
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_count_devices(self, device_service, mock_db):
        """Test counting devices"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.count.return_value = 5
        
        # Act
        result = device_service.count_devices()
        
        # Assert
        assert result == 5
        mock_query.count.assert_called_once()