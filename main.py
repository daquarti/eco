import os
import shutil
import tempfile
import zipfile
import logging
import time
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from docx import Document
from docxtpl import DocxTemplate

from template_manager import template_selector
from patient_data_extraction import extract_patient_info, image_extractor, generate_motility_report, get_measure_table, get_measurements, get_mot_table, mot_extractor
from aux_calculations import expand_dict_with_lists_inplace, calc_e_e_stress

app = FastAPI(
    title="EcoReport API",
    description="API para generación de informes médicos desde archivos Word/PDF",
    version="2.0.0"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safe import for PDF processing with enhanced fallback
try:
    from patient_data_extraction import process_pdf_images
    from pdf_processor import pdf_to_docx_data, format_for_template
    PDF_PROCESSING_AVAILABLE = True
    logger.info("Standard PDF processing modules loaded successfully")
except ImportError as e:
    logger.warning(f"Standard PDF processing not available: {e}")

    # Try enhanced PDF processor as fallback
    try:
        from pdf_processor_enhanced import pdf_to_docx_data, format_for_template
        from patient_data_extraction import process_pdf_images
        PDF_PROCESSING_AVAILABLE = True
        logger.info("Enhanced PDF processing modules loaded successfully")
    except ImportError as e2:
        PDF_PROCESSING_AVAILABLE = False
        logger.error(f"No PDF processing modules available: {e2}")

        # Create dummy functions that provide clear error messages
        def pdf_to_docx_data(pdf_path: str):
            raise HTTPException(
                status_code=503,
                detail="PDF processing temporarily unavailable. Missing dependencies: pdfplumber, langextract. Please use .docx files."
            )

        def format_for_template(pdf_data):
            raise HTTPException(
                status_code=503,
                detail="PDF processing temporarily unavailable. Please use .docx files."
            )

        def process_pdf_images(image_paths, template, tipo):
            raise HTTPException(
                status_code=503,
                detail="PDF processing temporarily unavailable. Please use .docx files."
            )

@app.get("/")
def root():
    return {"message": "API eco3 está activa", "version": "2.0.0", "status": "running"}

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check if Gemini API key is configured
        gemini_configured = bool(os.getenv('GOOGLE_API_KEY') and
                                os.getenv('GOOGLE_API_KEY') != 'your_gemini_api_key_here')

        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "timestamp": time.time(),
                "services": {
                    "pdf_processing": PDF_PROCESSING_AVAILABLE,
                    "word_processing": True,
                    "gemini_llm": gemini_configured and PDF_PROCESSING_AVAILABLE
                }
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )

@app.get("/info")
def system_info():
    """System information endpoint"""
    return {
        "name": "EcoReport API",
        "version": "2.0.0",
        "supported_formats": [".docx", ".doc", ".pdf"],
        "features": {
            "word_processing": True,
            "pdf_processing": PDF_PROCESSING_AVAILABLE,
            "gemini_llm": bool(os.getenv('GOOGLE_API_KEY')) and PDF_PROCESSING_AVAILABLE,
            "batch_processing": True,
            "image_extraction": True,
            "motility_analysis": True
        },
        "endpoints": {
            "single_file": "/generar_informe",
            "multiple_files": "/generar_informes_multiples",
            "debug": "/debug_files",
            "health": "/health"
        }
    }

