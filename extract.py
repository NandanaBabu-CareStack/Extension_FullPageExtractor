#this is the best
import requests
import json
import re
import time
import asyncio
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from procedure import ProcedureExtractor

class TextInput(BaseModel):
    text: str

class ExtractionResult(BaseModel):
    insurance_data: Dict[str, Any]
    procedures: List[Dict[str, str]]

class OllamaInsuranceExtractor:
    """
    Ollama-based insurance data extractor - completely offline
    Uses local Ollama models for confidential data processing
    """

    def __init__(self, model_name="llama3.2:3b", ollama_url="http://localhost:11434"):
        self.model_name = model_name
        self.ollama_url = ollama_url

        self.fields = [
            "Subscriber ID", "Effective Date", "Termination Date", "Carrier Name",
            "Plan Name", "Group Number", "Insurance Type", "Employer",
            "Plan Reset Date", "Plan Type", "Benefits Coordination Method",
            "Verified Date", "Participation Type", "Family Maximum",
            "Family Max. Remaining", "Individual Maximum", "Individual Max. Remaining",
            "Family Deductible", "Family Deductible Remaining",
            "Individual Deductible", "Individual Deductible Remaining"
        ]

        self._check_ollama_connection()
        self._ensure_model_exists()

    def _check_ollama_connection(self):
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise Exception(f"Ollama returned status code: {response.status_code}")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Ollama: {e}")

    def _ensure_model_exists(self):
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            models = response.json().get("models", [])
            model_exists = any(model["name"] == self.model_name for model in models)

            if not model_exists:
                self._pull_model()
        except Exception as e:
            raise RuntimeError(f"Error checking model: {e}")

    def _pull_model(self):
        try:
            response = requests.post(
                f"{self.ollama_url}/api/pull",
                json={"name": self.model_name},
                stream=True,
                timeout=300
            )
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("status") == "success":
                        break
        except Exception as e:
            raise RuntimeError(f"Error downloading model: {e}")

    def extract(self, text: str) -> Dict[str, Any]:
        start_time = time.time()

        if not text or text.strip() == "":
            empty_result = {field: "Not Available" for field in self.fields}
            print(f"[Timing] Extraction skipped (empty text): {time.time() - start_time:.2f} seconds")
            return empty_result

        prompt_creation_start = time.time()
        prompt = self._create_extraction_prompt(text)
        prompt_creation_end = time.time()

        llm_call_start = time.time()
        response = self._call_ollama(prompt)
        llm_call_end = time.time()

        parse_start = time.time()
        extracted_data = self._parse_llm_response(response)
        parse_end = time.time()

        total_time = time.time() - start_time

        print(f"[Timing] Prompt creation: {prompt_creation_end - prompt_creation_start:.2f} seconds")
        print(f"[Timing] Ollama API call: {llm_call_end - llm_call_start:.2f} seconds")
        print(f"[Timing] Response parsing: {parse_end - parse_start:.2f} seconds")
        print(f"[Timing] Total extraction time: {total_time:.2f} seconds")

        return extracted_data

    def _create_extraction_prompt(self, text: str) -> str:
        fields_list = "\n".join([f"- {field}" for field in self.fields])

        prompt = f"""You are an expert data extraction assistant specializing in insurance information. Carefully extract the requested fields from the document below.

DOCUMENT:
{text}

FIELDS TO EXTRACT:
{fields_list}

INSTRUCTIONS:
1. Extract ONLY information explicitly stated in the document; do not infer or guess.
2. If a field is missing, unclear, or cannot be confidently determined, set its value to the exact string "Not Available".
3. Ignore irrelevant, ambiguous, or noisy text that may appear.
4. Return ONLY a valid, well-formed JSON object with field names as keys and extracted values as strings.
5. Do NOT add explanations, comments, or any text outside the JSON object.
6. For both "Carrier Name" and "Employer" fields, use the insurance company name found in the text (e.g., if "Cigna" is found, use it for both fields).
7. Return "Plan Reset Date" exactly as it appears in the string after "Plan Renews |" in the raw text (e.g., "Every Calendar Year"). Print it exactly as found.
8. Default "Insurance Type" to "dental" if it is not explicitly stated.
9. Plan Name should be the corresponding group name in the raw text, and Plan Type is the text after "Plan Type".
10. If the raw text contains "Coverage To: Present", retain the exact word "Present" as the value for the field "Termination Date".
11. Pay special attention to these numeric fields and ensure correctness:
    - "Family Maximum"
    - "Family Max. Remaining"
    - "Individual Maximum"
    - "Individual Max. Remaining"
    - "Family Deductible"
    - "Family Deductible Remaining"
    - "Individual Deductible"
    - "Individual Deductible Remaining"
12. Ensure all values are accurate, clean, and formatted consistently, even if the input text is messy or unstructured.
13. If a field is missing, unclear, or cannot be confidently determined, set its value to the exact string 'Not Available'.
14. Participaton Type is not relationship.So dont put its value.

JSON OUTPUT:"""
        return prompt

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

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(0)
                data = json.loads(json_str)

                result = {}
                for field in self.fields:
                    result[field] = data.get(field, "Not Available")

                return result
            except json.JSONDecodeError:
                pass

        # Fallback parsing if JSON fails
        result = {}
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line:
                for field in self.fields:
                    if field.lower() in line.lower():
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            value = parts[1].strip().strip('"').strip(',')
                            if value and value.lower() not in ['not available', 'n/a', 'none', '']:
                                result[field] = value
                                break
        for field in self.fields:
            if field not in result:
                result[field] = "Not Available"

        return result

# Initialize FastAPI app
app = FastAPI(
    title="Insurance Data Extractor API",
    description="API for extracting insurance information and procedures from text using Ollama LLM",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize extractors
insurance_extractor = OllamaInsuranceExtractor()
procedure_extractor = ProcedureExtractor()

async def run_extractors(text: str) -> ExtractionResult:
    # Run both extractors concurrently
    insurance_task = asyncio.create_task(asyncio.to_thread(insurance_extractor.extract, text))
    procedure_task = asyncio.create_task(asyncio.to_thread(procedure_extractor.extract_procedures, text))
    
    # Wait for both tasks to complete
    insurance_data, procedures = await asyncio.gather(insurance_task, procedure_task)
    
    return ExtractionResult(
        insurance_data=insurance_data,
        procedures=procedures
    )

@app.post("/extract")
async def extract_data(input_data: TextInput) -> ExtractionResult:
    try:
        if not input_data.text or input_data.text.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="No text provided for extraction"
            )
            
        return await run_extractors(input_data.text)
            
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama service is not available: {str(e)}"
        )
    except Exception as e:
        print(f"Error during extraction: {str(e)}")  # Add logging
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process the text: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
