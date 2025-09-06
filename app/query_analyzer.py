"""
Query Analyzer component for intelligent query analysis and classification.
"""
import re
from typing import Dict, List, Set, Optional
from app.optimization_models import QueryAnalysis, QueryComplexity, QueryIntent, SummaryLength


class QueryAnalyzer:
    """
    Analyzes search queries to determine complexity, domain, intent, and other characteristics
    that inform downstream optimization decisions.
    """
    
    def __init__(self):
        """Initialize the QueryAnalyzer with domain keywords and patterns."""
        self._domain_keywords = self._initialize_domain_keywords()
        self._complexity_patterns = self._initialize_complexity_patterns()
        self._intent_patterns = self._initialize_intent_patterns()
        self._recency_keywords = self._initialize_recency_keywords()
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze a query and return comprehensive analysis results.
        
        Args:
            query: The search query string to analyze
            
        Returns:
            QueryAnalysis object containing all analysis results
        """
        query_lower = query.lower().strip()
        
        complexity = self._detect_complexity(query_lower)
        domain = self._detect_domain(query_lower)
        intent = self._detect_intent(query_lower)
        expected_length = self._determine_expected_length(complexity, intent, query_lower)
        recency_importance = self._calculate_recency_importance(query_lower)
        
        return QueryAnalysis(
            complexity=complexity,
            domain=domain,
            intent=intent,
            expected_length=expected_length,
            recency_importance=recency_importance
        )
    
    def _detect_complexity(self, query: str) -> QueryComplexity:
        """
        Detect query complexity based on length, structure, and patterns.
        
        Args:
            query: Lowercase query string
            
        Returns:
            QueryComplexity enum value
        """
        word_count = len(query.split())
        
        # Check for complex patterns
        complex_indicators = 0
        
        # Multiple questions or clauses
        if len(re.findall(r'[?!.]', query)) > 1:
            complex_indicators += 1
            
        # Comparison words
        comparison_words = ['vs', 'versus', 'compared to', 'difference between', 'better than']
        if any(word in query for word in comparison_words):
            complex_indicators += 1
            
        # Multiple concepts (conjunctions)
        conjunctions = ['and', 'or', 'but', 'however', 'while', 'whereas']
        conjunction_count = sum(1 for conj in conjunctions if conj in query)
        if conjunction_count >= 2:
            complex_indicators += 1
            
        # Technical or academic terms
        if any(pattern.search(query) for pattern in self._complexity_patterns['complex']):
            complex_indicators += 1
            
        # Determine complexity based on word count and indicators
        if word_count <= 3 and complex_indicators == 0:
            return QueryComplexity.SIMPLE
        elif word_count <= 6 and complex_indicators <= 1:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.COMPLEX
    
    def _detect_domain(self, query: str) -> Optional[str]:
        """
        Detect the domain/field of the query using keyword matching.
        
        Args:
            query: Lowercase query string
            
        Returns:
            Domain string if detected, None otherwise
        """
        domain_scores = {}
        
        for domain, keywords in self._domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query)
            if score > 0:
                domain_scores[domain] = score
        
        if not domain_scores:
            return None
            
        # Return domain with highest score
        return max(domain_scores.items(), key=lambda x: x[1])[0]
    
    def _detect_intent(self, query: str) -> QueryIntent:
        """
        Classify the intent behind the query.
        
        Args:
            query: Lowercase query string
            
        Returns:
            QueryIntent enum value
        """
        # Check for factual patterns first (highest priority)
        if any(pattern.search(query) for pattern in self._intent_patterns['factual']):
            return QueryIntent.FACTUAL
        
        # Check for comparison patterns
        if any(pattern.search(query) for pattern in self._intent_patterns['comparison']):
            return QueryIntent.COMPARISON
        
        # Check for how-to patterns
        if any(pattern.search(query) for pattern in self._intent_patterns['howto']):
            return QueryIntent.HOWTO
        
        # Check for news patterns
        if any(pattern.search(query) for pattern in self._intent_patterns['news']):
            return QueryIntent.NEWS
        
        # Check for research patterns
        if any(pattern.search(query) for pattern in self._intent_patterns['research']):
            return QueryIntent.RESEARCH
        
        # Default classification based on structure
        if query.startswith(('what is', 'who is', 'when is', 'where is')):
            return QueryIntent.FACTUAL
        elif 'how to' in query or 'how do' in query:
            return QueryIntent.HOWTO
        elif any(word in query for word in ['news', 'latest', 'recent', 'today']):
            return QueryIntent.NEWS
        else:
            return QueryIntent.RESEARCH
    
    def _determine_expected_length(self, complexity: QueryComplexity, 
                                 intent: QueryIntent, query: str) -> SummaryLength:
        """
        Determine expected summary length based on query characteristics.
        
        Args:
            complexity: Query complexity level
            intent: Query intent
            query: Lowercase query string
            
        Returns:
            SummaryLength enum value
        """
        # Intent-based length preferences
        if intent == QueryIntent.FACTUAL:
            return SummaryLength.SHORT
        elif intent == QueryIntent.COMPARISON:
            return SummaryLength.LONG
        elif intent == QueryIntent.RESEARCH:
            return SummaryLength.MEDIUM if complexity == QueryComplexity.MODERATE else SummaryLength.LONG
        elif intent == QueryIntent.HOWTO:
            return SummaryLength.MEDIUM
        elif intent == QueryIntent.NEWS:
            return SummaryLength.SHORT
        
        # Complexity-based fallback
        if complexity == QueryComplexity.SIMPLE:
            return SummaryLength.SHORT
        elif complexity == QueryComplexity.MODERATE:
            return SummaryLength.MEDIUM
        else:
            return SummaryLength.LONG
    
    def _calculate_recency_importance(self, query: str) -> float:
        """
        Calculate how important recent information is for this query.
        
        Args:
            query: Lowercase query string
            
        Returns:
            Float between 0.0 and 1.0 indicating recency importance
        """
        recency_score = 0.0
        
        # High recency keywords
        high_recency_words = self._recency_keywords['high']
        recency_score += sum(0.3 for word in high_recency_words if word in query)
        
        # Medium recency keywords
        medium_recency_words = self._recency_keywords['medium']
        recency_score += sum(0.2 for word in medium_recency_words if word in query)
        
        # Low recency keywords
        low_recency_words = self._recency_keywords['low']
        recency_score += sum(0.1 for word in low_recency_words if word in query)
        
        # Time-sensitive patterns
        time_patterns = [
            r'\b(today|now|current|latest|recent)\b',
            r'\b(2024|2025)\b',
            r'\b(this (year|month|week))\b'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, query):
                recency_score += 0.25
        
        # Cap at 1.0
        return min(recency_score, 1.0)
    
    def _initialize_domain_keywords(self) -> Dict[str, List[str]]:
        """Initialize domain-specific keyword mappings."""
        return {
            'technology': [
                'software', 'programming', 'code', 'algorithm', 'api', 'database',
                'python', 'javascript', 'react', 'node', 'docker', 'kubernetes',
                'machine learning', 'ai', 'artificial intelligence', 'blockchain',
                'cybersecurity', 'cloud', 'aws', 'azure', 'devops'
            ],
            'health': [
                'medicine', 'medical', 'health', 'disease', 'treatment', 'symptoms',
                'doctor', 'hospital', 'therapy', 'medication', 'diagnosis',
                'nutrition', 'fitness', 'wellness', 'mental health'
            ],
            'science': [
                'research', 'study', 'experiment', 'theory', 'physics', 'chemistry',
                'biology', 'mathematics', 'statistics', 'data', 'analysis',
                'scientific', 'laboratory', 'hypothesis'
            ],
            'business': [
                'company', 'business', 'market', 'finance', 'investment', 'stock',
                'economy', 'revenue', 'profit', 'startup', 'entrepreneur',
                'management', 'strategy', 'marketing', 'sales'
            ],
            'education': [
                'school', 'university', 'college', 'course', 'learning', 'student',
                'teacher', 'education', 'academic', 'degree', 'curriculum',
                'training', 'certification'
            ]
        }
    
    def _initialize_complexity_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Initialize regex patterns for complexity detection."""
        return {
            'complex': [
                re.compile(r'\b(methodology|implementation|architecture|framework)\b'),
                re.compile(r'\b(comprehensive|detailed|thorough|extensive)\b'),
                re.compile(r'\b(analysis|evaluation|assessment|comparison)\b'),
                re.compile(r'\b(advantages and disadvantages|pros and cons)\b')
            ]
        }
    
    def _initialize_intent_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Initialize regex patterns for intent classification."""
        return {
            'factual': [
                re.compile(r'^(what is|who is|when (is|was|were)|where is|which is|what are|who are)'),
                re.compile(r'\b(definition of|meaning of|explain what)\b'),
                re.compile(r'^define\b')
            ],
            'comparison': [
                re.compile(r'\b(vs|versus|compared? to|difference between)\b'),
                re.compile(r'\b(better than|worse than|advantages|disadvantages)\b'),
                re.compile(r'\b(pros and cons|benefits and drawbacks)\b')
            ],
            'research': [
                re.compile(r'\bresearch (on|about|into)\b'),
                re.compile(r'\b(study of|analysis of|investigation into)\b'),
                re.compile(r'\b(why does|how does|what causes|what leads to)\b'),
                re.compile(r'\b(impact of|effect of|influence of|relationship between)\b')
            ],
            'howto': [
                re.compile(r'^how to'),
                re.compile(r'\b(tutorial for|guide to|instructions for|steps to)\b'),
                re.compile(r'\b(learn how to|create a|build a|make a|setup)\b'),
                re.compile(r'^learn\b')
            ],
            'news': [
                re.compile(r'\b(breaking news|latest news|news about|news update)\b'),
                re.compile(r'\b(what happened|what occurred|recent event|recent incident)\b')
            ]
        }
    
    def _initialize_recency_keywords(self) -> Dict[str, List[str]]:
        """Initialize keywords that indicate recency importance."""
        return {
            'high': [
                'today', 'now', 'current', 'latest', 'recent', 'breaking',
                'live', 'real-time', 'update', 'new'
            ],
            'medium': [
                'this week', 'this month', 'this year', '2024', '2025',
                'modern', 'contemporary', 'trending'
            ],
            'low': [
                'news', 'development', 'change', 'evolution', 'progress'
            ]
        }