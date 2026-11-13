"""Catálogos oficiales de códigos de SUNAT (Anexo 8) para comprobantes de pago electrónicos UBL 2.1.

Este módulo centraliza las definiciones y validaciones de los catálogos fiscales peruanos.
"""

from typing import Dict, NamedTuple, Optional


class TributoInfo(NamedTuple):
    """Información oficial de un tipo de tributo según Catálogo 05."""
    codigo: str
    descripcion: str
    codigo_internacional: str
    nombre_tributo: str
    categoria_impuesto: str  # UN/ECE 5305 (S, E, O, Z, G)


# Catálogo No. 01: Código de tipo de documento
CATALOGO_01_TIPO_DOCUMENTO: Dict[str, str] = {
    "01": "Factura",
    "03": "Boleta de Venta",
    "07": "Nota de Crédito",
    "08": "Nota de Débito",
    "09": "Guía de Remisión Remitente",
    "12": "Ticket de Máquina Registradora",
    "13": "Documento emitido por bancos e instituciones financieras",
    "14": "Recibo de Servicios Públicos",
    "20": "Comprobante de Retención",
    "31": "Guía de Remisión Transportista",
    "40": "Comprobante de Percepción",
}

# Catálogo No. 02: Código de tipo de monedas (ISO 4217)
CATALOGO_02_MONEDAS: Dict[str, str] = {
    "PEN": "Soles (Perú)",
    "USD": "Dólares Americanos (EE.UU.)",
    "EUR": "Euros (Unión Europea)",
}

# Catálogo No. 03: Código de tipo de unidad de medida comercial (UN/ECE Rec 20)
CATALOGO_03_UNIDADES: Dict[str, str] = {
    "NIU": "Unidad (Bienes)",
    "ZZ": "Servicio (Unidad de servicio)",
    "KGM": "Kilogramo",
    "MTR": "Metro",
    "BX": "Caja",
    "PK": "Paquete",
    "DZN": "Docena",
    "LTR": "Litro",
    "TNE": "Tonelada métrica",
    "HUR": "Hora",
    "DAY": "Día",
}

# Catálogo No. 04: Código de países (ISO 3166-1)
CATALOGO_04_PAISES: Dict[str, str] = {
    "PE": "Perú",
    "US": "Estados Unidos",
    "CL": "Chile",
    "AR": "Argentina",
    "CO": "Colombia",
    "BR": "Brasil",
    "ES": "España",
}

# Catálogo No. 05: Códigos de tipos de tributos
CATALOGO_05_TRIBUTOS: Dict[str, TributoInfo] = {
    "1000": TributoInfo("1000", "IGV IMPUESTO GENERAL A LAS VENTAS", "VAT", "IGV", "S"),
    "1016": TributoInfo("1016", "IMPUESTO A LA VENTA ARROZ PILADO", "VAT", "IVAP", "S"),
    "2000": TributoInfo("2000", "ISC IMPUESTO SELECTIVO AL CONSUMO", "EXC", "ISC", "S"),
    "7152": TributoInfo("7152", "IMPUESTO AL CONSUMO DE BOLSAS DE PLÁSTICO", "OTH", "ICBPER", "S"),
    "9995": TributoInfo("9995", "EXPORTACIÓN", "FRE", "EXP", "G"),
    "9996": TributoInfo("9996", "GRATUITO", "FRE", "GRA", "Z"),
    "9997": TributoInfo("9997", "EXONERADO", "VAT", "EXO", "E"),
    "9998": TributoInfo("9998", "INAFECTO", "FRE", "INA", "O"),
    "9999": TributoInfo("9999", "OTROS CONCEPTOS DE PAGO", "OTH", "OTROS", "S"),
}

# Catálogo No. 06: Códigos de tipos de documentos de identidad
CATALOGO_06_TIPOS_IDENTIDAD: Dict[str, str] = {
    "0": "DOC.TRIB.NO.DOM.SIN.RUC",
    "1": "DOC. NACIONAL DE IDENTIDAD (DNI)",
    "4": "CARNET DE EXTRANJERIA",
    "6": "REG. UNICO DE CONTRIBUYENTES (RUC)",
    "7": "PASAPORTE",
    "A": "CED. DIPLOMATICA DE IDENTIDAD",
    "B": "DOC.IDENT.PAIS.RESIDENCIA-NO.D",
    "C": "Tax Identification Number - TIN",
    "D": "Identification Number - IN",
    "E": "TAM- Tarjeta Andina de Migración",
    "F": "Permiso Temporal de Permanencia - PTP",
    "G": "Salvoconducto",
    "H": "Carné Permiso Temp. Perman. - CPP",
}

