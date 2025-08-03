import os
import shutil
import tempfile
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

# Permitir CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generar_informe")
def generar_informe(file: UploadFile = File(...)):
    """
    Recibe un archivo Word del ecógrafo y devuelve el informe generado como descarga.
    """
    if not (file.filename.lower().endswith(".docx") or file.filename.lower().endswith(".doc")):
        raise HTTPException(status_code=400, detail="El archivo debe ser .docx o .doc")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, file.filename)
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Si es .doc, convertir a .docx usando libreoffice (más robusto que python-docx para .doc)
        if input_path.lower().endswith('.doc'):
            import subprocess
            soffice_cmd = shutil.which('soffice')
            if not soffice_cmd:
                # Intentar ruta típica de Mac
                mac_path = '/Applications/LibreOffice.app/Contents/MacOS/soffice'
                if os.path.exists(mac_path):
                    soffice_cmd = mac_path
                else:
                    raise HTTPException(status_code=500, detail="No se encontró 'soffice' en el PATH ni en /Applications/LibreOffice.app/Contents/MacOS/soffice. Instala LibreOffice o agrega 'soffice' al PATH.")
            converted_path = input_path + 'x'
            try:
                print(f"[INFO] Intentando convertir .doc a .docx usando: {soffice_cmd}")
                print(f"[INFO] Comando: {soffice_cmd} --headless --convert-to docx --outdir {tmpdir} {input_path}")
                result = subprocess.run([
                    soffice_cmd, '--headless', '--convert-to', 'docx', '--outdir', tmpdir, input_path
                ], capture_output=True, text=True)
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
            template, tipo = template_selector(input_path)
            info_pac = extract_patient_info(doc)
            image = image_extractor(doc, template, tipo=tipo)
            # Nombre de salida temporal
            save_path = os.path.join(tmpdir, f"{info_pac.get('Name', 'informe')}_{tipo}_{info_pac.get('Exam_Date', 'fecha')}.docx")
            
            if tipo in ['card', 'stress']:
                measurements_table = get_measure_table(doc)
                if 'Gender' not in info_pac:
                    print(f"[ERROR] info_pac keys: {list(info_pac.keys())}")
                    raise HTTPException(status_code=422, detail=f"Falta el dato 'Gender' en el archivo. Datos extraídos: {info_pac}")
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
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[ERROR] {tb}")
            raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {str(e)}\nTraceback:\n{tb}")

        # Devolver el archivo generado como descarga
        # Devuelve el informe generado como descarga de forma segura para cloud/container
        file = open(save_path, "rb")
        return StreamingResponse(
            file,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(save_path)}"}
        )
