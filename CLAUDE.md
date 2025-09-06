# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a medical report generation system that processes echocardiogram documents from medical equipment (Vinno) and automatically generates structured medical reports. The system supports multiple types of cardiovascular studies:

- **Cardiac Doppler** (card): Standard echocardiogram reports
- **Stress Echocardiogram** (stress): Stress test reports with wall motion analysis
- **Carotid Doppler** (carotid): Carotid artery studies
- **Arterial Doppler** (art): Arterial studies
- **Venous Doppler** (ven): Venous studies

## Architecture

The system has two main entry points:
- `main.py`: FastAPI-based API (primary, production-ready)
- `app.py`: Flask-based API (legacy, simpler implementation)

### Core Components

1. **Template Manager** (`template_manager.py`): Automatically selects appropriate report templates based on study type by analyzing filename and document content
2. **Patient Data Extraction** (`patient_data_extraction.py`): Extracts patient information, measurements, and images from source documents
3. **Auxiliary Calculations** (`aux_calculations.py`): Performs medical calculations and data transformations
4. **Report Generation**: Uses DocxTemplate to render final reports from templates

### Processing Flow

**Single File Processing** (`/generar_informe`):
1. Document upload via `/generar_informe` endpoint
2. Template selection based on filename patterns or document analysis
3. Patient data extraction from structured tables
4. Image extraction and processing
5. Medical calculations and measurements processing
6. Template rendering with extracted context
7. Generated report download

**Batch Processing** (`/generar_informes_multiples`):
1. Multiple documents upload via `/generar_informes_multiples` endpoint
2. Each file processed individually using the same pipeline
3. Error handling for individual files (continues processing others)
4. All generated reports packaged into a ZIP file
5. Error log included if any files failed processing
6. ZIP file download with all results

## Development Commands

### Running the Application
```bash
# FastAPI version (recommended)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Flask version (legacy)
python app.py
```

## API Endpoints

### Single File Processing
- **Endpoint**: `POST /generar_informe`
- **Input**: Single file upload (multipart/form-data)
- **Output**: Single DOCX file download
- **Accepted formats**: .docx, .doc

### Batch Processing  
- **Endpoint**: `POST /generar_informes_multiples`
- **Input**: Multiple file uploads (multipart/form-data)
- **Output**: ZIP file containing all generated reports
- **Limits**: Maximum 50 files per batch
- **Features**: 
  - Individual error handling (continues if some files fail)
  - Error log included in ZIP if any files failed
  - Automatic .doc to .docx conversion

### Testing
```bash
# Run tests using pytest
python -m pytest test_main.py -v

# Run specific test
python -m pytest test_main.py::test_generar_informe_ok -v
```

### Docker Development
```bash
# Build image
docker build -t eco-app .

# Run container
docker run -p 8000:8000 eco-app
```

### Dependencies Installation
```bash
pip install -r requirements.txt
```

## Environment Configuration

Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

Required environment variables:
- `OPENAI_API_KEY`: OpenAI API key for text analysis (used in Flask version)

## Template System

Templates are stored as DOCX files in the root directory:
- `auto card.docx`: Cardiac doppler template
- `auto stress.docx`: Stress echocardiogram template  
- `auto vc.docx`: Carotid studies template
- `auto art.docx`: Arterial studies template
- `auto ven.docx`: Venous studies template

Template selection is automatic based on:
1. Filename keywords (Carotid, Arteries, Veins)
2. Document content analysis (WMS presence for stress studies)
3. Default to cardiac template if no match

## File Processing Requirements

- Input: Word documents (.docx or .doc) from Vinno echocardiograph equipment
- LibreOffice required for .doc to .docx conversion
- Automatic document structure parsing expects specific table layouts from medical equipment

## Key Technical Details

- Uses `python-docx` for document manipulation
- `docxtpl` for template rendering
- PIL for image processing
- FastAPI with CORS enabled for frontend integration
- Supports both local development and containerized deployment