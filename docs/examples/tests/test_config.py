import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, Mock
import sys

# Add parent directory to path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.unit
class TestConfigManager:
    """Test cases for configuration manager (to be implemented)."""
    
    def test_config_from_env_vars(self):
        """Test loading configuration from environment variables."""
        from config import FetcherConfig
        
        env_vars = {
            'API_ID': '12345',
            'API_HASH': 'test_hash_value',
            'CHATS': 'channel1,channel2,channel3',
            'DATA_DIR': '/custom/data',
            'SESSION_DIR': '/custom/sessions',
            'MAX_RETRIES': '5',
            'RETRY_DELAY': '2.0',
            'CONCURRENT_CHANNELS': '3'
        }
        
        with patch.dict('os.environ', env_vars):
            config = FetcherConfig.from_env()
            
            assert config.api_id == 12345
            assert config.api_hash == 'test_hash_value'
            assert config.chats == ['channel1', 'channel2', 'channel3']
            assert config.data_dir == Path('/custom/data')
            assert config.session_dir == Path('/custom/sessions')
            assert config.max_retries == 5
            assert config.retry_delay == 2.0
            assert config.concurrent_channels == 3
    
    def test_config_from_file(self, temp_data_dir):
        """Test loading configuration from JSON file."""
        from config import FetcherConfig
        
        config_data = {
            "api_id": 67890,
            "api_hash": "file_hash_value",
            "chats": ["file_channel1", "file_channel2"],
            "data_dir": "/file/data",
            "session_dir": "/file/sessions",
            "max_retries": 3,
            "retry_delay": 1.5,
            "concurrent_channels": 2,
            "rate_limit": {
                "calls_per_second": 5,
                "burst_size": 3
            }
        }
        
        config_file = temp_data_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = FetcherConfig.from_file(config_file)
        
        assert config.api_id == 67890
        assert config.api_hash == "file_hash_value"
        assert config.chats == ["file_channel1", "file_channel2"]
        assert config.rate_limit.calls_per_second == 5
        assert config.rate_limit.burst_size == 3
    
    def test_config_validation_required_fields(self):
        """Test validation of required configuration fields."""
        from config import FetcherConfig, ConfigValidationError
        
        # Missing API_ID should raise validation error
        with pytest.raises(ConfigValidationError, match="api_id is required"):
            FetcherConfig(
                api_id=None,
                api_hash="test",
                chats=["channel1"]
            )
        
        # Missing API_HASH should raise validation error
        with pytest.raises(ConfigValidationError, match="api_hash is required"):
            FetcherConfig(
                api_id=12345,
                api_hash="",
                chats=["channel1"]
            )
        
        # Empty chats list should raise validation error
        with pytest.raises(ConfigValidationError, match="at least one chat must be specified"):
            FetcherConfig(
                api_id=12345,
                api_hash="test",
                chats=[]
            )
    
    def test_config_validation_ranges(self):
        """Test validation of configuration value ranges."""
        from config import FetcherConfig, ConfigValidationError
        
        # Invalid max_retries
        with pytest.raises(ConfigValidationError, match="max_retries must be between 1 and 10"):
            FetcherConfig(
                api_id=12345,
                api_hash="test", 
                chats=["channel1"],
                max_retries=0
            )
        
        # Invalid concurrent_channels
        with pytest.raises(ConfigValidationError, match="concurrent_channels must be between 1 and 20"):
            FetcherConfig(
                api_id=12345,
                api_hash="test",
                chats=["channel1"], 
                concurrent_channels=25
            )
    
    def test_config_defaults(self):
        """Test default configuration values."""
        from config import FetcherConfig
        
        config = FetcherConfig(
            api_id=12345,
            api_hash="test",
            chats=["channel1"]
        )
        
        # Check default values
        assert config.data_dir == Path("/data")
        assert config.session_dir == Path("/sessions")
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.concurrent_channels == 1
        assert config.rate_limit.calls_per_second == 10
        assert config.rate_limit.burst_size == 5
    
    def test_config_env_override_file(self, temp_data_dir):
        """Test that environment variables override file configuration."""
        from config import FetcherConfig
        
        # Create config file
        config_data = {
            "api_id": 11111,
            "api_hash": "file_hash",
            "chats": ["file_channel"],
            "max_retries": 5
        }
        
        config_file = temp_data_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Environment variables should override
        env_vars = {
            'API_ID': '22222',
            'MAX_RETRIES': '7'
        }
        
        with patch.dict('os.environ', env_vars, clear=True):
            config = FetcherConfig.from_file_with_env_override(config_file)
            
            assert config.api_id == 22222  # From env
            assert config.api_hash == "file_hash"  # From file
            assert config.max_retries == 7  # From env
            assert config.chats == ["file_channel"]  # From file
    
    def test_config_path_expansion(self):
        """Test path expansion and validation."""
        from config import FetcherConfig
        
        # Test with relative paths that will expand to home directory
        config = FetcherConfig(
            api_id=12345,
            api_hash="test",
            chats=["channel1"],
            data_dir="~/fetcher_data",
            session_dir="~/fetcher_sessions"
        )
        
        # Paths should be expanded to home directory
        expected_home = Path.home()
        assert config.data_dir == expected_home / "fetcher_data"
        assert config.session_dir == expected_home / "fetcher_sessions"
    
    def test_config_sanitize_chats(self):
        """Test chat list sanitization."""
        from config import FetcherConfig
        
        config = FetcherConfig(
            api_id=12345,
            api_hash="test",
            chats=["@channel1", "  channel2  ", "", "channel3", "@channel4"]
        )
        
        # Should remove @ prefix, strip whitespace, and filter empty
        expected_chats = ["channel1", "channel2", "channel3", "channel4"]
        assert config.chats == expected_chats
    
    def test_rate_limit_config(self):
        """Test rate limiting configuration."""
        from config import RateLimitConfig
        
        rate_config = RateLimitConfig(
            calls_per_second=5,
            burst_size=3,
            window_size=60
        )
        
        assert rate_config.calls_per_second == 5
        assert rate_config.burst_size == 3
        assert rate_config.window_size == 60
        
        # Test validation
        with pytest.raises(ValueError, match="calls_per_second must be positive"):
            RateLimitConfig(calls_per_second=0)
        
        with pytest.raises(ValueError, match="burst_size must be positive"):
            RateLimitConfig(burst_size=0)


