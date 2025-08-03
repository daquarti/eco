

from docxtpl import DocxTemplate, InlineImage
from docx.shared import Cm
import csv
from PIL import Image
from io import BytesIO
from aux_calculations import convert_to_int,conv_vel_a_m,text_mass_hypertrophy,text_diam_LV,text_atrium,remove_signs


#extraer los datos de las tablas
def extract_patient_info(doc)->dict:
    '''
    Accepts word docx and extracts info from the first table where the patient data resides
    returns a dictionary
    '''
    data = {}
    #itero sobre las tablas del documento
    for index_table,table in enumerate(doc.tables):
        #tabla 1 es la que contiene estos datos
        if index_table==1:
            for row_index, row in enumerate(table.rows):
                if row_index>0:
                    for cell in row.cells:
                        # Solo procesar si la celda contiene ':'
                        if ':' in cell.text:
                            key = cell.text.split(':')[0].strip().replace(' ', '_')
                            try:
                                value = cell.text.split(':', 1)[1].strip().replace('  ', ' ')
                            except IndexError:
                                value = ''
                            if key.lower() not in data:
                                data[key] = value
    return data



def update_dictionary(dic:dict)->dict:
    '''
    takes a dictionary and searches calculations within the values to turn them into new keys
    '''
    calc_list=['*Dimensionless Index','*Flow Rate AS','CSA(LVOT)','SV(LVOT)','CSA(AV SV)','Reg Vol(PISA TR)',
               'EROA(PISA TR)','Flow Rate(PISA TR)','Reg Vol(PISA MR)','EROA(PISA MR)','Flow Rate(PISA MR)',
               'AVA(VTI)','RWT(2D)','LVd Mass(2D-ASE)','MV E/A Ratio',"Average E'","E/Med E'",'LVIDd Index(2D)',
                '%LVPW(2D)','LVESV(A4C Simp)','EF(A4C Simp)',"E/Lat E'","E/Avg E'",'*Aortic Sinus Indexed',
               'LVEDVI(A4C Simp)','LA ESVI(BP A-L)','AVAI(AVA VTI)','SI(LVOT)','%IVS(2D)'
              ]
    updates={}
    for val in dic.values():
        for c in calc_list:
            if c in val:
                key=val[val.index(c)]
                value=val[val.index(c)+1]
                updates[key]=value
    dic.update(updates)
    return dic

def dic_cleaning(data)->dict:
    '''
    gets a dict. All the values are set to string, if there are more than one value gets the first.
    if there are keys within a value list it removes that and the following number that is the value of that key
    '''

    for key, value in data.items():
        if len(value) < 2:
            value = value[0]
            data[key]=value
        if isinstance(value,list):
            key_in_value=[v for v in value if v in data.keys()]#get the key
            if key_in_value:
                index=value.index(key_in_value[0])#get the index
                data[key]=value[:index][0]#get the values uptothe index
    return data

def get_measure_table(doc)->'table':
    '''
    Accepts word docx and extracts the table object where the measurements are
    '''
    #itero sobre las tablas del documento
    for index_table,table in enumerate(doc.tables):
        for row_index, row in enumerate(table.rows):
            for index_cell,cell in enumerate(row.cells):
                if cell.text=='Measure':
                    return table

def get_mot_table(doc)->'table':
    for index_table,table in enumerate(doc.tables):
        for row_index, row in enumerate(table.rows):
            for index_cell,cell in enumerate(row.cells):
                if cell.text=='WMS':
                    return table

def mot_extractor(table)->dict:

    '''
    Extrae las puntaciones y los nombres de los segmentos en los score de motilidad del ecostress
    '''

    mot={}
    for index_r, row in enumerate(table.rows):
        for cell in row.cells:
             for inner_table in cell.tables:
                    for index_r,inner_row in enumerate(inner_table.rows):
                       #la fila 1 contiene la primera info,la ultima info en la 17 (apex) 
                        if 1 <= index_r <= 17:
                            key = None
                            values = []
                            for index_c, inner_cell in enumerate(inner_row.cells):
                                #las primeras cuatro celdas son segment ID
                                #la 5 celda es el nombre del segmento
                                #la 6 es baseline, 7 peak, 8 recovery 
                                if index_c == 5:
                                    key = inner_cell.text.lower()
                                if 5 < index_c <= 8 and key:
                                    values.append(int(inner_cell.text))

                            if key and values:  # Store the key-value pair only if both key and values exist
                                mot[key] = values
                                mot_conv = {'mot': [{'key': k, 'motilidad': v} for k, v in mot.items()]}                

    return mot_conv 

