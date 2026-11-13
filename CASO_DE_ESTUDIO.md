# Caso de Estudio Empresarial: Facturación Electrónica SUNAT UBL 2.1

**Proyecto Académico:** Arquitectura de Software — Segundo Examen Parcial  
**Autor:** Antigravity Architecture & E-Invoicing Team  
**Estándar:** OASIS Universal Business Language (UBL) 2.1 — SUNAT CPE  
**Lenguaje y Entorno:** Python 3.11+, `lxml`, `pytest`, `Decimal`  

---

## 1. Identificación de la Empresa Emisora y Actividad Económica

La empresa emisora del comprobante es una persona jurídica ficticia debidamente domiciliada en el Perú:

* **Razón Social:** TECNOLOGÍA Y SISTEMAS DEL SUR S.A.C.
* **Nombre Comercial:** TECSUR PERÚ
* **Número de RUC:** `20605389458` (RUC válido verificado mediante algoritmo oficial Módulo 11 de SUNAT, con prefijo 20 de persona jurídica y dígito verificador 8).
* **Tipo de Documento de Identidad:** `6` (Registro Único de Contribuyentes, Catálogo 06).
* **Domicilio Fiscal Principal:** Av. República de Panamá 3545, Of. 801, Urbanización San Borja Sur, Distrito de San Isidro, Provincia de Lima, Departamento de Lima, Perú.
* **Código de Ubigeo INEI:** `150131` (Catálogo 13).
* **Código de Establecimiento Anexo:** `0000` (domicilio fiscal principal declarado en el RUC).
* **Actividad Económica:** Venta mayorista de equipamiento informático empresarial, provisión de servidores para centros de datos, consultoría técnica en arquitectura de sistemas distribuidos y comercialización de publicaciones técnicas especializadas.

---

## 2. Identificación del Cliente (Adquirente) y Bienes Vendidos

El cliente adquirente es una persona jurídica que requiere equipamiento para la ampliación de su infraestructura tecnológica:

* **Razón Social:** DISTRIBUIDORA INDUSTRIAL LIMA NORTE S.A.C.
* **Nombre Comercial:** LIMA NORTE DISTRIBUCIONES
* **Número de RUC:** `20552103816` (RUC válido verificado con Módulo 11, prefijo 20 y dígito verificador 6).
* **Tipo de Documento de Identidad:** `6` (RUC, Catálogo 06).
* **Domicilio Fiscal:** Av. Alfredo Mendiola 1400, Urb. Panamericana, Distrito de Los Olivos, Provincia de Lima, Departamento de Lima.
* **Código de Ubigeo INEI:** `150117` (Catálogo 13).

### Bienes y Servicios Objeto de la Operación

La transacción incluye tres conceptos que permiten ilustrar el tratamiento diferenciado de operaciones gravadas con el IGV y operaciones exoneradas:

1. **Ítem 1 (Bien Tangible Gravado):**
   * **Descripción:** `Servidor Rack 2U Enterprise Xeon 32GB RAM 2TB SSD`
   * **Código Interno:** `SRV-2U-XEON`
   * **Código UNSPSC (Catálogo 25):** `43211501` (Servidores informáticos)
   * **Cantidad:** `2.00` unidades (`NIU`, Catálogo 03)
   * **Valor Unitario:** `S/ 4,500.00` (sin IGV)
   * **Afectación al IGV:** `10` (Gravado - Operación Onerosa, Catálogo 07)

2. **Ítem 2 (Servicio Especializado Gravado):**
   * **Descripción:** `Servicio de Instalacion, Configuracion de Red y Puesta en Marcha`
   * **Código Interno:** `SRV-INST-01`
   * **Código UNSPSC (Catálogo 25):** `81111801` (Servicios de configuración de sistemas de computación)
   * **Cantidad:** `1.00` servicio (`ZZ`, Catálogo 03)
   * **Valor Unitario:** `S/ 800.00` (sin IGV)
   * **Afectación al IGV:** `10` (Gravado - Operación Onerosa, Catálogo 07)

3. **Ítem 3 (Bien Cultural Exonerado):**
   * **Descripción:** `Manual Tecnico de Arquitectura de Sistemas y E-Invoicing UBL 2.1 (Libro)`
   * **Código Interno:** `LIB-UBL-21`
   * **Código UNSPSC (Catálogo 25):** `55101509` (Libros o publicaciones impresas)
   * **Cantidad:** `1.00` unidad (`NIU`, Catálogo 03)
   * **Valor Unitario:** `S/ 250.00` (sin IGV)
   * **Afectación al IGV:** `20` (Exonerado - Operación Onerosa, Catálogo 07, amparado en la Ley de Democratización del Libro).

---

## 3. Motivo y Justificación de la Emisión Electrónica

La presente operación corresponde a una **Venta Interna** autorizada bajo el Sistema de Emisión Electrónica (SEE) de la SUNAT:

