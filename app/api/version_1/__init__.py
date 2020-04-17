from flask import Blueprint, current_app, request
from flask_restful import Api

from youquiz import api_v1, audit
from youquiz.api import EndPoint, V1

from youquiz.api.version_1.schemas import (
    role_schema,
    roles_schema,
    user_schema,
    users_schema,
    tag_schema,
    tags_schema,
    comment_schema,
    comments_schema,
    vote_schema,
    votes_schema,
    alternative_schema,
    alternatives_schema,
    answer_schema,
    answers_schema,
    question_schema,
    questions_schema,
    media_schema,
    medias_schema,
    quiz_schema,
    quizzes_schema,
    problem_schema,
    problems_schema,
)

from youquiz.api.version_1.quiz_resources import (
    TagResource,
    TagListResource,
    TagProblemListResource,
    MediaListResource,
    MediaResource,
    ProblemCommentListResource,
    ProblemCommentResource,
    ProblemListResource,
    ProblemQuestionAlternativeListResource,
    ProblemQuestionAlternativeResource,
    ProblemQuestionResource,
    ProblemQuestionListResource,
    ProblemQuestionKeyResource,
    ProblemResource,
    ProblemVoteListResource,
    ProblemVoteResource,
    ProblemTagResource,
    ProblemTagListResource,
    QuizListResource,
    QuizProblemListResource,
    QuizQuestionAnswerResource,
    QuizProblemAnswerListResource,
    QuizAnswerListResource,
    QuizProblemResource,
    QuizResource,
)
from youquiz.api.version_1.user_resources import (
    RoleListResource,
    RoleResource,
    TokenResource,
    UserConfirmationResource,
    UserListResource,
    UserPasswordResource,
    UserResource,
    UserCommentListResource,
    UserVoteListResource,
)

# Declare the blueprint and setup Api
v1 = Blueprint(V1, __name__)
api_v1.init_app(v1)

# Set the default route
@v1.route("/")
def show():
    # TODO Add swagger UI logic here?
    # Return open source licenses for
    #      https://github.com/miguelgrinberg/sqlalchemy-soft-delete
    #      https://github.com/hack4impact/flask-base
    return "This is whiziquiz API version 1"


"""Audit all incoming REST calls"""


@v1.before_request
def audit_rest_call():
    audit(f"{request.method} {request.full_path}", log_headers=True)


