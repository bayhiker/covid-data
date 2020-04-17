import logging
import os
import sys
import urllib.parse
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

if os.path.exists("config.env"):
    logging.info("Importing environment from config.env file")
    for line in open("config.env"):
        line = line.strip()
        if line.startswith("#"):
            continue
        var = line.split("=", 2)
        if len(var) == 2:
            os.environ[var[0].strip().upper()] = var[1].strip().replace('"', "")


class Config:
    APP_NAME = os.environ.get("APP_NAME", "covid")
    LOGGING_CONF = os.environ.get("LOGGING_CONF", "logging.conf")

    if os.environ.get("SECRET_KEY") and os.environ.get("JWT_SECRET_KEY"):
        SECRET_KEY = os.environ.get("SECRET_KEY")
        JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    else:
        SECRET_KEY = "SECRET_KEY_ENV_VAR_NOT_SET"
        JWT_SECRET_KEY = "JWT_SECRET_KEY_ENV_VAR_NOT_SET"
        print(
            "SECRET_KEY or JWT_SECRET_KEY ENV VAR NOT SET! SHOULD NOT SEE IN PRODUCTION"
        )

    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_ECHO = False

    # JWT config
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30 * 24 * 60)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    ASSETS_DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI_DEV", "sqlite:///" + os.path.join(basedir, "data-dev.sqlite")
    )
    SQLALCHEMY_ECHO = False  # Change to True to show sql statements

    @classmethod
    def init_app(cls, app):
        print(
            "THIS APP IS IN DEBUG MODE. \
                YOU SHOULD NOT SEE THIS IN PRODUCTION."
        )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI_TEST", "sqlite:///" + os.path.join(basedir, "data-test.sqlite")
    )
    SQLALCHEMY_ECHO = False  # Change to True to show sql statements
    WTF_CSRF_ENABLED = False

    @classmethod
    def init_app(cls, app):
        print(
            "THIS APP IS IN TESTING MODE.  \
                YOU SHOULD NOT SEE THIS IN PRODUCTION."
        )


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI", "sqlite:///" + os.path.join(basedir, "data.sqlite")
    )
    SSL_DISABLE = os.environ.get("SSL_DISABLE", "True") == "True"

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        assert os.environ.get("SECRET_KEY"), "SECRET_KEY IS NOT SET!"
        assert os.environ.get("JWT_SECRET_KEY"), "JWT_SECRET_KEY IS NOT SET!"


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
