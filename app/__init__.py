import os

from flask import Flask, current_app, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_wtf import CSRFProtect
from flask_compress import Compress
from flask_babel import Babel
from flask_jwt_extended import JWTManager
from flask_restful import Api
from redis import StrictRedis
from config import config as Config
from .utils import setup_logger


class YouQuizError(Exception):
    """Base class for exceptions/errors in youquiz module"""

    pass


basedir = os.path.abspath(os.path.dirname(__file__))

db = SQLAlchemy()
ma = Marshmallow()
csrf = CSRFProtect()
compress = Compress()
jwt = JWTManager()
babel = Babel()
api_v1 = Api(decorators=[csrf.exempt])


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(current_app.config["LANGUAGES"].keys())


@jwt.token_in_blacklist_loader
def check_if_token_is_revoked(decrypted_token):
    jwt_revoked_store = current_app.config["JWT_REVOKED_STORE"]
    jti = decrypted_token["jti"]
    entry = jwt_revoked_store.get(jti)
    if entry is None:
        return True
    return entry == "true"


def create_app(config):
    app = Flask(__name__)
    config_name = config

    if not isinstance(config, str):
        config_name = os.getenv("FLASK_CONFIG", "default")

    print(f"Runing in {config_name} mode")

    app.config.from_object(Config[config_name])
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # not using sqlalchemy event system, hence disabling it

    Config[config_name].init_app(app)

    setup_logger(app)
    app.logger.info(f"Loading application with config_name {config_name}")

    # Set up extensions
    db.init_app(app)
    ma.init_app(app)
    csrf.init_app(app)
    compress.init_app(app)
    jwt.init_app(app)
    babel.init_app(app)

    # Setup JWT_REVOKED_STORE
    app.config["JWT_REVOKED_STORE"] = StrictRedis(
        host=app.config["REDIS_HOSTNAME"],
        port=app.config["REDIS_PORT"],
        db=0,
        decode_responses=True,
    )

    from app.api.version_1 import v1 as api_v1_blueprint

    app.register_blueprint(api_v1_blueprint, url_prefix="/api/v1")

    return app


from app.utils import (
    audit,
    now,
    setup_logger,
)
