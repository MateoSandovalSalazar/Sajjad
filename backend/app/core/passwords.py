"""
Política de contraseñas.

Un mínimo de longitud más "una mayúscula y un dígito" deja pasar
`Password1`, `Sajjad123` y compañía — justo las que encabezan
cualquier diccionario. Estas comprobaciones cierran ese hueco sin
convertir el registro en un examen.
"""

# Las contraseñas más usadas en filtraciones reales, en las formas
# que además superan el requisito de mayúscula + dígito. No pretende
# ser exhaustiva: corta lo evidente, el rate limiting hace el resto.
_COMMON_PASSWORDS = frozenset({
    "password1", "password12", "password123", "password1234",
    "passw0rd", "passw0rd1", "passw0rd123",
    "qwerty123", "qwerty1234", "qwertyui1",
    "welcome1", "welcome123", "abc12345", "abcd1234",
    "admin123", "administrator1", "letmein1", "letmein123",
    "iloveyou1", "sunshine1", "princess1", "football1",
    "monkey123", "dragon123", "master123", "shadow123",
    "trustno1", "starwars1", "superman1", "batman123",
    "contrasena1", "contrasena123", "contraseña1",
    "hola1234", "holamundo1", "mexico123", "colombia1",
    "argentina1", "12345678a", "a1234567", "1qaz2wsx",
    "sajjad123", "sajjad1234",
})

_MIN_DISTINCT_CHARS = 5


def validate_password(value: str) -> str:
    """
    Valida una contraseña o lanza ValueError con un mensaje en
    español apto para mostrar tal cual al usuario.

    Se usa desde los validadores de Pydantic, que convierten el
    ValueError en un 422 con el mensaje dentro.
    """
    if not any(c.isupper() for c in value):
        raise ValueError(
            "La contraseña debe incluir al menos una mayúscula."
        )
    if not any(c.islower() for c in value):
        raise ValueError(
            "La contraseña debe incluir al menos una minúscula."
        )
    if not any(c.isdigit() for c in value):
        raise ValueError(
            "La contraseña debe incluir al menos un número."
        )

    # `Aaaaaaa1` cumple todo lo anterior y no vale nada.
    if len(set(value)) < _MIN_DISTINCT_CHARS:
        raise ValueError(
            "La contraseña es demasiado repetitiva. "
            "Usa al menos 5 caracteres distintos."
        )

    if value.lower() in _COMMON_PASSWORDS:
        raise ValueError(
            "Esa contraseña aparece en listas de filtraciones "
            "conocidas. Elige otra."
        )

    return value
