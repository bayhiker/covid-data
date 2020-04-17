from http import HTTPStatus

from flask import current_app, request
from flask_babel import gettext as _
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_raw_jwt,
    jwt_refresh_token_required,
    jwt_required,
)
from youquiz.jwt_store import (
    enable_access_token,
    enable_refresh_token,
    disable_access_token,
    disable_refresh_token_jti,
)
from flask_restful import Resource, fields, inputs, marshal_with, reqparse

from youquiz import api_v1, jwt, audit
from youquiz.models import (
    AlreadyExistsError,
    Role,
    User,
    Comment,
    VoteType,
    Vote,
    delete_record,
    persist_record,
    confirm_user,
    send_confirmation_token,
    send_email_change_token,
    send_password_reset_token,
)
from youquiz.api import (
    EndPoint,
    YouQuizResource,
    get_ep_v1,
    caller_is,
    get_error_result,
    get_message_result,
    youquiz_db_fields,
    parse_pagination_args,
)
from youquiz.api.version_1 import (
    role_schema,
    roles_schema,
    user_schema,
    users_schema,
    quizzes_schema,
    problems_schema,
    comments_schema,
    votes_schema,
)


class RoleResource(YouQuizResource):
    """Only GET is supported, no need to update or delete role via REST at
    this moment
    """

    @jwt_required
    def get(self, role_uuid):
        audit(f"Attempted to access role {role_uuid} via API")
        role = self.check_item(role_uuid)
        if role is None:
            return get_error_result(
                _("Failed to get role with uuid {}").format(role_uuid),
                status_code=HTTPStatus.BAD_REQUEST,
            )
        return role_schema.dump(role)


class RoleListResource(YouQuizResource):
    """Only GET is supported, no need to add a role, or
    update/delete multiple role via REST at this moment
    """

    @jwt_required
    def get(self):
        audit("Attempted to access role list via API")
        kwargs = parse_pagination_args("name_contains")
        name_contains = kwargs.pop("name_contains", None)
        filters = kwargs.setdefault("filters", [])
        if name_contains is not None:
            filters.append(Role.name.contains(name_contains))
        pagination = Role.list(**kwargs)
        return roles_schema.dump(pagination.items) if pagination is not None else []


class UserResource(YouQuizResource):
    """New users are created with POST /users defined in UserListResource,
    POST method for UserResource is undefined unless we support sub-user later on
    """

    @jwt_required
    @caller_is.admin_or_user()
    def get(self, user_uuid):
        audit(f"Attempted to access user {user_uuid}")
        user = self.check_item(user_uuid)
        return user_schema.dump(user)

    @jwt_required
    @caller_is.admin_or_user()
    def put(self, user_uuid):
        """Update user with uuid. 
        
        Args:
            uuid ([int]): User uuid
        
        Returns:
            [json]: Updated user
        """
        user = self.check_item(user_uuid)

        parser = reqparse.RequestParser()
        parser.add_argument("first_name", store_missing=False)
        parser.add_argument("last_name", store_missing=False)
        parser.add_argument("new_email", store_missing=False)
        parser.add_argument("password", store_missing=False)
        parser.add_argument("new_password", store_missing=False)
        args = parser.parse_args()
        if len(args) == 0:
            return get_error_result(
                _("No user attributes specified for update"),
                status_code=HTTPStatus.BAD_REQUEST,
            )
        msg = ""
        if "first_name" in args:
            user.first_name = args["first_name"]
            msg += "First name updated to {}; ".format(user.first_name)

        if "last_name" in args:
            user.last_name = args["last_name"]
            msg += "Last name updated to {}; ".format(user.last_name)

        password = ""
        if "new_email" in args or "new_password" in args:
            if not "password" in args:
                return get_error_result(
                    _("Must provide current password in order to change password"),
                    status_code=HTTPStatus.BAD_REQUEST,
                )
            password = args["password"]
            if not user.verify_password(password):
                return get_error_result(
                    _("Password mismatch"), status_code=HTTPStatus.BAD_REQUEST
                )

        if "new_email" in args:
            new_email = args["new_email"]
            if not send_email_change_token(user, new_email):
                return get_error_result(
                    _("Failed to update email"), status_code=HTTPStatus.BAD_REQUEST
                )
            audit(f"Sent update email request to email address {new_email}")
            msg += _(
                "Changing email to {}, a confirmation email was sent to {},"
                " please check your email to confirmation email change; "
            ).format(new_email, new_email)

        if "new_password" in args:
            new_password = args["new_password"]
            # TODO check password strength here
            user.password = new_password
            msg += _(" Password successfully reset for {}; ").format(user.email)

        persist_record(user)
        audit(msg)
        return get_message_result(msg)

    @jwt_required
    @caller_is.admin_or_user()
    def delete(self, user_uuid):
        audit(f"Attempted to delete user {user_uuid}")
        user = self.check_item(user_uuid)
        if user.is_admin():
            return get_error_result(
                _("Admin users cannot be deleted"), status_code=HTTPStatus.UNAUTHORIZED
            )
        delete_record(user)
        return get_message_result(_("User {} was removed"), user.email)


