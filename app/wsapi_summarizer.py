import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from string import punctuation
from collections import Counter
from heapq import nlargest
from typing import Dict, Any
from scraper import scrape_url


class TextSummarizer:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.stopwords = set(STOP_WORDS)
    
    def _calculate_word_frequencies(self, doc) -> dict:
        words = [
            token.text.lower() 
            for token in doc 
            if (token.text.lower() not in self.stopwords and 
                token.text.lower() not in punctuation and 
                token.is_alpha)
        ]
        
        word_freq = Counter(words)
        if not word_freq:
            return {}
            
        max_freq = max(word_freq.values())
        return {word: freq / max_freq for word, freq in word_freq.items()}
    
    def _score_sentences(self, doc, word_freq: dict) -> dict:
        sentence_scores = {}
        
        for sent in doc.sents:
            for word in sent:
                word_lower = word.text.lower()
                if word_lower in word_freq:
                    if sent in sentence_scores:
                        sentence_scores[sent] += word_freq[word_lower]
                    else:
                        sentence_scores[sent] = word_freq[word_lower]
        
        return sentence_scores
    
    def summarize(self, text: str, num_sentences: int = 3) -> str:
        if not text.strip():
            return "No content to summarize."
            
        doc = self.nlp(text)
        word_freq = self._calculate_word_frequencies(doc)
        if not word_freq:
            return "Not enough meaningful content to generate a summary."
        
        sentence_scores = self._score_sentences(doc, word_freq)
        num_sentences = min(num_sentences, len(sentence_scores))
        if num_sentences <= 0:
            return "Could not generate a summary from the provided text."
        
        top_sentences = nlargest(num_sentences, sentence_scores, key=sentence_scores.get)
        return ' '.join(sent.text for sent in top_sentences)


def main():
    example_url = "https://en.wikipedia.org/wiki/Large_language_model"
    
    print(f"Scraping content from: {example_url}")
    scraped_data = scrape_url(example_url)
    
    if not scraped_data or 'main_content' not in scraped_data:
        print("Failed to retrieve content from the URL.")
        return
    
    summarizer = TextSummarizer()
    
    print("\nGenerating summary...\n")
    summary = summarizer.summarize(scraped_data["main_content"])
    
    print("=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(summary)
    print("=" * 80)


if __name__ == "__main__":
    import time
    start_time = time.time()
    main()
    print(f"\nTime taken: {time.time() - start_time:.2f} seconds")