"""Backend observations and additive wrappers. Authorization lives in frozen rules.

The case RLock spans snapshot, native decision, callback and result observation.
This is a single-process consistency boundary, not distributed authentication or
an atomic transaction between files and the enforcement runtime.
"""
from contextlib import nullcontext
from contextvars import ContextVar
from functools import wraps
import inspect
import json
import sys
import uuid

from policyweave.core.policy import fact
from policyweave.enforcement.telemetry import current_trace
from policy_port.binding import make_policy, CALLS

GATES = frozenset(('set_case_scope', 'save_memo_part', 'save_memo_version', 'deliver_memo',
                   'start_review', 'save_review_pass', 'finish_review', 'tell_user', 'leave_note'))
PRODUCERS = frozenset(('run_qa_loop', 'get_memo_parts', 'get_memo_check', 'get_evidence_matrix',
                       'get_latest_review', 'save_research_plan', 'save_profile_requirements'))
# These codes concern the caller's own public operation. Combinations with other
# reasons are masked, including role/ownership reasons. Never reveal other state.
PUBLIC_CODES = {
    'set_case_scope': {'P5'}, 'save_memo_version': {'P6', 'P9'},
    'deliver_memo': {'N5', 'P9', 'P40'}, 'start_review': {'P9', 'P35'},
    'finish_review': {'P9', 'P25', 'P37'}, 'tell_user': {'P8'}, 'leave_note': {'P42'},
}
SYSTEM_ACTORS = {
    'set_case_scope': {'Lead Analyst'}, 'save_memo_version': {'Lead Analyst'},
    'deliver_memo': {'Lead Analyst'}, 'tell_user': {'Lead Analyst'},
    'start_review': {'IC Reviewer'}, 'save_review_pass': {'IC Reviewer'},
    'finish_review': {'IC Reviewer'},
}
_sessions = {}
_pending_reads = ContextVar('port_pending_reads', default=None)


def app():
    return sys.modules['tools.server']


def refusal(tool_name, feedback):
    """Use the existing ToolError channel, with bounded caller-safe feedback."""
    from mcp.server.mcpserver.exceptions import ToolError
    actor = app().CALLER.get()
    allowed_scope = SYSTEM_ACTORS.get(tool_name, set())
    if tool_name == 'leave_note':
        from tools.agents import RESEARCHERS
        allowed_scope = set(RESEARCHERS)
    reasons = set(feedback['reasonCodes'])
    visible = sorted(reasons) if (actor in allowed_scope and reasons
                                and reasons <= PUBLIC_CODES.get(tool_name, set())) else ['POLICY_BLOCKED']
    safe = {key: feedback[key] for key in ('requestId', 'decision', 'reasonType')}
    safe['reasonCodes'] = visible
    raise ToolError('Refused by rule ' + ', '.join(visible) + ': ' + json.dumps(safe, sort_keys=True))


def field(rows, obj, name, value):
    if value is not None:
        rows.append(fact('Field', obj, name, value))


def section_rows(rows, obj, key, revision):
    from tools import sections
    field(rows, obj, 'section_key', key)
    field(rows, obj, 'owner', sections.BY_KEY[key].owner)
    for key_in, key_out in [('author', 'author'), ('revision', 'revision'),
                             ('sha256', 'content_hash'), ('saved_at', 'saved_at_text')]:
        field(rows, obj, key_out, revision.get(key_in))


