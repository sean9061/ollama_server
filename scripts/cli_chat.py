#!/usr/bin/env python3
"""Simple CLI chat client for Ollama API (/api/chat).

Features:
- Interactive loop (type messages, get assistant replies)
- Streaming (default) and non-streaming modes
- /reset to clear local conversation history
- /exit or Ctrl-C to quit

Usage:
  python3 scripts/cli_chat.py --host http://localhost/api

By default the script uses http://localhost/api which matches the nginx proxy
in this repo. If you want to talk directly to the Ollama port, use
http://localhost:11434/api
"""

import argparse
import json
import sys
import requests
from requests.exceptions import RequestException


def post_chat(host: str, payload: dict, stream: bool = True):
    url = host.rstrip('/') + '/chat'
    headers = {'Content-Type': 'application/json'}
    try:
        if stream:
            resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=3600)
            resp.raise_for_status()
            return resp
        else:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            return resp
    except RequestException as e:
        print(f"Request failed: {e}")
        return None


def list_local_models(host: str):
    """Return a list of local model names by calling /tags."""
    url = host.rstrip('/') + '/tags'
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get('name') for m in data.get('models', []) if 'name' in m]
        return models
    except RequestException as e:
        print(f"Failed to list local models: {e}")
        return []


def resolve_model(host: str, requested_model: str, interactive: bool = True):
    """Resolve a requested model name against local models.

    Matching strategy (in order):
    - exact equality
    - requested + ':latest'
    - match by base name before ':'
    - startswith
    - contains

    If multiple candidates found and interactive, prompt the user to choose.
    Returns the chosen model name or None.
    """
    local = list_local_models(host)
    if not local:
        return None

    # Exact match
    if requested_model in local:
        return requested_model

    # requested + :latest
    candidate = requested_model + ':latest'
    if candidate in local:
        return candidate

    # Match base names (before colon)
    base_matches = [m for m in local if m.split(':', 1)[0] == requested_model]
    if len(base_matches) == 1:
        return base_matches[0]
    if len(base_matches) > 1 and interactive:
        print(f"Multiple models match base name '{requested_model}':")
        for i, m in enumerate(base_matches, 1):
            print(f"  {i}. {m}")
        sel = input('Choose number (or press Enter to cancel): ').strip()
        if sel.isdigit() and 1 <= int(sel) <= len(base_matches):
            return base_matches[int(sel)-1]
        return None

    # startswith
    starts = [m for m in local if m.startswith(requested_model)]
    if len(starts) == 1:
        return starts[0]
    if len(starts) > 1 and interactive:
        print(f"Multiple models start with '{requested_model}':")
        for i, m in enumerate(starts, 1):
            print(f"  {i}. {m}")
        sel = input('Choose number (or press Enter to cancel): ').strip()
        if sel.isdigit() and 1 <= int(sel) <= len(starts):
            return starts[int(sel)-1]
        return None

    # contains
    contains = [m for m in local if requested_model in m]
    if len(contains) == 1:
        return contains[0]
    if len(contains) > 1 and interactive:
        print(f"Multiple models contain '{requested_model}':")
        for i, m in enumerate(contains, 1):
            print(f"  {i}. {m}")
        sel = input('Choose number (or press Enter to cancel): ').strip()
        if sel.isdigit() and 1 <= int(sel) <= len(contains):
            return contains[int(sel)-1]
        return None

    return None


def pull_model(host: str, model: str):
    """Call /api/pull to download a model. Returns True on success."""
    url = host.rstrip('/') + '/pull'
    payload = {'model': model}
    try:
        # Use streaming to show progress
        resp = requests.post(url, json=payload, stream=True, timeout=3600)
        resp.raise_for_status()
        # Stream output lines
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            try:
                obj = json.loads(line)
                # Print status messages if present
                if isinstance(obj, dict) and 'status' in obj:
                    print(obj['status'])
                else:
                    print(line)
            except Exception:
                print(line)
        return True
    except RequestException as e:
        print(f"Failed to pull model: {e}")
        return False


