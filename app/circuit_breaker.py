"""
Circuit breaker pattern implementation for AI services.
Provides automatic fallback switching when primary services fail.
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service is failing, circuit is open
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5  # Number of failures before opening circuit
    recovery_timeout: int = 60  # Seconds to wait before trying half-open
    success_threshold: int = 2  # Successful calls needed to close circuit from half-open
    timeout: int = 30  # Timeout for individual service calls


@dataclass
class CircuitBreakerStats:
    """Statistics tracking for circuit breaker"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    total_calls: int = 0
    total_failures: int = 0


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting against cascading failures.
    
    Automatically opens when failure threshold is reached, preventing further calls
    to failing services. Gradually recovers by testing service availability.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = Lock()
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            CircuitBreakerOpenError: When circuit is open and call is rejected
            Exception: Any exception raised by the wrapped function
        """
        with self._lock:
            self.stats.total_calls += 1
            
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker {self.name} moving to HALF_OPEN state")
                else:
                    logger.warning(f"Circuit breaker {self.name} is OPEN, rejecting call")
                    raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
                
            except Exception as e:
                self._on_failure()
                raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.stats.last_failure_time is None:
            return True
        return time.time() - self.stats.last_failure_time >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful function execution"""
        self.stats.failure_count = 0
        self.stats.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.stats.success_count = 0
                logger.info(f"Circuit breaker {self.name} recovered, moving to CLOSED state")
    
    def _on_failure(self):
        """Handle failed function execution"""
        self.stats.failure_count += 1
        self.stats.total_failures += 1
        self.stats.last_failure_time = time.time()
        self.stats.success_count = 0
        
        if self.state == CircuitState.HALF_OPEN or self.stats.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} opened due to {self.stats.failure_count} failures")
    
    def get_state(self) -> CircuitState:
        """Get current circuit breaker state"""
        return self.state
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics"""
        return self.stats
    
    def reset(self):
        """Manually reset circuit breaker to closed state"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.stats.failure_count = 0
            self.stats.success_count = 0
            logger.info(f"Circuit breaker {self.name} manually reset to CLOSED state")


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open and rejects calls"""
    pass


class AIServiceCircuitBreaker:
    """
    Specialized circuit breaker manager for AI services with multiple fallbacks.
    """
    
    def __init__(self):
        self.breakers = {
            'pollinations': CircuitBreaker('pollinations', CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
                success_threshold=2
            )),
            'huggingface': CircuitBreaker('huggingface', CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=2
            ))
        }
    
    def call_with_fallback(self, primary_func: Callable, fallback_func: Callable, 
                          *args, **kwargs) -> Any:
        """
        Call primary function with automatic fallback to secondary function.
        
        Args:
            primary_func: Primary AI service function
            fallback_func: Fallback AI service function
            *args: Arguments for the functions
            **kwargs: Keyword arguments for the functions
            
        Returns:
            Result from either primary or fallback function
            
        Raises:
            Exception: When both primary and fallback services fail
        """
        # Try primary service
        try:
            return self.breakers['pollinations'].call(primary_func, *args, **kwargs)
        except (CircuitBreakerOpenError, Exception) as e:
            logger.warning(f"Primary AI service failed: {e}")
            
            # Try fallback service
            try:
                return self.breakers['huggingface'].call(fallback_func, *args, **kwargs)
            except (CircuitBreakerOpenError, Exception) as fallback_e:
                logger.error(f"Fallback AI service also failed: {fallback_e}")
                raise Exception("All AI services are currently unavailable")
    
    def get_service_status(self) -> dict:
        """Get status of all AI services"""
        return {
            name: {
                'state': breaker.get_state().value,
                'stats': breaker.get_stats()
            }
            for name, breaker in self.breakers.items()
        }