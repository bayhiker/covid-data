from flask import current_app, url_for
from sqlalchemy.dialects.postgresql import UUID
from flask_babel import gettext as _
from itsdangerous import BadSignature, SignatureExpired
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import CovidModel, AlreadyExistsError, list_items


class AdminUnit(CovidModel):
    __abstract__ = True
    # 0 country, 1 state/province, 2 us_county, 3 us_city, 4 ...
    name = db.Column(db.String(64))
    # Code for California is CA, for United States is US
    code = db.Column(db.String(64))
    level = db.Column(db.Integer)
    fips = db.Column(db.String(64))
    flag = db.Column(db.String())  # URL
    area = db.Column(db.Integer)
    population = db.Column(db.Integer)
    lon = db.Column(db.float())  # centroid longitude
    lat = db.Column(db.float())  # centroid lattitude
