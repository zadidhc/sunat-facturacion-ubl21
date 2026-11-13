"""Pruebas unitarias para los términos de pago al contado y al crédito según SUNAT."""

from decimal import Decimal
import pytest
from src.calculations import validar_condiciones_pago
from src.models import Installment, PaymentTerms
from src.validators import ValidationError


def test_pago_al_contado_valido():
    """Valida la estructura de pago al contado."""
    pt = PaymentTerms(forma_pago="Contado")
    # No debe levantar ninguna excepción
    validar_condiciones_pago(pt, importe_total_pagar=Decimal("1180.00"), fecha_emision="2026-11-12")


def test_pago_al_credito_dos_cuotas_valido():
    """Valida una operación al crédito con 2 cuotas consistentes."""
    cuotas = [
        Installment(id_cuota="Cuota001", monto=Decimal("500.00"), fecha_vencimiento="2026-12-12"),
        Installment(id_cuota="Cuota002", monto=Decimal("500.00"), fecha_vencimiento="2027-01-11"),
    ]
    pt = PaymentTerms(
        forma_pago="Credito",
        monto_neto_pendiente=Decimal("1000.00"),
        cuotas=cuotas,
    )
    validar_condiciones_pago(pt, importe_total_pagar=Decimal("1000.00"), fecha_emision="2026-11-12")


def test_pago_al_credito_monto_pendiente_excede_total():
    """Rechaza cuando el monto neto pendiente es mayor al total del comprobante."""
    cuotas = [
        Installment("Cuota001", Decimal("1500.00"), "2026-12-12"),
    ]
    pt = PaymentTerms(
        forma_pago="Credito",
        monto_neto_pendiente=Decimal("1500.00"),
        cuotas=cuotas,
    )
    with pytest.raises(ValidationError) as exc:
        validar_condiciones_pago(pt, importe_total_pagar=Decimal("1000.00"), fecha_emision="2026-11-12")
    assert "no puede superar el importe total" in str(exc.value)


def test_pago_al_credito_suma_cuotas_inconsistente():
    """Rechaza cuando la sumatoria de cuotas no coincide con el monto neto pendiente."""
    cuotas = [
        Installment("Cuota001", Decimal("600.00"), "2026-12-12"),
        Installment("Cuota002", Decimal("300.00"), "2027-01-11"),  # Suma = 900 != 1000
    ]
    pt = PaymentTerms(
        forma_pago="Credito",
        monto_neto_pendiente=Decimal("1000.00"),
        cuotas=cuotas,
    )
    with pytest.raises(ValidationError) as exc:
        validar_condiciones_pago(pt, importe_total_pagar=Decimal("1000.00"), fecha_emision="2026-11-12")
    assert "no coincide con el monto neto pendiente" in str(exc.value)


def test_pago_al_credito_fecha_vencimiento_anterior_o_igual_a_emision():
    """Rechaza cuotas con fecha de vencimiento anterior o igual a la emisión (Regla 3267)."""
    cuotas = [
        Installment("Cuota001", Decimal("1000.00"), "2026-11-12"),  # Mismo día que emisión
    ]
    pt = PaymentTerms(
        forma_pago="Credito",
        monto_neto_pendiente=Decimal("1000.00"),
        cuotas=cuotas,
    )
    with pytest.raises(ValidationError) as exc:
        validar_condiciones_pago(pt, importe_total_pagar=Decimal("1000.00"), fecha_emision="2026-11-12")
    assert "debe ser posterior a la fecha de emisión" in str(exc.value)


def test_pago_al_credito_sin_cuotas():
    """Rechaza operaciones al crédito que no definan ninguna cuota."""
    pt = PaymentTerms(
        forma_pago="Credito",
        monto_neto_pendiente=Decimal("1000.00"),
        cuotas=[],
    )
    with pytest.raises(ValidationError) as exc:
        validar_condiciones_pago(pt, importe_total_pagar=Decimal("1000.00"), fecha_emision="2026-11-12")
    assert "al menos una cuota" in str(exc.value)


def test_pago_al_credito_formato_cuota_invalido():
    """Rechaza identificadores de cuota que no cumplan el formato 'Cuota###'."""
    cuotas = [
        Installment("1ra_cuota", Decimal("1000.00"), "2026-12-12"),
    ]
    pt = PaymentTerms(
        forma_pago="Credito",
        monto_neto_pendiente=Decimal("1000.00"),
        cuotas=cuotas,
    )
    with pytest.raises(ValidationError) as exc:
        validar_condiciones_pago(pt, importe_total_pagar=Decimal("1000.00"), fecha_emision="2026-11-12")
    assert "patrón oficial 'Cuota###'" in str(exc.value)

