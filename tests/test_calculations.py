"""Pruebas unitarias para los cálculos monetarios, tributarios y de redondeo con Decimal."""

from decimal import Decimal
import pytest
from src.calculations import (
    calcular_totales_factura,
    procesar_linea,
    redondear,
)
from src.models import (
    InvoiceDocument,
    LineItemInput,
    Party,
)
from src.validators import ValidationError


def crear_documento_base(items):
    """Auxiliar para instanciar documentos de prueba."""
    emisor = Party("20605389458", "6", "TECSUR SAC")
    cliente = Party("20552103816", "6", "DISTRIBUIDORA SAC")
    return InvoiceDocument(
        emisor=emisor,
        cliente=cliente,
        tipo_documento="01",
        serie="F001",
        correlativo=1,
        fecha_emision="2026-11-12",
        hora_emision="10:00:00",
        items=items,
    )


def test_redondeo_half_up_exacto():
    """Valida el redondeo bancario/contable ROUND_HALF_UP con Decimal."""
    assert redondear(Decimal("10.005")) == Decimal("10.01")
    assert redondear(Decimal("10.004")) == Decimal("10.00")
    assert redondear(Decimal("10.0051")) == Decimal("10.01")
    assert redondear(Decimal("10.0050")) == Decimal("10.01")
    assert redondear(Decimal("0.000")) == Decimal("0.00")


def test_calculo_linea_gravada_onerosa():
    """Calcula cantidad x precio, IGV 18% y precio unitario que incluye IGV."""
    item = LineItemInput(
        id_linea=1,
        descripcion="Laptop de Desarrollo",
        cantidad=Decimal("3.00"),
        unidad_medida="NIU",
        valor_unitario=Decimal("3500.00"),
        codigo_afectacion_igv="10",
    )
    linea = procesar_linea(item, tasa_igv_defecto=Decimal("0.18"))

    # Valor venta = 3 * 3500 = 10500.00
    assert linea.line_extension_amount == Decimal("10500.00")
    # Base imponible = 10500.00
    assert linea.base_imponible_igv == Decimal("10500.00")
    # IGV = 10500 * 0.18 = 1890.00
    assert linea.monto_igv == Decimal("1890.00")
    assert linea.monto_total_impuestos_linea == Decimal("1890.00")
    # Precio unitario con IGV = 3500 * 1.18 = 4130.00
    assert linea.precio_unitario == Decimal("4130.00")
    assert linea.codigo_tipo_precio == "01"
    assert linea.codigo_tributo == "1000"
    assert linea.nombre_tributo == "IGV"


def test_calculo_linea_tasa_igv_especial_configurable():
    """Permite configurar una tasa distinta al 18% (ejemplo: 10.5% según régimen especial)."""
    item = LineItemInput(
        id_linea=1,
        descripcion="Servicio de Restaurante / Hospedaje MYPE",
        cantidad=Decimal("1.00"),
        unidad_medida="ZZ",
        valor_unitario=Decimal("200.00"),
        codigo_afectacion_igv="10",
        tasa_igv=Decimal("0.105"),  # 10.5%
    )
    linea = procesar_linea(item, tasa_igv_defecto=Decimal("0.18"))

    assert linea.line_extension_amount == Decimal("200.00")
    # IGV = 200 * 0.105 = 21.00
    assert linea.monto_igv == Decimal("21.00")
    assert linea.tasa_igv == Decimal("10.50")
    # Precio unitario = 200 * 1.105 = 221.00
    assert linea.precio_unitario == Decimal("221.00")


def test_calculo_linea_exonerada():
    """Línea exonerada (código 20) tributa código 9997 con IGV 0.00."""
    item = LineItemInput(
        id_linea=1,
        descripcion="Libro científico impreso",
        cantidad=Decimal("2.00"),
        unidad_medida="NIU",
        valor_unitario=Decimal("150.00"),
        codigo_afectacion_igv="20",
    )
    linea = procesar_linea(item, tasa_igv_defecto=Decimal("0.18"))

    assert linea.line_extension_amount == Decimal("300.00")
    assert linea.base_imponible_igv == Decimal("300.00")
    assert linea.monto_igv == Decimal("0.00")
    assert linea.precio_unitario == Decimal("150.00")
    assert linea.codigo_tributo == "9997"
    assert linea.nombre_tributo == "EXO"


def test_calculo_linea_inafecta():
    """Línea inafecta (código 30) tributa código 9998 con IGV 0.00."""
    item = LineItemInput(
        id_linea=1,
        descripcion="Servicio educativo inafecto",
        cantidad=Decimal("1.00"),
        unidad_medida="ZZ",
        valor_unitario=Decimal("500.00"),
        codigo_afectacion_igv="30",
    )
    linea = procesar_linea(item, tasa_igv_defecto=Decimal("0.18"))

    assert linea.line_extension_amount == Decimal("500.00")
    assert linea.monto_igv == Decimal("0.00")
    assert linea.codigo_tributo == "9998"
    assert linea.nombre_tributo == "INA"


