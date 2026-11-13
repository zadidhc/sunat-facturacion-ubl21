"""Validador de 3 niveles para facturación electrónica SUNAT UBL 2.1.

Nivel 1: Validación sintáctica de documento bien formado (Well-formed XML) y codificación real de bytes.
Nivel 2: Validación estructural estricta contra el esquema XSD oficial OASIS UBL 2.1 (UBL-Invoice-2.1.xsd).
Nivel 3: Validación de reglas de negocio locales de SUNAT (consistencias de cálculo, nomenclatura y catálogos).
"""

import os
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from lxml import etree
from src.validators import (
    validar_ruc,
    validar_documento_identidad,
    validar_serie_correlativo,
)

DOS_DECIMALES = Decimal("0.01")


@dataclass
class ValidationReport:
    """Informe detallado de la auditoría y validación del XML."""
    es_valido: bool
    nivel_1_bien_formado: bool
    nivel_2_xsd_valido: bool
    nivel_3_reglas_sunat_validas: bool
    codificacion_detectada: str
    errores_nivel_1: List[str] = field(default_factory=list)
    errores_nivel_2_xsd: List[str] = field(default_factory=list)
    errores_nivel_3_sunat: List[str] = field(default_factory=list)
    reglas_sunat_evaluadas: List[str] = field(default_factory=list)
    reglas_externas_no_evaluables: List[str] = field(default_factory=list)


# Directorio por defecto de esquemas XSD oficiales OASIS UBL 2.1
DEFAULT_XSD_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "xsd",
        "maindoc",
        "UBL-Invoice-2.1.xsd",
    )
)