def get_measurements(table,gender):
    data={}
    units=['mm','cm','ml','g','ms','mmHg','cm²','cm/s','ml/s','cm²','m²','ml/m²','cm²/m²','g/m²']
    for row_index, row in enumerate(table.rows):
        for index_cell,cell in enumerate(row.cells):
            for st in cell.tables:
                for index_rs,rs in enumerate(st.rows):
                    if index_rs>1:
                        elements=[]
                        values=[]
                        for index_cs,cs in enumerate(rs.cells):
                            if index_cs==0:
                                text=cs.text.replace(' ','',2)
                                if not text.startswith(' '):
                                    key=text
                                    subkey=''
                                    elements.append(key)
                                else:
                                    subkey=text
                                    elements.append(subkey.strip())   
                            if (cs.text.strip() 
                                not in elements 
                                and (cs.text.strip()!='') 
                                and not (cs.text.endswith('Last'))
                                and cs.text.strip() not in units
                               ):
                                value=cs.text.strip()
                                values.append(value)
                                data[key+subkey]=values
    data=update_dictionary(data) 
    data=dic_cleaning(data)
    data=convert_to_int(data)
    data=conv_vel_a_m(data)
    data['Gender']=gender
    data=text_mass_hypertrophy(data)
    data=text_diam_LV(data)
    data=text_atrium(data)
    data=remove_signs(data) #tiene que ir ultimo porque las funciones de interpretaci'on usan el dict como se ve en el word del equpo.
    return data




def image_extractor(doc, template, tipo, image_width=Cm(8), image_height=Cm(5.36)) -> dict:
    '''
    Extrae las imágenes del reporte docx del dispositivo Vinno y devuelve un diccionario con objetos InlineImage.
    Requiere:
        - doc: Documento a extraer
        - template: Template donde se renderizarán las imágenes
        - tipo: Tipo de template (por ejemplo, 'stress')
    Se establecen medidas habituales de 5.36x8 cm, excepto para el mapa polar del stress que es 8.22 x 16.23 y 6.39 x 16.23 cm.
    '''
    image_dict = {}

    # Extraer imágenes
    for rel in doc.part.rels:
        rel_obj = doc.part.rels[rel]
        if 'image' in rel_obj.reltype:
            image_data = rel_obj.target_part.blob
            image = Image.open(BytesIO(image_data))
            compressed_image = BytesIO()

            # Extraer el número de imagen
            target = rel_obj.target_ref.split('.')[0].replace(r'media/', '')
            image_number = int(target.replace('image', ''))

            # Si es 'stress' y la imagen es 1 o 2, se manejan de manera diferente
            if tipo == 'stress' and image_number in [1, 2]:
                compressed_image = BytesIO(image_data)  # Mantener PNG sin convertir
                compressed_image.seek(0)
                # Definir tamaños específicos para las primeras dos imágenes
                if image_number == 1:
                    image_dict[target] = InlineImage(template,
                                                     compressed_image,
                                                     width=Cm(16.23), height=Cm(8.22))
                else:
                    image_dict[target] = InlineImage(template,
                                                     compressed_image,
                                                     width=Cm(16.23), height=Cm(6.39))
            else:
                # Si no es 'stress' o es una imagen normal, convertir a JPEG si es necesario
                if image.format != 'JPEG':
                    image = image.convert("RGB")  # Convertir a RGB para JPEG
                image.save(compressed_image, format='JPEG', quality=85)  # Guardar como JPEG
                compressed_image.seek(0)

                # Asignar tamaño predeterminado
                image_dict[target] = InlineImage(template,
                                                 compressed_image,
                                                 width=image_width,
                                                 height=image_height)

    # Ordenar las imágenes por su número
    key = sorted(image_dict.keys(), key=lambda image_name: int(image_name.replace('image', '')))
    image_dict = {i: image_dict[i] for i in key}
    image_dict = {'image': [{'key': k, 'image': v} for k, v in image_dict.items()]}

    return image_dict