class UserConfirmationResource(YouQuizResource):
    # User email confirmation is in separate URI user/<email>/confirmation,
    # because confirm doesn't require an access_token

    def post(self, email):
        """Regenerate confirmation token for account associated with email,
        and send confirmation token to that email.
        
        Returns:
            [json]: Always a successful status msg as long as web server is
            accessible. No error will be reported about email address for
            security reasons
        """
        audit(f"Regenerating email confirmation token for user {email}")
        user = User.load(email=email)
        if user is not None:
            send_confirmation_token(user)
        return get_message_result(
            _(
                "If user {} exists, then an email"
                " would have been sent to that email address, please check your"
                " email to confirm your account."
            ),
            email,
        )

    # Confirm user email with confirmation token
    def put(self, email):
        """Confirm user with confirmation_token

        Args:
            email (str): email associated with a user account
        """
        # TODO Not sure if this is going to be used in a mobile app because
        # users will be asked to check email and click confirm. Not extensively
        # tested yet
        audit(f"Confirming email token for user {email}")
        parser = reqparse.RequestParser()
        parser.add_argument("confirmation_token", store_missing=False)
        args = parser.parse_args()
        if "confirmation_token" not in args:
            return get_error_result(
                _("confirmation_token cannot be empty"),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        confirmation_token = args["confirmation_token"]

        if confirm_user(email, confirmation_token):
            return get_message_result(_("User {} successfully confirmed"), email)
        else:
            return get_error_result(
                _(
                    "Failed to confirm user. Either user {} does not exist,"
                    " or token provided is not correct"
                ),
                email,
                status_code=HTTPStatus.BAD_REQUEST,
            )


class UserPasswordResource(YouQuizResource):
    # User password reset is in a separate URI /user/<email>/password,
    # because reset doesn't require an access_token or user uuid.
    # User password update, however, resides inside URI /user/<uuid>.
    # Confirm_password_reset is done via WEB only for now, after user clicks
    # link in email
    def post(self, email):
        """Regenerate confirmation token for account associated with email,
        and send confirmation token to that email.
        
        Returns:
            [json]: Always a successful status msg as long as web server is
            accessible. No error will be reported about email address for
            security reasons
        """
        audit(f"Resetting password for {email} via API")
        user = User.load(email=email)
        if user is not None:
            send_password_reset_token(user)
        return get_message_result(
            _(
                "If user {} exists, then an email"
                " would have been sent to that email address, please check your"
                " email to confirm your account."
            ),
            email,
        )


#
# Shows list of users with GET, and add a new user with POST
# PUT for bulk updating a list of users is not supported
# DELETE for deleting multiple users is not supported
#
class UserListResource(YouQuizResource):
    @jwt_required
    @caller_is.admin
    def get(self):
        """Get a list of users, with paging and optional filters applied
        
        Returns:
            [json]: List of users, with paging and optional filters applied
        """
        audit("Retrieving user list")

        kwargs = parse_pagination_args("email_contains", confirmed=inputs.boolean)

        order_by = kwargs.pop("order_by", None)
        if order_by is not None and order_by.lower() == "email":
            kwargs["order_by"] = User.email

        email_contains = kwargs.pop("email_contains", None)
        confirmed = kwargs.pop("confirmed", None)
        filters = kwargs.setdefault("filters", {})
        if email_contains is not None:
            filters.append(User.email.contains(email_contains))
        filter_bys = kwargs.setdefault("filter_bys", {})
        if confirmed is not None:
            filter_bys[User.confirmed] = confirmed

        pagination = User.list(**kwargs)
        return users_schema.dump(pagination.items) if pagination is not None else []

    def post(self):
        """Add a new user
        
        Returns:
            user: List of users, with paging and optional filters applied
        """
        parser = reqparse.RequestParser()
        parser.add_argument(
            "first_name", required=True, help=_("First name cannot be empty")
        )
        parser.add_argument(
            "last_name", required=True, help=_("Last name cannot be empty")
        )
        parser.add_argument("email", required=True, help=_("Email cannot be empty"))
        parser.add_argument(
            "password", required=True, help=_("Password cannot be empty")
        )
        parser.add_argument(
            "send_confirmation_token",
            type=inputs.boolean,
            required=False,
            store_missing=False,
        )
        args = parser.parse_args()
        try:
            user = User.add(**args)
            audit(f"Created user via REST API: {user.email}")
            return user_schema.dump(user)
        except AlreadyExistsError as ex:
            return get_error_result(
                _("Email {} already exists"),
                args["email"],
                status_code=HTTPStatus.BAD_REQUEST,
            )


class TokenResource(YouQuizResource):
    def post(self):
        """ Create a new access token and a new refresh token
        
        Returns:
            [json]: New access_token and refresh_token if user creds are valid,
            HTTPStatus.UNAUTHORIZED and an error_msg otherwise. This method only
            returns one status code with the same error message to avoid tipping
            off attackers with more info
        """
        parser = reqparse.RequestParser()
        parser.add_argument("email", required=True, help=_("Email cannot be empty"))
        parser.add_argument(
            "password", required=True, help=_("Password cannot be empty")
        )
        args = parser.parse_args()

        access_token = ""
        refresh_token = ""

        email = args["email"]
        user = User.load(email=email, password=args["password"])
        audit("User {email} logging in via REST")
        if user is None:
            audit("Failed login attemp on user {}.".format(email))
            return get_error_result(
                _("User {} doesn't exist, or password mismatch"),
                email,
                status_code=HTTPStatus.UNAUTHORIZED,
            )
        elif not user.confirmed:
            audit("Failed login attemp on user {}.".format(email))
            return get_error_result(
                _(
                    "User {} has not been confirmed, "
                    " please check your email and confirm your account"
                ),
                email,
                status_code=HTTPStatus.UNAUTHORIZED,
            )
        else:
            audit("User {} logged in.".format(user.email))
            access_token = create_access_token(identity=email)
            enable_access_token(access_token)
            refresh_token = create_refresh_token(identity=email)
            enable_refresh_token(refresh_token)
        return {"access_token": access_token, "refresh_token": refresh_token}

    @jwt_refresh_token_required
    def delete(self):
        """ Deletes current access token and refresh_token. Because refresh_token has
        higher priority and can be used to generate any new access_token, therefore
        refresh_token is passed in via Authorization HTTP header and goes through JWT
        authorization chain, while previous access_token is passed in as a variable
        "access_token" so it can be disabled after a new access_token is successfully
        generated
        
        Returns:
            [json]: boolean result access_token_revoked and refresh_token_revoked
        """
        audit(f"{get_jwt_identity()} logging out")
        parser = reqparse.RequestParser()
        parser.add_argument(
            "access_token", required=True, help=_("access_token cannot be empty")
        )
        args = parser.parse_args()
        access_token = args["access_token"]
        disable_access_token(access_token)

        refresh_token_jti = get_raw_jwt()["jti"]
        disable_refresh_token_jti(refresh_token_jti)

        return {"access_token_revoked": True, "refresh_token_revoked": True}

    @jwt_refresh_token_required
    def put(self):
        """ Refreshes the current access_token. Current token is passed in via
        parameters so it can be revoked after new access_token is generated
        
        Returns:
            [json]: Updated access_token
        """
        audit("Refershing access_token via REST")
        parser = reqparse.RequestParser()
        parser.add_argument(
            "access_token", required=True, help=_("access_token cannot be empty")
        )
        args = parser.parse_args()
        old_access_token = args["access_token"]

        current_user = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user)
        enable_access_token(new_access_token)
        disable_access_token(old_access_token)

        return {"access_token": new_access_token}


