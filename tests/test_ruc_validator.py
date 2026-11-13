"""Pruebas unitarias para la validación estricta de RUC, DNI y documentos de identidad."""

import pytest
from src.validators import (
    calcular_digito_verificador_ruc,
    validar_documento_identidad,
    validar_ruc,
    RucChecksumError,
    RucSyntacticError,
)

# Fixtures con RUCs reales peruanos verificados
RUCS_VALIDOS_REALES = [
    ("20131312955", "SUNAT"),
    ("20100047218", "BANCO DE LA NACION"),
    ("20100130204", "TELEFONICA DEL PERU"),
    ("20100070970", "BANCO DE CREDITO DEL PERU (BCP)"),
    ("20100055237", "SEDAPAL"),
    ("20100041953", "PETROPERU"),
    ("20131370301", "MEF - MINISTERIO DE ECONOMIA Y FINANZAS"),
    ("20131373580", "MINSA - MINISTERIO DE SALUD"),
    ("20155945860", "PONTIFICIA UNIVERSIDAD CATOLICA DEL PERU"),
    ("20100047480", "BBVA BANCO CONTINENTAL"),
    ("20605389458", "EMPRESA FICTICIA EMISORA (DV=8)"),
    ("20552103816", "EMPRESA FICTICIA CLIENTE (DV=6)"),
]


@pytest.mark.parametrize("ruc,entidad", RUCS_VALIDOS_REALES)
def test_rucs_validos_algoritmo_modulo_11(ruc, entidad):
    """Verifica que el algoritmo de módulo 11 valide RUCs auténticos."""
    resultado = validar_ruc(ruc, estricto=True)
    assert resultado.es_valido is True
    assert resultado.sintaxis_valida is True
    assert resultado.checksum_valido is True
    assert resultado.digito_calculado == int(ruc[10])
    assert resultado.digito_consignado == int(ruc[10])
    # Aclaración explícita: no afirma estado en SUNAT sin consultar servicio web
    assert resultado.registro_sunat_verificado is False
    assert "REQUIERE_SERVICIO_EXTERNO" in resultado.estado_contribuyente


def test_ruc_digito_verificador_alterado():
    """Detecta alteración intencional del dígito verificador."""
    # RUC SUNAT es 20131312955 (termina en 5). Cambiamos a 4 y a 0.
    with pytest.raises(RucChecksumError) as exc_info:
        validar_ruc("20131312954", estricto=True)
    assert "Dígito verificador inválido" in str(exc_info.value)

    res = validar_ruc("20131312950", estricto=False)
    assert res.es_valido is False
    assert res.sintaxis_valida is True
    assert res.checksum_valido is False
    assert res.digito_calculado == 5
    assert res.digito_consignado == 0


@pytest.mark.parametrize("prefijo_invalido", ["30", "40", "00", "99", "11", "21", "05"])
def test_ruc_prefijos_invalidos(prefijo_invalido):
    """Rechaza RUCs con prefijos no contemplados en normativa SUNAT."""
    ruc_invalido = f"{prefijo_invalido}123456789"
    with pytest.raises(RucSyntacticError) as exc_info:
        validar_ruc(ruc_invalido, estricto=True)
    assert "prefijo inválido" in str(exc_info.value)


@pytest.mark.parametrize("longitud_invalida", ["2013131295", "201313129555", "104589234", ""])
def test_ruc_longitud_incorrecta(longitud_invalida):
    """Rechaza RUCs con longitud distinta de 11 caracteres."""
    with pytest.raises(RucSyntacticError):
        validar_ruc(longitud_invalida, estricto=True)


@pytest.mark.parametrize("ruc_malformado", ["2013131295A", "2013 131295", "2013-131295", "ABCDEFGHIJK"])
def test_ruc_caracteres_no_numericos(ruc_malformado):
    """Rechaza RUCs con caracteres alfabéticos, espacios o guiones."""
    with pytest.raises(RucSyntacticError):
        validar_ruc(ruc_malformado, estricto=True)


def test_diferenciacion_sintaxis_vs_existencia():
    """Distingue entre validación matemática sintáctica y comprobación en padrón de SUNAT."""
    res = validar_ruc("20131312955", estricto=False)
    assert res.es_valido is True
    assert res.registro_sunat_verificado is False
    assert res.estado_contribuyente == "NO_CONSULTADO_REQUIERE_SERVICIO_EXTERNO"


@pytest.mark.parametrize("dni_valido", ["45892341", "01234567", "70809012"])
def test_dni_valido(dni_valido):
    """Valida DNI según Catálogo 06 (tipo '1', exactamente 8 dígitos)."""
    valido, msg = validar_documento_identidad(dni_valido, "1")
    assert valido is True
    assert "DNI" in msg


@pytest.mark.parametrize("dni_invalido", ["4589234", "458923410", "4589234A", " 4589234", ""])
def test_dni_invalido(dni_invalido):
    """Rechaza DNIs con longitud errónea o caracteres no numéricos."""
    valido, msg = validar_documento_identidad(dni_invalido, "1")
    assert valido is False
    assert "8 caracteres numéricos" in msg


def test_no_aplicar_checksum_ruc_a_dni():
    """Asegura que el algoritmo módulo 11 de RUC no se aplique a DNIs ni a otros documentos."""
    dni = "45892341"
    val_dni, _ = validar_documento_identidad(dni, "1")
    assert val_dni is True

    # Si se evaluara incorrectamente como RUC (tipo '6'), fallaría por longitud y prefijo
    val_ruc, _ = validar_documento_identidad(dni, "6")
    assert val_ruc is False


def test_otros_documentos_identidad_catalogo_06():
    """Valida carnet de extranjería (4) y pasaporte (7) sin aplicar checksum de RUC."""
    val_ce, _ = validar_documento_identidad("001234567", "4")
    assert val_ce is True

    val_pas, _ = validar_documento_identidad("A89765432", "7")
    assert val_pas is True

    # Rechazo si tiene espacios en blanco
    val_espacio, msg = validar_documento_identidad("A 89765432", "7")
    assert val_espacio is False
    assert "espacios en blanco" in msg

