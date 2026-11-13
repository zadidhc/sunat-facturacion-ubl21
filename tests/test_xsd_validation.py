"""Pruebas unitarias para la validación estricta contra el esquema oficial XSD OASIS UBL 2.1 y reglas SUNAT."""

import os
from decimal import Decimal
from lxml import etree
import pytest
from src.builder import InvoiceXmlBuilder
from src.models import (
    InvoiceDocument,
    LineItemInput,
    Party,
    PartyAddress,
    PaymentTerms,
    Installment,
)
from src.xsd_validator import SunatInvoiceValidator


@pytest.fixture(scope="module")
def validador_oficial():
    """Instancia el validador con el esquema oficial OASIS UBL-Invoice-2.1.xsd."""
    return SunatInvoiceValidator()


@pytest.fixture
def documento_valido_contado():
    """Genera un documento válido al contado listo para validación."""
    emisor = Party(
        numero_documento="20605389458",
        tipo_documento_identidad="6",
        razon_social="TECNOLOGIA Y SISTEMAS DEL SUR S.A.C.",
        nombre_comercial="TECSUR PERU",
        direccion=PartyAddress(
            direccion="Av. Republica de Panama 3545",
            ubigeo="150131",
            departamento="LIMA",
            provincia="LIMA",
            distrito="SAN ISIDRO",
            codigo_local_anexo="0000",
        ),
    )
    cliente = Party(
        numero_documento="20552103816",
        tipo_documento_identidad="6",
        razon_social="DISTRIBUIDORA INDUSTRIAL LIMA NORTE S.A.C.",
        direccion=PartyAddress(
            direccion="Av. Alfredo Mendiola 1400",
            ubigeo="150117",
            departamento="LIMA",
            provincia="LIMA",
            distrito="LOS OLIVOS",
        ),
    )
    items = [
        LineItemInput(
            id_linea=1,
            descripcion="Servidor Enterprise Xeon",
            cantidad=Decimal("2.00"),
            unidad_medida="NIU",
            valor_unitario=Decimal("4500.00"),
            codigo_afectacion_igv="10",
        ),
        LineItemInput(
            id_linea=2,
            descripcion="Manual Técnico UBL 2.1 (Exonerado)",
            cantidad=Decimal("1.00"),
            unidad_medida="NIU",
            valor_unitario=Decimal("250.00"),
            codigo_afectacion_igv="20",
        ),
    ]
    return InvoiceDocument(
        emisor=emisor,
        cliente=cliente,
        tipo_documento="01",
        serie="F001",
        correlativo=1,
        fecha_emision="2026-11-12",
        hora_emision="10:30:00",
        moneda="PEN",
        tipo_operacion="0101",
        terminos_pago=PaymentTerms(forma_pago="Contado"),
        items=items,
        leyendas={"1000": "SON DIEZ MIL OCHOCIENTOS SETENTA Y 00/100 SOLES"},
    )


def test_validacion_exitosa_contra_xsd_oficial(validador_oficial, documento_valido_contado):
    """Requerimiento 9: El XML generado dinámicamente valida con éxito contra el XSD oficial UBL-Invoice-2.1.xsd."""
    builder = InvoiceXmlBuilder(documento_valido_contado)
    xml_bytes = builder.generar_xml_bytes()
    nombre_archivo = builder.obtener_nombre_archivo()

    reporte = validador_oficial.validar_documento_completo(xml_bytes, nombre_archivo=nombre_archivo)

    assert reporte.es_valido is True
    assert reporte.nivel_1_bien_formado is True
    assert reporte.nivel_2_xsd_valido is True
    assert reporte.nivel_3_reglas_sunat_validas is True
    assert len(reporte.errores_nivel_2_xsd) == 0
    assert len(reporte.errores_nivel_3_sunat) == 0


def test_rechazo_xml_sintacticamente_malformado(validador_oficial):
    """Requerimiento 10: Rechazo de XML con sintaxis malformada (etiquetas no cerradas)."""
    xml_malformado = b"<?xml version='1.0' encoding='ISO-8859-1'?><Invoice><cbc:ID>F001-1</cbc:ID>"  # No cierra Invoice
    reporte = validador_oficial.validar_documento_completo(xml_malformado)

    assert reporte.es_valido is False
    assert reporte.nivel_1_bien_formado is False
    assert any("Error sintáctico" in err for err in reporte.errores_nivel_1)


