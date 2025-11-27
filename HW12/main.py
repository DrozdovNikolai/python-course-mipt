import csv
import sys
import hashlib
import secrets
import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, func, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import List, Dict, Optional, Tuple
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from pydantic import BaseModel
import redis
from functools import wraps

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

engine = create_engine('sqlite:///students.db')
Base = declarative_base()
app = FastAPI(title="Students API with Authentication & Background Tasks")

# Redis cache configuration
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except (redis.ConnectionError, ConnectionRefusedError):
    REDIS_AVAILABLE = False
    redis_client = None
    print("⚠️  Redis not available. Caching disabled.")


# Cache management utilities
class CacheManager:
    """Manage Redis caching for API responses"""

    CACHE_TTL = 3600  # 1 hour cache TTL in seconds

    @staticmethod
    def make_cache_key(endpoint: str, params: dict = None) -> str:
        """Generate cache key from endpoint and parameters"""
        if params:
            param_str = json.dumps(params, sort_keys=True, default=str)
            return f"cache:{endpoint}:{hash(param_str)}"
        return f"cache:{endpoint}"

    @staticmethod
    def get(key: str) -> Optional[List[Dict]]:
        """Get value from cache"""
        if not REDIS_AVAILABLE:
            return None
        try:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None

    @staticmethod
    def set(key: str, value: List[Dict], ttl: int = CACHE_TTL) -> bool:
        """Set value in cache"""
        if not REDIS_AVAILABLE:
            return False
        try:
            redis_client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
        return False

    @staticmethod
    def delete(key: str) -> bool:
        """Delete value from cache"""
        if not REDIS_AVAILABLE:
            return False
        try:
            redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
        return False

    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        if not REDIS_AVAILABLE:
            return 0
        try:
            keys = redis_client.keys(pattern)
            if keys:
                return redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache invalidate error: {e}")
        return 0


class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True)
    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    faculty = Column(String, nullable=False)
    course = Column(String, nullable=False)
    score = Column(Integer, nullable=False)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_read_only = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    refresh_token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)


# Pydantic models for API requests/responses
class StudentCreate(BaseModel):
    last_name: str
    first_name: str
    faculty: str
    course: str
    score: int


class StudentUpdate(BaseModel):
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    faculty: Optional[str] = None
    course: Optional[str] = None
    score: Optional[int] = None


class StudentResponse(BaseModel):
    id: int
    last_name: str
    first_name: str
    faculty: str
    course: str
    score: int

    class Config:
        from_attributes = True


# Authentication models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    is_read_only: bool = False


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_read_only: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuthUser(BaseModel):
    user_id: int
    username: str
    is_read_only: bool
    is_active: bool


