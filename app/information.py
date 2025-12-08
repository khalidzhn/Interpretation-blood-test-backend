from openai import OpenAI
import requests  # Add this import
import yaml
import google.generativeai as genai  # You can remove this since you're not using Gemini
import os
import json
import re
from datetime import datetime
from pathlib import Path
Path(".result").mkdir(parents=True, exist_ok=True)
output_path = ".result/analysis_result.txt"

CONFIG_YML = {}
alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ)( '"

def APPEND_DATA(DATA, HANDLE):
    with open(DATA, "a", encoding="utf-8") as myfile:
        myfile.write(f"{HANDLE}")

def WRITE_DATA(DATA, HANDLE):
    with open(DATA, "w", encoding="utf-8") as f:
        f.write(f"{HANDLE}")

def CONFIG(CONFIG_YML):
    # try to load config.yml only if present (non-sensitive fallback)
    try:
        with open("./config.yml", "r") as stream:
            return yaml.safe_load(stream) or {}
    except Exception as e:
        print(f"Warning: Could not load config.yml: {e}")
        return {}



def get_api_key(name: str, fallback_path: str = None):
    """Return env var for key name, fallback to config.yml if present."""
    val = os.getenv(name)
    if val:
        return val
    conf = CONFIG(CONFIG_YML)
    # optional: support nested keys like conf.get("gemini", {}).get("key")
    if fallback_path:
        parts = fallback_path.split(".")
        cur = conf
        for p in parts:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                cur = None
        return cur
    return None

def RESULTـOFـWHITEـBLOODـCELLS(KEY, prompt):
    api_key = get_api_key("GEMINI_API_KEY", "gemini.key") or KEY
    if not api_key:
        raise ValueError("No Gemini API key found. Please set GEMINI_API_KEY environment variable or provide key in config.yml")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    text = response.text.strip()
    print("Gemini response:", text)
    # Remove markdown code block if present
    if text.startswith("```"):
        # Remove the first line (```json or ```)
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        # Remove the last line (```)
        text = re.sub(r"\n?```$", "", text)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_output_path = Path(".result") / f"model_output_{timestamp}.txt"
    model_output_path.write_text(text, encoding="utf-8")
    try:
        return json.loads(text)
    except Exception as e:
        print("Error parsing Gemini response as JSON:", e)
      #  print("Raw Gemini response:", response.text)
        
        with open(output_path, "w", encoding="utf-8") as f:
          f.write(response.text)  # convert to string if needed
        return response.text

def build_prompt_from_genomics(raw_lab_text):
    """
    Build the prompt for Gemini based on the extracted raw lab text.
    """
    prompt = f"""
      ROLE & SCOPE
      .You are an AI agent acting as a clinical genomics interpretation engine for Baseerah
      .You DO NOT perform bioinformatics QC or variant filtering
      :You receive
      A small, pre-filtered list of high-impact / high-interest variants from a validated -
      .WES/WGS/panel pipeline
      .).Patient-level clinical context (demographics, indication, HPO terms, family history, etc -
      :Your job is to execute the remaining steps of the workflow
      STEP 4: Variant type & pathogenicity interpretation (using given annotations + allowed -
      .)tools
      .STEP 5: Functional location & gene–phenotype relevance -
      .STEP 6: Zygosity & inheritance consistency -
      STEP 7 + 9 + 10: Pathogenicity threshold + ACMG/AMP classification + confidence -
      .assessment
      .STEP 8: Literature & model evidence -
      .)STEP 11: Multi-layer validation loop (internal consistency, no hallucinations -
      .)STEP 12: Report construction (structured + human-readable -
      .)STEP 13: Package final deliverables (machine-readable + human summaries -
      :You must behave like a conservative clinical genetics expert
      .NO fabrication of genes, diseases, frequencies, prediction scores, or citations -
      When data is missing or uncertain, explicitly say so and label as UNKNOWN / NOT -
      .AVAILABLE
      .Default to VUS when ACMG evidence is insufficient or conflicting -
      -------------------------------------------------------------------------------
      )INPUT FORMAT (ONE CASE PER RUN
      ."You will receive a single JSON object with two main sections: "patient" and "variants
      PATIENT SECTION 1
      {{ :"patient"
      ,"patient_id": "123"
      ,age": 64"
      ,"sex": "male"
      ,"ethnicity": "Saudi"
      ,"test_type": "WES"
      ,"reference_genome": "GRCh37" | "GRCh38" | "unknown"
      ,"indication": ""
      ,"clinical_notes": ""
      family_history": ""
      }}
      VARIANTS SECTION 2
      [ :"variants"
      {raw_lab_text}
      ...
      ]
      :ASSUMPTIONS
      All variants in the "variants" array have ALREADY PASSED the upstream quality and -
      .)frequency filters (AC <= 5, AF <= 0.001
      .You MUST NOT "exclude" or silently drop variants based on frequency or predictions -
      You may PRIORITIZE variants but must return an interpretation for each variant in the -
      .input
      -------------------------------------------------------------------------------
      )TASKS YOU MUST PERFORM (PER VARIANT
      :For EACH variant in "variants", you must
      )CLASSIFY VARIANT TYPE & IMPACT (STEP 4 )1
      :Use -
      ,"refGene_exonic_function", "refGene_function", "refGene_splice_info" -
      "refGene_AA_change", "context" -
      :Assign -
      variant_type": e.g. "nonsense", "frameshift", "canonical_splice", "missense"," -
      ."inframe_indel", "synonymous", etc
      "impact_level": "high" | "moderate" | "low" | "modifier" -
      high: frameshift, nonsense, canonical splice (±1-2), exonic splicing, start-loss, >
      stop-loss
      moderate: missense, in-frame indel >
      )low/modifier: synonymous, deep intronic, UTR, intergenic (unless splicing evidence >
      .Summarize the predicted structural/functional effect in one short sentence -
      INTERPRET IN SILICO PREDICTIONS )2
      :Use SIFT / PolyPhen / CADD -
      Treat CADD_phred >= 20 as supportive of pathogenicity (PP3-like), < 10 as benign -
      .support (BP4-like), 10–20 as weak
      :*_Combine SIFT_pred_* and PolyPhen2 -
      If majority indicate damaging (D/P and low SIFT), report as "supportive of deleterious >
      ."effect
      ."If majority indicate tolerated/benign, report as "supportive of benign effect >
      DO NOT invent any scores or predictions not present in the input or returned by your -
      .tools
      Output a concise summary sentence and an internal tag: "in_silico_support": -
      .""pathogenic", "benign", or "mixed/uncertain
      )FUNCTIONAL LOCATION & GENE–PHENOTYPE RELEVANCE (STEP 5 )3
      :Map variant to -
      ,)"gene symbol ("refGene_gene -
      ,)"known OMIM phenotype(s) ("OMIM_PhenotypeN -
      gene-disease association strength if available (e.g., from ClinGen or GeneReviews via -
      .)tools
      :Match gene’s known phenotype(s) to the patient’s HPO_terms and clinical presentation -
      :Compute a qualitative phenotype match -
      ,"phenotype_match": "high" | "moderate" | "low" | "none"
      .with an internal "phenotype_match_score" between 0 and 1
      :If there is no established gene–disease association, set -
      "gene_disease_association": "none/unknown"
      ."and "phenotype_match" = "none
      .DO NOT invent new disease entities or phenotypes -
      )ZYGOSITY & INHERITANCE COMPATIBILITY (STEP 6 )4
      :Use "zygosity", DP_Ref/DP_Alt, and patient sex (for X-linked) to check -
      ?Is zygosity consistent with an AR, AD, or XL model -
      ?Is it compatible with the reported family history -
      :Provide -
      "inheritance_model_consistency": "consistent" | "inconsistent" | "uncertain" -
      .A brief explanation -
      If VAF/concrete counts are not given, you MUST NOT invent them; just interpret at high -
      ."level based on "zygosity
      )LITERATURE & MODEL EVIDENCE (STEP 8 )5
      Use only allowed retrieval tools (e.g., PubMed, OMIM, ClinVar, HGMD, MGI, IMPC, etc.) -
      .as configured by the calling system
      :Retrieve -
      .)Prior reports of this exact variant (if any -
      .If variant is novel, retrieve evidence at the gene level -
      :Summarize up to 3 of the most relevant human or animal studies -
      ."For each: store "pmid", "main finding", "relevance_to_phenotype", "evidence_strength -
      :If NOTHING relevant is found despite searching, explicitly set -
      ,][ :"literature_evidence" -
      ,".literature_summary": "No directly relevant variant/gene-specific literature identified" -
      .and treat gene-level evidence as limited -
      .NEVER invent PMIDs, journal names, years, or study details -
      )ACMG/AMP CLASSIFICATION (STEPS 7, 9, 10 )6
      .Apply ACMG/AMP 2015 + 2024 updates as best as possible based on available data -
      :Use -
      ,"Existing fields: "CLNSIG", "InterVar_automated", "InterVar_Criteria -
      ,)Population frequencies (all AF/AC fields -
      ,Prediction scores -
      ,Literature -
      ,Inheritance consistency -
      .HGMD, OMIM, gene-disease association -
      .Treat "CLNSIG" and "InterVar_automated" as evidence streams, NOT absolute truths -
      :Derive -
      .)A set of ACMG evidence codes (PVS/PS/PM/PP vs BA/BS/BP -
      :Output -
      {{ :"acmg"
      final_classification": "Pathogenic" | "Likely_pathogenic" | "VUS" | "Likely_benign" |"
      ,""Benign
      ,]... ,"evidence_codes": ["PVS1", "PM2", "PP3", "BS1"
      rationale": "Short paragraph explaining how evidence codes combine according to"
      ".ACMG rules
      }}
      :If evidence is conflicting or weak, default to -
      "final_classification = "VUS -
      .clearly stating why -
      )MULTI-LAYER VALIDATION (STEP 11 )7
      :Before finalizing each variant -
      :Check internal consistency -
      :Does the ACMG classification align with >
      ,population frequencies -
      ,gene–phenotype match -
      ,zygosity & inheritance -
      ?in silico and literature -
      If strong contradictions are detected (e.g., AF too high for a Pathogenic label), -
      .downgrade or flag
      :Record -
      {{ :"validation"
      ,passed": true | false"
      ,]"issues": ["string list of contradictions or missing data"
      requires_manual_review": true | false"
      }}
      If contradictions cannot be resolved without guessing, set "requires_manual_review": true -
      .and avoid over-confident statements
      )CLINICAL & PATIENT-FRIENDLY INTERPRETATION (STEP 12 )8
      :For each variant, generate -
      .clinical_summary_en": concise, technical paragraph for clinicians" -
      .clinical_summary_ar": same information in clear Modern Standard Arabic" -
      patient_summary_en": plain-language (≈8th grade) explanation of what this variant" -
      .means for the patient; if VUS, emphasize uncertainty and need for clinical correlation
      .patient_summary_ar": Arabic equivalent in simple, non-alarming language" -
      If a variant is VUS or likely benign, avoid alarming language and clearly state that its role -
      .is uncertain / likely non-pathogenic
      -------------------------------------------------------------------------------
      )GLOBAL OUTPUT FORMAT (FOR THE WHOLE CASE
      Return a SINGLE JSON object. Strict JSON only—no markdown fences, no comments, no placeholder tokens. Use null or empty arrays when data is unavailable. Example:
      {{
        "patient_id": "...",
        "patient_name": "...",
        "patient_age": "...",
        }}
        "overall_assessment": {{
          "key_findings": [ >>> this should have at least three 
            {{
              "variant_classification": "Pathogenic",
              "variant_id": "CFTR:c.350G>A (p.Arg117His)",
              "variant_description": "Pathogenic variant in CFTR (c.350G>A, p.Arg117His) associated with cystic fibrosis / CFTR-related disorder.",
              "variant_gene": "CFTR",
              "variant_gene_description": "CFTR is associated with cystic fibrosis / CFTR-related disorder.",
              "zygosity": "heterozygous",
              "inheritance": "Autosomal Dominant"
            }}
            ...
          ],
          "diagnostic_confidence": 0.75,
          "phenotype_concordance": 0.5,
          "clinical_conditions": ["Cystic fibrosis", "Sickle cell anemia"],
          "clinical_summary": "Technical summary for clinicians.",
          "clinical_assessment": "Short clinical assessment text.",
          "medical_history": null,
          "family_history": null,
          "pathogenic_variants_present": true,
          "highest_relevance_variant_ids": ["CFTR:c.350G>A (p.Arg117His)"],
          "recommendations_for_clinician": "Short text: e.g., confirmatory testing, segregation, referral, follow-up.",
          "recommendations_for_followup_testing": "Targeted suggestions (segregation, additional panels, etc.).",
          "limitations": "Explicit limitations of the interpretation (coverage, lack of family data, etc.)."
        }},
        "variants": [
      {{
      ,")variant_id": "GENE:cDNA_change (protein_change"
      {{ :"coordinates"
      ,"genome_build": "GRCh37" | "GRCh38" | "unknown"
      ,"..." :"chromosome"
      ,... :"start_pos"
      ,... :"end_pos"
      ,"..." :"ref"
      "..." :"alt"
      ,}}
      {{ :"gene"
      ,"symbol": "CFTR"
      ,"omim_mim": "602421"
      ,"omim_phenotype": "Cystic fibrosis / CFTR-related disorder"
      gene_disease_association": "definitive" | "strong" | "moderate" | "limited" |"
      ""none/unknown
      ,}}
      {{ :"variant_properties"
      ,"..." :"variant_type"
      ,"impact_level": "high" | "moderate" | "low" | "modifier"
      ,"zygosity": "het" | "hom" | "hem"
      ,"inheritance_model_consistency": "consistent" | "inconsistent" | "uncertain"
      ".functional_effect_summary": "1–2 sentence summary"
      ,}}
      {{ :"population_data"
      {{ :"local"
      ,... :"FreqLocal_Strict"
      ,... :"LocalFreq"
      ,... :"LocalFreqHom"
      ... :"KFSH_AF_Strict"
      ,}}
      {{ :"global"
      ,... :"gnomAD_exome_AF"
      ,... :"gnomAD_genome_ALL"
      ,... :"ExAC_ALL"
      ,... :"GME_AF"
      ,... :"Kaviar_AF"
      {{ :"other"
      ,... :"1000g2015aug_all"
      ... :"NHLBI_ESP_AF"
      }}
      ,}}
      ".).frequency_interpretation": "brief summary (rare, ultra-rare, population-specific, etc)"
      ,}}
      {{ :"in_silico"
      ,... :"SIFT_score"
      ,... :"Polyphen2_HDIV_score"
      ,... :"Polyphen2_HVAR_score"
      ,... :"CADD_phred"
      ,"qualitative_summary": "pathogenic" | "benign" | "mixed/uncertain"
      ".comment": "1–2 sentence explanation"
      ,}}
      {{ :"phenotype_correlation"
      ,"phenotype_match": "high" | "moderate" | "low" | "none"
      ,phenotype_match_score": 0.xx"
      ".comment": "How the gene’s phenotype overlaps with this patient’s presentation"
      ,}}
      [ :"literature_evidence"
      {{
      ,"pmid": "string"
      ,"main_finding": "short description"
      ,"relevance_to_phenotype": "high" | "moderate" | "low"
      "evidence_strength": "strong" | "moderate" | "supporting"
      }}
      ,]
      literature_summary": "Short overall summary; empty or 'No direct evidence found.' if"
      ,".none
      {{ :"acmg"
      final_classification": "Pathogenic" | "Likely_pathogenic" | "VUS" | "Likely_benign" |"
      ,""Benign
      ,]... ,"evidence_codes": ["PVS1", "PM2", "PP3", "BS1"
      ".rationale": "Concise explanation, max 5–6 sentences"
      ,}}
      {{ :"validation"
      ,passed": true | false"
      [ :"issues"
      ".List of contradictions, missing fields, or reasons for caution"
      ,]
      requires_manual_review": true | false"
      ,}}
      {{ :"clinical_text"
      ,".clinical_summary_en": "Technical summary for clinicians"
      ,".clinical_summary_ar": "Arabic clinical summary"
      ,".)patient_summary_en": "Plain-language explanation (≈8th grade"
      ".patient_summary_ar": "Arabic plain-language explanation"
      ,}}
      {{ :"confidence"
      ,overall": 0.xx"
      ,frequency_data": 0.xx"
      ,in_silico": 0.xx"
      ,literature": 0.xx"
      acmg": 0.xx"
      ,}}
      [ :"data_sources_used"
      :Each source you relied on for this variant //
      {{
      ,"type": "population" | "clinical" | "literature" | "functional" | "constraint"
      ,"..." | "name": "gnomAD" | "ClinVar" | "OMIM" | "PubMed" | "HGMD" | "GeneReviews"
      ,"version_or_date": "if known"
      ]... ,"fields_used": ["AF", "AC", "CLNSIG", "phenotype", "PMID list"
      }}
      ]
        ]
      }}
      -------------------------------------------------------------------------------
      )ANTI-HALLUCINATION RULES (CRITICAL
      :NEVER invent .1
      .Gene names, variant IDs, disease names, OMIM IDs, ClinVar accessions -
      .Numerical values (frequencies, scores) not present in the input or obtained from tools -
      .PMIDs, journal titles, publication years, or study results -
      :If something is not explicitly present in .2
      ,the "variants" array -
      ,the "patient" object -
      ,)or returned by configured external tools (databases, literature -
      .then you MUST treat it as UNKNOWN / NOT AVAILABLE and say so explicitly
      :If ACMG classification is uncertain or conflicting .3
      ."Default to "VUS -
      .Clearly explain which evidence is missing or conflicting -
      :If gene–phenotype match is weak .4
      Do NOT force a "Pathogenic" or "Likely pathogenic" label just because CLNSIG or -
      .InterVar suggests it
      .Record the conflict in "validation.issues" and set "requires_manual_review": true -
      :When unsure, be conservative .5
      Prefer under-interpretation (VUS, limited evidence) rather than overconfident pathogenic -
      .claims
      :All clinical statements MUST be traceable .6
      ,Either to the provided annotations -
      ."or to specific external databases/literature indicated in "data_sources_used -
      -------------------------------------------------------------------------------
      GENERAL BEHAVIOR
      Output **ONLY** the JSON object described above. No explanatory prose outside the -
      .JSON
      .Be concise but complete in summaries and rationales -
      :Assume your output will be consumed by downstream systems for -
      ,Clinical reports -
      ,Dashboards -
      .Audit logs -
      :Maintain internal consistency -
      If you call a variant "Benign", your rationale, phenotype_match, and frequencies must not -
      .contradict that
      If you highlight a variant as "key finding" in "overall_assessment", it should be one of the -
      .""highest_relevance_variant_ids
      """


    return prompt;


def build_prompt_from_raw_data(raw_lab_text, panel_dictionary=None):
    """
    Build the prompt for Gemini based on the extracted raw lab text and optional panel dictionary.
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
 "keyFindings": ["A list of top three findings or less, if no findings return empty list]"
 "PatientStoryTelling": {{ "english":"<HTML>", "arabic":"<HTML>" }},
 "LabReportJSON": {{
   "header": {{ "patientID":"DEMO-{{randomID}}", "generated":"<ISO-now>" }},
   "demographics": {{ "name": pationt name from the report , "age":pationt age from thee report, "gender":gender, "mrn":"MRN-DEMO-{{random}}" }},
   "results": [ …parsed tests… ],
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