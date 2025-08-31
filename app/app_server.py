from fastapi import FastAPI, File, UploadFile
from sqlalchemy import create_engine, Column, Integer, String, Text
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
        clinic = db.query(Clinic).filter(Clinic.uuid == clinic_uuid).first()
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
        clinic = db.query(Clinic).filter(Clinic.uuid == assigned_clinic_uuid).first()
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