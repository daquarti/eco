# Utiliza una imagen oficial de Python 3.10
FROM python:3.10-slim

# Actualizar paquetes e instalar LibreOffice para conversión .doc a .docx
RUN apt-get update && apt-get install -y \
    libreoffice \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de dependencias primero para aprovechar cache de Docker
COPY requirements.txt ./

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Expone el puerto que usará Uvicorn (por defecto 8000)
EXPOSE 8000

# Comando por defecto para iniciar la app (ajusta si tu entrypoint cambia)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
