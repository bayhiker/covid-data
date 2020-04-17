from pprint import pformat
from app import db
from app.models import CovidModel


def persist_record(record):
    if record is None:
        raise ValueError("None record encounted while persisting records")
    db.session.add(record)
    db.session.commit()
    return record


def delete_record(record):
    if record is None:
        return None
    db.session.delete(record)
    db.session.commit()
    return record


def list_items(model, **kwargs):
    """Gets a page of items list from the database. 
    
    Returns:
        [flask_sqlalchemy.Pagination]: Pagination object for listing recrods
    """
    page_size = 10 if "page_size" not in kwargs else int(kwargs["page_size"])
    page_no = 1 if "page_no" not in kwargs else int(kwargs["page_no"])
    order_by = model.created
    if "order_by" in kwargs:
        order_by = kwargs["order_by"]
    if "desc" in kwargs and kwargs["desc"]:
        order_by = order_by.desc()
    query = kwargs.pop("query", None)
    if query is None:
        query = model.query
    query = query.order_by(order_by)
    if "filter_bys" in kwargs:
        # Value of kwargs['filter_bys'] is another **kwargs as defined in
        # sqlalchemy.orm.query.Query.filter_by(**kwargs)
        query = query.filter_by(**(kwargs["filter_bys"]))
    if "filters" in kwargs:
        # Value of kwargs['filters'] is another *args as defined in
        # sqlalchemy.orm.query.Query.filter(*args)
        query = query.filter(*(kwargs["filters"]))
    return query.paginate(page_no, page_size, error_out=False)


def drain_pagination(pagination):
    items = []
    if pagination is not None:
        items += pagination.items
        pagination = pagination.next() if pagination.has_next else None
    return items
