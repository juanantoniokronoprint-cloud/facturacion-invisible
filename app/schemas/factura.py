from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TipoIVA(str, Enum):
    GENERAL = "21"      # 21% - Tipo general
    REDUCIDO = "10"     # 10% - Reducido (alimentación, transporte)
    SUPERREDUCIDO = "4" # 4% - Superreducido (medicamentos, libros)


class TipoIRPF(str, Enum):
    AUTONOMO = "15"     # 15% - Autónomo estándar
    SIN_RETENCION = "0" # 0% - Sin retención


class TipoCliente(str, Enum):
    AUTONOMO = "autonomo"
    SL = "sl"           # Sociedad Limitada
    SA = "sa"           # Sociedad Anónima
    PARTICULAR = "particular"


class LineaFacturaCreate(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=500)
    cantidad: float = Field(..., gt=0)
    precio_unitario: float = Field(..., ge=0)
    descuento_pct: float = Field(default=0, ge=0, le=100)
    iva_pct: float = Field(default=21, ge=0, le=100)
    es_servicio: bool = Field(default=False)

    @field_validator('cantidad', 'precio_unitario')
    @classmethod
    def validate_positivos(cls, v):
        if v <= 0:
            raise ValueError('El valor debe ser mayor que 0')
        return round(v, 2)


class LineaFacturaResponse(LineaFacturaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_linea: int
    base_imponible: float
    iva_cuota: float
    total: float
    created_at: Optional[datetime] = None


class CalculoFiscal(BaseModel):
    """Resultado de los cálculos fiscales de una factura"""
    base_imponible: float
    iva_cuota: float
    irpf_cuota: float
    total: float
    tipo_iva: str
    tipo_irpf: str
    tipo_cliente: str
    
    # Detalle por líneas
    lineas_base: float
    lineas_iva: float
    
    # Descuentos
    descuento_total: float
    
    # Notas
    notas: List[str] = []


class FacturaCreate(BaseModel):
    """Schema para crear una factura"""
    cliente_nif: str = Field(..., min_length=5, max_length=20)
    cliente_nombre: str = Field(..., min_length=1, max_length=200)
    
    # Datos opcionales del cliente
    cliente_domicilio: Optional[str] = None
    cliente_cp: Optional[str] = None
    cliente_ciudad: Optional[str] = None
    cliente_provincia: Optional[str] = None
    
    # Tipo de cliente para calcular retenciones
    tipo_cliente: TipoCliente = Field(default=TipoCliente.AUTONOMO)
    
    # Líneas de factura
    lineas: List[LineaFacturaCreate] = Field(..., min_length=1)
    
    # Fecha de operación (opcional, por defecto hoy)
    fecha_operacion: Optional[datetime] = None
    
    # Observaciones
    observaciones: Optional[str] = None
    
    # Forzar tipos específicos (override)
    iva_pct: float = Field(default=21, ge=0, le=100)
    irpf_pct: Optional[float] = None  # None = auto-detectar

    @field_validator('cliente_nif')
    @classmethod
    def validate_nif(cls, v):
        v = v.upper().strip()
        if not v:
            raise ValueError('El NIF no puede estar vacío')
        return v


class FacturaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    serie: str
    anno: int
    cliente_nif: str
    cliente_nombre: str
    fecha_emision: datetime
    fecha_operacion: Optional[datetime] = None
    
    base_imponible: float
    iva_pct: float
    iva_cuota: float
    irpf_pct: float
    irpf_cuota: float
    total: float
    
    estado: str
    verifactu_enviada: bool
    
    lineas: List[LineaFacturaResponse] = []
    
    observaciones: Optional[str] = None
    created_at: Optional[datetime] = None