#####

def mot_grouper(dic,idx): 
    group={
    'Normoquinesia':[],
    'Hipoquinesia':[],
    'Aquinesia':[],
    'Disquinesia':[],
    'Aneurismático':[],
    }        
    for dic in dic['mot']:
        if dic['motilidad'][idx]==2:
            group['Hipoquinesia'].append(dic['key'])
        elif dic['motilidad'][idx]==3:
            group['Aquinesia'].append(dic['key'])    
        elif dic['motilidad'][idx]==4:
            group['Disquinesia'].append(dic['key'])  
        elif dic['motilidad'][idx]==5:
            group['Aneurismático'].append(dic['key'])
        else:
            group['Normoquinesia'].append(dic['key'])

    return group

def mot_interpreter(dic:dict)->dict:
    """
    groups myocardial segments by motility

    """
    segments_group={}
    segments_group['reposo']=mot_grouper(dic,0)
    segments_group['esfuerzo']=mot_grouper(dic,1)
    return segments_group


def delta_motility(dic: dict)-> dict:

    improve=[]
    ischaemic=[]
    unchanged=[]
    for i in dic['mot']:
        segment=i['key']
        score_rep=i['motilidad'][0]
        score_stress=i['motilidad'][1]
        delta=score_rep-score_stress
        if delta <0:
            ischaemic.append(segment)
        elif delta >0:
            improve.append(segment)
        else: unchanged.append(segment)
    delta_mot={'improve':improve,
              'ischaemic':ischaemic,
              'unchanged':unchanged}
    return delta_mot






# In[ ]:


def generate_motility_report(mot):
    """
    Generates a motility report based on mot.

    Args:
        mot: dict returned by the mot extractor

    Returns:
        str: The generated motility report.
    """

    reposo = []
    esfuerzo=[]
    mejoria=[]
    mot_interpret=mot_interpreter(mot)
    delta_mot=delta_motility(mot)

    #group motility during reposo
    if len(mot_interpret['reposo'].get("Normoquinesia", [])) != 17:
        for key, segments in mot_interpret['reposo'].items():
            if key != "Normoquinesia":
                new_segments = [segment for segment in segments]
                if new_segments:
                    segments_str = ", ".join(new_segments)
                    reposo.append(f"{key}: {segments_str}.")

    else: reposo.append('Sin trastornos de la motilidad basal.')

    # Group new conditions in esfuerzo compared to reposo
    for key, segments in mot_interpret['esfuerzo'].items():
        if key != "Normoquinesia":
            new_segments = [segment for segment in segments if segment not in mot_interpret['reposo'].get(key, [])]
            if new_segments:
                segments_str = ", ".join(new_segments)
                esfuerzo.append(f"Nueva {key}: {segments_str}.")

#     # Handle segments with delta < 0 (ischaemic)
#     if delta_mot.get("ischaemic"):
#         segments = ", ".join(delta_mot["ischaemic"])
#         report.append(f"Nueva isquemia de los segmentos: {segments}.")

    # Handle segments with delta > 0 (improve)
    if delta_mot.get("improve"):
        segments = ", ".join(delta_mot["improve"])
        mejoria.append(f"Mejoria de los segmentos: {segments}.")

    # Handle unchanged segments
    unchanged = delta_mot.get("unchanged", [])
    if len(unchanged) == 17 and len(mot_interpret['reposo'].get("Normoquinesia", [])) == 17:
        esfuerzo.append("Hipercontractilidad de todos los segmentos.")
    elif len(unchanged) == 17 and len(mot_interpret['reposo'].get("Normoquinesia", [])) != 17:
        esfuerzo.append("Sin nuevos trastornos de motilidad.")
    reposo=' '.join(reposo)
    esfuerzo=' '.join(esfuerzo)
    mejoria=' '.join(mejoria)

    report={'reposo':reposo,
           'esfuerzo':esfuerzo,
           'mejoria':mejoria}

    return report



