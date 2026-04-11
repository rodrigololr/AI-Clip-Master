import requests
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

from app.config import N_CLIPS, POLLINATIONS_MODEL

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
        # number of retries for transient network errors
        try:
            self.max_retries = int(os.getenv("POLLINATIONS_MAX_RETRIES", "2"))
        except Exception:
            self.max_retries = 2
        # injection point for sleep (helps tests avoid real sleeps)
        self._sleep = time.sleep

    def identify_best_moments(self, transcription):
        if not self.api_key:
            raise AIServiceError("Defina POLLINATIONS_API_KEY antes de gerar clips.")

        if not transcription or not transcription.strip():
            raise AIServiceError(
                "A transcricao veio vazia. Nao foi possivel analisar o video."
            )

        payload = {
            "model": POLLINATIONS_MODEL,
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

        # Attempt the request with retries for transient failures
        last_exc = None
        for attempt in range(0, self.max_retries + 1):
            try:
                response = requests.post(
                    self.base_url, headers=headers, json=payload, timeout=60
                )
                response.raise_for_status()
                break
            except requests.Timeout as exc:
                last_exc = exc
                # timeouts are transient; retry if attempts remain
                if attempt < self.max_retries:
                    self._sleep(1 * (2**attempt))
                    continue
                raise AIServiceError(
                    "A IA demorou demais para responder. Tente novamente."
                ) from exc
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    # exponential backoff before retry
                    self._sleep(0.5 * (2**attempt))
                    continue
                # last attempt failed — provide richer diagnostics
                msg = "Falha ao consultar a Pollinations AI."
                try:
                    if hasattr(exc, "response") and exc.response is not None:
                        msg += f" Status={exc.response.status_code}"
                        # attempt to include response text safely
                        txt = (
                            exc.response.text if hasattr(exc.response, "text") else None
                        )
                        if txt:
                            msg += f" Response={txt[:200]}"
                except Exception:
                    pass
                raise AIServiceError(msg) from exc

        try:
            response_json = response.json()
        except ValueError as exc:
            raise AIServiceError("A API retornou uma resposta invalida.") from exc

        content = self._extract_message_content(response_json)
        cleaned_content = self._clean_json_response(content)

        try:
            parsed_content = json.loads(cleaned_content)
        except json.JSONDecodeError as exc:
            # As a last resort, attempt a local fallback if configured
            if os.getenv("POLLINATIONS_OFFLINE_FALLBACK", "0") == "1":
                fallback = self._fallback_moments(transcription)
                if fallback:
                    return fallback
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

    def _fallback_moments(self, transcription):
        """Very small heuristic to return two candidate moments from the transcription.

        This is used when the external AI fails and POLLINATIONS_OFFLINE_FALLBACK=1 is set.
        It parses lines like '[0.00s - 3.00s] text' produced by the local transcriber
        and selects the two longest text segments as candidate moments.
        """
        lines = (transcription or "").splitlines()
        candidates = []
        for ln in lines:
            try:
                if ln.startswith("[") and "]" in ln:
                    meta, text = ln.split("]", 1)
                    meta = meta.lstrip("[")
                    if "-" in meta:
                        a, b = meta.split("-", 1)
                        start = float(a.replace("s", "").strip())
                        end = float(b.replace("s", "").strip())
                        duration = max(0.0, end - start)
                        candidates.append(
                            {
                                "start": start,
                                "end": end,
                                "label": text.strip(),
                                "duration": duration,
                            }
                        )
            except Exception:
                continue

        if not candidates:
            return None

        # sort by duration or length of label
        candidates.sort(key=lambda x: (-x["duration"], -len(x.get("label", ""))))
        selected = []
        for item in candidates[:2]:
            selected.append(
                {"start": item["start"], "end": item["end"], "label": item["label"]}
            )
        if len(selected) == 2:
            return selected
        return None
