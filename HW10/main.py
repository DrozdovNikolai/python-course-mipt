import csv
import sys
from sqlalchemy import create_engine, Column, Integer, String, func
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

engine = create_engine('sqlite:///students.db')
Base = declarative_base()
app = FastAPI(title="Students API")

class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True)
    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    faculty = Column(String, nullable=False)
    course = Column(String, nullable=False)
    score = Column(Integer, nullable=False)


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


# Initialize manager as a global variable
manager = StudentManager()


# CRUD Endpoints

# CREATE - Add new student
@app.post("/students", response_model=StudentResponse, tags=["CRUD"])
def create_student(student: StudentCreate):
    """Create a new student"""
    result = manager.create_student(
        last_name=student.last_name,
        first_name=student.first_name,
        faculty=student.faculty,
        course=student.course,
        score=student.score
    )
    return result


# READ - Get all students
@app.get("/students", response_model=List[StudentResponse], tags=["CRUD"])
def get_all_students():
    """Get all students"""
    return manager.get_all_students()


# READ - Get student by ID
@app.get("/students/{student_id}", response_model=StudentResponse, tags=["CRUD"])
def get_student(student_id: int):
    """Get a specific student by ID"""
    student = manager.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# UPDATE - Update student
@app.put("/students/{student_id}", response_model=StudentResponse, tags=["CRUD"])
def update_student(student_id: int, student_update: StudentUpdate):
    """Update a student"""
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
    return result


# DELETE - Delete student
@app.delete("/students/{student_id}", tags=["CRUD"])
def delete_student(student_id: int):
    """Delete a student"""
    success = manager.delete_student(student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}


# Additional endpoints for queries

# GET students by faculty
@app.get("/students/faculty/{faculty}", response_model=List[StudentResponse], tags=["Queries"])
def get_students_by_faculty(faculty: str):
    """Get all students from a specific faculty"""
    return manager.get_students_by_faculty(faculty)


# GET unique courses
@app.get("/courses/unique", response_model=List[str], tags=["Queries"])
def get_unique_courses():
    """Get list of all unique courses"""
    return manager.get_unique_courses()


# GET average score by faculty
@app.get("/faculty/{faculty}/average-score", tags=["Queries"])
def get_average_score(faculty: str):
    """Get average score for a faculty"""
    avg_score = manager.get_average_score_by_faculty(faculty)
    return {"faculty": faculty, "average_score": avg_score}


# GET low score students by course
@app.get("/courses/{course}/low-scores", response_model=List[StudentResponse], tags=["Queries"])
def get_low_score_students(course: str, threshold: int = 30):
    """Get students with low scores in a specific course"""
    return manager.get_low_score_students_by_course(course, threshold)


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
