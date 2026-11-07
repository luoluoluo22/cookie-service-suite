"""FastAPI route for the gpt-6 Cookie API bridge."""
import json
import logging
import secrets
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

from gpt6_responses_adapter import GenerationError, RequestError, complete_prepared, json_text
from gpt6_responses_adapter import prepare as prepare_response

MAX_REQUEST_BYTES = 131072
LOGGER = logging.getLogger(__name__)


def error_response(status, code, message):
    return JSONResponse({'error': {'code': code, 'message': message}}, status_code=status)


def event(kind, **fields):
    return f'event: {kind}\ndata: {json_text({"type": kind, **fields})}\n\n'


def response_events(prepared, generate):
    response_id = 'resp_' + secrets.token_hex(12)
    response = {'id': response_id, 'object': 'response', 'created_at': int(time.time()), 'model': prepared.model}
    yield event('response.created', response=response | {'status': 'in_progress', 'output': []})
    try:
        result = complete_prepared(prepared, generate) | response
    except (GenerationError, OSError, ValueError, TypeError, KeyError, IndexError) as error:
        LOGGER.warning("GPT-6 Responses generation failed (%s)", type(error).__name__)
        failure = {'code': 'upstream_output_invalid', 'message': 'Cookie API did not return a usable response'}
        yield event('response.failed', response=response | {'status': 'failed', 'output': [], 'error': failure})
        return
    item = result['output'][0]
    if item['type'] == 'function_call':
        yield event('response.output_item.added', output_index=0, item=item | {'status': 'in_progress', 'arguments': ''})
        yield event('response.function_call_arguments.delta', output_index=0, item_id=item['id'], delta=item['arguments'])
        yield event('response.function_call_arguments.done', output_index=0, item_id=item['id'], arguments=item['arguments'])
    else:
        yield event('response.output_item.added', output_index=0, item=item | {'status': 'in_progress', 'content': []})
        part = item['content'][0]
        part_fields = {'item_id': item['id'], 'output_index': 0, 'content_index': 0}
        yield event('response.content_part.added', **part_fields, part=part | {'text': ''})
        yield event('response.output_text.delta', **part_fields, delta=part['text'])
        yield event('response.output_text.done', **part_fields, text=part['text'])
        yield event('response.content_part.done', **part_fields, part=part)
    yield event('response.output_item.done', output_index=0, item=item)
    yield event('response.completed', response=result)
    yield 'data: [DONE]\n\n'


def make_responses_router(generate):
    router = APIRouter()

    @router.post('/v1/responses')
    async def responses(request: Request):
        host = request.headers.get('host', '').partition(':')[0].lower()
        if host not in ('127.0.0.1', 'localhost') or 'origin' in request.headers:
            return error_response(403, 'forbidden_origin', 'Only local native clients may use this route')
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                return error_response(413, 'request_too_large', 'Responses request exceeds 128 KiB')
            body.extend(chunk)
        try:
            data = json.loads(body)
            if not isinstance(data, dict):
                raise RequestError('Expected a JSON object')
            if data.get('model') != 'gpt-6':
                return error_response(501, 'unsupported_model', 'This Cookie API Responses route supports gpt-6')
            if not isinstance(data.get('stream', False), bool):
                raise RequestError('stream must be a boolean')
            prepared = prepare_response(data)
        except (RequestError, ValueError, TypeError, RecursionError) as error:
            return error_response(422, 'invalid_request', str(error))

        headers = {'Cache-Control': 'no-store'}
        if data.get('stream'):
            return StreamingResponse(response_events(prepared, generate), media_type='text/event-stream', headers=headers)
        try:
            result = await run_in_threadpool(complete_prepared, prepared, generate)
        except (GenerationError, OSError, ValueError, TypeError, KeyError, IndexError) as error:
            LOGGER.warning("GPT-6 Responses generation failed (%s)", type(error).__name__)
            return error_response(502, 'upstream_output_invalid', 'Cookie API did not return a usable response')
        return JSONResponse(result, headers=headers)

    return router
