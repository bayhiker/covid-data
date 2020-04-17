from datetime import datetime, timezone
from flask import current_app, request, url_for


def now():
    # Because naive datetime objects are treated by
    # many datetime methods as local times, it is
    # preferred to use aware datetimes to represent times in UTC.
    # Therefore, now(tz) instead of utcnow()
    return datetime.now(timezone.utc)


def audit(audit_msg, log_headers=False):
    """Log audit messages
    
    Args:
        audit_msg (str): audit message, if None, log current request header info
        args (List): args used to format audit msg, if any
    """
    audit_prefix = "[Audit] "
    current_app.logger.info(audit_prefix + audit_msg)
    if log_headers:
        from pprint import saferepr

        current_app.logger.info(audit_prefix + saferepr(request.headers))


def setup_logger(app):
    import logging
    from logging.config import fileConfig

    fileConfig(app.config["LOGGING_CONF"])
    root_logger = logging.getLogger("root")
    app.logger = root_logger
