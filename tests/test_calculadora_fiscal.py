"""
Tests para calculadora fiscal
"""
import pytest
from app.schemas.factura import FacturaCreate, LineaFacturaCreate
from app.services.calculadora_fiscal import (
    calcular_factura,
    calcular_linea,
    detectar_tipo_cliente,
    es_factura_correcta,
)


class TestCalculoLinea:
    """Tests para cálculo de línea individual"""
    
    def test_linea_sin_descuento(self):
        linea = LineaFacturaCreate(
            descripcion="Servicio",
            cantidad=1,
            precio_unitario=100.0,
            iva_pct=21.0
        )
        calc = calcular_linea(linea)
        
        assert calc["base_imponible"] == 100.0
        assert calc["iva_cuota"] == 21.0
        assert calc["total"] == 121.0
    
    def test_linea_con_descuento(self):
        linea = LineaFacturaCreate(
            descripcion="Servicio",
            cantidad=1,
            precio_unitario=100.0,
            descuento_pct=10.0,
            iva_pct=21.0
        )
        calc = calcular_linea(linea)
        
        assert calc["base_imponible"] == 90.0  # 100 - 10%
        assert calc["iva_cuota"] == 18.90      # 90 * 21%
        assert calc["total"] == 108.90
    
    def test_linea_cantidad_multiple(self):
        linea = LineaFacturaCreate(
            descripcion="10 horas",
            cantidad=10,
            precio_unitario=50.0,
            iva_pct=21.0
        )
        calc = calcular_linea(linea)
        
        assert calc["base_imponible"] == 500.0
        assert calc["iva_cuota"] == 105.0
        assert calc["total"] == 605.0


class TestCalculoFactura:
    """Tests para cálculo de factura completa"""
    
    def test_factura_autonomo_con_iva_y_irpf(self):
        """Factura a autónomo: aplica IVA 21% + IRPF 15%"""
        lineas = [
            LineaFacturaCreate(
                descripcion="Servicio traducción",
                cantidad=1,
                precio_unitario=300.0,
                iva_pct=21.0
            )
        ]
        calc = calcular_factura(lineas, tipo_cliente="autonomo")
        
        assert calc.base_imponible == 300.0
        assert calc.iva_cuota == 63.0
        assert calc.irpf_cuota == 45.0  # 300 * 15%
        assert calc.total == 318.0  # 300 + 63 - 45
    
    def test_factura_empresa_sin_irpf(self):
        """Factura a empresa: aplica IVA 21% sin IRPF"""
        lineas = [
            LineaFacturaCreate(
                descripcion="Servicio consultoría",
                cantidad=1,
                precio_unitario=1000.0,
                iva_pct=21.0
            )
        ]
        calc = calcular_factura(lineas, tipo_cliente="sl")
        
        assert calc.base_imponible == 1000.0
        assert calc.iva_cuota == 210.0
        assert calc.irpf_cuota == 0.0
        assert calc.total == 1210.0
    
    def test_factura_multiple_lineas(self):
        """Factura con múltiples líneas"""
        lineas = [
            LineaFacturaCreate(descripcion="Artículo 1", cantidad=2, precio_unitario=100.0, iva_pct=21.0),
            LineaFacturaCreate(descripcion="Artículo 2", cantidad=1, precio_unitario=50.0, iva_pct=10.0),
        ]
        calc = calcular_factura(lineas, tipo_cliente="autonomo")
        
        # Línea 1: 2 * 100 = 200 + 21% IVA = 242
        # Línea 2: 1 * 50 = 50 + 10% IVA = 55
        assert calc.base_imponible == 250.0  # 200 + 50
        assert calc.iva_cuota == 47.0  # 42 + 5
        assert calc.irpf_cuota == 37.5  # 250 * 15%
        assert calc.total == 259.5  # 250 + 47 - 37.5


class TestDetectarTipoCliente:
    """Tests para detección de tipo de cliente"""
    
    def test_nif_autonomo(self):
        assert detectar_tipo_cliente("12345678A") == "autonomo"
        assert detectar_tipo_cliente("X1234567A") == "autonomo"
    
    def test_cif_empresa(self):
        assert detectar_tipo_cliente("A12345678") == "sl"
        assert detectar_tipo_cliente("B12345678") == "sl"


class TestValidacion:
    """Tests de validación"""
    
    def test_factura_correcta(self):
        lineas = [
            LineaFacturaCreate(descripcion="Test", cantidad=1, precio_unitario=100.0, iva_pct=21.0)
        ]
        calc = calcular_factura(lineas)
        es_valida, errores = es_factura_correcta(calc)
        
        assert es_valida is True
        assert len(errores) == 0
    
    def test_factura_cero(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FacturaCreate(
                cliente_nif="12345678A",
                cliente_nombre="Test",
                lineas=[
                    LineaFacturaCreate(
                        descripcion="Test",
                        cantidad=0,
                        precio_unitario=100.0,
                        iva_pct=21.0,
                    )
                ],
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