class Session:
    def __init__(self, case_id):
        self.case_id = case_id
        self.history = []
        self.policy = make_policy(facts=self.snapshot, refusal=refusal, after=self.after)

    def snapshot(self, context, registry):
        from tools import case_file, sections
        server = app()
        case = case_file.read_case()  # An exception never becomes an empty snapshot.
        if case['run_id'] != self.case_id:
            raise RuntimeError('Active case changed during policy observation')
        req = context['request']
        q, action, params = req['id'], req['event'], self.arguments
        # Parameters in this hook are the original values, not parsed gate text.
        rows = list(self.history)
        field(rows, q, 'case_id', self.case_id)
        field(rows, q, 'version_count', len(case['memo_drafts']))
        if case.get('scope') is not None:
            field(rows, q, 'scope_record', q + '/scope')
        if action == 'save_memo_part':
            try:
                key = sections.section_key(params.get('section'))
            except ValueError:
                pass  # No escape Allow just to execute an unknown-section error.
            else:
                field(rows, q, 'section_key', key)
                field(rows, q, 'owner', sections.BY_KEY[key].owner)
        for key, revision in case_file.current_parts(case).items():
            obj = q + '/section/' + key
            field(rows, q, 'section_record', obj)
            section_rows(rows, obj, key, revision)
        for kind, record in (case.get('workflow') or {}).items():
            if not isinstance(record, dict):
                continue  # iteration_log/rewrite_plan are lists, not workflow records.
            obj = q + '/workflow/' + kind
            field(rows, q, 'workflow_record', obj)
            field(rows, obj, 'workflow_kind', kind)
            field(rows, obj, 'author', record.get('author'))
            field(rows, obj, 'saved_at_text', record.get('saved_at'))
        for position, review in enumerate(case['reviews']):
            obj = q + '/review/' + str(position)
            field(rows, q, 'review_record', obj)
            for source, target in [('memo_version', 'memo_version'), ('round', 'review_round'),
                                   ('verdict', 'verdict')]:
                field(rows, obj, target, review.get(source))
            field(rows, obj, 'review_position', position)
            for number in review['passes']:
                field(rows, obj, 'pass_number', int(number))
            for index, item in enumerate(review['items']):
                field(rows, obj + '/item/' + str(index), 'severity', item.get('severity'))
        saved = None
        if action in ('deliver_memo', 'start_review'):
            number = params.get('version' if action == 'deliver_memo' else 'memo_version')
            # Resolve the real original selector. Its missing-version error cannot
            # authorize execution. Missing positive observations cause a refusal.
            try:
                saved = server._version(case, number)
            except ValueError:
                pass
        elif action == 'finish_review':
            try:
                review = server._review(case, params['review_id'])
                saved = server._version(case, review['memo_version'])
            except ValueError:
                pass
        if saved is not None:
            field(rows, q, 'memo_version', saved['version'])
            # Missing/malformed check is a capture error, never an empty clean check.
            findings = saved['check']['rule_findings']
            for index, finding in enumerate(findings):
                field(rows, q, 'rule_finding', str(index) + ':' + str(finding['rule']))
        for index, delivery in enumerate(case['deliveries']):
            obj = q + '/delivery/' + str(index)
            field(rows, q, 'delivery_record', obj)
            field(rows, obj, 'memo_version', delivery['memo_version'])
        if action in ('tell_user', 'leave_note'):
            text = params['message' if action == 'tell_user' else 'note']
            field(rows, q, 'character_count', len(text if action == 'tell_user' else text.strip()))
        return rows

    def after(self, context, result):
        # This is a real successful original callback, not inferred from a gate.
        from tools import case_file
        req = context['request']
        rows = [fact('Event', req['id'], req['principal'], req['event'])]
        field(rows, req['id'], 'case_id', self.case_id)
        field(rows, req['id'], 'outcome', 'applied')
        # Backend snapshot refresh following execution publishes these observations.
        self.history.extend(rows)
        trace = current_trace()
        if trace:
            trace.event('state', 'case-file', data={'operation': req['event'],
                         'requestId': req['id'], 'observed_case': case_file.read_case()})
        return result


def session(case):
    from tools import case_file
    key = str(case_file.active_run_dir().resolve())
    if key not in _sessions:
        _sessions[key] = Session(case['run_id'])
    return _sessions[key]


