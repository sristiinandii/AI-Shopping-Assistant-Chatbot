import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
import numpy as np

class DeepLearningEngine:
    def __init__(self):
        # Load pre-trained models
        self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        self.model = AutoModelForSequenceClassification.from_pretrained('bert-base-uncased')
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Store embeddings for semantic search
        self.conversation_embeddings = {}
        self.product_embeddings = {}
        
    def get_semantic_embedding(self, text):
        return self.sentence_model.encode(text)
        
    def find_similar_conversations(self, text, threshold=0.7):
        text_embedding = self.get_semantic_embedding(text)
        similar_conversations = []
        
        for conv_id, embedding in self.conversation_embeddings.items():
            similarity = np.dot(text_embedding, embedding) / (np.linalg.norm(text_embedding) * np.linalg.norm(embedding))
            if similarity > threshold:
                similar_conversations.append((conv_id, similarity))
                
        return sorted(similar_conversations, key=lambda x: x[1], reverse=True) 