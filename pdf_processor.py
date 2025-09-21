import pdfplumber
from pathlib import Path
import re
from PIL import Image
from io import BytesIO
from typing import Dict, List, Optional, Any
import tempfile
import os

def find_pdf_files(folder_path: str) -> List[Path]:
    """
    Finds all PDF files in the given folder path.

    Args:
        folder_path: The path to the folder.

    Returns:
        List of Path objects representing the PDF files.
    """
    return list(Path(folder_path).glob("*.pdf"))

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
                page_data["has_tables"] = True
                page_data["tables"] = tables

            # Check for images
            if page.images:
                page_data["has_images"] = True

            all_pages_content.append(page_data)

    return all_pages_content

def extract_images_from_pdf(pdf_path: str) -> Dict[str, bytes]:
    """
    Extracts images from a PDF file.

    Args:
        pdf_path: The path to the PDF file.

    Returns:
        Dictionary where keys are image names and values are image data.
    """
    extracted_images = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            images = page.images
            for i, img in enumerate(images):
                image_name = f"page_{page.page_number}_img_{i+1}"
                if hasattr(img, 'stream') and hasattr(img['stream'], 'get_data'):
                    extracted_images[image_name] = img['stream'].get_data()
                elif 'data' in img:
                    extracted_images[image_name] = img['data']

    return extracted_images

def extract_measurements_from_pdf(pdf_content: List[Dict[str, Any]], use_gemini: bool = True) -> Dict[str, Any]:
    """
    Extracts measurements from PDF content using pattern matching or Gemini LLM.

    Args:
        pdf_content: Analyzed PDF content from analyze_pdf_content.
        use_gemini: Whether to use Gemini LLM for extraction (default True).

    Returns:
        Dictionary of extracted measurements.
    """

    # Try Gemini LLM first if enabled
    if use_gemini:
        try:
            from pdf_processor_enhanced import extract_with_llm

            # Combine all text from PDF
            all_text = []
            for page in pdf_content:
                all_text.extend(page.get('text_lines', []))
                # Also add table content
                if page.get('tables'):
                    for table in page['tables']:
                        for row in table:
                            for cell in row:
                                if cell:
                                    all_text.append(str(cell))

            full_text = '\n'.join(all_text)
            return extract_with_llm(full_text, use_gemini=True)

        except Exception as e:
            print(f"[INFO] Gemini extraction failed, falling back to pattern matching: {e}")

    # Fallback to original pattern matching
    measurements = {}

    # Enhanced field mapping with medical term synonyms
    field_mapping = {
        'LVEDD': ['LVEDD', 'DDVI', 'LVIDd', 'LVEDd', 'diámetro diastólico'],
        'LVESD': ['LVESD', 'DSVI', 'LVIDs', 'LVESd', 'diámetro sistólico'],
        'LVEF': ['LVEF', 'EF', 'FEVI', 'fracción de eyección'],
        'PWd': ['PWd', 'LVPWd', 'Posterior Wall', 'pared posterior'],
        'IVSd': ['IVSd', 'IVSD', 'Septum', 'septo', 'septum diastolic'],
        'LA': ['LA', 'Left Atrium', 'AI', 'aurícula izquierda'],
        'AOD': ['AOD', 'Ao', 'Aorta', 'aortic root', 'raíz aórtica'],
        'EDV': ['EDV', 'LVEDV', 'volumen diastólico'],
        'ESV': ['ESV', 'LVESV', 'volumen sistólico'],
        'SV': ['SV', 'stroke volume', 'volumen latido'],
        'FS': ['FS', 'fractional shortening', 'fracción acortamiento'],
        'E/A': ['E/A', 'E/A ratio', 'relación E/A'],
        'TAPSE': ['TAPSE'],
        'FAC': ['FAC', 'fractional area change'],
        'PAPS': ['PAPS', 'PAP', 'presión pulmonar']
    }

    # Units to look for
    units = ['mm', 'cm', 'ml', 'g', 'ms', 'mmHg', 'cm²', 'cm/s', 'ml/s', 'm²', 'ml/m²', 'cm²/m²', 'g/m²', '%']

    # Process all text from all pages
    all_text = []
    for page in pdf_content:
        all_text.extend(page.get('text_lines', []))

        # Also process tables if present
        if page.get('has_tables') and page.get('tables'):
            for table in page['tables']:
                for row in table:
                    for cell in row:
                        if cell:
                            all_text.append(str(cell))

    # Search for measurements in text
    for line in all_text:
        if not line:
            continue

        line_lower = line.lower()

        # Check each measurement pattern
        for key, patterns in field_mapping.items():
            for pattern in patterns:
                if pattern.lower() in line_lower:
                    # Extract numeric value following the pattern
                    numeric_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(' + '|'.join(units) + ')?', line)
                    if numeric_match:
                        value = numeric_match.group(1).replace(',', '.')
                        unit = numeric_match.group(2) if numeric_match.group(2) else ''

                        # Store the measurement
                        if key not in measurements:
                            measurements[key] = {
                                'value': value,
                                'unit': unit
                            }
                        break

    return measurements

