from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import uuid
import hashlib
import jwt
from datetime import datetime, timedelta
import qrcode
import io
import base64
from motor.motor_asyncio import AsyncIOMotorClient
import os
from contextlib import asynccontextmanager

# Environment variables
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "cashless_system")
SECRET_KEY = "cashless-secret-key-2025"

# Database
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Cashless System...")
    print(f"📊 Database: {DB_NAME}")
    print(f"🔗 MongoDB: {MONGO_URL}")
    yield
    # Shutdown
    print("🛑 Shutting down Cashless System...")

app = FastAPI(title="Sistema Cashless", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class User(BaseModel):
    id: str
    email: str
    name: str
    balance: float
    nfc_id: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    name: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Transaction(BaseModel):
    id: str
    from_user: str
    to_user: str
    amount: float
    description: str
    timestamp: datetime
    type: str  # 'nfc', 'qr', 'transfer'

class PaymentRequest(BaseModel):
    to_user: str
    amount: float
    description: str
    method: str  # 'nfc', 'qr', 'transfer'

class RechargeRequest(BaseModel):
    amount: float

class NFCRegister(BaseModel):
    nfc_id: str

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = decode_token(credentials.credentials)
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return User(**user)

def generate_qr_code(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()

# Routes
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Sistema Cashless funcionando!"}

@app.post("/api/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já está em uso")
    
    # Create user
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password": hash_password(user_data.password),
        "balance": 0.0,
        "nfc_id": None,
        "created_at": datetime.utcnow()
    }
    
    await db.users.insert_one(user)
    
    # Generate token
    token = create_token(user_id)
    
    return {
        "message": "Usuário criado com sucesso",
        "token": token,
        "user": {
            "id": user_id,
            "email": user_data.email,
            "name": user_data.name,
            "balance": 0.0,
            "nfc_id": None
        }
    }

@app.post("/api/login")
async def login(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    
    token = create_token(user["id"])
    
    return {
        "message": "Login realizado com sucesso",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "balance": user["balance"],
            "nfc_id": user.get("nfc_id")
        }
    }

@app.get("/api/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/api/recharge")
async def recharge_balance(
    recharge_data: RechargeRequest, 
    current_user: User = Depends(get_current_user)
):
    if recharge_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser positivo")
    
    # Update user balance
    new_balance = current_user.balance + recharge_data.amount
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"balance": new_balance}}
    )
    
    # Create transaction record
    transaction = {
        "id": str(uuid.uuid4()),
        "from_user": "system",
        "to_user": current_user.id,
        "amount": recharge_data.amount,
        "description": "Recarga de saldo",
        "timestamp": datetime.utcnow(),
        "type": "recharge"
    }
    await db.transactions.insert_one(transaction)
    
    return {
        "message": "Recarga realizada com sucesso",
        "new_balance": new_balance,
        "transaction_id": transaction["id"]
    }

@app.post("/api/register-nfc")
async def register_nfc(
    nfc_data: NFCRegister,
    current_user: User = Depends(get_current_user)
):
    # Check if NFC ID is already in use
    existing_nfc = await db.users.find_one({"nfc_id": nfc_data.nfc_id})
    if existing_nfc and existing_nfc["id"] != current_user.id:
        raise HTTPException(status_code=400, detail="NFC ID já está em uso")
    
    # Update user with NFC ID
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"nfc_id": nfc_data.nfc_id}}
    )
    
    return {
        "message": "NFC registrado com sucesso",
        "nfc_id": nfc_data.nfc_id
    }

@app.get("/api/generate-qr")
async def generate_payment_qr(current_user: User = Depends(get_current_user)):
    # Generate QR code data
    qr_data = {
        "user_id": current_user.id,
        "name": current_user.name,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    qr_string = f"cashless:{current_user.id}:{current_user.name}"
    qr_image = generate_qr_code(qr_string)
    
    return {
        "qr_data": qr_string,
        "qr_image": qr_image,
        "user_name": current_user.name
    }

@app.post("/api/pay")
async def make_payment(
    payment_data: PaymentRequest,
    current_user: User = Depends(get_current_user)
):
    if payment_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser positivo")
    
    if current_user.balance < payment_data.amount:
        raise HTTPException(status_code=400, detail="Saldo insuficiente")
    
    # Find recipient
    recipient = await db.users.find_one({"id": payment_data.to_user})
    if not recipient:
        raise HTTPException(status_code=404, detail="Usuário destinatário não encontrado")
    
    if current_user.id == payment_data.to_user:
        raise HTTPException(status_code=400, detail="Não é possível transferir para si mesmo")
    
    # Process payment
    new_sender_balance = current_user.balance - payment_data.amount
    new_recipient_balance = recipient["balance"] + payment_data.amount
    
    # Update balances
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"balance": new_sender_balance}}
    )
    
    await db.users.update_one(
        {"id": payment_data.to_user},
        {"$set": {"balance": new_recipient_balance}}
    )
    
    # Create transaction record
    transaction = {
        "id": str(uuid.uuid4()),
        "from_user": current_user.id,
        "to_user": payment_data.to_user,
        "amount": payment_data.amount,
        "description": payment_data.description,
        "timestamp": datetime.utcnow(),
        "type": payment_data.method
    }
    await db.transactions.insert_one(transaction)
    
    return {
        "message": "Pagamento realizado com sucesso",
        "transaction_id": transaction["id"],
        "new_balance": new_sender_balance,
        "recipient": recipient["name"]
    }

@app.get("/api/pay-by-nfc/{nfc_id}")
async def get_user_by_nfc(nfc_id: str):
    user = await db.users.find_one({"nfc_id": nfc_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário NFC não encontrado")
    
    return {
        "user_id": user["id"],
        "name": user["name"],
        "nfc_id": user["nfc_id"]
    }

@app.get("/api/transactions")
async def get_transactions(current_user: User = Depends(get_current_user)):
    transactions = await db.transactions.find({
        "$or": [
            {"from_user": current_user.id},
            {"to_user": current_user.id}
        ]
    }).sort("timestamp", -1).limit(50).to_list(length=50)
    
    # Get user names for transactions
    for transaction in transactions:
        if transaction["from_user"] == "system":
            transaction["from_name"] = "Sistema"
        else:
            from_user = await db.users.find_one({"id": transaction["from_user"]})
            transaction["from_name"] = from_user["name"] if from_user else "Usuário"
        
        to_user = await db.users.find_one({"id": transaction["to_user"]})
        transaction["to_name"] = to_user["name"] if to_user else "Usuário"
    
    return transactions

@app.get("/api/users/search")
async def search_users(q: str, current_user: User = Depends(get_current_user)):
    if len(q) < 2:
        return []
    
    users = await db.users.find({
        "$and": [
            {"id": {"$ne": current_user.id}},
            {
                "$or": [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"email": {"$regex": q, "$options": "i"}}
                ]
            }
        ]
    }).limit(10).to_list(length=10)
    
    return [
        {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
        for user in users
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)