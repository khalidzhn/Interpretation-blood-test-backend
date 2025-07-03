from openai import OpenAI
import yaml
import google.generativeai as genai
import os
import json
import re

CONFIG_YML = {}
alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ)( '"

def APPEND_DATA(DATA, HANDLE):
    with open(DATA, "a", encoding="utf-8") as myfile:
        myfile.write(f"{HANDLE}")

def WRITE_DATA(DATA, HANDLE):
    with open(DATA, "w", encoding="utf-8") as f:
        f.write(f"{HANDLE}")

def CONFIG(CONFIG_YML):
    with open("./config.yml") as stream:
        try:
            CONFIG_YML = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"parse data from config.yml have error {exc}")
    return CONFIG_YML


def RESULTـOFـWHITEـBLOODـCELLS(KEY, prompt):
    genai.configure(api_key=KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    text = response.text.strip()
    # Remove markdown code block if present
    if text.startswith("```"):
        # Remove the first line (```json or ```)
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        # Remove the last line (```)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except Exception as e:
        print("Error parsing Gemini response as JSON:", e)
        print("Raw Gemini response:", response.text)
        return None
    
def build_prompt_from_raw_data(raw_lab_text, panel_dictionary=None):
    """
    Build the prompt for Gemini based on the extracted raw lab text and optional panel dictionary.
    """
    prompt = f"""
You are “Baseerah AI,” an evidence-based clinical reasoning engine.

INPUTS:
- raw_lab_text: {raw_lab_text}
- panel_dictionary: {panel_dictionary if panel_dictionary else '[Not provided]'}

NOTE: In demo mode, there is no clinical note, EMR, or real referral API.
You must synthesize plausible clinical context and referral details for demo purposes only.

OBJECTIVES:
1. Parse raw_lab_text into a structured analyte list: {{ testName, value, units, refRange? }}
2. Classify each test as Normal, Borderline, High, or Critical.
3. Synthesize a 1-sentence HPI + PMH based on age/gender clues in the lab text (if absent, assume 45-year-old male, routine screen).
4. Determine holistic RiskLevel and AI Confidence.
5. Referral Logic (Demo): Choose the most relevant specialty for the worst abnormality. Auto-generate a fake appointment:
   - Date: 7-10 days after today at 10:00 AM
   - Location: “King Faisal Specialist Hospital, Clinic B” (if renal), “King Fahad Medical City, Endocrine Center” (if endocrine), etc.
   - Physician: “Dr. Demo Surname (Specialty)”
6. DoctorInterpretation: ≤150 words, guideline language, cite synthesized clinical note.
7. PatientStory: ≤90 words in English and Arabic, using panel_dictionary phrases.
8. Return JSON in the exact schema below.

OUTPUT SCHEMA (return JSON only):
{{
 "IntelligenceHubCard": aiConfidence  High|Low|Moderate, hpiPmhSummary, riskLevel High|Low|Moderate > {{ … }},
 "AutoReferralBlock": {{
   "needed": true|false,
   "specialty": "<string|null>",
   "urgency": "Urgent|Soon|Routine|null",
   "bookedStatus": "Booked",
   "suggestedDate": "<ISO-date 10:00 AM>"
 }},
 "DoctorInterpretation": "<HTML>",
 "keyFindings:": "A list of top three findings or less, if no findings return emty list  > String[]"
 "PatientStoryTelling": {{ "english":"<HTML>", "arabic":"<HTML>" }},
 "LabReportJSON": {{
   "header": {{ "patientID":"DEMO-{{randomID}}", "generated":"<ISO-now>" }},
   "demographics": {{ "name":"Ahmed Al-Mansouri", "age":"45", "gender":"Male", "mrn":"MRN-DEMO-{{random}}" }},
   "results": [ …parsed tests… ],
   "aiInterpretationEN": "<copy DoctorInterpretation>",
   "referral": {{ …same as AutoReferralBlock }},
   "patientSummary": {{ "en":"<copy>", "ar":"<copy>" }}
 }}
}}

RULES:
- If refRange is absent, infer standard adult range (cite silently).
- Use panel_dictionary stories; never output untranslated placeholders.
- Synthetic data must look plausible but clearly demo-only.
- Return only the JSON; no markdown fences or extra text.
"""
    return prompt