def port_entry(body):
    """Wrap the unchanged source callback; native stack tracking retains body."""
    signature = inspect.signature(body)
    @wraps(body)
    def invoke(*args, **kwargs):
        from tools import case_file
        server = app()
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        arguments = {key: server._plain(value) for key, value in bound.arguments.items()}
        with case_file._lock:
            before = case_file.read_case()
            state = session(before)
            if body.__name__ in GATES:
                # execute retains a direct original-body reference on this stack.
                state.arguments = arguments
                encoded = {key: json.dumps(value, ensure_ascii=False) if
                           CALLS[body.__name__].get(key) == 'json' and isinstance(value, str)
                           else value for key, value in arguments.items()}
                original_error = []
                def callback(context):
                    try:
                        return body(*args, **kwargs)
                    except Exception as error:
                        original_error.append(error)
                        raise
                try:
                    return state.policy.execute(server.CALLER.get() or 'unattributed', body.__name__, encoded,
                                                callback)
                except Exception:
                    # Preserve the error while retaining stopped-session state.
                    if original_error:
                        raise original_error[0]
                    raise
                finally:
                    del state.arguments
            result = body(*args, **kwargs)
            pending = _pending_reads.get()
            if body.__name__.startswith('get_') and pending is not None:
                pending.append((state, body.__name__, arguments, before, result))
            else:
                record_producer(state, body.__name__, arguments, before, result)
            return result
    return invoke


def record_producer(state, action, arguments, before, result, dispatched=None):
    """Successful source execution only; historical task reads are not model inputs."""
    from tools import case_file, sections
    actor = app().CALLER.get() or 'unattributed'
    event_id = 'observed-' + uuid.uuid4().hex  # producers have no gate request ID
    rows = [fact('Event', event_id, actor, action)]
    field(rows, event_id, 'case_id', state.case_id)
    field(rows, event_id, 'outcome', 'applied')
    if action in ('run_qa_loop', 'save_research_plan', 'save_profile_requirements'):
        field(rows, event_id, 'preceding_version_count', len(before['memo_drafts']))
    open_review = next((r for r in reversed(before['reviews']) if not r.get('verdict')), None)
    if open_review and action.startswith('get_'):
        field(rows, event_id, 'review_scope', state.case_id + '/' + open_review['id'])
    complete = dispatched is not None and not dispatched.endswith(app().TRUNCATED)
    if complete and action in ('get_memo_parts', 'get_memo_check') and arguments.get('version') is not None:
        saved = app()._version(before, arguments['version'])
        # A section-only check is NOT an exact whole-version check observation.
        if action == 'get_memo_parts' or not arguments.get('section'):
            field(rows, event_id, 'memo_version', saved['version'])
        if action == 'get_memo_parts' and arguments.get('sections_wanted'):
            for alias in arguments['sections_wanted']:
                key = sections.section_key(alias)
                ref = saved['parts'].get(key)
                if ref:
                    revision = before['memo_parts'][key][ref['revision'] - 1]
                    # Original MAX_READ protects this string-returning read;
                    # no notes are attached to this tool, and no quarantine runs.
                    if len(result) <= app().MAX_READ and revision['markdown'] in result:
                        obj = state.case_id + '/section/' + key + '/' + str(ref['revision'])
                        section_rows(rows, obj, key, revision)
                        field(rows, event_id, 'returned_section', obj)
    if complete and action == 'get_memo_parts' and arguments.get('version') is None:
        for alias in arguments.get('sections_wanted') or []:
            key = sections.section_key(alias)
            current = case_file.current_parts(before).get(key)
            if current and len(result) <= app().MAX_READ and current['markdown'] in result:
                obj = state.case_id + '/section/' + key + '/' + str(current['revision'])
                section_rows(rows, obj, key, current)
                field(rows, event_id, 'returned_section', obj)
    if complete and action == 'get_latest_review':
        finished = case_file.finished_reviews(before)
        if finished:
            field(rows, event_id, 'returned_review', state.case_id + '/' + finished[-1]['id'])
    state.history.extend(rows)
    trace = current_trace()
    if trace:
        trace.event('state', 'case-file', data={'operation': action, 'occurrenceId': event_id,
                     'confirmed_result': app()._plain(result), 'observed_case': case_file.read_case()})


def observe_tool(fn):
    """Surround the original dispatcher, including original refusals and formatting."""
    def decorate(body):
        return _observe_dispatch(body, fn.__name__)
    return decorate


