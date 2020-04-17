"""
These imports enable us to make all defined models members of the models
module (as opposed to just their python files)
"""

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text
from app import db, now


class AlreadyExistsError(CovidError):
    pass


class CovidModel(db.Model):  # noqa
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(
        UUID(as_uuid=True),
        index=True,
        unique=True,
        nullable=False,
        server_default=text("uuid_generate_v4()"),
        # If needed, connect to postgresql server and run pgsqlcommand:
        # CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
    )
    created = db.Column(db.DateTime, server_default=text("now()"))
    # No deleted field for soft delete, prefer audits over softdelete, for example,
    # https://jameshalsall.co.uk/posts/why-soft-deletes-are-evil-and-what-to-do-instead


from app.models.utils import (
    persist_record,
    delete_record,
    list_items,
    drain_pagination,
)


from app.models.admin_unit import AdminUnit