class UserCommentListResource(YouQuizResource):
    """Only requirement at this moment is to get list of comments made by a user."""

    @jwt_required
    def get(self, user_uuid):
        user = self.check_item(user_uuid)
        kwargs = parse_pagination_args("content_contains")
        order_by = kwargs.pop("order_by", None)
        if order_by is not None and order_by.lower() == "content":
            kwargs["order_by"] = Comment.content
        content_contains = kwargs.pop("content_contains", None)
        filters = kwargs.setdefault("filters", [])
        if content_contains is not None:
            filters.append(Comment.content.contains(content_contains))
        filter_bys = kwargs.setdefault("filter_bys", {})
        filter_bys["user_uuid"] = user_uuid

        pagination = Comment.list(**kwargs)
        return comments_schema.dump(pagination.items) if pagination is not None else []


class UserVoteListResource(YouQuizResource):
    """Only requirement at this moment is to get list of votes by a user"""

    @jwt_required
    def get(self, user_uuid):
        user = self.check_item(user_uuid)
        kwargs = parse_pagination_args("vote_type")
        order_by = kwargs.pop("order_by", None)
        if order_by is not None and order_by.lower() == "vote_type":
            kwargs["order_by"] = Vote.vote_type
        vote_type = VoteType.from_name(kwargs.pop("vote_type", None))
        filters = kwargs.setdefault("filters", [])
        if vote_type is not None:
            filters.append(Vote.vote_type == vote_type)
        filter_bys = kwargs.setdefault("filter_bys", {})
        filter_bys["user_uuid"] = user_uuid

        pagination = Vote.list(**kwargs)
        return votes_schema.dump(pagination.items) if pagination is not None else []