def _observe_dispatch(body, tool_name):
    @wraps(body)
    def observed(**arguments):
        from tools import case_file
        trace = current_trace()
        actor = app().CALLER.get() or 'unattributed'
        if trace:
            trace.participant(actor, kind='agent' if app().CALLER.get() else 'environment')
            trace.participant('case-file', kind='environment')
            trace.participant('user', kind='user')
            trace.participant(tool_name, kind='tool')
        operation = trace.operation(actor, tool_name, {key: app()._plain(value) for key, value in arguments.items()}) if trace else nullcontext({})
        with case_file._lock, operation as outcome:
            if trace:
                try:
                    initial = case_file.read_case()
                except (RuntimeError, FileNotFoundError) as error:
                    trace.event('state', 'case-file', data={'phase': 'before_dispatch',
                                'observation_error': str(error)})
                else:
                    trace.event('state', 'case-file', data={'phase': 'before_dispatch', 'case': initial})
            pending = []
            pending_token = _pending_reads.set(pending)
            try:
                result = body(**arguments)
                for capture in pending:
                    record_producer(*capture, dispatched=result)
            except Exception as error:
                if trace:
                    trace.event('state', 'case-file', data={'phase': 'dispatch_error',
                                'tool': tool_name, 'errorType': type(error).__name__, 'error': str(error)})
                raise
            finally:
                _pending_reads.reset(pending_token)
            if trace:
                try:
                    final = case_file.read_case()
                except (RuntimeError, FileNotFoundError) as error:
                    trace.event('state', 'case-file', data={'phase': 'after_dispatch',
                                'observation_error': str(error)})
                else:
                    trace.event('state', 'case-file', data={'phase': 'after_dispatch', 'case': final})
            outcome['value'] = result  # exact original dispatched/truncated result
            outcome.setdefault('outcome', 'returned')
            if trace and tool_name == 'tell_user':
                message = case_file.read_case()['user_messages'][-1]
                trace.message(actor, ['user'], message['text'], phase='sent')
            return result
    return observed


def observe_background(body):
    """Observe actual local rendering/subprocess callbacks, without declaring success."""
    signature = inspect.signature(body)
    @wraps(body)
    def observed(*args, **kwargs):
        trace = current_trace()
        if not trace:
            return body(*args, **kwargs)
        bound = signature.bind(*args, **kwargs)
        # Paths are public operation arguments, not credential/config dumps.
        values = {key: str(value) if hasattr(value, '__fspath__') else value
                  for key, value in bound.arguments.items()}
        trace.participant('report-effects', kind='environment')
        with trace.operation('report-effects', body.__name__, values) as outcome:
            result = body(*args, **kwargs)
            outcome['value'] = result
            return result
    return observed


def observe_send(body):
    @wraps(body)
    def observed(self, bot_id, text):
        result = body(self, bot_id, text)
        trace = current_trace()
        if trace:
            trace.participant('scenario-input', kind='environment')
            trace.participant(bot_id, kind='agent')
            trace.message('scenario-input', [bot_id], text, phase='sent')
        return result
    return observed


def observe_messages(body):
    """Observe visible thread blocks only. Never hidden thinking or raw model input."""
    @wraps(body)
    def observed(self, bot_id, max_pages=200):
        result = body(self, bot_id, max_pages)
        trace = current_trace()
        if trace:
            trace.participant(bot_id, kind='agent')
            seen = getattr(self, '_policy_port_seen', None)
            if seen is None:
                seen = self._policy_port_seen = set()
            for message in result:
                for index, block in enumerate(message.get('blocks') or []):
                    key = (id(trace), bot_id, message['id'], index)
                    if key in seen:
                        continue
                    seen.add(key)
                    kind = block.get('kind')
                    if kind == 'text' and message.get('role') in ('bot', 'assistant'):
                        trace.model_output(bot_id, block.get('text', ''), stage='visible thread observation')
                    elif kind == 'bot_message_sent' and block.get('toBotName'):
                        recipient = block['toBotName']
                        trace.participant(recipient, kind='agent')
                        trace.message(bot_id, [recipient], block.get('text', ''), phase='sent',
                                      message_id=message['id'])
                    elif kind == 'bot_message_received' and block.get('fromBotName'):
                        sender = block['fromBotName']
                        trace.participant(sender, kind='agent')
                        trace.message(sender, [bot_id], block.get('text', ''), phase='received',
                                      message_id=message['id'])
        return result
    return observed
