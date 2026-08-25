import base64
import hashlib
import hmac
import secrets
import re

PBKDF2_ITERATIONS = 260_000

# Password validation constants
MIN_PASSWORD_LENGTH = 8
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_DIGITS = True
REQUIRE_SPECIAL_CHARS = True


def validate_password(password: str) -> None:
    """
    Validate password meets security requirements.
    
    Args:
        password: Password to validate
        
    Raises:
        ValueError: If password doesn't meet requirements
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )

    if REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")

    if REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")

    if REQUIRE_DIGITS and not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

    if REQUIRE_SPECIAL_CHARS and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError(
            "Password must contain at least one special character (!@#$%^&*..."
        )


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-SHA256.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
    """
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8")
    hash_b64 = base64.urlsafe_b64encode(dk).decode("utf-8")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Previously hashed password
        
    Returns:
        True if passwords match, False otherwise
    """
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            _, iter_str, salt_b64, hash_b64 = hashed_password.split("$", 3)
            iterations = int(iter_str)
            salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
            expected_hash = base64.urlsafe_b64decode(hash_b64.encode("utf-8"))
            computed_hash = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode("utf-8"), salt, iterations
            )
            return hmac.compare_digest(computed_hash, expected_hash)
        except Exception:
            return False

    # Legacy fallback for existing passlib/bcrypt hashes from older versions.
    try:
        from passlib.context import CryptContext

        legacy_context = CryptContext(
            schemes=["bcrypt", "bcrypt_sha256"], deprecated="auto"
        )
        return legacy_context.verify(plain_password, hashed_password)
    except Exception:
        return False