"""
Unit tests for the enhanced agent with adaptive synthesis capabilities.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agent import EnhancedAgent, huggingface_fallback, get_ai_synthesis
from app.optimization_models import QueryAnalysis, QueryComplexity, QueryIntent, SummaryLength
from app.circuit_breaker import CircuitBreakerOpenError


class TestEnhancedAgent:
    """Test cases for the EnhancedAgent class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = EnhancedAgent()
        self.sample_query = "What is machine learning?"
        self.sample_sources = [
            {
                'url': 'https://example.com/ml',
                'title': 'Machine Learning Basics',
                'main_content': 'Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed.',
                'images': [],
                'categories': ['technology']
            },
            {
                'url': 'https://example.com/ai',
                'title': 'AI Overview',
                'main_content': 'Artificial intelligence encompasses various technologies including machine learning, deep learning, and neural networks.',
                'images': [],
                'categories': ['technology']
            }
        ]
    
    @patch('app.agent.logger')
    def test_synthesize_response_success(self, mock_logger):
        """Test successful response synthesis with AI services."""
        with patch.object(self.agent.query_analyzer, 'analyze_query') as mock_analyze, \
             patch.object(self.agent, '_generate_ai_summary') as mock_ai_summary:
            
            # Mock query analysis
            mock_analysis = QueryAnalysis(
                complexity=QueryComplexity.SIMPLE,
                domain='technology',
                intent=QueryIntent.FACTUAL,
                expected_length=SummaryLength.SHORT,
                recency_importance=0.2
            )
            mock_analyze.return_value = mock_analysis
            
            # Mock AI summary generation
            expected_response = "Machine learning is a technology that enables computers to learn from data."
            mock_ai_summary.return_value = expected_response
            
            # Test synthesis
            result = self.agent.synthesize_response(self.sample_query, self.sample_sources)
            
            assert result == expected_response
            mock_analyze.assert_called_once_with(self.sample_query)
            mock_ai_summary.assert_called_once()
    
    @patch('app.agent.logger')
    def test_synthesize_response_ai_failure_fallback(self, mock_logger):
        """Test fallback response when AI services fail."""
        with patch.object(self.agent.query_analyzer, 'analyze_query') as mock_analyze, \
             patch.object(self.agent, '_generate_ai_summary') as mock_ai_summary, \
             patch.object(self.agent, '_generate_fallback_response') as mock_fallback:
            
            # Mock query analysis
            mock_analysis = QueryAnalysis(
                complexity=QueryComplexity.SIMPLE,
                domain='technology',
                intent=QueryIntent.FACTUAL,
                expected_length=SummaryLength.SHORT,
                recency_importance=0.2
            )
            mock_analyze.return_value = mock_analysis
            
            # Mock AI summary failure
            mock_ai_summary.side_effect = Exception("AI service unavailable")
            
            # Mock fallback response
            expected_fallback = "Fallback response about machine learning."
            mock_fallback.return_value = expected_fallback
            
            # Test synthesis
            result = self.agent.synthesize_response(self.sample_query, self.sample_sources)
            
            assert result == expected_fallback
            mock_fallback.assert_called_once()
    
    @patch('app.agent.logger')
    def test_synthesize_response_critical_error(self, mock_logger):
        """Test emergency fallback when critical errors occur."""
        with patch.object(self.agent.query_analyzer, 'analyze_query') as mock_analyze, \
             patch.object(self.agent, '_generate_emergency_fallback') as mock_emergency:
            
            # Mock query analysis failure
            mock_analyze.side_effect = Exception("Critical error")
            
            # Mock emergency fallback
            expected_emergency = "Emergency fallback response."
            mock_emergency.return_value = expected_emergency
            
            # Test synthesis
            result = self.agent.synthesize_response(self.sample_query, self.sample_sources)
            
            assert result == expected_emergency
            mock_emergency.assert_called_once_with(self.sample_query, self.sample_sources)
    
    @patch('pollinations.Text')
    @patch('app.agent.logger')
    def test_generate_ai_summary_pollinations_success(self, mock_logger, mock_pollinations):
        """Test successful AI summary generation using Pollinations."""
        # Mock Pollinations response
        mock_model = Mock()
        mock_model.return_value = "AI generated summary about machine learning."
        mock_pollinations.return_value = mock_model
        
        # Mock query analysis
        query_analysis = QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain='technology',
            intent=QueryIntent.FACTUAL,
            expected_length=SummaryLength.SHORT,
            recency_importance=0.2
        )
        
        # Convert sources to enhanced format
        enhanced_sources = self.agent._convert_to_enhanced_sources(self.sample_sources)
        
        # Test AI summary generation
        result = self.agent._generate_ai_summary(self.sample_query, enhanced_sources, query_analysis)
        
        assert "AI generated summary about machine learning." == result
        mock_pollinations.assert_called_once_with(model="openai")
    
    @patch('app.agent.InferenceClient')
    @patch('app.agent.logger')
    def test_generate_ai_summary_huggingface_fallback(self, mock_logger, mock_inference_client):
        """Test AI summary generation falling back to Hugging Face."""
        # Mock Hugging Face response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hugging Face generated summary."
        mock_client.chat_completion.return_value = mock_response
        mock_inference_client.return_value = mock_client
        
        # Mock Pollinations failure and circuit breaker behavior
        with patch.object(self.agent.circuit_breaker, 'call_with_fallback') as mock_circuit:
            mock_circuit.side_effect = lambda primary, fallback: fallback()
            
            # Mock query analysis
            query_analysis = QueryAnalysis(
                complexity=QueryComplexity.SIMPLE,
                domain='technology',
                intent=QueryIntent.FACTUAL,
                expected_length=SummaryLength.SHORT,
                recency_importance=0.2
            )
            
            # Convert sources to enhanced format
            enhanced_sources = self.agent._convert_to_enhanced_sources(self.sample_sources)
            
            # Test AI summary generation
            result = self.agent._generate_ai_summary(self.sample_query, enhanced_sources, query_analysis)
            
            assert "Hugging Face generated summary." == result
    
    @patch('app.agent.logger')
    def test_generate_fallback_response(self, mock_logger):
        """Test fallback response generation."""
        with patch.object(self.agent.summary_generator, 'generate_summary') as mock_generate, \
             patch.object(self.agent.circuit_breaker, 'get_service_status') as mock_status:
            
            # Mock summary generation
            mock_generate.return_value = "Fallback summary content."
            
            # Mock service status
            mock_status.return_value = {
                'pollinations': {'state': 'open'},
                'huggingface': {'state': 'closed'}
            }
            
            # Mock query analysis
            query_analysis = QueryAnalysis(
                complexity=QueryComplexity.SIMPLE,
                domain='technology',
                intent=QueryIntent.FACTUAL,
                expected_length=SummaryLength.SHORT,
                recency_importance=0.2
            )
            
            # Convert sources to enhanced format
            enhanced_sources = self.agent._convert_to_enhanced_sources(self.sample_sources)
            
            # Test fallback generation
            result = self.agent._generate_fallback_response(
                self.sample_query, enhanced_sources, query_analysis
            )
            
            assert "Fallback summary content." in result
            assert "[Note: Generated using fallback method" in result
            assert "Service status:" in result
    
    def test_generate_emergency_fallback_with_sources(self):
        """Test emergency fallback with available sources."""
        result = self.agent._generate_emergency_fallback(self.sample_query, self.sample_sources)
        
        assert self.sample_query in result
        assert "Source 1:" in result
        assert "Source 2:" in result
        assert "[Note: This is a basic response due to service limitations" in result
    
    def test_generate_emergency_fallback_no_sources(self):
        """Test emergency fallback with no sources."""
        result = self.agent._generate_emergency_fallback(self.sample_query, [])
        
        assert self.sample_query in result
        assert "couldn't find any relevant sources" in result
        assert "try rephrasing" in result
    
    def test_convert_to_enhanced_sources(self):
        """Test conversion of raw sources to enhanced format."""
        enhanced_sources = self.agent._convert_to_enhanced_sources(self.sample_sources)
        
        assert len(enhanced_sources) == 2
        assert enhanced_sources[0].url == 'https://example.com/ml'
        assert enhanced_sources[0].title == 'Machine Learning Basics'
        assert enhanced_sources[0].word_count > 0
        assert enhanced_sources[1].url == 'https://example.com/ai'
    
    def test_convert_to_enhanced_sources_with_invalid_data(self):
        """Test conversion handling invalid source data."""
        invalid_sources = [
            {'url': 'https://valid.com', 'title': 'Valid', 'main_content': 'Content'},
            {'invalid': 'data'},  # Missing required fields
            None  # Invalid source
        ]
        
        with patch('app.agent.logger'):
            enhanced_sources = self.agent._convert_to_enhanced_sources(invalid_sources)
        
        # Should only convert the valid source
        assert len(enhanced_sources) == 1
        assert enhanced_sources[0].url == 'https://valid.com'
    
    def test_format_service_status(self):
        """Test service status formatting."""
        service_status = {
            'pollinations': {'state': 'open'},
            'huggingface': {'state': 'closed'},
            'backup': {'state': 'half_open'}
        }
        
        result = self.agent._format_service_status(service_status)
        
        assert "Service status:" in result
        assert "pollinations: unavailable" in result
        assert "huggingface: available" in result
        assert "backup: recovering" in result
    
    def test_get_service_health(self):
        """Test service health retrieval."""
        with patch.object(self.agent.circuit_breaker, 'get_service_status') as mock_status:
            expected_status = {'pollinations': {'state': 'closed'}}
            mock_status.return_value = expected_status
            
            result = self.agent.get_service_health()
            
            assert result == expected_status
            mock_status.assert_called_once()