@pytest.mark.unit
class TestConfigConstants:
    """Test configuration constants and enums."""
    
    def test_fetch_modes(self):
        """Test fetch mode enumeration."""
        from config import FetchMode
        
        assert FetchMode.YESTERDAY.value == "yesterday"
        assert FetchMode.FULL.value == "full"
        assert FetchMode.INCREMENTAL.value == "incremental"
        
        # Test validation
        assert FetchMode.is_valid("yesterday") is True
        assert FetchMode.is_valid("invalid") is False
    
    def test_default_paths(self):
        """Test default path constants."""
        from config import DEFAULT_DATA_DIR, DEFAULT_SESSION_DIR, DEFAULT_PROGRESS_FILE
        
        assert DEFAULT_DATA_DIR == "/data"
        assert DEFAULT_SESSION_DIR == "/sessions"
        assert DEFAULT_PROGRESS_FILE == "progress.json"


@pytest.mark.integration
class TestConfigIntegration:
    """Integration tests for configuration loading."""
    
    def test_full_config_loading_chain(self, temp_data_dir):
        """Test complete configuration loading with all sources."""
        from config import load_config
        
        # Create config file
        config_file = temp_data_dir / "fetcher.json"
        config_data = {
            "api_id": 88888,  # Add required api_id
            "api_hash": "file_hash",
            "chats": ["file_channel1", "file_channel2"],
            "data_dir": str(temp_data_dir / "data"),
            "max_retries": 5
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Set environment overrides
        env_vars = {
            'API_ID': '99999',
            'CHATS': 'env_channel1,env_channel2,env_channel3',
            'FETCHER_CONFIG_FILE': str(config_file)
        }
        
        with patch.dict('os.environ', env_vars, clear=True):
            config = load_config()
            
            # Environment should override file where present
            assert config.api_id == 99999  # From env
            assert config.api_hash == "file_hash"  # From file
            assert config.chats == ["env_channel1", "env_channel2", "env_channel3"]  # From env
            assert config.max_retries == 5  # From file
            assert config.data_dir == temp_data_dir / "data"  # From file