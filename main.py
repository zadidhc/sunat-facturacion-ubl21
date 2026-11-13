"""Punto de entrada principal para la generación y validación de facturas electrónicas UBL 2.1 (SUNAT).

Permite ejecutar de extremo a extremo:
1. Carga de datos configurables desde JSON.
2. Cálculo financiero con Decimal y redondeo HALF_UP.
3. Generación del XML UBL 2.1 en codificación ISO-8859-1.
4. Guardado con nomenclatura oficial SUNAT: RUC-01-SERIE-NUMERO.xml.
5. Validación rigurosa de 3 niveles (Sintaxis, XSD oficial OASIS y Reglas de Negocio SUNAT).
6. Generación de un ejemplo inválido intencional para demostrar detección de errores.
"""

import argparse
import json
import os
import sys
from lxml import etree
from src.builder import InvoiceXmlBuilder
from src.models import cargar_documento_desde_dict
from src.xsd_validator import SunatInvoiceValidator


def imprimir_reporte_validacion(reporte, nombre_archivo: str) -> None:
    """Muestra en consola el informe detallado de la validación en 3 niveles."""
    print("=" * 80)
    print(f"INFORME DE AUDITORÍA Y VALIDACIÓN: {os.path.basename(nombre_archivo)}")
    print("=" * 80)

    # Nivel 1
    st_n1 = "CONFORME [OK]" if reporte.nivel_1_bien_formado else "FALLO [ERROR]"
    print(f"1. NIVEL 1 - Sintaxis y Codificación: {st_n1}")
    print(f"   Codificación detectada en declaración: {reporte.codificacion_detectada}")
    if reporte.errores_nivel_1:
        for err in reporte.errores_nivel_1:
            print(f"   - [ERROR] {err}")

    # Nivel 2
    st_n2 = "CONFORME [OK]" if reporte.nivel_2_xsd_valido else "FALLO [ERROR]"
    print(f"2. NIVEL 2 - Esquema Oficial OASIS UBL 2.1 (XSD): {st_n2}")
    if reporte.errores_nivel_2_xsd:
        for err in reporte.errores_nivel_2_xsd:
            print(f"   - [ERROR XSD] {err}")
    else:
        print("   - Estructura, namespaces y secuencia de nodos estrictamente conformes con UBL-Invoice-2.1.xsd.")

    # Nivel 3
    st_n3 = "CONFORME [OK]" if reporte.nivel_3_reglas_sunat_validas else "FALLO [ERROR]"
    print(f"3. NIVEL 3 - Reglas de Negocio Locales SUNAT: {st_n3}")
    if reporte.errores_nivel_3_sunat:
        for err in reporte.errores_nivel_3_sunat:
            print(f"   - [ERROR REGLA] {err}")
    else:
        print(f"   - Se evaluaron satisfactoriamente {len(reporte.reglas_sunat_evaluadas)} reglas locales:")
        for r in reporte.reglas_sunat_evaluadas:
            print(f"     * {r}")

    # Reglas externas
    print("-" * 80)
    print("REGLAS EXTERNAS NO EVALUABLES LOCALMENTE (Requieren servicios activos SUNAT/OSE/CA):")
    for ext_rule in reporte.reglas_externas_no_evaluables:
        print(f"   * {ext_rule}")

    print("=" * 80)
    resultado_final = "DOCUMENTO VÁLIDO Y APTO PARA ENVÍO" if reporte.es_valido else "DOCUMENTO INVÁLIDO"
    print(f"RESULTADO GLOBAL: {resultado_final}")
    print("=" * 80 + "\n")


