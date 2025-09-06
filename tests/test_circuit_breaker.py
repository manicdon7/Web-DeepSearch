"""
Unit tests for the circuit breaker pattern implementation.
"""
import pytest
import time
from unittest.mock import Mock, patch
from app.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState, 
    CircuitBreakerOpenError, AIServiceCircuitBreaker
)


class TestCircuitBreaker:
    """Test cases for the CircuitBreaker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1,  # Short timeout for testing
            success_threshold=2
        )
        self.breaker = CircuitBreaker("test_service", self.config)
    
    def test_initial_state(self):
        """Test circuit breaker initial state."""
        assert self.breaker.get_state() == CircuitState.CLOSED
        assert self.breaker.get_stats().failure_count == 0
        assert self.breaker.get_stats().success_count == 0
        assert self.breaker.get_stats().total_calls == 0
    
    def test_successful_call(self):
        """Test successful function execution."""
        def success_func():
            return "success"
        
        result = self.breaker.call(success_func)
        
        assert result == "success"
        assert self.breaker.get_state() == CircuitState.CLOSED
        assert self.breaker.get_stats().total_calls == 1
        assert self.breaker.get_stats().failure_count == 0
    
    def test_failed_call(self):
        """Test failed function execution."""
        def failing_func():
            raise Exception("Test failure")
        
        with pytest.raises(Exception, match="Test failure"):
            self.breaker.call(failing_func)
        
        assert self.breaker.get_state() == CircuitState.CLOSED
        assert self.breaker.get_stats().total_calls == 1
        assert self.breaker.get_stats().failure_count == 1
        assert self.breaker.get_stats().total_failures == 1
    
    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold is reached."""
        def failing_func():
            raise Exception("Test failure")
        
        # Fail up to threshold
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                self.breaker.call(failing_func)
        
        # Circuit should now be open
        assert self.breaker.get_state() == CircuitState.OPEN
        assert self.breaker.get_stats().failure_count == self.config.failure_threshold
    
    def test_open_circuit_rejects_calls(self):
        """Test open circuit rejects calls immediately."""
        def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                self.breaker.call(failing_func)
        
        # Next call should be rejected
        with pytest.raises(CircuitBreakerOpenError):
            self.breaker.call(lambda: "should not execute")
        
        assert self.breaker.get_state() == CircuitState.OPEN
    
    def test_half_open_after_timeout(self):
        """Test circuit moves to half-open after recovery timeout."""
        def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                self.breaker.call(failing_func)
        
        # Wait for recovery timeout
        time.sleep(self.config.recovery_timeout + 0.1)
        
        # Next call should move to half-open
        def success_func():
            return "success"
        
        result = self.breaker.call(success_func)
        
        assert result == "success"
        assert self.breaker.get_state() == CircuitState.HALF_OPEN
    
    def test_half_open_to_closed_recovery(self):
        """Test circuit recovery from half-open to closed."""
        # Open the circuit
        def failing_func():
            raise Exception("Test failure")
        
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                self.breaker.call(failing_func)
        
        # Wait and move to half-open
        time.sleep(self.config.recovery_timeout + 0.1)
        
        def success_func():
            return "success"
        
        # First success moves to half-open
        self.breaker.call(success_func)
        assert self.breaker.get_state() == CircuitState.HALF_OPEN
        
        # Second success should close the circuit
        self.breaker.call(success_func)
        assert self.breaker.get_state() == CircuitState.CLOSED
        assert self.breaker.get_stats().failure_count == 0
    
    def test_half_open_failure_reopens_circuit(self):
        """Test circuit reopens if failure occurs in half-open state."""
        # Open the circuit
        def failing_func():
            raise Exception("Test failure")
        
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                self.breaker.call(failing_func)
        
        # Wait and move to half-open
        time.sleep(self.config.recovery_timeout + 0.1)
        
        # Success moves to half-open
        self.breaker.call(lambda: "success")
        assert self.breaker.get_state() == CircuitState.HALF_OPEN
        
        # Failure should reopen circuit
        with pytest.raises(Exception):
            self.breaker.call(failing_func)
        
        assert self.breaker.get_state() == CircuitState.OPEN
    
    def test_manual_reset(self):
        """Test manual circuit reset."""
        # Open the circuit
        def failing_func():
            raise Exception("Test failure")
        
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                self.breaker.call(failing_func)
        
        assert self.breaker.get_state() == CircuitState.OPEN
        
        # Manual reset
        self.breaker.reset()
        
        assert self.breaker.get_state() == CircuitState.CLOSED
        assert self.breaker.get_stats().failure_count == 0
        assert self.breaker.get_stats().success_count == 0
    
    def test_call_with_arguments(self):
        """Test circuit breaker with function arguments."""
        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        result = self.breaker.call(func_with_args, "arg1", "arg2", c="kwarg")
        
        assert result == "arg1-arg2-kwarg"
    
    def test_thread_safety(self):
        """Test basic thread safety of circuit breaker."""
        import threading
        
        results = []
        errors = []
        
        def test_function():
            try:
                result = self.breaker.call(lambda: "success")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=test_function)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(results) == 10
        assert len(errors) == 0
        assert self.breaker.get_stats().total_calls == 10


