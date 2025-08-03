#!/usr/bin/env python
# coding: utf-8

# In[1]:


def is_float(s:str)->bool:
    try:
        float(s)
        return True
    except ValueError:
        return False 

def expand_dict_with_lists_inplace(input_dict: dict)->None:
    '''
    Accepts dictionary with values that are lists and expand them to form a key: value pair for each value on the list
    removes de key:list from the dict

    '''
    # Collect new key-value pairs
    new_items = {}

    # Loop through the original dictionary keys
    keys_to_remove = []  # To track which keys need to be removed

    for key, value in input_dict.items():
        # Check if the value is a list
        if isinstance(value, list):
            # Add the items in the list as new key-value pairs
            for index, item in enumerate(value):
                new_key = f"{key}_{index}"
                new_items[new_key] = item
            # Mark the original key for removal
            keys_to_remove.append(key)

    # Remove the original list-type keys
    for key in keys_to_remove:
        del input_dict[key]

    # Update the original dictionary with the new items
    input_dict.update(new_items)

def calc_e_e_stress(dic: dict)-> 'rel E/e avg rep and stress':
    mv_e_0=(dic.get('MV_Vel_E_0',0))*100
    mv_e_1=(dic.get('MV_Vel_E_1',0))*100
    med_e_0=dic.get('Med_Vel_E_0',0)
    med_e_1=dic.get('Med_Vel_E_1',0)
    lat_e_0=dic.get('Lat_Vel_E_0',0)
    lat_e_1=dic.get('Lat_Vel_E_1',0)
    e_avg_0=int((med_e_0+lat_e_0)/2) if lat_e_0!= 0 else med_e_0
    e_avg_1=int((med_e_1+lat_e_1)/2) if lat_e_1!= 0 else med_e_1
    try:
        e_e_0=int(mv_e_0/e_avg_0)
        e_e_1=int(mv_e_1/e_avg_1)
    except ZeroDivisionError as e:
        print(f'{e}')
        if e_avg_0==0:
            e_e_0='XX'
        if e_avg_1==0:
            e_e_1='XX'
    return (e_e_0,e_e_1),(e_avg_0,e_avg_1)

def remove_signs(dic:dict)-> dict:
    '''
    accepts a dictionary and returns a dictionary without signs
    '''
    dic_without_signs={key.replace('  ',' ').replace(' ', '_').replace('/','_').replace('(','_').replace(')','').
                    replace('-','_').replace('%','').replace("'",'').replace('*',''): value 
                    for key, value in dic.items()
                   }
    return dic_without_signs

def convert_to_int(dic):
    '''
    accepts a dictionary and converts stings to floats, if they are on the key_to_round list,
    they are rounded and transformed to int

    key_to_round=['LVIDd','LVIDs','IVSd','%FS(2D)','LVd Mass Index(2D-ASE)',
                  'Ao Sinusus','Ao Diam','RAAd','RVAWd','LVPWd','LAVI',
                  "E/Avg E'",'EF(A4C Simp)','AR PHT','LAAd','LA ESVI(BP A-L)','Bi-plane LA A-L  LAVI',
                 'AV Vmax','AV Vmax  PG','LVOT Vmax', 'LVOT Vmax  PG','LVOT Trace  Peak PG','RVSP  TR Vmax',
                 'RVSP    PG','AV Trace  Vmax','AV Trace  Peak PG']
    '''
    key_to_round=['LVIDd','LVIDs','IVSd','%FS(2D)','LVd Mass Index(2D-ASE)',
                  'Ao Sinusus','Ao Diam','RAAd','RVAWd','LVPWd','LAVI',
                  "E/Avg E'",'EF(A4C Simp)','AR PHT','LAAd','LA ESVI(BP A-L)','Bi-plane LA A-L  LAVI',
                 'AV Vmax','AV Vmax  PG','LVOT Vmax', 'LVOT Vmax  PG','LVOT Trace  Peak PG','RVSP  TR Vmax',
                 'RVSP    PG','AV Trace  Vmax','AV Trace  Peak PG','TR Vmax  PG']
    for val in dic.keys():
        if 'Exam_Date' not in val:
            if isinstance(dic.get(val),list):
                valores=[]
                for i in dic.get(val):
                    if is_float(i):
                        valor=float(i.replace('-',''))
                        if val in key_to_round:
                            valor=int(round(valor,0))
                        valores.append(valor)
                dic[val]=valores
            else:
                value = dic.get(val)
                if isinstance(value, str) and is_float(value):
                    valor=float(value.replace('-', '')) 
                    if val in key_to_round:
                        dic[val]=int(round(valor,0))
                    else:          
                        dic[val] =valor

    return dic

