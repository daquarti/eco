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

            # Define examples for structured extraction
            examples = [
                lx.data.ExampleData(
                    text="DDVI 40 mm, DSVI 25 mm, EF 55 %, PWd 10 mm",
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
                        lx.data.Extraction(
                            extraction_class="measurement",
                            extraction_text="PWd",
                            attributes={"measurement_group": "PWd", "value": 10, "unit": "mm"}
                        ),
                    ]
                )
            ]

            # Run extraction with Gemini
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

        except Exception as e:
            print(f"[WARNING] Gemini extraction failed, falling back to pattern matching: {e}")
            # Fall through to pattern matching

    # Fallback to pattern matching if Gemini is not available or failed
    if not measurements:
        measurements = extract_measurements_pattern_matching(text)

    return measurements

def extract_measurements_pattern_matching(text: str) -> Dict[str, Any]:
    """
    Extract measurements using regex pattern matching as fallback.

    Args:
        text: Text content to analyze

    Returns:
        Dictionary of extracted measurements
    """
    measurements = {}

    # Common measurement patterns
    patterns = {
        'LVEF': r'(?:LVEF|EF|FEVI)[\s:]*(\d+(?:\.\d+)?)[\s]*%',
        'LVEDD': r'(?:LVEDD|DDVI|LVIDd|LVEDd)[\s:]*(\d+(?:\.\d+)?)[\s]*(?:mm|cm)',
        'LVESD': r'(?:LVESD|DSVI|LVIDs|LVESd)[\s:]*(\d+(?:\.\d+)?)[\s]*(?:mm|cm)',
        'PWd': r'(?:PWd|LVPWd|Posterior Wall)[\s:]*(\d+(?:\.\d+)?)[\s]*(?:mm|cm)',
        'IVSd': r'(?:IVSd|IVSD|Septum)[\s:]*(\d+(?:\.\d+)?)[\s]*(?:mm|cm)',
        'LA': r'(?:LA|Left Atrium|AI)[\s:]*(\d+(?:\.\d+)?)[\s]*(?:mm|cm)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = 'mm' if key != 'LVEF' else '%'
            measurements[key] = {"value": value, "unit": unit}

    return measurements

def analyze_pdf_content(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Analyzes the content of a PDF file, extracting text and tables from each page.

    Args:
        pdf_path: The path to the PDF file.

    Returns:
        List of dictionaries, each representing a page with extracted content.
    """
    all_pages_content = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_data = {
                "page_number": page.page_number,
                "text_lines": [],
                "tables": [],
                "has_tables": False,
                "has_images": False
            }

            # Extract text
            if page.extract_text():
                page_data["text_lines"] = page.extract_text().splitlines()

            # Extract tables
            tables = page.extract_tables()
            if tables:
                page_data["tables"] = tables
                page_data["has_tables"] = True

            # Check for images
            if hasattr(page, 'images') and page.images:
                page_data["has_images"] = True

            all_pages_content.append(page_data)

    return all_pages_content

def extract_images_from_pdf(pdf_path: str) -> Dict[str, bytes]:
    """
    Extracts images from a PDF file and returns them as a dictionary.

    Args:
        pdf_path: The path to the PDF file.

    Returns:
        Dictionary where keys are image names and values are image data.
    """
    extracted_images = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                if hasattr(page, 'images'):
                    images = page.images
                    for i, img in enumerate(images):
                        image_name = f"page_{page.page_number}_img_{i+1}"
                        try:
                            # Try to get image data
                            if hasattr(img, 'stream') and hasattr(img['stream'], 'get_data'):
                                extracted_images[image_name] = img["stream"].get_data()
                        except Exception as e:
                            print(f"[WARNING] Could not extract image {image_name}: {e}")
                            continue
    except Exception as e:
        print(f"[WARNING] Image extraction failed: {e}")

    return extracted_images

def extract_patient_info_from_pdf(pdf_content: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract patient information from PDF content.

    Args:
        pdf_content: List of page content dictionaries

    Returns:
        Dictionary with patient information
    """
    patient_info = {
        'Name': 'Unknown',
        'Exam_Date': 'Unknown',
        'Gender': 'M',  # Default to Male if not found
        'Age': '0',
        'ID': 'Unknown'
    }

    # Combine all text from all pages
    all_text = ""
    for page in pdf_content:
        if page.get("text_lines"):
            all_text += "\n".join(page["text_lines"]) + "\n"

    # Pattern matching for patient info
    patterns = {
        'Name': r'(?:Patient|Paciente|Name|Nombre)[\s:]*([A-Za-z\s]+)',
        'Exam_Date': r'(?:Date|Fecha|Exam)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        'Gender': r'(?:Gender|Sexo|Sex)[\s:]*([MFmf])',
        'Age': r'(?:Age|Edad)[\s:]*(\d+)',
        'ID': r'(?:ID|DNI|Document)[\s:]*(\d+)'
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, all_text, re.IGNORECASE)
        if match:
            patient_info[key] = match.group(1).strip()

    return patient_info

def extract_measurements_from_pdf(pdf_content: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract measurements from PDF content using LLM or pattern matching.

    Args:
        pdf_content: List of page content dictionaries

    Returns:
        Dictionary with measurements
    """
    # Combine all text
    all_text = ""
    for page in pdf_content:
        if page.get("text_lines"):
            all_text += "\n".join(page["text_lines"]) + "\n"

    # Try Gemini extraction first, fallback to pattern matching
    measurements = extract_with_llm(all_text, use_gemini=True)

    return measurements

def extract_wall_motion_scores(pdf_content: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract wall motion scores from PDF content.

    Args:
        pdf_content: List of page content dictionaries

    Returns:
        Dictionary with motility data
    """
    motility = {}

    # Look for wall motion score patterns
    for page in pdf_content:
        if page.get("text_lines"):
            for line in page["text_lines"]:
                # Look for WMS patterns like "Basal Anterior 1 1 1"
                wms_match = re.search(r'(Basal|Mid|Apical)\s+(\w+)\s+(\d)\s+(\d)\s+(\d)', line, re.IGNORECASE)
                if wms_match:
                    segment = f"{wms_match.group(1)} {wms_match.group(2)}"
                    motility[segment] = {
                        'baseline': int(wms_match.group(3)),
                        'peak': int(wms_match.group(4)),
                        'recovery': int(wms_match.group(5))
                    }

    return {'mot': motility} if motility else {}

def pdf_to_docx_data(pdf_path: str) -> Dict[str, Any]:
    """
    Converts PDF data into a format compatible with existing DOCX processing.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dictionary with extracted data ready for template processing.
    """
    try:
        # Analyze PDF content
        pdf_content = analyze_pdf_content(pdf_path)

        # Extract different types of data
        patient_info = extract_patient_info_from_pdf(pdf_content)
        measurements = extract_measurements_from_pdf(pdf_content)
        motility = extract_wall_motion_scores(pdf_content)

        # Extract images and save them temporarily
        images = extract_images_from_pdf(pdf_path)
        image_paths = {}

        if images:
            temp_dir = tempfile.mkdtemp()
            for name, data in images.items():
                image_path = os.path.join(temp_dir, f"{name}.png")
                with open(image_path, 'wb') as f:
                    f.write(data)
                image_paths[name] = image_path

        return {
            'patient_info': patient_info,
            'measurements': measurements,
            'motility': motility,
            'images': image_paths
        }

    except Exception as e:
        print(f"[ERROR] PDF processing failed: {e}")
        # Return minimal data structure to prevent crashes
        return {
            'patient_info': {
                'Name': 'PDF_Processing_Error',
                'Exam_Date': 'Unknown',
                'Gender': 'M',
                'Age': '0',
                'ID': 'Unknown'
            },
            'measurements': {},
            'motility': {},
            'images': {}
        }

def format_for_template(pdf_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats PDF extracted data for template rendering.

    Args:
        pdf_data: Dictionary with extracted PDF data.

    Returns:
        Dictionary formatted for template context.
    """
    try:
        context = {}

        # Add patient info
        if 'patient_info' in pdf_data:
            context.update(pdf_data['patient_info'])

        # Add measurements
        if 'measurements' in pdf_data:
            context.update(pdf_data['measurements'])

        # Format motility data if present
        if 'motility' in pdf_data and pdf_data['motility']:
            context.update(pdf_data['motility'])

        return context

    except Exception as e:
        print(f"[ERROR] Template formatting failed: {e}")
        return {
            'Name': 'Formatting_Error',
            'Exam_Date': 'Unknown',
            'Gender': 'M',
            'Age': '0',
            'ID': 'Unknown'
        }