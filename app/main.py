from PyPDF2 import PdfReader

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
    
    text = ""
    
    '''
        The data is received by pdf files in the assets section 
        and the data is analyzed by the PDFQuery library and 
        stored in a list and the output is published.
        
    ''' 
    with open(data_input, 'rb') as f:
        reader = PdfReader(f)
        for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
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