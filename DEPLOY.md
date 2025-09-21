# Deployment Guide - EcoReport API

## Deployment Ready Features

✅ **FastAPI Backend**: Versión 2.0.0 con endpoints optimizados
✅ **PDF + Word Processing**: Soporte completo para .docx, .doc y .pdf
✅ **Gemini LLM Integration**: Extracción inteligente con fallback automático
✅ **Docker Optimized**: Multi-stage build y health checks
✅ **Production Logging**: Logging estructurado y manejo de errores
✅ **CORS Configured**: Configurado para frontend integration
✅ **Health Monitoring**: Endpoints /health e /info para monitoring

## Quick Deploy to Render

1. **Connect Repository**: Conecta este repo en Render.com
2. **Set Environment Variables**:
   ```
   GOOGLE_API_KEY=your_gemini_api_key_here
   ENVIRONMENT=production
   ```
3. **Deploy**: Render usará automáticamente `render.yaml` configuration

## API Endpoints for Frontend

### Core Endpoints
- `POST /generar_informe` - Single file processing (.docx/.doc/.pdf)
- `POST /generar_informes_multiples` - Batch processing (up to 50 files)

### Monitoring
- `GET /health` - Health check (for load balancers)
- `GET /info` - API information and capabilities
- `GET /` - Basic status

### Development
- `POST /debug_files` - Debug file information

## Frontend Integration Examples

### Single File Upload
```javascript
const formData = new FormData();
formData.append('file', selectedFile);

const response = await fetch('https://your-api.onrender.com/generar_informe', {
  method: 'POST',
  body: formData
});

if (response.ok) {
  const blob = await response.blob();
  // Download generated report
} else {
  const error = await response.json();
  console.error('Error:', error);
}
```

### Batch Upload
```javascript
const formData = new FormData();
files.forEach(file => formData.append('files', file));

const response = await fetch('https://your-api.onrender.com/generar_informes_multiples', {
  method: 'POST',
  body: formData
});

// Returns ZIP file with all generated reports
```

### Health Check
```javascript
const health = await fetch('https://your-api.onrender.com/health')
  .then(r => r.json());

console.log('PDF Processing:', health.services.pdf_processing);
console.log('Gemini LLM:', health.services.gemini_llm);
```

## Performance Considerations

- **File Size Limit**: 50MB per file
- **Batch Limit**: 50 files maximum
- **Processing Time**: PDF with Gemini ~5-10 seconds, Word files ~2-3 seconds
- **Memory Usage**: Optimized for Render free tier

## Error Handling

All endpoints return structured error responses:
```json
{
  "error": "User-friendly error message",
  "filename": "problematic_file.pdf",
  "details": "Technical details"
}
```

## Security Features

- File type validation (.docx, .doc, .pdf only)
- File size limits
- Filename sanitization
- Non-root Docker user
- CORS configured for specific domains in production

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY

# Run development server
uvicorn main:app --reload

# Test endpoints
curl http://localhost:8000/health
```

## Docker Build

```bash
# Build image
docker build -t eco-api .

# Run container
docker run -p 8000:8000 -e GOOGLE_API_KEY=your_key eco-api

# Health check
curl http://localhost:8000/health
```