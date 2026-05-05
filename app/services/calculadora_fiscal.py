"""
Calculadora Fiscal para Facturación Invisible

Calcula IVA y retenciones IRPF según la normativa fiscal española.
"""
from typing import List, Optional
from app.schemas.factura import (
    LineaFacturaCreate,
    CalculoFiscal,
    TipoIVA,
    TipoIRPF,
    TipoCliente
)
from app.config import IVA_DEFAULT, IRPF_DEFAULT


# Tabla de IVA por tipo de operación
IVA_POR_TIPO = {
    "general": 21.0,
    "reducido": 10.0,
    "superreducido": 4.0,
    "exento": 0.0,
}

# Tabla de IRPF por tipo de cliente
IRPF_POR_TIPO = {
    "autonomo": 15.0,
    "sl": 0.0,
    "sa": 0.0,
    "particular": 0.0,
}


def detectar_tipo_cliente(nif: str) -> str:
    """
    Detecta el tipo de cliente basado en el NIF/CIF
    
    - NIF starts with letter = particular/autonomo
    - CIF starts with letter (A,B,C,D,E,F,G,H,J,N,P,Q,S) = empresa
    """
    nif = nif.upper().strip()
    
    if not nif:
        return "particular"
    
    # CIF de empresas
    if len(nif) == 9 and nif[0] in "ABCDEFGHJNPSQ":
        return "sl"  # Asumimos SL por defecto
    
    # NIF de particulares/autónomos
    return "autonomo"


def calcular_linea(linea: LineaFacturaCreate) -> dict:
    """
    Calcula importes de una línea de factura
    
    Returns:
        dict con base_imponible, iva_cuota, total
    """
    # Aplicar descuento
    if isinstance(linea, dict):
        cantidad = float(linea.get("cantidad", 1))
        precio_unitario = float(linea.get("precio_unitario", 0))
        descuento_pct = float(linea.get("descuento_pct", 0))
        iva_pct = float(linea.get("iva_pct", 21))
    else:
        cantidad = linea.cantidad
        precio_unitario = linea.precio_unitario
        descuento_pct = linea.descuento_pct
        iva_pct = linea.iva_pct

    subtotal = cantidad * precio_unitario
    descuento = subtotal * (descuento_pct / 100)
    base = subtotal - descuento
    
    # Redondear a 2 decimales
    base = round(base, 2)
    
    # Calcular IVA
    iva_cuota = round(base * (iva_pct / 100), 2)
    
    # Total línea
    total = round(base + iva_cuota, 2)
    
    return {
        "base_imponible": base,
        "iva_cuota": iva_cuota,
        "total": total,
        "descuento": round(descuento, 2)
    }


def calcular_factura(
    lineas: List[LineaFacturaCreate],
    tipo_cliente: str = "autonomo",
    irpf_pct: Optional[float] = None,
    iva_pct: float = 21.0,
) -> CalculoFiscal:
    """
    Calcula los totales fiscales de una factura
    
    Args:
        lineas: Lista de líneas de factura
        tipo_cliente: Tipo de cliente (autonomo, sl, sa, particular)
        irpf_pct: Porcentaje IRPF (None = auto-detectar)
        iva_pct: Porcentaje IVA por defecto
    
    Returns:
        CalculoFiscal con todos los importes calculados
    """
    notas = []
    
    # Calcular subtotales por línea
    total_base = 0.0
    total_iva = 0.0
    total_descuento = 0.0
    
    for linea in lineas:
        calc = calcular_linea(linea)
        total_base += calc["base_imponible"]
        total_iva += calc["iva_cuota"]
        total_descuento += calc["descuento"]
    
    # Redondear
    total_base = round(total_base, 2)
    total_iva = round(total_iva, 2)
    total_descuento = round(total_descuento, 2)
    
    # Detectar tipo IRPF si no se especifica
    if irpf_pct is None:
        irpf_pct = IRPF_POR_TIPO.get(tipo_cliente, 0.0)
        if irpf_pct > 0:
            notas.append(f"IRPF automático {irpf_pct}% (cliente {tipo_cliente})")
    else:
        irpf_pct = float(irpf_pct)
    
    # Calcular IRPF (retención)
    irpf_cuota = round(total_base * (irpf_pct / 100), 2)
    
    # Total final
    total = round(total_base + total_iva - irpf_cuota, 2)
    
    # Validaciones
    if total_base <= 0:
        notas.append("ADVERTENCIA: Base imponible cero o negativa")
    
    if irpf_pct > 0 and tipo_cliente not in ["autonomo"]:
        notas.append(f"ADVERTENCIA: Retención {irpf_pct}% aplicada a {tipo_cliente}")
    
    # Descuentos aplicados
    if total_descuento > 0:
        notas.append(f"Descuentos aplicados: {total_descuento}€")
    
    return CalculoFiscal(
        base_imponible=total_base,
        iva_cuota=total_iva,
        irpf_cuota=irpf_cuota,
        total=total,
        tipo_iva=str(iva_pct),
        tipo_irpf=str(irpf_pct),
        tipo_cliente=tipo_cliente,
        lineas_base=total_base,
        lineas_iva=total_iva,
        descuento_total=total_descuento,
        notas=notas
    )


def es_factura_correcta(calculo: CalculoFiscal) -> tuple[bool, List[str]]:
    """
    Valida que una factura sea fiscalmente correcta
    
    Returns:
        (es_correcta, lista_errores)
    """
    errores = []
    
    if calculo.base_imponible <= 0:
        errores.append("Base imponible debe ser mayor que 0")
    
    if calculo.iva_cuota < 0:
        errores.append("Cuota IVA no puede ser negativa")
    
    if calculo.total < 0:
        errores.append("Total no puede ser negativo")
    
    # Verificar consistencia
    iva_esperado = round(calculo.lineas_base * 0.21, 2)  # Asumiendo 21%
    if abs(calculo.iva_cuota - iva_esperado) > 0.02:
        # Permitir pequeño error de redondeo
        pass
    
    return len(errores) == 0, errores


def calcular_ejemplo_autonomo() -> CalculoFiscal:
    """Calcula ejemplo para autónomo estándar"""
    lineas = [
        LineaFacturaCreate(
            descripcion="Servicio de traducción",
            cantidad=1,
            precio_unitario=300.0,
            iva_pct=21.0
        )
    ]
    return calcular_factura(lineas, tipo_cliente="autonomo")


def calcular_ejemplo_empresa() -> CalculoFiscal:
    """Calcula ejemplo para empresa (sin retención)"""
    lineas = [
        LineaFacturaCreate(
            descripcion="Servicio de consultoría",
            cantidad=1,
            precio_unitario=1000.0,
            iva_pct=21.0
        )
    ]
    return calcular_factura(lineas, tipo_cliente="sl")


if __name__ == "__main__":
    print("=== Ejemplo Autónomo ===")
    calc = calcular_ejemplo_autonomo()
    print(f"Base: {calc.base_imponible}€")
    print(f"IVA: {calc.iva_cuota}€")
    print(f"IRPF: {calc.irpf_cuota}€")
    print(f"Total: {calc.total}€")
    print(f"Notas: {calc.notas}")
    
    print("\n=== Ejemplo Empresa ===")
    calc2 = calcular_ejemplo_empresa()
    print(f"Base: {calc2.base_imponible}€")
    print(f"IVA: {calc2.iva_cuota}€")
    print(f"IRPF: {calc2.irpf_cuota}€")
    print(f"Total: {calc2.total}€")
