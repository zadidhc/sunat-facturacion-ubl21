"""Modelos de dominio tipados para el comprobante de pago electrónico UBL 2.1."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class PartyAddress:
    """Domicilio fiscal o dirección de un participante en la operación comercial."""
    direccion: str
    ubigeo: str  # Código INEI de 6 dígitos (Catálogo 13)
    departamento: str
    provincia: str
    distrito: str
    codigo_pais: str = "PE"  # Catálogo 04 (ISO 3166-1)
    codigo_local_anexo: str = "0000"  # Código de establecimiento anexo SUNAT (0000 = domicilio fiscal principal)
    urbanizacion: Optional[str] = None


@dataclass
class Party:
    """Datos de una persona natural o jurídica (Emisor o Adquirente/Cliente)."""
    numero_documento: str
    tipo_documento_identidad: str  # Catálogo 06 ('6'=RUC, '1'=DNI)
    razon_social: str
    nombre_comercial: Optional[str] = None
    direccion: Optional[PartyAddress] = None


@dataclass
class LineItemInput:
    """Entrada de datos para una línea o ítem del comprobante."""
    id_linea: int
    descripcion: str
    cantidad: Decimal
    unidad_medida: str  # Catálogo 03 ('NIU', 'ZZ', 'KGM')
    valor_unitario: Decimal  # Valor monetario unitario antes de tributos (sin IGV)
    codigo_afectacion_igv: str = "10"  # Catálogo 07 ('10'=Gravado Oneroso, '20'=Exonerado, '30'=Inafecto)
    tasa_igv: Optional[Decimal] = None  # Si es None, utiliza la tasa general de la factura
    codigo_producto: Optional[str] = None  # Código interno del ítem
    codigo_producto_sunat: Optional[str] = None  # Código UNSPSC (Catálogo 25)


@dataclass
class CalculatedLineItem:
    """Ítem procesado con todos sus cálculos matemáticos y fiscales desglosados."""
    id_linea: int
    descripcion: str
    cantidad: Decimal
    unidad_medida: str
    valor_unitario: Decimal  # cac:Price/cbc:PriceAmount
    precio_unitario: Decimal  # cac:PricingReference/.../cbc:PriceAmount (con IGV si gravado)
    codigo_tipo_precio: str  # Catálogo 16 ('01'=precio unitario, '02'=valor referencial)
    line_extension_amount: Decimal  # Valor de venta neto = cantidad * valor_unitario
    codigo_afectacion_igv: str  # Catálogo 07
    codigo_tributo: str  # Catálogo 05 ('1000', '9997', '9998', '9996')
    nombre_tributo: str  # ('IGV', 'EXO', 'INA', 'GRA')
    codigo_internacional_tributo: str  # ('VAT', 'FRE')
    categoria_impuesto: str  # ('S', 'E', 'O', 'Z')
    tasa_igv: Decimal  # Porcentaje (ej. 18.00 o 0.00)
    base_imponible_igv: Decimal  # cbc:TaxableAmount
    monto_igv: Decimal  # cbc:TaxAmount
    monto_total_impuestos_linea: Decimal  # cac:TaxTotal/cbc:TaxAmount
    codigo_producto: Optional[str] = None
    codigo_producto_sunat: Optional[str] = None


@dataclass
class Installment:
    """Cuota individual para operaciones de venta al crédito."""
    id_cuota: str  # Formato oficial: 'Cuota001', 'Cuota002', etc.
    monto: Decimal
    fecha_vencimiento: str  # Formato 'YYYY-MM-DD', debe ser posterior a la fecha de emisión


@dataclass
class PaymentTerms:
    """Condición y términos de pago según normativa SUNAT vigente."""
    forma_pago: str  # 'Contado' o 'Credito'
    monto_neto_pendiente: Optional[Decimal] = None  # Obligatorio si forma_pago es 'Credito'
    cuotas: List[Installment] = field(default_factory=list)


@dataclass
class TaxSubtotalSummary:
    """Subtotal acumulado por cada tipo de tributo en la cabecera."""
    codigo_tributo: str  # Catálogo 05
    nombre_tributo: str
    codigo_internacional: str
    categoria_impuesto: str
    base_imponible: Decimal
    monto_impuesto: Decimal


@dataclass
class InvoiceCalculations:
    """Resultado completo de los cálculos monetarios de la factura."""
    lineas: List[CalculatedLineItem]
    subtotales_tributo: Dict[str, TaxSubtotalSummary]
    total_valor_venta_gravada: Decimal  # Concepto 1001 Cat 14 (base de IGV 1000)
    total_valor_venta_exonerada: Decimal  # Concepto 1003 Cat 14 (base de 9997)
    total_valor_venta_inafecta: Decimal  # Concepto 1002 Cat 14 (base de 9998)
    total_valor_venta_gratuita: Decimal  # Concepto 1004 Cat 14 (base de 9996)
    total_valor_venta: Decimal  # cac:LegalMonetaryTotal/cbc:LineExtensionAmount
    total_igv: Decimal  # Total acumulado de impuesto IGV
    total_impuestos: Decimal  # cac:TaxTotal/cbc:TaxAmount
    total_precio_venta: Decimal  # cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount
    importe_total_pagar: Decimal  # cac:LegalMonetaryTotal/cbc:PayableAmount


@dataclass
class InvoiceDocument:
    """Estructura completa de la Factura Electrónica UBL 2.1."""
    emisor: Party
    cliente: Party
    tipo_documento: str  # Catálogo 01 ('01'=Factura)
    serie: str  # Formato 'F###'
    correlativo: int  # Entero positivo
    fecha_emision: str  # 'YYYY-MM-DD'
    hora_emision: str  # 'hh:mm:ss'
    moneda: str = "PEN"  # Catálogo 02
    tipo_operacion: str = "0101"  # Catálogo 51 ('0101'=Venta interna no sujeta a Detracción/Percepción)
    fecha_vencimiento: Optional[str] = None
    terminos_pago: Optional[PaymentTerms] = None
    items: List[LineItemInput] = field(default_factory=list)
    leyendas: Dict[str, str] = field(default_factory=dict)  # Catálogo 52 (código -> descripción)
    tasa_igv_defecto: Decimal = Decimal("0.18")  # 18% general, configurable (ej. 10.5% MYPEs)


def cargar_documento_desde_dict(data: dict) -> InvoiceDocument:
    """Crea una instancia de InvoiceDocument a partir de un diccionario cargado de JSON."""
    dir_emisor = None
    if "direccion" in data["emisor"] and data["emisor"]["direccion"]:
        d = data["emisor"]["direccion"]
        dir_emisor = PartyAddress(
            direccion=d["direccion"],
            ubigeo=d["ubigeo"],
            departamento=d["departamento"],
            provincia=d["provincia"],
            distrito=d["distrito"],
            codigo_pais=d.get("codigo_pais", "PE"),
            codigo_local_anexo=d.get("codigo_local_anexo", "0000"),
            urbanizacion=d.get("urbanizacion"),
        )

    emisor = Party(
        numero_documento=data["emisor"]["numero_documento"],
        tipo_documento_identidad=data["emisor"]["tipo_documento_identidad"],
        razon_social=data["emisor"]["razon_social"],
        nombre_comercial=data["emisor"].get("nombre_comercial"),
        direccion=dir_emisor,
    )

    dir_cliente = None
    if "direccion" in data["cliente"] and data["cliente"]["direccion"]:
        d = data["cliente"]["direccion"]
        dir_cliente = PartyAddress(
            direccion=d["direccion"],
            ubigeo=d["ubigeo"],
            departamento=d["departamento"],
            provincia=d["provincia"],
            distrito=d["distrito"],
            codigo_pais=d.get("codigo_pais", "PE"),
        )

    cliente = Party(
        numero_documento=data["cliente"]["numero_documento"],
        tipo_documento_identidad=data["cliente"]["tipo_documento_identidad"],
        razon_social=data["cliente"]["razon_social"],
        nombre_comercial=data["cliente"].get("nombre_comercial"),
        direccion=dir_cliente,
    )

    items = []
    for it in data["items"]:
        items.append(
            LineItemInput(
                id_linea=int(it["id_linea"]),
                descripcion=it["descripcion"],
                cantidad=Decimal(str(it["cantidad"])),
                unidad_medida=it["unidad_medida"],
                valor_unitario=Decimal(str(it["valor_unitario"])),
                codigo_afectacion_igv=it.get("codigo_afectacion_igv", "10"),
                tasa_igv=Decimal(str(it["tasa_igv"])) if "tasa_igv" in it and it["tasa_igv"] is not None else None,
                codigo_producto=it.get("codigo_producto"),
                codigo_producto_sunat=it.get("codigo_producto_sunat"),
            )
        )

    terminos_pago = None
    if "terminos_pago" in data and data["terminos_pago"]:
        tp = data["terminos_pago"]
        cuotas = []
        for c in tp.get("cuotas", []):
            cuotas.append(
                Installment(
                    id_cuota=c["id_cuota"],
                    monto=Decimal(str(c["monto"])),
                    fecha_vencimiento=c["fecha_vencimiento"],
                )
            )
        monto_pendiente = (
            Decimal(str(tp["monto_neto_pendiente"]))
            if "monto_neto_pendiente" in tp and tp["monto_neto_pendiente"] is not None
            else None
        )
        terminos_pago = PaymentTerms(
            forma_pago=tp.get("forma_pago", "Contado"),
            monto_neto_pendiente=monto_pendiente,
            cuotas=cuotas,
        )

    tasa_def = Decimal(str(data.get("tasa_igv_defecto", "0.18")))

    return InvoiceDocument(
        emisor=emisor,
        cliente=cliente,
        tipo_documento=data.get("tipo_documento", "01"),
        serie=data["serie"],
        correlativo=int(data["correlativo"]),
        fecha_emision=data["fecha_emision"],
        hora_emision=data.get("hora_emision", "10:00:00"),
        moneda=data.get("moneda", "PEN"),
        tipo_operacion=data.get("tipo_operacion", "0101"),
        fecha_vencimiento=data.get("fecha_vencimiento"),
        terminos_pago=terminos_pago,
        items=items,
        leyendas=data.get("leyendas", {}),
        tasa_igv_defecto=tasa_def,
    )

