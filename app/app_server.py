from fastapi import FastAPI, File, UploadFile
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import shutil
from .main import get_data_from_user
import app.information as information  # Import your analysis logic
import uuid
from sqlalchemy.dialects.postgresql import UUID
from fastapi.responses import JSONResponse
import os
from fastapi.middleware.cors import CORSMiddleware
import json
from sqlalchemy.dialects.postgresql import JSON
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import desc

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@localhost:5432/mydatabase")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend URL instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True, index=True)
    pdf_filename = Column(String, nullable=False)      # Path to saved PDF
    raw_data = Column(Text, nullable=False)            # Extracted text from PDF
    analysis = Column(JSON, nullable=False)
    patient_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))

Base.metadata.create_all(bind=engine)
@app.get("/")
def read_root():
    return {"status": "ok"}
@app.get("/analysis-results/")
@app.get("/analysis-results")
def get_all_analysis_results():
    db = SessionLocal()
    results = db.query(AnalysisResult).order_by(desc(AnalysisResult.id)).all()
    db.close()
    results_list = []
    for r in results:
        analysis = r.analysis
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except Exception:
                analysis = {}
        results_list.append({
            "patient_id": r.patient_id,
            "pdf_filename": r.pdf_filename,
            "DoctorInterpretation": analysis.get("DoctorInterpretation"),
            "AutoReferralBlock": analysis.get("AutoReferralBlock"),
            "IntelligenceHubCard": analysis.get("IntelligenceHubCard"),
            "keyFindings": analysis.get("keyFindings"),
        })
    return JSONResponse(content=results_list)
@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    print("UPLOAD ENDPOINT CALLED")
    print("Received file:", file.filename)
    pdf_dir = "uploaded_pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, file.filename)
    pdf_name = file.filename
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    print("Saved PDF to:", pdf_path)

    raw_data = get_data_from_user(pdf_path)
    print("Extracted raw data:", raw_data[:200])  # Print first 200 chars


    # Read your text file as CSV
    panel_path = os.path.join("panel", "labPanels.txt")
    df = pd.read_csv(panel_path)
    # Convert to list of dicts
    panel_dictionary = df.to_dict(orient="records")
    prompt = information.build_prompt_from_raw_data(raw_data, panel_dictionary)
    print("Prompt built.")  # Print first 200 chars of the prompt")

    key = information.CONFIG(information.CONFIG_YML).get("gemini").get("key")
    print("Gemini key loaded.")

    analysis = information.RESULTـOFـWHITEـBLOODـCELLS(key, prompt)
    print("Raw analysis result:", analysis)    
    patient_id = str(uuid.uuid4())
    db = SessionLocal()
    
    if isinstance(analysis, str):
        try:
            # Keep decoding until it's a dict (handles double-encoded JSON)
            while isinstance(analysis, str):
                analysis = json.loads(analysis)
        except Exception:
            db.close()
            return JSONResponse(status_code=400, content={"error": "Analysis could not be generated or parsed as JSON."})

    if not analysis or not isinstance(analysis, dict):
        db.close()
        return JSONResponse(status_code=400, content={"error": "Analysis is empty or not a valid JSON object."})

    db_result = AnalysisResult(
        pdf_filename=pdf_name,
        raw_data=raw_data,
        analysis=analysis,  # Save as dict
        patient_id=patient_id

    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    db.close()
    print("Saved to DB.")

    return {"message": "PDF processed and data stored.", "id": db_result.id}
@app.get("/lab-result/{labResultId}")
def get_lab_report_json(labResultId: str):
    db = SessionLocal()
    result = db.query(AnalysisResult).filter(AnalysisResult.patient_id == labResultId).first()
    db.close()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    analysis = result.analysis
    # Parse if it's a string (even if it's double-encoded)
    if isinstance(analysis, str):
        try:
            # Try to decode until it's a dict
            while isinstance(analysis, str):
                analysis = json.loads(analysis)
        except Exception:
            raise HTTPException(status_code=500, detail="Analysis could not be parsed as JSON")
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis