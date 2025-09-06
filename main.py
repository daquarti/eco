import os
import shutil
import tempfile
import zipfile
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from docx import Document
from docxtpl import DocxTemplate

from template_manager import template_selector
from patient_data_extraction import extract_patient_info, image_extractor, generate_motility_report, get_measure_table, get_measurements, get_mot_table, mot_extractor
from aux_calculations import expand_dict_with_lists_inplace, calc_e_e_stress

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API eco3 está activa"}

# Permitir CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def procesar_archivo_individual(file: UploadFile, tmpdir: str) -> str:
    """
    Procesa un archivo individual y devuelve la ruta del archivo generado.
    """
    if not (file.filename.lower().endswith(".docx") or file.filename.lower().endswith(".doc")):
        raise HTTPException(status_code=400, detail=f"El archivo {file.filename} debe ser .docx o .doc")

    input_path = os.path.join(tmpdir, file.filename)
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Si es .doc, convertir a .docx usando libreoffice (más robusto que python-docx para .doc)
    if input_path.lower().endswith('.doc'):
        import subprocess
        soffice_cmd = shutil.which('soffice')
        if not soffice_cmd:
            # Intentar rutas típicas según el sistema operativo
            possible_paths = [
                '/Applications/LibreOffice.app/Contents/MacOS/soffice',  # macOS
                '/usr/bin/soffice',  # Linux (Docker/Render)
                '/usr/local/bin/soffice',  # Linux alternativo
                'C:\\Program Files\\LibreOffice\\program\\soffice.exe'  # Windows
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    soffice_cmd = path
                    break
            
            if not soffice_cmd:
                raise HTTPException(status_code=500, detail="LibreOffice no encontrado. Instala LibreOffice para procesar archivos .doc")
        converted_path = input_path + 'x'
        try:
            print(f"[INFO] Intentando convertir .doc a .docx usando: {soffice_cmd}")
            print(f"[INFO] Comando: {soffice_cmd} --headless --convert-to docx --outdir {tmpdir} {input_path}")
            # Use better LibreOffice parameters for preserving table structure
            result = subprocess.run([
                soffice_cmd, 
                '--headless', 
                '--convert-to', 'docx:"Office Open XML Text"',
                '--outdir', tmpdir, 
                '--infilter=MS Word 97/2000/XP/2003',
                input_path
            ], capture_output=True, text=True, timeout=60)
            print(f"[INFO] stdout: {result.stdout}")
            print(f"[INFO] stderr: {result.stderr}")
            # Listar archivos en tmpdir tras conversión
            print(f"[INFO] Archivos en {tmpdir} tras conversión: {os.listdir(tmpdir)}")
            # Buscar cualquier archivo .docx en el tmpdir
            docx_files = [f for f in os.listdir(tmpdir) if f.lower().endswith('.docx')]
            print(f"[INFO] Archivos .docx encontrados en {tmpdir}: {docx_files}")
            if not docx_files:
                print(f"[ERROR] No se encontró ningún archivo .docx convertido. Archivos en tmpdir: {os.listdir(tmpdir)}")
                raise Exception('No se pudo convertir el archivo .doc a .docx')
            converted_path = os.path.join(tmpdir, docx_files[0])
            print(f"[INFO] Usando archivo convertido: {converted_path}")
            # Chequeo de existencia y tamaño
            if not os.path.exists(converted_path):
                print(f"[ERROR] El archivo convertido no existe. Archivos en tmpdir: {os.listdir(tmpdir)}")
                raise Exception('El archivo .docx convertido no existe')
            size = os.path.getsize(converted_path)
            print(f"[INFO] Tamaño del archivo convertido: {size} bytes")
            if size == 0:
                print(f"[ERROR] El archivo convertido está vacío. Archivos en tmpdir: {os.listdir(tmpdir)}")
                raise Exception('El archivo .docx convertido está vacío')
            doc_path = converted_path
        except Exception as e:
            print(f"[ERROR] Error en la conversión: {e}")
            raise HTTPException(status_code=500, detail=f"Error convirtiendo archivo .doc a .docx: {str(e)}")
    else:
        doc_path = input_path

    try:
        doc = Document(doc_path)
        template, tipo = template_selector(doc_path)
        info_pac = extract_patient_info(doc)
        image = image_extractor(doc, template, tipo=tipo)
        # Nombre de salida temporal
        safe_name = info_pac.get('Name', 'informe').replace('/', '_').replace('\\', '_')
        safe_date = info_pac.get('Exam_Date', 'fecha').replace('/', '_').replace('\\', '_')
        output_filename = f"{safe_name}_{tipo}_{safe_date}.docx"
        save_path = os.path.join(tmpdir, output_filename)
        
        if tipo in ['card', 'stress']:
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
        else:
            context = {**info_pac, 'image': image['image']}
        template.render(context)
        template.save(save_path)
        return save_path
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] {tb}")
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo {file.filename}: {str(e)}\nTraceback:\n{tb}")

@app.post("/generar_informe")
def generar_informe(file: UploadFile = File(...)):
    """
    Recibe un archivo Word del ecógrafo y devuelve el informe generado como descarga.
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
def generar_informes_multiples(files: List[UploadFile] = File(...)):
    """
    Recibe múltiples archivos Word del ecógrafo y devuelve un archivo ZIP con todos los informes generados.
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