@app.post("/test_pdf_debug")
async def test_pdf_debug(file: UploadFile = File(...)):
    """Debug endpoint to test PDF processing step by step"""
    import tempfile

    step_info = {"filename": file.filename}

    try:
        # Step 1: Save file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        step_info["step"] = "file_saved"
        step_info["tmp_path"] = tmp_path

        # Step 2: Test PDF analysis
        from pdf_processor import analyze_pdf_content
        pdf_content = analyze_pdf_content(tmp_path)
        step_info["step"] = "pdf_analyzed"
        step_info["pages"] = len(pdf_content)

        # Step 3: Test template selection
        from template_manager import template_selector
        template, tipo = template_selector(tmp_path)
        step_info["step"] = "template_selected"
        step_info["template_type"] = tipo

        # Step 4: Test data extraction
        from pdf_processor import pdf_to_docx_data
        pdf_data = pdf_to_docx_data(tmp_path)
        step_info["step"] = "data_extracted"
        step_info["data_keys"] = list(pdf_data.keys())

        # Cleanup
        os.unlink(tmp_path)

        step_info["success"] = True
        return step_info

    except Exception as e:
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass

        step_info["success"] = False
        step_info["error"] = str(e)
        step_info["error_type"] = type(e).__name__
        return step_info

@app.options("/generar_informes_multiples")
def options_multiple():
    return {"message": "CORS preflight OK"}

@app.post("/debug_files")
def debug_files(files: List[UploadFile] = File(...)):
    """Debug endpoint to see what files are being received"""
    file_info = []
    for file in files:
        info = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(file.file.read()) if hasattr(file.file, 'read') else "unknown"
        }
        file.file.seek(0)  # Reset file pointer
        file_info.append(info)
    
    return {
        "total_files": len(files),
        "files": file_info,
        "valid_files": len([f for f in files if f.filename.lower().endswith(('.doc', '.docx', '.pdf'))]),
        "message": "Debug info - no processing done"
    }

# Configure CORS - adjust origins for production
FRONTEND_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server
    "https://your-frontend-domain.com",  # Production frontend
    "*"  # Allow all for development - remove in production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS if os.getenv("ENVIRONMENT") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

