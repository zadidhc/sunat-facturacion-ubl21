"""Motor de cálculo financiero para facturación electrónica SUNAT UBL 2.1.

Utiliza aritmética Decimal estricta con redondeo financiero estándar (ROUND_HALF_UP).
No utiliza operaciones de punto flotante en cálculos contables ni monetarios.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List
from src.catalogs import (
    AFECTACION_A_TRIBUTO,
    CATALOGO_05_TRIBUTOS,
    CATALOGO_07_AFECTACION_IGV,
)
from src.models import (
    CalculatedLineItem,
    InvoiceCalculations,
    InvoiceDocument,
    LineItemInput,
    PaymentTerms,
    TaxSubtotalSummary,
)
from src.validators import ValidationError

DOS_DECIMALES = Decimal("0.01")


def redondear(valor: Decimal, decimales: Decimal = DOS_DECIMALES) -> Decimal:
    """Aplica redondeo contable explícito ROUND_HALF_UP."""
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    return valor.quantize(decimales, rounding=ROUND_HALF_UP)


def procesar_linea(
    item: LineItemInput,
    tasa_igv_defecto: Decimal,
) -> CalculatedLineItem:
    """Calcula los importes netos, bases imponibles, tributos y precios de una línea de factura."""
    if item.cantidad <= Decimal("0"):
        raise ValidationError(f"La cantidad del ítem {item.id_linea} debe ser mayor a cero (recibido: {item.cantidad}).")
    if item.valor_unitario < Decimal("0"):
        raise ValidationError(f"El valor unitario del ítem {item.id_linea} no puede ser negativo.")

    afectacion = item.codigo_afectacion_igv
    if afectacion not in CATALOGO_07_AFECTACION_IGV:
        raise ValidationError(
            f"Código de afectación al IGV '{afectacion}' en ítem {item.id_linea} "
            f"no es válido según el Catálogo 07 de SUNAT."
        )

    cod_tributo = AFECTACION_A_TRIBUTO.get(afectacion, "1000")
    tributo_meta = CATALOGO_05_TRIBUTOS.get(cod_tributo)
    if not tributo_meta:
        raise ValidationError(f"Código de tributo '{cod_tributo}' no encontrado en Catálogo 05.")

    # Valor de venta neto de la línea
    line_extension_amount = redondear(item.cantidad * item.valor_unitario)

    # Determinación de tasa y cálculo de IGV según tipo de afectación
    if afectacion == "10":  # Gravado - Operación Onerosa
        tasa_aplicable = item.tasa_igv if item.tasa_igv is not None else tasa_igv_defecto
        tasa_porcentaje = redondear(tasa_aplicable * Decimal("100"))
        base_imponible = line_extension_amount
        monto_igv = redondear(base_imponible * tasa_aplicable)
        # Precio unitario que incluye el impuesto
        precio_unitario = redondear(item.valor_unitario * (Decimal("1") + tasa_aplicable))
        codigo_tipo_precio = "01"  # Precio unitario incluye IGV (Catálogo 16)
        monto_total_impuestos = monto_igv

    elif afectacion in ("20", "30", "40"):  # Exonerado / Inafecto / Exportación
        tasa_porcentaje = Decimal("0.00")
        base_imponible = line_extension_amount
        monto_igv = Decimal("0.00")
        precio_unitario = redondear(item.valor_unitario)
        codigo_tipo_precio = "01"
        monto_total_impuestos = Decimal("0.00")

    else:  # Operaciones no onerosas (Gratuitas, retiros, etc.)
        tasa_porcentaje = Decimal("0.00")
        base_imponible = line_extension_amount
        monto_igv = Decimal("0.00")
        precio_unitario = redondear(item.valor_unitario)
        codigo_tipo_precio = "02"  # Valor referencial unitario (Catálogo 16)
        monto_total_impuestos = Decimal("0.00")

    return CalculatedLineItem(
        id_linea=item.id_linea,
        descripcion=item.descripcion,
        cantidad=item.cantidad,
        unidad_medida=item.unidad_medida,
        valor_unitario=item.valor_unitario,
        precio_unitario=precio_unitario,
        codigo_tipo_precio=codigo_tipo_precio,
        line_extension_amount=line_extension_amount,
        codigo_afectacion_igv=afectacion,
        codigo_tributo=cod_tributo,
        nombre_tributo=tributo_meta.nombre_tributo,
        codigo_internacional_tributo=tributo_meta.codigo_internacional,
        categoria_impuesto=tributo_meta.categoria_impuesto,
        tasa_igv=tasa_porcentaje,
        base_imponible_igv=base_imponible,
        monto_igv=monto_igv,
        monto_total_impuestos_linea=monto_total_impuestos,
        codigo_producto=item.codigo_producto,
        codigo_producto_sunat=item.codigo_producto_sunat,
    )


def calcular_totales_factura(documento: InvoiceDocument) -> InvoiceCalculations:
    """Calcula todos los totales de impuestos, bases imponibles y totales legales monetarios de la factura."""
    if not documento.items:
        raise ValidationError("El comprobante debe contener al menos una línea de detalle (ítem).")

    lineas_calculadas: List[CalculatedLineItem] = []
    subtotales_map: Dict[str, TaxSubtotalSummary] = {}

    tot_gravada = Decimal("0.00")
    tot_exonerada = Decimal("0.00")
    tot_inafecta = Decimal("0.00")
    tot_gratuita = Decimal("0.00")

    tot_line_extension = Decimal("0.00")
    tot_igv = Decimal("0.00")

    for item_input in documento.items:
        linea = procesar_linea(item_input, documento.tasa_igv_defecto)
        lineas_calculadas.append(linea)

        # Clasificación según Catálogo 14 (totales de valor de venta)
        if linea.codigo_afectacion_igv == "10":
            tot_gravada += linea.line_extension_amount
            tot_line_extension += linea.line_extension_amount
            tot_igv += linea.monto_igv
        elif linea.codigo_afectacion_igv == "20":
            tot_exonerada += linea.line_extension_amount
            tot_line_extension += linea.line_extension_amount
        elif linea.codigo_afectacion_igv in ("30", "40"):
            tot_inafecta += linea.line_extension_amount
            tot_line_extension += linea.line_extension_amount
        else:
            tot_gratuita += linea.line_extension_amount

        # Acumular por código de tributo de Catálogo 05
        cod_trib = linea.codigo_tributo
        if cod_trib not in subtotales_map:
            subtotales_map[cod_trib] = TaxSubtotalSummary(
                codigo_tributo=cod_trib,
                nombre_tributo=linea.nombre_tributo,
                codigo_internacional=linea.codigo_internacional_tributo,
                categoria_impuesto=linea.categoria_impuesto,
                base_imponible=Decimal("0.00"),
                monto_impuesto=Decimal("0.00"),
            )

        actual = subtotales_map[cod_trib]
        subtotales_map[cod_trib] = TaxSubtotalSummary(
            codigo_tributo=cod_trib,
            nombre_tributo=actual.nombre_tributo,
            codigo_internacional=actual.codigo_internacional,
            categoria_impuesto=actual.categoria_impuesto,
            base_imponible=redondear(actual.base_imponible + linea.base_imponible_igv),
            monto_impuesto=redondear(actual.monto_impuesto + linea.monto_igv),
        )

    # Redondeo de totales
    tot_gravada = redondear(tot_gravada)
    tot_exonerada = redondear(tot_exonerada)
    tot_inafecta = redondear(tot_inafecta)
    tot_gratuita = redondear(tot_gratuita)
    tot_line_extension = redondear(tot_line_extension)
    tot_igv = redondear(tot_igv)

    total_impuestos = tot_igv  # En ausencia de ISC u otros tributos
    total_precio_venta = redondear(tot_line_extension + total_impuestos)
    importe_total_pagar = total_precio_venta

    return InvoiceCalculations(
        lineas=lineas_calculadas,
        subtotales_tributo=subtotales_map,
        total_valor_venta_gravada=tot_gravada,
        total_valor_venta_exonerada=tot_exonerada,
        total_valor_venta_inafecta=tot_inafecta,
        total_valor_venta_gratuita=tot_gratuita,
        total_valor_venta=tot_line_extension,
        total_igv=tot_igv,
        total_impuestos=total_impuestos,
        total_precio_venta=total_precio_venta,
        importe_total_pagar=importe_total_pagar,
    )


def validar_condiciones_pago(
    terminos_pago: PaymentTerms,
    importe_total_pagar: Decimal,
    fecha_emision: str,
) -> None:
    """Valida la consistencia de las condiciones de pago (Contado o Crédito) según las reglas de SUNAT."""
    if terminos_pago.forma_pago not in ("Contado", "Credito"):
        raise ValidationError(
            f"Forma de pago '{terminos_pago.forma_pago}' no permitida. Debe ser 'Contado' o 'Credito'."
        )

    if terminos_pago.forma_pago == "Credito":
        if terminos_pago.monto_neto_pendiente is None:
            raise ValidationError("Para operaciones al crédito, es obligatorio indicar el monto neto pendiente de pago.")

        monto_pendiente = redondear(terminos_pago.monto_neto_pendiente)
        if monto_pendiente <= Decimal("0"):
            raise ValidationError("El monto neto pendiente de pago en operaciones al crédito debe ser mayor a cero.")
        if monto_pendiente > importe_total_pagar:
            raise ValidationError(
                f"El monto neto pendiente de pago ({monto_pendiente}) no puede superar "
                f"el importe total de la factura ({importe_total_pagar})."
            )

        if not terminos_pago.cuotas:
            raise ValidationError("Para operaciones al crédito, debe definirse al menos una cuota de pago.")

        suma_cuotas = Decimal("0.00")
        for cuota in terminos_pago.cuotas:
            if not cuota.id_cuota.startswith("Cuota"):
                raise ValidationError(
                    f"El identificador de cuota '{cuota.id_cuota}' no cumple con el patrón oficial 'Cuota###' (ej: Cuota001)."
                )
            if cuota.monto <= Decimal("0"):
                raise ValidationError(f"El monto de la cuota {cuota.id_cuota} debe ser mayor a cero.")
            if cuota.fecha_vencimiento <= fecha_emision:
                raise ValidationError(
                    f"La fecha de vencimiento de {cuota.id_cuota} ({cuota.fecha_vencimiento}) "
                    f"debe ser posterior a la fecha de emisión ({fecha_emision})."
                )
            suma_cuotas += cuota.monto

        suma_cuotas = redondear(suma_cuotas)
        if suma_cuotas != monto_pendiente:
            raise ValidationError(
                f"La suma de las cuotas ({suma_cuotas}) no coincide con el monto neto pendiente ({monto_pendiente})."
            )