class StudentManager:
    def __init__(self, db_path='sqlite:///students.db'):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def populate_from_csv(self, csv_file: str) -> None:
        session = self.Session()
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    student = Student(
                        last_name=row['Фамилия'],
                        first_name=row['Имя'],
                        faculty=row['Факультет'],
                        course=row['Курс'],
                        score=int(row['Оценка'])
                    )
                    session.add(student)
            session.commit()
        finally:
            session.close()

    def get_students_by_faculty(self, faculty: str) -> List[Dict]:
        session = self.Session()
        try:
            students = session.query(Student).filter(
                Student.faculty == faculty
            ).all()
            result = [
                {
                    'id': s.id,
                    'last_name': s.last_name,
                    'first_name': s.first_name,
                    'faculty': s.faculty,
                    'course': s.course,
                    'score': s.score
                }
                for s in students
            ]
            return result
        finally:
            session.close()

    def get_unique_courses(self) -> List[str]:
        session = self.Session()
        try:
            courses = session.query(Student.course).distinct().all()
            return [course[0] for course in courses]
        finally:
            session.close()

    def get_average_score_by_faculty(self, faculty: str) -> float:
        session = self.Session()
        try:
            from sqlalchemy import func
            result = session.query(
                func.avg(Student.score)
            ).filter(
                Student.faculty == faculty
            ).scalar()
            return result if result else 0.0
        finally:
            session.close()

    def get_low_score_students_by_course(self, course: str, threshold: int = 30) -> List[Dict]:
        session = self.Session()
        try:
            students = session.query(Student).filter(
                Student.course == course,
                Student.score < threshold
            ).all()
            result = [
                {
                    'id': s.id,
                    'last_name': s.last_name,
                    'first_name': s.first_name,
                    'faculty': s.faculty,
                    'course': s.course,
                    'score': s.score
                }
                for s in students
            ]
            return result
        finally:
            session.close()

    def create_student(self, last_name: str, first_name: str, faculty: str, course: str, score: int) -> Dict:
        """Create a new student record"""
        session = self.Session()
        try:
            student = Student(
                last_name=last_name,
                first_name=first_name,
                faculty=faculty,
                course=course,
                score=score
            )
            session.add(student)
            session.commit()
            result = {
                'id': student.id,
                'last_name': student.last_name,
                'first_name': student.first_name,
                'faculty': student.faculty,
                'course': student.course,
                'score': student.score
            }
            return result
        finally:
            session.close()

    def get_student_by_id(self, student_id: int) -> Optional[Dict]:
        """Get student by ID"""
        session = self.Session()
        try:
            student = session.query(Student).filter(Student.id == student_id).first()
            if not student:
                return None
            return {
                'id': student.id,
                'last_name': student.last_name,
                'first_name': student.first_name,
                'faculty': student.faculty,
                'course': student.course,
                'score': student.score
            }
        finally:
            session.close()

    def get_all_students(self) -> List[Dict]:
        """Get all students"""
        session = self.Session()
        try:
            students = session.query(Student).all()
            result = [
                {
                    'id': s.id,
                    'last_name': s.last_name,
                    'first_name': s.first_name,
                    'faculty': s.faculty,
                    'course': s.course,
                    'score': s.score
                }
                for s in students
            ]
            return result
        finally:
            session.close()

    def update_student(self, student_id: int, **kwargs) -> Optional[Dict]:
        """Update student record"""
        session = self.Session()
        try:
            student = session.query(Student).filter(Student.id == student_id).first()
            if not student:
                return None

            for key, value in kwargs.items():
                if value is not None and hasattr(student, key):
                    setattr(student, key, value)

            session.commit()
            result = {
                'id': student.id,
                'last_name': student.last_name,
                'first_name': student.first_name,
                'faculty': student.faculty,
                'course': student.course,
                'score': student.score
            }
            return result
        finally:
            session.close()

    def delete_student(self, student_id: int) -> bool:
        """Delete student record"""
        session = self.Session()
        try:
            student = session.query(Student).filter(Student.id == student_id).first()
            if not student:
                return False
            session.delete(student)
            session.commit()
            return True
        finally:
            session.close()

    def populate_from_csv_background(self, csv_file: str) -> Dict:
        """Populate database from CSV file (background task)"""
        session = self.Session()
        try:
            count = 0
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    student = Student(
                        last_name=row['Фамилия'],
                        first_name=row['Имя'],
                        faculty=row['Факультет'],
                        course=row['Курс'],
                        score=int(row['Оценка'])
                    )
                    session.add(student)
                    count += 1
            session.commit()
            # Invalidate all cache related to students
            CacheManager.invalidate_pattern("cache:students*")
            return {
                'status': 'completed',
                'records_imported': count,
                'message': f'Successfully imported {count} student records'
            }
        except FileNotFoundError:
            return {
                'status': 'error',
                'message': f'File not found: {csv_file}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error importing CSV: {str(e)}'
            }
        finally:
            session.close()

    def delete_students_by_ids(self, student_ids: List[int]) -> Dict:
        """Delete multiple student records (background task)"""
        session = self.Session()
        try:
            deleted_count = 0
            for student_id in student_ids:
                student = session.query(Student).filter(Student.id == student_id).first()
                if student:
                    session.delete(student)
                    deleted_count += 1
            session.commit()
            # Invalidate all cache related to students
            CacheManager.invalidate_pattern("cache:students*")
            return {
                'status': 'completed',
                'records_deleted': deleted_count,
                'message': f'Successfully deleted {deleted_count} student records'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error deleting students: {str(e)}'
            }
        finally:
            session.close()


