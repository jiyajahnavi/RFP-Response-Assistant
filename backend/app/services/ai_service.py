import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.models.entities import ResponseLibrary
from app.services.gemini_service import client

logger = logging.getLogger("rfp_assistant.services.ai")


class AIService:
    """
    AI Generation & Semantic RAG Search Service.
    Integrates Gemini / LLM models and semantic embedding retrieval.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate semantic text embeddings using Gemini embedding model.
        Returns float vector or None on failure.
        """
        if not text or not text.strip():
            return None
        try:
            response = client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text.strip(),
            )
            if hasattr(response, "embeddings") and response.embeddings:
                return response.embeddings[0].values
            elif hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                return response.embedding.values
            return None
        except Exception as e:
            logger.warning("Failed to generate embedding via Gemini API: %s", e)
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two numerical vectors."""
        a = np.array(vec1, dtype=np.float32)
        b = np.array(vec2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _lexical_similarity(self, text1: str, text2: str) -> float:
        """Fallback word-overlap Jaccard similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return float(len(intersection) / len(union))

    def search_response_library(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 3,
        min_threshold: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """
        Search historical ResponseLibrary using semantic similarity + category weighting.
        """
        stmt = select(ResponseLibrary)
        if category:
            stmt = stmt.where(ResponseLibrary.Category == category)
        entries = list(self.db.scalars(stmt).all())

        if not entries:
            # If nothing found with exact category, search all
            entries = list(self.db.scalars(select(ResponseLibrary)).all())

        if not entries:
            return []

        query_emb = self.get_embedding(query)
        results: List[Tuple[float, ResponseLibrary]] = []

        for entry in entries:
            sim_score = 0.0
            if query_emb is not None:
                entry_emb = self.get_embedding(f"{entry.Question} {entry.Answer}")
                if entry_emb is not None:
                    sim_score = self._cosine_similarity(query_emb, entry_emb)
            
            # If embedding failed or score is 0, compute lexical fallback
            if sim_score <= 0.01:
                lexical_score = self._lexical_similarity(query, f"{entry.Question} {entry.Answer}")
                sim_score = lexical_score

            # Category boost if match
            if category and entry.Category and category.lower() == entry.Category.lower():
                sim_score = min(1.0, sim_score + 0.1)

            results.append((sim_score, entry))

        # Sort descending by similarity score
        results.sort(key=lambda x: x[0], reverse=True)

        matched = []
        for score, entry in results[:top_k]:
            matched.append({
                "library_id": entry.LibraryId,
                "question": entry.Question,
                "answer": entry.Answer,
                "category": entry.Category,
                "technology": entry.Technology,
                "confidence_score": round(score, 3),
            })

        return matched

    def generate_draft_response(
        self,
        question_text: str,
        category: Optional[str] = None,
        context_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate contextual RFP draft response via RAG + Gemini 2.5 Flash.
        Enforces Business Rule: Always initiates in 'Draft' status with IsAIGenerated=True.
        """
        # 1. Retrieve most relevant context from ResponseLibrary
        rag_matches = self.search_response_library(question_text, category=category, top_k=3)
        
        context_blocks = []
        citations = []
        top_confidence = 0.0

        for match in rag_matches:
            if match["confidence_score"] > top_confidence:
                top_confidence = match["confidence_score"]
            context_blocks.append(
                f"[Source #{match['library_id']} - Category: {match.get('category')} | Match: {int(match['confidence_score']*100)}%]\n"
                f"Question: {match['question']}\nApproved Response: {match['answer']}"
            )
            citations.append({
                "library_id": match["library_id"],
                "category": match["category"],
                "confidence_score": match["confidence_score"],
            })

        context_str = "\n\n".join(context_blocks) if context_blocks else "No prior verified historical responses found."

        system_instruction = (
            "You are an expert RFP (Request for Proposal) proposal architect. "
            "Your task is to draft a clear, persuasive, compliant, and professional enterprise response to the customer's RFP question. "
            "Use the provided verified historical responses as foundational context and tone. "
            "Ensure the response directly answers what the customer is asking without generic fluff. "
            "If exact details are missing, provide a robust enterprise standard answer while clearly phrasing it for human review."
        )

        user_prompt = (
            f"RFP Question: {question_text}\n"
            f"Category: {category or 'General'}\n"
            f"Additional Project Notes: {context_notes or 'None'}\n\n"
            f"=== Verified Historical Knowledge Base Context ===\n"
            f"{context_str}\n\n"
            "Please generate the complete, authoritative proposal response text:"
        )

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[user_prompt],
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.2,
                }
            )
            draft_text = response.text.strip()
            # If RAG found strong evidence, confidence is high, else default baseline AI confidence
            calculated_confidence = max(0.85, top_confidence) if top_confidence >= 0.5 else 0.78
        except Exception as e:
            logger.error("Error generating response with Gemini: %s", e)
            # Graceful rule-compliant fallback
            if rag_matches:
                draft_text = f"Based on verified company standard:\n\n{rag_matches[0]['answer']}"
                calculated_confidence = max(0.65, rag_matches[0]["confidence_score"])
            else:
                draft_text = f"Draft proposal response addressing: {question_text}. (AI service currently formulating response)"
                calculated_confidence = 0.60

        return {
            "draft_text": draft_text,
            "confidence_score": round(calculated_confidence, 2),
            "citations": citations,
            "status": "Draft",  # Invariant
            "is_ai_generated": True,  # Invariant
        }
