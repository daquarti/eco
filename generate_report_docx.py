from main import app
from fastapi.testclient import TestClient
import tempfile

test_file = '/Users/mandarina/Downloads/13_S1-6P_card2.Report.V3.docx'
client = TestClient(app)

with open(test_file, 'rb') as f:
    response = client.post(
        '/generar_informe',
        files={'file': ('13_S1-6P_card2.Report.V3.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    )
    assert response.status_code == 200, response.text
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False, dir='.') as tmp:
        tmp.write(response.content)
        print('DOCX generado:', tmp.name)
