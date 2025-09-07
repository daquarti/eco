# 🌐 FRONTEND ECO - Instrucciones de Uso

## 🚀 **INICIO RÁPIDO**

### 1. **Iniciar el Servidor API**
```bash
# Navegar al directorio del proyecto
cd /Users/mandarina/Lucho/App_eco_report/eco

# Activar entorno virtual (si no está activo)
source venv/bin/activate

# Iniciar servidor FastAPI
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. **Abrir el Frontend**
```bash
# Abrir en navegador (desde el directorio eco)
open frontend.html
```

## 🎯 **FUNCIONALIDADES DEL FRONTEND**

### ✅ **Estado de la API**
- **Indicador visual** en la esquina superior derecha
- 🟢 **Verde**: API conectada y funcionando
- 🔴 **Rojo**: API desconectada o con problemas
- **Auto-verificación** cada 10 segundos

### 📄 **Procesamiento Individual**
1. Click en pestaña **"📄 Archivo Individual"**
2. **Seleccionar archivo** .docx o .doc del equipo ecocardiográfico
3. Verificar que aparezca el nombre y tamaño del archivo
4. Click en **"🚀 Generar Informe"**
5. **Esperar** la barra de progreso
6. **Descargar** el informe generado automáticamente

### 📦 **Procesamiento Múltiple**
1. Click en pestaña **"📦 Múltiples Archivos"**
2. **Seleccionar múltiples archivos** (hasta 50 archivos)
3. Verificar lista de archivos seleccionados
4. Click en **"🚀 Generar Informes (ZIP)"**
5. **Esperar** el procesamiento de todos los archivos
6. **Descargar** el archivo ZIP con todos los informes

## 🔧 **CARACTERÍSTICAS TÉCNICAS**

### **Interfaz**
- ✅ **Responsive**: Funciona en desktop y móvil
- ✅ **Moderna**: Diseño con gradientes y animaciones
- ✅ **Intuitiva**: Dos pestañas claras para cada modo
- ✅ **Feedback visual**: Barras de progreso y estados

### **Validaciones**
- ✅ **Tipos de archivo**: Solo .docx y .doc
- ✅ **Límite de archivos**: Máximo 50 archivos en modo lote
- ✅ **Tamaño de archivos**: Muestra tamaño en MB
- ✅ **Estado de conexión**: Verifica API automáticamente

### **Experiencia de Usuario**
- ✅ **Drag & Drop**: Arrastrar archivos funciona
- ✅ **Progreso visual**: Barras de progreso animadas
- ✅ **Descarga automática**: Links de descarga directa
- ✅ **Manejo de errores**: Mensajes de error claros

## 📱 **COMPATIBILIDAD**

### **Navegadores Soportados**
- ✅ Chrome/Chromium (Recomendado)
- ✅ Firefox
- ✅ Safari
- ✅ Edge

### **Dispositivos**
- ✅ **Desktop**: Experiencia completa
- ✅ **Tablet**: Adaptado para pantalla táctil
- ✅ **Móvil**: Versión optimizada

## 🐛 **SOLUCIÓN DE PROBLEMAS**

### **API Desconectada (🔴)**
```bash
# Verificar que el servidor esté corriendo
curl http://localhost:8001/

# Si no responde, reiniciar servidor
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### **Error de CORS**
- El servidor ya tiene CORS habilitado para todos los orígenes
- Si persiste, verificar que la URL en JavaScript sea correcta: `http://localhost:8001`

### **Archivos no se procesan**
1. Verificar que sean archivos .docx o .doc válidos
2. Verificar que los archivos no estén corruptos
3. Revisar logs del servidor en la consola donde corre uvicorn

### **Descarga no funciona**
- Verificar que el navegador permita descargas
- Algunos navegadores bloquean descargas automáticas

## 📊 **MONITOREO**

### **Logs del Servidor**
```bash
# Ver logs en tiempo real donde corre uvicorn
# Muestra cada petición y su estado
INFO: 127.0.0.1:60627 - "POST /generar_informe HTTP/1.1" 200 OK
```

### **Consola del Navegador**
```bash
# Abrir Developer Tools (F12)
# Ver errores JavaScript en la pestaña Console
```

## 🎉 **¡LISTO PARA USAR!**

El frontend está completamente funcional y conectado a la API. 

**URLs importantes:**
- **Frontend**: `file:///path/to/frontend.html`
- **API**: `http://localhost:8001`
- **Documentación API**: `http://localhost:8001/docs`

---
*Frontend creado con ❤️ para el sistema ECO de generación de informes médicos*