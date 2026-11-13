# Sistema de Facturación Electrónica SUNAT UBL 2.1 (OASIS UBL 2.1)

Proyecto académico independiente, modular y ejecutable para la evaluación de **Arquitectura de Software** (Segundo Examen Parcial).

Implementa la generación dinámica, validación estructural oficial contra **XSD OASIS UBL 2.1** y auditoría de reglas fiscales de la **SUNAT** (Perú) para comprobantes tipo **Factura Electrónica (01)** con codificación **ISO-8859-1**, cálculo financiero estricto mediante `Decimal` y pruebas unitarias automatizadas con `pytest`.

---

## 1. Características de la Solución

* **Generación Dinámica Real:** Construye el árbol XML nodo a nodo con `lxml` a partir de estructuras de datos configurables (JSON o modelos de dominio). No utiliza plantillas de texto estáticas ni reemplazos de cadenas.
* **Alineación Oficial OASIS UBL 2.1 y SUNAT:**
  * Estructura basada en `xsd/maindoc/UBL-Invoice-2.1.xsd` y esquemas compartidos en `xsd/common/`.
  * Namespaces oficiales (`urn:oasis:names:specification:ubl:schema:xsd:Invoice-2`, `cac`, `cbc`, `ext`, `ds`).
  * `cbc:UBLVersionID` = `2.1` y `cbc:CustomizationID` = `2.0`.
* **Codificación ISO-8859-1:** Emisión en XML 1.0 con bytes codificados en `ISO-8859-1` y soporte íntegro de caracteres en español (`á, é, í, ó, ú, ñ, Á, É, Í, Ó, Ú, Ñ, °`).
* **Validación de Identidad Fiscal:**
  * Algoritmo de **Módulo 11** de SUNAT con factores ponderados `[5, 4, 3, 2, 7, 6, 5, 4, 3, 2]` para verificación estricta del dígito verificador del RUC del emisor y cliente.
  * Validación sintáctica de DNI (8 dígitos) y otros documentos del Catálogo 06 sin aplicar checksum de RUC a no-RUCs.
  * Distinción formal entre validación matemática/sintáctica y verificación en padrones externos de SUNAT.
* **Cálculo Financiero con Decimal:** Redondeo bancario `ROUND_HALF_UP` a 2 decimales para importes y precios, sin usar aritmética de punto flotante (`float`).
* **Condiciones de Pago al Contado y Crédito:** Soporte para cuotas (`Cuota001`, `Cuota002`), fechas de vencimiento y monto neto pendiente conforme a la normativa vigente (D.U. 013-2020 y R.S. 193-2020).
* **Validación en 3 Niveles:**
  1. *Nivel 1:* Documento bien formado (Well-formed XML) y coincidencia binaria de codificación.
  2. *Nivel 2:* Validación estructural contra el paquete XSD oficial de OASIS mediante `lxml.etree.XMLSchema`.
  3. *Nivel 3:* Validación de reglas de negocio locales de SUNAT (consistencia nombre de archivo, coincidencia de RUC, tipo de comprobante, sumatorias y cuotas).
* **Autonomía y Reproducibilidad:** No requiere bases de datos, UI, Odoo, Laragon, servidores web ni dependencias externas.

---

## 2. Requisitos Previos

* Sistema Operativo: Windows 10 / 11 (o Linux / macOS).
* Python: versión 3.11 o superior.
* Conexión a internet únicamente para la instalación inicial de dependencias vía `pip`.

---

## 3. Instrucciones de Instalación y Configuración en Windows

