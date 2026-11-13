"""Generador dinámico de XML UBL 2.1 para Facturación Electrónica SUNAT.

Construye la estructura de elementos conforme a los esquemas OASIS UBL 2.1 e instructivos SUNAT,
respetando estrictamente los namespaces, orden de secuencia de nodos XSD y codificación ISO-8859-1.
"""

from decimal import Decimal
from lxml import etree
from typing import Optional, Tuple
from src.calculations import calcular_totales_factura, validar_condiciones_pago
from src.models import (
    CalculatedLineItem,
    InvoiceCalculations,
    InvoiceDocument,
    PaymentTerms,
)
from src.validators import (
    formatear_nombre_archivo_xml,
    validar_documento_identidad,
    validar_ruc,
    validar_serie_correlativo,
    ValidationError,
)

# Definición de Namespaces oficiales OASIS UBL 2.1
NS_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"

NSMAP = {
    None: NS_INVOICE,
    "cac": NS_CAC,
    "cbc": NS_CBC,
    "ext": NS_EXT,
    "ds": NS_DS,
}

# Claves QName para creación rápida de elementos
def qname_inv(tag: str) -> etree.QName:
    return etree.QName(NS_INVOICE, tag)

def qname_cac(tag: str) -> etree.QName:
    return etree.QName(NS_CAC, tag)

def qname_cbc(tag: str) -> etree.QName:
    return etree.QName(NS_CBC, tag)

def qname_ext(tag: str) -> etree.QName:
    return etree.QName(NS_EXT, tag)

def qname_ds(tag: str) -> etree.QName:
    return etree.QName(NS_DS, tag)


