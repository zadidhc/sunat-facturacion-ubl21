"""Validadores de negocio e identidad fiscal para facturación electrónica SUNAT.

Implementa validación estricta de RUC (módulo 11), DNI, tipos de documento según
el Catálogo 06 de SUNAT, formatos de series, correlativos y nomenclaturas oficiales de archivo.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple
from src.catalogs import (
    CATALOGO_01_TIPO_DOCUMENTO,
    CATALOGO_02_MONEDAS,
    CATALOGO_03_UNIDADES,
    CATALOGO_06_TIPOS_IDENTIDAD,
    CATALOGO_07_AFECTACION_IGV,
)


class ValidationError(Exception):
    """Excepción base para errores de validación de negocio."""
    pass


class RucValidationError(ValidationError):
    """Error general en la validación de un RUC peruano."""
    pass


class RucSyntacticError(RucValidationError):
    """Error sintáctico en el RUC (longitud, caracteres no numéricos o prefijo inválido)."""
    pass


class RucChecksumError(RucValidationError):
    """Error en el cálculo del dígito verificador del RUC (módulo 11)."""
    pass


@dataclass
class RucValidationResult:
    """Resultado detallado de la validación de un RUC peruano.

    Distingue explícitamente:
    1. Validez sintáctica (11 dígitos, prefijo válido).
    2. Integridad matemática del dígito verificador (módulo 11).
    3. Estado de registro en SUNAT (requiere consulta externa; no se asume).
    """
    es_valido: bool
    ruc: str
    sintaxis_valida: bool
    checksum_valido: bool
    digito_calculado: Optional[int]
    digito_consignado: Optional[int]
    mensaje: str
    registro_sunat_verificado: bool = False
    estado_contribuyente: str = "NO_CONSULTADO_REQUIERE_SERVICIO_EXTERNO"


# Factores ponderados oficiales para el cálculo módulo 11 del RUC peruano
FACTORES_RUC = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

# Prefijos permitidos para RUC según normativa de SUNAT:
# 10: Persona Natural con negocio / DNI
# 15: Persona Natural extranjera con carnet de extranjería
# 16: Persona Natural extranjera sin carnet / otros regímenes
# 17: Otros regímenes especiales
# 20: Persona Jurídica (sociedades, corporaciones, entidades estatales)
PREFIJOS_RUC_VALIDOS = ("10", "15", "16", "17", "20")


def calcular_digito_verificador_ruc(ruc_base_10: str) -> int:
    """Calcula el dígito verificador para los primeros 10 dígitos de un RUC según algoritmo oficial SUNAT (módulo 11).

    Fórmula:
        Suma = sum(d[i] * w[i]) para i=0..9
        Resto = Suma % 11
        Diferencia = 11 - Resto
        Si Diferencia == 10 -> Dígito = 0
        Si Diferencia == 11 -> Dígito = 1
        En otro caso -> Dígito = Diferencia
    """
    if not isinstance(ruc_base_10, str) or len(ruc_base_10) < 10 or not ruc_base_10[:10].isdigit():
        raise RucSyntacticError("Se requieren al menos 10 caracteres numéricos para calcular el dígito verificador.")

    digitos = [int(c) for c in ruc_base_10[:10]]
    suma = sum(d * w for d, w in zip(digitos, FACTORES_RUC))
    resto = suma % 11
    diferencia = 11 - resto

    if diferencia == 10:
        return 0
    elif diferencia == 11:
        return 1
    else:
        return diferencia


def validar_ruc(ruc: str, estricto: bool = True) -> RucValidationResult:
    """Valida un RUC peruano de manera estricta.

    Verifica:
    1. Que sea cadena de texto de exactamente 11 dígitos numéricos.
    2. Que comience con un prefijo reglamentario (10, 15, 16, 17, 20).
    3. Que el 11.° dígito coincida con el dígito verificador del algoritmo módulo 11.

    Aclara explícitamente que no verifica si el RUC existe o está habido en los padrones
    de SUNAT, dado que dicha comprobación requiere invocar servicios externos o consultar el padrón reducido.
    """
    if not isinstance(ruc, str):
        msg = f"El RUC debe ser una cadena de texto, no {type(ruc).__name__}."
        if estricto:
            raise RucSyntacticError(msg)
        return RucValidationResult(False, str(ruc), False, False, None, None, msg)

    ruc_limpio = ruc.strip()

    if len(ruc_limpio) != 11:
        msg = f"El RUC '{ruc_limpio}' debe contener exactamente 11 dígitos (longitud actual: {len(ruc_limpio)})."
        if estricto:
            raise RucSyntacticError(msg)
        return RucValidationResult(False, ruc_limpio, False, False, None, None, msg)

    if not ruc_limpio.isdigit():
        msg = f"El RUC '{ruc_limpio}' contiene caracteres no numéricos."
        if estricto:
            raise RucSyntacticError(msg)
        return RucValidationResult(False, ruc_limpio, False, False, None, None, msg)

    prefijo = ruc_limpio[:2]
    if prefijo not in PREFIJOS_RUC_VALIDOS:
        msg = (
            f"El RUC '{ruc_limpio}' tiene un prefijo inválido ('{prefijo}'). "
            f"Los prefijos autorizados por SUNAT son: {', '.join(PREFIJOS_RUC_VALIDOS)}."
        )
        if estricto:
            raise RucSyntacticError(msg)
        return RucValidationResult(False, ruc_limpio, False, False, None, None, msg)

    digito_consignado = int(ruc_limpio[10])
    digito_calculado = calcular_digito_verificador_ruc(ruc_limpio[:10])

    if digito_consignado != digito_calculado:
        msg = (
            f"Dígito verificador inválido para el RUC '{ruc_limpio}'. "
            f"Consignado: {digito_consignado}, Calculado por módulo 11: {digito_calculado}."
        )
        if estricto:
            raise RucChecksumError(msg)
        return RucValidationResult(False, ruc_limpio, True, False, digito_calculado, digito_consignado, msg)

    return RucValidationResult(
        es_valido=True,
        ruc=ruc_limpio,
        sintaxis_valida=True,
        checksum_valido=True,
        digito_calculado=digito_calculado,
        digito_consignado=digito_consignado,
        mensaje="RUC válido sintáctica y matemáticamente (dígito verificador correcto).",
        registro_sunat_verificado=False,
        estado_contribuyente="NO_CONSULTADO_REQUIERE_SERVICIO_EXTERNO",
    )


def validar_documento_identidad(numero: str, tipo_catalogo_06: str) -> Tuple[bool, str]:
    """Valida un documento de identidad según su tipo en el Catálogo 06 de SUNAT.

    Aplica las reglas específicas de cada tipo sin mezclar el algoritmo de RUC con DNI u otros.
    """
    if tipo_catalogo_06 not in CATALOGO_06_TIPOS_IDENTIDAD:
        return False, f"Tipo de documento '{tipo_catalogo_06}' no existe en el Catálogo 06 de SUNAT."

    num_limpio = str(numero).strip() if numero is not None else ""

    if tipo_catalogo_06 == "6":  # RUC
        res = validar_ruc(num_limpio, estricto=False)
        return res.es_valido, res.mensaje

    elif tipo_catalogo_06 == "1":  # DNI
        if len(num_limpio) != 8 or not num_limpio.isdigit():
            return False, f"El DNI debe tener exactamente 8 caracteres numéricos (valor recibido: '{num_limpio}')."
        return True, "DNI con formato sintáctico correcto (8 dígitos numéricos)."

    elif tipo_catalogo_06 in ("4", "7", "A", "B", "C", "D", "E", "F", "G", "H"):  # CE, Pasaporte, etc.
        if not (1 <= len(num_limpio) <= 15):
            return False, f"El documento tipo {tipo_catalogo_06} debe tener entre 1 y 15 caracteres."
        if re.search(r"\s", num_limpio):
            return False, "El documento no debe contener espacios en blanco ni caracteres de salto de línea."
        return True, "Documento de identidad alfanumérico válido."

    elif tipo_catalogo_06 == "0":  # No domiciliado sin RUC
        if not (1 <= len(num_limpio) <= 15):
            return False, "El documento no domiciliado debe tener entre 1 y 15 caracteres."
        return True, "Documento no domiciliado válido."

    return False, f"Tipo de documento {tipo_catalogo_06} no contemplado."


def validar_serie_correlativo(tipo_documento: str, serie: str, correlativo: int) -> Tuple[bool, str]:
    """Valida la serie y el número correlativo fiscal según normativa SUNAT.

    Reglas para Factura (01):
      - Serie electrónica: empieza con 'F' seguido de 3 alfanuméricos en mayúsculas (ej: F001, FA01).
      - Serie de contingencia: 4 dígitos numéricos (ej: 0001).
    Reglas para Boleta (03):
      - Serie electrónica: empieza con 'B' seguido de 3 alfanuméricos (ej: B001).
      - Serie de contingencia: 4 dígitos numéricos.
    Correlativo: entero positivo entre 1 y 99999999 (máx 8 dígitos).
    """
    if tipo_documento not in ("01", "03"):
        return False, f"Tipo de documento '{tipo_documento}' no soportado para esta validación (use 01 o 03)."

    serie_limpia = serie.strip().upper() if serie else ""

    if tipo_documento == "01":
        patron_fe = r"^F[A-Z0-9]{3}$"
        patron_fisico = r"^[0-9]{4}$"
        if not (re.match(patron_fe, serie_limpia) or re.match(patron_fisico, serie_limpia)):
            return False, (
                f"La serie '{serie}' para Factura (01) debe tener 4 caracteres: "
                f"iniciar con 'F' (ej. F001) o ser numérico de 4 dígitos (contingencia)."
            )
    elif tipo_documento == "03":
        patron_be = r"^B[A-Z0-9]{3}$"
        patron_fisico = r"^[0-9]{4}$"
        if not (re.match(patron_be, serie_limpia) or re.match(patron_fisico, serie_limpia)):
            return False, (
                f"La serie '{serie}' para Boleta (03) debe tener 4 caracteres: "
                f"iniciar con 'B' (ej. B001) o ser numérico de 4 dígitos."
            )

    if not isinstance(correlativo, int) or correlativo <= 0:
        return False, f"El correlativo debe ser un entero positivo mayor a cero (recibido: {correlativo})."

    if correlativo > 99999999:
        return False, f"El correlativo supera el límite máximo permitido de 8 dígitos ({correlativo} > 99999999)."

    return True, "Serie y correlativo válidos."


def formatear_nombre_archivo_xml(
    ruc_emisor: str,
    tipo_documento: str,
    serie: str,
    correlativo: int,
    padding_correlativo: int = 8,
) -> str:
    """Construye el nombre de archivo XML estándar exigido por SUNAT:

        RRRRRRRRRRR-TT-SSSS-NNNNNNNN.xml

    Donde:
        RRRRRRRRRRR: RUC del emisor (11 dígitos validados por módulo 11).
        TT: Código del tipo de comprobante (Catálogo 01, ej. '01').
        SSSS: Serie fiscal de 4 caracteres (ej. 'F001').
        NNNNNNNN: Correlativo numérico con relleno a N dígitos (por defecto 8).
    """
    val_ruc = validar_ruc(ruc_emisor, estricto=True)
    val_serie, msg_serie = validar_serie_correlativo(tipo_documento, serie, correlativo)
    if not val_serie:
        raise ValidationError(msg_serie)

    correlativo_str = str(correlativo).zfill(padding_correlativo)
    return f"{val_ruc.ruc}-{tipo_documento}-{serie.upper()}-{correlativo_str}.xml"