class TestAIServiceCircuitBreaker:
    """Test cases for the AIServiceCircuitBreaker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.ai_breaker = AIServiceCircuitBreaker()
    
    def test_initialization(self):
        """Test AI service circuit breaker initialization."""
        assert 'pollinations' in self.ai_breaker.breakers
        assert 'huggingface' in self.ai_breaker.breakers
        
        # Check initial states
        for breaker in self.ai_breaker.breakers.values():
            assert breaker.get_state() == CircuitState.CLOSED
    
    def test_successful_primary_service(self):
        """Test successful call to primary service."""
        def primary_func():
            return "primary success"
        
        def fallback_func():
            return "fallback success"
        
        result = self.ai_breaker.call_with_fallback(primary_func, fallback_func)
        
        assert result == "primary success"
    
    def test_fallback_on_primary_failure(self):
        """Test fallback when primary service fails."""
        def primary_func():
            raise Exception("Primary service down")
        
        def fallback_func():
            return "fallback success"
        
        result = self.ai_breaker.call_with_fallback(primary_func, fallback_func)
        
        assert result == "fallback success"
    
    def test_fallback_on_circuit_open(self):
        """Test fallback when primary circuit is open."""
        # Open the primary circuit
        primary_breaker = self.ai_breaker.breakers['pollinations']
        
        def failing_func():
            raise Exception("Service failure")
        
        # Fail enough times to open circuit
        for i in range(primary_breaker.config.failure_threshold):
            try:
                primary_breaker.call(failing_func)
            except:
                pass
        
        assert primary_breaker.get_state() == CircuitState.OPEN
        
        # Now test fallback
        def primary_func():
            return "should not execute"
        
        def fallback_func():
            return "fallback success"
        
        result = self.ai_breaker.call_with_fallback(primary_func, fallback_func)
        
        assert result == "fallback success"
    
    def test_both_services_fail(self):
        """Test behavior when both services fail."""
        def primary_func():
            raise Exception("Primary service down")
        
        def fallback_func():
            raise Exception("Fallback service down")
        
        with pytest.raises(Exception, match="All AI services are currently unavailable"):
            self.ai_breaker.call_with_fallback(primary_func, fallback_func)
    
    def test_get_service_status(self):
        """Test service status retrieval."""
        status = self.ai_breaker.get_service_status()
        
        assert 'pollinations' in status
        assert 'huggingface' in status
        
        for service_status in status.values():
            assert 'state' in service_status
            assert 'stats' in service_status
            assert service_status['state'] == 'closed'  # Initial state
    
    @patch('app.circuit_breaker.logger')
    def test_logging_on_failures(self, mock_logger):
        """Test that failures are properly logged."""
        def primary_func():
            raise Exception("Primary failure")
        
        def fallback_func():
            return "fallback success"
        
        result = self.ai_breaker.call_with_fallback(primary_func, fallback_func)
        
        assert result == "fallback success"
        # Verify warning was logged for primary failure
        mock_logger.warning.assert_called()
    
    def test_circuit_breaker_config_differences(self):
        """Test that different services have appropriate configurations."""
        pollinations_config = self.ai_breaker.breakers['pollinations'].config
        huggingface_config = self.ai_breaker.breakers['huggingface'].config
        
        # Pollinations should be more sensitive (lower threshold)
        assert pollinations_config.failure_threshold <= huggingface_config.failure_threshold
        
        # Pollinations should recover faster
        assert pollinations_config.recovery_timeout <= huggingface_config.recovery_timeout


class TestCircuitBreakerConfig:
    """Test cases for CircuitBreakerConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60
        assert config.success_threshold == 2
        assert config.timeout == 30
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=120,
            success_threshold=3,
            timeout=45
        )
        
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 120
        assert config.success_threshold == 3
        assert config.timeout == 45


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker scenarios."""
    
    def test_realistic_service_degradation_scenario(self):
        """Test realistic service degradation and recovery scenario."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # Very short for testing
            success_threshold=1
        )
        breaker = CircuitBreaker("test_service", config)
        
        call_count = 0
        
        def unreliable_service():
            nonlocal call_count
            call_count += 1
            
            # Fail first 2 calls, then succeed
            if call_count <= 2:
                raise Exception(f"Service failure {call_count}")
            return f"Success on call {call_count}"
        
        # First two calls fail, opening circuit
        with pytest.raises(Exception):
            breaker.call(unreliable_service)
        
        with pytest.raises(Exception):
            breaker.call(unreliable_service)
        
        assert breaker.get_state() == CircuitState.OPEN
        
        # Immediate call should be rejected
        with pytest.raises(CircuitBreakerOpenError):
            breaker.call(unreliable_service)
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Next call should succeed and close circuit
        result = breaker.call(unreliable_service)
        
        assert result == "Success on call 3"
        assert breaker.get_state() == CircuitState.CLOSED
    
    def test_multiple_circuit_breakers_independence(self):
        """Test that multiple circuit breakers operate independently."""
        breaker1 = CircuitBreaker("service1", CircuitBreakerConfig(failure_threshold=1))
        breaker2 = CircuitBreaker("service2", CircuitBreakerConfig(failure_threshold=1))
        
        # Fail service1
        with pytest.raises(Exception):
            breaker1.call(lambda: exec('raise Exception("Service1 failure")'))
        
        assert breaker1.get_state() == CircuitState.OPEN
        assert breaker2.get_state() == CircuitState.CLOSED
        
        # Service2 should still work
        result = breaker2.call(lambda: "Service2 success")
        assert result == "Service2 success"
        assert breaker2.get_state() == CircuitState.CLOSED