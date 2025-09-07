#!/usr/bin/env python3
"""
Prueba la detección de tipo de template sin dependencias completas
"""

import os

def test_template_detection():
    """
    Simula la lógica de detección de template basada en el nombre del archivo
    """
    test_file = "/Users/mandarina/Lucho/App_eco_report/2_S1-6P_Lucho-Card.Report.V3_1.docx"
    
    print("🔍 PRUEBA DE DETECCIÓN DE TEMPLATE")
    print("=" * 50)
    
    filename = os.path.basename(test_file)
    print(f"Archivo: {filename}")
    
    # Simular la lógica de template_manager.py
    template_type = 'card'  # default
    template_file = "auto card.docx"
    
    if 'Carotid' in filename:
        template_type = 'carotid'
        template_file = "auto vc.docx"
        print("✅ Detectado: Estudio CAROTÍDEO")
    elif 'Arteries' in filename:
        template_type = 'art'
        template_file = "auto art.docx"
        print("✅ Detectado: Estudio ARTERIAL")
    elif 'Veins' in filename:
        template_type = 'ven'
        template_file = "auto ven.docx"
        print("✅ Detectado: Estudio VENOSO")
    elif 'Card' in filename:
        template_type = 'card'
        template_file = "auto card.docx"
        print("✅ Detectado: Estudio CARDÍACO (por nombre)")
    else:
        print("🔎 Se requiere análisis de contenido para determinar tipo")
        print("   - Si contiene tabla 'WMS' → Ecostrés")
        print("   - Por defecto → Cardíaco")
    
    print(f"\nTemplate seleccionado: {template_file}")
    print(f"Tipo de procesamiento: {template_type.upper()}")
    
    # Mostrar qué datos se extraerían
    print(f"\n📊 DATOS QUE SE EXTRAERÍAN:")
    print("• Información del paciente (tabla 1)")
    print("• Imágenes del estudio")
    
    if template_type in ['card', 'stress']:
        print("• Mediciones cardíacas")
        print("• Cálculos automáticos")
        print("• Interpretaciones médicas")
        
        if template_type == 'stress':
            print("• Análisis de motilidad segmentaria")
            print("• Comparación reposo vs esfuerzo")
    
    return template_type, template_file

if __name__ == "__main__":
    tipo, template = test_template_detection()
    
    print(f"\n✅ DETECCIÓN COMPLETADA")
    print(f"Tipo: {tipo}")
    print(f"Template: {template}")