* **Tipo de Documento (Catálogo 01):** `01` (Factura Electrónica).
* **Tipo de Operación (Catálogo 51):** `0101` (Venta interna no sujeta a Detracción o Percepción).
* **Justificación Tributaria:** La factura electrónica permite al adquirente sustentar gasto y costo para el Impuesto a la Renta de tercera categoría (según artículo 37 de la Ley del Impuesto a la Renta) y ejercer el derecho al Crédito Fiscal respecto al IGV facturado (artículo 18 y 19 de la Ley del IGV).
* **Moneda de Emisión:** Soles (`PEN`, Catálogo 02).

---

## 4. Desglose de Elementos XML UBL 2.1 y su Significado

El documento XML generado sigue estrictamente la jerarquía definida en el estándar OASIS UBL 2.1 y las reglas de validación de SUNAT:

| Elemento XML UBL 2.1 | Significado Fiscal y de Arquitectura |
| :--- | :--- |
| `<ext:UBLExtensions>` | Contenedor de extensiones de UBL. Aloja el elemento `<ds:Signature>` preparado según el estándar W3C XMLDSig / XAdES-BES para la firma digital con certificado digital tributario. |
| `<cbc:UBLVersionID>` | Indica la versión del estándar base de OASIS. Su valor obligatorio en este sistema es `2.1`. |
| `<cbc:CustomizationID>` | Especifica la versión de la especificación técnica de SUNAT. El valor oficial reglamentario es `2.0` con atributo `@schemeAgencyName="PE:SUNAT"`. |
| `<cbc:ID>` | Numeración correlativa del comprobante compuesta por la serie fiscal y el número correlativo: `F001-00000001`. |
| `<cbc:IssueDate>` | Fecha de emisión del comprobante en formato `AAAA-MM-DD` (`2026-11-12`). |
| `<cbc:IssueTime>` | Hora de generación del documento en formato `hh:mm:ss` (`10:30:00`). |
| `<cbc:InvoiceTypeCode>` | Código del Catálogo 01 (`01` = Factura). Contiene el atributo `@listID="0101"` que identifica el tipo de operación de venta interna (Catálogo 51). |
| `<cbc:Note languageLocaleID="1000">` | Leyenda obligatoria del Catálogo 52 con el monto total en letras: `SON ONCE MIL OCHOCIENTOS CATORCE Y 00/100 SOLES`. |
| `<cbc:DocumentCurrencyCode>` | Moneda de la transacción según código ISO 4217 (`PEN`). |
| `<cac:Signature>` | Declaración formal de la firma dentro del cuerpo UBL, vinculando el ID del comprobante, el RUC del emisor y el URI del bloque de firma. |
| `<cac:AccountingSupplierParty>` | Bloque con la información completa del contribuyente emisor (RUC con `@schemeID="6"`, razón social y domicilio fiscal). |
| `<cac:AccountingCustomerParty>` | Bloque con la información completa del adquirente (RUC con `@schemeID="6"`, razón social y dirección). |
| `<cac:PaymentTerms>` | Bloque que define la forma de pago. En ventas al contado consigna `ID="FormaPago"` y `PaymentMeansID="Contado"`. En ventas al crédito consigna `PaymentMeansID="Credito"` con el monto neto pendiente y los nodos subsiguientes para cada cuota (`Cuota001`, `Cuota002`) con sus fechas de vencimiento. |
| `<cac:TaxTotal>` | Agregación global de tributos. Contiene el total de impuestos (`cbc:TaxAmount`) y el desglose en subgrupos (`<cac:TaxSubtotal>`) para operaciones gravadas (`1000 - IGV`) y operaciones exoneradas (`9997 - EXO`). |
| `<cac:LegalMonetaryTotal>` | Resumen monetario legal: Total valor de venta (`LineExtensionAmount`), Total precio de venta (`TaxInclusiveAmount`) e Importe total a pagar (`PayableAmount`). |
| `<cac:InvoiceLine>` | Detalle de cada ítem facturado: cantidad, unidad de medida, valor de venta de la línea, precio unitario que incluye IGV (`AlternativeConditionPrice`), desglose de tributos de línea, descripción y valor unitario (`Price/PriceAmount`). |

---

## 5. Memoria de Cálculo Matemático y Tributario

Todos los cálculos financieros se procesan mediante el módulo `src/calculations.py` usando `decimal.Decimal` con política de redondeo `ROUND_HALF_UP` a 2 decimales (`Decimal('0.01')`), eliminando cualquier distorsión por aritmética de punto flotante.

### 5.1. Cálculos a Nivel de Ítem

* **Línea 1: Servidor Rack 2U**
  $$\text{Valor Venta} = 2.00 \times 4,500.00 = 9,000.00\,\text{PEN}$$
  $$\text{Base Imponible IGV} = 9,000.00\,\text{PEN}$$
  $$\text{IGV (18\%)} = 9,000.00 \times 0.18 = 1,620.00\,\text{PEN}$$
  $$\text{Precio Unitario con IGV} = 4,500.00 \times 1.18 = 5,310.00\,\text{PEN}$$