class AuthManager:
    """Manage user authentication and sessions"""

    def __init__(self, db_path='sqlite:///students.db'):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_value = password_hash.split(':')
            return hashlib.sha256((password + salt).encode()).hexdigest() == hash_value
        except:
            return False

    @staticmethod
    def generate_tokens() -> Tuple[str, str]:
        """Generate access and refresh tokens"""
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        return access_token, refresh_token

    def register_user(self, username: str, email: str, password: str, is_read_only: bool = False) -> Optional[Dict]:
        """Register new user"""
        session = self.Session()
        try:
            # Check if user exists
            existing = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            if existing:
                return None

            # Create new user
            user = User(
                username=username,
                email=email,
                password_hash=self.hash_password(password),
                is_read_only=is_read_only,
                is_active=True
            )
            session.add(user)
            session.commit()

            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_read_only': user.is_read_only,
                'is_active': user.is_active,
                'created_at': user.created_at
            }
        finally:
            session.close()

    def login_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and create session"""
        session = self.Session()
        try:
            user = session.query(User).filter(User.username == username).first()
            if not user or not user.is_active:
                return None

            if not self.verify_password(password, user.password_hash):
                return None

            # Generate tokens
            access_token, refresh_token = self.generate_tokens()
            expires_at = datetime.utcnow() + timedelta(hours=24)

            # Create session
            db_session = Session(
                user_id=user.id,
                token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                is_active=True
            )
            session.add(db_session)
            session.commit()

            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_id': user.id,
                'username': user.username,
                'is_read_only': user.is_read_only
            }
        finally:
            session.close()

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify token and return user info"""
        session = self.Session()
        try:
            db_session = session.query(Session).filter(
                (Session.token == token) & (Session.is_active == True)
            ).first()

            if not db_session:
                return None

            if db_session.expires_at < datetime.utcnow():
                return None

            user = session.query(User).filter(User.id == db_session.user_id).first()
            if not user or not user.is_active:
                return None

            return {
                'user_id': user.id,
                'username': user.username,
                'is_read_only': user.is_read_only,
                'is_active': user.is_active
            }
        finally:
            session.close()

    def refresh_token_user(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token using refresh token"""
        session = self.Session()
        try:
            db_session = session.query(Session).filter(
                (Session.refresh_token == refresh_token) & (Session.is_active == True)
            ).first()

            if not db_session:
                return None

            user = session.query(User).filter(User.id == db_session.user_id).first()
            if not user or not user.is_active:
                return None

            # Generate new tokens
            new_access_token, new_refresh_token = self.generate_tokens()
            new_expires_at = datetime.utcnow() + timedelta(hours=24)

            # Update session
            db_session.token = new_access_token
            db_session.refresh_token = new_refresh_token
            db_session.expires_at = new_expires_at
            session.commit()

            return {
                'access_token': new_access_token,
                'refresh_token': new_refresh_token,
                'user_id': user.id,
                'username': user.username,
                'is_read_only': user.is_read_only
            }
        finally:
            session.close()

    def logout_user(self, token: str) -> bool:
        """Logout user by invalidating session"""
        session = self.Session()
        try:
            db_session = session.query(Session).filter(Session.token == token).first()
            if not db_session:
                return False

            db_session.is_active = False
            session.commit()
            return True
        finally:
            session.close()


# Initialize managers as global variables
manager = StudentManager()
auth_manager = AuthManager()


# Dependency for authentication
async def get_current_user(authorization: str = Header(None)) -> AuthUser:
    """Verify token and return current user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    user_info = auth_manager.verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return AuthUser(**user_info)


def check_read_only(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Ensure user has write permissions"""
    if user.is_read_only:
        raise HTTPException(status_code=403, detail="User has read-only access")
    return user


# Authentication Endpoints

@app.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
def register(user_data: UserRegister):
    """Register new user"""
    result = auth_manager.register_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        is_read_only=user_data.is_read_only
    )
    if not result:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    return result


@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(user_data: UserLogin):
    """Login user and return tokens"""
    result = auth_manager.login_user(
        username=user_data.username,
        password=user_data.password
    )
    if not result:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return result


@app.post("/auth/refresh", response_model=TokenResponse, tags=["Authentication"])
def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    result = auth_manager.refresh_token_user(refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return result


@app.post("/auth/logout", tags=["Authentication"])
def logout(user: AuthUser = Depends(get_current_user), authorization: str = Header(None)):
    """Logout user and invalidate session"""
    try:
        scheme, token = authorization.split()
        success = auth_manager.logout_user(token)
        if not success:
            raise HTTPException(status_code=400, detail="Logout failed")
        return {"message": "Logged out successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid authorization header")


# CRUD Endpoints (Protected)

# CREATE - Add new student
@app.post("/students", response_model=StudentResponse, tags=["CRUD"])
def create_student(student: StudentCreate, user: AuthUser = Depends(check_read_only)):
    """Create a new student (requires authentication and write access)"""
    result = manager.create_student(
        last_name=student.last_name,
        first_name=student.first_name,
        faculty=student.faculty,
        course=student.course,
        score=student.score
    )
    # Invalidate cache after creating a student
    CacheManager.invalidate_pattern("cache:students*")
    return result


# READ - Get all students
@app.get("/students", response_model=List[StudentResponse], tags=["CRUD"])
def get_all_students(user: AuthUser = Depends(get_current_user)):
    """Get all students (requires authentication)"""
    cache_key = CacheManager.make_cache_key("students:all")
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    result = manager.get_all_students()
    CacheManager.set(cache_key, result)
    return result


# READ - Get student by ID
@app.get("/students/{student_id}", response_model=StudentResponse, tags=["CRUD"])
def get_student(student_id: int, user: AuthUser = Depends(get_current_user)):
    """Get a specific student by ID (requires authentication)"""
    cache_key = CacheManager.make_cache_key("students:by_id", {"id": student_id})
    cached = CacheManager.get(cache_key)
    if cached is not None and len(cached) > 0:
        return cached[0]
    student = manager.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    CacheManager.set(cache_key, [student])
    return student


# UPDATE - Update student
@app.put("/students/{student_id}", response_model=StudentResponse, tags=["CRUD"])
def update_student(student_id: int, student_update: StudentUpdate, user: AuthUser = Depends(check_read_only)):
    """Update a student (requires authentication and write access)"""
    result = manager.update_student(
        student_id,
        last_name=student_update.last_name,
        first_name=student_update.first_name,
        faculty=student_update.faculty,
        course=student_update.course,
        score=student_update.score
    )
    if not result:
        raise HTTPException(status_code=404, detail="Student not found")
    # Invalidate related caches
    CacheManager.invalidate_pattern("cache:students*")
    return result


# DELETE - Delete student
@app.delete("/students/{student_id}", tags=["CRUD"])
def delete_student(student_id: int, user: AuthUser = Depends(check_read_only)):
    """Delete a student (requires authentication and write access)"""
    success = manager.delete_student(student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")
    # Invalidate related caches
    CacheManager.invalidate_pattern("cache:students*")
    return {"message": "Student deleted successfully"}


# Background Task Endpoints

@app.post("/students/import-csv", tags=["Background Tasks"])
def import_csv_background(csv_file: str, background_tasks: BackgroundTasks, user: AuthUser = Depends(check_read_only)):
    """
    Import student records from CSV file as background task

    Parameters:
    - csv_file: Path to CSV file (e.g., 'students.csv')

    Returns task status immediately, processing happens in background
    """
    background_tasks.add_task(manager.populate_from_csv_background, csv_file)
    return {
        "status": "processing",
        "message": f"CSV import started for file: {csv_file}",
        "csv_file": csv_file
    }


class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete"""
    student_ids: List[int]


@app.post("/students/bulk-delete", tags=["Background Tasks"])
def delete_students_bulk(request: BulkDeleteRequest, background_tasks: BackgroundTasks, user: AuthUser = Depends(check_read_only)):
    """
    Delete multiple student records by IDs as background task

    Parameters:
    - student_ids: List of student IDs to delete

    Returns task status immediately, deletion happens in background
    """
    if not request.student_ids:
        raise HTTPException(status_code=400, detail="student_ids list cannot be empty")

    background_tasks.add_task(manager.delete_students_by_ids, request.student_ids)
    return {
        "status": "processing",
        "message": f"Bulk delete started for {len(request.student_ids)} students",
        "student_ids": request.student_ids
    }


# Additional endpoints for queries

# GET students by faculty
@app.get("/students/faculty/{faculty}", response_model=List[StudentResponse], tags=["Queries"])
def get_students_by_faculty(faculty: str, _: AuthUser = Depends(get_current_user)):
    """Get all students from a specific faculty (requires authentication)"""
    cache_key = CacheManager.make_cache_key("students:by_faculty", {"faculty": faculty})
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    result = manager.get_students_by_faculty(faculty)
    CacheManager.set(cache_key, result)
    return result


# GET unique courses
@app.get("/courses/unique", response_model=List[str], tags=["Queries"])
def get_unique_courses(_: AuthUser = Depends(get_current_user)):
    """Get list of all unique courses (requires authentication)"""
    cache_key = CacheManager.make_cache_key("courses:unique")
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    result = manager.get_unique_courses()
    # Store as dict list for consistency
    CacheManager.set(cache_key, [{"course": c} for c in result])
    return result


# GET average score by faculty
@app.get("/faculty/{faculty}/average-score", tags=["Queries"])
def get_average_score(faculty: str, _: AuthUser = Depends(get_current_user)):
    """Get average score for a faculty (requires authentication)"""
    cache_key = CacheManager.make_cache_key("faculty:avg_score", {"faculty": faculty})
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached[0]
    avg_score = manager.get_average_score_by_faculty(faculty)
    result = {"faculty": faculty, "average_score": avg_score}
    CacheManager.set(cache_key, [result])
    return result


# GET low score students by course
@app.get("/courses/{course}/low-scores", response_model=List[StudentResponse], tags=["Queries"])
def get_low_score_students(course: str, threshold: int = 30, _: AuthUser = Depends(get_current_user)):
    """Get students with low scores in a specific course (requires authentication)"""
    cache_key = CacheManager.make_cache_key("students:low_scores", {"course": course, "threshold": threshold})
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    result = manager.get_low_score_students_by_course(course, threshold)
    CacheManager.set(cache_key, result)
    return result


# Root endpoint
@app.get("/", tags=["Info"])
def root():
    """API root endpoint"""
    return {
        "message": "Students API",
        "version": "1.0",
        "endpoints": {
            "CRUD": [
                "POST /students",
                "GET /students",
                "GET /students/{student_id}",
                "PUT /students/{student_id}",
                "DELETE /students/{student_id}"
            ],
            "Queries": [
                "GET /students/faculty/{faculty}",
                "GET /courses/unique",
                "GET /faculty/{faculty}/average-score",
                "GET /courses/{course}/low-scores"
            ]
        }
    }


# Test function for CLI usage
def test_cli():
    """Test the API using CLI"""
    print("Database initialized!")
    print("\nRunning tests...")

    # Get all students count
    all_students = manager.get_all_students()
    print(f"Total students: {len(all_students)}")

    if all_students:
        print("\nFirst 3 students:")
        for s in all_students[:3]:
            print(f"  {s['id']}: {s['last_name']} {s['first_name']} ({s['faculty']})")

        # Test faculty query
        first_faculty = all_students[0]['faculty']
        faculty_students = manager.get_students_by_faculty(first_faculty)
        print(f"\nStudents in {first_faculty}: {len(faculty_students)}")

        # Test unique courses
        courses = manager.get_unique_courses()
        print(f"\nUnique courses: {len(courses)}")
        for course in courses:
            print(f"  - {course}")

        # Test average score
        avg = manager.get_average_score_by_faculty(first_faculty)
        print(f"\nAverage score in {first_faculty}: {avg:.2f}")

        # Test low score students
        if courses:
            low_score = manager.get_low_score_students_by_course(courses[0], 30)
            print(f"\nLow score students in {courses[0]}: {len(low_score)}")


if __name__ == '__main__':
    import uvicorn

    # Check if database needs initial population
    all_students = manager.get_all_students()
    if len(all_students) == 0:
        try:
            manager.populate_from_csv('students.csv')
            print("Database populated from CSV!")
        except FileNotFoundError:
            print("students.csv not found. Starting with empty database.")

    print(f"Total students in database: {len(manager.get_all_students())}")
    print("\nStarting FastAPI server...")
    print("API Documentation available at: http://localhost:8000/docs")

    uvicorn.run(app, host="0.0.0.0", port=8000)
