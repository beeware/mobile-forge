def test_basic():
    import bcrypt

    hashed = b"$2b$12$9cwzD/MRnVT7uvkxAQvkIejrif4bwRTGvIRqO7xf4OYtDQ3sl8CWW"
    assert bcrypt.checkpw(b"password", hashed)
    assert not bcrypt.checkpw(b"passwerd", hashed)