def procesar_archivo_individual(file: UploadFile, tmpdir: str) -> str:
    """
    Procesa un archivo individual y devuelve la ruta del archivo generado.
    """
    logger.info(f"Processing file: {file.filename}")
    logger.info(f"Content type: {file.content_type}")
    logger.info(f"File size: {file.size if hasattr(file, 'size') else 'unknown'}")

    # Validate file size (50MB limit)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"Archivo demasiado grande. Máximo: 50MB")

    # Validate filename
    if not file.filename or len(file.filename) > 255:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    
    # Check file extension
    is_pdf = file.filename.lower().endswith(".pdf")
    is_doc = file.filename.lower().endswith((".docx", ".doc"))

    if not (is_doc or is_pdf):
        raise HTTPException(status_code=400, detail=f"El archivo {file.filename} debe ser .docx, .doc o .pdf")

    # Check if PDF processing is available
    if is_pdf and not PDF_PROCESSING_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Procesamiento de PDF no disponible",
                "message": "El servidor no tiene configuradas las dependencias para procesar archivos PDF",
                "suggestions": ["Use archivos .docx o .doc", "Contacte al administrador si necesita procesamiento PDF"],
                "available_formats": [".docx", ".doc"]
            }
        )

    # Extract just the filename without path for security and compatibility
    safe_filename = os.path.basename(file.filename)
    input_path = os.path.join(tmpdir, safe_filename)
    
    print(f"[DEBUG] Original filename: {file.filename}")
    print(f"[DEBUG] Safe filename: {safe_filename}")
    print(f"[DEBUG] Input path: {input_path}")
    
    # Save uploaded file to temporary directory
    with open(input_path, "wb") as f:
        import shutil
        shutil.copyfileobj(file.file, f)

    # Si es .doc, convertir a .docx usando LibreOffice
    if input_path.lower().endswith('.doc'):
        try:
            # Generar nombre para archivo convertido
            converted_filename = os.path.splitext(os.path.basename(input_path))[0] + '.docx'
            converted_path = os.path.join(tmpdir, converted_filename)
            
            print(f"[INFO] Convirtiendo .doc a .docx usando LibreOffice")
            print(f"[INFO] Input: {input_path}")
            print(f"[INFO] Output: {converted_path}")
            
            # Usar LibreOffice para la conversión inicial .doc -> .docx
            import subprocess
            
            # Buscar LibreOffice en diferentes ubicaciones posibles
            soffice_paths = [
                'soffice',  # En PATH
                '/usr/bin/soffice',
                '/usr/local/bin/soffice',
                '/opt/homebrew/bin/soffice',
                '/Applications/LibreOffice.app/Contents/MacOS/soffice'  # macOS
            ]
            
            soffice_cmd = None
            for path in soffice_paths:
                try:
                    result = subprocess.run([path, '--version'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        soffice_cmd = path
                        break
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            
            if not soffice_cmd:
                raise Exception("No se encontró LibreOffice/soffice en el sistema")
            
            # Convertir usando LibreOffice
            cmd = [
                soffice_cmd,
                '--headless',
                '--convert-to', 'docx',
                '--outdir', tmpdir,
                input_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise Exception(f"LibreOffice falló: {result.stderr}")
            
            # Verificar que el archivo se creó correctamente
            if not os.path.exists(converted_path):
                raise Exception('El archivo .docx convertido no se creó')
            
            size = os.path.getsize(converted_path)
            print(f"[INFO] Archivo convertido exitosamente: {size} bytes")
            
            if size == 0:
                raise Exception('El archivo .docx convertido está vacío')
            
            doc_path = converted_path
            
        except Exception as e:
            print(f"[ERROR] Error en la conversión: {e}")
            raise HTTPException(status_code=500, detail=f"Error convirtiendo archivo .doc a .docx: {str(e)}")
    else:
        doc_path = input_path

    try:
        # Handle PDF files differently
        if doc_path.lower().endswith('.pdf'):
            logger.info(f"Processing PDF file: {doc_path}")

            # Extract data from PDF
            pdf_data = pdf_to_docx_data(doc_path)

            # Select template based on PDF content
            template, tipo = template_selector(doc_path)

            # Format PDF data for template
            context = format_for_template(pdf_data)

            # Add patient info
            info_pac = pdf_data.get('patient_info', {})

            # Process images if available
            if 'images' in pdf_data and pdf_data['images']:
                image = process_pdf_images(pdf_data['images'], template, tipo)
                context['image'] = image['image']

            # Add motility if available
            if 'motility' in pdf_data and pdf_data['motility']:
                mot = pdf_data['motility']
                if 'mot' in mot:
                    mot_report = generate_motility_report(mot)
                    context.update(mot_report)

            # Clean up temp images
            if 'images' in pdf_data:
                import shutil
                for path in pdf_data['images'].values():
                    if os.path.exists(os.path.dirname(path)):
                        shutil.rmtree(os.path.dirname(path), ignore_errors=True)
        else:
            # Process DOCX files as before
            doc = Document(doc_path)
            template, tipo = template_selector(doc_path)
            info_pac = extract_patient_info(doc)
            image = image_extractor(doc, template, tipo=tipo)
            context = None
        # Nombre de salida temporal
        safe_name = info_pac.get('Name', 'informe').replace('/', '_').replace('\\', '_')
        safe_date = info_pac.get('Exam_Date', 'fecha').replace('/', '_').replace('\\', '_')
        output_filename = f"{safe_name}_{tipo}_{safe_date}.docx"
        save_path = os.path.join(tmpdir, output_filename)

        # If context was already built (PDF case), skip the rest
        if context is None and tipo in ['card', 'stress']:
            measurements_table = get_measure_table(doc)
            if 'Gender' not in info_pac:
                print(f"[ERROR] info_pac keys: {list(info_pac.keys())}")
                raise HTTPException(status_code=422, detail=f"Falta el dato 'Gender' en el archivo {file.filename}. Datos extraídos: {info_pac}")
            measurements_dic = get_measurements(measurements_table, info_pac['Gender'])
            if tipo == 'stress':
                mot_table = get_mot_table(doc)
                mot = mot_extractor(mot_table)
                mot_report = generate_motility_report(mot)
                expand_dict_with_lists_inplace(measurements_dic)
                measurements_dic['E_e_rel'], measurements_dic['e_e_avg'] = calc_e_e_stress(measurements_dic)
                context = {**info_pac, **measurements_dic, 'image': image['image'], 'mot': mot['mot'], **mot_report}
            else:
                context = {**info_pac, **measurements_dic, 'image': image['image']}
        elif context is None:
            context = {**info_pac, 'image': image['image']}

        # Render template with context
        template.render(context)
        template.save(save_path)
        return save_path
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error processing file {file.filename}: {tb}")

        # Return user-friendly error message
        error_msg = "Error interno del servidor procesando el archivo"
        if "No se encontró LibreOffice" in str(e):
            error_msg = "Error de conversión de documento .doc"
        elif "Falta el dato 'Gender'" in str(e):
            error_msg = "Falta información requerida en el documento (Gender)"
        elif "No se encontró tabla" in str(e):
            error_msg = "Formato de documento no reconocido"

        raise HTTPException(
            status_code=500,
            detail={
                "error": error_msg,
                "filename": file.filename,
                "details": str(e)
            }
        )

@app.post("/generar_informe")
def generar_informe(file: UploadFile = File(...)):
    """
    Recibe un archivo Word o PDF del ecógrafo y devuelve el informe generado como descarga.
    Soporta archivos .docx, .doc y .pdf.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = procesar_archivo_individual(file, tmpdir)
        
        # Devolver el archivo generado como descarga
        generated_file = open(save_path, "rb")
        return StreamingResponse(
            generated_file,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(save_path)}"}
        )

@app.post("/generar_informes_multiples")
async def generar_informes_multiples(files: List[UploadFile] = File(...)):
    """
    Recibe múltiples archivos Word o PDF del ecógrafo y devuelve un archivo ZIP con todos los informes generados.
    Soporta archivos .docx, .doc y .pdf.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un archivo")
    
    if len(files) > 50:  # Límite de seguridad
        raise HTTPException(status_code=400, detail="Máximo 50 archivos por lote")

    with tempfile.TemporaryDirectory() as tmpdir:
        generated_files = []
        errors = []
        
        # Procesar cada archivo
        for file in files:
            try:
                print(f"[INFO] Procesando archivo: {file.filename}")
                save_path = procesar_archivo_individual(file, tmpdir)
                generated_files.append(save_path)
                print(f"[INFO] Archivo procesado exitosamente: {file.filename}")
            except Exception as e:
                error_msg = f"Error procesando {file.filename}: {str(e)}"
                print(f"[ERROR] {error_msg}")
                errors.append(error_msg)
        
        if not generated_files:
            raise HTTPException(
                status_code=500, 
                detail=f"No se pudo procesar ningún archivo. Errores: {'; '.join(errors)}"
            )
        
        # Crear archivo ZIP con todos los informes generados
        zip_filename = "informes_generados.zip"
        zip_path = os.path.join(tmpdir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in generated_files:
                filename = os.path.basename(file_path)
                zip_file.write(file_path, filename)
            
            # Si hay errores, agregar un archivo de log con los errores
            if errors:
                error_log = "\n".join([f"- {error}" for error in errors])
                error_content = f"Archivos procesados exitosamente: {len(generated_files)}\n"
                error_content += f"Archivos con errores: {len(errors)}\n\n"
                error_content += "Errores encontrados:\n" + error_log
                
                error_file_path = os.path.join(tmpdir, "errores.txt")
                with open(error_file_path, 'w', encoding='utf-8') as error_file:
                    error_file.write(error_content)
                zip_file.write(error_file_path, "errores.txt")
        
        print(f"[INFO] ZIP creado con {len(generated_files)} archivos procesados")
        
        # Devolver el archivo ZIP como descarga
        zip_file_obj = open(zip_path, "rb")
        return StreamingResponse(
            zip_file_obj,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
