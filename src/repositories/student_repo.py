"""
Student repository with specialized queries.
"""

from typing import Optional, List, Dict
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database.models import Student, Department
from src.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    """Repository for Student operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Student)
    
    async def get_by_email(self, email: str) -> Optional[Student]:
        """
        Get student by email.
        
        Args:
            email: Student email
        
        Returns:
            Student or None
        """
        query = select(Student).where(Student.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_roll_no(self, roll_no: str) -> Optional[Student]:
        """
        Get student by roll number.
        
        Args:
            roll_no: Student roll number
        
        Returns:
            Student or None
        """
        return await self.get(roll_no)
    
    async def get_with_department(self, roll_no: str) -> Optional[Student]:
        """
        Get student with department relationship loaded.
        
        Args:
            roll_no: Student roll number
        
        Returns:
            Student with department or None
        """
        query = (
            select(Student)
            .options(selectinload(Student.department))
            .where(Student.roll_no == roll_no)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_department(
        self,
        department_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Student]:
        """
        Get students by department.
        
        Args:
            department_id: Department ID
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of students
        """
        query = (
            select(Student)
            .where(Student.department_id == department_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_year(
        self,
        year: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Student]:
        """
        Get students by academic year.
        
        Args:
            year: Academic year (1-4)
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of students
        """
        query = (
            select(Student)
            .where(Student.year == year)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_department_and_year(
        self,
        department_id: int,
        year: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Student]:
        """
        Get students by department and year.
        
        Args:
            department_id: Department ID
            year: Academic year (1-4)
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of students
        """
        query = (
            select(Student)
            .where(
                and_(
                    Student.department_id == department_id,
                    Student.year == year
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_stay_type(
        self,
        stay_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Student]:
        """
        Get students by stay type (Hostel/Day Scholar).
        
        Args:
            stay_type: Stay type
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of students
        """
        query = (
            select(Student)
            .where(Student.stay_type == stay_type)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def search_students(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Student]:
        """
        Search students by name, roll_no, email, or year.
        
        Args:
            search_term: Search term
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of matching students
        """
        search_pattern = f"%{search_term}%"
        
        # Build search conditions
        conditions = [
            Student.name.ilike(search_pattern),
            Student.roll_no.ilike(search_pattern),
            Student.email.ilike(search_pattern)
        ]
        
        # If search term is numeric, also search by year
        if search_term.isdigit():
            year_value = int(search_term)
            if 1 <= year_value <= 4:
                conditions.append(Student.year == year_value)
        
        query = (
            select(Student)
            .where(or_(*conditions))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_active_students(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Student]:
        """
        Get active students only.
        
        Args:
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of active students
        """
        query = (
            select(Student)
            .where(Student.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count_by_department(self, department_id: int) -> int:
        """
        Count students in a department.
        
        Args:
            department_id: Department ID
        
        Returns:
            Number of students
        """
        query = (
            select(func.count())
            .select_from(Student)
            .where(Student.department_id == department_id)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def count_by_year(self, year: int) -> int:
        """
        Count students by academic year.
        
        Args:
            year: Academic year (1-4)
        
        Returns:
            Number of students
        """
        query = (
            select(func.count())
            .select_from(Student)
            .where(Student.year == year)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def count_by_stay_type(self, stay_type: str) -> int:
        """
        Count students by stay type.
        
        Args:
            stay_type: Stay type
        
        Returns:
            Number of students
        """
        query = (
            select(func.count())
            .select_from(Student)
            .where(Student.stay_type == stay_type)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_year_distribution(self) -> Dict[int, int]:
        """
        Get distribution of students across years.
        
        Returns:
            Dictionary of year counts {1: 50, 2: 45, 3: 40, 4: 35}
        """
        query = (
            select(Student.year, func.count(Student.roll_no))
            .group_by(Student.year)
            .order_by(Student.year)
        )
        result = await self.session.execute(query)
        return dict(result.all())
    
    async def get_department_distribution(self) -> Dict[str, int]:
        """
        Get distribution of students across departments.
        
        Returns:
            Dictionary of department counts
        """
        query = (
            select(Department.name, func.count(Student.roll_no))
            .join(Student.department)
            .group_by(Department.name)
            .order_by(func.count(Student.roll_no).desc())
        )
        result = await self.session.execute(query)
        return dict(result.all())
    
    async def get_stay_type_distribution(self) -> Dict[str, int]:
        """
        Get distribution of students by stay type.
        
        Returns:
            Dictionary of stay type counts {"Hostel": 120, "Day Scholar": 80}
        """
        query = (
            select(Student.stay_type, func.count(Student.roll_no))
            .group_by(Student.stay_type)
        )
        result = await self.session.execute(query)
        return dict(result.all())
    
    async def verify_email(self, roll_no: str) -> bool:
        """
        Mark student email as verified.
        
        Args:
            roll_no: Student roll number
        
        Returns:
            True if successful
        """
        student = await self.get(roll_no)
        if student:
            student.email_verified = True
            student.verification_token = None
            await self.session.commit()
            return True
        return False
    
    async def update_password(self, roll_no: str, password_hash: str) -> bool:
        """
        Update student password.
        
        Args:
            roll_no: Student roll number
            password_hash: New password hash
        
        Returns:
            True if successful
        """
        student = await self.get(roll_no)
        if student:
            student.password_hash = password_hash
            await self.session.commit()
            return True
        return False
    
    async def get_students_with_complaints_count(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[tuple]:
        """
        Get students with their complaint counts.
        
        Args:
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of (Student, complaint_count) tuples
        """
        from src.database.models import Complaint
        
        query = (
            select(Student, func.count(Complaint.id).label("complaint_count"))
            .outerjoin(Complaint, Student.roll_no == Complaint.student_roll_no)
            .group_by(Student.roll_no)
            .order_by(func.count(Complaint.id).desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.all()


__all__ = ["StudentRepository"]
