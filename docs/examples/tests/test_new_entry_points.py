"""
Tests for new unified entry points.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from pathlib import Path


@pytest.mark.integration
class TestNewEntryPoints:
    """Test new entry point scripts."""
    
    @pytest.mark.asyncio
    async def test_new_fetcher_entry_point(self):
        """Test new_fetcher.py entry point."""
        with patch('new_fetcher.load_config') as mock_load_config, \
             patch('new_fetcher.FetcherService') as mock_service_class:
            
            # Mock config
            mock_config = Mock()
            mock_config.data_dir = Path('/tmp/data')
            mock_config.chats = ['test_channel']
            mock_config.fetch_mode = 'continuous'
            mock_load_config.return_value = mock_config
            
            # Mock service
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Test import and run
            from new_fetcher import main
            
            # Should not raise exception
            result = await main()
            
            # Verify configuration was set to continuous
            assert mock_config.fetch_mode == 'continuous'
            
            # Verify service was created and run
            mock_service_class.assert_called_once_with(mock_config)
            mock_service.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_new_fetch_yesterday_entry_point(self):
        """Test new_fetch_yesterday.py entry point."""
        with patch('new_fetch_yesterday.load_config') as mock_load_config, \
             patch('new_fetch_yesterday.FetcherService') as mock_service_class:
            
            # Mock config
            mock_config = Mock()
            mock_config.data_dir = Path('/tmp/data')
            mock_config.chats = ['test_channel']
            mock_config.fetch_mode = 'yesterday'
            mock_load_config.return_value = mock_config
            
            # Mock service
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Test import and run
            from new_fetch_yesterday import main
            
            # Should not raise exception
            result = await main()
            
            # Verify configuration was set to yesterday
            assert mock_config.fetch_mode == 'yesterday'
            
            # Verify service was created and run
            mock_service_class.assert_called_once_with(mock_config)
            mock_service.run.assert_called_once()
    
    def test_new_fetcher_executable(self):
        """Test new_fetcher.py can be imported without errors.""" 
        try:
            import new_fetcher
            assert hasattr(new_fetcher, 'main')
        except ImportError as e:
            pytest.fail(f"Could not import new_fetcher: {e}")
    
    def test_new_fetch_yesterday_executable(self):
        """Test new_fetch_yesterday.py can be imported without errors."""
        try:
            import new_fetch_yesterday  
            assert hasattr(new_fetch_yesterday, 'main')
        except ImportError as e:
            pytest.fail(f"Could not import new_fetch_yesterday: {e}")