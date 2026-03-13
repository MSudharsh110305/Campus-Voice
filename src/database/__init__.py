"""
Database package initialization.
Exports all models and connection utilities.
"""

from .connection import (
    engine,
    AsyncSessionLocal,
    get_db,
    create_all_tables,
    drop_all_tables,
    init_db,
    seed_initial_data,
    health_check,
    get_db_info,
    get_pool_status,
    test_connection,
    close_db,
    execute_in_transaction,
    execute_with_retry,
    reset_database,
)

from .models import (
    Base,
    Department,
    ComplaintCategory,
    Student,
    Authority,
    Complaint,
    AuthorityUpdate,
    Vote,
    StatusUpdate,
    AuthorityRoutingRule,
    ImageVerificationLog,
    SpamBlacklist,
    LLMProcessingLog,
    Notification,
    Comment,
    AdminAuditLog,
)

__all__ = [
    # Engine & Session
    "engine",
    "AsyncSessionLocal",
    "get_db",
    
    # Initialization
    "create_all_tables",
    "drop_all_tables",
    "init_db",
    "seed_initial_data",
    
    # Health & Monitoring
    "health_check",
    "get_db_info",
    "get_pool_status",
    "test_connection",
    
    # Cleanup
    "close_db",
    
    # Transaction Helpers
    "execute_in_transaction",
    "execute_with_retry",
    
    # Testing
    "reset_database",
    
    # Models
    "Base",
    "Department",
    "ComplaintCategory",
    "Student",
    "Authority",
    "Complaint",
    "AuthorityUpdate",
    "Vote",
    "StatusUpdate",
    "AuthorityRoutingRule",
    "ImageVerificationLog",
    "SpamBlacklist",
    "LLMProcessingLog",
    "Notification",
    "Comment",
    "AdminAuditLog",
]
