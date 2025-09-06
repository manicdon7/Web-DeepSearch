"""
Source ranking functionality for intelligent source prioritization.
"""
import re
from typing import List, Dict, Set
from urllib.parse import urlparse, parse_qs
from app.optimization_models import SourceScore, QueryAnalysis


class SourceRanker:
    """
    Ranks search result sources based on multiple quality and relevance factors.
    """
    
    def __init__(self):
        """Initialize the SourceRanker with domain authority lists and scoring weights."""
        self.high_authority_domains = self._load_high_authority_domains()
        self.scoring_weights = {
            'relevance': 0.4,
            'authority': 0.3,
            'freshness': 0.15,
            'url_quality': 0.15
        }
    
    def _load_high_authority_domains(self) -> Set[str]:
        """Load known high-quality domains for authority scoring."""
        return {
            # News and Media
            'reuters.com', 'bbc.com', 'cnn.com', 'npr.org', 'apnews.com',
            'theguardian.com', 'nytimes.com', 'wsj.com', 'washingtonpost.com',
            
            # Academic and Research
            'ncbi.nlm.nih.gov', 'pubmed.ncbi.nlm.nih.gov', 'scholar.google.com',
            'arxiv.org', 'researchgate.net', 'ieee.org', 'acm.org',
            
            # Government and Official
            'gov.uk', 'cdc.gov', 'nih.gov', 'fda.gov', 'who.int',
            'europa.eu', 'un.org', 'worldbank.org',
            
            # Technology
            'stackoverflow.com', 'github.com', 'mozilla.org', 'w3.org',
            'developer.mozilla.org', 'docs.python.org', 'kubernetes.io',
            
            # Reference and Education
            'wikipedia.org', 'britannica.com', 'merriam-webster.com',
            'dictionary.com', 'investopedia.com', 'khanacademy.org',
            
            # Health and Medical
            'mayoclinic.org', 'webmd.com', 'healthline.com', 'medlineplus.gov',
            'clevelandclinic.org', 'hopkinsmedicine.org'
        }
    
    def rank_sources(self, search_results: List[Dict], query_analysis: QueryAnalysis) -> List[SourceScore]:
        """
        Rank search result sources based on multiple factors.
        
        Args:
            search_results: List of search result dictionaries with 'url', 'title', 'snippet'
            query_analysis: Analysis results from QueryAnalyzer
            
        Returns:
            List of SourceScore objects sorted by final_score (highest first)
        """
        scored_sources = []
        
        for result in search_results:
            url = result.get('url', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Calculate individual scores
            relevance_score = self._calculate_relevance_score(title, snippet, query_analysis)
            authority_score = self._calculate_authority_score(url)
            freshness_score = self._calculate_freshness_score(url, title, snippet, query_analysis)
            url_quality_score = self._calculate_url_quality_score(url)
            
            # Calculate weighted final score
            final_score = (
                relevance_score * self.scoring_weights['relevance'] +
                authority_score * self.scoring_weights['authority'] +
                freshness_score * self.scoring_weights['freshness'] +
                url_quality_score * self.scoring_weights['url_quality']
            )
            
            source_score = SourceScore(
                url=url,
                relevance_score=relevance_score,
                authority_score=authority_score,
                freshness_score=freshness_score,
                final_score=final_score
            )
            
            scored_sources.append(source_score)
        
        # Sort by final score (highest first)
        scored_sources.sort(key=lambda x: x.final_score, reverse=True)
        
        return scored_sources
    
    def _calculate_relevance_score(self, title: str, snippet: str, query_analysis: QueryAnalysis) -> float:
        """
        Calculate relevance score based on title and snippet content matching query.
        
        Args:
            title: Page title
            snippet: Page snippet/description
            query_analysis: Query analysis results
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not title and not snippet:
            return 0.0
        
        # Combine title and snippet for analysis
        content = f"{title} {snippet}".lower()
        
        # Extract keywords from domain and intent
        domain_keywords = self._get_domain_keywords(query_analysis.domain)
        intent_keywords = self._get_intent_keywords(query_analysis.intent)
        
        # Calculate keyword match score
        keyword_matches = 0
        total_keywords = len(domain_keywords) + len(intent_keywords)
        
        if total_keywords > 0:
            for keyword in domain_keywords + intent_keywords:
                if keyword.lower() in content:
                    keyword_matches += 1
            
            keyword_score = keyword_matches / total_keywords
        else:
            keyword_score = 0.5  # Default score when no specific keywords
        
        # Boost score for title matches (titles are more important)
        title_boost = 0.0
        if title:
            title_lower = title.lower()
            for keyword in domain_keywords + intent_keywords:
                if keyword.lower() in title_lower:
                    title_boost += 0.1
        
        # Combine scores with title boost
        relevance_score = min(1.0, keyword_score + title_boost)
        
        return relevance_score
    
    def _calculate_authority_score(self, url: str) -> float:
        """
        Calculate domain authority score based on known high-quality domains.
        
        Args:
            url: Source URL
            
        Returns:
            Authority score between 0.0 and 1.0
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check for exact domain match
            if domain in self.high_authority_domains:
                return 1.0
            
            # Check for subdomain matches (e.g., blog.example.com matches example.com)
            for auth_domain in self.high_authority_domains:
                if domain.endswith('.' + auth_domain):
                    return 0.8
            
            # Check for government domains
            if domain.endswith('.gov') or domain.endswith('.edu'):
                return 0.9
            
            # Check for organization domains
            if domain.endswith('.org'):
                return 0.6
            
            # Default score for unknown domains
            return 0.3
            
        except Exception:
            return 0.1  # Low score for malformed URLs
    
    def _calculate_freshness_score(self, url: str, title: str, snippet: str, query_analysis: QueryAnalysis) -> float:
        """
        Calculate freshness score based on recency indicators and query requirements.
        
        Args:
            url: Source URL
            title: Page title
            snippet: Page snippet
            query_analysis: Query analysis results
            
        Returns:
            Freshness score between 0.0 and 1.0
        """
        # Base freshness score
        freshness_score = 0.5
        
        # Check for date indicators in URL, title, or snippet
        content = f"{url} {title} {snippet}".lower()
        
        # Look for recent year indicators (2023, 2024, etc.)
        current_year = 2024  # This should be dynamic in production
        recent_years = [str(current_year), str(current_year - 1)]
        
        for year in recent_years:
            if year in content:
                freshness_score += 0.2
                break
        
        # Look for recent month indicators
        recent_months = ['january', 'february', 'march', 'april', 'may', 'june',
                        'july', 'august', 'september', 'october', 'november', 'december',
                        'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                        'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        
        for month in recent_months:
            if month in content:
                freshness_score += 0.1
                break
        
        # Look for freshness keywords
        freshness_keywords = ['latest', 'recent', 'new', 'updated', 'current', '2024', '2023']
        for keyword in freshness_keywords:
            if keyword in content:
                freshness_score += 0.1
                break
        
        # Adjust based on query's recency importance
        if query_analysis.recency_importance > 0.7:
            # High recency importance - boost fresh content more
            freshness_score *= (1 + query_analysis.recency_importance * 0.5)
        
        return min(1.0, freshness_score)
    
    def _calculate_url_quality_score(self, url: str) -> float:
        """
        Calculate URL structure quality score.
        
        Args:
            url: Source URL
            
        Returns:
            URL quality score between 0.0 and 1.0
        """
        try:
            parsed_url = urlparse(url)
            
            # Start with base score
            quality_score = 0.5
            
            # Check URL depth (prefer shorter paths)
            path_segments = [seg for seg in parsed_url.path.split('/') if seg]
            if len(path_segments) <= 2:
                quality_score += 0.2
            elif len(path_segments) <= 4:
                quality_score += 0.1
            else:
                quality_score -= 0.1  # Penalize very deep URLs
            
            # Check for clean URL structure (no excessive parameters)
            query_params = parse_qs(parsed_url.query)
            if len(query_params) == 0:
                quality_score += 0.2
            elif len(query_params) <= 2:
                quality_score += 0.1
            else:
                quality_score -= 0.1  # Penalize URLs with many parameters
            
            # Check for readable URL structure
            path = parsed_url.path.lower()
            if any(indicator in path for indicator in ['/article/', '/post/', '/blog/', '/news/']):
                quality_score += 0.1
            
            # Penalize URLs with suspicious patterns
            suspicious_patterns = ['?id=', 'sessionid', 'tracking', 'utm_', 'ref=']
            for pattern in suspicious_patterns:
                if pattern in url.lower():
                    quality_score -= 0.1
                    break
            
            # Ensure score stays within bounds
            return max(0.0, min(1.0, quality_score))
            
        except Exception:
            return 0.1  # Low score for malformed URLs
    
    def _get_domain_keywords(self, domain: str) -> List[str]:
        """
        Get relevant keywords for a specific domain.
        
        Args:
            domain: Domain name (e.g., 'technology', 'health')
            
        Returns:
            List of domain-specific keywords
        """
        domain_keywords_map = {
            'technology': ['tech', 'software', 'programming', 'computer', 'digital', 'AI', 'machine learning'],
            'health': ['health', 'medical', 'medicine', 'doctor', 'treatment', 'disease', 'symptoms'],
            'science': ['research', 'study', 'scientific', 'experiment', 'analysis', 'data'],
            'business': ['business', 'company', 'market', 'finance', 'economy', 'industry'],
            'news': ['news', 'breaking', 'report', 'update', 'latest', 'current'],
            'education': ['education', 'learning', 'course', 'tutorial', 'guide', 'how-to']
        }
        
        return domain_keywords_map.get(domain, []) if domain else []
    
    def _get_intent_keywords(self, intent) -> List[str]:
        """
        Get relevant keywords for a specific query intent.
        
        Args:
            intent: QueryIntent enum value
            
        Returns:
            List of intent-specific keywords
        """
        from app.optimization_models import QueryIntent
        
        intent_keywords_map = {
            QueryIntent.FACTUAL: ['what', 'who', 'when', 'where', 'definition', 'meaning'],
            QueryIntent.RESEARCH: ['analysis', 'study', 'research', 'comprehensive', 'detailed'],
            QueryIntent.COMPARISON: ['vs', 'versus', 'compare', 'comparison', 'difference', 'better'],
            QueryIntent.HOWTO: ['how', 'tutorial', 'guide', 'step', 'instructions', 'method'],
            QueryIntent.NEWS: ['news', 'latest', 'recent', 'breaking', 'update', 'current']
        }
        
        return intent_keywords_map.get(intent, [])