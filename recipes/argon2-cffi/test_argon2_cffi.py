import pytest


# See https://argon2-cffi.readthedocs.io/en/stable/
def test_basic(self):
    import argon2

    ph = argon2.PasswordHasher()
    hashed = ph.hash("s3kr3tp4ssw0rd")
    assert hashed.startswith("$argon2")
    assert ph.verify(hashed, "s3kr3tp4ssw0rd")
    with pytest.raises(argon2.exceptions.VerifyMismatchError):
        ph.verify(hashed, "s3kr3tp4sswOrd")
