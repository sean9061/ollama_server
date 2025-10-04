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
            print('/help  - show this help')
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

    try:
        interactive(args.host, args.model, stream=not args.no_stream)
    except Exception as e:
        print(f'Fatal error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
