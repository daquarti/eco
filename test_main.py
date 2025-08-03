import os
import tempfile
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_generar_informe_ok():
    # Usa un archivo de ejemplo real que esté en la carpeta (auto card.docx)
    # Usar un archivo real extraído del .rar
    test_file = "/Users/mandarina/Downloads/13_S1-6P_card2.Report.V3.docx"
    assert os.path.exists(test_file), f"El archivo de prueba {test_file} no existe."
    with open(test_file, "rb") as f:
        response = client.post(
            "/generar_informe",
            files={"file": (os.path.basename(test_file), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert len(response.content) > 10000
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(response.content)
        print(f"Informe generado guardado temporalmente en: {tmp.name}")

def test_generar_informe_archivo_invalido():
    # Prueba con un archivo que no es docx
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        tmp.write(b"texto de prueba")
        tmp.flush()
        with open(tmp.name, "rb") as f:
            response = client.post(
                "/generar_informe",
                files={"file": ("prueba.txt", f, "text/plain")}
            )
    assert response.status_code == 400
    assert "El archivo debe ser .docx" in response.text

def test_generar_informe_docx_corrupto():
    # Prueba con un archivo docx corrupto
    with tempfile.NamedTemporaryFile(suffix=".docx") as tmp:
        tmp.write(b"no es un docx real")
        tmp.flush()
        with open(tmp.name, "rb") as f:
            response = client.post(
                "/generar_informe",
                files={"file": ("corrupto.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
    assert response.status_code == 500
    assert "Error procesando el archivo" in response.text
