from re import search
from enum import Enum
import logging
from http import HTTPStatus
from flask_restful import abort, Resource

# imports used by eval() in check_item() method
from app.models import AdminUnit

REST_RESULT_ERROR = "error"
REST_RESULT_MSG = "msg"

#
# Blueprint names of all API versions defined here
#
V1 = "api_v1"

#
# All endpoints defined here
#
class EndPoint(str, Enum):
    DATA = "data"


# Extending youquiz_db_fields
# requires python 3.5 or later
covid_db_fields = ("uuid", "created", "uri_self")


class CovidResource(Resource):
    def check_item(self, item_uuid, model=None):
        if model is None:
            # CAUTIOUS!!! eval should be used with care. Here we know input
            # is ONLY out current class name.
            model = eval(search("[A-Z][^A-Z]*", self.__class__.__name__).group(0))
        item = model.load(uuid=item_uuid)
        if item is None:
            logging.error(
                f"Item of type {model.__name__} with uuid {item_uuid} not found."
            )
            abort(HTTPStatus.BAD_REQUEST)
        return item


from app.api.utils import (
    get_ep_v1,
    get_url_v1,
    get_message_result,
    get_error_result,
    get_jwt_identity,
    get_jwt_user,
    parse_pagination_args,
)