def conv_vel_a_m(dic)-> dict:

    '''
    accepts dictionary checks for speed in cm/seg and converts to m/seg.
    Returns the same dict.
    '''
    lista=['RVOT Vmax','AV Vmax','LVOT Vmax','TR Vmax','MV Vel E','MV Vel A','Vmax',
           'AV Trace  Vmax','LVOT Trace  Vmax','RVSP  TR Vmax'
          ]
    for key in dic.keys():
        if key in lista:
            if isinstance(dic.get(key),list):
                vel=[]
                for i in dic.get(key):
                    vel.append(round(i/100,2))
                dic[key]=vel
            else:
                dic[key]=round(dic.get(key)/100,2)
    return dic



# In[2]:


def text_mass_hypertrophy(dic:dict)->dict:
    '''
    Accepts mesuarament dict, searches the following keys:
    LVd Mass Index(2D-ASE)
    LVd Mass(2D-ASE)
    Gender
    RWT(2D)
    returns updated dict with "mass_interpretation" key.
    '''
    mass_index=dic.get('LVd Mass Index(2D-ASE)','')
    # set mass to '' if index present, to use it mass_index as defaul
    mass=dic.get('LVd Mass(2D-ASE)','') if mass_index=='' else ''
    gender=dic.get('Gender','')
    rwt=dic.get('RWT(2D)','')
    text_mass='Índice de masa dentro del parámetros de la normalidad' if mass_index!='' else 'Masa dentro de parámetros de la normalidad'
    text_rwt='' if rwt!='' and float(rwt) <0.42 else ', remodelado concéntrico'
    #interpret mass or mass index according to gender
    if gender != '' and gender=='Male':
        if (mass_index != '' and mass_index>=115
            or
            mass != '' and mass>= 200
           ):
            text_mass='Hipertrofia'       
    #female if not male
    else:
        if (mass_index != ''and mass_index>=95
            or
            mass != '' and mass>=150
           ):
            text_mass='Hipertrofia'
    if text_mass=='Hipertrofia':
        if rwt != '' and rwt>=0.42:
            text_rwt=' concéntrica'
        else: text_rwt=' excéntrica'
    #create new key
    dic['mass_interpretation']=text_mass+text_rwt
    dic['mass_conc']=mass_conc(text_mass, text_rwt)
    #return dict uptadted
    return dic
def mass_conc(text_mass, text_rwt):
    conc=text_rwt
    if text_mass !='Índice de masa dentro del parámetros de la normalidad':
        conc=text_mass+text_rwt
    return conc



# In[3]:

# In[4]:


def mass_conc(text_mass, text_rwt):
    conc=text_rwt
    if text_mass !='Índice de masa dentro del parámetros de la normalidad':
        conc=text_mass+text_rwt
    return conc
text_mass='a '
text_rwt=''
mass_conc(text_mass, text_rwt)


# In[5]:


def assign_max_if_list(*args):
    updated_vars = []
    for var in args:
        if isinstance(var, list):
            updated_vars.append(max(var))
        else:
            updated_vars.append(var)
    return updated_vars


