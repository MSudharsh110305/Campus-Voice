"""
Authority service for routing and escalation logic.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Authority, Complaint
from src.repositories.authority_repo import AuthorityRepository
from src.repositories.complaint_repo import ComplaintRepository
from src.config.constants import ESCALATION_RULES, ESCALATION_THRESHOLD_DAYS

logger = logging.getLogger(__name__)


class AuthorityService:
    """Service for authority operations"""
    
    async def route_complaint(
        self,
        db: AsyncSession,
        category_id: int,
        department_id: Optional[int],
        is_against_authority: bool,
        student_gender: Optional[str] = None,
        complaint_about_authority_type: Optional[str] = None
    ) -> Optional[Authority]:
        """
        Route complaint to appropriate authority based on category and context.

        Args:
            db: Database session
            category_id: Complaint category ID
            department_id: Student's department ID
            is_against_authority: If complaint is against an authority
            student_gender: Student's gender (for hostel routing)
            complaint_about_authority_type: Type of authority the complaint is about

        Returns:
            Authority or None
        """
        authority_repo = AuthorityRepository(db)

        # Get category name
        from src.database.models import ComplaintCategory
        category = await db.get(ComplaintCategory, category_id)
        if not category:
            logger.error(f"Category {category_id} not found for routing")
            return None

        category_name = category.name
        logger.info(f"Routing complaint: Category={category_name}, Department={department_id}, Against Authority={is_against_authority}")

        # Route based on category
        authority = None

        if category_name == "Men's Hostel":
            authority = await authority_repo.get_default_for_category("Men's Hostel", None)
            logger.debug(f"Men's Hostel category: Routed to {authority.name if authority else 'None'}")

        elif category_name == "Women's Hostel":
            authority = await authority_repo.get_default_for_category("Women's Hostel", None)
            logger.debug(f"Women's Hostel category: Routed to {authority.name if authority else 'None'}")

        elif category_name == "Department":
            authority = await authority_repo.get_default_for_category("Department", department_id)
            logger.debug(f"Department category: Routed to {authority.name if authority else 'None'}")

        elif category_name == "Disciplinary Committee":
            authority = await authority_repo.get_default_for_category("Disciplinary Committee", None)
            logger.debug(f"Disciplinary category: Routed to {authority.name if authority else 'None'}")

        else:  # General or other categories
            authority = await authority_repo.get_default_for_category("General", None)
            logger.debug(f"General/Other category: Routed to {authority.name if authority else 'None'}")

        # If no authority found, try fallback routing
        if not authority:
            logger.warning(f"No authority found for category {category_name}, attempting fallback")
            authority = await self._fallback_routing(db, category_name, department_id)

        # If complaint is against an authority, escalate to the next higher authority.
        # is_against_authority=True means the LLM confirmed the complaint is directed at
        # the authority who would normally handle it (HOD for dept, Warden for hostel).
        # Staff/faculty complaints → is_against_authority=False → goes to HOD as normal.
        # HOD complaints → is_against_authority=True → skip HOD, escalate to Admin Officer / Admin.
        if is_against_authority and authority:
            logger.info(f"Complaint is against authority ({authority.name}), escalating")

            # Check if complaint is about a warden — bypass all wardens of same level
            if complaint_about_authority_type and "Warden" in complaint_about_authority_type:
                escalated_authority = await authority_repo.get_higher_authority_excluding_same_level(
                    authority.authority_level,
                    authority.authority_type
                )
                if escalated_authority:
                    logger.info(f"Bypassing same-level wardens, escalated to {escalated_authority.name}")
                    return escalated_authority

            # Standard escalation (works for both Hostel and Department)
            escalated_authority = await self.get_escalated_authority(db, authority.id)

            if escalated_authority:
                logger.info(f"Escalated to {escalated_authority.name}")
                return escalated_authority
            else:
                logger.warning(f"No escalation path found for {authority.name}, keeping original assignment")

        if authority:
            logger.info(f"Complaint routed to: {authority.name} (ID: {authority.id})")
        else:
            logger.error(f"Failed to route complaint - no authority available for category {category_name}")

        return authority
    
    async def _fallback_routing(
        self,
        db: AsyncSession,
        category_name: str,
        department_id: Optional[int]
    ) -> Optional[Authority]:
        """
        Fallback routing when no specific authority found.

        Args:
            db: Database session
            category_name: Category name
            department_id: Department ID

        Returns:
            Fallback authority or None
        """
        authority_repo = AuthorityRepository(db)

        # Try to get any active authority of appropriate type
        fallback_types = {
            "Men's Hostel": ["Men's Hostel Warden", "Men's Hostel Deputy Warden", "Senior Deputy Warden", "Admin"],
            "Women's Hostel": ["Women's Hostel Warden", "Women's Hostel Deputy Warden", "Senior Deputy Warden", "Admin"],
            "Department": ["HOD", "Admin"],
            "General": ["Admin Officer", "Admin"],
            "Disciplinary Committee": ["Disciplinary Committee", "Admin"]
        }

        types_to_try = fallback_types.get(category_name, ["Admin"])

        for authority_type in types_to_try:
            authorities = await authority_repo.get_by_type(authority_type)
            if authorities:
                logger.info(f"Fallback routing: Found {authority_type}")
                return authorities[0]

        logger.error("Fallback routing failed - no authorities available")
        return None
    
    async def get_escalation_authority(
        self,
        db: AsyncSession,
        category_id: int,
        current_level: int,
        department_id: Optional[int] = None
    ) -> Optional[Authority]:
        """
        Find a higher-level authority for escalation based on category and level.

        Used by the escalation endpoint to find the next authority in the chain.

        Args:
            db: Database session
            category_id: Complaint category ID
            current_level: Current authority's level
            department_id: Optional department ID for scoping

        Returns:
            Higher authority or None
        """
        authority_repo = AuthorityRepository(db)

        # Get current authority type from level
        from src.config.constants import LEVEL_TO_AUTHORITY
        current_type = LEVEL_TO_AUTHORITY.get(current_level)

        if current_type:
            next_type = ESCALATION_RULES.get(current_type)
            if next_type and next_type != current_type:
                authorities = await authority_repo.get_by_type(next_type)
                if authorities:
                    # Prefer same department if applicable
                    if department_id:
                        dept_authorities = [
                            a for a in authorities if a.department_id == department_id
                        ]
                        if dept_authorities:
                            return dept_authorities[0]
                    return authorities[0]

        # Fallback: find any authority with a higher level
        higher_authority = await authority_repo.get_higher_authority(
            current_level=current_level,
            department_id=department_id
        )
        return higher_authority

    async def get_escalated_authority(
        self,
        db: AsyncSession,
        current_authority_id: int
    ) -> Optional[Authority]:
        """
        Get higher authority for escalation based on hierarchy.
        
        Args:
            db: Database session
            current_authority_id: Current authority ID
        
        Returns:
            Higher authority or None
        """
        authority_repo = AuthorityRepository(db)
        
        current_authority = await authority_repo.get(current_authority_id)
        if not current_authority:
            logger.error(f"Current authority {current_authority_id} not found for escalation")
            return None
        
        logger.info(f"Escalating from: {current_authority.name} ({current_authority.authority_type}, Level {current_authority.authority_level})")
        
        # Get next authority type from escalation rules
        next_type = ESCALATION_RULES.get(current_authority.authority_type)
        
        if not next_type:
            logger.warning(f"No escalation rule defined for {current_authority.authority_type}")
            # Try to escalate by level instead
            return await self._escalate_by_level(db, current_authority)
        
        # Get authorities of next type
        authorities = await authority_repo.get_by_type(next_type)
        
        if not authorities:
            logger.warning(f"No authorities found of type {next_type}")
            return None
        
        # If current authority has department, try to match department first
        if current_authority.department_id:
            dept_authorities = [a for a in authorities if a.department_id == current_authority.department_id]
            if dept_authorities:
                logger.info(f"Escalated to same department: {dept_authorities[0].name}")
                return dept_authorities[0]
        
        # Otherwise, return first available authority of next type
        logger.info(f"Escalated to: {authorities[0].name}")
        return authorities[0]
    
    async def _escalate_by_level(
        self,
        db: AsyncSession,
        current_authority: Authority
    ) -> Optional[Authority]:
        """
        Escalate by authority level when no type-based rule exists.
        
        Args:
            db: Database session
            current_authority: Current authority
        
        Returns:
            Higher level authority or None
        """
        authority_repo = AuthorityRepository(db)
        
        # Get authority with higher level
        higher_authority = await authority_repo.get_higher_authority(
            current_level=current_authority.authority_level,
            department_id=current_authority.department_id
        )
        
        if higher_authority:
            logger.info(f"Level-based escalation: {current_authority.name} (L{current_authority.authority_level}) → {higher_authority.name} (L{higher_authority.authority_level})")
        else:
            logger.warning(f"No higher authority found above level {current_authority.authority_level}")
        
        return higher_authority
    
    async def check_and_escalate_pending_complaints(
        self,
        db: AsyncSession,
        threshold_days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for complaints pending escalation and escalate them.
        This should be run as a scheduled job (e.g., daily cron).
        
        Args:
            db: Database session
            threshold_days: Days threshold for escalation (default from constants)
        
        Returns:
            List of escalated complaints
        """
        if threshold_days is None:
            threshold_days = ESCALATION_THRESHOLD_DAYS
        
        complaint_repo = ComplaintRepository(db)
        
        # Get complaints pending escalation
        pending_complaints = await complaint_repo.get_pending_for_escalation(threshold_days)
        
        escalated = []
        
        for complaint in pending_complaints:
            try:
                # Get higher authority
                if not complaint.assigned_authority_id:
                    logger.warning(f"Complaint {complaint.id} has no assigned authority, skipping escalation")
                    continue
                
                higher_authority = await self.get_escalated_authority(
                    db, complaint.assigned_authority_id
                )
                
                if not higher_authority:
                    logger.warning(f"No escalation path for complaint {complaint.id}")
                    continue
                
                # Update complaint
                old_authority_id = complaint.assigned_authority_id
                complaint.assigned_authority_id = higher_authority.id
                complaint.status = "Escalated"
                complaint.escalated_at = datetime.now(timezone.utc)
                
                await db.commit()
                
                # Create notification for new authority
                from src.services.notification_service import notification_service
                await notification_service.create_notification(
                    db,
                    recipient_type="Authority",
                    recipient_id=str(higher_authority.id),
                    complaint_id=complaint.id,
                    notification_type="complaint_escalated",
                    message=f"Complaint escalated to you: {complaint.rephrased_text[:100]}..."
                )
                
                # Notify student
                await notification_service.create_notification(
                    db,
                    recipient_type="Student",
                    recipient_id=complaint.student_roll_no,
                    complaint_id=complaint.id,
                    notification_type="status_update",
                    message=f"Your complaint has been escalated to {higher_authority.name}"
                )
                
                escalated.append({
                    "complaint_id": str(complaint.id),
                    "from_authority_id": old_authority_id,
                    "to_authority_id": higher_authority.id,
                    "to_authority_name": higher_authority.name,
                    "days_pending": threshold_days
                })
                
                logger.info(f"Complaint {complaint.id} escalated to {higher_authority.name}")
                
            except Exception as e:
                logger.error(f"Error escalating complaint {complaint.id}: {e}")
                continue
        
        logger.info(f"Escalated {len(escalated)} complaints")
        return escalated
    
    async def get_authority_workload(
        self,
        db: AsyncSession,
        authority_id: int
    ) -> Dict[str, Any]:
        """
        Get workload statistics for an authority.
        
        Args:
            db: Database session
            authority_id: Authority ID
        
        Returns:
            Workload statistics
        """
        complaint_repo = ComplaintRepository(db)
        
        # Get all complaints assigned to authority
        complaints = await complaint_repo.get_assigned_to_authority(authority_id)
        
        total = len(complaints)
        pending = sum(1 for c in complaints if c.status in ["Raised", "In Progress"])
        resolved = sum(1 for c in complaints if c.status == "Resolved")
        escalated = sum(1 for c in complaints if c.status == "Escalated")
        
        # Get high priority count
        high_priority = sum(1 for c in complaints if c.priority in ["High", "Critical"])
        
        return {
            "authority_id": authority_id,
            "total_assigned": total,
            "pending": pending,
            "resolved": resolved,
            "escalated": escalated,
            "high_priority": high_priority,
            "resolution_rate": (resolved / total * 100) if total > 0 else 0
        }
    
    async def get_all_authorities_workload(
        self,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Get workload statistics for all authorities.
        
        Args:
            db: Database session
        
        Returns:
            List of workload statistics
        """
        authority_repo = AuthorityRepository(db)
        
        authorities = await authority_repo.get_active_authorities()
        
        workloads = []
        for authority in authorities:
            workload = await self.get_authority_workload(db, authority.id)
            workload["authority_name"] = authority.name
            workload["authority_type"] = authority.authority_type
            workloads.append(workload)
        
        # Sort by pending complaints (most loaded first)
        workloads.sort(key=lambda x: x["pending"], reverse=True)
        
        return workloads
    
    async def suggest_reassignment(
        self,
        db: AsyncSession,
        complaint_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Suggest reassignment of complaint to a different authority.
        
        Args:
            db: Database session
            complaint_id: Complaint UUID
            reason: Reason for reassignment
        
        Returns:
            Suggested authority
        """
        from uuid import UUID
        complaint_repo = ComplaintRepository(db)
        
        complaint = await complaint_repo.get(UUID(complaint_id))
        if not complaint:
            raise ValueError("Complaint not found")
        
        if not complaint.assigned_authority_id:
            raise ValueError("Complaint has no assigned authority")
        
        # Get higher authority as suggestion
        suggested_authority = await self.get_escalated_authority(
            db, complaint.assigned_authority_id
        )
        
        if not suggested_authority:
            raise ValueError("No alternative authority available")
        
        return {
            "complaint_id": complaint_id,
            "current_authority_id": complaint.assigned_authority_id,
            "suggested_authority_id": suggested_authority.id,
            "suggested_authority_name": suggested_authority.name,
            "reason": reason
        }
    
    async def manually_escalate_complaint(
        self,
        db: AsyncSession,
        complaint_id: str,
        escalated_by_authority_id: int,
        reason: str
    ) -> Dict[str, Any]:
        """
        Manually escalate a complaint (by authority request).
        
        Args:
            db: Database session
            complaint_id: Complaint UUID
            escalated_by_authority_id: Authority requesting escalation
            reason: Escalation reason
        
        Returns:
            Escalation result
        """
        from uuid import UUID
        complaint_repo = ComplaintRepository(db)
        
        complaint = await complaint_repo.get(UUID(complaint_id))
        if not complaint:
            raise ValueError("Complaint not found")
        
        # Verify authority has permission
        if complaint.assigned_authority_id != escalated_by_authority_id:
            raise PermissionError("Only assigned authority can escalate")
        
        # Get higher authority
        higher_authority = await self.get_escalated_authority(
            db, escalated_by_authority_id
        )
        
        if not higher_authority:
            raise ValueError("No escalation path available")
        
        # Update complaint
        old_authority_id = complaint.assigned_authority_id
        complaint.assigned_authority_id = higher_authority.id
        complaint.status = "Escalated"
        complaint.escalated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        # Create status update record
        from src.database.models import StatusUpdate
        status_update = StatusUpdate(
            complaint_id=UUID(complaint_id),
            old_status=complaint.status,
            new_status="Escalated",
            updated_by=escalated_by_authority_id,
            reason=f"Manual escalation: {reason}"
        )
        db.add(status_update)
        await db.commit()
        
        # Notify new authority
        from src.services.notification_service import notification_service
        await notification_service.create_notification(
            db,
            recipient_type="Authority",
            recipient_id=str(higher_authority.id),
            complaint_id=UUID(complaint_id),
            notification_type="complaint_escalated",
            message=f"Complaint manually escalated to you: {reason}"
        )
        
        # Notify student
        await notification_service.create_notification(
            db,
            recipient_type="Student",
            recipient_id=complaint.student_roll_no,
            complaint_id=UUID(complaint_id),
            notification_type="status_update",
            message=f"Your complaint has been escalated to {higher_authority.name}"
        )
        
        logger.info(
            f"Complaint {complaint_id} manually escalated from "
            f"authority {old_authority_id} to {higher_authority.id}"
        )
        
        return {
            "complaint_id": complaint_id,
            "from_authority_id": old_authority_id,
            "to_authority_id": higher_authority.id,
            "to_authority_name": higher_authority.name,
            "reason": reason,
            "escalated_at": complaint.escalated_at.isoformat()
        }


# Create global instance
authority_service = AuthorityService()

__all__ = ["AuthorityService", "authority_service"]