* **Línea 2: Servicio de Instalación**
  $$\text{Valor Venta} = 1.00 \times 800.00 = 800.00\,\text{PEN}$$
  $$\text{Base Imponible IGV} = 800.00\,\text{PEN}$$
  $$\text{IGV (18\%)} = 800.00 \times 0.18 = 144.00\,\text{PEN}$$
  $$\text{Precio Unitario con IGV} = 800.00 \times 1.18 = 944.00\,\text{PEN}$$

* **Línea 3: Manual Técnico (Libro Exonerado)**
  $$\text{Valor Venta} = 1.00 \times 250.00 = 250.00\,\text{PEN}$$
  $$\text{Base Exonerada} = 250.00\,\text{PEN}$$
  $$\text{IGV (0\%)} = 0.00\,\text{PEN}$$
  $$\text{Precio Unitario} = 250.00\,\text{PEN}$$

### 5.2. Agregación de Totales Globales

1. **Total Valor Venta Operaciones Gravadas (Concepto Catálogo 14: 1001):**
   $$9,000.00 + 800.00 = 9,800.00\,\text{PEN}$$
2. **Total Valor Venta Operaciones Exoneradas (Concepto Catálogo 14: 1003):**
   $$250.00\,\text{PEN}$$
3. **Total Valor de Venta (`LineExtensionAmount`):**
   $$9,800.00 + 250.00 = 10,050.00\,\text{PEN}$$
4. **Sumatoria Total de IGV (`TaxAmount` de tributo 1000):**
   $$1,620.00 + 144.00 = 1,764.00\,\text{PEN}$$
5. **Total Precio de Venta (`TaxInclusiveAmount`):**
   $$10,050.00 + 1,764.00 = 11,814.00\,\text{PEN}$$
6. **Importe Total a Pagar (`PayableAmount`):**
   $$11,814.00\,\text{PEN}$$

> [!IMPORTANT]
> **Distinción Crítica de Catálogos:**  
> Los códigos del Catálogo 14 (`1001`, `1002`, `1003`) representan clasificaciones de importes de venta (gravada, inafecta, exonerada). **Bajo ninguna circunstancia** se insertan como identificadores de impuesto en `TaxScheme/cbc:ID`. En UBL 2.1, los tributos se identifican exclusivamente con el Catálogo 05 (`1000` para IGV, `9997` para Exonerado, `9998` para Inafecto, `9996` para Gratuito).

---

## 6. Nomenclatura Oficial del Archivo XML

Conforme a la Resolución de Superintendencia de SUNAT, el archivo XML se genera con el formato:

$$\text{RRRRRRRRRRR-TT-SSSS-NNNNNNNN.xml}$$

Para este caso de estudio:
* **RUC Emisor:** `20605389458`
* **Tipo de Comprobante:** `01` (Factura)
* **Serie Fiscal:** `F001`
* **Correlativo con padding de 8 dígitos:** `00000001`

**Nombre del Archivo resultante:**
`20605389458-01-F001-00000001.xml`

Existe correspondencia total entre los valores del nombre de archivo y las etiquetas internas:
* RUC en nombre == `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID`
* Tipo en nombre == `/Invoice/cbc:InvoiceTypeCode`
* Serie-Correlativo en nombre == `/Invoice/cbc:ID`

---

## 7. Validación Oficial XSD y Verificación Automatizada

El archivo generado es sometido a un pipeline de validación formal en 3 niveles:

1. **Nivel 1 — Well-Formedness y Codificación:**
   Se comprueba que la estructura XML sea bien formada y que la declaración `<?xml version='1.0' encoding='ISO-8859-1'?>` coincida de manera binaria con los bytes escritos, asegurando la preservación de caracteres como `ó`, `ñ`, `Á`, `°`.

2. **Nivel 2 — Validación Estructural contra XSD Oficial de OASIS:**
   Se compila `lxml.etree.XMLSchema` directamente desde el esquema oficial `xsd/maindoc/UBL-Invoice-2.1.xsd` y sus esquemas compartidos en `xsd/common/`. El archivo supera la validación con **cero errores de esquema**, certificando que los tipos de datos, cardinalidades y secuencias de nodos son 100% conformes.

3. **Nivel 3 — Reglas de Negocio SUNAT y Pytest:**
   Se ejecutan pruebas automatizadas mediante `pytest` que verifican:
   * El cálculo exacto del dígito verificador del RUC del emisor y receptor (Módulo 11).
   * La coherencia de la sumatoria de líneas contra la cabecera.
   * La conformidad de los términos de pago al contado y al crédito con cuotas (Decreto de Urgencia 013-2020).
   * La detección y rechazo de documentos alterados, malformados o con cálculos inconsistentes.

