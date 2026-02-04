import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

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
                    "content": "Você é um editor de vídeos viral. Receba uma transcrição e retorne APENAS um JSON com os 2 melhores momentos: [{'start': seg, 'end': seg, 'label': 'motivo'}]."
                },
                {"role": "user", "content": f"Transcrição: {transcription}"}
            ],
            "response_format": { "type": "json_object" } # Recurso suportado por modelos compatíveis
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}", # Autenticação via Bearer token
            "Content-Type": "application/json"
        }

        response = requests.post(self.base_url, headers=headers, json=payload)
        return response.json()['choices'][0]['message']['content']
