"""
Simple unit tests for the enhanced agent functionality (without external dependencies).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock pollinations before importing
sys.modules['pollinations'] = Mock()

from app.optimization_models import QueryAnalysis, QueryComplexity, QueryIntent, SummaryLength


class TestEnhancedAgentCore:
    """Test core functionality of enhanced agent without external dependencies."""
    
    def test_convert_to_enhanced_sources(self):
        """Test conversion of raw sources to enhanced format."""
        # Import here to avoid pollinations import issues
        with patch.dict('sys.modules', {'pollinations': Mock()}):
            from app.agent import EnhancedAgent
            
            agent = EnhancedAgent()
            
            sample_sources = [
                {
                    'url': 'https://example.com/test',
                    'title': 'Test Article',
                    'main_content': 'This is test content with multiple words.',
                    'images': [],
                    'categories': ['test']
                }
            ]
            
            enhanced_sources = agent._convert_to_enhanced_sources(sample_sources)
            
            assert len(enhanced_sources) == 1
            assert enhanced_sources[0].url == 'https://example.com/test'
            assert enhanced_sources[0].title == 'Test Article'
            assert enhanced_sources[0].word_count == 8  # "This is test content with multiple words."
    
    def test_format_service_status(self):
        """Test service status formatting."""
        with patch.dict('sys.modules', {'pollinations': Mock()}):
            from app.agent import EnhancedAgent
            
            agent = EnhancedAgent()
            
            service_status = {
                'pollinations': {'state': 'open'},
                'huggingface': {'state': 'closed'},
                'backup': {'state': 'half_open'}
            }
            
            result = agent._format_service_status(service_status)
            
            assert "Service status:" in result
            assert "pollinations: unavailable" in result
            assert "huggingface: available" in result
            assert "backup: recovering" in result
    
    def test_generate_emergency_fallback_with_sources(self):
        """Test emergency fallback response generation."""
        with patch.dict('sys.modules', {'pollinations': Mock()}):
            from app.agent import EnhancedAgent
            
            agent = EnhancedAgent()
            
            query = "What is Python?"
            sources = [
                {
                    'url': 'https://python.org',
                    'title': 'Python Programming',
                    'main_content': 'Python is a high-level programming language known for its simplicity and readability.',
                    'images': [],
                    'categories': ['programming']
                }
            ]
            
            result = agent._generate_emergency_fallback(query, sources)
            
            assert query in result
            assert "Source 1:" in result
            assert "Python is a high-level programming language" in result
            assert "[Note: This is a basic response due to service limitations" in result
    
    def test_generate_emergency_fallback_no_sources(self):
        """Test emergency fallback with no sources."""
        with patch.dict('sys.modules', {'pollinations': Mock()}):
            from app.agent import EnhancedAgent
            
            agent = EnhancedAgent()
            
            query = "What is machine learning?"
            sources = []
            
            result = agent._generate_emergency_fallback(query, sources)
            
            assert query in result
            assert "couldn't find any relevant sources" in result
            assert "try rephrasing" in result


class TestLegacyFunctionsSimple:
    """Test legacy functions with mocked dependencies."""
    
    @patch('app.agent.InferenceClient')
    def test_huggingface_fallback_success(self, mock_inference_client):
        """Test successful Hugging Face fallback."""
        with patch.dict('sys.modules', {'pollinations': Mock()}):
            from app.agent import huggingface_fallback
            
            # Mock Hugging Face response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "  Test response  "
            mock_client.chat_completion.return_value = mock_response
            mock_inference_client.return_value = mock_client
            
            result = huggingface_fallback("Test prompt")
            
            assert result == "Test response"
            mock_client.chat_completion.assert_called_once()
    
    @patch('app.agent.EnhancedAgent')
    def test_get_ai_synthesis_legacy(self, mock_enhanced_agent):
        """Test legacy get_ai_synthesis function."""
        with patch.dict('sys.modules', {'pollinations': Mock()}):
            from app.agent import get_ai_synthesis
            
            # Mock enhanced agent
            mock_agent_instance = Mock()
            mock_agent_instance.synthesize_response.return_value = "Legacy response"
            mock_enhanced_agent.return_value = mock_agent_instance
            
            sources = [{'url': 'test.com', 'main_content': 'content'}]
            result = get_ai_synthesis("test query", sources, max_retries=3)
            
            assert result == "Legacy response"
            mock_agent_instance.synthesize_response.assert_called_once_with("test query", sources, 3)


if __name__ == "__main__":
    pytest.main([__file__])