class TestLegacyFunctions:
    """Test cases for legacy compatibility functions."""
    
    @patch('app.agent.InferenceClient')
    @patch('app.agent.logger')
    def test_huggingface_fallback_success(self, mock_logger, mock_inference_client):
        """Test successful Hugging Face fallback."""
        # Mock Hugging Face response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "  Fallback response  "
        mock_client.chat_completion.return_value = mock_response
        mock_inference_client.return_value = mock_client
        
        result = huggingface_fallback("Test prompt")
        
        assert result == "Fallback response"
        mock_client.chat_completion.assert_called_once()
    
    @patch('app.agent.InferenceClient')
    @patch('app.agent.logger')
    def test_huggingface_fallback_failure(self, mock_logger, mock_inference_client):
        """Test Hugging Face fallback failure."""
        # Mock Hugging Face failure
        mock_inference_client.side_effect = Exception("API error")
        
        result = huggingface_fallback("Test prompt")
        
        assert result is None
    
    @patch('app.agent.EnhancedAgent')
    @patch('app.agent.logger')
    def test_get_ai_synthesis_legacy(self, mock_logger, mock_enhanced_agent):
        """Test legacy get_ai_synthesis function."""
        # Mock enhanced agent
        mock_agent_instance = Mock()
        mock_agent_instance.synthesize_response.return_value = "Legacy response"
        mock_enhanced_agent.return_value = mock_agent_instance
        
        sources = [{'url': 'test.com', 'main_content': 'content'}]
        result = get_ai_synthesis("test query", sources, max_retries=3)
        
        assert result == "Legacy response"
        mock_agent_instance.synthesize_response.assert_called_once_with("test query", sources, 3)