def text_diam_LV(dic:dict)->str:
    '''
    accepts dict with "LVIDd","IVSd","LVPWd","Gender"
    returns updated dict with key "diam_lv_interpretation"
    abnormal IVSd >12 or LVPWd >9
    Male: 42< LIVDd > 58
    Female: 38< LIVDd > 54
    '''
    lvidd=dic.get('LVIDd','')
    ivsd=dic.get('IVSd','')
    lvpwd=dic.get('LVPWd','')
    gender=dic.get('Gender','')
    lvidd,ivsd,lvpwd=assign_max_if_list(lvidd,ivsd,lvpwd)
    text_lvidd='Dimensiones y '
    text_thick='espesores conservados'
    if all([lvidd!='',ivsd!='',lvpwd!='']):
        #interpret thickness
        if float(ivsd)>12 or float(lvpwd)>9:
            text_thick='espesores aumentados'
            text_lvidd='Dimensiones conservadas y '

        #interpret diam according to gender
        if gender != '' and gender=='Male':
            if lvidd !='' and float(lvidd)>58:
                text_lvidd='Dimensiones aumentadas, '
            elif lvidd !='' and float(lvidd)<42:
                text_lvidd='Dimensiones disminuidas, '
        else:
            if lvidd !='' and float(lvidd)>54:
                text_lvidd='Dimensiones aumentadas, '
            elif lvidd !='' and float(lvidd)<38:
                text_lvidd='Dimensiones disminuidas, '
        dic['diam_lv_interpretation']=text_lvidd+text_thick
    return dic
#los valores su numeros a esta altura, asi que puedo sacar float


# In[6]:


def text_atrium(dic:dict)-> str:
    '''
    accepts dict with measurements. Searches key "LA ESVI(BP A-L)",
    "LAAd","Bi-plane LA A-L  LAVI", "RAAd"
    '''
    #check if volume is in LA ESVI, if not gets LAVI. IF neither ''
    lav=dic.get('Bi-plane LA A-L  LAVI','') if dic.get('LA ESVI(BP A-L)','')=='' else dic.get('LA ESVI(BP A-L)','')
    #prioritizes volume before diameter, it only assigns a value if LAV is ''
    lad=dic.get('LAAd','') if lav=='' else ''
    rad=dic.get('RAAd','')
    la_text='Diámetros conservados'
    ra_text='Diámetros conservados'
    #if list of values select the max
    if isinstance(lav,list):
        lav=max(lav)
    if isinstance(lad,list):
        lad=max(lad)
    if isinstance(rad,list):
        rad=max(rad)
    # if no measurements of atriums returns dic with normal values
    if lad=='' and lav=='':
        dic['la_text']=la_text
        dic['ra_text']=ra_text
        return dic

    #check if diameter is '', then procedes to asses volumen
    if lad =='':
        if 34<=lav<44:
            la_text='Levemente dilatada'
        elif 44<=lav<54:
            la_text='Moderadamente dilatada'
        elif 54<=lav:
            la_text='Severamente dilatada'
    #if lad as a value in it, it means that there is no volume
    else:
        if 21<=lad<31:
            la_text='Levemente dilatada'
        elif 31<=lad<41:
            la_text='Moderadamente dilatada'
        elif 41<=lad:
            la_text='Severamente dilatada'
    #determino texto de la AD
    if rad!='':
        if 18<rad<=28:
            ra_text='Levemente dilatada'
        elif 28<rad<=38:
            ra_text='Moderadamente dilatada'
        elif 38< rad:
            ra_text='Severamente dilatada'
    dic['la_text']=la_text
    dic['ra_text']=ra_text
    dic['conc_atrium']=conc_atrium(la_text,ra_text)
    return dic

def conc_atrium(la_text,ra_text):
    conc='Aurículas de dimensiones normales'
    if 'dilatada' in la_text and 'dilatada' in ra_text:
        conc='Aurículas dilatadas'
    if 'dilatada' in la_text and 'dilatada' not in ra_text:
        conc='Aurícula izquierda dilatada'
    if 'dilatada' not in la_text and 'dilatada' in ra_text:
        conc='Aurícula derecha dilatada'
    return conc





