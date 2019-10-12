from typing import Any

from flask import Flask, jsonify, abort, request
from zstandard import ZstdCompressor  # type: ignore

from penguin_judge.models import (
    configure, transaction,
    Submission, Contest, Environment, Problem, TestCase,
)

app = Flask(__name__)


@app.route('/environments')
def list_environments() -> Any:
    ret = []
    with transaction() as s:
        for c in s.query(Environment):
            ret.append(c.to_summary_dict())
    return jsonify(ret)


@app.route('/contests')
def list_contests() -> Any:
    # TODO(kazuki): フィルタ＆最低限の情報に絞り込み
    ret = []
    with transaction() as s:
        for c in s.query(Contest):
            ret.append(c.to_summary_dict())
    return jsonify(ret)


@app.route('/contests/<contest_id>')
def get_contest(contest_id: str) -> Any:
    with transaction() as s:
        ret = s.query(Contest).filter(Contest.id == contest_id).first()
        if not ret:
            abort(404)
        ret = ret.to_dict()
        problems = s.query(Problem).filter(
            Problem.contest_id == contest_id).all()
        if problems:
            ret['problems'] = [p.to_dict() for p in problems]
    return jsonify(ret)


@app.route('/contests/<contest_id>/problems/<problem_id>', methods=['POST'])
def submission(contest_id: str, problem_id: str) -> Any:
    body = request.json
    code = body.get('code')
    env_id = body.get('environment_id')
    if not (code and env_id):
        abort(400)

    cctx = ZstdCompressor()
    code = cctx.compress(code.encode('utf8'))

    with transaction() as s:
        if not s.query(Environment).filter(Environment.id == env_id).first():
            abort(400)
        tests = s.query(TestCase).filter(
            TestCase.contest_id == contest_id,
            TestCase.problem_id == problem_id).all()
        if not tests:
            abort(400)
        s.add(Submission(
            contest_id=contest_id, problem_id=problem_id,
            user_id='kazuki', code=code, environment_id=env_id))
        # TODO(kazuki): MQに積む
    return b'', 201


if __name__ == '__main__':
    configure()
    app.run()