def test_calculo_linea_gratuita():
    """Línea no onerosa / gratuita (código 11) utiliza tipo de precio '02' y tributo 9996."""
    item = LineItemInput(
        id_linea=1,
        descripcion="Muestra promocional sin valor comercial",
        cantidad=Decimal("5.00"),
        unidad_medida="NIU",
        valor_unitario=Decimal("10.00"),
        codigo_afectacion_igv="11",  # Retiro por premio / bonificación
    )
    linea = procesar_linea(item, tasa_igv_defecto=Decimal("0.18"))

    assert linea.line_extension_amount == Decimal("50.00")
    assert linea.codigo_tipo_precio == "02"  # Valor referencial unitario (Catálogo 16)
    assert linea.codigo_tributo == "9996"


def test_totales_factura_mixta_y_distincion_catalogo_14():
    """Verifica la correcta agregación de subtotales, totales y distinción de Catálogo 14."""
    items = [
        LineItemInput(1, "Prod Gravado A", Decimal("2"), "NIU", Decimal("100.00"), "10"),  # VV=200, IGV=36
        LineItemInput(2, "Prod Gravado B", Decimal("1"), "NIU", Decimal("50.00"), "10"),   # VV=50, IGV=9
        LineItemInput(3, "Prod Exonerado", Decimal("1"), "NIU", Decimal("80.00"), "20"),   # VV=80, IGV=0
        LineItemInput(4, "Prod Inafecto", Decimal("1"), "NIU", Decimal("120.00"), "30"),   # VV=120, IGV=0
    ]
    doc = crear_documento_base(items)
    calc = calcular_totales_factura(doc)

    # Catálogo 14:
    # 1001 Total Gravadas = 250.00
    assert calc.total_valor_venta_gravada == Decimal("250.00")
    # 1003 Total Exoneradas = 80.00
    assert calc.total_valor_venta_exonerada == Decimal("80.00")
    # 1002 Total Inafectas = 120.00
    assert calc.total_valor_venta_inafecta == Decimal("120.00")

    # Total Valor de Venta (LineExtensionAmount) = 250 + 80 + 120 = 450.00
    assert calc.total_valor_venta == Decimal("450.00")
    # Total IGV = 36 + 9 = 45.00
    assert calc.total_igv == Decimal("45.00")
    # Total Precio de Venta (TaxInclusiveAmount) = 450 + 45 = 495.00
    assert calc.total_precio_venta == Decimal("495.00")
    # Importe Total a Pagar (PayableAmount) = 495.00
    assert calc.importe_total_pagar == Decimal("495.00")

    # Consistencia en TaxSubtotal: debe haber grupo 1000, 9997 y 9998
    assert "1000" in calc.subtotales_tributo
    assert calc.subtotales_tributo["1000"].base_imponible == Decimal("250.00")
    assert calc.subtotales_tributo["1000"].monto_impuesto == Decimal("45.00")

    assert "9997" in calc.subtotales_tributo
    assert calc.subtotales_tributo["9997"].base_imponible == Decimal("80.00")
    assert calc.subtotales_tributo["9997"].monto_impuesto == Decimal("0.00")

    assert "9998" in calc.subtotales_tributo
    assert calc.subtotales_tributo["9998"].base_imponible == Decimal("120.00")
    assert calc.subtotales_tributo["9998"].monto_impuesto == Decimal("0.00")


def test_rechazo_cantidad_invalida_o_cero():
    """Rechaza ítems con cantidad menor o igual a cero."""
    item_cero = LineItemInput(1, "Prod Inválido", Decimal("0.00"), "NIU", Decimal("100.00"), "10")
    with pytest.raises(ValidationError) as exc:
        procesar_linea(item_cero, Decimal("0.18"))
    assert "mayor a cero" in str(exc.value)

    item_neg = LineItemInput(1, "Prod Negativo", Decimal("-2.00"), "NIU", Decimal("100.00"), "10")
    with pytest.raises(ValidationError):
        procesar_linea(item_neg, Decimal("0.18"))


def test_rechazo_valor_unitario_negativo():
    """Rechaza ítems con precio unitario negativo."""
    item = LineItemInput(1, "Prod Precio Negativo", Decimal("1.00"), "NIU", Decimal("-50.00"), "10")
    with pytest.raises(ValidationError):
        procesar_linea(item, Decimal("0.18"))


def test_rechazo_codigo_afectacion_inexistente():
    """Rechaza códigos de afectación no contemplados en el Catálogo 07."""
    item = LineItemInput(1, "Prod Afectacion Rara", Decimal("1.00"), "NIU", Decimal("50.00"), "99")
    with pytest.raises(ValidationError) as exc:
        procesar_linea(item, Decimal("0.18"))
    assert "Catálogo 07" in str(exc.value)


def test_rechazo_factura_sin_items():
    """Rechaza facturas que no tengan ninguna línea."""
    doc = crear_documento_base(items=[])
    with pytest.raises(ValidationError) as exc:
        calcular_totales_factura(doc)
    assert "al menos una línea" in str(exc.value)

