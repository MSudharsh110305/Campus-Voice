"""
Authority Update service for announcements and updates.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AuthorityUpdate
from src.repositories.authority_update_repo import AuthorityUpdateRepository
from src.repositories.student_repo import StudentRepository
from src.repositories.authority_repo import AuthorityRepository
from src.services.notification_service import notification_service

logger = logging.getLogger(__name__)


class AuthorityUpdateService:
    """Service for authority announcements and updates"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.update_repo = AuthorityUpdateRepository(db)
        self.student_repo = StudentRepository(db)
        self.authority_repo = AuthorityRepository(db)
    
    async def create_announcement(
        self,
        authority_id: int,
        title: str,
        content: str,
        category: str,
        priority: str = "Medium",
        target_audience: str = "All",
        target_department_id: Optional[int] = None,
        target_year: Optional[int] = None,
        expires_in_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new announcement.
        
        Args:
            authority_id: Authority creating the announcement
            title: Announcement title
            content: Announcement content
            category: Category (Hostel, General, Department, Academic, Emergency)
            priority: Low, Medium, High, Critical
            target_audience: All, Day Scholar, Hostellers, Department
            target_department_id: Target department ID (if audience=Department)
            target_year: Target year (1, 2, 3, 4)
            expires_in_days: Days until expiration (None = no expiration)
        
        Returns:
            Created announcement details
        """
        # Verify authority exists
        authority = await self.authority_repo.get(authority_id)
        if not authority:
            raise ValueError("Authority not found")
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        # Validate category
        valid_categories = ["Hostel", "General", "Department", "Academic", "Emergency"]
        if category not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        
        # Validate priority
        valid_priorities = ["Low", "Medium", "High", "Critical"]
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
        
        # Validate target audience
        valid_audiences = ["All", "Day Scholar", "Hostellers", "Department"]
        if target_audience not in valid_audiences:
            raise ValueError(f"Invalid target audience. Must be one of: {', '.join(valid_audiences)}")
        
        # Department-specific validation
        if target_audience == "Department" and not target_department_id:
            raise ValueError("target_department_id required when target_audience is 'Department'")
        
        # Create announcement
        announcement = await self.update_repo.create(
            authority_id=authority_id,
            title=title,
            content=content,
            category=category,
            priority=priority,
            target_audience=target_audience,
            target_department_id=target_department_id,
            target_year=target_year,
            expires_at=expires_at,
            is_active=True
        )
        
        logger.info(
            f"Announcement created by authority {authority_id} ({authority.name}): "
            f"{title} - Priority: {priority}, Audience: {target_audience}"
        )
        
        # TODO: Send push notifications to targeted students
        # This would be implemented when real-time notification system is added
        
        return {
            "id": announcement.id,
            "title": title,
            "content": content,
            "category": category,
            "priority": priority,
            "target_audience": target_audience,
            "created_at": announcement.created_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "is_active": True,
            "message": "Announcement created successfully"
        }
    
    async def get_announcements_for_student(
        self,
        student_roll_no: str,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get announcements visible to a specific student.
        
        Args:
            student_roll_no: Student roll number
            skip: Number to skip (pagination)
            limit: Maximum results
            category: Optional category filter
            priority: Optional priority filter
        
        Returns:
            List of announcements
        """
        # Get student details
        student = await self.student_repo.get_with_department(student_roll_no)
        if not student:
            raise ValueError("Student not found")
        
        # Get visible announcements
        announcements = await self.update_repo.get_visible_to_student(
            stay_type=student.stay_type,
            department_id=student.department_id,
            year=student.year,
            skip=skip,
            limit=limit
        )
        
        # Apply additional filters
        if category:
            announcements = [a for a in announcements if a.category == category]
        
        if priority:
            announcements = [a for a in announcements if a.priority == priority]
        
        # Format response
        result = []
        for announcement in announcements:
            result.append({
                "id": announcement.id,
                "title": announcement.title,
                "content": announcement.content,
                "category": announcement.category,
                "priority": announcement.priority,
                "authority_name": announcement.authority.name if announcement.authority else "Unknown",
                "authority_type": announcement.authority.authority_type if announcement.authority else None,
                "created_at": announcement.created_at.isoformat(),
                "updated_at": announcement.updated_at.isoformat() if announcement.updated_at else None,
                "expires_at": announcement.expires_at.isoformat() if announcement.expires_at else None,
                "view_count": announcement.view_count,
                "target_audience": announcement.target_audience
            })
        
        logger.info(f"Retrieved {len(result)} announcements for student {student_roll_no}")
        return result
    
    async def get_announcement_details(
        self,
        announcement_id: int,
        student_roll_no: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed announcement information.
        
        Args:
            announcement_id: Announcement ID
            student_roll_no: Optional student requesting (for view count)
        
        Returns:
            Detailed announcement info
        """
        announcement = await self.update_repo.get_with_authority(announcement_id)
        if not announcement:
            raise ValueError("Announcement not found")
        
        # Increment view count if student is viewing
        if student_roll_no:
            await self.update_repo.increment_views(announcement_id)
            logger.debug(f"View count incremented for announcement {announcement_id}")
        
        return {
            "id": announcement.id,
            "title": announcement.title,
            "content": announcement.content,
            "category": announcement.category,
            "priority": announcement.priority,
            "authority_name": announcement.authority.name if announcement.authority else "Unknown",
            "authority_type": announcement.authority.authority_type if announcement.authority else None,
            "target_audience": announcement.target_audience,
            "target_department": announcement.target_department.name if announcement.target_department else None,
            "target_year": announcement.target_year,
            "created_at": announcement.created_at.isoformat(),
            "updated_at": announcement.updated_at.isoformat() if announcement.updated_at else None,
            "expires_at": announcement.expires_at.isoformat() if announcement.expires_at else None,
            "view_count": announcement.view_count,
            "is_active": announcement.is_active
        }
    
    async def update_announcement(
        self,
        announcement_id: int,
        authority_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        priority: Optional[str] = None,
        expires_in_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update an existing announcement.
        
        Args:
            announcement_id: Announcement ID
            authority_id: Authority making the update
            title: New title (optional)
            content: New content (optional)
            priority: New priority (optional)
            expires_in_days: New expiration (optional)
        
        Returns:
            Updated announcement details
        """
        announcement = await self.update_repo.get(announcement_id)
        if not announcement:
            raise ValueError("Announcement not found")
        
        # Verify authority has permission
        if announcement.authority_id != authority_id:
            raise PermissionError("Not authorized to update this announcement")
        
        # Update fields
        if title:
            announcement.title = title
        
        if content:
            announcement.content = content
        
        if priority:
            valid_priorities = ["Low", "Medium", "High", "Critical"]
            if priority not in valid_priorities:
                raise ValueError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
            announcement.priority = priority
        
        if expires_in_days is not None:
            if expires_in_days > 0:
                announcement.expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            else:
                announcement.expires_at = None
        
        announcement.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        logger.info(f"Announcement {announcement_id} updated by authority {authority_id}")
        
        return {
            "id": announcement.id,
            "title": announcement.title,
            "content": announcement.content,
            "priority": announcement.priority,
            "updated_at": announcement.updated_at.isoformat(),
            "expires_at": announcement.expires_at.isoformat() if announcement.expires_at else None,
            "message": "Announcement updated successfully"
        }
    
    async def toggle_announcement_status(
        self,
        announcement_id: int,
        authority_id: int
    ) -> Dict[str, Any]:
        """
        Toggle announcement active status (activate/deactivate).
        
        Args:
            announcement_id: Announcement ID
            authority_id: Authority making the change
        
        Returns:
            Updated status
        """
        announcement = await self.update_repo.get(announcement_id)
        if not announcement:
            raise ValueError("Announcement not found")
        
        # Verify authority has permission
        if announcement.authority_id != authority_id:
            raise PermissionError("Not authorized to modify this announcement")
        
        # Toggle status
        announcement = await self.update_repo.toggle_active(announcement_id)
        
        status_text = "activated" if announcement.is_active else "deactivated"
        logger.info(f"Announcement {announcement_id} {status_text} by authority {authority_id}")
        
        return {
            "id": announcement.id,
            "is_active": announcement.is_active,
            "message": f"Announcement {status_text} successfully"
        }
    
    async def delete_announcement(
        self,
        announcement_id: int,
        authority_id: int
    ) -> Dict[str, Any]:
        """
        Delete an announcement (soft delete by deactivating).
        
        Args:
            announcement_id: Announcement ID
            authority_id: Authority making the deletion
        
        Returns:
            Deletion confirmation
        """
        announcement = await self.update_repo.get(announcement_id)
        if not announcement:
            raise ValueError("Announcement not found")
        
        # Verify authority has permission
        if announcement.authority_id != authority_id:
            raise PermissionError("Not authorized to delete this announcement")
        
        # Soft delete by deactivating
        announcement.is_active = False
        announcement.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        logger.info(f"Announcement {announcement_id} deleted (deactivated) by authority {authority_id}")
        
        return {
            "id": announcement_id,
            "message": "Announcement deleted successfully"
        }
    
    async def get_announcements_by_authority(
        self,
        authority_id: int,
        skip: int = 0,
        limit: int = 50,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all announcements created by a specific authority.
        
        Args:
            authority_id: Authority ID
            skip: Number to skip
            limit: Maximum results
            include_inactive: Include deactivated announcements
        
        Returns:
            List of announcements
        """
        announcements = await self.update_repo.get_by_authority(
            authority_id=authority_id,
            skip=skip,
            limit=limit
        )
        
        # Filter inactive if needed
        if not include_inactive:
            announcements = [a for a in announcements if a.is_active]
        
        result = []
        for announcement in announcements:
            result.append({
                "id": announcement.id,
                "title": announcement.title,
                "content": announcement.content[:200] + "..." if len(announcement.content) > 200 else announcement.content,
                "category": announcement.category,
                "priority": announcement.priority,
                "target_audience": announcement.target_audience,
                "view_count": announcement.view_count,
                "is_active": announcement.is_active,
                "created_at": announcement.created_at.isoformat(),
                "expires_at": announcement.expires_at.isoformat() if announcement.expires_at else None
            })
        
        return result
    
    async def get_announcement_statistics(
        self,
        authority_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get announcement statistics.
        
        Args:
            authority_id: Optional authority ID to filter by
        
        Returns:
            Statistics dictionary
        """
        if authority_id:
            announcements = await self.update_repo.get_by_authority(authority_id)
        else:
            stats = await self.update_repo.get_stats()
            return stats
        
        total = len(announcements)
        active = sum(1 for a in announcements if a.is_active)
        expired = sum(1 for a in announcements if a.expires_at and a.expires_at < datetime.now(timezone.utc))
        
        # Category breakdown
        categories = {}
        for announcement in announcements:
            categories[announcement.category] = categories.get(announcement.category, 0) + 1
        
        # Priority breakdown
        priorities = {}
        for announcement in announcements:
            priorities[announcement.priority] = priorities.get(announcement.priority, 0) + 1
        
        return {
            "total_announcements": total,
            "active": active,
            "inactive": total - active,
            "expired": expired,
            "categories": categories,
            "priorities": priorities
        }
    
    async def expire_old_announcements(self) -> int:
        """
        Expire announcements that have passed their expiration date.
        This should be run as a scheduled job.
        
        Returns:
            Number of announcements expired
        """
        count = await self.update_repo.expire_old_announcements()
        
        if count > 0:
            logger.info(f"Expired {count} old announcements")
        
        return count
    
    async def get_high_priority_announcements(
        self,
        student_roll_no: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get high-priority announcements for a student (for dashboard).
        
        Args:
            student_roll_no: Student roll number
            limit: Maximum results
        
        Returns:
            List of high-priority announcements
        """
        student = await self.student_repo.get_with_department(student_roll_no)
        if not student:
            raise ValueError("Student not found")
        
        # Get high priority announcements
        announcements = await self.update_repo.get_high_priority()
        
        # Filter by visibility rules
        visible_announcements = []
        for announcement in announcements:
            # Check target audience
            if announcement.target_audience == "All":
                visible_announcements.append(announcement)
            elif announcement.target_audience == "Day Scholar" and student.stay_type == "Day Scholar":
                visible_announcements.append(announcement)
            elif announcement.target_audience == "Hostellers" and student.stay_type == "Hosteller":
                visible_announcements.append(announcement)
            elif announcement.target_audience == "Department" and announcement.target_department_id == student.department_id:
                visible_announcements.append(announcement)
            
            if len(visible_announcements) >= limit:
                break
        
        # Format response
        result = []
        for announcement in visible_announcements[:limit]:
            result.append({
                "id": announcement.id,
                "title": announcement.title,
                "content": announcement.content[:150] + "..." if len(announcement.content) > 150 else announcement.content,
                "priority": announcement.priority,
                "category": announcement.category,
                "created_at": announcement.created_at.isoformat()
            })
        
        return result


__all__ = ["AuthorityUpdateService"]
