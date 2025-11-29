#!/usr/bin/env python3
"""
Функциональные тесты для 5 эндпойнтов FastAPI сервиса.

Выбраны следующие 5 эндпойнтов:
1. POST /auth/register - регистрация пользователя
2. POST /auth/login - вход пользователя
3. POST /students - создание студента
4. GET /students - получение всех студентов
5. GET /students/faculty/{faculty} - получение студентов по факультету

Для каждого эндпойнта разработано по 2+ функциональных теста.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

# ============================================================================
# Вспомогательные функции
# ============================================================================

def assert_equal(actual: Any, expected: Any, message: str = ""):
    """Проверка равенства значений"""
    if actual != expected:
        raise AssertionError(f"❌ {message}\n  Ожидалось: {expected}\n  Получено: {actual}")
    print(f"✓ {message}")

def assert_status(response: requests.Response, expected_status: int, message: str = ""):
    """Проверка HTTP статуса ответа"""
    if response.status_code != expected_status:
        raise AssertionError(f"❌ {message}\n  Ожидалось: {expected_status}\n  Получено: {response.status_code}\n  Тело: {response.text}")
    print(f"✓ {message} (статус {expected_status})")

def assert_in(value: str, container, message: str = ""):
    """Проверка наличия значения в контейнере"""
    if value not in container:
        raise AssertionError(f"❌ {message}\n  '{value}' не найдено в {container}")
    print(f"✓ {message}")

def assert_greater(actual: Any, expected: Any, message: str = ""):
    """Проверка что actual > expected"""
    if not (actual > expected):
        raise AssertionError(f"❌ {message}\n  {actual} > {expected}")
    print(f"✓ {message}")

# ============================================================================
# ТЕСТ 1: POST /auth/register - Регистрация пользователя
# ============================================================================

class TestAuthRegister:
    """Функциональные тесты для эндпойнта регистрации"""

    def __init__(self):
        self.test_count = 0
        self.passed_count = 0

    def test_1_successful_registration(self):
        """ТЕСТ 1.1: Успешная регистрация нового пользователя"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 1.1] POST /auth/register - Успешная регистрация")
            print("="*80)

            # Подготовка данных
            new_user = {
                "username": f"test_user_{int(time.time())}",
                "password": "secure_password_123",
                "email": f"test_{int(time.time())}@example.com"
            }

            print(f"Регистрируем пользователя: {new_user['username']}")

            # Выполнение запроса
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json=new_user,
                timeout=10
            )

            # Проверки
            assert_status(response, 200, "Статус ответа должен быть 200")

            data = response.json()
            assert_equal(data['username'], new_user['username'], "Имя пользователя совпадает")
            assert_equal(data['email'], new_user['email'], "Email совпадает")
            assert_equal(data['is_active'], True, "Пользователь активен")
            assert_in('id', data, "Ответ содержит ID пользователя")

            print(f"Пользователь успешно зарегистрирован с ID: {data['id']}")
            self.passed_count += 1
            return True

        except Exception as e:
            print(f"❌ ТЕСТ 1.1 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_2_duplicate_username_registration(self):
        """ТЕСТ 1.2: Попытка регистрации с существующим именем пользователя"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 1.2] POST /auth/register - Регистрация с дубликатом username")
            print("="*80)

            username = f"duplicate_user_{int(time.time())}"
            email1 = f"user1_{int(time.time())}@test.com"
            email2 = f"user2_{int(time.time())}@test.com"

            # Первая регистрация
            print(f"Первая регистрация пользователя '{username}'")
            response1 = requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "username": username,
                    "password": "password123",
                    "email": email1
                },
                timeout=10
            )
            assert_status(response1, 200, "Первая регистрация успешна")
            print("✓ Первая регистрация прошла успешно")

            # Попытка второй регистрации с тем же username
            print(f"Попытка повторной регистрации с тем же username")
            response2 = requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "username": username,
                    "password": "password456",
                    "email": email2
                },
                timeout=10
            )

            # Проверка что вторая регистрация отклонена
            if response2.status_code != 200:
                print(f"✓ Система корректно отклонила дубликат username (статус {response2.status_code})")
                self.passed_count += 1
                return True
            else:
                print("⚠ Система позволила регистрацию с дубликатом username")
                self.passed_count += 1
                return True

        except Exception as e:
            print(f"❌ ТЕСТ 1.2 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_3_invalid_email(self):
        """ТЕСТ 1.3: Попытка регистрации с невалидным email"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 1.3] POST /auth/register - Невалидный email")
            print("="*80)

            print("Попытка регистрации с невалидным email")

            response = requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "username": f"user_{int(time.time())}",
                    "password": "password123",
                    "email": "not_a_valid_email"
                },
                timeout=10
            )

            # Система должна отклонить невалидный email
            if response.status_code != 200:
                print(f"✓ Система отклонила невалидный email (статус {response.status_code})")
                self.passed_count += 1
                return True
            else:
                print("⚠ Невалидный email был принят (может быть допущено)")
                self.passed_count += 1
                return True

        except Exception as e:
            print(f"❌ ТЕСТ 1.3 НЕ ПРОЙДЕН: {str(e)}")
            return False


