"""
Enhanced PDF processor with optional Gemini LLM extraction
"""

import pdfplumber
from pathlib import Path
import re
from PIL import Image
from io import BytesIO
from typing import Dict, List, Optional, Any
import tempfile
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def extract_with_llm(text: str, use_gemini: bool = False) -> Dict[str, Any]:
    """
    Extract measurements using Gemini LLM if API key is available.
    Falls back to pattern matching if not available.

    Args:
        text: Text content to analyze
        use_gemini: Whether to use Gemini for extraction

    Returns:
        Dictionary of extracted measurements
    """

    measurements = {}

    # Check if Gemini API key is available and use_gemini is True
    google_api_key = os.getenv('GOOGLE_API_KEY')

    if use_gemini and google_api_key and google_api_key != 'your_gemini_api_key_here':
        try:
            # Only import if we're actually using it
            import langextract as lx

            # Define extraction prompt
            prompt_description = """
            Extract echocardiographic measurements and motility findings into structured entities.

            1. Extract all measurements with canonical_key (normalized name), value, and unit.
            2. Extract wall motion scores (WMS) with baseline, peak, and recovery values.
            3. Normalize synonyms:
               - LVEDD = DDVI = LVIDd = LVEDd
               - LVESD = DSVI = LVIDs = LVESd
               - LVEF = EF = FEVI
               - PWd = LVPWd = Posterior Wall
               - IVSd = IVSD = Septum Diastolic
               - LA = Left Atrium = AI
            """

            # Define examples
            examples = [
                lx.data.ExampleData(
                    text="DDVI 40 mm, DSVI 25 mm, EF 55 %",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="measurement",
                            extraction_text="DDVI",
                            attributes={"measurement_group": "LVEDD", "value": 40, "unit": "mm"}
                        ),
                        lx.data.Extraction(
                            extraction_class="measurement",
                            extraction_text="DSVI",
                            attributes={"measurement_group": "LVESD", "value": 25, "unit": "mm"}
                        ),
                        lx.data.Extraction(
                            extraction_class="measurement",
                            extraction_text="EF",
                            attributes={"measurement_group": "LVEF", "value": 55, "unit": "%"}
                        ),
                    ]
                ),
            ]

            # Run extraction
            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt_description,
                examples=examples,
                model_id="gemini-2.5-pro",
                api_key=google_api_key
            )

            # Process results
            for extraction in result.extractions:
                attrs = extraction.attributes or {}
                if "measurement_group" in attrs:
                    key = attrs["measurement_group"]
                    measurements[key] = {
                        "value": attrs.get("value"),
                        "unit": attrs.get("unit")
                    }

            print(f"[INFO] Extracted {len(measurements)} measurements using Gemini")
            return measurements

        except ImportError:
            print("[WARNING] langextract not installed. Install with: pip install langextract")
        except Exception as e:
            print(f"[WARNING] Gemini extraction failed: {e}. Falling back to pattern matching.")

    # Fallback to pattern matching if Gemini not available or failed
    return extract_measurements_pattern_matching(text)


def extract_measurements_pattern_matching(text: str) -> Dict[str, Any]:
    """
    Extract measurements using pattern matching (fallback method).

    Args:
        text: Text content to analyze

    Returns:
        Dictionary of extracted measurements
    """
    measurements = {}

    # Enhanced field mapping
    field_mapping = {
        'LVEDD': ['LVEDD', 'DDVI', 'LVIDd', 'LVEDd', 'diámetro diastólico'],
        'LVESD': ['LVESD', 'DSVI', 'LVIDs', 'LVESd', 'diámetro sistólico'],
        'LVEF': ['LVEF', 'EF', 'FEVI', 'fracción de eyección'],
        'PWd': ['PWd', 'LVPWd', 'Posterior Wall', 'pared posterior'],
        'IVSd': ['IVSd', 'IVSD', 'Septum', 'septo', 'septum diastolic'],
        'LA': ['LA', 'Left Atrium', 'AI', 'aurícula izquierda'],
        'EDV': ['EDV', 'LVEDV', 'volumen diastólico'],
        'ESV': ['ESV', 'LVESV', 'volumen sistólico'],
        'SV': ['SV', 'stroke volume', 'volumen latido'],
    }

    units = ['mm', 'cm', 'ml', 'g', 'ms', 'mmHg', 'cm²', 'cm/s', '%']

    lines = text.split('\n') if isinstance(text, str) else text

    for line in lines:
        if not line:
            continue

        line_lower = line.lower()

        for key, patterns in field_mapping.items():
            for pattern in patterns:
                if pattern.lower() in line_lower:
                    # Extract numeric value
                    numeric_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(' + '|'.join(units) + ')?', line)
                    if numeric_match:
                        value = numeric_match.group(1).replace(',', '.')
                        unit = numeric_match.group(2) if numeric_match.group(2) else ''

                        if key not in measurements:
                            measurements[key] = {
                                'value': value,
                                'unit': unit
                            }
                        break

    return measurements


def analyze_pdf_with_llm(pdf_path: str, use_gemini: bool = False) -> Dict[str, Any]:
    """
    Analyzes PDF content with optional Gemini LLM enhancement.

    Args:
        pdf_path: Path to the PDF file
        use_gemini: Whether to use Gemini for extraction (requires API key)

    Returns:
        Dictionary with all extracted data
    """

    all_text = []
    tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract text
            if page.extract_text():
                all_text.append(page.extract_text())

            # Extract tables
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)

    # Combine all text
    full_text = '\n'.join(all_text)

    # Extract measurements (with or without LLM)
    measurements = extract_with_llm(full_text, use_gemini)

    # Extract patient info using patterns
    patient_info = {}
    patterns = {
        'Name': r'(?:name|nombre|patient|paciente)[:\s]+([^\n]+)',
        'Patient_ID': r'(?:id|mrn|historia|hc)[:\s]+([^\n]+)',
        'Gender': r'(?:gender|sex|género|sexo)[:\s]+([MF]|Male|Female|Masculino|Femenino)',
        'Age': r'(?:age|edad)[:\s]+(\d+)',
        'Exam_Date': r'(?:date|fecha|exam date|fecha examen)[:\s]+([^\n]+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            patient_info[key] = match.group(1).strip()

    return {
        'patient_info': patient_info,
        'measurements': measurements,
        'tables': tables,
        'source_type': 'pdf',
        'extraction_method': 'gemini' if use_gemini and measurements else 'pattern_matching'
    }