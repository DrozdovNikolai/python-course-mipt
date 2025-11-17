import csv
import sys
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import List, Dict

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

engine = create_engine('sqlite:///students.db')
Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True)
    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    faculty = Column(String, nullable=False)
    course = Column(String, nullable=False)
    score = Column(Integer, nullable=False)


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


if __name__ == '__main__':
    manager = StudentManager()

    manager.populate_from_csv('students.csv')
    print("Database populated successfully!")

    print("\nStudents in АВТФ faculty:")
    students = manager.get_students_by_faculty('АВТФ')
    for s in students[:5]:
        print(f"  {s['last_name']} {s['first_name']}: {s['score']}")

    print("\nUnique courses:")
    courses = manager.get_unique_courses()
    for course in courses:
        print(f"  - {course}")

    print("\nAverage scores by faculty:")
    faculties = set([s['faculty'] for s in students])
    for faculty in sorted(faculties):
        avg = manager.get_average_score_by_faculty(faculty)
        print(f"  {faculty}: {avg:.2f}")

    print("\nStudents in 'Мат. Анализ' with score < 30:")
    low_score_students = manager.get_low_score_students_by_course('Мат. Анализ', 30)
    for s in low_score_students[:5]:
        print(f"  {s['last_name']} {s['first_name']}: {s['score']}")