def extract_wall_motion_scores(pdf_content: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """
    Extracts wall motion scores (WMS) from PDF content.

    Args:
        pdf_content: Analyzed PDF content.

    Returns:
        Dictionary with motility data.
    """
    motility_data = {}

    # Segment names to look for
    segments = [
        'basal anterior', 'basal anteroseptal', 'basal inferoseptal',
        'basal inferior', 'basal inferolateral', 'basal anterolateral',
        'mid anterior', 'mid anteroseptal', 'mid inferoseptal',
        'mid inferior', 'mid inferolateral', 'mid anterolateral',
        'apical anterior', 'apical septal', 'apical inferior', 'apical lateral',
        'apex'
    ]

    # Process all tables looking for WMS data
    for page in pdf_content:
        if page.get('has_tables') and page.get('tables'):
            for table in page['tables']:
                for row in table:
                    if not row:
                        continue

                    # Convert row to string for searching
                    row_text = ' '.join(str(cell) if cell else '' for cell in row).lower()

                    # Check if this row contains segment data
                    for segment in segments:
                        if segment in row_text:
                            # Try to extract scores (baseline, peak, recovery)
                            scores = []
                            for cell in row:
                                if cell and re.match(r'^\d+$', str(cell).strip()):
                                    scores.append(int(cell))

                            if len(scores) >= 3:
                                motility_data[segment] = scores[:3]  # [baseline, peak, recovery]
                            elif len(scores) > 0:
                                motility_data[segment] = scores
                            break

    # Format for compatibility with existing system
    if motility_data:
        return {
            'mot': [
                {'key': key, 'motilidad': values}
                for key, values in motility_data.items()
            ]
        }

    return {}

def extract_patient_info_from_pdf(pdf_content: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extracts patient information from PDF content.

    Args:
        pdf_content: Analyzed PDF content.

    Returns:
        Dictionary with patient information.
    """
    patient_info = {}

    # Patterns to look for
    patterns = {
        'Name': r'(?:name|nombre|patient|paciente)[:\s]+([^\n]+)',
        'Patient_ID': r'(?:id|mrn|historia|hc)[:\s]+([^\n]+)',
        'Gender': r'(?:gender|sex|género|sexo)[:\s]+([MF]|Male|Female|Masculino|Femenino)',
        'Age': r'(?:age|edad)[:\s]+(\d+)',
        'Exam_Date': r'(?:date|fecha|exam date|fecha examen)[:\s]+([^\n]+)',
        'Height': r'(?:height|altura)[:\s]+(\d+(?:\.\d+)?)\s*(cm|m)?',
        'Weight': r'(?:weight|peso)[:\s]+(\d+(?:\.\d+)?)\s*(kg|lb)?',
        'BSA': r'(?:bsa|superficie corporal)[:\s]+(\d+(?:\.\d+)?)',
        'HR': r'(?:hr|heart rate|fc|frecuencia)[:\s]+(\d+)',
        'BP': r'(?:bp|blood pressure|presión|pa)[:\s]+(\d+/\d+)'
    }

    # Process all text
    all_text = '\n'.join(
        line for page in pdf_content
        for line in page.get('text_lines', [])
    )

    # Search for patient info patterns
    for key, pattern in patterns.items():
        match = re.search(pattern, all_text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            patient_info[key] = value

    return patient_info

def pdf_to_docx_data(pdf_path: str) -> Dict[str, Any]:
    """
    Converts PDF data into a format compatible with existing DOCX processing.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dictionary with extracted data ready for template processing.
    """
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

    # Combine all data
    combined_data = {
        'patient_info': patient_info,
        'measurements': measurements,
        'motility': motility,
        'images': image_paths,
        'source_type': 'pdf'
    }

    return combined_data

def format_for_template(pdf_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats PDF-extracted data for use with existing DocxTemplate system.

    Args:
        pdf_data: Data extracted from PDF.

    Returns:
        Dictionary formatted for template rendering.
    """
    context = {}

    # Add patient info
    if 'patient_info' in pdf_data:
        context.update(pdf_data['patient_info'])

    # Add measurements
    if 'measurements' in pdf_data:
        for key, value_dict in pdf_data['measurements'].items():
            if isinstance(value_dict, dict) and 'value' in value_dict:
                context[key] = value_dict['value']
                # Also add with unit suffix if unit exists
                if value_dict.get('unit'):
                    context[f"{key}_unit"] = value_dict['unit']
            else:
                context[key] = value_dict

    # Add motility data if present
    if 'motility' in pdf_data and pdf_data['motility']:
        context['mot'] = pdf_data['motility']['mot']

    return context