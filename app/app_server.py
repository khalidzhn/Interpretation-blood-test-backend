from fastapi import FastAPI, File, UploadFile
from sqlalchemy import create_engine, Column, Integer, String, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Form
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
from enum import Enum
from sqlalchemy import Boolean
from typing import Optional, List


DATABASE_URL = os.getenv("postgresql+psycopg2://DB_dev:jdow!242F@database-1.c5mswemmu8to.us-west-2.rds.amazonaws.com:5432/database-1")
port = int(os.getenv("PORT", 8080))
engine = create_engine("postgresql+psycopg2://DB_dev:Ala.zoby!108@database-1.c5mswemmu8to.us-west-2.rds.amazonaws.com:5432/database-1")
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

# Configure CORS origins explicitly. When credentials are allowed,
# Access-Control-Allow-Origin must NOT be "*". Use the environment
# variable `ALLOWED_ORIGINS` to list comma-separated origins (for example:
# "http://localhost:3000,http://127.0.0.1:3000,http://interpretation-frontend-dev-bucket.s3-website-us-west-2.amazonaws.com").
allowed_origins_env = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://interpretation-frontend-dev-bucket.s3-website-us-west-2.amazonaws.com",
)
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows any domain
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],
)

class UserRole(str, Enum):
    admin = "admin"
    hospital_admin = "hospital_admin"
    clinic_admin = "clinic_admin"
    doctor = "doctor"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)  
    title = Column(String, nullable=True) 
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=True)  
    clinic = relationship("Clinic", back_populates="users")
    role = Column(String, nullable=False, default="doctor") 
    clinic = relationship("Clinic", back_populates="users")
    is_active = Column(Boolean, nullable=False, default=True)  # <-- Use Boolean for status

import requests

def get_access_token(client_id, client_secret, token_url):
    data = {
        'grant_type': 'client_credentials',
        'client_id': 'a5d28321-20bd-4479-81ee-80ee4066e415',
        'client_secret': 'UTCSecret6eTUOTGAHkN46ZOgIsQVH4UvnXjoA-xF',
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()['access_token']

def get_patient_data(fhir_base_url, access_token, patient_id):
    headers = {"Accept": "application/fhir+json"}
    url = f"https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Observation?patient=12724066"
    response = requests.get(url, headers=headers)
    print("Request URL:", url)
    print("Response Status:", response.status_code)
    print("Response Content:", response.text)
    response.raise_for_status()
    return response.json()

def get_lab_results(fhir_base_url, access_token, patient_id):
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f"{fhir_base_url}/Observation?patient={patient_id}&category=laboratory"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


@app.get("/oracle/patient/{patient_id}")
def fetch_oracle_patient(patient_id: str):
    get_patient_data('https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d', 'your_access_token', patient_id)
   
   
    return {"msg": "Fetched and stored patient data"}


def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String, unique=True, nullable=False)
    max_users = Column(Integer, nullable=False)
    max_reports = Column(Integer, nullable=False)
    clinic = relationship("Clinic", uselist=False, back_populates="hospital")

class Clinic(Base):
    __tablename__ = "clinics"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String, nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    hospital = relationship("Hospital", back_populates="clinic")
    users = relationship("User", back_populates="clinic")

def remove_patient_id_unique_constraint():
    """Remove unique constraint from patient_id column"""
    try:
        with engine.connect() as connection:
            # Drop the unique constraint
            connection.execute(text("ALTER TABLE analysis_results DROP CONSTRAINT IF EXISTS ix_analysis_results_patient_id;"))
            # Recreate as regular index (not unique)
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_analysis_results_patient_id ON analysis_results (patient_id);"))
            connection.commit()
            print("✅ Removed unique constraint from patient_id")
    except Exception as e:
        print(f"Error removing constraint: {e}")

