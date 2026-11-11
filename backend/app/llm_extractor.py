import json
import logging
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

class LLMExtractor:
    """
    LLM Extractor for structured text analysis.
    Supports LangChain with OpenAI/DeepInfra/Ollama or fallback heuristic mode for offline execution.
    """

    def __init__(self):
        self.use_chain = False
        self.chain = None
        self._init_langchain()

    def _init_langchain(self):
        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                from langchain_core.prompts import ChatPromptTemplate
                from langchain_core.output_parsers import JsonOutputParser

                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are an AI analyst. Analyze the following text and return JSON with keys: sentiment (Positive/Negative/Neutral), entities (list of strings), category (e.g., Billing, Technical Support, Security, Feedback, General), and summary (1-2 sentences)."),
                    ("user", "{text}")
                ])
                llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name="gpt-4o-mini", temperature=0.0)
                self.chain = prompt | llm | JsonOutputParser()
                self.use_chain = True
                logger.info("Initialized LangChain ChatOpenAI engine.")
            except Exception as e:
                logger.warning(f"Failed to initialize LangChain ChatOpenAI: {e}. Falling back to mock extractor.")
        else:
            logger.info("No LLM API key detected. Operating in resilient heuristic extraction mode.")

    def extract_insights(self, text: str) -> Dict[str, Any]:
        """
        Extract structured insights from unstructured text.
        """
        if self.use_chain and self.chain:
            try:
                result = self.chain.invoke({"text": text})
                if isinstance(result, dict) and "sentiment" in result:
                    return result
            except Exception as e:
                logger.error(f"Error invoking LangChain model: {e}. Falling back to heuristic extraction.")

        return self._heuristic_extraction(text)

    def _heuristic_extraction(self, text: str) -> Dict[str, Any]:
        """
        Fallback heuristic analyzer for offline testing and zero-dependency execution.
        """
        lower_text = text.lower()

        # Sentiment determination
        if any(w in lower_text for w in ["error", "fail", "slow", "broken", "bug", "bad", "terrible", "issue", "crash"]):
            sentiment = "Negative"
        elif any(w in lower_text for w in ["great", "excellent", "fast", "love", "awesome", "good", "happy", "smooth"]):
            sentiment = "Positive"
        else:
            sentiment = "Neutral"

        # Categorization
        if any(w in lower_text for w in ["payment", "invoice", "billing", "charge", "refund", "card", "price"]):
            category = "Billing & Financial"
        elif any(w in lower_text for w in ["server", "api", "latency", "timeout", "bug", "log", "error", "database"]):
            category = "Technical Infrastructure"
        elif any(w in lower_text for w in ["auth", "login", "token", "security", "breach", "password", "unauthorized"]):
            category = "Security & Auth"
        else:
            category = "Customer Feedback"

        # Entity Extraction
        entities = []
        words = text.split()
        for w in words:
            clean_word = w.strip(".,!?:;()[]{}")
            if clean_word and clean_word[0].isupper() and len(clean_word) > 2 and clean_word not in ["The", "And", "This", "That", "With", "For"]:
                if clean_word not in entities:
                    entities.append(clean_word)

        # Summary
        summary = text[:120] + "..." if len(text) > 120 else text

        return {
            "sentiment": sentiment,
            "entities": entities[:5],
            "category": category,
            "summary": summary
        }

extractor = LLMExtractor()
