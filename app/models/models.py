from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    nif = Column(String(20), unique=True, index=True)
    nombre = Column(String(200), nullable=False)
    razon_social = Column(String(200))
    domicilio = Column(String(500))
    codigo_postal = Column(String(10))
    ciudad = Column(String(100))
    provincia = Column(String(100))
    email = Column(String(200))
    telefono = Column(String(20))
    telefono_autorizado = Column(String(20), index=True)  # Teléfono autorizado para facturar
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    facturas = relationship("Factura", back_populates="cliente")

class Factura(Base):
    __tablename__ = "facturas"
    
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(20), index=True)
    serie = Column(String(10), default="FI")
    anno = Column(Integer, default=datetime.now().year)
    
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    
    fecha_emision = Column(DateTime, default=datetime.utcnow)
    fecha_operacion = Column(DateTime)
    
    base_imponible = Column(Float, default=0)
    iva_pct = Column(Float, default=21)
    iva_cuota = Column(Float, default=0)
    irpf_pct = Column(Float, default=0)
    irpf_cuota = Column(Float, default=0)
    total = Column(Float, default=0)
    
    estado = Column(String(20), default="borrador")
    pdf_path = Column(String(500))
    xml_path = Column(String(500))
    
    verifactu_enviada = Column(Boolean, default=False)
    verifactu_fecha = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    cliente = relationship("Cliente", back_populates="facturas")
    lineas = relationship("LineaFactura", back_populates="factura")

class LineaFactura(Base):
    __tablename__ = "lineas_factura"
    
    id = Column(Integer, primary_key=True, index=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"))
    
    numero_linea = Column(Integer)
    descripcion = Column(String(500))
    cantidad = Column(Float, default=1)
    precio_unitario = Column(Float)
    descuento_pct = Column(Float, default=0)
    base_imponible = Column(Float)
    iva_pct = Column(Float, default=21)
    iva_cuota = Column(Float, default=0)
    total = Column(Float)
    
    factura = relationship("Factura", back_populates="lineas")

class Configuracion(Base):
    __tablename__ = "configuracion"
    
    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(100), unique=True, index=True)
    valor = Column(String(500))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