class InvoiceXmlBuilder:
    """Constructor dinámico del documento XML de Factura Electrónica UBL 2.1."""

    def __init__(self, documento: InvoiceDocument):
        self.documento = documento
        self._validar_precondiciones()
        self.calculos: InvoiceCalculations = calcular_totales_factura(self.documento)
        if self.documento.terminos_pago:
            validar_condiciones_pago(
                self.documento.terminos_pago,
                self.calculos.importe_total_pagar,
                self.documento.fecha_emision,
            )

    def _validar_precondiciones(self) -> None:
        """Verifica la validez de los datos de entrada antes de generar el XML."""
        # Validación de RUC del emisor (obligatorio tipo 6 para factura)
        validar_ruc(self.documento.emisor.numero_documento, estricto=True)
        if self.documento.emisor.tipo_documento_identidad != "6":
            raise ValidationError("El tipo de documento del emisor debe ser '6' (RUC).")

        # Validación del documento del cliente (en Factura 01 debe ser RUC '6')
        val_cliente, msg_cliente = validar_documento_identidad(
            self.documento.cliente.numero_documento,
            self.documento.cliente.tipo_documento_identidad,
        )
        if not val_cliente:
            raise ValidationError(f"Documento del cliente inválido: {msg_cliente}")

        if self.documento.tipo_documento == "01" and self.documento.cliente.tipo_documento_identidad != "6":
            raise ValidationError(
                f"Para Factura electrónica (01), el cliente debe identificarse con RUC ('6'), "
                f"recibido: '{self.documento.cliente.tipo_documento_identidad}'."
            )

        # Validación de serie y correlativo
        val_sc, msg_sc = validar_serie_correlativo(
            self.documento.tipo_documento,
            self.documento.serie,
            self.documento.correlativo,
        )
        if not val_sc:
            raise ValidationError(msg_sc)

    def obtener_nombre_archivo(self, padding_correlativo: int = 8) -> str:
        """Devuelve el nombre de archivo reglamentario según estándar SUNAT."""
        return formatear_nombre_archivo_xml(
            ruc_emisor=self.documento.emisor.numero_documento,
            tipo_documento=self.documento.tipo_documento,
            serie=self.documento.serie,
            correlativo=self.documento.correlativo,
            padding_correlativo=padding_correlativo,
        )

    def construir_arbol(self) -> etree._Element:
        """Genera el árbol DOM del XML respetando la secuencia exacta de UBL 2.1."""
        doc = self.documento
        calc = self.calculos

        # Elemento raíz <Invoice>
        root = etree.Element(qname_inv("Invoice"), nsmap=NSMAP)

        # 1. ext:UBLExtensions (sección oficial para firma electrónica digital en UBL 2.1)
        exts = etree.SubElement(root, qname_ext("UBLExtensions"))
        ext = etree.SubElement(exts, qname_ext("UBLExtension"))
        content = etree.SubElement(ext, qname_ext("ExtensionContent"))

        # Nodo ds:Signature como apex element válido bajo ExtensionContentType (##other processContents=lax)
        sig_ext = etree.SubElement(content, qname_ds("Signature"), Id=f"Signature-{doc.emisor.numero_documento}")
        signed_info = etree.SubElement(sig_ext, qname_ds("SignedInfo"))
        etree.SubElement(signed_info, qname_ds("CanonicalizationMethod"), Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        etree.SubElement(signed_info, qname_ds("SignatureMethod"), Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1")
        ref_sig = etree.SubElement(signed_info, qname_ds("Reference"), URI="")
        transforms = etree.SubElement(ref_sig, qname_ds("Transforms"))
        etree.SubElement(transforms, qname_ds("Transform"), Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature")
        etree.SubElement(ref_sig, qname_ds("DigestMethod"), Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
        digest_val = etree.SubElement(ref_sig, qname_ds("DigestValue"))
        digest_val.text = "MDAwMDAwMDAwMDAwMDAwMDAwMDA="
        sig_val = etree.SubElement(sig_ext, qname_ds("SignatureValue"))
        sig_val.text = "MDAwMDAwMDAwMA=="
        key_info = etree.SubElement(sig_ext, qname_ds("KeyInfo"))
        x509_data = etree.SubElement(key_info, qname_ds("X509Data"))
        x509_cert = etree.SubElement(x509_data, qname_ds("X509Certificate"))
        x509_cert.text = "MDAwMDAwMDAwMA=="

        # 2. cbc:UBLVersionID (2.1)
        ubl_ver = etree.SubElement(root, qname_cbc("UBLVersionID"))
        ubl_ver.text = "2.1"

        # 3. cbc:CustomizationID (2.0 según norma técnica SUNAT UBL 2.1)
        cust_id = etree.SubElement(root, qname_cbc("CustomizationID"), schemeAgencyName="PE:SUNAT")
        cust_id.text = "2.0"

        # 4. cbc:ID (Serie-Número)
        correlativo_str = str(doc.correlativo).zfill(8)
        invoice_id = f"{doc.serie.upper()}-{correlativo_str}"
        id_elem = etree.SubElement(root, qname_cbc("ID"))
        id_elem.text = invoice_id

        # 5. cbc:IssueDate (YYYY-MM-DD)
        issue_date = etree.SubElement(root, qname_cbc("IssueDate"))
        issue_date.text = doc.fecha_emision

        # 6. cbc:IssueTime (hh:mm:ss)
        if doc.hora_emision:
            issue_time = etree.SubElement(root, qname_cbc("IssueTime"))
            issue_time.text = doc.hora_emision

        # 7. cbc:DueDate (YYYY-MM-DD) - Opcional
        if doc.fecha_vencimiento:
            due_date = etree.SubElement(root, qname_cbc("DueDate"))
            due_date.text = doc.fecha_vencimiento

        # 8. cbc:InvoiceTypeCode (Catálogo 01)
        inv_type = etree.SubElement(
            root,
            qname_cbc("InvoiceTypeCode"),
            listAgencyName="PE:SUNAT",
            listName="Tipo de Documento",
            listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01",
            listID=doc.tipo_operacion,
        )
        inv_type.text = doc.tipo_documento

        # 9. cbc:Note (Leyendas del Catálogo 52)
        for cod_leyenda, texto_leyenda in doc.leyendas.items():
            note = etree.SubElement(root, qname_cbc("Note"), languageLocaleID=cod_leyenda)
            note.text = texto_leyenda

        # 10. cbc:DocumentCurrencyCode (Catálogo 02)
        curr = etree.SubElement(
            root,
            qname_cbc("DocumentCurrencyCode"),
            listID="ISO 4217 Alpha",
            listName="Currency",
            listAgencyName="United Nations Economic Commission for Europe",
        )
        curr.text = doc.moneda

        # 11. cac:Signature (Metadatos de la firma digital)
        sig = etree.SubElement(root, qname_cac("Signature"))
        sig_id = etree.SubElement(sig, qname_cbc("ID"))
        sig_id.text = invoice_id
        sig_party = etree.SubElement(sig, qname_cac("SignatoryParty"))
        sig_party_id = etree.SubElement(sig_party, qname_cac("PartyIdentification"))
        sig_party_id_val = etree.SubElement(sig_party_id, qname_cbc("ID"))
        sig_party_id_val.text = doc.emisor.numero_documento
        sig_party_name = etree.SubElement(sig_party, qname_cac("PartyName"))
        sig_party_name_val = etree.SubElement(sig_party_name, qname_cbc("Name"))
        sig_party_name_val.text = doc.emisor.razon_social
        sig_attach = etree.SubElement(sig, qname_cac("DigitalSignatureAttachment"))
        sig_ref = etree.SubElement(sig_attach, qname_cac("ExternalReference"))
        sig_uri = etree.SubElement(sig_ref, qname_cbc("URI"))
        sig_uri.text = f"#Signature-{doc.emisor.numero_documento}"

        # 12. cac:AccountingSupplierParty (Emisor)
        asp = etree.SubElement(root, qname_cac("AccountingSupplierParty"))
        party_emisor = etree.SubElement(asp, qname_cac("Party"))

        p_id = etree.SubElement(party_emisor, qname_cac("PartyIdentification"))
        p_id_val = etree.SubElement(
            p_id,
            qname_cbc("ID"),
            schemeID=doc.emisor.tipo_documento_identidad,
            schemeName="Documento de Identidad",
            schemeAgencyName="PE:SUNAT",
            schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06",
        )
        p_id_val.text = doc.emisor.numero_documento

        if doc.emisor.nombre_comercial:
            p_name = etree.SubElement(party_emisor, qname_cac("PartyName"))
            p_name_val = etree.SubElement(p_name, qname_cbc("Name"))
            p_name_val.text = doc.emisor.nombre_comercial

        ple = etree.SubElement(party_emisor, qname_cac("PartyLegalEntity"))
        reg_name = etree.SubElement(ple, qname_cbc("RegistrationName"))
        reg_name.text = doc.emisor.razon_social

        if doc.emisor.direccion:
            dir_e = doc.emisor.direccion
            reg_addr = etree.SubElement(ple, qname_cac("RegistrationAddress"))
            ubig = etree.SubElement(
                reg_addr,
                qname_cbc("ID"),
                schemeAgencyName="PE:INEI",
                schemeName="Ubigeos",
            )
            ubig.text = dir_e.ubigeo
            addr_type = etree.SubElement(reg_addr, qname_cbc("AddressTypeCode"))
            addr_type.text = dir_e.codigo_local_anexo
            if dir_e.urbanizacion:
                urb = etree.SubElement(reg_addr, qname_cbc("CitySubdivisionName"))
                urb.text = dir_e.urbanizacion
            prov = etree.SubElement(reg_addr, qname_cbc("CityName"))
            prov.text = dir_e.provincia
            dpto = etree.SubElement(reg_addr, qname_cbc("CountrySubentity"))
            dpto.text = dir_e.departamento
            dist = etree.SubElement(reg_addr, qname_cbc("District"))
            dist.text = dir_e.distrito

            addr_line = etree.SubElement(reg_addr, qname_cac("AddressLine"))
            line_val = etree.SubElement(addr_line, qname_cbc("Line"))
            line_val.text = dir_e.direccion

            country = etree.SubElement(reg_addr, qname_cac("Country"))
            c_code = etree.SubElement(
                country,
                qname_cbc("IdentificationCode"),
                listID="ISO 3166-1",
                listAgencyName="United Nations Economic Commission for Europe",
                listName="Country",
            )
            c_code.text = dir_e.codigo_pais

        # 13. cac:AccountingCustomerParty (Receptor / Cliente)
        acp = etree.SubElement(root, qname_cac("AccountingCustomerParty"))
        party_cliente = etree.SubElement(acp, qname_cac("Party"))

        c_pid = etree.SubElement(party_cliente, qname_cac("PartyIdentification"))
        c_pid_val = etree.SubElement(
            c_pid,
            qname_cbc("ID"),
            schemeID=doc.cliente.tipo_documento_identidad,
            schemeName="Documento de Identidad",
            schemeAgencyName="PE:SUNAT",
            schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06",
        )
        c_pid_val.text = doc.cliente.numero_documento

        c_ple = etree.SubElement(party_cliente, qname_cac("PartyLegalEntity"))
        c_reg_name = etree.SubElement(c_ple, qname_cbc("RegistrationName"))
        c_reg_name.text = doc.cliente.razon_social

        if doc.cliente.direccion:
            dir_c = doc.cliente.direccion
            c_reg_addr = etree.SubElement(c_ple, qname_cac("RegistrationAddress"))
            c_ubig = etree.SubElement(c_reg_addr, qname_cbc("ID"), schemeAgencyName="PE:INEI", schemeName="Ubigeos")
            c_ubig.text = dir_c.ubigeo
            c_addr_line = etree.SubElement(c_reg_addr, qname_cac("AddressLine"))
            c_line_val = etree.SubElement(c_addr_line, qname_cbc("Line"))
            c_line_val.text = dir_c.direccion
            c_country = etree.SubElement(c_reg_addr, qname_cac("Country"))
            c_country_code = etree.SubElement(c_country, qname_cbc("IdentificationCode"), listID="ISO 3166-1", listAgencyName="United Nations Economic Commission for Europe", listName="Country")
            c_country_code.text = dir_c.codigo_pais

        # 14. cac:PaymentTerms (Términos de pago: Contado o Crédito)
        terminos = doc.terminos_pago or PaymentTerms(forma_pago="Contado")
        if terminos.forma_pago == "Contado":
            pt_contado = etree.SubElement(root, qname_cac("PaymentTerms"))
            pt_id = etree.SubElement(pt_contado, qname_cbc("ID"))
            pt_id.text = "FormaPago"
            pt_means = etree.SubElement(pt_contado, qname_cbc("PaymentMeansID"))
            pt_means.text = "Contado"
        else:  # 'Credito'
            # Encabezado de pago al crédito
            pt_credito = etree.SubElement(root, qname_cac("PaymentTerms"))
            pt_id = etree.SubElement(pt_credito, qname_cbc("ID"))
            pt_id.text = "FormaPago"
            pt_means = etree.SubElement(pt_credito, qname_cbc("PaymentMeansID"))
            pt_means.text = "Credito"
            pt_amount = etree.SubElement(pt_credito, qname_cbc("Amount"), currencyID=doc.moneda)
            pt_amount.text = f"{terminos.monto_neto_pendiente:.2f}"

            # Cuotas al crédito
            for cuota in terminos.cuotas:
                pt_cuota = etree.SubElement(root, qname_cac("PaymentTerms"))
                cuota_id = etree.SubElement(pt_cuota, qname_cbc("ID"))
                cuota_id.text = "FormaPago"
                cuota_means = etree.SubElement(pt_cuota, qname_cbc("PaymentMeansID"))
                cuota_means.text = cuota.id_cuota
                cuota_amount = etree.SubElement(pt_cuota, qname_cbc("Amount"), currencyID=doc.moneda)
                cuota_amount.text = f"{cuota.monto:.2f}"
                cuota_date = etree.SubElement(pt_cuota, qname_cbc("PaymentDueDate"))
                cuota_date.text = cuota.fecha_vencimiento

        # 15. cac:TaxTotal (Totales de tributos a nivel global)
        tax_total = etree.SubElement(root, qname_cac("TaxTotal"))
        tax_total_amount = etree.SubElement(tax_total, qname_cbc("TaxAmount"), currencyID=doc.moneda)
        tax_total_amount.text = f"{calc.total_impuestos:.2f}"

        for sub_trib in calc.subtotales_tributo.values():
            tax_subtotal = etree.SubElement(tax_total, qname_cac("TaxSubtotal"))
            taxable_amount = etree.SubElement(tax_subtotal, qname_cbc("TaxableAmount"), currencyID=doc.moneda)
            taxable_amount.text = f"{sub_trib.base_imponible:.2f}"
            tax_amount = etree.SubElement(tax_subtotal, qname_cbc("TaxAmount"), currencyID=doc.moneda)
            tax_amount.text = f"{sub_trib.monto_impuesto:.2f}"

            tax_cat = etree.SubElement(tax_subtotal, qname_cac("TaxCategory"))
            tax_scheme = etree.SubElement(tax_cat, qname_cac("TaxScheme"))
            sch_id = etree.SubElement(
                tax_scheme,
                qname_cbc("ID"),
                schemeID="UN/ECE 5153",
                schemeAgencyID="6",
            )
            sch_id.text = sub_trib.codigo_tributo
            sch_name = etree.SubElement(tax_scheme, qname_cbc("Name"))
            sch_name.text = sub_trib.nombre_tributo
            sch_type = etree.SubElement(tax_scheme, qname_cbc("TaxTypeCode"))
            sch_type.text = sub_trib.codigo_internacional

        # 16. cac:LegalMonetaryTotal (Totales monetarios legales)
        lmt = etree.SubElement(root, qname_cac("LegalMonetaryTotal"))
        line_ext = etree.SubElement(lmt, qname_cbc("LineExtensionAmount"), currencyID=doc.moneda)
        line_ext.text = f"{calc.total_valor_venta:.2f}"

        tax_inc = etree.SubElement(lmt, qname_cbc("TaxInclusiveAmount"), currencyID=doc.moneda)
        tax_inc.text = f"{calc.total_precio_venta:.2f}"

        pay_amount = etree.SubElement(lmt, qname_cbc("PayableAmount"), currencyID=doc.moneda)
        pay_amount.text = f"{calc.importe_total_pagar:.2f}"

        # 17. cac:InvoiceLine (Detalle de cada ítem)
        for linea in calc.lineas:
            line_elem = etree.SubElement(root, qname_cac("InvoiceLine"))

            # ID de línea
            lid = etree.SubElement(line_elem, qname_cbc("ID"))
            lid.text = str(linea.id_linea)

            # InvoicedQuantity
            qty = etree.SubElement(
                line_elem,
                qname_cbc("InvoicedQuantity"),
                unitCode=linea.unidad_medida,
                unitCodeListID="UN/ECE rec 20",
                unitCodeListAgencyName="United Nations Economic Commission for Europe",
            )
            qty.text = f"{linea.cantidad:.2f}"

            # LineExtensionAmount (Valor de venta ítem)
            lea = etree.SubElement(line_elem, qname_cbc("LineExtensionAmount"), currencyID=doc.moneda)
            lea.text = f"{linea.line_extension_amount:.2f}"

            # PricingReference
            pricing = etree.SubElement(line_elem, qname_cac("PricingReference"))
            alt_price = etree.SubElement(pricing, qname_cac("AlternativeConditionPrice"))
            p_amount = etree.SubElement(alt_price, qname_cbc("PriceAmount"), currencyID=doc.moneda)
            p_amount.text = f"{linea.precio_unitario:.2f}"
            p_type = etree.SubElement(
                alt_price,
                qname_cbc("PriceTypeCode"),
                listName="Tipo de Precio",
                listAgencyName="PE:SUNAT",
                listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16",
            )
            p_type.text = linea.codigo_tipo_precio

            # TaxTotal de la línea
            l_tax_total = etree.SubElement(line_elem, qname_cac("TaxTotal"))
            l_tax_amount = etree.SubElement(l_tax_total, qname_cbc("TaxAmount"), currencyID=doc.moneda)
            l_tax_amount.text = f"{linea.monto_total_impuestos_linea:.2f}"

            l_tax_subtotal = etree.SubElement(l_tax_total, qname_cac("TaxSubtotal"))
            l_taxable = etree.SubElement(l_tax_subtotal, qname_cbc("TaxableAmount"), currencyID=doc.moneda)
            l_taxable.text = f"{linea.base_imponible_igv:.2f}"
            l_sub_tax_amount = etree.SubElement(l_tax_subtotal, qname_cbc("TaxAmount"), currencyID=doc.moneda)
            l_sub_tax_amount.text = f"{linea.monto_igv:.2f}"

            l_tax_cat = etree.SubElement(l_tax_subtotal, qname_cac("TaxCategory"))
            l_pct = etree.SubElement(l_tax_cat, qname_cbc("Percent"))
            l_pct.text = f"{linea.tasa_igv:.2f}"

            l_exempt = etree.SubElement(
                l_tax_cat,
                qname_cbc("TaxExemptionReasonCode"),
                listAgencyName="PE:SUNAT",
                listName="Afectacion del IGV",
                listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07",
            )
            l_exempt.text = linea.codigo_afectacion_igv

            l_tax_scheme = etree.SubElement(l_tax_cat, qname_cac("TaxScheme"))
            l_sch_id = etree.SubElement(
                l_tax_scheme,
                qname_cbc("ID"),
                schemeID="UN/ECE 5153",
                schemeAgencyID="6",
            )
            l_sch_id.text = linea.codigo_tributo
            l_sch_name = etree.SubElement(l_tax_scheme, qname_cbc("Name"))
            l_sch_name.text = linea.nombre_tributo
            l_sch_type = etree.SubElement(l_tax_scheme, qname_cbc("TaxTypeCode"))
            l_sch_type.text = linea.codigo_internacional_tributo

            # Item
            item_elem = etree.SubElement(line_elem, qname_cac("Item"))
            desc = etree.SubElement(item_elem, qname_cbc("Description"))
            desc.text = linea.descripcion

            if linea.codigo_producto:
                s_ident = etree.SubElement(item_elem, qname_cac("SellersItemIdentification"))
                s_id = etree.SubElement(s_ident, qname_cbc("ID"))
                s_id.text = linea.codigo_producto

            if linea.codigo_producto_sunat:
                comm = etree.SubElement(item_elem, qname_cac("CommodityClassification"))
                c_code = etree.SubElement(
                    comm,
                    qname_cbc("ItemClassificationCode"),
                    listID="UNSPSC",
                    listAgencyName="GS1 US",
                    listName="Item Classification",
                )
                c_code.text = linea.codigo_producto_sunat

            # Price (Valor unitario antes de impuestos)
            price_elem = etree.SubElement(line_elem, qname_cac("Price"))
            pr_amount = etree.SubElement(price_elem, qname_cbc("PriceAmount"), currencyID=doc.moneda)
            pr_amount.text = f"{linea.valor_unitario:.2f}"

        return root

    def generar_xml_bytes(self, encoding: str = "ISO-8859-1") -> bytes:
        """Serializa el árbol XML a bytes con declaración XML y codificación especificada (ISO-8859-1)."""
        arbol = self.construir_arbol()
        return etree.tostring(
            arbol,
            encoding=encoding,
            xml_declaration=True,
            pretty_print=True,
        )

    def guardar_en_archivo(self, ruta_directorio: str, encoding: str = "ISO-8859-1") -> str:
        """Guarda el XML generado con el nombre de archivo reglamentario SUNAT."""
        import os
        os.makedirs(ruta_directorio, exist_ok=True)
        nombre_archivo = self.obtener_nombre_archivo()
        ruta_completa = os.path.join(ruta_directorio, nombre_archivo)
        xml_bytes = self.generar_xml_bytes(encoding=encoding)
        with open(ruta_completa, "wb") as f:
            f.write(xml_bytes)
        return ruta_completa
