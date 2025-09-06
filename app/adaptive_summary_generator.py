"""
Adaptive Summary Generator for creating length-aware summaries based on query analysis.
"""
from typing import List, Dict, Optional
import re
from app.optimization_models import (
    QueryAnalysis, SummaryConfig, DetailLevel, SummaryLength, 
    QueryComplexity, QueryIntent, EnhancedSource
)


class AdaptiveSummaryGenerator:
    """
    Generates summaries with appropriate length and detail based on query characteristics.
    """
    
    def __init__(self):
        """Initialize the adaptive summary generator."""
        self.length_mappings = {
            SummaryLength.SHORT: (100, 200),
            SummaryLength.MEDIUM: (300, 600),
            SummaryLength.LONG: (400, 800)
        }
        
        self.detail_level_mappings = {
            QueryComplexity.SIMPLE: DetailLevel.CONCISE,
            QueryComplexity.MODERATE: DetailLevel.BALANCED,
            QueryComplexity.COMPLEX: DetailLevel.COMPREHENSIVE
        }
    
    def generate_summary_config(self, query_analysis: QueryAnalysis) -> SummaryConfig:
        """
        Generate summary configuration based on query analysis results.
        
        Args:
            query_analysis: Analysis results from QueryAnalyzer
            
        Returns:
            SummaryConfig: Configuration for summary generation
        """
        # Determine target length based on expected length
        min_length, max_length = self.length_mappings[query_analysis.expected_length]
        target_length = (min_length + max_length) // 2
        
        # Determine detail level based on complexity
        detail_level = self.detail_level_mappings[query_analysis.complexity]
        
        # Extract focus areas from domain and intent
        focus_areas = []
        if query_analysis.domain:
            focus_areas.append(query_analysis.domain)
        
        # Add intent-specific focus areas
        if query_analysis.intent == QueryIntent.COMPARISON:
            focus_areas.extend(["comparison", "differences", "similarities"])
        elif query_analysis.intent == QueryIntent.HOWTO:
            focus_areas.extend(["steps", "process", "instructions"])
        elif query_analysis.intent == QueryIntent.NEWS:
            focus_areas.extend(["recent", "updates", "developments"])
        elif query_analysis.intent == QueryIntent.RESEARCH:
            focus_areas.extend(["analysis", "findings", "evidence"])
        
        # Include examples for complex queries or how-to queries
        include_examples = (
            query_analysis.complexity == QueryComplexity.COMPLEX or
            query_analysis.intent == QueryIntent.HOWTO
        )
        
        return SummaryConfig(
            target_length=target_length,
            detail_level=detail_level,
            focus_areas=focus_areas,
            include_examples=include_examples
        )
    
    def adjust_length_for_content_quality(
        self, 
        base_config: SummaryConfig, 
        sources: List[EnhancedSource]
    ) -> SummaryConfig:
        """
        Dynamically adjust summary length based on available content quality.
        
        Args:
            base_config: Base summary configuration
            sources: List of enhanced sources with quality metrics
            
        Returns:
            SummaryConfig: Adjusted configuration
        """
        if not sources:
            # Reduce length if no sources available
            adjusted_config = SummaryConfig(
                target_length=max(50, base_config.target_length // 2),
                detail_level=DetailLevel.CONCISE,
                focus_areas=base_config.focus_areas,
                include_examples=False
            )
            return adjusted_config
        
        # Calculate average content quality
        quality_scores = []
        total_content_length = 0
        
        for source in sources:
            if source.content_quality:
                quality_scores.append(source.content_quality.relevance_score)
            if source.word_count:
                total_content_length += source.word_count
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.5
        
        # Adjust length based on quality and available content
        length_multiplier = 1.0
        
        # High quality content allows for longer summaries
        if avg_quality > 0.8:
            length_multiplier = 1.2
        elif avg_quality < 0.4:
            length_multiplier = 0.7
        
        # Insufficient content requires shorter summaries
        if total_content_length < base_config.target_length * 2:
            length_multiplier *= 0.8
        
        adjusted_length = int(base_config.target_length * length_multiplier)
        
        # Adjust detail level based on quality
        adjusted_detail_level = base_config.detail_level
        if avg_quality < 0.4:
            adjusted_detail_level = DetailLevel.CONCISE
        elif avg_quality > 0.8 and base_config.detail_level == DetailLevel.BALANCED:
            adjusted_detail_level = DetailLevel.COMPREHENSIVE
        
        return SummaryConfig(
            target_length=adjusted_length,
            detail_level=adjusted_detail_level,
            focus_areas=base_config.focus_areas,
            include_examples=base_config.include_examples and avg_quality > 0.6
        )
    
    def create_summary_prompt(
        self, 
        query: str, 
        sources: List[EnhancedSource], 
        config: SummaryConfig
    ) -> str:
        """
        Create a tailored prompt for summary generation based on configuration.
        
        Args:
            query: Original search query
            sources: List of enhanced sources
            config: Summary configuration
            
        Returns:
            str: Engineered prompt for AI summary generation
        """
        # Base prompt structure
        prompt_parts = []
        
        # Create human-like, casual prompt for better AI synthesis
        prompt_parts.append("You are a helpful assistant who explains things in a casual, conversational way.")
        prompt_parts.append("Always respond in English, using a friendly and natural tone like you're talking to a friend.")
        
        if config.target_length <= 200:
            # Short, casual prompt
            prompt_parts.append(f"Hey, can you give me a quick summary about '{query}'? Keep it around {config.target_length} words and make it easy to understand.")
            if config.focus_areas:
                focus_text = ", ".join(config.focus_areas)
                prompt_parts.append(f"I'm especially interested in: {focus_text}.")
        else:
            # Longer, conversational prompt
            prompt_parts.append(f"I'm curious about '{query}'. Can you explain what's going on with this topic?")
            prompt_parts.append(f"Give me a good overview - around {config.target_length} words would be perfect.")
            
            # Add casual style instructions
            if config.detail_level == DetailLevel.CONCISE:
                prompt_parts.append("Keep it simple and to the point - just the key stuff I should know.")
            elif config.detail_level == DetailLevel.BALANCED:
                prompt_parts.append("Give me a nice balance of details - not too technical, but informative.")
            else:  # COMPREHENSIVE
                prompt_parts.append("I want the full picture - give me all the important details and context.")
            
            # Add focus areas in casual tone
            if config.focus_areas:
                focus_text = ", ".join(config.focus_areas)
                prompt_parts.append(f"I'm particularly interested in: {focus_text}.")
        
        prompt_parts.append("Use the information from these sources to give me a helpful explanation:")
        prompt_parts.append("Remember: Write like you're having a conversation - be natural, friendly, and always in English!")
        
        # Add source content (optimized for better AI processing)
        prompt_parts.append("\nSources:")
        
        # Limit to top 10 most relevant sources and shorter content
        limited_sources = sources[:10]  # Limit sources for better processing
        
        for i, source in enumerate(limited_sources, 1):
            # Use shorter content preview for better AI processing
            content_preview = source.main_content[:300] + "..." if len(source.main_content) > 300 else source.main_content
            prompt_parts.append(f"\nSource {i} ({source.url}):\n{content_preview}")
        
        return "\n".join(prompt_parts)
    
    def generate_summary(
        self, 
        query: str, 
        sources: List[EnhancedSource], 
        query_analysis: QueryAnalysis
    ) -> str:
        """
        Generate an adaptive summary based on query analysis and source content.
        
        Args:
            query: Original search query
            sources: List of enhanced sources with content
            query_analysis: Analysis results from QueryAnalyzer
            
        Returns:
            str: Generated summary tailored to query characteristics
        """
        # Generate base configuration
        base_config = self.generate_summary_config(query_analysis)
        
        # Adjust configuration based on content quality
        final_config = self.adjust_length_for_content_quality(base_config, sources)
        
        # Create tailored prompt
        prompt = self.create_summary_prompt(query, sources, final_config)
        
        # For now, return the prompt as a placeholder
        # In a real implementation, this would be sent to an AI service
        return self._generate_fallback_summary(query, sources, final_config)
    
    def _generate_fallback_summary(
        self, 
        query: str, 
        sources: List[EnhancedSource], 
        config: SummaryConfig
    ) -> str:
        """
        Generate a basic fallback summary when AI services are unavailable.
        
        Args:
            query: Original search query
            sources: List of enhanced sources
            config: Summary configuration
            
        Returns:
            str: Basic summary extracted from sources
        """
        if not sources:
            return f"No relevant sources found for query: '{query}'"
        
        # Extract key sentences from sources
        all_sentences = []
        for source in sources:
            sentences = self._extract_sentences(source.main_content)
            # Score sentences based on query relevance
            scored_sentences = self._score_sentences(sentences, query)
            all_sentences.extend(scored_sentences)
        
        # Sort by relevance score and select top sentences
        all_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Select sentences to meet target length
        selected_sentences = []
        current_length = 0
        target_words = config.target_length
        
        for sentence, score in all_sentences:
            sentence_length = len(sentence.split())
            if current_length + sentence_length <= target_words * 1.2:  # Allow 20% overage
                selected_sentences.append(sentence)
                current_length += sentence_length
            if current_length >= target_words * 0.8:  # Stop at 80% of target
                break
        
        # Join sentences into coherent summary
        summary = " ".join(selected_sentences)
        
        # Add query context if very short
        if len(summary.split()) < 50:
            summary = f"Based on available sources regarding '{query}': {summary}"
        
        return summary
    
    def _extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text content."""
        # Simple sentence splitting on periods, exclamation marks, and question marks
        sentences = re.split(r'[.!?]+', text)
        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and len(sentence.split()) > 3:  # Filter very short sentences
                cleaned_sentences.append(sentence)
        return cleaned_sentences
    
    def _score_sentences(self, sentences: List[str], query: str) -> List[tuple]:
        """Score sentences based on relevance to query."""
        query_words = set(query.lower().split())
        scored_sentences = []
        
        for sentence in sentences:
            sentence_words = set(sentence.lower().split())
            # Simple relevance scoring based on word overlap
            overlap = len(query_words.intersection(sentence_words))
            score = overlap / len(query_words) if query_words else 0
            scored_sentences.append((sentence, score))
        
        return scored_sentences