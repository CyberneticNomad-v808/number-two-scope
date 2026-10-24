# Future Work - SpiderFoot Improvements

## Database Abstraction Layer (DAL)

### Problem
Currently, SpiderFoot uses raw SQL queries with conditional logic for different database backends (SQLite vs PostgreSQL). This leads to:
- Duplicate query logic with different placeholders (`?` for SQLite, `%s` for PostgreSQL)
- Duplicate table schemas with different data types (TEXT/REAL for SQLite, VARCHAR/DOUBLE PRECISION for PostgreSQL)
- Manual input validation scattered across multiple files
- Security concerns with SQL injection if not carefully managed
- Maintenance burden when adding new database backends

### Proposed Solution
Implement a Database Abstraction Layer using an ORM (Object-Relational Mapper) like SQLAlchemy:

#### Benefits
1. **Single Source of Truth**: Define schemas once, auto-generate SQL for all backends
2. **Security**: Built-in parameterization and SQL injection protection
3. **Input Validation**: Centralized validation at the ORM layer
4. **Maintainability**: Easier to add new database backends (MySQL, MariaDB, etc.)
5. **Type Safety**: Python type hints map to database column types
6. **Migrations**: Automated schema migrations using Alembic

#### Implementation Approach
```python
# Example using SQLAlchemy
from sqlalchemy import Column, String, Float, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Workspace(Base):
    __tablename__ = 'tbl_workspaces'

    workspace_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_time = Column(Float)
    modified_time = Column(Float)
    targets = Column(Text)
    scans = Column(Text)
    metadata = Column(Text)
    correlations = Column(Text)
    workflows = Column(Text)
```

#### Migration Strategy
1. Create ORM models parallel to existing code
2. Add feature flag to toggle between raw SQL and ORM
3. Gradually migrate endpoints
4. Extensive testing with both SQLite and PostgreSQL
5. Remove raw SQL once ORM is proven stable

### Files Affected
- `spiderfoot/db.py` - Main database class
- `spiderfoot/workspace.py` - Workspace management
- All modules using `SpiderFootDb`

### Estimated Effort
- Design & Planning: 1-2 weeks
- Implementation: 4-6 weeks
- Testing: 2-3 weeks
- Documentation: 1 week

### Priority
**Medium-High**: This would significantly improve code quality, security, and maintainability.

---

## Other Future Improvements

### 1. Enhanced Security
- Implement prepared statements universally
- Add SQL query logging for audit trails
- Row-level security for multi-tenant deployments

### 2. Performance Optimizations
- Connection pooling (partially implemented for PostgreSQL)
- Query result caching
- Batch operations for bulk inserts

### 3. Database Feature Parity
- Ensure all features work identically on SQLite and PostgreSQL
- Add comprehensive integration tests for both backends
- Document database-specific limitations

---

*Last Updated: 2025-10-02*
*Created during PostgreSQL compatibility fixes*
