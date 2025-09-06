"""
Content Quality Assessor for evaluating scraped content quality and relevance.
"""
import re
import math
from typing import List, Dict, Set
from collections import Counter
from difflib import SequenceMatcher

from .optimization_models import ContentQuality, QueryAnalysis, EnhancedSource


class ContentQualityAssessor:
    """
    Evaluates content quality and relevance in real-time to optimize scraping decisions.
    """
    
    def __init__(self, 
                 min_content_length: int = 100,
                 max_duplicate_threshold: float = 0.8,
                 min_information_density: float = 0.3,
                 sufficient_content_threshold: int = 3):
        """
        Initialize the Content Quality Assessor.
        
        Args:
            min_content_length: Minimum content length to consider quality
            max_duplicate_threshold: Maximum similarity threshold for duplicate detection
            min_information_density: Minimum information density threshold
            sufficient_content_threshold: Number of quality sources needed to stop scraping
        """
        self.min_content_length = min_content_length
        self.max_duplicate_threshold = max_duplicate_threshold
        self.min_information_density = min_information_density
        self.sufficient_content_threshold = sufficient_content_threshold
        
        # Common stop words for information density calculation
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
    
    def assess_content(self, content: Dict, query_analysis: QueryAnalysis) -> ContentQuality:
        """
        Assess the quality of scraped content.
        
        Args:
            content: Dictionary containing scraped content (title, main_content, etc.)
            query_analysis: Analysis results from the query analyzer
            
        Returns:
            ContentQuality object with assessment results
        """
        main_content = content.get('main_content', '')
        title = content.get('title', '')
        
        # Calculate relevance score
        relevance_score = self._calculate_relevance_score(
            main_content, title, query_analysis
        )
        
        # Calculate content length
        content_length = len(main_content.split())
        
        # Calculate information density
        information_density = self._calculate_information_density(main_content)
        
        # Calculate quality indicators
        quality_indicators = self._calculate_quality_indicators(
            main_content, title, content
        )
        
        return ContentQuality(
            relevance_score=relevance_score,
            content_length=content_length,
            information_density=information_density,
            duplicate_content=False,  # Will be set by duplicate detection
            quality_indicators=quality_indicators
        )
    
    def _calculate_relevance_score(self, content: str, title: str, 
                                 query_analysis: QueryAnalysis) -> float:
        """
        Calculate relevance score based on query analysis and content.
        
        Args:
            content: Main content text
            title: Content title
            query_analysis: Query analysis results
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not content and not title:
            return 0.0
        
        # Extract keywords from domain and intent
        domain_keywords = self._get_domain_keywords(query_analysis.domain)
        intent_keywords = self._get_intent_keywords(query_analysis.intent)
        
        # Combine all text for analysis
        full_text = f"{title} {content}".lower()
        
        # Calculate keyword presence scores
        domain_score = self._calculate_keyword_presence(full_text, domain_keywords)
        intent_score = self._calculate_keyword_presence(full_text, intent_keywords)
        
        # Weight scores based on query complexity
        if query_analysis.complexity.value == 'simple':
            # Simple queries prioritize direct keyword matches
            relevance_score = 0.7 * domain_score + 0.3 * intent_score
        elif query_analysis.complexity.value == 'moderate':
            # Moderate queries balance domain and intent
            relevance_score = 0.5 * domain_score + 0.5 * intent_score
        else:  # complex
            # Complex queries prioritize intent understanding
            relevance_score = 0.3 * domain_score + 0.7 * intent_score
        
        return min(1.0, relevance_score)
    
    def _calculate_information_density(self, content: str) -> float:
        """
        Calculate information density of content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Information density score between 0.0 and 1.0
        """
        if not content:
            return 0.0
        
        words = content.lower().split()
        if not words:
            return 0.0
        
        # Count meaningful words (not stop words)
        meaningful_words = [word for word in words if word not in self.stop_words]
        
        # Calculate unique word ratio
        unique_words = len(set(meaningful_words))
        total_meaningful = len(meaningful_words)
        
        if total_meaningful == 0:
            return 0.0
        
        # Information density based on unique meaningful words ratio
        density = unique_words / total_meaningful
        
        # Adjust for content length (longer content tends to have lower density)
        length_factor = min(1.0, math.log(len(words) + 1) / 10)
        
        return min(1.0, density * length_factor)
    
    def _calculate_quality_indicators(self, content: str, title: str, 
                                    full_content: Dict) -> Dict[str, float]:
        """
        Calculate various quality indicators for the content.
        
        Args:
            content: Main content text
            title: Content title
            full_content: Full content dictionary
            
        Returns:
            Dictionary of quality indicator scores
        """
        indicators = {}
        
        # Structure quality (presence of headings, lists, etc.)
        indicators['structure_score'] = self._assess_structure_quality(content)
        
        # Readability score (sentence length, complexity)
        indicators['readability_score'] = self._assess_readability(content)
        
        # Title relevance to content
        indicators['title_relevance'] = self._assess_title_relevance(title, content)
        
        # Content completeness (presence of images, categories, etc.)
        indicators['completeness_score'] = self._assess_completeness(full_content)
        
        # Freshness indicator (if available)
        indicators['freshness_score'] = self._assess_freshness(full_content)
        
        return indicators
    
    def _assess_structure_quality(self, content: str) -> float:
        """Assess the structural quality of content."""
        if not content:
            return 0.0
        
        score = 0.0
        
        # Check for headings (markdown or HTML-like patterns)
        heading_patterns = [r'^#{1,6}\s', r'<h[1-6]>', r'^[A-Z][^.!?]*:$']
        for pattern in heading_patterns:
            if re.search(pattern, content, re.MULTILINE):
                score += 0.2
                break
        
        # Check for lists
        list_patterns = [r'^\s*[-*+]\s', r'^\s*\d+\.\s', r'<li>', r'<ul>', r'<ol>']
        for pattern in list_patterns:
            if re.search(pattern, content, re.MULTILINE):
                score += 0.2
                break
        
        # Check for paragraphs (multiple line breaks)
        if len(re.findall(r'\n\s*\n', content)) >= 2:
            score += 0.2
        
        # Check for proper sentence structure
        sentences = re.split(r'[.!?]+', content)
        if len(sentences) >= 3:
            score += 0.2
        
        # Check for balanced sentence lengths
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        if sentence_lengths:
            avg_length = sum(sentence_lengths) / len(sentence_lengths)
            if 10 <= avg_length <= 25:  # Good sentence length range
                score += 0.2
        
        return min(1.0, score)
    
    def _assess_readability(self, content: str) -> float:
        """Assess readability of content."""
        if not content:
            return 0.0
        
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        words = content.split()
        if not words:
            return 0.0
        
        # Calculate average sentence length
        avg_sentence_length = len(words) / len(sentences)
        
        # Calculate average word length
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Simple readability score (inverse of complexity)
        # Optimal: 15-20 words per sentence, 4-6 characters per word
        sentence_score = 1.0 - abs(avg_sentence_length - 17.5) / 17.5
        word_score = 1.0 - abs(avg_word_length - 5) / 5
        
        readability = (sentence_score + word_score) / 2
        return max(0.0, min(1.0, readability))
    
    def _assess_title_relevance(self, title: str, content: str) -> float:
        """Assess how relevant the title is to the content."""
        if not title or not content:
            return 0.0
        
        title_words = set(title.lower().split())
        content_words = set(content.lower().split())
        
        if not title_words:
            return 0.0
        
        # Calculate overlap between title and content
        overlap = len(title_words.intersection(content_words))
        relevance = overlap / len(title_words)
        
        return min(1.0, relevance)
    
    def _assess_completeness(self, full_content: Dict) -> float:
        """Assess completeness of content structure."""
        score = 0.0
        
        # Check for various content elements
        if full_content.get('title'):
            score += 0.3
        if full_content.get('main_content'):
            score += 0.4
        if full_content.get('images'):
            score += 0.1
        if full_content.get('categories'):
            score += 0.1
        if full_content.get('url'):
            score += 0.1
        
        return min(1.0, score)
    
    def _assess_freshness(self, full_content: Dict) -> float:
        """Assess content freshness if date information is available."""
        # This is a placeholder - in real implementation, you'd parse
        # publication dates, last modified dates, etc.
        return 0.5  # Neutral score when freshness can't be determined
    
    def detect_duplicate_content(self, content_list: List[ContentQuality], 
                               content_texts: List[str]) -> List[ContentQuality]:
        """
        Detect and mark duplicate content across multiple sources.
        
        Args:
            content_list: List of ContentQuality objects to check
            content_texts: Corresponding list of content text strings
            
        Returns:
            Updated list of ContentQuality objects with duplicate flags set
        """
        if len(content_list) != len(content_texts):
            raise ValueError("content_list and content_texts must have same length")
        
        # Create a copy to avoid modifying the original
        updated_content = []
        
        for i, (quality, text) in enumerate(zip(content_list, content_texts)):
            is_duplicate = False
            
            # Compare with all previous content
            for j in range(i):
                similarity = self._calculate_text_similarity(text, content_texts[j])
                if similarity > self.max_duplicate_threshold:
                    is_duplicate = True
                    break
            
            # Create new ContentQuality object with updated duplicate flag
            updated_quality = ContentQuality(
                relevance_score=quality.relevance_score,
                content_length=quality.content_length,
                information_density=quality.information_density,
                duplicate_content=is_duplicate,
                quality_indicators=quality.quality_indicators
            )
            updated_content.append(updated_quality)
        
        return updated_content
    
    def should_continue_scraping(self, gathered_content: List[ContentQuality]) -> bool:
        """
        Determine if scraping should continue based on gathered content quality.
        
        Args:
            gathered_content: List of ContentQuality objects from scraped sources
            
        Returns:
            True if scraping should continue, False if sufficient content gathered
        """
        if not gathered_content:
            return True
        
        # Filter out duplicate and low-quality content
        quality_content = [
            content for content in gathered_content
            if (not content.duplicate_content and 
                content.relevance_score >= 0.5 and
                content.information_density >= self.min_information_density and
                content.content_length >= self.min_content_length)
        ]
        
        # Check if we have sufficient quality content
        if len(quality_content) >= self.sufficient_content_threshold:
            return False
        
        # Check if we have good coverage (high relevance scores)
        high_relevance_content = [
            content for content in quality_content
            if content.relevance_score >= 0.8
        ]
        
        # If we have multiple high-relevance sources, we might have enough
        if len(high_relevance_content) >= 2:
            total_content_length = sum(content.content_length for content in quality_content)
            # Stop if we have substantial content (>1000 words from quality sources)
            if total_content_length >= 1000:
                return False
        
        return True
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        # Use SequenceMatcher for similarity calculation
        similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        return similarity
    
    def _get_domain_keywords(self, domain: str) -> List[str]:
        """Get relevant keywords for a specific domain."""
        domain_keywords = {
            'technology': ['tech', 'software', 'computer', 'digital', 'programming', 'code'],
            'health': ['health', 'medical', 'doctor', 'treatment', 'medicine', 'patient'],
            'finance': ['money', 'financial', 'investment', 'bank', 'economy', 'market'],
            'science': ['research', 'study', 'scientific', 'experiment', 'data', 'analysis'],
            'news': ['news', 'report', 'breaking', 'update', 'current', 'latest'],
        }
        
        return domain_keywords.get(domain, []) if domain else []
    
    def _get_intent_keywords(self, intent) -> List[str]:
        """Get relevant keywords for query intent."""
        intent_keywords = {
            'factual': ['what', 'who', 'when', 'where', 'definition', 'meaning'],
            'research': ['analysis', 'study', 'research', 'investigation', 'detailed'],
            'comparison': ['compare', 'versus', 'difference', 'better', 'best', 'vs'],
            'howto': ['how', 'tutorial', 'guide', 'steps', 'instructions', 'method'],
            'news': ['recent', 'latest', 'breaking', 'update', 'current', 'today'],
        }
        
        return intent_keywords.get(intent.value, [])
    
    def _calculate_keyword_presence(self, text: str, keywords: List[str]) -> float:
        """Calculate the presence score of keywords in text."""
        if not keywords or not text:
            return 0.0
        
        text_lower = text.lower()
        present_keywords = sum(1 for keyword in keywords if keyword in text_lower)
        
        return present_keywords / len(keywords)