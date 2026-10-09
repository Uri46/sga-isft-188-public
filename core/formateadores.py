"""Formateadores de presentación reutilizables (DNI, CUIL, teléfono, carreras)."""


def limpiar_dni(dni) -> str:
    """Normaliza un DNI recibido por URL/formulario (sin puntos, espacios ni guiones)."""
    return str(dni).replace('.', '').replace(' ', '').replace('-', '').strip()[:20]


def formatear_dni(dni):
    if not dni:
        return "-"
    digits = "".join(c for c in str(dni) if c.isdigit())
    if not digits:
        return str(dni)
    return f"{int(digits):,}".replace(",", ".")


def formatear_cuil(cuil):
    if not cuil or str(cuil).strip() in ['', 'None', '-', '--']:
        return "-"
    digits = "".join(c for c in str(cuil) if c.isdigit())
    if len(digits) == 11:
        return f"{digits[:2]}-{digits[2:10]}-{digits[10]}"
    return str(cuil)


def formatear_telefono(tel):
    if not tel or str(tel).strip() in ['', 'None', '-', '--']:
        return "-"
    digits = "".join(c for c in str(tel) if c.isdigit())
    if not digits:
        return str(tel)
    if digits.startswith('549'):
        digits = digits[3:]
    elif digits.startswith('54'):
        digits = digits[2:]
    if digits.startswith('0'):
        digits = digits[1:]

    if len(digits) == 10:
        if digits.startswith('11'):
            return f"+54 9 11 {digits[2:6]}-{digits[6:]}"
        else:
            return f"+54 9 {digits[:3]} {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 8:
        return f"+54 9 11 {digits[:4]}-{digits[4:]}"
    return f"+54 9 {digits}"


def formatear_carreras_con_resolucion(carreras_dict):
    """
    Formatea las carreras incluyendo su resolución y los años agrupados correctamente.
    Ejemplo:
    - 'Técnico Superior en Energía con Orientación Industrial (Res. 794/01) (1°, 2° y 3° Año)'
    - 'Tecnicatura Superior en Higiene y Seguridad en el Trabajo (Res. 320/13) (1° Año)'
    """
    resultado = []
    for (c_nom, c_res), anios_set in sorted(carreras_dict.items(), key=lambda x: x[0][0]):
        anios_clean = []
        for a in anios_set:
            digits = "".join(c for c in str(a) if c.isdigit())
            if digits:
                anios_clean.append(int(digits))
        anios_sorted = sorted(list(set(anios_clean)))

        if len(anios_sorted) == 1:
            anios_str = f"{anios_sorted[0]}° Año"
        elif len(anios_sorted) == 2:
            anios_str = f"{anios_sorted[0]}° y {anios_sorted[1]}° Año"
        elif len(anios_sorted) > 2:
            anios_str = f"{', '.join(f'{a}°' for a in anios_sorted[:-1])} y {anios_sorted[-1]}° Año"
        else:
            anios_str = "Año s/d"

        res_str = f" ({c_res})" if c_res and str(c_res).strip() not in ['', 'None', '-'] else ""
        resultado.append(f"{c_nom}{res_str} ({anios_str})")
    return resultado


def formatear_carreras_estructuradas(carreras_dict):
    """
    Formatea las carreras devolviendo una lista de diccionarios con el nombre, resolución y años separados.
    Útil para renderizar cada parte en etiquetas diferentes en el frontend.
    """
    resultado = []
    for (c_nom, c_res), anios_set in sorted(carreras_dict.items(), key=lambda x: x[0][0]):
        anios_clean = []
        for a in anios_set:
            digits = "".join(c for c in str(a) if c.isdigit())
            if digits:
                anios_clean.append(int(digits))
        anios_sorted = sorted(list(set(anios_clean)))

        if len(anios_sorted) == 1:
            anios_str = f"{anios_sorted[0]}° Año"
        elif len(anios_sorted) == 2:
            anios_str = f"{anios_sorted[0]}° y {anios_sorted[1]}° Año"
        elif len(anios_sorted) > 2:
            anios_str = f"{', '.join(f'{a}°' for a in anios_sorted[:-1])} y {anios_sorted[-1]}° Año"
        else:
            anios_str = "Año s/d"

        res_str = str(c_res).strip() if c_res and str(c_res).strip() not in ['', 'None', '-'] else "-"
        
        nombre_abreviado = str(c_nom).replace("Tecnicatura Superior en", "T.S. en").replace("Tecnicatura Superior", "T.S.").replace("Técnico Superior en", "T.S. en").replace("Técnico Superior", "T.S.")
        
        resultado.append({
            'nombre': nombre_abreviado,
            'resolucion': res_str,
            'anio': anios_str
        })
    return resultado

