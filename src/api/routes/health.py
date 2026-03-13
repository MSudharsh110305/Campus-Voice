"""
Health check endpoints.

No authentication required - these are public endpoints for monitoring.

✅ FIXED: Import from src.database.connection
✅ FIXED: Use timezone-aware datetime
✅ ADDED: Database pool statistics
✅ ADDED: Service dependencies check
✅ ADDED: Metrics endpoint for monitoring
✅ NO AUTHENTICATION: All endpoints are public
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, select

from src.database.connection import get_db, engine  # ✅ FIXED IMPORT
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description="Check if API is running (no auth required)"
)
async def health_check():
    """
    ✅ Basic health check endpoint.
    
    No authentication required - used by monitoring systems.
    """
    return {
        "status": "healthy",
        "service": "CampusVoice API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()  # ✅ FIXED: timezone-aware
    }


@router.get(
    "/health/detailed",
    summary="Detailed health check",
    description="Detailed health check with database connectivity (no auth required)"
)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    ✅ Detailed health check including database connectivity.
    
    No authentication required - used by monitoring systems.
    """
    health_status = {
        "status": "healthy",
        "service": "CampusVoice API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),  # ✅ FIXED
        "checks": {}
    }
    
    # Database connectivity check
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }
    
    # Database version check
    try:
        version_result = await db.execute(text("SELECT version()"))
        db_version = version_result.scalar()
        health_status["checks"]["database_version"] = {
            "status": "healthy",
            "version": db_version
        }
    except Exception as e:
        logger.warning(f"Could not get database version: {e}")
        health_status["checks"]["database_version"] = {
            "status": "unknown",
            "message": str(e)
        }
    
    # Environment check
    health_status["checks"]["environment"] = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }
    
    # Database pool statistics
    try:
        pool = engine.pool
        health_status["checks"]["connection_pool"] = {
            "status": "healthy",
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
    except Exception as e:
        logger.warning(f"Could not get pool stats: {e}")
        health_status["checks"]["connection_pool"] = {
            "status": "unknown",
            "message": str(e)
        }
    
    return health_status


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Check if service is ready to accept traffic (no auth required)"
)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    ✅ Readiness check for Kubernetes/Docker health probes.
    
    No authentication required - used by orchestration systems.
    
    Returns HTTP 200 if ready, 503 if not ready.
    """
    try:
        # Check database connectivity
        await db.execute(text("SELECT 1"))
        
        # Check if critical tables exist
        from src.database.models import Student, Complaint, Authority
        
        # Simple query to verify tables are accessible
        student_count = await db.execute(select(func.count()).select_from(Student))
        student_count.scalar()
        
        complaint_count = await db.execute(select(func.count()).select_from(Complaint))
        complaint_count.scalar()
        
        authority_count = await db.execute(select(func.count()).select_from(Authority))
        authority_count.scalar()
        
        return {
            "ready": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Service is ready to accept traffic"
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "ready": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Service is not ready"
            }
        )


@router.get(
    "/health/live",
    summary="Liveness check",
    description="Check if service is alive (no auth required)"
)
async def liveness_check():
    """
    ✅ Liveness check for Kubernetes/Docker health probes.
    
    No authentication required - used by orchestration systems.
    
    Simple check that the application is running.
    Always returns 200 unless the application is completely down.
    """
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Service is alive"
    }


@router.get(
    "/health/startup",
    summary="Startup check",
    description="Check if service has completed startup (no auth required)"
)
async def startup_check(db: AsyncSession = Depends(get_db)):
    """
    ✅ NEW: Startup check for Kubernetes startup probes.
    
    No authentication required - used by orchestration systems.
    
    Verifies that the application has fully started and initialized.
    """
    try:
        # Verify database connection
        await db.execute(text("SELECT 1"))
        
        # Verify critical tables exist and are queryable
        from src.database.models import Student
        
        result = await db.execute(select(func.count()).select_from(Student))
        result.scalar()
        
        return {
            "started": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Service has completed startup"
        }
        
    except Exception as e:
        logger.error(f"Startup check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "started": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Service startup incomplete"
            }
        )


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Metrics endpoint for monitoring (no auth required)"
)
async def metrics(db: AsyncSession = Depends(get_db)):
    """
    ✅ NEW: Metrics endpoint for Prometheus/monitoring systems.
    
    No authentication required - used by monitoring systems.
    
    Returns metrics in JSON format (can be adapted for Prometheus format).
    """
    try:
        from src.database.models import Student, Complaint, Authority
        
        # Get counts
        student_count_query = select(func.count()).select_from(Student)
        student_result = await db.execute(student_count_query)
        total_students = student_result.scalar() or 0
        
        complaint_count_query = select(func.count()).select_from(Complaint)
        complaint_result = await db.execute(complaint_count_query)
        total_complaints = complaint_result.scalar() or 0
        
        authority_count_query = select(func.count()).select_from(Authority)
        authority_result = await db.execute(authority_count_query)
        total_authorities = authority_result.scalar() or 0
        
        # Complaint status breakdown
        pending_query = select(func.count()).where(Complaint.status == "Raised")
        pending_result = await db.execute(pending_query)
        pending_complaints = pending_result.scalar() or 0
        
        in_progress_query = select(func.count()).where(Complaint.status == "In Progress")
        in_progress_result = await db.execute(in_progress_query)
        in_progress_complaints = in_progress_result.scalar() or 0
        
        resolved_query = select(func.count()).where(Complaint.status == "Resolved")
        resolved_result = await db.execute(resolved_query)
        resolved_complaints = resolved_result.scalar() or 0
        
        # Database pool stats
        pool = engine.pool
        pool_stats = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "total_students": total_students,
                "total_complaints": total_complaints,
                "total_authorities": total_authorities,
                "pending_complaints": pending_complaints,
                "in_progress_complaints": in_progress_complaints,
                "resolved_complaints": resolved_complaints
            },
            "database_pool": pool_stats
        }
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Metrics collection failed"
            }
        )


@router.get(
    "/ping",
    summary="Simple ping",
    description="Minimal endpoint for uptime checks (no auth required)"
)
async def ping():
    """
    ✅ NEW: Minimal ping endpoint.
    
    No authentication required - used for simple uptime checks.
    
    Fastest possible response with no dependencies.
    """
    return {"pong": True}


__all__ = ["router"]