### Paso 1: Clonar el repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd sunat_facturacion_ubl21
```

**Todas las rutas XSD y de datos se resuelven desde la carpeta del proyecto; no requieren la misma ruta de instalación.**

### Paso 2: Crear y activar entorno virtual (Recomendado)
En PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
En Command Prompt (CMD):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

### Paso 3: Instalar dependencias
```bash
python -m pip install -r requirements.txt
```

---

## 4. Comandos de Ejecución

### 4.1. Ejecutar la Suite Completa de Pruebas Unitarias (pytest)
```bash
python -m pytest -v
```
Ejecuta 85 pruebas automatizadas que cubren el 100% de los requerimientos de la prueba, incluyendo cálculo de RUC módulo 11, clasificaciones tributarias, términos de pago contado/crédito, codificación ISO-8859-1 y validación estructural contra el XSD oficial de OASIS.

### 4.2. Ejecutar la Demostración Completa de Punta a Punta
```bash
python main.py
```
Este comando ejecuta:
1. Lectura del caso de estudio configurable al contado (`data/invoice_input.json`).
2. Generación del archivo XML oficial: `generated/20605389458-01-F001-00000001.xml`.
3. Validación en 3 niveles con reporte detallado en consola.
4. Generación y validación del caso al crédito con cuotas (`data/invoice_input_credit.json` -> `generated/20605389458-01-F001-00000002.xml`).
5. Generación de un XML intencionalmente inválido (`generated/invalid_invoice_example.xml`) para demostrar la detección de fallos por el XSD y por las reglas de negocio.

### 4.3. Opciones Adicionales de la CLI
* **Procesar un JSON personalizado:**
  ```bash
  python main.py --input data/invoice_input.json --output-dir generated
  ```
* **Validar únicamente un archivo XML existente:**
  ```bash
  python main.py --validate-only generated/20605389458-01-F001-00000001.xml
  ```

---

## 5. Instrucciones de Validación en Herramientas Externas

### 5.1. Validación en Notepad++ (Plugin XML Tools)
1. Abrir Notepad++.
2. Abrir el archivo generado: `generated\20605389458-01-F001-00000001.xml`.
3. Ir al menú superior: **Plugins** → **XML Tools** → **Validate Now** (o presionar `Ctrl + Shift + Alt + M`).
4. En el diálogo que solicita el archivo de esquema XML (XSD), navegar y seleccionar:
   `xsd\maindoc\UBL-Invoice-2.1.xsd`.
5. El plugin resolverá las dependencias relativas en `xsd/common/` y mostrará la notificación:  
   `"The XML is valid"`.

### 5.2. Validación en Visual Studio Code (Extensión Red Hat XML)
1. Instalar la extensión oficial **XML** de Red Hat (`redhat.vscode-xml`).
2. El proyecto ya incluye el archivo `.vscode/settings.json` con la asociación automática:
   ```json
   {
     "xml.fileAssociations": [
       {
         "pattern": "generated/*.xml",
         "systemId": "xsd/maindoc/UBL-Invoice-2.1.xsd"
       }
     ]
   }
   ```
3. Al abrir cualquier XML de la carpeta `generated/`, VS Code validará el documento en tiempo real contra el XSD oficial mostrando estado conforme en la barra inferior.

---

## 6. Estructura del Proyecto

```text
sunat_facturacion_ubl21/
├── xsd/                               # Paquete oficial OASIS UBL 2.1 sin modificaciones
│   ├── maindoc/
│   │   ├── UBL-Invoice-2.1.xsd        # Esquema oficial para Facturas y Boletas
│   │   ├── UBL-CreditNote-2.1.xsd     # Esquema oficial para Notas de Crédito
│   │   └── UBL-DebitNote-2.1.xsd      # Esquema oficial para Notas de Débito
│   └── common/                        # Esquemas de componentes comunes y tipos de datos
├── src/
│   ├── __init__.py
│   ├── catalogs.py                    # Catálogos fiscales de SUNAT (01, 02, 03, 05, 06, 07, 14, 16, 51, 52)
│   ├── validators.py                  # Validador de RUC (módulo 11), DNI, series y correlativos
│   ├── models.py                      # Modelos de datos tipados (Invoice, Party, LineItem, etc.)
│   ├── calculations.py                # Motor de cálculo financiero con Decimal (ROUND_HALF_UP)
│   ├── builder.py                     # Generador dinámico de XML UBL 2.1 con lxml e ISO-8859-1
│   └── xsd_validator.py               # Validador de 3 niveles (Sintaxis, XSD oficial y Reglas SUNAT)
├── data/
│   ├── invoice_input.json             # Entrada configurable para venta al contado (Caso de Estudio)
│   └── invoice_input_credit.json      # Entrada configurable para venta al crédito con cuotas
├── generated/
│   ├── 20605389458-01-F001-00000001.xml # XML válido al contado
│   ├── 20605389458-01-F001-00000002.xml # XML válido al crédito
│   └── invalid_invoice_example.xml      # Ejemplo intencionalmente inválido
├── tests/
│   ├── __init__.py
│   ├── test_ruc_validator.py          # Pruebas de algoritmo RUC, DNI, prefijos y checksum
│   ├── test_calculations.py           # Pruebas de cálculo monetario, IGV, redondeo y Catálogo 14
│   ├── test_catalogs_and_rules.py     # Pruebas de catálogos, series y nomenclatura
│   ├── test_payment_terms.py          # Pruebas de condiciones de pago contado y crédito
│   ├── test_xml_generation.py         # Pruebas de generación de namespaces y codificación ISO-8859-1
│   └── test_xsd_validation.py         # Pruebas de validación estructural contra el XSD oficial
├── .vscode/
│   └── settings.json                  # Asociación de esquemas para VS Code
├── main.py                            # Script CLI ejecutable para demostración completa
├── requirements.txt                   # Dependencias mínimas del proyecto
├── .gitignore                         # Exclusiones de caché y entornos
├── CASO_DE_ESTUDIO.md                 # Documento explicativo del caso empresarial
└── README.md                          # Guía técnica y manual de reproducción
```

---

## 7. Alcance y Reglas Fiscales

### Reglas Verificadas Localmente:
* Formato y algoritmo Módulo 11 del RUC del emisor y receptor.
* Nomenclatura del archivo XML conforme a la R.S. de SUNAT (`RRRRRRRRRRR-01-SSSS-NNNNNNNN.xml`).
* Coherencia entre el nombre de archivo y las etiquetas `cbc:ID`, `cbc:InvoiceTypeCode` y RUC del emisor.
* Versión UBL (`2.1`) y versión de estructura del documento (`2.0`).
* Consistencia de moneda (`PEN`/`USD`) en todo el comprobante.
* Exactitud de cálculos de línea (`LineExtensionAmount = Cantidad * ValorUnitario`).
* Desglose y cálculo de IGV según código de afectación del Catálogo 07 (operaciones gravadas y exoneradas).
* Consistencia de totales: `LineExtensionAmount` global, sumatoria de `TaxAmount` e `Importe Total a Pagar`.
* Términos de pago al contado y al crédito con validación de cuotas, montos y fechas de vencimiento.

### Reglas Fuera de Alcance Local (Dependientes de Servicios Externos de SUNAT):
* Consulta en línea del estado activo y condición de habido del contribuyente en el Padrón de SUNAT.
* Comprobación de afiliación o autorización de emisión en el SEE-Del Contribuyente o SEE-OSE.
* Firma digital criptográfica con certificado digital X.509 de persona jurídica y verificación de revocación en CRL/OCSP de la Entidad de Certificación.
* Envío SOAP/REST y recepción de la Constancia de Recepción (CDR) firmada por SUNAT u OSE.



## Entrega GitHub (versión estable)

Este proyecto incluye los ejemplos XML del caso de estudio generados con Python.
Los XML son datos de demostración y no representan documentos tributarios reales.
La estructura `ds:Signature` de esta versión es **un marcador de prueba, NO una firma criptográfica válida**; Nubefact/OSE-Demo puede sustituirla por un certificado de pruebas al usar «Firmar». No se afirma que el programa firme XML ni que exista aceptación en SUNAT de producción.

Para comprobar el proyecto en otra computadora, desde la raíz:

```powershell
python -m pip install -r requirements.txt
python main.py
python -m pytest -q
```

**No utilices para emitir facturas reales sin completar el proceso de firma y certificación correspondiente.**