def stream_response(resp, messages):
    """Consume a streaming response from the Ollama server.

    The server streams newline-delimited JSON objects. Each object may contain
    partial assistant content in `message.content` or generate responses in
    `response`. We print content fragments as they arrive and collect the final
    assistant message to append to the conversation history.
    """
    assistant_buf = []
    try:
        for raw in resp.iter_lines(decode_unicode=False):
            # raw may be bytes or a str depending on the response/requests version
            if not raw:
                continue
            if isinstance(raw, bytes):
                try:
                    line = raw.decode('utf-8')
                except Exception:
                    line = raw.decode('utf-8', errors='replace')
            else:
                line = str(raw)

            line = line.strip()
            # Some servers may prefix with data: or similar; try to strip
            if line.startswith('data:'):
                line = line[len('data:'):].strip()
            try:
                obj = json.loads(line)
            except Exception:
                # Not JSON — print raw chunk
                print(line, end='', flush=True)
                continue

            # Partial message (chat streaming uses message.content)
            if 'message' in obj and isinstance(obj['message'], dict):
                content = obj['message'].get('content')
                if content is not None:
                    # Print fragment (could be incremental)
                    print(content, end='', flush=True)
                    assistant_buf.append(content)

            # For generate endpoint compatibility
            elif 'response' in obj:
                content = obj.get('response')
                if content is not None:
                    print(content, end='', flush=True)
                    assistant_buf.append(content)

            # If done, break and append final message
            if obj.get('done') or obj.get('done', False) is True:
                break
    except KeyboardInterrupt:
        print('\n[Interrupted]')

    print('\n---')
    full = ''.join(assistant_buf).strip()
    if full:
        messages.append({'role': 'assistant', 'content': full})


def nonstream_response(resp, messages):
    try:
        obj = resp.json()
    except Exception as e:
        print(f"Failed to parse JSON response: {e}")
        return

    # chat returns message.content
    if 'message' in obj and isinstance(obj['message'], dict):
        content = obj['message'].get('content', '')
        print(content)
        messages.append({'role': 'assistant', 'content': content})
    elif 'response' in obj:
        content = obj.get('response', '')
        print(content)
        messages.append({'role': 'assistant', 'content': content})
    else:
        print(json.dumps(obj, indent=2))


def interactive(host: str, model: str, stream: bool):
    messages = []
    print('Interactive chat CLI. Type /help for commands.')
    while True:
        try:
            text = input('\nYou: ').strip()
        except (KeyboardInterrupt, EOFError):
            print('\nExiting.')
            return

        if not text:
            continue

        if text == '/help':
            print('/reset - clear conversation history')
            print('/exit  - quit')
            print('/model <name> - switch to a different model (will pull if not available)')
            print('/help  - show this help')
            continue

        # Model change command: /model <name>
        if text.startswith('/model'):
            parts = text.split(None, 1)
            if len(parts) == 1 or not parts[1].strip():
                print('Usage: /model <model-name>')
                continue
            new_model = parts[1].strip()
            # Check local models
            local = list_local_models(host)
            if new_model in local:
                model = new_model
                messages = []
                print(f"Switched to model: {model}")
                continue
            print(f"Model '{new_model}' not found locally.")
            choice = input('Pull it now? [y/N]: ').strip().lower()
            if choice == 'y' or choice == 'yes':
                ok = pull_model(host, new_model)
                if ok:
                    model = new_model
                    messages = []
                    print(f"Model pulled and switched to: {model}")
                else:
                    print('Pull failed; model not switched.')
            else:
                print('Model not pulled.')
            continue

        if text == '/reset':
            messages = []
            print('Conversation reset.')
            continue

        if text == '/exit':
            print('Goodbye')
            return

        # Add user's message
        messages.append({'role': 'user', 'content': text})

        payload = {
            'model': model,
            'messages': messages,
        }
        if not stream:
            payload['stream'] = False

        resp = post_chat(host, payload, stream=stream)
        if resp is None:
            # remove last user message on failure
            messages.pop()
            continue

        if stream:
            stream_response(resp, messages)
        else:
            nonstream_response(resp, messages)


def main():
    parser = argparse.ArgumentParser(description='CLI chat client for Ollama API')
    parser.add_argument('--host', default='http://localhost/api', help='Base API host (including /api), e.g. http://localhost/api or http://localhost:11434/api')
    parser.add_argument('--model', default='llama3.2', help='Model name to use')
    parser.add_argument('--no-stream', action='store_true', help='Disable streaming and receive single response')
    args = parser.parse_args()

    # Resolve requested model against local models. If not present, offer to pull.
    resolved = resolve_model(args.host, args.model, interactive=True)
    model_to_use = args.model
    if resolved:
        model_to_use = resolved
    else:
        print(f"Model '{args.model}' not found locally.")
        choice = input('Pull it now? [y/N]: ').strip().lower()
        if choice in ('y', 'yes'):
            ok = pull_model(args.host, args.model)
            if ok:
                model_to_use = args.model
            else:
                print('Pull failed; starting with requested model name (may error).')
        else:
            print('Continuing without pulling; the server may reject requests for this model.')

    try:
        interactive(args.host, model_to_use, stream=not args.no_stream)
    except Exception as e:
        print(f'Fatal error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
