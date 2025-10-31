import pytest
from datetime import timedelta
from app.core.security import SecurityManager


def test_password_hash_different_each_time():
    """Хеш одного пароля дает разные результаты"""
    password = "TestPassword123!"
    hash1 = SecurityManager.get_password_hash(password)
    hash2 = SecurityManager.get_password_hash(password)
    
    assert hash1 != hash2
    assert SecurityManager.verify_password(password, hash1)
    assert SecurityManager.verify_password(password, hash2)


def test_password_verification_fails_wrong_password():
    """Проверка неверного пароля"""
    correct = "CorrectPass123!"
    wrong = "WrongPass123!"
    
    hashed = SecurityManager.get_password_hash(correct)
    
    assert SecurityManager.verify_password(correct, hashed)
    assert not SecurityManager.verify_password(wrong, hashed)


def test_password_strength_validation():
    """Валидация силы пароля"""
    # Слишком короткий
    ok, msg = SecurityManager.validate_password_strength("short")
    assert not ok
    assert "at least" in msg.lower()
    
    # Достаточно длинный
    ok, msg = SecurityManager.validate_password_strength("LongEnoughPassword123!")
    assert ok
    assert "valid" in msg.lower()


def test_create_access_token():
    """Создание access токена"""
    user_id = "user-123"
    token = SecurityManager.create_access_token(user_id)
    
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Проверяем, что токен валидный
    payload = SecurityManager.verify_token(token, allowed_types={"access"})
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "access"


def test_create_access_token_with_expiry():
    """Создание токена с истечением"""
    user_id = "user-456"
    expires = timedelta(minutes=30)
    
    token = SecurityManager.create_access_token(user_id, expires_delta=expires)
    
    payload = SecurityManager.verify_token(token)
    assert payload is not None
    assert "exp" in payload
    assert "iat" in payload


def test_create_robot_token():
    """Создание токена для робота"""
    robot_id = "RB-001"
    token = SecurityManager.create_robot_token(robot_id)
    
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Проверяем тип токена
    payload = SecurityManager.verify_token(token, allowed_types={"robot"})
    assert payload is not None
    assert payload["sub"] == robot_id
    assert payload["type"] == "robot"


def test_verify_token_invalid():
    """Проверка невалидного токена"""
    invalid_token = "invalid.token.here"
    
    payload = SecurityManager.verify_token(invalid_token)
    assert payload is None


def test_verify_token_wrong_type():
    """Проверка токена неправильного типа"""
    # Создаем access токен
    token = SecurityManager.create_access_token("user-123")
    
    # Пытаемся проверить как robot токен
    payload = SecurityManager.verify_token(token, allowed_types={"robot"})
    assert payload is None


def test_verify_token_multiple_allowed_types():
    """Проверка с несколькими разрешенными типами"""
    access_token = SecurityManager.create_access_token("user-123")
    robot_token = SecurityManager.create_robot_token("RB-001")
    
    # access токен должен пройти
    payload = SecurityManager.verify_token(
        access_token,
        allowed_types={"access", "robot"}
    )
    assert payload is not None
    assert payload["type"] == "access"
    
    # robot токен тоже должен пройти
    payload = SecurityManager.verify_token(
        robot_token,
        allowed_types={"access", "robot"}
    )
    assert payload is not None
    assert payload["type"] == "robot"


def test_verify_token_no_type_restriction():
    """Проверка без ограничения типа"""
    access_token = SecurityManager.create_access_token("user-123")
    robot_token = SecurityManager.create_robot_token("RB-001")
    
    # Оба должны пройти
    payload1 = SecurityManager.verify_token(access_token)
    assert payload1 is not None
    
    payload2 = SecurityManager.verify_token(robot_token)
    assert payload2 is not None


def test_token_contains_required_fields():
    """Токен содержит обязательные поля"""
    token = SecurityManager.create_access_token("user-123")
    payload = SecurityManager.verify_token(token)
    
    assert payload is not None
    assert "sub" in payload
    assert "type" in payload
    assert "iat" in payload
    assert "nbf" in payload
    assert "exp" in payload


def test_robot_token_long_expiry():
    """Токен робота с длительным сроком действия"""
    robot_id = "RB-LONG-001"
    expires = timedelta(days=365)  # год
    
    token = SecurityManager.create_robot_token(robot_id, expires_delta=expires)
    payload = SecurityManager.verify_token(token)
    
    assert payload is not None
    assert payload["sub"] == robot_id
    
    # Проверяем, что exp действительно далеко в будущем
    import time
    exp_timestamp = payload["exp"]
    current_timestamp = time.time()
    
    # Разница должна быть примерно год (с небольшой погрешностью)
    difference_days = (exp_timestamp - current_timestamp) / (60 * 60 * 24)
    assert 364 <= difference_days <= 366


@pytest.mark.parametrize("password,expected_valid", [
    ("ab", False),           # слишком короткий
    ("abc", False),          # слишком короткий
    ("abcd", False),         # слишком короткий (если MIN_LENGTH > 4)
    ("ValidPassword123!", True),  # нормальный
    ("AnotherGoodOne456", True),  # нормальный
])
def test_password_strength_parametrized(password, expected_valid):
    """Параметризованная проверка силы пароля"""
    ok, msg = SecurityManager.validate_password_strength(password)
    assert ok == expected_valid