# Call this after Base.metadata.create_all(bind=engine)
Base.metadata.create_all(bind=engine)
remove_patient_id_unique_constraint()

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True, index=True)
    pdf_filename = Column(String, nullable=False)
    raw_data = Column(Text, nullable=False)
    analysis = Column(JSON, nullable=False)
    patient_id = Column(String(10),  index=True, nullable=False)  # 10-digit patient ID
    #assigned_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    #assigned_doctor = relationship("User")
    
Base.metadata.create_all(bind=engine)
@app.get("/")
def read_root():
    return {"status": "ok"}
@app.get("/analysis-results/", dependencies=[Depends(get_current_user)])
@app.get("/analysis-results", dependencies=[Depends(get_current_user)])
def get_all_analysis_results(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    
    # if current_user.role == UserRole.admin:
    results = db.query(AnalysisResult).order_by(desc(AnalysisResult.id)).limit(10).all()
    # else:
    #     results = db.query(AnalysisResult).filter(
    #         AnalysisResult.assigned_doctor_id == current_user.id
    #     ).order_by(desc(AnalysisResult.id)).limit(10).all()
    
    results_list = []
    for r in results:
        # doctor = db.query(User).filter(User.id == r.assigned_doctor_id).first()
        doctor_email = None
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
            "assigned_doctor_email": None,  # Temporarily None
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

    key = information.CONFIG(information.CONFIG_YML).get("poe").get("key")
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
        #assigned_doctor_id=assigned_doctor_id
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    db.close()
    print("Saved to DB.")
    return {"message": "PDF processed and data stored.", "id": db_result.id}


@app.post("/filter-excel/")
async def filter_excel(file: UploadFile = File(...)):
    """Accept an Excel file, apply column filters, and write filtered-in and filtered-out records
    into the `.result` directory as separate .txt files. Returns counts and file paths.
    """
    import pandas as pd
    from pathlib import Path

    # Ensure result directory
    result_dir = Path(".result")
    result_dir.mkdir(parents=True, exist_ok=True)

    # Read uploaded file into a DataFrame
    contents = await file.read()
    try:
        df = pd.read_excel(contents, engine="openpyxl")
    except Exception:
        # fallback: try reading from bytes via BytesIO
        from io import BytesIO
        df = pd.read_excel(BytesIO(contents), engine="openpyxl")

    # Columns and filter logic
    group1 = [
        "Local_Hom", "Local_Het", "AC", "AC_hom", "ExAC_AC", "Kaviar_AC",
    ]

    group2 = [
        "1000g2015aug_all", "LocalFreq", "NHLBI ESP AF", "ExAC_ALL", "GME_AF",
        "gnomAD_exome_AF", "gnomAD_genome_ALL", "Kaviar_AF",
    ]

    allowed_refgene = {"exonic", "exonic;splicing", "splicing"}

    def find_column(df, name):
        for c in df.columns:
            if c == name:
                return c
        lname = name.lower()
        for c in df.columns:
            if str(c).lower() == lname:
                return c
        return None

    # Map requested names to actual columns or None
    g1_cols_map = {c: find_column(df, c) for c in group1}
    g2_cols_map = {c: find_column(df, c) for c in group2}
    # additional annotation columns we will use
    sift_col = find_column(df, "SIFT_score") or find_column(df, "SIFT")
    polyphen_col = find_column(df, "Polyphen2_HDIV_score") or find_column(df, "Polyphen2") or find_column(df, "PolyPhen2_HDIV_score")
    cadd_col = find_column(df, "CADD_phred_41a") or find_column(df, "CADD_phred") or find_column(df, "CADD_phred_41")
    # two refGene-related columns: high-level function and exonic-specific function
    ref_col = find_column(df, "refGene") or find_column(df, "refGene function") or find_column(df, "refgene")
    exonic_func_col = find_column(df, "refGene exonic function") or find_column(df, "refGene_exonic_function") or find_column(df, "refgene exonic function")

    # Track completely missing expected columns (for appending to filtered_in file)
    missing_columns = [name for name, col in {**g1_cols_map, **g2_cols_map}.items() if col is None]
    if ref_col is None:
        missing_columns.append("refGene")

    # Prepare working dataframe with reason columns
    df_work = df.copy()
    df_work["MissingFields"] = ""
    df_work["FilterReasons"] = ""
    # Also track a column for rule-based forced inclusion
    df_work["ForceIncludeReason"] = ""

    # Evaluate row-by-row so we can record missing values vs failing checks
    for idx in df_work.index:
        missing = []
        reasons = []

        # Group1 checks: > 5
        for logical_name, col in g1_cols_map.items():
            if col is None:
                # column missing entirely; don't mark per-row missing here (global list added later)
                continue
            val = df_work.at[idx, col]
            if pd.isna(val) or (str(val).strip() == ""):
                missing.append(col)
            else:
                try:
                    num = float(val)
                except Exception:
                    missing.append(col)
                    num = None
                if num is not None and not (num > 5):
                    reasons.append(f"{col}<=5")

        # Group2 checks: > 0.001
        for logical_name, col in g2_cols_map.items():
            if col is None:
                continue
            val = df_work.at[idx, col]
            if pd.isna(val) or (str(val).strip() == ""):
                missing.append(col)
            else:
                try:
                    num = float(val)
                except Exception:
                    missing.append(col)
                    num = None
                if num is not None and not (num > 0.001):
                    reasons.append(f"{col}<=0.001")

        # refGene check - apply ONLY after group1/group2 checks (initial filtering)
        variant_match = False
        variant_reasons = []
        if ref_col is not None:
            val = df_work.at[idx, ref_col]
            if pd.isna(val) or (str(val).strip() == ""):
                missing.append(ref_col)
                # if missing high-level ref, treat as not allowed (record reason)
                reasons.append(f"{ref_col}=MISSING")
            else:
                txt = str(val).lower().strip()
                # If high-level function not in allowed set, record reason now (this is part of initial filtering)
                if txt not in allowed_refgene:
                    reasons.append(f"{ref_col}={val}")

                # Only evaluate variant-specific rules if the row passed group1/group2 and high-level allowed_refgene
                initial_pass = len(reasons) == 0
                if initial_pass:
                    # exonic-specific text
                    exonic_txt = None
                    if exonic_func_col is not None:
                        ex_val = df_work.at[idx, exonic_func_col]
                        if not (pd.isna(ex_val) or str(ex_val).strip() == ""):
                            exonic_txt = str(ex_val).lower().strip()
                        else:
                            # missing exonic-specific annotation shouldn't auto-filter; flag it
                            missing.append(exonic_func_col)

                    # Rule 1: exonic or exonic;splicing and exonic function contains frameshift or nonsynonymous
                    if txt in {"exonic", "exonic;splicing"} and exonic_txt and ("frameshift" in exonic_txt or "nonsynonymous" in exonic_txt):
                        variant_match = True
                        variant_reasons.append("exonic_frameshift_or_nonsynonymous")

                    # Rule 2: synonymous SNV in exonic function -> check SIFT/PolyPhen/CADD
                    if exonic_txt and "synonymous" in exonic_txt:
                        s_val = None
                        p_val = None
                        c_val = None
                        if sift_col is not None:
                            try:
                                s_val = float(df_work.at[idx, sift_col])
                            except Exception:
                                missing.append(sift_col)
                        if polyphen_col is not None:
                            try:
                                p_val = float(df_work.at[idx, polyphen_col])
                            except Exception:
                                missing.append(polyphen_col)
                        if cadd_col is not None:
                            try:
                                c_val = float(df_work.at[idx, cadd_col])
                            except Exception:
                                missing.append(cadd_col)
                        if (s_val is not None and s_val < 0.5) or (p_val is not None and p_val >= 0.5) or (c_val is not None and c_val > 20):
                            variant_match = True
                            variant_reasons.append("synonymous_predicted_damaging_or_CADD")

                    # Rule 3: splicing or exonic;splicing -> check SIFT >= 0.5
                    if "splicing" in txt:
                        s_val = None
                        if sift_col is not None:
                            try:
                                s_val = float(df_work.at[idx, sift_col])
                            except Exception:
                                missing.append(sift_col)
                        if s_val is not None and s_val >= 0.5:
                            variant_match = True
                            variant_reasons.append("splicing_sift_high")

                    # If initial passed but no variant rule matched, mark as failing variant-level filter
                    if not variant_match:
                        reasons.append("refGene_rules_not_met")
                    else:
                        # record variant match reasons into ForceIncludeReason for output
                        df_work.at[idx, "ForceIncludeReason"] = ";".join(sorted(set(variant_reasons)))

        df_work.at[idx, "MissingFields"] = ";".join(sorted(set(missing)))
        df_work.at[idx, "FilterReasons"] = ";".join(sorted(set(reasons)))
        # If ForceIncludeReason present, clear FilterReasons so row is included (and ForceIncludeReason will be written to output)
        if df_work.at[idx, "ForceIncludeReason"]:
            df_work.at[idx, "FilterReasons"] = ""

    # Rows with any FilterReasons are filtered out; rows with no reasons are filtered in
    mask_in = df_work["FilterReasons"].astype(str) == ""
    df_in = df_work[mask_in].copy()
    df_out = df_work[~mask_in].copy()

    # Helper to stringify rows
    def rows_to_txt_with_reasons(df_rows: pd.DataFrame) -> str:
        if df_rows.empty:
            return ""
        # include MissingFields and FilterReasons columns in output
        return df_rows.to_csv(sep="\t", index=False)

    in_path = result_dir / f"{Path(file.filename).stem}_filtered_in.txt"
    out_path = result_dir / f"{Path(file.filename).stem}_filtered_out.txt"

    # Write filtered-in rows
    content_in = rows_to_txt_with_reasons(df_in)
    if missing_columns:
        content_in += "\n\nMissing columns in uploaded file: " + ", ".join(sorted(set(missing_columns))) + "\n"
    in_path.write_text(content_in, encoding="utf-8")

    # Write filtered-out rows (with FilterReasons appended as a column)
    content_out = rows_to_txt_with_reasons(df_out)
    # Additionally, for clarity append a short footer describing why rows were filtered
    out_path.write_text(content_out, encoding="utf-8")

    return {
        "filtered_in_count": len(df_in),
        "filtered_out_count": len(df_out),
        "filtered_in_path": str(in_path),
        "filtered_out_path": str(out_path),
    }


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
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=2000))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/admin-register")
def admin_register(
    email: str = Body(...),
    password: str = Body(...),
    role: str = Body("doctor"),
    full_name: str = Body(None),
    title: str = Body(None),
    clinic_uuid: str = Body(None),
    is_active: bool = Body(True)
):
    db = SessionLocal()
    
    clinic_id = None
    if clinic_uuid:
        try:
            parsed_clinic_uuid = uuid.UUID(clinic_uuid)
        except (ValueError, TypeError):
            db.close()
            raise HTTPException(status_code=400, detail="Invalid clinic_uuid format")
        clinic = db.query(Clinic).filter(Clinic.uuid == parsed_clinic_uuid).first()
        if clinic:
            clinic_id = clinic.id
    
    hashed_password = get_password_hash(password)
    
    new_user = User(
        email=email,
        hashed_password=hashed_password,
        role=role,
        full_name=full_name,
        title=title,
        clinic_id=clinic_id,
        is_active=is_active
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    user_uuid = str(new_user.uuid)
    user_id = new_user.id
    
    db.close()
    
    return {
        "msg": "User created successfully",
        "user": {
            "id": user_id,
            "uuid": user_uuid,
            "email": email,
            "role": role,
            "full_name": full_name,
            "title": title,
            "is_active": is_active
        }
    }


@app.post("/register")
def register(email: str = Body(...), password: str = Body(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="No invitation found for this email")
    if user.is_active:
        db.close()
        raise HTTPException(status_code=400, detail="User already registered and active")
    hashed_password = get_password_hash(password)
    user.hashed_password = hashed_password
    user.is_active = True
    db.commit()
    db.close()
    return {"msg": "User registered and activated successfully"}


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        db.close()
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    # Get related clinic and hospital IDs (if any)
    clinic_id = user.clinic_id
    hospital_id = None
    if user.clinic and user.clinic.hospital_id:
        hospital_id = user.clinic.hospital_id
    # Add role, email, clinic_id, hospital_id to token
    access_token = create_access_token(data={
        "sub": user.email,
        "role": user.role,
        "clinic_id": clinic_id,
        "hospital_id": hospital_id,
        "full_name": user.full_name,
        "title": user.title
    })
    db.close()
    return {"access_token": access_token, "token_type": "bearer"}
from fastapi import Query



@app.post("/invite")
def invite_user(
    email: str = Body(...),
    role: str = Body(...),
    assigned_hospital_uuid: str = Body(None),
    assigned_clinic_uuid: str = Body(None)
):
    db = SessionLocal()
    # Check if user already exists
    user = db.query(User).filter(User.email == email).first()
    if user:
        db.close()
        raise HTTPException(status_code=400, detail="Email already invited or registered")
    clinic_id = None
    if assigned_clinic_uuid:
        try:
            parsed_assigned_clinic_uuid = uuid.UUID(assigned_clinic_uuid)
        except (ValueError, TypeError):
            db.close()
            raise HTTPException(status_code=400, detail="Invalid assigned_clinic_uuid format")
        clinic = db.query(Clinic).filter(Clinic.uuid == parsed_assigned_clinic_uuid).first()
        if not clinic:
            db.close()
            raise HTTPException(status_code=404, detail="Clinic not found")
        clinic_id = clinic.id
    # (Optional) You can also check hospital UUID if needed
    new_user = User(
        email=email,
        hashed_password="",  # No password yet, will be set on registration
        role=role,
        is_active=False,
        clinic_id=clinic_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    user_uuid = str(new_user.uuid)
    db.close()
    return {
        "msg": "Invitation created. Email will be sent to complete registration.",
        "id": user_uuid
    }

@app.get("/users/", dependencies=[Depends(get_current_user)])
def list_users(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    users_query = db.query(User)
    # Admin: see all users
    if current_user.role == UserRole.admin:
        users = users_query.all()
    # Hospital admin: users in clinics of their hospital
    elif current_user.role == UserRole.hospital_admin:
        if not current_user.clinic or not current_user.clinic.hospital_id:
            db.close()
            return []
        hospital_id = current_user.clinic.hospital_id
        clinic_ids = [c.id for c in db.query(Clinic).filter(Clinic.hospital_id == hospital_id).all()]
        users = users_query.filter(User.clinic_id.in_(clinic_ids)).all()
    # Clinic admin: users in their clinic
    elif current_user.role == UserRole.clinic_admin:
        if not current_user.clinic_id:
            db.close()
            return []
        users = users_query.filter(User.clinic_id == current_user.clinic_id).all()
    # Doctor: cannot see users
    else:
        db.close()
        raise HTTPException(status_code=403, detail="Doctors cannot view users list")

    result = []
    for u in users:
        clinic_name = u.clinic.name if u.clinic else "-"
        hospital_name = u.clinic.hospital.name if u.clinic and u.clinic.hospital else "-"
        result.append({
            "id": u.id,
            "uuid": str(u.uuid),
            "email": u.email,
            "role": u.role,
            "clinic": clinic_name,
            "hospital": hospital_name,
            "is_active": u.is_active
        })
    db.close()
    return result
from fastapi import Path

@app.patch("/users/{user_id}", dependencies=[Depends(get_current_user)])
def toggle_user_active(
    user_id: str = Path(...),  # Accept UUID as string
):
    db = SessionLocal()
    user = db.query(User).filter(User.uuid == user_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="User not found")
    # Toggle is_active status
    user.is_active = not user.is_active
    db.commit()
    is_active = user.is_active
    db.close()
    return {"id": user_id, "active": is_active}
@app.post("/hospitals/", dependencies=[Depends(get_current_user)])
def create_hospital(
    name: str = Body(...),
    max_users: int = Body(...),
    clinics: Optional[List[str]] = Body(None)
):
    db = SessionLocal()
    # Check if hospital name already exists
    existing = db.query(Hospital).filter(Hospital.name == name).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Hospital name already exists")
    # Create hospital
    new_hospital = Hospital(
        name=name,
        max_users=max_users,
        max_reports=0  # or set a default or accept as input
    )
    db.add(new_hospital)
    db.flush()  # Get new_hospital.id before adding clinics

    created_clinics = []
    if clinics:
        for clinic_name in clinics:
            new_clinic = Clinic(
                name=clinic_name,
                hospital_id=new_hospital.id
            )
            db.add(new_clinic)
            db.flush()
            created_clinics.append({
                "uuid": str(new_clinic.uuid),
                "name": new_clinic.name
            })
    db.commit()
    # Read attributes before closing session
    hospital_id = new_hospital.id
    hospital_uuid = str(new_hospital.uuid)
    hospital_name = new_hospital.name
    hospital_max_users = new_hospital.max_users
    db.close()
    return {
        "msg": "Hospital created successfully",
        "hospital": {
            "id": hospital_id,
            "uuid": hospital_uuid,
            "name": hospital_name,
            "max_users": hospital_max_users
        },
        "clinics": created_clinics
    }


@app.get("/hospitals/", dependencies=[Depends(get_current_user)])
def list_hospitals():
    db = SessionLocal()
    hospitals = db.query(Hospital).all()
    result = []
    for h in hospitals:
        clinics = db.query(Clinic).filter(Clinic.hospital_id == h.id).all()
        # Get all clinic ids for this hospital
        clinic_ids = [c.id for c in clinics]
        # Count users in all clinics of this hospital
        num_users = db.query(User).filter(User.clinic_id.in_(clinic_ids)).count() if clinic_ids else 0
        result.append({
            "id": h.id,
            "name": h.name,
            "uuid": str(h.uuid),
            "max_users": h.max_users,
            "max_reports": h.max_reports,
            "num_users": num_users,  # <-- Add this line
            "clinics": [
                {
                    "id": c.id,
                    "name": c.name,
                    "uuid": str(c.uuid)
                } for c in clinics
            ]
        })
    db.close()
    return result

@app.post("/clinics/", dependencies=[Depends(get_current_user)])
def add_clinics(
    hospital_uuid: str = Body(...),
    clinics: Optional[List[str]] = Body(None),
    max_users: int = Body(None)
):
    db = SessionLocal()
    hospital = db.query(Hospital).filter(Hospital.uuid == hospital_uuid).first()
    if not hospital:
        db.close()
        raise HTTPException(status_code=404, detail="Hospital not found")
    created_clinics = []
    if clinics:
        for clinic_name in clinics:
            new_clinic = Clinic(
                name=clinic_name,
                hospital_id=hospital.id
            )
            db.add(new_clinic)
            db.flush()
            created_clinics.append({
                "uuid": str(new_clinic.uuid),
                "name": new_clinic.name
            })
    if max_users is not None:
        hospital.max_users = max_users
    db.commit()
    db.close()
    return {
        "msg": "Clinics created successfully" if created_clinics else "No clinics added",
        "clinics": created_clinics
    }