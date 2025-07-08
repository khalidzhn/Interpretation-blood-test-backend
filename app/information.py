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
3. Create Clinical Context: Create a one-sentence synthetic clinical note describing the patient profile (e.g., "45-year-old male, BMI 31 kg/m², smoker...").
4. Determine holistic RiskLevel and AI Confidence.
5. Create Result-Linked Analysis: For the top 3-4 most significant abnormal results, generate a concise, one-line clinical analysis linking the result to established guidelines (e.g., LDL 160 mg/dL → "ASCVD 10-yr risk now ≥ 15%. Intensify lipid-lowering therapy.").
6. Generate Evidence-Based Recommendations: Create a numbered list of 3-5 specific, evidence-based clinical recommendations intended for a physician. These should be scientific and actionable (e.g., "Start high-intensity statin; target LDL < 70 mg/dL.", "Initiate metformin 500 mg BID after nephrology clearance.").
7. Generate Doctor's Summary: Write a high-level summary paragraph explaining the findings for a patient, as if a doctor were speaking. This will populate the "What do these results mean for me?" section.
8. Create a separate, simplified Patient Action Plan with 3-5 motivational, easy-to-understand bullets for the patient.
9. Referral Logic (Demo): Choose the most relevant specialty for the worst abnormality. Auto-generate a fake appointment:
   - Date: 7-10 days after today at 10:00 AM
   - Location: “King Faisal Specialist Hospital, Clinic B” (if renal), “King Fahad Medical City, Endocrine Center” (if endocrine), etc.
   - Physician: “Dr. Demo Surname (Specialty)”
10. DoctorInterpretation: ≤150 words, guideline language, cite synthesized clinical note.
11. PatientStory: greeting the pationt with his name  ≤90 words in English and Arabic, using panel_dictionary phrases.
12. Return JSON in the exact schema below.

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
  "AI_ClinicalInterpretation": {{
    "integratedClinicalContext": "<The synthetic clinical note string goes here>",
    "resultLinkedAnalysis": [
      {{ "finding": "HbA1c 6.2%", "analysis": "Consistent with ADA 'pre-diabetes' criteria; aligns with prior fasting glucose (112 mg/dL)." }},
      {{ "finding": "LDL 160 mg/dL", "analysis": "ASCVD 10-yr risk now ≥ 15%. Intensify lipid-lowering therapy." }},
      {{ "finding": "Creatinine 2.4 mg/dL", "analysis": "eGFR ≈ 32 mL/min/1.73 m² (CKD-3b). Possible diabetic nephropathy." }}
    ],
    "evidenceBasedRecommendations": [
      "Start high-intensity statin; target LDL < 70 mg/dL.",
      "Initiate metformin 500 mg BID after nephrology clearance.",
      "Refer to Nephrology (auto-booked below) for renal work-up + ACE inhibitor optimization.",
      "Lifestyle: DASH diet, smoking cessation, 150 min/week moderate exercise."
    ]
  }},
 "DoctorInterpretation": "<HTML>",
 "keyFindings:": ["A list of top three findings or less, if no findings return emty list]"
 "PatientStoryTelling": {{ "english":"<HTML>", "arabic":"<HTML>" }},
 "LabReportJSON": {{
   "header": {{ "patientID":"DEMO-{{randomID}}", "generated":"<ISO-now>" }},
   "demographics": {{ "name": pationt name from the report , "age":pationt age from thee report, "gender":gender, "mrn":"MRN-DEMO-{{random}}" }},
   "results": [ …parsed tests… ],
   "aiInterpretationEN": "<copy DoctorInterpretation>",
   "referral": {{ …same as AutoReferralBlock }},
   "patientSummary": {{ "en":"<copy>", "ar":"<copy>" }}
 }},
  // High-level summary for the patient
  "DoctorSummaryForPatient": "<The paragraph for 'What do these results mean for me?' goes here. These findings place the patient at high cardiometabolic risk...>",

  // The complete, personalized patient-facing report
  "IntelligentPatientReport": {{
    "introEN": "<Friendly intro in English>",
    "introAR": "<Friendly intro in Arabic>",
    // repeats for all other abnormal tests
    "abnormalTests": [
      {{
        "testNameEN": "Blood Sugar (HbA1c)",
        "testNameAR": "السكر التراكمي",
        "resultDisplay": "6.2%",
        "status": "High",
        "emoji": "🩸",
        "storyEN": "<Personalized story for HbA1c...>",
        "storyAR": "<...قصة مخصصة للسكر التراكمي>"
      }}
      
    ],
    "patientActionPlan": [ // Simplified plan for the patient
      {{"actionEn":"(emoji) <b>Stop smoking</b> - this is the #1 priority for your health.",
        "actionAr":"(emoji) <b>توقف عن التدخين</b> - هذه هي الأولوية الأولى لصحتك."}},
      {{"actionEn":"(emoji) <b>Follow the DASH</b> - diet meal plan we're preparing for you.",
        "actionAr":"(emoji) <b>اتباع نظام DASH</b> - خطة الوجبات الغذائية التي نقوم بإعدادها لك."}},
      {{"actionEn":"(emoji) <b>Walk 30 minutes every day</b> - start with 10 minutes if needed.",
        "actionAr":"(emoji) <b>المشي 30 دقيقة كل يوم</b> - ابدأ بـ 10 دقائق إذا لزم الأمر."}},
      {{"actionEn":"(emoji) <b>New medications</b> - your doctor will discuss new medications with you.",
        "actionAr":"(emoji) <b>المشي 30 دقيقة كل يوم</b> - ابدأ بـ 10 دقائق إذا لزم الأمر."}},
      {{"actionEn":"(emoji) Attend your kidney specialist visit on July 11th at 10:00 AM.",
        "actionAr":"(emoji) احضر زيارة أخصائي الكلى في 11 يوليو الساعة 10:00 صباحًا."}}
    ]
  }},

  // Supporting Data for UI elements like referral blocks
  "AutoReferralBlock": {{
    "needed": true,
    "specialty": "Nephrology",
    "urgency": "Soon",
    "bookedStatus": "Booked",
    // Set appointment 7-10 days from today (July 4, 2025) -> e.g., July 11-14
    "suggestedDate": "2025-07-11T10:00:00"
  }}
}}

RULES:
- If refRange is absent, infer standard adult range (cite silently).
- Use panel_dictionary stories; never output untranslated placeholders.
- Synthetic data must look plausible but clearly demo-only.
- Return only the JSON; no markdown fences or extra text.
"""
    return prompt