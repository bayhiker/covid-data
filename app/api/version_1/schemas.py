from marshmallow.fields import Function as MarshMallowFunction
from flask_marshmallow.fields import URLFor
from marshmallow_enum import EnumField

from youquiz import ma
from youquiz.models import (
    Role,
    User,
    Alternative,
    Answer,
    Comment,
    Media,
    Tag,
    Problem,
    Question,
    Quiz,
    Vote,
    VoteType,
)
from youquiz.api import EndPoint, get_ep_v1, youquiz_db_fields


class YouQuizSchema(ma.ModelSchema):
    uuid = ma.UUID(required=True)
    created = ma.DateTime()


class RoleSchema(YouQuizSchema):
    class Meta:
        model = Role
        fields = (*youquiz_db_fields, "name", "default", "permissions")

    uri_self = URLFor(get_ep_v1(EndPoint.ROLE), role_uuid="<uuid>")


role_schema = RoleSchema()
roles_schema = RoleSchema(many=True)


class UserSchema(YouQuizSchema):
    class Meta:
        model = User
        fields = (
            *youquiz_db_fields,
            "first_name",
            "last_name",
            "email",
            "confirmed",
            "role_uuid",
            "uri_role",
        )

    uri_role = URLFor(get_ep_v1(EndPoint.ROLE), role_uuid="<role_uuid>")
    uri_self = URLFor(get_ep_v1(EndPoint.USER), user_uuid="<uuid>")


user_schema = UserSchema()
users_schema = UserSchema(many=True)


class TagSchema(YouQuizSchema):
    class Meta:
        model = Tag
        fields = (*youquiz_db_fields, "name", "uri_problems")

    uri_self = URLFor(get_ep_v1(EndPoint.TAG), tag_uuid="<uuid>")
    uri_problems = URLFor(get_ep_v1(EndPoint.TAG_PROBLEM_LIST), tag_uuid="<uuid>")


tag_schema = TagSchema()
tags_schema = TagSchema(many=True)


class CommentSchema(YouQuizSchema):
    class Meta:
        model = Comment
        fields = (*youquiz_db_fields, "content", "uri_user")

    uri_self = URLFor(
        get_ep_v1(EndPoint.PROBLEM_COMMENT),
        problem_uuid="<problem_uuid>",
        comment_uuid="<uuid>",
    )
    uri_user = URLFor(get_ep_v1(EndPoint.USER), user_uuid="<user_uuid>")


comment_schema = CommentSchema()
comments_schema = CommentSchema(many=True)


class VoteSchema(YouQuizSchema):
    vote_type = EnumField(VoteType)

    class Meta:
        model = Vote
        fields = (
            *youquiz_db_fields,
            "problem_uuid",
            "user_uuid",
            "vote_type",
            "uri_user",
        )

    uri_self = URLFor(
        get_ep_v1(EndPoint.PROBLEM_VOTE),
        problem_uuid="<problem_uuid>",
        vote_uuid="<uuid>",
    )
    uri_user = URLFor(get_ep_v1(EndPoint.USER), user_uuid="<user_uuid>")


vote_schema = VoteSchema()
votes_schema = VoteSchema(many=True)


class MediaSchema(YouQuizSchema):
    class Meta:
        model = Media
        fields = (*youquiz_db_fields, "path", "description")

    uri_self = URLFor(get_ep_v1(EndPoint.MEDIA), media_uuid="<uuid>")


media_schema = MediaSchema
# Plural of media should be media, but to be consistent with every other list schema
medias_schema = MediaSchema(many=True)


class QuizSchema(YouQuizSchema):
    class Meta:
        model = Quiz
        fields = (
            *youquiz_db_fields,
            "description",
            "problem_repeats",
            "user_uuid",
            "uri_user",
            "uri_problems",
        )

    problem_repeats = MarshMallowFunction(lambda obj: obj.get_problem_repeats())
    uri_self = URLFor(get_ep_v1(EndPoint.QUIZ), quiz_uuid="<uuid>")
    uri_user = URLFor(get_ep_v1(EndPoint.USER), user_uuid="<user_uuid>")
    uri_problems = URLFor(get_ep_v1(EndPoint.QUIZ_PROBLEM_LIST), quiz_uuid="<uuid>")


quiz_schema = QuizSchema()
quizzes_schema = QuizSchema(many=True)


class AlternativeSchema(YouQuizSchema):
    class Meta:
        model = Alternative
        fields = (*youquiz_db_fields, "index", "content", "question_uuid")
        uri_self = "-"  # Not possible, missing problem_uuid


alternative_schema = AlternativeSchema()
alternatives_schema = AlternativeSchema(many=True)


class AnswerSchema(YouQuizSchema):
    class Meta:
        model = Answer
        fields = (
            *youquiz_db_fields,
            "solution",
            "quiz_uuid",
            "question_uuid",
            "uri_quiz",
        )

    uri_self = "-"  # Not possible, missing problem_uuid
    uri_quiz = URLFor(get_ep_v1(EndPoint.QUIZ), quiz_uuid="<quiz_uuid>")


answer_schema = AnswerSchema()
answers_schema = AnswerSchema(many=True)


class QuestionSchema(YouQuizSchema):
    class Meta:
        model = Question
        fields = (
            *youquiz_db_fields,
            "stem",
            "problem_uuid",
            "alternatives",
            "uri_key",
            "uri_answers",
            "uri_problem",
        )

    alternatives = ma.Nested(AlternativeSchema(many=True))
    uri_self = URLFor(
        get_ep_v1(EndPoint.PROBLEM_QUESTION),
        problem_uuid="<problem_uuid>",
        question_uuid="<uuid>",
    )
    uri_problem = URLFor(get_ep_v1(EndPoint.PROBLEM), problem_uuid="<problem_uuid>")
    uri_key = URLFor(
        get_ep_v1(EndPoint.PROBLEM_QUESTION_KEY),
        problem_uuid="<problem_uuid>",
        question_uuid="<uuid>",
    )


question_schema = QuestionSchema()
questions_schema = QuestionSchema(many=True)


class ProblemSchema(YouQuizSchema):
    class Meta:
        model = Problem
        fields = (
            *youquiz_db_fields,
            "statement",
            "author",
            "author_uuid",
            "questions",
            "tags",
            "yaml",
            "sample_problem",
            "vote_count",
            "comment_count",
            "uri_author",
            "uri_questions",
            "uri_comments",
            "uri_votes",
        )

    author = ma.Nested(UserSchema)
    questions = ma.Nested(QuestionSchema(many=True))
    tags = ma.Nested(TagSchema(many=True))
    yaml = MarshMallowFunction(lambda obj: obj.to_yaml())
    sample_problem = MarshMallowFunction(lambda obj: obj.get_sample_problem())
    vote_count = MarshMallowFunction(lambda obj: obj.count_votes())
    comment_count = MarshMallowFunction(lambda obj: obj.count_comments())
    uri_self = URLFor(get_ep_v1(EndPoint.PROBLEM), problem_uuid="<uuid>")
    uri_author = URLFor(get_ep_v1(EndPoint.USER), user_uuid="<author_uuid>")
    uri_questions = URLFor(
        get_ep_v1(EndPoint.PROBLEM_QUESTION_LIST), problem_uuid="<uuid>"
    )
    uri_comments = URLFor(
        get_ep_v1(EndPoint.PROBLEM_COMMENT_LIST), problem_uuid="<uuid>"
    )
    uri_votes = URLFor(get_ep_v1(EndPoint.PROBLEM_VOTE_LIST), problem_uuid="<uuid>")


problem_schema = ProblemSchema()
problems_schema = ProblemSchema(many=True)