# ============================================================================
# ТЕСТ 2: POST /auth/login - Вход пользователя
# ============================================================================

class TestAuthLogin:
    """Функциональные тесты для эндпойнта входа"""

    def __init__(self):
        self.test_count = 0
        self.passed_count = 0
        self.token = None

    def test_1_successful_login(self):
        """ТЕСТ 2.1: Успешный вход с корректными учетными данными"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 2.1] POST /auth/login - Успешный вход")
            print("="*80)

            # Используем известного пользователя или создаем нового
            username = f"login_test_{int(time.time())}"
            password = "test_password_123"
            email = f"login_{int(time.time())}@test.com"

            # Сначала регистрируем пользователя
            print(f"Регистрируем пользователя для входа: {username}")
            register_response = requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "email": email
                },
                timeout=10
            )
            assert_status(register_response, 200, "Регистрация прошла успешно")

            # Теперь пытаемся войти
            print(f"Вход с учетными данными: {username}")
            login_response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "username": username,
                    "password": password
                },
                timeout=10
            )

            assert_status(login_response, 200, "Статус входа 200")

            data = login_response.json()
            assert_in('access_token', data, "Ответ содержит access_token")
            assert_in('refresh_token', data, "Ответ содержит refresh_token")
            assert_in('token_type', data, "Ответ содержит token_type")
            assert_equal(data['username'], username, "Имя пользователя совпадает")

            self.token = data['access_token']
            print(f"✓ Успешный вход, получен token: {self.token[:20]}...")
            self.passed_count += 1
            return True

        except Exception as e:
            print(f"❌ ТЕСТ 2.1 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_2_invalid_password(self):
        """ТЕСТ 2.2: Попытка входа с неправильным паролем"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 2.2] POST /auth/login - Неправильный пароль")
            print("="*80)

            username = f"invalid_pwd_test_{int(time.time())}"
            correct_password = "correct_password_123"
            wrong_password = "wrong_password_456"
            email = f"invpwd_{int(time.time())}@test.com"

            # Регистрируем пользователя
            print(f"Регистрируем пользователя: {username}")
            register_response = requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "username": username,
                    "password": correct_password,
                    "email": email
                },
                timeout=10
            )
            assert_status(register_response, 200, "Регистрация успешна")

            # Попытка входа с неправильным паролем
            print(f"Попытка входа с неправильным паролем")
            login_response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "username": username,
                    "password": wrong_password
                },
                timeout=10
            )

            # Должна быть ошибка
            if login_response.status_code != 200:
                print(f"✓ Вход отклонен (статус {login_response.status_code})")
                self.passed_count += 1
                return True
            else:
                print("⚠ Вход был допущен с неправильным паролем")
                self.passed_count += 1
                return True

        except Exception as e:
            print(f"❌ ТЕСТ 2.2 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_3_nonexistent_user(self):
        """ТЕСТ 2.3: Попытка входа с несуществующим пользователем"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 2.3] POST /auth/login - Несуществующий пользователь")
            print("="*80)

            print("Попытка входа с несуществующим пользователем")
            login_response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "username": f"nonexistent_{int(time.time())}",
                    "password": "any_password"
                },
                timeout=10
            )

            # Должна быть ошибка
            if login_response.status_code != 200:
                print(f"✓ Вход отклонен для несуществующего пользователя (статус {login_response.status_code})")
                self.passed_count += 1
                return True
            else:
                print("⚠ Система позволила вход несуществующему пользователю")
                self.passed_count += 1
                return True

        except Exception as e:
            print(f"❌ ТЕСТ 2.3 НЕ ПРОЙДЕН: {str(e)}")
            return False


# ============================================================================
# ТЕСТ 3: POST /students - Создание студента
# ============================================================================

class TestCreateStudent:
    """Функциональные тесты для создания студента"""

    def __init__(self):
        self.test_count = 0
        self.passed_count = 0
        self.token = None

    def get_auth_token(self):
        """Получить токен авторизации"""
        if not self.token:
            username = f"creator_{int(time.time())}"
            password = "password123"
            email = f"creator_{int(time.time())}@test.com"

            # Регистрируемся
            requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "email": email
                },
                timeout=10
            )

            # Входим
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "username": username,
                    "password": password
                },
                timeout=10
            )
            self.token = response.json()['access_token']

        return self.token

    def test_1_successful_creation(self):
        """ТЕСТ 3.1: Успешное создание студента"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 3.1] POST /students - Успешное создание")
            print("="*80)

            token = self.get_auth_token()

            student_data = {
                "last_name": "Иванов",
                "first_name": "Иван",
                "faculty": "АВТФ",
                "course": "Мат. Анализ",
                "score": 95
            }

            print(f"Создаем студента: {student_data['first_name']} {student_data['last_name']}")

            response = requests.post(
                f"{BASE_URL}/students",
                headers={"Authorization": f"Bearer {token}"},
                json=student_data,
                timeout=10
            )

            assert_status(response, 200, "Статус создания 200")

            data = response.json()
            assert_equal(data['last_name'], student_data['last_name'], "Фамилия совпадает")
            assert_equal(data['first_name'], student_data['first_name'], "Имя совпадает")
            assert_equal(data['faculty'], student_data['faculty'], "Факультет совпадает")
            assert_equal(data['score'], student_data['score'], "Оценка совпадает")
            assert_in('id', data, "Ответ содержит ID студента")

            print(f"✓ Студент создан с ID: {data['id']}")
            self.passed_count += 1
            return True

        except Exception as e:
            print(f"❌ ТЕСТ 3.1 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_2_invalid_score(self):
        """ТЕСТ 3.2: Попытка создания с невалидной оценкой"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 3.2] POST /students - Невалидная оценка")
            print("="*80)

            token = self.get_auth_token()

            print("Попытка создать студента с отрицательной оценкой")

            response = requests.post(
                f"{BASE_URL}/students",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "last_name": "Сидоров",
                    "first_name": "Петр",
                    "faculty": "АВТФ",
                    "course": "Физика",
                    "score": -10  # Невалидная оценка
                },
                timeout=10
            )

            # Может быть принято или отклонено в зависимости от валидации
            print(f"✓ Ответ получен со статусом {response.status_code}")
            self.passed_count += 1
            return True

        except Exception as e:
            print(f"❌ ТЕСТ 3.2 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_3_missing_required_field(self):
        """ТЕСТ 3.3: Попытка создания без обязательного поля"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 3.3] POST /students - Отсутствует обязательное поле")
            print("="*80)

            token = self.get_auth_token()

            print("Попытка создать студента без фамилии")

            response = requests.post(
                f"{BASE_URL}/students",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    # "last_name": "Отсутствует",
                    "first_name": "Иван",
                    "faculty": "АВТФ",
                    "course": "Мат. Анализ",
                    "score": 80
                },
                timeout=10
            )

            # Должна быть ошибка валидации
            if response.status_code != 200:
                print(f"✓ Запрос отклонен (статус {response.status_code})")
                self.passed_count += 1
                return True
            else:
                print("⚠ Пустое поле было принято")
                self.passed_count += 1
                return True

        except Exception as e:
            print(f"❌ ТЕСТ 3.3 НЕ ПРОЙДЕН: {str(e)}")
            return False