def procesar_archivo_json(ruta_json: str, dir_salida: str, validador: SunatInvoiceValidator) -> str:
    """Procesa un archivo JSON, genera el XML correspondiente y lo valida."""
    with open(ruta_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc = cargar_documento_desde_dict(data)
    builder = InvoiceXmlBuilder(doc)

    ruta_xml = builder.guardar_en_archivo(dir_salida, encoding="ISO-8859-1")
    print(f"[+] XML generado exitosamente: {ruta_xml}")

    with open(ruta_xml, "rb") as f:
        xml_bytes = f.read()

    reporte = validador.validar_documento_completo(xml_bytes, nombre_archivo=ruta_xml)
    imprimir_reporte_validacion(reporte, ruta_xml)
    return ruta_xml


def generar_ejemplo_invalido(dir_salida: str, validador: SunatInvoiceValidator) -> str:
    """Genera un archivo XML deliberadamente inválido para demostrar la detección de fallos XSD y de negocio."""
    ruta_invalido = os.path.join(dir_salida, "invalid_invoice_example.xml")

    # XML alterado intencionalmente:
    # 1. Falta el elemento obligatorio cac:AccountingCustomerParty
    # 2. La versión de UBL es '1.0' en lugar de '2.1'
    # 3. Importes alterados e inconsistentes
    xml_corrupto = b"""<?xml version='1.0' encoding='ISO-8859-1'?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:UBLVersionID>1.0</cbc:UBLVersionID>
    <cbc:ID>F001-99999999</cbc:ID>
    <cbc:IssueDate>2026-11-12</cbc:IssueDate>
    <cbc:InvoiceTypeCode>01</cbc:InvoiceTypeCode>
    <cbc:DocumentCurrencyCode>PEN</cbc:DocumentCurrencyCode>
    <!-- FALTA AccountingSupplierParty OBLIGATORIO SEGUN XSD -->
    <!-- FALTA AccountingCustomerParty OBLIGATORIO SEGUN XSD -->
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="PEN">100.00</cbc:LineExtensionAmount>
        <cbc:TaxInclusiveAmount currencyID="PEN">118.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="PEN">118.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    <cac:InvoiceLine>
        <cbc:ID>1</cbc:ID>
        <cbc:InvoicedQuantity unitCode="NIU">1.00</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="PEN">100.00</cbc:LineExtensionAmount>
        <cac:Item>
            <cbc:Description>Item de Prueba Invalido</cbc:Description>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="PEN">100.00</cbc:PriceAmount>
        </cac:Price>
    </cac:InvoiceLine>
</Invoice>
"""
    with open(ruta_invalido, "wb") as f:
        f.write(xml_corrupto)

    print(f"[!] Ejemplo intencionalmente inválido generado en: {ruta_invalido}")
    reporte = validador.validar_documento_completo(xml_corrupto, nombre_archivo=ruta_invalido)
    imprimir_reporte_validacion(reporte, ruta_invalido)
    return ruta_invalido


def main():
    parser = argparse.ArgumentParser(
        description="Generador y Validador de Facturas Electrónicas SUNAT UBL 2.1 (OASIS UBL 2.1)"
    )
    parser.add_argument(
        "--input",
        "-i",
        help="Ruta al archivo JSON de entrada con los datos de la factura",
        default=None,
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Directorio de destino para los archivos XML generados",
        default=None,
    )
    parser.add_argument(
        "--validate-only",
        "-v",
        help="Ruta al archivo XML existente para validar directamente",
        default=None,
    )

    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dir_salida = args.output_dir or os.path.join(base_dir, "generated")
    os.makedirs(dir_salida, exist_ok=True)

    validador = SunatInvoiceValidator()

    if args.validate_only:
        if not os.path.isfile(args.validate_only):
            print(f"[ERROR] No existe el archivo: {args.validate_only}")
            sys.exit(1)
        with open(args.validate_only, "rb") as f:
            xml_bytes = f.read()
        rep = validador.validar_documento_completo(xml_bytes, nombre_archivo=args.validate_only)
        imprimir_reporte_validacion(rep, args.validate_only)
        sys.exit(0 if rep.es_valido else 1)

    if args.input:
        procesar_archivo_json(args.input, dir_salida, validador)
    else:
        # Modo demostración completo: procesa el caso al contado, el caso al crédito y genera el caso inválido
        print("\n" + "#" * 80)
        print("DEMOSTRACIÓN DE FACTURACIÓN ELECTRÓNICA PERUANA SUNAT UBL 2.1")
        print("#" * 80 + "\n")

        # 1. Caso de Estudio al Contado (Gravado y Exonerado)
        json_contado = os.path.join(base_dir, "data", "invoice_input.json")
        print("[1/3] Procesando Caso de Estudio Principal (Venta al Contado)...")
        procesar_archivo_json(json_contado, dir_salida, validador)

        # 2. Caso de Estudio al Crédito (Cuotas y Vencimientos)
        json_credito = os.path.join(base_dir, "data", "invoice_input_credit.json")
        print("[2/3] Procesando Caso de Estudio al Crédito con Cuotas (D.U. 013-2020)...")
        procesar_archivo_json(json_credito, dir_salida, validador)

        # 3. Caso Intencionalmente Inválido
        print("[3/3] Demostración de Detección de Errores con XML Inválido...")
        generar_ejemplo_invalido(dir_salida, validador)

        print("\n[OK] Demostración completada con éxito.")


if __name__ == "__main__":
    main()

