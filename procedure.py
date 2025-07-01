import re
import json
import requests
from typing import List, Dict


class ProcedureExtractor:
    def __init__(self, model_name="llama3.2:3b", ollama_url="http://localhost:11434"):
        self.model_name = model_name
        self.ollama_url = ollama_url

    def _call_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 1000,
            }
        }

        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json=payload,
            timeout=1000
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        else:
            raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text}")

    def extract_procedures(self, text: str) -> List[Dict[str, str]]:
        prompt = f"""
You are a highly accurate data extraction assistant. From the following dental benefits text, extract all dental procedure codes and their frequency information.

📋 For each procedure code, extract and return these fields:
- "code": the dental procedure code (e.g., D0210)
- "frequency": the full frequency string (e.g., "Twice Per Calendar Year")
- "limited_to": the total allowed usage, from strings like "1 of 2" → "2"
- "every": the amount already used or available per period, from "1 of 2" → "1"
- "duration": the duration or time period mentioned in the frequency (e.g., "Calendar Year", "36 Consecutive Months")

📌 IMPORTANT RULES:
- Only extract entries that include frequency information.
- If the phrase "X of Y" appears (e.g., "1 of 2"), then:
    - "every" = X
    - "limited_to" = Y
- For "every" and "duration", if not found in "X of Y", try to infer them from the "frequency" phrase.
- Each returned object MUST contain all 5 fields, even if you must return an empty string for any missing values.
- Do NOT return anything except the JSON array.

✅ Expected output format:
[
  {{
    "code": "D0120",
    "frequency": "Once Per 36/60 Consecutive Months",
    "limited_to": "1",
    "every": "1",
    "duration": "Consecutive Months"
  }},
  ...
]

TEXT TO PARSE:
{text}

OUTPUT JSON ONLY:
"""

        response = self._call_ollama(prompt)

        # Try to isolate valid JSON
        json_match = re.search(r'\[\s*{.*?}\s*\]', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                print("LLM response not valid JSON.")
        return []


# Example usage
if __name__ == "__main__":
    extractor = ProcedureExtractor()
    
    with open("raw_input.txt", "r", encoding="utf-8") as file:
        raw_text = file.read()

    procedures = extractor.extract_procedures(raw_text)
    print(json.dumps(procedures, indent=2))