def test_rechazo_por_eliminacion_de_nodo_obligatorio_en_xsd(validador_oficial, documento_valido_contado):
    """Requerimiento 11: Rechazo si se elimina deliberadamente un elemento obligatorio (cac:AccountingCustomerParty)."""
    builder = InvoiceXmlBuilder(documento_valido_contado)
    root = builder.construir_arbol()

    # Localizar y remover cac:AccountingCustomerParty
    ns = {"cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"}
    acp = root.xpath("//cac:AccountingCustomerParty", namespaces=ns)[0]
    root.remove(acp)

    xml_alterado = etree.tostring(root, encoding="ISO-8859-1", xml_declaration=True)
    reporte = validador_oficial.validar_documento_completo(xml_alterado)

    assert reporte.nivel_2_xsd_valido is False
    assert reporte.es_valido is False
    assert any("AccountingCustomerParty" in err for err in reporte.errores_nivel_2_xsd)


def test_rechazo_por_alteracion_de_orden_secuencia_xsd(validador_oficial, documento_valido_contado):
    """Requerimiento 8/11: Rechazo si se invierte el orden exigido por la secuencia XSD."""
    builder = InvoiceXmlBuilder(documento_valido_contado)
    root = builder.construir_arbol()

    ns = {"cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"}
    ubl_ver = root.xpath("cbc:UBLVersionID", namespaces=ns)[0]
    cust_id = root.xpath("cbc:CustomizationID", namespaces=ns)[0]

    # Invertir el orden: colocar CustomizationID antes de UBLVersionID
    root.remove(cust_id)
    root.insert(root.index(ubl_ver), cust_id)

    xml_desordenado = etree.tostring(root, encoding="ISO-8859-1", xml_declaration=True)
    reporte = validador_oficial.validar_documento_completo(xml_desordenado)

    assert reporte.nivel_2_xsd_valido is False
    assert any("This element is not expected" in err for err in reporte.errores_nivel_2_xsd)


def test_rechazo_por_inconsistencia_en_regla_sunat_line_extension(validador_oficial, documento_valido_contado):
    """Requerimiento 21: Detecta y rechaza alteración manual del total valor de venta en regla SUNAT 3278."""
    builder = InvoiceXmlBuilder(documento_valido_contado)
    root = builder.construir_arbol()

    ns = {
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }
    # Alterar LineExtensionAmount en LegalMonetaryTotal
    lea = root.xpath("//cac:LegalMonetaryTotal/cbc:LineExtensionAmount", namespaces=ns)[0]
    lea.text = "99999.00"

    xml_alterado = etree.tostring(root, encoding="ISO-8859-1", xml_declaration=True)
    nombre_archivo = builder.obtener_nombre_archivo()
    reporte = validador_oficial.validar_documento_completo(xml_alterado, nombre_archivo=nombre_archivo)

    assert reporte.nivel_3_reglas_sunat_validas is False
    assert any("Regla 3278" in err for err in reporte.errores_nivel_3_sunat)


def test_validacion_operacion_al_credito_completa(validador_oficial, documento_valido_contado):
    """Requerimiento 18: Valida factura al crédito con cuotas contra XSD y reglas SUNAT 3244-3256."""
    doc_credito = documento_valido_contado
    doc_credito.correlativo = 2
    doc_credito.terminos_pago = PaymentTerms(
        forma_pago="Credito",
        monto_neto_pendiente=Decimal("10870.00"),
        cuotas=[
            Installment("Cuota001", Decimal("5435.00"), "2026-12-12"),
            Installment("Cuota002", Decimal("5435.00"), "2027-01-11"),
        ],
    )
    builder = InvoiceXmlBuilder(doc_credito)
    xml_bytes = builder.generar_xml_bytes()
    nombre_archivo = builder.obtener_nombre_archivo()

    reporte = validador_oficial.validar_documento_completo(xml_bytes, nombre_archivo=nombre_archivo)

    assert reporte.es_valido is True
    assert reporte.nivel_2_xsd_valido is True
    assert reporte.nivel_3_reglas_sunat_validas is True


def test_ejecucion_autonoma_sin_servicios_externos(validador_oficial, documento_valido_contado):
    """Requerimiento 22: La generación y validación se ejecuta de forma autónoma y reproducible offline."""
    builder = InvoiceXmlBuilder(documento_valido_contado)
    xml_bytes = builder.generar_xml_bytes()
    reporte = validador_oficial.validar_documento_completo(xml_bytes)

    assert reporte.es_valido is True
    # Registra formalmente que no requiere llamadas a APIs externas en tiempo de test
    assert len(reporte.reglas_externas_no_evaluables) > 0