# Catálogo No. 07: Códigos de tipo de afectación del IGV
CATALOGO_07_AFECTACION_IGV: Dict[str, str] = {
    "10": "Gravado - Operación Onerosa",
    "11": "Gravado - Retiro por premio",
    "12": "Gravado - Retiro por donación",
    "13": "Gravado - Retiro",
    "14": "Gravado - Retiro por publicidad",
    "15": "Gravado - Bonificaciones",
    "16": "Gravado - Retiro por entrega a trabajadores",
    "17": "Gravado - IVAP",
    "20": "Exonerado - Operación Onerosa",
    "21": "Exonerado - Transferencia Gratuita",
    "30": "Inafecto - Operación Onerosa",
    "31": "Inafecto - Retiro por Bonificación",
    "32": "Inafecto - Retiro",
    "33": "Inafecto - Retiro por Muestras Médicas",
    "34": "Inafecto - Retiro por Convenio Colectivo",
    "35": "Inafecto - Retiro por premio",
    "36": "Inafecto - Retiro por publicidad",
    "37": "Inafecto - Transferencia Gratuita",
    "40": "Exportación de Bienes o Servicios",
}

# Mapeo de afectación al IGV (Catálogo 07) al código de tributo correspondiente (Catálogo 05)
AFECTACION_A_TRIBUTO: Dict[str, str] = {
    "10": "1000",  # Gravado Oneroso -> IGV (1000)
    "11": "9996",  # Retiro por premio -> Gratuito (9996)
    "12": "9996",  # Retiro por donación -> Gratuito (9996)
    "13": "9996",  # Retiro -> Gratuito (9996)
    "14": "9996",  # Retiro publicidad -> Gratuito (9996)
    "15": "9996",  # Bonificaciones -> Gratuito (9996)
    "16": "9996",  # Entrega a trabajadores -> Gratuito (9996)
    "17": "1016",  # IVAP
    "20": "9997",  # Exonerado Oneroso -> Exonerado (9997)
    "21": "9996",  # Exonerado Gratuito -> Gratuito (9996)
    "30": "9998",  # Inafecto Oneroso -> Inafecto (9998)
    "31": "9996",  # Inafecto Gratuito -> Gratuito (9996)
    "32": "9996",  # Inafecto Gratuito -> Gratuito (9996)
    "33": "9996",  # Inafecto Muestras -> Gratuito (9996)
    "34": "9996",  # Inafecto Convenio -> Gratuito (9996)
    "35": "9996",  # Inafecto Premio -> Gratuito (9996)
    "36": "9996",  # Inafecto Publicidad -> Gratuito (9996)
    "37": "9996",  # Inafecto Gratuita -> Gratuito (9996)
    "40": "9995",  # Exportación -> Exportación (9995)
}

# Catálogo No. 14: Códigos de otros conceptos tributarios
# NOTA ARQUITECTÓNICA VITAL:
# Estos códigos (1001, 1002, 1003, etc.) se utilizaban en UBL 2.0 en sac:AdditionalInformation/sac:AdditionalMonetaryTotal.
# En UBL 2.1 SUNAT NO se deben colocar como TaxScheme/cbc:ID, sino que corresponden a los totales
# representados mediante cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount con el tributo de Catálogo 05,
# y cac:LegalMonetaryTotal/cbc:LineExtensionAmount.
CATALOGO_14_CONCEPTOS_TRIBUTARIOS: Dict[str, str] = {
    "1000": "Total valor de venta - operaciones exportadas",
    "1001": "Total valor de venta - operaciones gravadas",
    "1002": "Total valor de venta - operaciones inafectas",
    "1003": "Total valor de venta - operaciones exoneradas",
    "1004": "Total valor de venta - operaciones gratuitas",
    "1005": "Sub total de venta",
    "2001": "Percepciones",
    "2002": "Retenciones",
    "2003": "Detracciones",
    "2004": "Bonificaciones",
    "2005": "Total descuentos",
    "3001": "FISE (Fondo de Inclusión Social Energético)",
}

# Catálogo No. 16: Códigos de tipo de precio de venta unitario
CATALOGO_16_TIPO_PRECIO: Dict[str, str] = {
    "01": "Precio unitario (incluye el IGV)",
    "02": "Valor referencial unitario en operaciones no onerosas",
    "03": "Tarifas reguladas",
}

# Catálogo No. 51: Códigos de tipo de operación
CATALOGO_51_TIPO_OPERACION: Dict[str, str] = {
    "0101": "Venta interna no sujeta a Detracción o Percepción",
    "0112": "Venta Interna - Sustenta Gastos Deducibles Persona Natural",
    "0200": "Exportación de Bienes",
    "0201": "Exportación de Servicios - Prestación realizada íntegramente en el país",
    "1001": "Operación Sujeta a Detracción",
    "2001": "Operación Sujeta a Percepción",
}

# Catálogo No. 52: Códigos de leyendas
CATALOGO_52_LEYENDAS: Dict[str, str] = {
    "1000": "Monto en Letras",
    "1002": "TRANSFERENCIA GRATUITA DE UN BIEN Y/O SERVICIO PRESTADO GRATUITAMENTE",
    "2000": "COMPROBANTE DE PERCEPCIÓN",
    "2006": "Operación sujeta a detracción",
    "2007": "Operación sujeta a IVAP",
}

# Catálogo No. 59: Medios de pago
CATALOGO_59_MEDIOS_PAGO: Dict[str, str] = {
    "001": "Depósito en cuenta",
    "003": "Transferencia de fondos",
    "005": "Tarjeta de débito",
    "006": "Tarjeta de crédito",
    "008": "Efectivo",
    "999": "Otros medios de pago",
}

