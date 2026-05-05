from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
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
    anno = Column(Integer, default=lambda: datetime.utcnow().year)
    
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

    tipo_factura = Column(String(5), default="F1")  # F1, F2, R1-R5
    tipo_rectificacion = Column(String(1))  # S=sustitución, I=diferencias
    motivo_rectificacion = Column(String(500))
    factura_origen_id = Column(Integer, ForeignKey("facturas.id"))
    
    verifactu_enviada = Column(Boolean, default=False)
    verifactu_fecha = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    cliente = relationship("Cliente", back_populates="facturas")
    factura_origen = relationship("Factura", remote_side=[id], uselist=False)
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
    ensure_schema_updates()


def ensure_schema_updates():
    """Migración ligera e idempotente para SQLite/SQLAlchemy sin Alembic."""
    inspector = inspect(engine)
    if "facturas" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("facturas")}
    columns = {
        "tipo_factura": "VARCHAR(5) DEFAULT 'F1'",
        "tipo_rectificacion": "VARCHAR(1)",
        "motivo_rectificacion": "VARCHAR(500)",
        "factura_origen_id": "INTEGER",
    }
    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE facturas ADD COLUMN {name} {ddl}"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
