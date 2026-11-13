"""Pruebas unitarias para la generación del documento XML UBL 2.1 y codificación ISO-8859-1."""

from decimal import Decimal
from lxml import etree
import pytest
from src.builder import (
    InvoiceXmlBuilder,
    NS_CAC,
    NS_CBC,
    NS_INVOICE,
)
from src.models import (
    InvoiceDocument,
    LineItemInput,
    Party,
    PartyAddress,
)


def crear_documento_con_caracteres_espanoles():
    """Crea una factura con tildes, eñes y caracteres especiales en español."""
    emisor = Party(
        numero_documento="20605389458",
        tipo_documento_identidad="6",
        razon_social="TECNOLOGÍA, INNOVACIÓN & DISEÑO S.A.C.",
        nombre_comercial="DISEÑO & MÁS",
        direccion=PartyAddress(
            direccion="Av. Los Álamos N.° 450, Mz. Ñ Lote 12",
            ubigeo="150131",
            departamento="LIMA",
            provincia="LIMA",
            distrito="SAN ISIDRO",
            urbanizacion="Jardín El Edén",
        ),
    )
    cliente = Party(
        numero_documento="20552103816",
        tipo_documento_identidad="6",
        razon_social="COMPAÑÍA DE DISTRIBUCIÓN Y LOGÍSTICA DEL PERÚ S.A.",
        direccion=PartyAddress(
            direccion="Jr. Junín 1020, Int. 3° Piso",
            ubigeo="150117",
            departamento="LIMA",
            provincia="LIMA",
            distrito="LOS OLIVOS",
        ),
    )
    items = [
        LineItemInput(
            id_linea=1,
            descripcion="Módulo de Transmisión Inalámbrica Estándar (Cañón Óptico)",
            cantidad=Decimal("1.00"),
            unidad_medida="NIU",
            valor_unitario=Decimal("1250.50"),
            codigo_afectacion_igv="10",
        ),
        LineItemInput(
            id_linea=2,
            descripcion="Diseño Gráfico y Maquetación de Guía Técnica en Español (Álbum)",
            cantidad=Decimal("1.00"),
            unidad_medida="ZZ",
            valor_unitario=Decimal("350.00"),
            codigo_afectacion_igv="20",
        ),
    ]
    return InvoiceDocument(
        emisor=emisor,
        cliente=cliente,
        tipo_documento="01",
        serie="F001",
        correlativo=100,
        fecha_emision="2026-11-12",
        hora_emision="14:20:00",
        items=items,
        leyendas={
            "1000": "SON UN MIL OCHOCIENTOS VEINTICINCO Y 59/100 SOLES"
        },
    )


def test_generacion_xml_namespaces_y_raiz():
    """Verifica que el elemento raíz sea Invoice y contenga los namespaces oficiales UBL 2.1."""
    doc = crear_documento_con_caracteres_espanoles()
    builder = InvoiceXmlBuilder(doc)
    root = builder.construir_arbol()

    assert root.tag == f"{{{NS_INVOICE}}}Invoice"
    assert root.nsmap[None] == NS_INVOICE
    assert root.nsmap["cac"] == NS_CAC
    assert root.nsmap["cbc"] == NS_CBC


def test_codificacion_iso_8859_1_y_caracteres_espanoles():
    """Asegura que el XML emitido esté en ISO-8859-1 y soporte tildes y eñes correctamente."""
    doc = crear_documento_con_caracteres_espanoles()
    builder = InvoiceXmlBuilder(doc)
    xml_bytes = builder.generar_xml_bytes(encoding="ISO-8859-1")

    # 1. Declaración XML contiene encoding="ISO-8859-1"
    assert b"encoding='ISO-8859-1'" in xml_bytes or b'encoding="ISO-8859-1"' in xml_bytes

    # 2. Los bytes se decodifican limpiamente con iso-8859-1
    texto_decodificado = xml_bytes.decode("iso-8859-1")

    # 3. Contiene los caracteres específicos del español
    assert "TECNOLOGÍA" in texto_decodificado
    assert "DISEÑO" in texto_decodificado
    assert "Álamos" in texto_decodificado
    assert "COMPAÑÍA" in texto_decodificado
    assert "LOGÍSTICA" in texto_decodificado
    assert "Cañón" in texto_decodificado
    assert "Óptico" in texto_decodificado
    assert "N.°" in texto_decodificado

    # 4. En ISO-8859-1, 'ñ' es el byte 0xF1 y 'ó' es 0xF3
    assert b"\xf1" in xml_bytes  # ñ
    assert b"\xf3" in xml_bytes  # ó
    assert b"\xed" in xml_bytes  # í
    assert b"\xc1" in xml_bytes  # Á


def test_orden_estricto_elementos_cabecera():
    """Verifica que los elementos principales de Invoice sigan el orden de secuencia XSD."""
    doc = crear_documento_con_caracteres_espanoles()
    builder = InvoiceXmlBuilder(doc)
    root = builder.construir_arbol()

    etiquetas = [child.tag.split("}")[1] for child in root]

    # Orden relativo requerido:
    # UBLExtensions -> UBLVersionID -> CustomizationID -> ID -> IssueDate -> InvoiceTypeCode -> DocumentCurrencyCode -> Signature -> AccountingSupplierParty -> AccountingCustomerParty -> PaymentTerms -> TaxTotal -> LegalMonetaryTotal -> InvoiceLine
    idx_exts = etiquetas.index("UBLExtensions")
    idx_ubl = etiquetas.index("UBLVersionID")
    idx_cust = etiquetas.index("CustomizationID")
    idx_id = etiquetas.index("ID")
    idx_date = etiquetas.index("IssueDate")
    idx_type = etiquetas.index("InvoiceTypeCode")
    idx_curr = etiquetas.index("DocumentCurrencyCode")
    idx_sig = etiquetas.index("Signature")
    idx_asp = etiquetas.index("AccountingSupplierParty")
    idx_acp = etiquetas.index("AccountingCustomerParty")
    idx_pt = etiquetas.index("PaymentTerms")
    idx_tt = etiquetas.index("TaxTotal")
    idx_lmt = etiquetas.index("LegalMonetaryTotal")
    idx_line = etiquetas.index("InvoiceLine")

    assert idx_exts < idx_ubl < idx_cust < idx_id < idx_date < idx_type < idx_curr < idx_sig < idx_asp < idx_acp < idx_pt < idx_tt < idx_lmt < idx_line

