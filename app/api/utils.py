from http import HTTPStatus

from flask import current_app
from flask_jwt_extended import get_jwt_identity
from flask_restful import fields, url_for, reqparse, inputs

from youquiz import audit, now
from youquiz.api import REST_RESULT_ERROR, REST_RESULT_MSG, V1
from youquiz.models import User


def __get_endpoint(api_version_blueprint_name, endpoint):
    return f"{api_version_blueprint_name}.{endpoint}"


def get_ep_v1(endpoint):
    """Get an endpoint for API version 1
    
    Args:
        endpoint ([str]): Name of the end point, for example, 'user'
    
    Returns:
        [str]: Full endpoint name with version blueprint name, for example, 'api_v1.user'
    """
    return __get_endpoint(V1, endpoint)


def get_url_v1(endpoint, **values):
    return url_for(get_ep_v1(endpoint), **values)


def get_error_result(error_msg, *args, status_code=HTTPStatus.BAD_REQUEST):
    """Composes error message for REST results
    
    Args:
        error_msg (str): Error message, with optional format() placeholders
        status_code (int, optional): HTTP status code.
            Defaults to 500 Internal Server Error.
    
    Returns:
        dict: A dict with REST_RESULT_ERROR keyword and formatted error_msg as value
    """
    formatted_msg = error_msg.format(*args)
    current_app.logger.error(formatted_msg)
    return ({REST_RESULT_ERROR: formatted_msg, "timestamp": str(now())}, status_code)


def get_message_result(msg, *args, status_code=200):
    """Composes error message for REST results
    
    Args:
        msg (str): Message, with optional format() placeholders
        status_code (int, optional): HTTP status code. Defaults to 200 OK
    
    Returns:
        dict: A dict with 'msg' keyword and formatted msg as value
    """
    return {REST_RESULT_MSG: msg.format(*args)}, status_code


def get_jwt_user():
    """Retrieves a User corresponding to current JWT token
    
    Returns:
        [User]: The User associated with current JWT token
    """
    jwt_email = get_jwt_identity()
    # Keep this audit message, it will be important context information if
    # later audits records some actions taken by this user, but don't want
    # to retrieve jwt_email again
    current_app.logger.info(
        f"User email corresponding to current JWT token is {jwt_email}"
    )
    return User.load(email=jwt_email) if jwt_email is not None else None


def parse_pagination_args(*args, **kwargs):
    """Creates a reqparser, with default pagination arguments page_no,
    page_size, order_by, and desc. Args items are added as str arguments,
    while each k,v item in kwargs is added as argument k of type v
    
    Returns:
        [dict]: Parsed arguments
    """
    parser = reqparse.RequestParser()
    parser.add_argument("page_size", type=int, store_missing=False)
    parser.add_argument("page_no", type=int, store_missing=False)
    parser.add_argument("order_by", store_missing=False)
    parser.add_argument("desc", type=inputs.boolean, store_missing=False)
    for arg in args:
        parser.add_argument(arg, store_missing=False)
    for key, value in kwargs.items():
        parser.add_argument(key, type=value, store_missing=False)
    return parser.parse_args()

