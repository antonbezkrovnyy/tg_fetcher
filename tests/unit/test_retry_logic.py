"""Unit tests for retry utilities and backoff logic."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from telethon.errors import FloodWaitError

from src.core.retry import (
    RetryConfig,
    handle_flood_wait,
    retry_with_backoff,
    safe_operation,
)


class TestRetryWithBackoff:
    """Test exponential backoff retry logic."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test operation succeeding on first attempt."""
        operation = AsyncMock(return_value="success")
        result = await retry_with_backoff(operation, max_attempts=3)
        assert result == "success"
        operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Test operation succeeding after failures."""
        operation = AsyncMock(side_effect=[ValueError("error"), "success"])
        result = await retry_with_backoff(
            operation, max_attempts=3, base_delay=0.01, retry_on=(ValueError,)
        )
        assert result == "success"
        assert operation.await_count == 2

    @pytest.mark.asyncio
    async def test_exhaust_all_retries(self):
        """Test operation failing all retry attempts."""
        operation = AsyncMock(side_effect=ValueError("error"))
        with pytest.raises(ValueError, match="error"):
            await retry_with_backoff(
                operation, max_attempts=3, base_delay=0.01, retry_on=(ValueError,)
            )
        assert operation.await_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff delay calculation."""
        operation = AsyncMock(side_effect=[ValueError(), ValueError(), "success"])
        start_time = asyncio.get_event_loop().time()

        result = await retry_with_backoff(
            operation,
            max_attempts=3,
            base_delay=0.1,
            exponential_base=2.0,
            jitter=False,
            retry_on=(ValueError,),
        )

        elapsed = asyncio.get_event_loop().time() - start_time
        # Expected delays: 0.1s (attempt 1) + 0.2s (attempt 2) = 0.3s minimum
        assert elapsed >= 0.3
        assert result == "success"

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        operation = AsyncMock(side_effect=[ValueError(), "success"])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await retry_with_backoff(
                operation,
                max_attempts=3,
                base_delay=10.0,
                max_delay=5.0,
                exponential_base=2.0,
                jitter=False,
                retry_on=(ValueError,),
            )
            # First retry delay should be capped to max_delay
            mock_sleep.assert_called_once()
            call_args = mock_sleep.call_args[0][0]
            assert call_args <= 5.0

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test jitter adds randomness to delay."""
        operation = AsyncMock(side_effect=[ValueError(), ValueError(), "success"])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await retry_with_backoff(
                operation,
                max_attempts=3,
                base_delay=1.0,
                jitter=True,
                retry_on=(ValueError,),
            )
            # With jitter, delay should be between 0.5x and 1.5x base
            calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert len(calls) == 2
            for delay in calls:
                assert 0.5 <= delay <= 3.0  # Considering exponential growth

    @pytest.mark.asyncio
    async def test_retry_on_specific_exceptions(self):
        """Test retry only on specified exception types."""
        operation = AsyncMock(side_effect=RuntimeError("error"))
        with pytest.raises(RuntimeError, match="error"):
            await retry_with_backoff(
                operation,
                max_attempts=3,
                base_delay=0.01,
                retry_on=(ValueError,),  # Only retry ValueError
            )
        # Should fail immediately, not retry
        operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_multiple_exception_types(self):
        """Test retry on multiple exception types."""
        operation = AsyncMock(
            side_effect=[ValueError("error1"), RuntimeError("error2"), "success"]
        )
        result = await retry_with_backoff(
            operation,
            max_attempts=4,
            base_delay=0.01,
            retry_on=(ValueError, RuntimeError),
        )
        assert result == "success"
        assert operation.await_count == 3

    @pytest.mark.asyncio
    async def test_operation_name_in_logging(self, caplog):
        """Test operation name appears in log messages."""
        operation = AsyncMock(side_effect=[ValueError(), "success"])
        await retry_with_backoff(
            operation,
            max_attempts=3,
            base_delay=0.01,
            retry_on=(ValueError,),
            operation_name="test_operation",
        )
        assert "test_operation" in caplog.text


class TestHandleFloodWait:
    """Test FloodWait handling."""

    @pytest.mark.asyncio
    async def test_no_flood_wait(self):
        """Test operation without FloodWait succeeds normally."""
        operation = AsyncMock(return_value="success")
        result = await handle_flood_wait(operation)
        assert result == "success"
        operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_flood_wait_and_retry(self):
        """Test automatic retry after FloodWait."""
        flood_error = FloodWaitError(request=None, capture=1)  # 1 second wait
        operation = AsyncMock(side_effect=[flood_error, "success"])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await handle_flood_wait(operation, max_wait_seconds=10)

        assert result == "success"
        mock_sleep.assert_called_once_with(2)  # 1s + 1s safety margin
        assert operation.await_count == 2

    @pytest.mark.asyncio
    async def test_flood_wait_exceeds_max(self):
        """Test FloodWait exceeding max wait time raises error."""
        flood_error = FloodWaitError(request=None, capture=3700)  # > 1 hour
        operation = AsyncMock(side_effect=flood_error)

        with pytest.raises(FloodWaitError):
            await handle_flood_wait(operation, max_wait_seconds=3600)

        operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_multiple_flood_waits(self):
        """Test handling multiple consecutive FloodWaits."""
        flood1 = FloodWaitError(request=None, capture=1)
        flood2 = FloodWaitError(request=None, capture=2)
        operation = AsyncMock(side_effect=[flood1, flood2, "success"])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await handle_flood_wait(operation, max_wait_seconds=10)

        assert result == "success"
        assert mock_sleep.call_count == 2
        assert operation.await_count == 3

    @pytest.mark.asyncio
    async def test_flood_wait_with_other_exception(self):
        """Test non-FloodWait exceptions pass through."""
        operation = AsyncMock(side_effect=ValueError("other error"))
        with pytest.raises(ValueError, match="other error"):
            await handle_flood_wait(operation)
        operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_flood_wait_safety_margin(self):
        """Test safety margin added to FloodWait sleep."""
        flood_error = FloodWaitError(request=None, capture=5)
        operation = AsyncMock(side_effect=[flood_error, "success"])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await handle_flood_wait(operation)

        # Should sleep for 5 + 1 = 6 seconds
        mock_sleep.assert_called_once_with(6)


class TestSafeOperation:
    """Test combined retry with backoff and FloodWait handling."""

    @pytest.mark.asyncio
    async def test_success_without_errors(self):
        """Test successful operation without any errors."""
        operation = AsyncMock(return_value="success")
        result = await safe_operation(operation)
        assert result == "success"
        operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        """Test retry on transient error then success."""
        operation = AsyncMock(side_effect=[ValueError(), "success"])
        result = await safe_operation(
            operation, max_attempts=3, base_delay=0.01, retry_on=(ValueError,)
        )
        assert result == "success"
        assert operation.await_count == 2

    @pytest.mark.asyncio
    async def test_flood_wait_then_success(self):
        """Test FloodWait handling then success."""
        flood_error = FloodWaitError(request=None, capture=1)
        operation = AsyncMock(side_effect=[flood_error, "success"])

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await safe_operation(operation, max_flood_wait=10)

        assert result == "success"
        assert operation.await_count == 2

    @pytest.mark.asyncio
    async def test_combined_errors(self):
        """Test handling both FloodWait and retryable errors."""
        flood_error = FloodWaitError(request=None, capture=1)
        operation = AsyncMock(side_effect=[ValueError(), flood_error, "success"])

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await safe_operation(
                operation, max_attempts=5, base_delay=0.01, retry_on=(ValueError,)
            )

        assert result == "success"
        assert operation.await_count == 3


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.max_flood_wait == 3600
        assert config.jitter is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            max_flood_wait=7200,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.max_flood_wait == 7200
        assert config.jitter is False

    @pytest.mark.asyncio
    async def test_config_execute(self):
        """Test RetryConfig.execute method."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        operation = AsyncMock(side_effect=[ValueError(), "success"])

        result = await config.execute(
            operation, operation_name="test_op", retry_on=(ValueError,)
        )

        assert result == "success"
        assert operation.await_count == 2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_max_attempts_one(self):
        """Test single attempt with no retries."""
        operation = AsyncMock(side_effect=ValueError())
        with pytest.raises(ValueError):
            await retry_with_backoff(operation, max_attempts=1, retry_on=(ValueError,))
        operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_zero_base_delay(self):
        """Test retry with zero base delay."""
        operation = AsyncMock(side_effect=[ValueError(), "success"])
        result = await retry_with_backoff(
            operation, max_attempts=3, base_delay=0.0, retry_on=(ValueError,)
        )
        assert result == "success"

    @pytest.mark.asyncio
    async def test_flood_wait_zero_seconds(self):
        """Test FloodWait with zero seconds."""
        flood_error = FloodWaitError(request=None, capture=0)
        operation = AsyncMock(side_effect=[flood_error, "success"])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await handle_flood_wait(operation)

        assert result == "success"
        mock_sleep.assert_called_once_with(1)  # Safety margin only

    @pytest.mark.asyncio
    async def test_concurrent_retries(self):
        """Test multiple concurrent retry operations."""
        op1 = AsyncMock(side_effect=[ValueError(), "success1"])
        op2 = AsyncMock(side_effect=[ValueError(), "success2"])

        results = await asyncio.gather(
            retry_with_backoff(
                op1, max_attempts=3, base_delay=0.01, retry_on=(ValueError,)
            ),
            retry_with_backoff(
                op2, max_attempts=3, base_delay=0.01, retry_on=(ValueError,)
            ),
        )

        assert results == ["success1", "success2"]