api_v1.add_resource(RoleResource, "/roles/<role_uuid>", endpoint=EndPoint.ROLE.value)
api_v1.add_resource(RoleListResource, "/roles", endpoint=EndPoint.ROLE_LIST.value)
api_v1.add_resource(UserResource, "/users/<user_uuid>", endpoint=EndPoint.USER.value)
api_v1.add_resource(
    UserConfirmationResource,
    "/users/<email>/confirmation",
    endpoint=EndPoint.USER_CONFIRMATION.value,
)
api_v1.add_resource(UserListResource, "/users", endpoint=EndPoint.USER_LIST.value)
api_v1.add_resource(
    UserPasswordResource,
    "/users/<email>/password",
    endpoint=EndPoint.USER_PASSWORD.value,
)
api_v1.add_resource(
    UserCommentListResource,
    "/users/<user_uuid>/comments",
    endpoint=EndPoint.USER_COMMENT_LIST.value,
)
api_v1.add_resource(
    UserVoteListResource,
    "/users/<user_uuid>/votes",
    endpoint=EndPoint.USER_VOTE_LIST.value,
)
api_v1.add_resource(TokenResource, "/tokens", endpoint=EndPoint.TOKEN.value)
api_v1.add_resource(QuizResource, "/quizzes/<quiz_uuid>", endpoint=EndPoint.QUIZ.value)
api_v1.add_resource(QuizListResource, "/quizzes", endpoint=EndPoint.QUIZ_LIST.value)
api_v1.add_resource(
    QuizProblemResource,
    "/quizzes/<quiz_uuid>/problems/<problem_uuid>",
    endpoint=EndPoint.QUIZ_PROBLEM.value,
)
api_v1.add_resource(
    QuizProblemListResource,
    "/quizzes/<quiz_uuid>/problems",
    endpoint=EndPoint.QUIZ_PROBLEM_LIST.value,
)
api_v1.add_resource(
    QuizQuestionAnswerResource,
    "/quizzes/<quiz_uuid>/questions/<question_uuid>/answer",
    endpoint=EndPoint.QUIZ_QUESTION_ANSWER.value,
)
api_v1.add_resource(
    QuizProblemAnswerListResource,
    "/quizzes/<quiz_uuid>/problems/<problem_uuid>/answers",
    endpoint=EndPoint.QUIZ_PROBLEM_ANSWER_LIST.value,
)
api_v1.add_resource(
    QuizAnswerListResource,
    "/quizzes/<quiz_uuid>/answers",
    endpoint=EndPoint.QUIZ_ANSWER_LIST.value,
)
api_v1.add_resource(
    ProblemResource, "/problems/<problem_uuid>", endpoint=EndPoint.PROBLEM.value
)
api_v1.add_resource(
    ProblemListResource, "/problems", endpoint=EndPoint.PROBLEM_LIST.value
)
api_v1.add_resource(
    ProblemQuestionResource,
    "/problems/<problem_uuid>/questions/<question_uuid>",
    endpoint=EndPoint.PROBLEM_QUESTION.value,
)
api_v1.add_resource(
    ProblemQuestionListResource,
    "/problems/<problem_uuid>/questions",
    endpoint=EndPoint.PROBLEM_QUESTION_LIST.value,
)
api_v1.add_resource(
    ProblemQuestionAlternativeResource,
    "/problems/<problem_uuid>/questions/<question_uuid>/alternatives/<alternative_uuid>",
    endpoint=EndPoint.PROBLEM_QUESTION_ALTERNATIVE.value,
)
api_v1.add_resource(
    ProblemQuestionAlternativeListResource,
    "/problems/<problem_uuid>/questions/<question_uuid>/alternatives",
    endpoint=EndPoint.PROBLEM_QUESTION_ALTERNATIVE_LIST.value,
)
api_v1.add_resource(
    ProblemQuestionKeyResource,
    "/problems/<problem_uuid>/questions/<question_uuid>/key",
    endpoint=EndPoint.PROBLEM_QUESTION_KEY.value,
)
api_v1.add_resource(
    ProblemCommentResource,
    "/problems/<problem_uuid>/comments/<comment_uuid>",
    endpoint=EndPoint.PROBLEM_COMMENT.value,
)
api_v1.add_resource(
    ProblemCommentListResource,
    "/problems/<problem_uuid>/comments",
    endpoint=EndPoint.PROBLEM_COMMENT_LIST.value,
)
api_v1.add_resource(
    ProblemVoteResource,
    "/problems/<problem_uuid>/votes/<vote_uuid>",
    endpoint=EndPoint.PROBLEM_VOTE.value,
)
api_v1.add_resource(
    ProblemVoteListResource,
    "/problems/<problem_uuid>/votes",
    endpoint=EndPoint.PROBLEM_VOTE_LIST.value,
)
api_v1.add_resource(
    ProblemTagResource,
    "/problems/<problem_uuid>/tags/<tag_uuid>",
    endpoint=EndPoint.PROBLEM_TAG.value,
)
api_v1.add_resource(
    ProblemTagListResource,
    "/problems/<problem_uuid>/tags",
    endpoint=EndPoint.PROBLEM_TAG_LIST.value,
)
api_v1.add_resource(MediaResource, "/media/<media_uuid>", endpoint=EndPoint.MEDIA.value)
api_v1.add_resource(MediaListResource, "/media", endpoint=EndPoint.MEDIA_LIST.value)
api_v1.add_resource(TagResource, "/tags/<tag_uuid>", endpoint=EndPoint.TAG.value)
api_v1.add_resource(TagListResource, "/tags", endpoint=EndPoint.TAG_LIST.value)
api_v1.add_resource(
    TagProblemListResource,
    "/tags/<tag_uuid>/problems",
    endpoint=EndPoint.TAG_PROBLEM_LIST.value,
)
