from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import os

DATA_PROPERTI = {}

# Blood factors needed to interpret laboratory data 
# data dynamic geting from PDF file.

QUERY_B = [
    "Hemoglobin",
    "WBC count",
    "RBC count",
    "Platelet Count",
    "PCV",
    "MCV",
    "MCH",
    "MCHC",
    "RDW",
    "Neutrophils",
    "Lymphocytes",
    "Monocytes",
    "Eosinophils",
    "Basophils"
]


def get_data_from_user(data_input):
    """
    Extract text from PDF using OCR (pdf2image + pytesseract).
    This method preserves the visual order of text better than direct PDF text extraction.
    
    Note: Requires poppler-utils and tesseract-ocr to be installed on the system.
    """
    text = ""
    
    try:
        # Convert PDF pages to images
        # dpi=300 for better OCR accuracy, can be adjusted based on PDF quality
        images = convert_from_path(data_input, dpi=300)
        
        # Extract text from each page image using OCR
        for i, image in enumerate(images):
            # Use pytesseract to extract text from the image
            # This preserves the visual layout order
            page_text = pytesseract.image_to_string(image, lang='eng')
            if page_text:
                text += page_text + "\n"
                
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        # Fallback: try basic text extraction if OCR fails
        try:
            from PyPDF2 import PdfReader
            with open(data_input, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as fallback_error:
            print(f"Fallback extraction also failed: {fallback_error}")
            return ""
    
    return text
    

def FIND_USABLE_DATA(final_get_data, query):
    
    REQUESTED_INFORMATION = ""
    
    '''
    
    By sending requested requests, the data will be divided in better details 
    and placed more easily in the database.
    
    '''
    RAW = final_get_data.find(query)
    INIT = 0
    while INIT < len(final_get_data):        
        if final_get_data[RAW + INIT] == "\n":
            break
        
        REQUESTED_INFORMATION = REQUESTED_INFORMATION + final_get_data[RAW+INIT]
        INIT += 1
        
    
    NEW_DATA = ""
    counter_MELON = 0
    for i in REQUESTED_INFORMATION:
        if counter_MELON == 1:
            NEW_DATA = NEW_DATA + "----"
            counter_MELON = 2
            
        if i != " ":
            NEW_DATA = NEW_DATA + i
            counter_MELON = 0
            continue
        
        counter_MELON += 1
    
    # REQUESTED_INFORMATION.replace(query, "")
    return NEW_DATA


    '''

    This function will display the data in the form of a table 
    by receiving the information under the terminal and regularly deliver the data to the database.

        | Data   |      Value    |

        | WBC    |       34      |
        | RBC    |       43      |
        | HCT    |       23      |
        | MCV    |       12      |
        | MCH    |       45      |

    ''' 