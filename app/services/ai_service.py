import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

prompt = (
    "Aja como um editor de clips virais. Com base na transcrição abaixo, "
    "retorne EXATAMENTE um objeto JSON com uma chave 'moments' contendo uma lista COM DOIS MOMENTOS. "
    "Exemplo de formato: {\"moments\": [{\"start\": 10, \"end\": 30, \"label\": \"Título\"}]} "
)

class AIService:
    def __init__(self):
        # Base URL definida na documentação da API
        self.base_url = "https://gen.pollinations.ai/v1/chat/completions"
        self.api_key = os.getenv("POLLINATIONS_API_KEY")

    def identify_best_moments(self, transcription):
        """
        Envia a transcrição para a IA e pede os timestamps.
        """
        # Exemplo de uso do modelo 'openai' conforme a documentação
        payload = {
            "model": "nova-fast", 
            "messages": [
                {
                    "role": "system", 
                    "content": prompt
                },
                {"role": "user", "content": transcription}
            ],
            "response_format": { "type": "json_object" } # Recurso suportado por modelos compatíveis
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}", # Autenticação via Bearer token
            "Content-Type": "application/json"
        }

        response = requests.post(self.base_url, headers=headers, json=payload)
        content = response.json()['choices'][0]['message']['content']
        return self._clean_json_response(content)

    def _clean_json_response(self, text):
        """
        Limpa blocos de código markdown se houver.
        """
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
            
        return text.strip()
