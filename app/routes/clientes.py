from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.models import get_db, Cliente
from app.services.auth import get_api_key
from pydantic import BaseModel, ConfigDict

router = APIRouter(dependencies=[Depends(get_api_key)])

class ClienteCreate(BaseModel):
    nif: str
    nombre: str
    razon_social: str = None
    domicilio: str = None
    codigo_postal: str = None
    ciudad: str = None
    provincia: str = None
    email: str = None
    telefono: str = None

class ClienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nif: str
    nombre: str
    email: str = None

@router.post("/", response_model=ClienteResponse)
def crear_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    """Crear un nuevo cliente"""
    db_cliente = Cliente(**cliente.dict())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

@router.get("/", response_model=list[ClienteResponse])
def listar_clientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Listar clientes"""
    return db.query(Cliente).offset(skip).limit(limit).all()

@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtener un cliente"""
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()
