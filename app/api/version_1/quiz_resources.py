from http import HTTPStatus

from flask import current_app, request, send_file
from flask_babel import gettext as _
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, reqparse, inputs, abort

from youquiz import audit, db
from youquiz.models import (
    Quiz,
    Problem,
    Tag,
    Comment,
    Vote,
    VoteType,
    Question,
    Alternative,
    Answer,
    delete_record,
    persist_record,
)
from youquiz.api import (
    YouQuizResource,
    caller_is,
    get_error_result,
    get_jwt_user,
    get_message_result,
    parse_pagination_args,
)
from youquiz.api.caller_is import get_jwt_user
from youquiz.api.version_1 import (
    quiz_schema,
    quizzes_schema,
    problem_schema,
    problems_schema,
    tag_schema,
    tags_schema,
    comment_schema,
    comments_schema,
    vote_schema,
    votes_schema,
    question_schema,
    questions_schema,
    alternative_schema,
    alternatives_schema,
    answer_schema,
    answers_schema,
    media_schema,
    medias_schema,
    answer_schema,
    answers_schema,
)


class QuizResource(YouQuizResource):
    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def get(self, quiz_uuid):
        audit(f"Accessing quiz {quiz_uuid} via API")
        parser = reqparse.RequestParser()
        parser.add_argument("format", store_missing=False)
        args = parser.parse_args()
        format = "json"
        if "format" in args:
            format = args["format"]
        quiz = self.check_item(quiz_uuid)
        if format == "pdf":
            f = quiz.generate_pdf()
            return send_file(f, as_attachment=True, attachment_filename="quiz.pdf")
        else:
            return quiz_schema.dump(quiz)

    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def put(self, quiz_uuid):
        audit(f"Updating quiz {quiz_uuid} via API", log_headers=True)
        quiz = self.check_item(quiz_uuid)

        parser = reqparse.RequestParser()
        parser.add_argument("description", store_missing=False)
        args = parser.parse_args()
        if len(args) == 0:
            return get_error_result(_("No attributes to update"))
        # Only description should be updated, updating list of problems
        # would invalidate previous answers to current quiz.
        # Always create new quizzes if problems set needs to be updated.
        if "description" in args:
            quiz.description = args["description"]
        persist_record(quiz)
        return quiz_schema.dump(quiz)

    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def delete(self, quiz_uuid):
        audit(f"Deleting quiz {quiz_uuid}")
        quiz = self.check_item(quiz_uuid)
        delete_record(quiz)
        return get_message_result(_("Quiz {} was removed"), quiz_uuid)


class QuizListResource(YouQuizResource):
    @jwt_required
    def get(self):
        jwt_user = get_jwt_user()
        audit(f"{jwt_user.email} accessing quiz list via API")
        kwargs = parse_pagination_args("description_contains", "user_uuid")

        description_contains = kwargs.pop("description_contains", None)
        user_uuid = kwargs.pop("user_uuid", None)
        filter_bys = kwargs.setdefault("filter_bys", {})
        if user_uuid is not None:
            if jwt_user.is_admin() or user_uuid == str(jwt_user.uuid):
                filter_bys["user_uuid"] = user_uuid
            else:
                return get_error_result(
                    _("Only admin user can list quizzes owned by other users"),
                    status_code=HTTPStatus.UNAUTHORIZED,
                )
        else:
            if not jwt_user.is_admin():
                filter_bys["user_uuid"] = str(jwt_user.uuid)
        filters = kwargs.setdefault("filters", [])
        if description_contains is not None:
            filters.append(Quiz.description.contains(description_contains))

        pagination = Quiz.list(**kwargs)
        return quizzes_schema.dump(pagination.items) if pagination is not None else []

    @jwt_required
    def post(self):
        email = get_jwt_identity()
        audit(f"User {email} adding a new quiz")

        parser = reqparse.RequestParser()
        parser.add_argument("description", store_missing=False)
        parser.add_argument("problem", action="append", store_missing=False)
        args = parser.parse_args()
        description = args["description"] if "description" in args else ""
        problems = args["problem"] if "problem" in args else []
        quiz = Quiz.add(user_email=email, description=description, problems=problems)
        if quiz is None:
            return get_error_result(_("Error adding quiz"))
        return quiz_schema.dump(quiz)


