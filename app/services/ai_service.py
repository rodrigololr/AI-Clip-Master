import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

from app.config import N_CLIPS

PROMPT = (
    "Aja como um editor de clips virais. Com base na transcricao abaixo, "
    "retorne EXATAMENTE um objeto JSON com a chave 'moments' contendo uma lista com "
    f"{N_CLIPS} momentos. "
    "Cada momento deve conter: start (segundos), end (segundos) e label (titulo curto). "
    "Nao inclua markdown nem texto extra."
)


class AIServiceError(RuntimeError):
    pass


class AIService:
    def __init__(self):
        self.base_url = "https://gen.pollinations.ai/v1/chat/completions"
        self.api_key = os.getenv("POLLINATIONS_API_KEY")

    def identify_best_moments(self, transcription):
        if not self.api_key:
            raise AIServiceError("Defina POLLINATIONS_API_KEY antes de gerar clips.")

        if not transcription or not transcription.strip():
            raise AIServiceError(
                "A transcricao veio vazia. Nao foi possivel analisar o video."
            )

        payload = {
            "model": "nova-fast",
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": transcription},
            ],
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.base_url, headers=headers, json=payload, timeout=60
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise AIServiceError(
                "A IA demorou demais para responder. Tente novamente."
            ) from exc
        except requests.RequestException as exc:
            raise AIServiceError("Falha ao consultar a Pollinations AI.") from exc

        try:
            response_json = response.json()
        except ValueError as exc:
            raise AIServiceError("A API retornou uma resposta invalida.") from exc

        content = self._extract_message_content(response_json)
        cleaned_content = self._clean_json_response(content)

        try:
            parsed_content = json.loads(cleaned_content)
        except json.JSONDecodeError as exc:
            raise AIServiceError(
                "A IA retornou JSON invalido para os momentos do video."
            ) from exc

        return self._validate_moments(parsed_content)

    def _extract_message_content(self, response_json):
        choices = response_json.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AIServiceError("A API nao retornou sugestoes de momentos.")

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise AIServiceError("A API nao retornou conteudo util para gerar clips.")

        return content

    def _extract_first_json_object(self, text):
        """
        Tenta extrair o primeiro objeto JSON bem formado do texto devolvido pela API.
        Se nao encontrar um objeto JSON, retorna None.
        """
        text = text or ""
        # procura pelo primeiro '{' e tenta balancear chaves até achar um JSON valido
        start_idx = text.find("{")
        if start_idx == -1:
            return None

        depth = 0
        for i in range(start_idx, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start_idx : i + 1]

        return None

    def _validate_moments(self, parsed_content):
        moments = parsed_content.get("moments")
        if not isinstance(moments, list) or len(moments) < 2:
            raise AIServiceError("A IA nao retornou os 2 momentos esperados.")

        validated_moments = []
        for item in moments[:2]:
            if not isinstance(item, dict):
                raise AIServiceError("Formato de momento invalido retornado pela IA.")

            try:
                start = float(item["start"])
                end = float(item["end"])
            except (KeyError, TypeError, ValueError) as exc:
                raise AIServiceError(
                    "Os timestamps retornados pela IA estao invalidos."
                ) from exc

            label = str(item.get("label", "")).strip()
            if not label:
                raise AIServiceError("Um dos momentos retornou sem titulo.")

            if end <= start:
                raise AIServiceError("Um dos momentos retornou com intervalo invalido.")

            validated_moments.append(
                {
                    "start": start,
                    "end": end,
                    "label": label,
                }
            )

        if len(validated_moments) != 2:
            raise AIServiceError("Nao foi possivel validar os 2 momentos fixos.")

        return validated_moments

    def _clean_json_response(self, text):
        text = text or ""
        text = text.strip()

        # remove fences de code block simples
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # tentar extrair o primeiro objeto JSON completo caso haja texto adicional
        candidate = self._extract_first_json_object(text)
        if candidate:
            return candidate.strip()

        # fallback: retorna o texto limpo para tentar json.loads e gerar o erro padrao a montante
        return text