class SunatInvoiceValidator:
    """Motor de validación multi-nivel para facturas electrónicas SUNAT UBL 2.1."""

    def __init__(self, ruta_xsd: Optional[str] = None):
        self.ruta_xsd = ruta_xsd or DEFAULT_XSD_PATH
        if not os.path.isfile(self.ruta_xsd):
            raise FileNotFoundError(
                f"No se encontró el esquema XSD oficial en la ruta: {self.ruta_xsd}. "
                f"Asegúrese de extraer el paquete OASIS UBL 2.1 en la carpeta 'xsd/'."
            )
        self.xml_schema = self._cargar_esquema_xsd()

    def _cargar_esquema_xsd(self) -> etree.XMLSchema:
        """Compila el esquema XSD oficial OASIS UBL 2.1 y sus dependencias con lxml."""
        schema_doc = etree.parse(self.ruta_xsd)
        return etree.XMLSchema(schema_doc)

    def validar_nivel_1_bien_formado(self, xml_bytes: bytes) -> Tuple[bool, str, List[str]]:
        """Nivel 1: Verifica que el XML sea bien formado y coincida con la codificación declarada."""
        errores = []
        codificacion = "Desconocida"

        # Verificar declaración XML y codificación
        match_decl = re.search(rb"<\?xml\s+version=['\"]1\.0['\"]\s+encoding=['\"]([^'\"]+)['\"]\s*\?>", xml_bytes)
        if match_decl:
            codificacion = match_decl.group(1).decode("ascii", errors="ignore").upper()
        else:
            errores.append("No se encontró la declaración XML 1.0 estándar con atributo de codificación.")

        # Verificar decodificación real de los bytes
        try:
            if codificacion == "ISO-8859-1":
                xml_bytes.decode("iso-8859-1")
            elif codificacion == "UTF-8":
                xml_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            errores.append(f"Los bytes del archivo no coinciden con la codificación declarada '{codificacion}': {exc}")

        # Parsear con lxml para verificar que esté bien formado
        try:
            parser = etree.XMLParser(recover=False)
            etree.fromstring(xml_bytes, parser=parser)
        except etree.XMLSyntaxError as exc:
            errores.append(f"Error sintáctico de XML bien formado: {exc}")

        return (len(errores) == 0), codificacion, errores

    def validar_nivel_2_xsd(self, xml_tree: etree._Element) -> Tuple[bool, List[str]]:
        """Nivel 2: Valida estructuralmente contra el XSD oficial OASIS UBL-Invoice-2.1.xsd."""
        errores = []
        es_valido = self.xml_schema.validate(xml_tree)
        if not es_valido:
            for error in self.xml_schema.error_log:
                errores.append(
                    f"Línea {error.line}, Columna {error.column}: {error.message} (Dominio: {error.domain_name})"
                )
        return es_valido, errores

    def validar_nivel_3_reglas_sunat(
        self,
        xml_tree: etree._Element,
        nombre_archivo: Optional[str] = None,
    ) -> Tuple[bool, List[str], List[str], List[str]]:
        """Nivel 3: Valida las reglas de negocio locales de SUNAT aplicables al comprobante."""
        errores = []
        reglas_locales = []
        reglas_externas = [
            "Regla 2010: Estado activo del RUC del emisor en los padrones de SUNAT (requiere consulta al RUC / padrón SUNAT)",
            "Regla 2011: Condición de habido del RUC del emisor en SUNAT (requiere consulta al RUC / padrón SUNAT)",
            "Regla 4013/4014: Estado activo y condición de habido del receptor en SUNAT (requiere servicio externo)",
            "Regla 1078/2012: Autorización de emisor electrónico en el sistema SEE-Desde los sistemas del contribuyente u OSE",
            "Regla 1033: Comprobante no informado previamente con otros datos en servidores de SUNAT (duplicidad)",
            "Regla 2325/2326: Validación del certificado digital ante la Entidad de Certificación acreditada / CA de SUNAT",
            "Regla 2335: Integridad criptográfica de la firma digital XAdES-BES (verificación con clave pública del emisor)",
            "Constancia de Recepción (CDR): Generación de respuesta oficial firmada por OSE o SUNAT",
        ]

        ns = {
            "inv": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        }

        def xpath_text(path: str) -> Optional[str]:
            res = xml_tree.xpath(path, namespaces=ns)
            return res[0].text if res and res[0].text else None

        # 1. Versión UBL y CustomizationID
        ubl_ver = xpath_text("/inv:Invoice/cbc:UBLVersionID")
        reglas_locales.append("Regla 2074: UBLVersionID debe ser exactamente '2.1'")
        if ubl_ver != "2.1":
            errores.append(f"Regla 2074: UBLVersionID esperado '2.1', encontrado '{ubl_ver}'.")

        cust_id = xpath_text("/inv:Invoice/cbc:CustomizationID")
        reglas_locales.append("Regla 2072: CustomizationID debe ser exactamente '2.0'")
        if cust_id != "2.0":
            errores.append(f"Regla 2072: CustomizationID esperado '2.0', encontrado '{cust_id}'.")

        # 2. Datos de identificación y numeración
        doc_id = xpath_text("/inv:Invoice/cbc:ID")
        tipo_doc = xpath_text("/inv:Invoice/cbc:InvoiceTypeCode")
        emisor_ruc = xpath_text("/inv:Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID")
        emisor_tipo_doc = xml_tree.xpath(
            "/inv:Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID/@schemeID",
            namespaces=ns,
        )
        emisor_tipo_doc_val = emisor_tipo_doc[0] if emisor_tipo_doc else None

        reglas_locales.append("Regla 1008/1007: Tipo de documento del emisor debe ser '6' (RUC)")
        if emisor_tipo_doc_val != "6":
            errores.append(f"Regla 1007: El atributo @schemeID del emisor debe ser '6', recibido: '{emisor_tipo_doc_val}'.")

        # 3. Validación de algoritmo de RUC del emisor (módulo 11)
        reglas_locales.append("Regla 1034: Verificación sintáctica y de dígito verificador módulo 11 del RUC del emisor")
        if emisor_ruc:
            res_ruc = validar_ruc(emisor_ruc, estricto=False)
            if not res_ruc.es_valido:
                errores.append(f"RUC de emisor inválido: {res_ruc.mensaje}")

        # 4. Datos del receptor
        cliente_num = xpath_text("/inv:Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID")
        cliente_tipo = xml_tree.xpath(
            "/inv:Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID/@schemeID",
            namespaces=ns,
        )
        cliente_tipo_val = cliente_tipo[0] if cliente_tipo else None

        reglas_locales.append("Regla 2017/2800: Receptor de factura comercial (01) debe ser RUC (tipo '6') válido")
        if tipo_doc == "01":
            if cliente_tipo_val != "6":
                errores.append(f"Regla 2800: En Factura (01), el cliente debe tener tipo documento '6' (RUC), encontrado: '{cliente_tipo_val}'.")
            if cliente_num:
                res_c_ruc = validar_ruc(cliente_num, estricto=False)
                if not res_c_ruc.es_valido:
                    errores.append(f"RUC de cliente inválido: {res_c_ruc.mensaje}")

        # 5. Coincidencia de nombre de archivo si se proporciona
        if nombre_archivo:
            reglas_locales.append("Regla 1003/1034/1035/1036: Coincidencia del nombre de archivo con RUC, tipo, serie y número")
            # Estructura esperada: RUC-TIPO-SERIE-CORRELATIVO.xml
            patron_fn = r"^([0-9]{11})-([0-9]{2})-([A-Z0-9]{4})-([0-9]{1,8})\.xml$"
            m_fn = re.match(patron_fn, os.path.basename(nombre_archivo), re.IGNORECASE)
            if not m_fn:
                errores.append(f"El nombre de archivo '{nombre_archivo}' no cumple con el formato RRRRRRRRRRR-TT-SSSS-NNNNNNNN.xml")
            else:
                fn_ruc, fn_tipo, fn_serie, fn_corr = m_fn.groups()
                if fn_ruc != emisor_ruc:
                    errores.append(f"Regla 1034: RUC del archivo ({fn_ruc}) no coincide con el RUC del XML ({emisor_ruc}).")
                if fn_tipo != tipo_doc:
                    errores.append(f"Regla 1003: Tipo documento del archivo ({fn_tipo}) no coincide con el XML ({tipo_doc}).")
                if doc_id:
                    partes_id = doc_id.split("-")
                    if len(partes_id) == 2:
                        id_serie, id_corr = partes_id
                        if fn_serie.upper() != id_serie.upper():
                            errores.append(f"Regla 1035: Serie del archivo ({fn_serie}) no coincide con el XML ({id_serie}).")
                        if int(fn_corr) != int(id_corr):
                            errores.append(f"Regla 1036: Número de comprobante del archivo ({fn_corr}) no coincide con el XML ({id_corr}).")

        # 6. Moneda única en comprobante
        doc_moneda = xpath_text("/inv:Invoice/cbc:DocumentCurrencyCode")
        reglas_locales.append("Regla 2071: La moneda debe ser la misma en todo el documento")
        currency_attrs = xml_tree.xpath("//@currencyID")
        for curr in currency_attrs:
            if curr != doc_moneda:
                errores.append(f"Regla 2071: Se encontró moneda '{curr}' distinta a la cabecera '{doc_moneda}'.")

        # 7. Verificación de cálculos aritméticos de ítems y totales
        reglas_locales.append("Regla 3271/3278: Coincidencia aritmética de valor de venta de ítems y Total Valor de Venta")
        lines = xml_tree.xpath("/inv:Invoice/cac:InvoiceLine", namespaces=ns)
        suma_line_extensions = Decimal("0.00")
        suma_igv_lines = Decimal("0.00")

        for line in lines:
            lid = line.xpath("cbc:ID/text()", namespaces=ns)[0]
            qty_str = line.xpath("cbc:InvoicedQuantity/text()", namespaces=ns)[0]
            val_unit_str = line.xpath("cac:Price/cbc:PriceAmount/text()", namespaces=ns)[0]
            line_ext_str = line.xpath("cbc:LineExtensionAmount/text()", namespaces=ns)[0]

            qty = Decimal(qty_str)
            val_unit = Decimal(val_unit_str)
            line_ext = Decimal(line_ext_str)

            calc_line_ext = (qty * val_unit).quantize(DOS_DECIMALES)
            if abs(calc_line_ext - line_ext) > Decimal("0.01"):
                errores.append(
                    f"Regla 3271: En línea {lid}, valor de venta {line_ext} difiere del cálculo {qty} * {val_unit} = {calc_line_ext}."
                )

            suma_line_extensions += line_ext

            igv_str = line.xpath("cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount/text()", namespaces=ns)
            if igv_str:
                suma_igv_lines += Decimal(igv_str[0])

        total_valor_venta_str = xpath_text("/inv:Invoice/cac:LegalMonetaryTotal/cbc:LineExtensionAmount")
        if total_valor_venta_str:
            tot_vv = Decimal(total_valor_venta_str)
            if abs(tot_vv - suma_line_extensions) > Decimal("0.01"):
                errores.append(
                    f"Regla 3278: Total Valor de Venta ({tot_vv}) difiere de la sumatoria de líneas ({suma_line_extensions})."
                )

        reglas_locales.append("Regla 3294: Coincidencia de la sumatoria de impuestos globales con los impuestos de línea")
        total_tax_str = xpath_text("/inv:Invoice/cac:TaxTotal/cbc:TaxAmount")
        if total_tax_str:
            tot_tax = Decimal(total_tax_str)
            if abs(tot_tax - suma_igv_lines) > Decimal("0.01"):
                errores.append(
                    f"Regla 3294: Total de impuestos ({tot_tax}) difiere de la sumatoria de impuestos de línea ({suma_igv_lines})."
                )

        reglas_locales.append("Regla 3280: Importe Total a Pagar = Total Valor Venta + Total Impuestos")
        total_pagar_str = xpath_text("/inv:Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount")
        if total_pagar_str and total_valor_venta_str and total_tax_str:
            tot_pagar = Decimal(total_pagar_str)
            tot_esperado = Decimal(total_valor_venta_str) + Decimal(total_tax_str)
            if abs(tot_pagar - tot_esperado) > Decimal("0.01"):
                errores.append(
                    f"Regla 3280: PayableAmount ({tot_pagar}) difiere de Valor Venta + Impuestos ({tot_esperado})."
                )

        # 8. Verificación de Forma de Pago y Cuotas
        reglas_locales.append("Regla 3244-3256: Forma de pago Contado/Crédito y consistencia de cuotas")
        pt_nodes = xml_tree.xpath("/inv:Invoice/cac:PaymentTerms", namespaces=ns)
        has_contado = False
        has_credito = False
        cuotas_sum = Decimal("0.00")
        monto_credito = None

        for pt in pt_nodes:
            pt_id = pt.xpath("cbc:ID/text()", namespaces=ns)
            pt_means = pt.xpath("cbc:PaymentMeansID/text()", namespaces=ns)
            if pt_id and pt_id[0] == "FormaPago" and pt_means:
                means = pt_means[0]
                if means == "Contado":
                    has_contado = True
                elif means == "Credito":
                    has_credito = True
                    amt_str = pt.xpath("cbc:Amount/text()", namespaces=ns)
                    if amt_str:
                        monto_credito = Decimal(amt_str[0])
                elif means.startswith("Cuota"):
                    c_amt_str = pt.xpath("cbc:Amount/text()", namespaces=ns)
                    c_date_str = pt.xpath("cbc:PaymentDueDate/text()", namespaces=ns)
                    issue_date_str = xpath_text("/inv:Invoice/cbc:IssueDate")
                    if c_amt_str:
                        cuotas_sum += Decimal(c_amt_str[0])
                    if c_date_str and issue_date_str:
                        if c_date_str[0] <= issue_date_str:
                            errores.append(
                                f"Regla 3267: Fecha de cuota ({c_date_str[0]}) no puede ser anterior o igual a la emisión ({issue_date_str})."
                            )

        if has_contado and has_credito:
            errores.append("Regla 3247: El comprobante no puede consignar a la vez forma de pago 'Contado' y 'Credito'.")

        if has_credito:
            if monto_credito is None:
                errores.append("Regla 3251: Si la transacción es al crédito, debe consignarse el monto neto pendiente de pago.")
            elif abs(cuotas_sum - monto_credito) > Decimal("0.01"):
                errores.append(
                    f"Regla 3319: La suma de cuotas ({cuotas_sum}) debe ser igual al monto neto pendiente ({monto_credito})."
                )

        es_valido = len(errores) == 0
        return es_valido, errores, reglas_locales, reglas_externas

    def validar_documento_completo(
        self,
        xml_bytes: bytes,
        nombre_archivo: Optional[str] = None,
    ) -> ValidationReport:
        """Ejecuta los 3 niveles de validación sobre el documento XML."""
        # Nivel 1
        n1_ok, codificacion, n1_errores = self.validar_nivel_1_bien_formado(xml_bytes)
        if not n1_ok:
            return ValidationReport(
                es_valido=False,
                nivel_1_bien_formado=False,
                nivel_2_xsd_valido=False,
                nivel_3_reglas_sunat_validas=False,
                codificacion_detectada=codificacion,
                errores_nivel_1=n1_errores,
            )

        parser = etree.XMLParser(recover=False)
        xml_tree = etree.fromstring(xml_bytes, parser=parser)

        # Nivel 2: XSD oficial
        n2_ok, n2_errores = self.validar_nivel_2_xsd(xml_tree)

        # Nivel 3: Reglas de negocio SUNAT
        n3_ok, n3_errores, reglas_locales, reglas_externas = self.validar_nivel_3_reglas_sunat(
            xml_tree,
            nombre_archivo=nombre_archivo,
        )

        es_valido_global = n1_ok and n2_ok and n3_ok

        return ValidationReport(
            es_valido=es_valido_global,
            nivel_1_bien_formado=n1_ok,
            nivel_2_xsd_valido=n2_ok,
            nivel_3_reglas_sunat_validas=n3_ok,
            codificacion_detectada=codificacion,
            errores_nivel_1=n1_errores,
            errores_nivel_2_xsd=n2_errores,
            errores_nivel_3_sunat=n3_errores,
            reglas_sunat_evaluadas=reglas_locales,
            reglas_externas_no_evaluables=reglas_externas,
        )

