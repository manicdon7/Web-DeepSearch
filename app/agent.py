import time
import logging
from typing import List, Dict, Optional

# Python 3.9 compatibility fix for pollinations
import typing
if not hasattr(typing, 'TypeAlias'):
    typing.TypeAlias = type
if not hasattr(typing, 'Self'):
    typing.Self = typing.Any
if not hasattr(typing, 'LiteralString'):
    typing.LiteralString = str

# Handle pollinations import with fallback
try:
    import pollinations as ai
    POLLINATIONS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Pollinations not available: {e}. Using Hugging Face only.")
    POLLINATIONS_AVAILABLE = False
    ai = None

from huggingface_hub import InferenceClient

from .config import settings
from .circuit_breaker import AIServiceCircuitBreaker, CircuitBreakerOpenError
from .adaptive_summary_generator import AdaptiveSummaryGenerator
from .query_analyzer import QueryAnalyzer
from .optimization_models import EnhancedSource, QueryAnalysis

# Configure logging
logger = logging.getLogger(__name__)


class EnhancedAgent:
    """
    Enhanced agent with adaptive synthesis capabilities, circuit breaker protection,
    and intelligent query analysis integration.
    """
    
    def __init__(self):
        """Initialize the enhanced agent with all optimization components."""
        self.circuit_breaker = AIServiceCircuitBreaker()
        
        # Configure circuit breaker to be more tolerant of temporary failures
        self.circuit_breaker.breakers['pollinations'].config.failure_threshold = 10
        self.circuit_breaker.breakers['pollinations'].config.recovery_timeout = 30
        self.circuit_breaker.breakers['pollinations'].config.timeout = 45
        
        self.summary_generator = AdaptiveSummaryGenerator()
        self.query_analyzer = QueryAnalyzer()
        
    def synthesize_response(
        self, 
        query: str, 
        sources: List[Dict], 
        max_retries: int = 3
    ) -> str:
        """
        Synthesize an intelligent response using adaptive summary generation
        with circuit breaker protection and fallback strategies.
        
        Args:
            query: The original search query
            sources: List of source dictionaries with scraped content
            max_retries: Maximum retry attempts for AI services
            
        Returns:
            str: Synthesized response tailored to query characteristics
        """
        try:
            # Analyze query to determine optimal synthesis approach
            query_analysis = self.query_analyzer.analyze_query(query)
            logger.info(f"Query analysis completed: complexity={query_analysis.complexity.value}, "
                       f"intent={query_analysis.intent.value}, domain={query_analysis.domain}")
            
            # Convert sources to enhanced format for adaptive generation
            enhanced_sources = self._convert_to_enhanced_sources(sources)
            
            # Generate adaptive summary using AI services with circuit breaker protection
            try:
                return self._generate_ai_summary(query, enhanced_sources, query_analysis)
                
            except Exception as e:
                logger.warning(f"AI synthesis failed: {e}")
                # Fall back to adaptive summary generator's built-in fallback
                return self._generate_fallback_response(query, enhanced_sources, query_analysis)
                
        except Exception as e:
            logger.error(f"Critical error in synthesis: {e}")
            return self._generate_emergency_fallback(query, sources)
    
    def _generate_ai_summary(
        self, 
        query: str, 
        sources: List[EnhancedSource], 
        query_analysis: QueryAnalysis
    ) -> str:
        """
        Generate summary using AI services with circuit breaker protection.
        
        Args:
            query: Original search query
            sources: Enhanced source objects
            query_analysis: Query analysis results
            
        Returns:
            str: AI-generated summary
        """
        # Create adaptive prompt using summary generator
        prompt = self.summary_generator.create_summary_prompt(
            query, sources, 
            self.summary_generator.generate_summary_config(query_analysis)
        )
        
        # Define AI service functions for circuit breaker
        def pollinations_call():
            # Use direct HTTP API to Pollinations
            return self._pollinations_http_synthesis(prompt)
        
        def huggingface_call():
            return self._huggingface_synthesis(prompt)
        
        # Use circuit breaker to call AI services with automatic fallback
        try:
            # Always try Pollinations HTTP API first, then Hugging Face
            result = self.circuit_breaker.call_with_fallback(
                pollinations_call, 
                huggingface_call
            )
            logger.info("AI synthesis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"All AI services failed: {e}")
            raise e
    
    def _pollinations_http_synthesis(self, prompt: str) -> str:
        """
        Generate synthesis using Pollinations HTTP API with retry logic.
        
        Args:
            prompt: The engineered prompt for synthesis
            
        Returns:
            str: Generated response
            
        Raises:
            Exception: When Pollinations HTTP API fails after retries
        """
        import requests
        import time
        
        logger.info("Using Pollinations HTTP API for synthesis")
        
        # Retry configuration
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Use the direct Pollinations API
                api_url = "https://text.pollinations.ai/"
                
                # Prepare the request payload with casual English instructions
                enhanced_prompt = f"""You are a helpful, friendly assistant. Always respond in English using a casual, conversational tone like you're talking to a friend. Be natural and easy to understand.

{prompt}

Remember: Keep it casual, friendly, and always in English!"""
                
                payload = {
                    "messages": [
                        {
                            "role": "user", 
                            "content": enhanced_prompt
                        }
                    ],
                    "model": "openai",
                    "jsonMode": False
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "text/plain"
                }
                
                # Make the API request with timeout
                response = requests.post(
                    api_url, 
                    json=payload, 
                    headers=headers, 
                    timeout=45  # Increased timeout
                )
                
                if response.status_code == 200:
                    result = response.text.strip()
                    if result and not result.startswith("An error occurred") and len(result) > 20:
                        logger.info(f"Pollinations HTTP API synthesis completed successfully on attempt {attempt + 1}")
                        return result
                    else:
                        raise Exception(f"Pollinations returned invalid response: {result[:100]}")
                elif response.status_code == 502:
                    # 502 Bad Gateway - service temporarily down, retry
                    raise Exception(f"Service temporarily unavailable (502)")
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                logger.warning(f"Pollinations API attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    logger.error(f"Pollinations HTTP API synthesis failed after {max_retries} attempts")
                    raise e
    
    def _alternative_ai_synthesis(self, prompt: str) -> str:
        """
        Generate synthesis using alternative free AI APIs.
        
        Args:
            prompt: The engineered prompt for synthesis
            
        Returns:
            str: Generated response
        """
        import requests
        
        logger.info("Using alternative AI API for synthesis")
        
        # Try Groq free API (if available)
        try:
            api_url = "https://api.groq.com/openai/v1/chat/completions"
            
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "model": "llama3-8b-8192",
                "max_tokens": 1024,
                "temperature": 0.7
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer gsk_free_api_key"  # This would need a real key
            }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                raise Exception(f"Groq API failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Alternative AI API failed: {e}")
            
        # If all AI services fail, create a smart summary from the sources
        return self._create_smart_fallback_summary(prompt)
    
    def _create_smart_fallback_summary(self, prompt: str) -> str:
        """
        Create an intelligent summary when AI services are unavailable.
        Uses text processing techniques to extract key information.
        
        Args:
            prompt: The original prompt containing query and sources
            
        Returns:
            str: Intelligent summary based on source content
        """
        logger.info("Creating smart fallback summary using text processing")
        
        try:
            # Extract query and sources from prompt
            lines = prompt.split('\n')
            query = ""
            sources_content = []
            
            # Parse the prompt to extract query and source content
            for i, line in enumerate(lines):
                if "create a summary for the query:" in line.lower():
                    # Extract query from the line
                    query_start = line.lower().find("query:") + 6
                    query_end = line.find("'", query_start + 1)
                    if query_end > query_start:
                        query = line[query_start:query_end].strip(" '\"")
                elif line.startswith("Source ") and ":" in line:
                    # Extract source content
                    content_start = i + 1
                    if content_start < len(lines):
                        content = lines[content_start].strip()
                        if content and len(content) > 50:  # Only use substantial content
                            sources_content.append(content)
            
            if not query:
                query = "the requested topic"
            
            # Create intelligent summary
            if not sources_content:
                return f"Hey, I looked through the sources but couldn't find much solid info about {query}. The sources might not have had the details you're looking for."
            
            # Extract key information from sources
            key_points = []
            for content in sources_content[:5]:  # Use top 5 sources
                # Extract sentences that seem most relevant
                sentences = content.split('.')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if (len(sentence) > 30 and 
                        any(keyword in sentence.lower() for keyword in query.lower().split()) and
                        not sentence.startswith('http')):
                        key_points.append(sentence)
                        if len(key_points) >= 8:  # Limit to 8 key points
                            break
                if len(key_points) >= 8:
                    break
            
            # Create casual, conversational summary
            if key_points:
                summary_parts = [
                    f"Here's what I found about {query}:",
                    ""
                ]
                
                # Group similar points and create a coherent summary
                unique_points = []
                for point in key_points:
                    # Avoid duplicate information
                    is_duplicate = False
                    for existing in unique_points:
                        if len(set(point.lower().split()) & set(existing.lower().split())) > len(point.split()) * 0.6:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        unique_points.append(point)
                
                # Create the casual summary
                for i, point in enumerate(unique_points[:5]):  # Use top 5 unique points
                    # Make it more conversational
                    casual_point = point.strip()
                    if not casual_point.endswith('.'):
                        casual_point += '.'
                    summary_parts.append(f"• {casual_point}")
                
                summary_parts.append("")
                summary_parts.append("Hope this helps! Let me know if you need more details about any of these points.")
                
                return "\n".join(summary_parts)
            else:
                return f"I found some info about {query}, but it's pretty scattered across the sources. There seem to be various technical details and recent developments, but I'd need better sources to give you a clearer picture."
                
        except Exception as e:
            logger.error(f"Smart fallback summary creation failed: {e}")
            return f"Sorry, I ran into some technical issues while trying to process the info about {query}. Mind giving it another shot?"
    
    def _huggingface_synthesis(self, prompt: str) -> str:
        """
        Generate synthesis using Hugging Face Inference API or alternative free APIs.
        
        Args:
            prompt: The engineered prompt for synthesis
            
        Returns:
            str: Generated response
            
        Raises:
            Exception: When all Hugging Face methods fail
        """
        logger.info("Using Hugging Face Inference API for synthesis")
        
        # Try official Hugging Face API first
        if settings.huggingface_token and settings.huggingface_token != "test-token":
            try:
                client = InferenceClient(token=settings.huggingface_token)
                
                response = client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    model="mistralai/Mistral-7B-Instruct-v0.2",
                    max_tokens=1024,
                )
                
                result = response.choices[0].message.content.strip()
                logger.info("Hugging Face synthesis completed successfully")
                return result
                
            except Exception as e:
                logger.warning(f"Official Hugging Face API failed: {e}")
        
        # Try alternative free API
        try:
            return self._alternative_ai_synthesis(prompt)
            
        except Exception as e:
            logger.error(f"Hugging Face synthesis failed: {e}")
            raise e
    
    def _generate_fallback_response(
        self, 
        query: str, 
        sources: List[EnhancedSource], 
        query_analysis: QueryAnalysis
    ) -> str:
        """
        Generate fallback response when AI services are unavailable.
        
        Args:
            query: Original search query
            sources: Enhanced source objects
            query_analysis: Query analysis results
            
        Returns:
            str: Fallback summary generated without AI services
        """
        logger.info("Generating fallback response using adaptive summary generator")
        
        try:
            # Use adaptive summary generator's built-in fallback
            fallback_summary = self.summary_generator.generate_summary(
                query, sources, query_analysis
            )
            
            # Add service status information
            service_status = self.circuit_breaker.get_service_status()
            status_info = self._format_service_status(service_status)
            
            return f"{fallback_summary}\n\n[Note: Generated using fallback method due to AI service unavailability. {status_info}]"
            
        except Exception as e:
            logger.error(f"Fallback generation failed: {e}")
            return self._generate_emergency_fallback(query, [s.__dict__ for s in sources])
    
    def _generate_emergency_fallback(self, query: str, sources: List[Dict]) -> str:
        """
        Generate emergency fallback when all other methods fail.
        
        Args:
            query: Original search query
            sources: Raw source dictionaries
            
        Returns:
            str: Basic emergency response
        """
        logger.warning("Using emergency fallback response generation")
        
        if not sources:
            return f"I apologize, but I couldn't find any relevant sources for your query: '{query}'. Please try rephrasing your question or check your internet connection."
        
        # Extract basic information from sources
        source_summaries = []
        for i, source in enumerate(sources[:3], 1):  # Limit to first 3 sources
            content = source.get('main_content', '')
            if content:
                # Take first 200 characters as a basic summary
                summary = content[:200].strip()
                if len(content) > 200:
                    summary += "..."
                source_summaries.append(f"Source {i}: {summary}")
        
        basic_response = f"Based on available sources regarding '{query}':\n\n" + "\n\n".join(source_summaries)
        
        return f"{basic_response}\n\n[Note: This is a basic response due to service limitations. For better results, please try again later.]"
    
    def _convert_to_enhanced_sources(self, sources: List[Dict]) -> List[EnhancedSource]:
        """
        Convert raw source dictionaries to EnhancedSource objects.
        
        Args:
            sources: List of raw source dictionaries
            
        Returns:
            List[EnhancedSource]: Converted enhanced source objects
        """
        enhanced_sources = []
        
        for source in sources:
            try:
                enhanced_source = EnhancedSource(
                    url=source.get('url', ''),
                    title=source.get('title', ''),
                    main_content=source.get('main_content', ''),
                    images=source.get('images', []),
                    categories=source.get('categories', []),
                    word_count=len(source.get('main_content', '').split()),
                    # These will be None for now, but could be populated by other components
                    content_quality=None,
                    scraping_duration=0.0,
                    relevance_score=0.0,
                    last_updated=None
                )
                enhanced_sources.append(enhanced_source)
                
            except Exception as e:
                logger.warning(f"Failed to convert source {source.get('url', 'unknown')}: {e}")
                continue
        
        return enhanced_sources
    
    def _format_service_status(self, service_status: Dict) -> str:
        """
        Format service status information for user display.
        
        Args:
            service_status: Dictionary of service status information
            
        Returns:
            str: Formatted status message
        """
        status_parts = []
        for service, status in service_status.items():
            state = status['state']
            if state == 'open':
                status_parts.append(f"{service}: unavailable")
            elif state == 'half_open':
                status_parts.append(f"{service}: recovering")
            else:
                status_parts.append(f"{service}: available")
        
        return "Service status: " + ", ".join(status_parts)
    
    def get_service_health(self) -> Dict:
        """
        Get current health status of all AI services.
        
        Returns:
            Dict: Service health information
        """
        return self.circuit_breaker.get_service_status()


# Legacy function for backward compatibility
def huggingface_fallback(prompt: str) -> Optional[str]:
    """
    Legacy function for backward compatibility.
    Uses the Hugging Face Inference API as a fallback if Pollinations fails.
    """
    logger.warning("Using legacy huggingface_fallback function. Consider using EnhancedAgent instead.")
    
    try:
        client = InferenceClient(token=settings.huggingface_token)
        
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="mistralai/Mistral-7B-Instruct-v0.2",
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Hugging Face fallback failed: {e}")
        return None


# Legacy function for backward compatibility
def get_ai_synthesis(query: str, sources: List[Dict], max_retries: int = 5, backoff_factor: float = 2.0) -> str:
    """
    Legacy function for backward compatibility.
    Synthesizes an answer using Pollinations.ai, with a fallback to Hugging Face.
    """
    logger.warning("Using legacy get_ai_synthesis function. Consider using EnhancedAgent instead.")
    
    # Use enhanced agent for better functionality
    enhanced_agent = EnhancedAgent()
    return enhanced_agent.synthesize_response(query, sources, max_retries)