class QuizProblemResource(YouQuizResource):
    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def get(self, quiz_uuid, problem_uuid):
        quiz = self.check_item(quiz_uuid)
        problem = quiz.get_problem(problem_uuid)
        return problem_schema.dump(problem) if problem is not None else []

    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def delete(self, quiz_uuid, problem_uuid):
        quiz = self.check_item(quiz_uuid)
        problem = quiz.remove_problem(problem_uuid)
        return problem_schema.dump(problem) if problem is not None else []


class QuizProblemListResource(YouQuizResource):
    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def get(self, quiz_uuid):
        quiz = self.check_item(quiz_uuid)
        kwargs = parse_pagination_args("statement_contains")
        statement_contains = kwargs.pop("statement_contains", None)
        problems = quiz.get_problems()
        if statement_contains is not None:
            problems = [
                x for x in quiz.get_problems() if statement_contains in x.statement
            ]
        return problems_schema.dump(problems)

    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def post(self, quiz_uuid):
        quiz = self.check_item(quiz_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("problem_uuid", required=True)
        parser.add_argument("repeat", type=int, store_missing=False)
        kwargs = parser.parse_args()
        problem_uuid = kwargs.pop("problem_uuid", None)
        repeat = kwargs.pop("repeat", 1)
        problem = quiz.add_problem(problem_uuid, repeat=repeat)
        return problem_schema.dump(problem)


class QuizQuestionAnswerResource(YouQuizResource):
    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def get(self, quiz_uuid, question_uuid):
        quiz = self.check_item(quiz_uuid)
        answer = quiz.get_answer(question_uuid)
        return answer_schema.dump(answer) if answer is not None else []

    @jwt_required
    @caller_is.quiz_owner()
    def post(self, quiz_uuid, question_uuid):
        quiz = self.check_item(quiz_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("solution", required=True)
        kwargs = parser.parse_args()
        solution = kwargs.pop("solution", None)
        answer = quiz.add_answer(question_uuid, solution)
        return answer_schema.dump(answer) if answer is not None else []

    @jwt_required
    @caller_is.quiz_owner()
    def delete(self, quiz_uuid, question_uuid):
        quiz = self.check_item(quiz_uuid)
        answer = quiz.delete_answer(question_uuid)
        return answer_schema.dump(answer) if answer is not None else []


class _QuizAnswerListResource(YouQuizResource):
    def _get_answers(self, quiz_uuid, problem_uuid=None):
        quiz = self.check_item(quiz_uuid)
        kwargs = parse_pagination_args("solution_contains")
        problem = Problem.load(problem_uuid) if problem_uuid is not None else None
        if problem is not None:
            filters = kwargs.setdefault("filters", [])
            filters.append(problem in quiz.problems)
        solution_contains = kwargs.pop("solution_contains", None)
        if solution_contains is not None:
            filters = kwargs.setdefault("filters", [])
            filters.append(Answer.solution.contains(solution_contains))
        pagination = quiz.get_answers(**kwargs)
        return answers_schema.dump(pagination.items) if pagination is not None else []


class QuizProblemAnswerListResource(_QuizAnswerListResource):
    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def get(self, quiz_uuid, problem_uuid):
        # Get all answers for a problem in a quiz
        return self._get_answers(quiz_uuid, problem_uuid)


class QuizAnswerListResource(_QuizAnswerListResource):
    @jwt_required
    @caller_is.admin_or_quiz_owner()
    def get(self, quiz_uuid):
        # Get all answers in a quiz
        return self._get_answers(quiz_uuid)


class ProblemResource(YouQuizResource):
    @jwt_required
    @caller_is.admin_or_problem_author()
    def get(self, problem_uuid):
        audit(f"Retrieving problem with uuid {problem_uuid}")
        return problem_schema.dump(self.check_item(problem_uuid))

    @jwt_required
    @caller_is.admin_or_problem_author()
    def put(self, problem_uuid):
        audit(f"Updating problem with uuid {problem_uuid}", log_headers=True)
        problem = self.check_item(problem_uuid)

        parser = reqparse.RequestParser()
        parser.add_argument("statement", store_missing=False)
        parser.add_argument("yaml", store_missing=False)
        args = parser.parse_args()
        if len(args) == 0:
            return get_error_result(_("No attributes to update"))
        if "statement" in args:
            problem.statement = args["statement"]
        elif "yaml" in args:
            problem.update_with_yaml(args["yaml"])
        persist_record(problem)
        return problem_schema.dump(problem)

    @jwt_required
    @caller_is.admin_or_problem_author()
    def delete(self, problem_uuid):
        audit(f"Deleting problem with uuid {problem_uuid}")
        problem = self.check_item(problem_uuid)
        problem.add_tag(Tag.SystemTag.HIDDEN.value)
        return get_message_result(_("Problem {} was set to hidden"), problem_uuid)


class ProblemListResource(YouQuizResource):
    def get(self):
        # jwt_user = get_jwt_user()
        # audit(f"{jwt_user.email} accessing problem list via API")

        # TODO filter by number of tags, comments, votes, etc
        kwargs = parse_pagination_args(
            "statement_contains", "author_uuid", "fuzzy_search"
        )

        statement_contains = kwargs.pop("statement_contains", None)
        author_uuid = kwargs.pop("author_uuid", None)
        filter_bys = kwargs.setdefault("filter_bys", {})
        if author_uuid is not None:
            filter_bys["author_uuid"] = author_uuid
        filters = kwargs.setdefault("filters", [])
        # For now, include Tag.SystemTag.HIDDEN problems, clients should filter them out
        # before showing users list of problems
        if statement_contains is not None:
            filters.append(Problem.statement.contains(statement_contains))

        pagination = Problem.list(**kwargs)
        return problems_schema.dump(pagination.items) if pagination is not None else []

    @jwt_required
    def post(self):
        # TODO Extract to caller_is.not_none() decorator to guard against cases
        # where user still has a token, but the user has been removed since token was issued
        author = get_jwt_user()
        if author is None:
            return get_error_result(_("User does not exist"))
        audit(f"User {author.email} adding a new problem")

        parser = reqparse.RequestParser()
        parser.add_argument("statement", store_missing=False)
        # Refer to Problem.from_yaml()
        parser.add_argument("yaml", store_missing=False)
        kwargs = parser.parse_args()
        statement = kwargs.pop("statement", None)
        yaml = kwargs.pop("yaml", None)
        problem = None
        if statement is not None:
            problem = Problem(author_uuid=author.uuid, statement=statement)
        elif yaml is not None:
            problem = Problem.from_yaml(author_uuid=author.uuid, yaml=yaml)
        else:
            current_app.logger.info(
                "Neither statement nor yaml was defined during this POST /problems call"
            )
        if problem is not None:
            persist_record(problem)
        return problem_schema.dump(problem) if problem is not None else []


class ProblemQuestionResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid, question_uuid):
        problem = self.check_item(problem_uuid)
        question = _check_question(problem_uuid, question_uuid)
        return question_schema.dump(question)

    @jwt_required
    @caller_is.admin_or_problem_author()
    def put(self, problem_uuid, question_uuid):
        question = _check_question(problem_uuid, question_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("stem", store_missing=False)
        args = parser.parse_args()
        if len(args) == 0:
            return get_error_result(_("No attributes to update"))
        if "stem" in args:
            question.stem = args["stem"]
        audit(f"Trying to update question {question_uuid} to {question.stem}")
        persist_record(question)
        return question_schema.dump(question)

    @jwt_required
    @caller_is.admin_or_problem_author()
    def delete(self, problem_uuid, question_uuid):
        question = _check_question(problem_uuid, question_uuid)
        return question_schema.dump(delete_record(question))


class ProblemQuestionListResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid):
        problem = self.check_item(problem_uuid)
        if problem.questions is None:
            return []
        kwargs = parse_pagination_args("stem_contains")
        stem_contains = kwargs.pop("stem_contains", None)
        questions = problem.questions
        if stem_contains is not None:
            questions = [x for x in problem.questions if stem_contains in x.stem]
        return questions_schema.dump(questions)

    @jwt_required
    @caller_is.admin_or_problem_author()
    def post(self, problem_uuid):
        problem = self.check_item(problem_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("stem", required=True)
        kwargs = parser.parse_args()
        stem = kwargs.pop("stem", None)
        question = problem.add_question(stem)
        return question_schema.dump(question)


class ProblemQuestionAlternativeResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid, question_uuid, alternative_uuid):
        problem = self.check_item(problem_uuid)
        alternative = _check_alternative(problem_uuid, question_uuid, alternative_uuid)
        return alternative_schema.dump(alternative)

    @jwt_required
    @caller_is.admin_or_problem_author()
    def put(self, problem_uuid, question_uuid, alternative_uuid):
        alternative = _check_alternative(problem_uuid, question_uuid, alternative_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("content", store_missing=False)
        args = parser.parse_args()
        if len(args) == 0:
            return get_error_result(_("No attributes to update"))
        if "content" in args:
            alternative.content = args["content"]
        audit(
            f"Trying to update alternative {alternative_uuid} to {alternative.content}"
        )
        persist_record(alternative)
        return alternative_schema.dump(alternative)

    @jwt_required
    @caller_is.admin_or_problem_author()
    def delete(self, problem_uuid, question_uuid, alternative_uuid):
        alternative = _check_alternative(problem_uuid, question_uuid, alternative_uuid)
        return alternative_schema.dump(delete_record(alternative))


class ProblemQuestionAlternativeListResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid, question_uuid):
        question = _check_question(problem_uuid, question_uuid)
        kwargs = parse_pagination_args("content_contains")
        content_contains = kwargs.pop("content_contains", None)
        alternative_list = question.alternatives
        if content_contains is not None:
            alternative_list = [
                x for x in question.alternatives if content_contains in x.content
            ]
        return alternatives_schema.dump(alternative_list)

    @jwt_required
    @caller_is.admin_or_problem_author()
    def post(self, problem_uuid, question_uuid):
        question = _check_question(problem_uuid, question_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("content", required=True)
        kwargs = parser.parse_args()
        content = kwargs.pop("content", None)
        alternative = question.add_alternative(content)
        return alternative_schema.dump(alternative)

    @jwt_required
    @caller_is.admin_or_problem_author()
    def delete(self, problem_uuid, question_uuid, alternative_uuid):
        alternative = _check_alternative(problem_uuid, question_uuid, alternative_uuid)
        return alternative_schema.dump(delete_record(alternative))


class ProblemQuestionKeyResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid, question_uuid):
        question = _check_question(problem_uuid, question_uuid)
        return answer_schema.dump(question.key) if question.key is not None else []

    @jwt_required
    @caller_is.admin_or_problem_author()
    def post(self, problem_uuid, question_uuid):
        # TODO need to use session in case question.key removal fails?
        question = _check_question(problem_uuid, question_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("solution", required=True)
        kwargs = parser.parse_args()
        question.key = Answer(
            question_uuid=question.uuid, solution=kwargs.pop("solution", None)
        )
        persist_record(question)
        return answer_schema.dump(question.key)

    @jwt_required
    @caller_is.admin_or_problem_author()
    def delete(self, problem_uuid, question_uuid):
        question = _check_question(problem_uuid, question_uuid)
        deleted_key = question.key
        question.key = None
        persist_record(question)
        return answer_schema.dump(deleted_key)


class ProblemCommentResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid, comment_uuid):
        problem = self.check_item(problem_uuid)
        comment = problem.get_comment(comment_uuid)
        if comment is None:
            return get_error_result(
                _("Comment {} not in problem {}"), comment_uuid, problem_uuid
            )
        return comment_schema.dump(comment)

    @jwt_required
    @caller_is.admin_or_comment_author()
    def put(self, problem_uuid, comment_uuid):
        comment = _check_comment(problem_uuid, comment_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("content", store_missing=False)
        args = parser.parse_args()
        if len(args) == 0:
            return get_error_result(_("No attributes to update"))
        if "content" in args:
            comment.content = args["content"]
        audit(f"Trying to update comment {comment_uuid} to {comment.content}")
        persist_record(comment)
        return comment_schema.dump(comment)

    @jwt_required
    @caller_is.admin_or_problem_or_comment_author()
    def delete(self, problem_uuid, comment_uuid):
        comment = _check_comment(problem_uuid, comment_uuid)
        return comment_schema.dump(delete_record(comment))


class ProblemCommentListResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid):
        problem = self.check_item(problem_uuid)
        kwargs = parse_pagination_args("content_contains")
        content_contains = kwargs.pop("content_contains", None)
        filters = kwargs.setdefault("filters", [])
        if content_contains is not None:
            filters.append(Comment.content.contains(content_contains))
        pagination = problem.get_comments(**kwargs)
        return comments_schema.dump(pagination.items) if pagination is not None else []

    @jwt_required
    def post(self, problem_uuid):
        problem = self.check_item(problem_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("content", required=True)
        kwargs = parser.parse_args()
        content = kwargs.pop("content", None)
        comment = problem.add_comment(get_jwt_user().uuid, content)
        return comment_schema.dump(comment)


class ProblemVoteResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid, vote_uuid):
        problem = self.check_item(problem_uuid)
        vote = problem.get_vote(vote_uuid)
        if vote is None:
            return get_error_result(
                _("Vote {} not in problem {}"), vote_uuid, problem_uuid
            )
        return vote_schema.dump(vote)

    @jwt_required
    @caller_is.vote_owner()
    def put(self, problem_uuid, vote_uuid):
        vote = self._check_vote(problem_uuid, vote_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("vote_type", store_missing=False)
        args = parser.parse_args()
        vote_type = VoteType.from_name(args.pop("vote_type", None))
        audit(f"Trying to update vote {vote_uuid} to {vote_type}")
        if vote_type is None:
            return get_error_result(_("Invaluuid vote_type {}", vote_type))
        vote.vote_type = vote_type
        persist_record(vote)
        return vote_schema.dump(vote)

    @jwt_required
    @caller_is.admin_or_vote_owner()
    def delete(self, problem_uuid, vote_uuid):
        vote = self._check_vote(problem_uuid, vote_uuid)
        return vote_schema.dump(delete_record(vote))

    def _check_vote(self, problem_uuid, vote_uuid):
        problem = Problem.load(uuid=problem_uuid)
        vote = problem.get_vote(vote_uuid)
        if vote is None:
            abort(HTTPStatus.BAD_REQUEST)
        return vote


class ProblemVoteListResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid):
        problem = self.check_item(problem_uuid)
        kwargs = parse_pagination_args("vote_type")
        vote_type = VoteType.from_name(kwargs.pop("vote_type", None))
        filters = kwargs.setdefault("filters", [])
        if vote_type is not None:
            filters.append(Vote.vote_type == vote_type)
        pagination = problem.get_votes(**kwargs)
        return votes_schema.dump(pagination.items) if pagination is not None else []

    @jwt_required
    def post(self, problem_uuid):
        problem = self.check_item(problem_uuid)
        user = get_jwt_user()
        vote = Vote.load(problem_uuid=problem_uuid, user_uuid=user.uuid)
        if vote is None:
            parser = reqparse.RequestParser()
            parser.add_argument("vote_type", store_missing=False)
            kwargs = parser.parse_args()
            vote_type = VoteType.from_name(kwargs.pop("vote_type", None))
            if vote_type is None:
                return get_error_result(_("Invalid vote_type {}"), vote_type)
            vote = problem.add_vote(get_jwt_user().uuid, vote_type)
        return vote_schema.dump(vote)


class ProblemTagResource(YouQuizResource):
    @jwt_required
    @caller_is.admin_or_problem_author()
    def delete(self, problem_uuid, tag_uuid):
        problem = self.check_item(problem_uuid)
        tag = self.check_item(tag_uuid, model=Tag)
        problem.tags.remove(tag)
        return tag_schema.dump(tag)


class ProblemTagListResource(YouQuizResource):
    @jwt_required
    def get(self, problem_uuid):
        # For now, anybody can read tags of any problem,
        # if this is abused, then only if the problem is in some quiz the caller owns
        audit(f"Retrieving tags list for problem {problem_uuid}")
        problem = self.check_item(problem_uuid)
        # There shouldn't be that many tags, and tags are small,
        # set to 100 so most of the time tags should be returned in one page
        kwargs = parse_pagination_args("name_contains")
        if "page_size" not in kwargs:
            kwargs["page_size"] = 100
        name_contains = kwargs.pop("name_contains", None)
        filters = kwargs.setdefault("filters", [])
        if name_contains is not None:
            filters.append(Tag.name.contains(name_contains))
        pagination = problem.get_tags(**kwargs)
        return tags_schema.dump(pagination.items) if pagination is not None else []

    @jwt_required
    @caller_is.admin_or_problem_author()
    def post(self, problem_uuid):
        problem = self.check_item(problem_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("name", required=True)
        kwargs = parser.parse_args()
        name = kwargs.pop("name", "")
        tag = problem.add_tag(name)
        return tag_schema.dump(tag)


class MediaResource(YouQuizResource):
    @jwt_required
    def get(self, media_uuid):
        pass

    @jwt_required
    def put(self, media_uuid):
        pass

    @jwt_required
    def delete(self, media_uuid):
        pass


class MediaListResource(YouQuizResource):
    @jwt_required
    def get(self):
        pass

    @jwt_required
    def post(self):
        pass


class TagResource(YouQuizResource):
    @jwt_required
    def get(self, tag_uuid):
        tag = self.check_item(tag_uuid)
        return tag_schema.dump(tag)

    @jwt_required
    @caller_is.admin
    def put(self, tag_uuid):
        # Only admin can update a tag, use with care,
        # only update case-errors, typos, etc
        # Changing a tag to a different name could confuse users!!!
        audit(f"Updating tag {tag_uuid} via API", log_headers=True)
        tag = self.check_item(tag_uuid)

        parser = reqparse.RequestParser()
        parser.add_argument("name", store_missing=False)
        args = parser.parse_args()
        if len(args) == 0:
            return get_error_result(_("No attributes to update"))
        if "name" in args:
            tag.name = args["name"]
        persist_record(tag)
        return tag_schema.dump(tag)

    @jwt_required
    @caller_is.admin
    def delete(self, tag_uuid):
        tag = self.check_item(tag_uuid)
        parser = reqparse.RequestParser()
        parser.add_argument("force", type=inputs.boolean, store_missing=False)
        kwargs = parser.parse_args()
        force = kwargs.pop("force", False)
        if tag.delete(force=force):
            return get_message_result(_("Tag {} {} was removed"), tag_uuid, tag.name)
        else:
            return get_error_result(_("Unable to remove Tag {} {}"), tag_uuid, tag.name)


class TagListResource(YouQuizResource):
    @jwt_required
    def get(self):
        kwargs = parse_pagination_args("name_contains")
        name_contains = kwargs.pop("name_contains", None)
        filters = kwargs.setdefault("filters", [])
        if name_contains is not None:
            filters.append(Tag.name.contains(name_contains))
        pagination = Tag.list(**kwargs)
        return tags_schema.dump(pagination.items) if pagination is not None else []

    @jwt_required
    def post(self):
        audit("Adding a new tag")
        parser = reqparse.RequestParser()
        parser.add_argument("name", required=True)
        args = parser.parse_args()
        name = args["name"]
        tag = Tag.add(name)
        if tag is None:
            return get_error_result(_("Error adding tag"))
        return tag_schema.dump(tag)


class TagProblemListResource(YouQuizResource):
    """Only requirement at this moment is to get list of problems associated with a tag"""

    NON_ADMIN_MAX = 3  # Max problems non-admin can retrieve

    @jwt_required
    def get(self, tag_uuid):
        tag = self.check_item(tag_uuid)
        kwargs = parse_pagination_args("statement_contains")
        statement_contains = kwargs.pop("statement_contains", None)
        filters = kwargs.setdefault("filters", [])
        if statement_contains is not None:
            filters.append(Problem.statement.contains(statement_contains))
        pagination = tag.get_problems(**kwargs)
        if pagination is None:
            return []
        # Prevent user from abusing/dumping all problems
        problems = []
        if not get_jwt_user().is_admin():
            problems = pagination.items[: TagProblemListResource.NON_ADMIN_MAX]
        else:
            problems = pagination.items
        return problems_schema.dump(problems)


def _check_question(problem_uuid, question_uuid):
    problem = Problem.load(uuid=problem_uuid)
    question = None
    if problem is not None:
        question = problem.get_question(question_uuid)
    if question is None:
        abort(HTTPStatus.BAD_REQUEST)
    return question


def _check_alternative(problem_uuid, question_uuid, alternative_uuid):
    problem = Problem.load(uuid=problem_uuid)
    question = problem.get_question(question_uuid)
    if question is None:
        abort(HTTPStatus.BAD_REQUEST)
    alternative = question.get_alternative(alternative_uuid)
    if alternative is None:
        abort(HTTPStatus.BAD_REQUEST)
    return alternative


def _check_comment(problem_uuid, comment_uuid):
    problem = Problem.load(uuid=problem_uuid)
    comment = problem.get_comment(comment_uuid)
    if comment is None:
        abort(HTTPStatus.BAD_REQUEST)
    return comment