class TestIntegrationScenarios:
    """Integration test scenarios for enhanced agent."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.agent = EnhancedAgent()
    
    @patch('pollinations.Text')
    @patch('app.agent.logger')
    def test_end_to_end_simple_query(self, mock_logger, mock_pollinations):
        """Test end-to-end processing of a simple factual query."""
        # Mock Pollinations success
        mock_model = Mock()
        mock_model.return_value = "Python is a programming language."
        mock_pollinations.return_value = mock_model
        
        query = "What is Python?"
        sources = [{
            'url': 'https://python.org',
            'title': 'Python Programming',
            'main_content': 'Python is a high-level programming language known for its simplicity.',
            'images': [],
            'categories': ['programming']
        }]
        
        result = self.agent.synthesize_response(query, sources)
        
        assert "Python is a programming language." == result
    
    @patch('app.agent.InferenceClient')
    @patch('pollinations.Text')
    @patch('app.agent.logger')
    def test_end_to_end_with_service_failure(self, mock_logger, mock_pollinations, mock_inference_client):
        """Test end-to-end processing with primary service failure."""
        # Mock Pollinations failure
        mock_pollinations.side_effect = Exception("Service unavailable")
        
        # Mock Hugging Face success
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hugging Face response about Python."
        mock_client.chat_completion.return_value = mock_response
        mock_inference_client.return_value = mock_client
        
        query = "What is Python programming?"
        sources = [{
            'url': 'https://python.org',
            'title': 'Python Programming',
            'main_content': 'Python is a versatile programming language.',
            'images': [],
            'categories': ['programming']
        }]
        
        # Patch circuit breaker to allow fallback
        with patch.object(self.agent.circuit_breaker, 'call_with_fallback') as mock_circuit:
            mock_circuit.side_effect = lambda primary, fallback: fallback()
            
            result = self.agent.synthesize_response(query, sources)
            
            assert "Hugging Face response about Python." == result
    
    @patch('app.agent.logger')
    def test_end_to_end_complete_service_failure(self, mock_logger):
        """Test end-to-end processing with complete AI service failure."""
        query = "What is machine learning?"
        sources = [{
            'url': 'https://ml.com',
            'title': 'ML Basics',
            'main_content': 'Machine learning enables computers to learn from data without explicit programming.',
            'images': [],
            'categories': ['ai']
        }]
        
        # Mock complete AI service failure
        with patch.object(self.agent.circuit_breaker, 'call_with_fallback') as mock_circuit:
            mock_circuit.side_effect = Exception("All services down")
            
            result = self.agent.synthesize_response(query, sources)
            
            # Should get fallback response
            assert "machine learning" in result.lower()
            assert "[Note: Generated using fallback method" in result