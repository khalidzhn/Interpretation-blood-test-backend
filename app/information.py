from openai import OpenAI
import requests  # Add this import
import yaml
import google.generativeai as genai  # You can remove this since you're not using Gemini
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
    """
    Send prompt to Poe API using requests instead of OpenAI client
    """
    try:
        url = "https://api.poe.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "GPT-OSS-120B-T",
            "messages": [
                {
                    "role": "system", 
                    "content": "You are Baseerah AI. Always respond with valid JSON only. No markdown formatting or code blocks."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent JSON
            "max_tokens": 4000
        }
        
        print("🔄 Sending request to Poe API...")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"📡 API Response status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            response_text = response_data["choices"][0]["message"]["content"].strip()
            print(f"✅ Received response: {len(response_text)} characters")
            
            # More aggressive cleaning of the response
            response_text = response_text.strip()
            
            # Remove markdown code blocks
            if response_text.startswith("```"):
                response_text = re.sub(r"^```[a-zA-Z]*\n?", "", response_text)
                response_text = re.sub(r"\n?```$", "", response_text)
            
            # Remove any text before the first {
            if not response_text.startswith("{"):
                first_brace = response_text.find("{")
                if first_brace != -1:
                    response_text = response_text[first_brace:]
            
            # Remove any text after the last }
            if not response_text.endswith("}"):
                last_brace = response_text.rfind("}")
                if last_brace != -1:
                    response_text = response_text[:last_brace + 1]
            
            print(f"🧹 Cleaned response first 200 chars: {response_text[:200]}...")
            
            try:
                parsed_response = json.loads(response_text)
                print("✅ Successfully parsed JSON response from Poe API")
                return parsed_response
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                print(f"Raw response: {response_text[:500]}...")
                return None
                
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error calling Poe API: {e}")
        print(f"Error type: {type(e).__name__}")
        return None




def build_prompt_from_raw_data(raw_lab_text, panel_dictionary=None):
    """
    Build the prompt for Poe API based on the extracted raw lab text and optional panel dictionary.
    """
    prompt = f"""
You are "Baseerah AI," an evidence-based clinical reasoning engine.

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
   - Location: "King Faisal Specialist Hospital, Clinic B" (if renal), "King Fahad Medical City, Endocrine Center" (if endocrine), etc.
   - Physician: "Dr. Demo Surname (Specialty)"
10. DoctorInterpretation: ≤150 words, guideline language, cite synthesized clinical note.
11. PatientStory: greeting the patient with his name ≤90 words in English and Arabic, using panel_dictionary phrases.
12. Return JSON in the exact schema below.

IMPORTANT: Return ONLY valid JSON. No markdown formatting, no code blocks, no extra text.

OUTPUT SCHEMA (return valid JSON only):
{{
 "IntelligenceHubCard": {{
   "aiConfidence": "High|Low|Moderate",
   "hpiPmhSummary": "<synthetic clinical context>",
   "riskLevel": "High|Low|Moderate"
 }},
 "AutoReferralBlock": {{
   "needed": true,
   "specialty": "Nephrology",
   "urgency": "Soon",
   "bookedStatus": "Booked",
   "suggestedDate": "2025-09-13T10:00:00"
 }},
 "AI_ClinicalInterpretation": {{
   "integratedClinicalContext": "<The synthetic clinical note string goes here>",
   "resultLinkedAnalysis": [
     {{ "finding": "HbA1c 6.2%", "analysis": "Consistent with ADA 'pre-diabetes' criteria; aligns with prior fasting glucose (112 mg/dL)." }},
     {{ "finding": "LDL 160 mg/dL", "analysis": "ASCVD 10-yr risk now ≥ 15%. Intensify lipid-lowering therapy." }}
   ],
   "evidenceBasedRecommendations": [
     "Start high-intensity statin; target LDL < 70 mg/dL.",
     "Initiate metformin 500 mg BID after nephrology clearance."
   ]
 }},
 "DoctorInterpretation": "<HTML>",
 "keyFindings": ["List of top findings"],
 "PatientStoryTelling": {{ "english":"<HTML>", "arabic":"<HTML>" }},
 "LabReportJSON": {{
   "header": {{ "patientID":"DEMO-12345", "generated":"2025-09-06T10:00:00Z" }},
   "demographics": {{ "name": "Demo Patient", "age": "45", "gender": "Male", "mrn":"MRN-DEMO-67890" }},
   "results": [],
   "aiInterpretationEN": "<copy DoctorInterpretation>",
   "referral": {{
     "needed": true,
     "specialty": "Nephrology",
     "urgency": "Soon",
     "bookedStatus": "Booked",
     "suggestedDate": "2025-09-13T10:00:00"
   }},
   "patientSummary": {{ "en":"<copy>", "ar":"<copy>" }}
 }},
 "DoctorSummaryForPatient": "<The paragraph for 'What do these results mean for me?' goes here>",
 "IntelligentPatientReport": {{
   "introEN": "<Friendly intro in English>",
   "introAR": "<Friendly intro in Arabic>",
   "abnormalTests": [
     {{
       "testNameEN": "Blood Sugar (HbA1c)",
       "testNameAR": "السكر التراكمي",
       "resultDisplay": "6.2%",
       "status": "High",
       "emoji": "🩸",
       "storyEN": "<Personalized story for HbA1c...>",
       "storyAR": "<قصة مخصصة للسكر التراكمي>"
     }}
   ],
   "patientActionPlan": [
     {{"actionEn":"🚭 <b>Stop smoking</b> - this is the #1 priority for your health.", "actionAr":"🚭 <b>توقف عن التدخين</b> - هذه هي الأولوية الأولى لصحتك."}}
   ]
 }}
}}

RULES:
- If refRange is absent, infer standard adult range (cite silently).
- Use panel_dictionary stories; never output untranslated placeholders.
- Synthetic data must look plausible but clearly demo-only.
- Return only valid JSON; no markdown fences or extra text.

CRITICAL RULES:
1. Return ONLY the JSON object above
2. No markdown code blocks (no ```)  
3. No extra text before or after the JSON
4. Ensure all JSON syntax is correct with proper colons and commas
5. All string values must be in quotes
6. All object properties must be properly formatted
"""
    return prompt