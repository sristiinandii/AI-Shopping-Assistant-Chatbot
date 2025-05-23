from transformers import AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import random
from datetime import datetime
from products import PRODUCTS, add_to_cart  # Ensure products.py exists with proper data


class AIEngine:
    def __init__(self):
        """Initialize models and load data."""
        try:
            # Use Auto classes with a lightweight GPT-2 variant
            self.gpt_tokenizer = AutoTokenizer.from_pretrained('distilgpt2')
            self.gpt_model = AutoModelForCausalLM.from_pretrained('distilgpt2')

            self.gpt_tokenizer.add_special_tokens({'pad_token': '[PAD]'})
            self.gpt_model.resize_token_embeddings(len(self.gpt_tokenizer))

            # SentenceTransformer for semantic similarity
            self.sentence_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

            # Load training data
            with open('training_data.json', 'r') as f:
                self.training_data = json.load(f)

            # Initialize product embeddings
            self.product_embeddings = self._initialize_product_embeddings()

            self.conversation_history = {}
            self.user_preferences = {}

        except Exception as e:
            raise RuntimeError(f"Error initializing AI Engine: {e}")

    def generate_response(self, text, user_id):
        """Generate response based on user input."""
        try:
            intent, entities = self._analyze_input(text)

            if intent == 'greeting':
                return random.choice(self.training_data['intents']['greeting']['responses'])

            if intent in ['show_products', 'ask_products']:
                return self._handle_product_query(text, entities)

            if intent == 'add_to_cart':
                product_id = entities.get('product_id')
                if product_id:
                    return add_to_cart(product_id)

            prompt = self._create_prompt(text, self.conversation_history.get(user_id, []))
            response = self._generate_gpt_response(prompt)

            self._update_history(user_id, text, response)

            return response

        except Exception as e:
            return f"Sorry, I encountered an error: {e}"

    def _analyze_input(self, text):
        """Analyze user input and extract intent and entities."""
        text = text.lower()

        entities = {'gender': None, 'category': None, 'product_id': None}
        if 'men' in text:
            entities['gender'] = 'men'
        elif 'women' in text:
            entities['gender'] = 'women'

        if 'top' in text:
            entities['category'] = 'tops'

        if 'add to cart' in text:
            entities['product_id'] = self._extract_product_id(text)

        intent = 'general'
        for intent_name, data in self.training_data['intents'].items():
            if any(pattern.lower() in text for pattern in data['patterns']):
                intent = intent_name
                break

        return intent, entities

    def _extract_product_id(self, text):
        """Extract product ID from the user input."""
        for product in PRODUCTS['men']['tops'] + PRODUCTS['women']['tops']:
            if product['name'].lower() in text:
                return product['id']
        return None

    def _handle_product_query(self, text, entities):
        """Handle product-related queries."""
        relevant_products = self._find_relevant_products(text, entities)
        if relevant_products:
            product_list = "".join([f"<a href='{product['image']}' target='_blank'>"
                                    f"<img src='{product['image']}' alt='{product['name']}' style='width:100px;height:auto;'>"
                                    f"{product['name']}</a> ₹{product['price']}<br>"
                                    for product in relevant_products])
            return f"Here are some products:<br>{product_list}"
        return "Sorry, no products match your query."

    def _generate_gpt_response(self, prompt):
        """Generate GPT-2 response."""
        inputs = self.gpt_tokenizer(prompt, return_tensors='pt', padding=True, truncation=True, max_length=512)
        outputs = self.gpt_model.generate(
            inputs['input_ids'],
            attention_mask=inputs['attention_mask'],
            max_length=150,
            temperature=0.7,
            pad_token_id=self.gpt_tokenizer.pad_token_id,
            do_sample=True
        )
        return self.gpt_tokenizer.decode(outputs[0], skip_special_tokens=True)

    def _update_history(self, user_id, text, response):
        """Update user conversation history."""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append({'text': text, 'response': response, 'timestamp': datetime.now()})

    def _create_prompt(self, text, history):
        """Create a conversation prompt for GPT-2."""
        prompt = "Conversation:\n"
        for msg in history:
            prompt += f"User: {msg['text']}\nAssistant: {msg['response']}\n"
        prompt += f"User: {text}\nAssistant:"
        return prompt

    def _find_relevant_products(self, text, entities):
        """Find products based on semantic similarity."""
        text_embedding = self.sentence_model.encode(text)
        relevant_products = []
        for product_id, embedding in self.product_embeddings.items():
            similarity = np.dot(text_embedding, embedding) / (
                np.linalg.norm(text_embedding) * np.linalg.norm(embedding)
            )
            if similarity > 0.3:
                for gender in PRODUCTS:
                    for category in PRODUCTS[gender]:
                        for product in PRODUCTS[gender][category]:
                            if product['id'] == product_id:
                                relevant_products.append(product)
        return relevant_products

    def _initialize_product_embeddings(self):
        """Initialize product embeddings."""
        embeddings = {}
        for gender in PRODUCTS:
            for category in PRODUCTS[gender]:
                for product in PRODUCTS[gender][category]:
                    text = f"{product['name']} {product['description']}"
                    embeddings[product['id']] = self.sentence_model.encode(text)
        return embeddings


# Example interaction
if __name__ == "__main__":
    engine = AIEngine()
    print("Chatbot is running. Type 'exit' to quit.")
    user_id = "test_user"
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        response = engine.generate_response(user_input, user_id)
        print("Bot:", response)
