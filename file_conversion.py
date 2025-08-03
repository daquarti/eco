#!/usr/bin/env python
# coding: utf-8

# In[5]:


from pathlib import Path
import os
import win32com.client as win32


def cargar_path(path):
    '''
    Aceptal el path a un directorio conteniendo multiples archivos doc
    y los convierte en docx los archivos
    '''
    p=Path(path)
    convert_doc_to_docx(p)
    return list(p.glob('**\\*.docx'))

def convert_doc_to_docx(path):
    '''
    This function checks for .doc files in the directory, converts them to .docx if 
    there are more .doc files than .docx, and deletes the original .doc files after conversion.

    Parameters:
    path (Path object): The directory path containing the .doc and .docx files.
    '''
    # Initialize Word application
    word = win32.Dispatch("Word.Application")
    word.Visible = False  # Run in the background (headless)

    try:
        # Find all .doc and .docx files
        doc_files = list(path.glob('**\\*.doc'))
        docx_files = list(path.glob('**\\**.docx'))

        # Compare the count of .doc and .docx files
        if len(doc_files) > len(docx_files):
            for doc in doc_files:
                # Check if the corresponding .docx file already exists
                docx_path = doc.with_suffix('.docx')
                if not docx_path.exists():  # Only convert if .docx doesn't already exist
                    # Open the .doc file in Word
                    doc_obj = word.Documents.Open(str(doc))
                    # Save as .docx
                    doc_obj.SaveAs(str(docx_path), FileFormat=16)  # 16 is the format code for .docx
                    doc_obj.Close()  # Close the document
                    # Delete the original .doc file after conversion
                    doc.unlink()
                    print(f"Converted {doc} to {docx_path}")
        else:
            print("No conversion needed: .docx files are equal to or outnumber .doc files.")

    except Exception as e:
        print(f"Error during conversion: {e}")

    finally:
        word.Quit()



# In[ ]:




