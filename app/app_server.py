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
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from fastapi import Depends
from fastapi import Body
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship



DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@localhost:5432/mydatabase")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()


SECRET_KEY = "your-secret-key"  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.close()
    if user is None:
        raise credentials_exception
    return user


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend URL instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True, index=True)
    pdf_filename = Column(String, nullable=False)
    raw_data = Column(Text, nullable=False)
    analysis = Column(JSON, nullable=False)
    patient_id = Column(String(10), unique=True, index=True, nullable=False)  # 10-digit patient ID
    assigned_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_doctor = relationship("User")
    
Base.metadata.create_all(bind=engine)
@app.get("/", dependencies=[Depends(get_current_user)])
def read_root():
    return {"status": "ok"}
@app.get("/analysis-results/", dependencies=[Depends(get_current_user)])
@app.get("/analysis-results", dependencies=[Depends(get_current_user)])
def get_all_analysis_results():
    db = SessionLocal()
    results = db.query(AnalysisResult).order_by(desc(AnalysisResult.id)).limit(10).all()
    results_list = []
    for r in results:
        doctor = db.query(User).filter(User.id == r.assigned_doctor_id).first()
        doctor_email = doctor.email if doctor else None
        analysis = r.analysis
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except Exception:
                analysis = {}
        patient_name = None
        try:
            patient_name = analysis.get("LabReportJSON", {}).get("demographics", {}).get("name")
        except Exception:
            patient_name = None
        results_list.append({
            "patient_id": r.patient_id,
            "assigned_doctor_email": doctor_email,
            "pdf_filename": r.pdf_filename,
            "patient_name": patient_name,
            "DoctorInterpretation": analysis.get("DoctorInterpretation"),
            "AutoReferralBlock": analysis.get("AutoReferralBlock"),
            "IntelligenceHubCard": analysis.get("IntelligenceHubCard"),
            "keyFindings": analysis.get("keyFindings"),
        })
    db.close()
    return JSONResponse(content=results_list)

@app.post("/upload-pdf/")
@app.post("/upload-pdf/")
async def upload_pdf(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    assigned_doctor_id: int = Form(...)
):
        # Validate patient_id is 10 digits
    if not (patient_id.isdigit() and len(patient_id) == 10):
        return JSONResponse(status_code=400, content={"error": "patient_id must be a 10-digit number."})

    db = SessionLocal()
    # Validate doctor exists
    doctor = db.query(User).filter(User.id == assigned_doctor_id).first()
    if not doctor:
        db.close()
        return JSONResponse(status_code=400, content={"error": "Assigned doctor not found."})

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
        patient_id=patient_id,
        assigned_doctor_id=assigned_doctor_id
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
@app.delete("/analysis-results/")
def delete_all_analysis_results():
    db = SessionLocal()
    try:
        num_deleted = db.query(AnalysisResult).delete()
        db.commit()
        return {"message": f"Deleted {num_deleted} analysis results."}
    finally:
        db.close()




def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@app.post("/register")
def register(email: str = Body(...), password: str = Body(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        db.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.close()
    return {"msg": "User registered successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(User).filter(User.email == form_data.username).first()
    db.close()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}