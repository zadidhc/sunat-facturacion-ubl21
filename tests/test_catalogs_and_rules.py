"""Pruebas unitarias para catálogos SUNAT, series, correlativos y nomenclatura de archivo."""

import pytest
from src.catalogs import (
    CATALOGO_01_TIPO_DOCUMENTO,
    CATALOGO_02_MONEDAS,
    CATALOGO_03_UNIDADES,
    CATALOGO_05_TRIBUTOS,
    CATALOGO_07_AFECTACION_IGV,
)
from src.validators import (
    formatear_nombre_archivo_xml,
    validar_serie_correlativo,
    ValidationError,
)


def test_catalogo_01_tipos_documento():
    """Verifica que el Catálogo 01 contenga los comprobantes de pago oficiales."""
    assert CATALOGO_01_TIPO_DOCUMENTO["01"] == "Factura"
    assert CATALOGO_01_TIPO_DOCUMENTO["03"] == "Boleta de Venta"
    assert CATALOGO_01_TIPO_DOCUMENTO["07"] == "Nota de Crédito"
    assert CATALOGO_01_TIPO_DOCUMENTO["08"] == "Nota de Débito"


@pytest.mark.parametrize("tipo,serie,corr,esperado", [
    ("01", "F001", 1, True),
    ("01", "FA01", 99999999, True),
    ("01", "0001", 50, True),  # Serie de contingencia
    ("03", "B001", 10, True),
    ("03", "B099", 500, True),
    ("03", "0002", 123, True),
])
def test_series_y_correlativos_validos(tipo, serie, corr, esperado):
    """Valida series electrónicas y de contingencia válidas para Facturas y Boletas."""
    valido, _ = validar_serie_correlativo(tipo, serie, corr)
    assert valido is esperado


@pytest.mark.parametrize("tipo,serie,corr", [
    ("01", "B001", 1),    # Serie de Boleta en Factura
    ("01", "F01", 1),     # Longitud 3 en lugar de 4
    ("01", "F0001", 1),   # Longitud 5 en lugar de 4
    ("01", "E001", 1),    # Serie no autorizada
    ("03", "F001", 1),    # Serie de Factura en Boleta
    ("01", "F001", 0),    # Correlativo 0 inválido
    ("01", "F001", -5),   # Correlativo negativo
    ("01", "F001", 100000000),  # Supera 8 dígitos (> 99999999)
])
def test_series_y_correlativos_invalidos(tipo, serie, corr):
    """Rechaza combinaciones ilegales de serie y correlativo."""
    valido, _ = validar_serie_correlativo(tipo, serie, corr)
    assert valido is False


def test_no_generar_notas_con_raiz_invoice():
    """Valida que Notas de Crédito (07) y Débito (08) no se generen bajo Invoice root."""
    valido_07, msg_07 = validar_serie_correlativo("07", "FC01", 1)
    assert valido_07 is False
    assert "no soportado" in msg_07

    valido_08, msg_08 = validar_serie_correlativo("08", "FD01", 1)
    assert valido_08 is False
    assert "no soportado" in msg_08


def test_formato_nombre_archivo_sunat():
    """Verifica el nombre de archivo reglamentario RUC-TIPO-SERIE-CORRELATIVO.xml."""
    ruc = "20605389458"
    tipo = "01"
    serie = "F001"
    correlativo = 1

    nombre = formatear_nombre_archivo_xml(ruc, tipo, serie, correlativo, padding_correlativo=8)
    assert nombre == "20605389458-01-F001-00000001.xml"

    # Con correlativo mayor
    nombre_2 = formatear_nombre_archivo_xml(ruc, tipo, serie, 4520, padding_correlativo=8)
    assert nombre_2 == "20605389458-01-F001-00004520.xml"


def test_nombre_archivo_falla_con_ruc_invalido():
    """Rechaza la generación del nombre de archivo si el RUC tiene dígito verificador erróneo."""
    with pytest.raises(ValidationError):
        formatear_nombre_archivo_xml("20605389450", "01", "F001", 1)