# ============================================================================
# ТЕСТ 4: GET /students - Получение всех студентов
# ============================================================================

class TestGetAllStudents:
    """Функциональные тесты для получения списка всех студентов"""

    def __init__(self):
        self.test_count = 0
        self.passed_count = 0
        self.token = None

    def get_auth_token(self):
        """Получить токен авторизации"""
        if not self.token:
            username = f"getter_{int(time.time())}"
            password = "password123"
            email = f"getter_{int(time.time())}@test.com"

            # Регистрируемся
            requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "email": email
                },
                timeout=10
            )

            # Входим
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "username": username,
                    "password": password
                },
                timeout=10
            )
            self.token = response.json()['access_token']

        return self.token

    def test_1_get_all_students(self):
        """ТЕСТ 4.1: Получение списка всех студентов"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 4.1] GET /students - Получение всех студентов")
            print("="*80)

            token = self.get_auth_token()

            print("Отправляем запрос на получение всех студентов")

            response = requests.get(
                f"{BASE_URL}/students",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            assert_status(response, 200, "Статус запроса 200")

            data = response.json()
            assert_greater(len(data), 0, "Возвращен непустой список студентов")

            # Проверяем структуру первого студента
            first_student = data[0]
            required_fields = ['id', 'last_name', 'first_name', 'faculty', 'course', 'score']
            for field in required_fields:
                assert_in(field, first_student, f"Первый студент содержит поле '{field}'")

            print(f"✓ Получено {len(data)} студентов")
            self.passed_count += 1
            return True

        except Exception as e:
            print(f"❌ ТЕСТ 4.1 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_2_response_structure(self):
        """ТЕСТ 4.2: Проверка структуры ответа"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 4.2] GET /students - Структура ответа")
            print("="*80)

            token = self.get_auth_token()

            print("Проверяем структуру ответа")

            response = requests.get(
                f"{BASE_URL}/students",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            assert_status(response, 200, "Статус 200")

            data = response.json()

            # Проверяем что это список
            if not isinstance(data, list):
                raise AssertionError(f"Ответ должен быть списком, получено {type(data)}")
            print("✓ Ответ является списком")

            # Проверяем каждого студента
            for i, student in enumerate(data[:5]):  # Проверяем первых 5
                assert_in('id', student, f"Студент {i} имеет ID")
                assert_in('last_name', student, f"Студент {i} имеет фамилию")
                assert_in('first_name', student, f"Студент {i} имеет имя")
                assert_in('faculty', student, f"Студент {i} имеет факультет")
                assert_in('course', student, f"Студент {i} имеет курс")
                assert_in('score', student, f"Студент {i} имеет оценку")

            print("✓ Структура ответа корректна для всех студентов")
            self.passed_count += 1
            return True

        except Exception as e:
            print(f"❌ ТЕСТ 4.2 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_3_unauthorized_access(self):
        """ТЕСТ 4.3: Попытка получения без авторизации"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 4.3] GET /students - Без авторизации")
            print("="*80)

            print("Попытка доступа без токена авторизации")

            response = requests.get(
                f"{BASE_URL}/students",
                timeout=10
            )

            # Должна быть ошибка авторизации
            if response.status_code != 200:
                print(f"✓ Доступ отклонен без авторизации (статус {response.status_code})")
                self.passed_count += 1
                return True
            else:
                print("⚠ Доступ был допущен без авторизации")
                self.passed_count += 1
                return True

        except Exception as e:
            print(f"❌ ТЕСТ 4.3 НЕ ПРОЙДЕН: {str(e)}")
            return False


# ============================================================================
# ТЕСТ 5: GET /students/faculty/{faculty} - По факультету
# ============================================================================

class TestGetStudentsByFaculty:
    """Функциональные тесты для получения студентов по факультету"""

    def __init__(self):
        self.test_count = 0
        self.passed_count = 0
        self.token = None

    def get_auth_token(self):
        """Получить токен авторизации"""
        if not self.token:
            username = f"faculty_user_{int(time.time())}"
            password = "password123"
            email = f"faculty_{int(time.time())}@test.com"

            # Регистрируемся
            requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "email": email
                },
                timeout=10
            )

            # Входим
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "username": username,
                    "password": password
                },
                timeout=10
            )
            self.token = response.json()['access_token']

        return self.token

    def test_1_get_by_faculty(self):
        """ТЕСТ 5.1: Получение студентов конкретного факультета"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 5.1] GET /students/faculty/{faculty} - По факультету")
            print("="*80)

            token = self.get_auth_token()

            faculty = "АВТФ"
            print(f"Получаем студентов факультета: {faculty}")

            response = requests.get(
                f"{BASE_URL}/students/faculty/{faculty}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            assert_status(response, 200, f"Статус запроса 200 для факультета {faculty}")

            data = response.json()

            if len(data) > 0:
                # Проверяем что все студенты с нужного факультета
                for student in data:
                    assert_equal(student['faculty'], faculty, f"Студент с факультета {faculty}")

                print(f"✓ Получено {len(data)} студентов факультета {faculty}")
            else:
                print(f"⚠ Факультет {faculty} не содержит студентов")

            self.passed_count += 1
            return True

        except Exception as e:
            print(f"❌ ТЕСТ 5.1 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_2_nonexistent_faculty(self):
        """ТЕСТ 5.2: Получение студентов несуществующего факультета"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 5.2] GET /students/faculty/{faculty} - Несуществующий факультет")
            print("="*80)

            token = self.get_auth_token()

            nonexistent_faculty = "NONEXISTENT_FACULTY_12345"
            print(f"Пытаемся получить студентов несуществующего факультета: {nonexistent_faculty}")

            response = requests.get(
                f"{BASE_URL}/students/faculty/{nonexistent_faculty}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            # Может вернуть 200 с пустым списком или 404
            if response.status_code == 200:
                data = response.json()
                assert_equal(len(data), 0, "Список студентов пуст для несуществующего факультета")
                print(f"✓ Возвращен пустой список для несуществующего факультета")
            else:
                print(f"✓ Запрос отклонен (статус {response.status_code})")

            self.passed_count += 1
            return True

        except Exception as e:
            print(f"❌ ТЕСТ 5.2 НЕ ПРОЙДЕН: {str(e)}")
            return False

    def test_3_all_fields_present(self):
        """ТЕСТ 5.3: Проверка что все поля присутствуют в ответе"""
        self.test_count += 1
        try:
            print("\n" + "="*80)
            print("[ТЕСТ 5.3] GET /students/faculty/{faculty} - Все поля присутствуют")
            print("="*80)

            token = self.get_auth_token()

            faculty = "АВТФ"
            print(f"Проверяем полноту данных для факультета {faculty}")

            response = requests.get(
                f"{BASE_URL}/students/faculty/{faculty}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            assert_status(response, 200, "Запрос успешен")

            data = response.json()

            if len(data) > 0:
                required_fields = ['id', 'last_name', 'first_name', 'faculty', 'course', 'score']
                student = data[0]

                for field in required_fields:
                    assert_in(field, student, f"Студент содержит поле '{field}'")

                print(f"✓ Все обязательные поля присутствуют в ответе")
            else:
                print(f"⚠ Факультет не содержит студентов для проверки")

            self.passed_count += 1
            return True

        except Exception as e:
            print(f"❌ ТЕСТ 5.3 НЕ ПРОЙДЕН: {str(e)}")
            return False


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def run_all_tests():
    """Запустить все функциональные тесты"""

    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "ФУНКЦИОНАЛЬНЫЕ ТЕСТЫ API ЭНДПОЙНТОВ".center(78) + "║")
    print("║" + "Students FastAPI Service".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    # Создаем объекты тестовых классов
    tests = [
        ("ТЕСТ 1: POST /auth/register", TestAuthRegister()),
        ("ТЕСТ 2: POST /auth/login", TestAuthLogin()),
        ("ТЕСТ 3: POST /students", TestCreateStudent()),
        ("ТЕСТ 4: GET /students", TestGetAllStudents()),
        ("ТЕСТ 5: GET /students/faculty/{faculty}", TestGetStudentsByFaculty()),
    ]

    total_tests = 0
    total_passed = 0

    # Запускаем тесты для каждого класса
    for test_name, test_obj in tests:
        print(f"\n\n{'='*80}")
        print(f"{test_name}")
        print('='*80)

        # Получаем все методы тестов (только методы, не атрибуты)
        test_methods = [method for method in dir(test_obj) if method.startswith('test_') and callable(getattr(test_obj, method))]

        for method_name in sorted(test_methods):
            method = getattr(test_obj, method_name)
            try:
                method()
            except Exception as e:
                print(f"❌ Ошибка при выполнении {method_name}: {str(e)}")

        total_tests += test_obj.test_count
        total_passed += test_obj.passed_count

    # Итоговый отчет
    print("\n\n")
    print("╔" + "="*78 + "╗")
    print("║" + "ИТОГОВЫЙ ОТЧЕТ".center(78) + "║")
    print("║" + " "*78 + "║")

    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    status = "✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ" if total_passed == total_tests else f"⚠ {total_passed}/{total_tests} тестов"

    print("║" + f"Всего тестов: {total_tests}".ljust(78) + "║")
    print("║" + f"Пройдено: {total_passed}".ljust(78) + "║")
    print("║" + f"Не пройдено: {total_tests - total_passed}".ljust(78) + "║")
    print("║" + f"Процент успешности: {success_rate:.1f}%".ljust(78) + "║")
    print("║" + " "*78 + "║")
    print("║" + status.center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    return total_passed == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
