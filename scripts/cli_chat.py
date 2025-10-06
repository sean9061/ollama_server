#!/usr/bin/env python3
"""Enhanced CLI chat client for Ollama API with visual improvements.

Features:
- Interactive loop with rich formatting
- Streaming (default) and non-streaming modes
- Syntax highlighting and colors
- Progress indicators
- /reset to clear local conversation history
- /exit or Ctrl-C to quit

Usage:
  python3 scripts/cli_chat.py --host http://localhost/api
"""

import argparse
import json
import sys
import requests
from requests.exceptions import RequestException
from datetime import datetime
import time
import threading
import re
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table

console = Console()

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'

# Box drawing characters
BOX_HORIZONTAL = '─'
BOX_VERTICAL = '│'
BOX_TOP_LEFT = '╭'
BOX_TOP_RIGHT = '╮'
BOX_BOTTOM_LEFT = '╰'
BOX_BOTTOM_RIGHT = '╯'
BOX_VERTICAL_RIGHT = '├'
BOX_VERTICAL_LEFT = '┤'

def print_banner():
    """Print a stylish banner on startup."""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
  ____  __   __   ___   __  ______     _______   ____
 / __ \/ /  / /  / _ | /  |/  / _ |   / ___/ /  /  _/
/ /_/ / /__/ /__/ __ |/ /|_/ / __ |  / /__/ /___/ /  
\____/____/____/_/ |_/_/  /_/_/ |_|  \___/____/___/  
                                                     
{Colors.ENDC}{Colors.DIM}Interactive AI Chat Interface{Colors.ENDC}
"""
    print(banner)

def print_separator(char='─', length=60, color=Colors.DIM):
    """Print a separator line."""
    print(f"{color}{char * length}{Colors.ENDC}")

def print_box_message(text, prefix='', color=Colors.BLUE):
    """Print a message in a nice box."""
    lines = text.split('\n')
    max_len = max(len(line) for line in lines) if lines else 0
    width = min(max_len + 4, 80)
    
    print(f"\n{color}{BOX_TOP_LEFT}{BOX_HORIZONTAL * (width - 2)}{BOX_TOP_RIGHT}")
    if prefix:
        print(f"{BOX_VERTICAL} {Colors.BOLD}{prefix}{Colors.ENDC}{color}")
        print(f"{BOX_VERTICAL_RIGHT}{BOX_HORIZONTAL * (width - 2)}{BOX_VERTICAL_LEFT}")
    for line in lines:
        padding = width - len(line) - 4
        print(f"{BOX_VERTICAL} {Colors.ENDC}{line}{' ' * padding}{color}{BOX_VERTICAL}")
    print(f"{BOX_BOTTOM_LEFT}{BOX_HORIZONTAL * (width - 2)}{BOX_BOTTOM_RIGHT}{Colors.ENDC}\n")

def print_status(message, status='info'):
    """Print a status message with icon."""
    icons = {
        'info': '[INFO]',
        'success': '[OK]',
        'error': '[ERROR]',
        'warning': '[WARN]',
        'loading': '[...]'
    }
    colors = {
        'info': Colors.BLUE,
        'success': Colors.GREEN,
        'error': Colors.RED,
        'warning': Colors.YELLOW,
        'loading': Colors.CYAN
    }
    icon = icons.get(status, '')
    color = colors.get(status, Colors.ENDC)
    print(f"{color}{icon}  {message}{Colors.ENDC}")

def print_thinking_animation():
    """Print a thinking animation while waiting for response."""
    frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    return frames

def show_loading(stop_event):
    """Show loading animation in a separate thread."""
    frames = print_thinking_animation()
    idx = 0
    while not stop_event.is_set():
        frame = frames[idx % len(frames)]
        print(f"\r{Colors.CYAN}{frame} Thinking...{Colors.ENDC}", end='', flush=True)
        idx += 1
        time.sleep(0.1)
    print('\r' + ' ' * 20 + '\r', end='', flush=True)

def get_model_info(host: str, model: str):
    """Retrieve detailed model information."""
    url = host.rstrip('/') + '/show'
    try:
        resp = requests.post(url, json={'model': model}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except RequestException:
        return None
    """Retrieve detailed model information."""
    url = host.rstrip('/') + '/show'
    try:
        resp = requests.post(url, json={'model': model}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except RequestException:
        return None

def wrap_text(text, width=56):
    """Wrap text to fit within a given width."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_length = len(word)
        if current_length + word_length + len(current_line) <= width:
            current_line.append(word)
            current_length += word_length
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_length
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def print_model_details(host: str, model: str):
    """Print detailed model information."""
    print(f"\n{Colors.BOLD}Model Information:{Colors.ENDC}")
    print(f"{Colors.DIM}{BOX_TOP_LEFT}{BOX_HORIZONTAL * 58}{BOX_TOP_RIGHT}{Colors.ENDC}")
    
    # Basic info
    print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} {Colors.CYAN}Name:{Colors.ENDC} {Colors.BOLD}{model}{Colors.ENDC}")
    
    # Try to get detailed info
    info = get_model_info(host, model)
    if info:
        # Model file info
        if 'modelfile' in info:
            modelfile_lines = info['modelfile'].split('\n')
            for line in modelfile_lines:
                if line.strip().startswith('FROM'):
                    base_model = line.replace('FROM', '').strip()
                    if len(base_model) > 45:
                        base_model = base_model[:42] + '...'
                    print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} {Colors.CYAN}Base:{Colors.ENDC} {base_model}")
                    break
        
        # Parameters
        if 'parameters' in info:
            params = info['parameters']
            if len(params) > 45:
                params = params[:42] + '...'
            print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} {Colors.CYAN}Parameters:{Colors.ENDC} {params}")
        
        # Template
        if 'template' in info:
            template = info['template']
            if len(template) > 40:
                template = template[:37] + '...'
            print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} {Colors.CYAN}Template:{Colors.ENDC} {template}")
        
        # Details
        if 'details' in info and isinstance(info['details'], dict):
            details = info['details']
            if 'format' in details:
                print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} {Colors.CYAN}Format:{Colors.ENDC} {details['format']}")
            if 'family' in details:
                print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} {Colors.CYAN}Family:{Colors.ENDC} {details['family']}")
            if 'parameter_size' in details:
                print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} {Colors.CYAN}Parameter Size:{Colors.ENDC} {details['parameter_size']}")
            if 'quantization_level' in details:
                print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} {Colors.CYAN}Quantization:{Colors.ENDC} {details['quantization_level']}")
    
    print(f"{Colors.DIM}{BOX_BOTTOM_LEFT}{BOX_HORIZONTAL * 58}{BOX_BOTTOM_RIGHT}{Colors.ENDC}")

def list_available_models(host: str):
    """List all available models with details."""
    local = list_local_models(host)
    if not local:
        print_status("No local models found", 'warning')
        return
    
    print(f"\n{Colors.BOLD}Available Local Models ({len(local)}):{Colors.ENDC}")
    print(f"{Colors.DIM}{BOX_TOP_LEFT}{BOX_HORIZONTAL * 58}{BOX_TOP_RIGHT}{Colors.ENDC}")
    for i, model_name in enumerate(local, 1):
        print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} {Colors.CYAN}{i:2}.{Colors.ENDC} {model_name}")
    print(f"{Colors.DIM}{BOX_BOTTOM_LEFT}{BOX_HORIZONTAL * 58}{BOX_BOTTOM_RIGHT}{Colors.ENDC}")

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
        print_status(f"Request failed: {e}", 'error')
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
        print_status(f"Failed to list local models: {e}", 'error')
        return []

def resolve_model(host: str, requested_model: str, interactive: bool = True):
    """Resolve a requested model name against local models."""
    local = list_local_models(host)
    if not local:
        return None

    if requested_model in local:
        return requested_model

    candidate = requested_model + ':latest'
    if candidate in local:
        return candidate

    base_matches = [m for m in local if m.split(':', 1)[0] == requested_model]
    if len(base_matches) == 1:
        return base_matches[0]
    if len(base_matches) > 1 and interactive:
        print(f"\n{Colors.YELLOW}Multiple models match base name '{requested_model}':{Colors.ENDC}")
        for i, m in enumerate(base_matches, 1):
            print(f"  {Colors.CYAN}{i}.{Colors.ENDC} {m}")
        sel = input(f'{Colors.GREEN}Choose number (or press Enter to cancel): {Colors.ENDC}').strip()
        if sel.isdigit() and 1 <= int(sel) <= len(base_matches):
            return base_matches[int(sel)-1]
        return None

    starts = [m for m in local if m.startswith(requested_model)]
    if len(starts) == 1:
        return starts[0]
    if len(starts) > 1 and interactive:
        print(f"\n{Colors.YELLOW}Multiple models start with '{requested_model}':{Colors.ENDC}")
        for i, m in enumerate(starts, 1):
            print(f"  {Colors.CYAN}{i}.{Colors.ENDC} {m}")
        sel = input(f'{Colors.GREEN}Choose number (or press Enter to cancel): {Colors.ENDC}').strip()
        if sel.isdigit() and 1 <= int(sel) <= len(starts):
            return starts[int(sel)-1]
        return None

    contains = [m for m in local if requested_model in m]
    if len(contains) == 1:
        return contains[0]
    if len(contains) > 1 and interactive:
        print(f"\n{Colors.YELLOW}Multiple models contain '{requested_model}':{Colors.ENDC}")
        for i, m in enumerate(contains, 1):
            print(f"  {Colors.CYAN}{i}.{Colors.ENDC} {m}")
        sel = input(f'{Colors.GREEN}Choose number (or press Enter to cancel): {Colors.ENDC}').strip()
        if sel.isdigit() and 1 <= int(sel) <= len(contains):
            return contains[int(sel)-1]
        return None

    return None

def pull_model(host: str, model: str):
    """Call /api/pull to download a model."""
    url = host.rstrip('/') + '/pull'
    payload = {'model': model}
    try:
        print_status(f"Downloading model: {model}", 'loading')
        resp = requests.post(url, json=payload, stream=True, timeout=3600)
        resp.raise_for_status()
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and 'status' in obj:
                    print(f"\r{Colors.CYAN}  → {obj['status']}{Colors.ENDC}", end='', flush=True)
                else:
                    print(f"\r{Colors.CYAN}  → {line}{Colors.ENDC}", end='', flush=True)
            except Exception:
                print(f"\r{Colors.CYAN}  → {line}{Colors.ENDC}", end='', flush=True)
        print()
        print_status(f"Model '{model}' downloaded successfully!", 'success')
        return True
    except RequestException as e:
        print_status(f"Failed to pull model: {e}", 'error')
        return False

def render_markdown_content(content):
    """Render markdown content with rich formatting."""
    # Check if content contains code blocks or tables
    has_code = '```' in content
    has_table = '|' in content and '-|-' in content
    
    if has_code or has_table:
        # Use rich markdown rendering
        md = Markdown(content)
        console.print(md)
    else:
        # Simple text output
        print(content)

def stream_response(resp, messages, stop_loading):
    """Consume a streaming response with enhanced visuals."""
    assistant_buf = []
    
    # Stop the loading animation
    stop_loading.set()
    time.sleep(0.15)  # Give time for loading thread to clean up
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}Assistant:{Colors.ENDC}")
    print(f"{Colors.DIM}{BOX_TOP_LEFT}{BOX_HORIZONTAL * 58}{BOX_TOP_RIGHT}{Colors.ENDC}")
    print(f"{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} ", end='', flush=True)
    
    current_line_length = 0
    max_line_width = 56
    
    # Timing for tokens/s calculation
    start_time = time.time()
    token_count = 0
    eval_count = 0
    prompt_eval_count = 0
    
    in_code_block = False
    
    try:
        for raw in resp.iter_lines(decode_unicode=False):
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
            if line.startswith('data:'):
                line = line[len('data:'):].strip()
            try:
                obj = json.loads(line)
            except Exception:
                continue

            # Extract token counts from response
            if 'eval_count' in obj:
                eval_count = obj['eval_count']
            if 'prompt_eval_count' in obj:
                prompt_eval_count = obj['prompt_eval_count']

            if 'message' in obj and isinstance(obj['message'], dict):
                content = obj['message'].get('content')
                if content is not None:
                    for char in content:
                        if char == '\n':
                            print(f"\n{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} ", end='', flush=True)
                            current_line_length = 0
                        else:
                            if current_line_length >= max_line_width and not in_code_block:
                                print(f"\n{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} ", end='', flush=True)
                                current_line_length = 0
                            print(char, end='', flush=True)
                            current_line_length += 1
                        
                        # Track code blocks to avoid breaking them
                        if content[max(0, len(''.join(assistant_buf))-2):len(''.join(assistant_buf))+1] == '```':
                            in_code_block = not in_code_block
                    
                    assistant_buf.append(content)

            elif 'response' in obj:
                content = obj.get('response')
                if content is not None:
                    for char in content:
                        if char == '\n':
                            print(f"\n{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} ", end='', flush=True)
                            current_line_length = 0
                        else:
                            if current_line_length >= max_line_width and not in_code_block:
                                print(f"\n{Colors.DIM}{BOX_VERTICAL}{Colors.ENDC} ", end='', flush=True)
                                current_line_length = 0
                            print(char, end='', flush=True)
                            current_line_length += 1
                    
                    assistant_buf.append(content)

            if obj.get('done') or obj.get('done', False) is True:
                break
    except KeyboardInterrupt:
        print(f'\n{Colors.YELLOW}[Interrupted]{Colors.ENDC}')

    print(f"\n{Colors.DIM}{BOX_BOTTOM_LEFT}{BOX_HORIZONTAL * 58}{BOX_BOTTOM_RIGHT}{Colors.ENDC}\n")
    
    full = ''.join(assistant_buf).strip()
    if full:
        messages.append({'role': 'assistant', 'content': full})
    
    # Calculate and display tokens/s
    end_time = time.time()
    elapsed = end_time - start_time
    if eval_count > 0 and elapsed > 0:
        tokens_per_sec = eval_count / elapsed
        print(f"{Colors.DIM}⚡ {eval_count} tokens in {elapsed:.2f}s ({tokens_per_sec:.2f} tokens/s){Colors.ENDC}")
        if prompt_eval_count > 0:
            print(f"{Colors.DIM}   Prompt: {prompt_eval_count} tokens{Colors.ENDC}")
    print()

def nonstream_response(resp, messages, stop_loading):
    # Stop the loading animation
    stop_loading.set()
    time.sleep(0.15)  # Give time for loading thread to clean up
    
    start_time = time.time()
    
    try:
        obj = resp.json()
    except Exception as e:
        print_status(f"Failed to parse JSON response: {e}", 'error')
        return

    print(f"\n{Colors.GREEN}{Colors.BOLD}Assistant:{Colors.ENDC}")
    print(f"{Colors.DIM}{BOX_TOP_LEFT}{BOX_HORIZONTAL * 58}{BOX_TOP_RIGHT}{Colors.ENDC}")
    
    eval_count = 0
    prompt_eval_count = 0
    
    content = ''
    if 'message' in obj and isinstance(obj['message'], dict):
        content = obj['message'].get('content', '')
    elif 'response' in obj:
        content = obj.get('response', '')
    else:
        print(json.dumps(obj, indent=2))
    
    if content:
        print(f"{Colors.DIM}{BOX_BOTTOM_LEFT}{BOX_HORIZONTAL * 58}{BOX_BOTTOM_RIGHT}{Colors.ENDC}\n")
        render_markdown_content(content)
        messages.append({'role': 'assistant', 'content': content})
        print()  # Add spacing
    
    # Extract token counts
    if 'eval_count' in obj:
        eval_count = obj['eval_count']
    if 'prompt_eval_count' in obj:
        prompt_eval_count = obj['prompt_eval_count']
    
    # Calculate and display tokens/s
    end_time = time.time()
    elapsed = end_time - start_time
    if eval_count > 0 and elapsed > 0:
        tokens_per_sec = eval_count / elapsed
        print(f"{Colors.DIM}⚡ {eval_count} tokens in {elapsed:.2f}s ({tokens_per_sec:.2f} tokens/s){Colors.ENDC}")
        if prompt_eval_count > 0:
            print(f"{Colors.DIM}   Prompt: {prompt_eval_count} tokens{Colors.ENDC}")
    print()

def print_help():
    """Print help with nice formatting."""
    help_text = f"""
{Colors.BOLD}Available Commands:{Colors.ENDC}

  {Colors.CYAN}/reset{Colors.ENDC}          Clear conversation history
  {Colors.CYAN}/exit{Colors.ENDC}           Quit the application
  {Colors.CYAN}/model <name>{Colors.ENDC}   Switch to a different model
  {Colors.CYAN}/help{Colors.ENDC}           Show this help message
"""
    print(help_text)

def interactive(host: str, model: str, stream: bool):
    messages = []
    
    print_banner()
    print_status(f"Connected to: {host}", 'success')
    print_separator()
    
    # Show detailed model information
    print_model_details(host, model)
    
    # List available models
    list_available_models(host)
    
    print_separator()
    print(f"\n{Colors.DIM}Type your message or /help for commands{Colors.ENDC}\n")
    
    while True:
        try:
            text = input(f'{Colors.BLUE}{Colors.BOLD}You:{Colors.ENDC} ').strip()
        except (KeyboardInterrupt, EOFError):
            print(f'\n\n{Colors.YELLOW}Goodbye!{Colors.ENDC}\n')
            return

        if not text:
            continue

        if text == '/help':
            print_help()
            continue

        if text == '/models':
            list_available_models(host)
            continue

        if text == '/info':
            print_model_details(host, model)
            continue

        if text.startswith('/model'):
            parts = text.split(None, 1)
            if len(parts) == 1 or not parts[1].strip():
                print_status('Usage: /model <model-name>', 'warning')
                continue
            new_model = parts[1].strip()
            local = list_local_models(host)
            if new_model in local:
                model = new_model
                messages = []
                print_status(f"Switched to model: {Colors.BOLD}{model}{Colors.ENDC}", 'success')
                print_model_details(host, model)
                continue
            print_status(f"Model '{new_model}' not found locally", 'warning')
            choice = input(f'{Colors.GREEN}Pull it now? [y/N]: {Colors.ENDC}').strip().lower()
            if choice == 'y' or choice == 'yes':
                ok = pull_model(host, new_model)
                if ok:
                    model = new_model
                    messages = []
                    print_status(f"Model pulled and switched to: {Colors.BOLD}{model}{Colors.ENDC}", 'success')
                    print_model_details(host, model)
                else:
                    print_status('Pull failed; model not switched', 'error')
            else:
                print_status('Model not pulled', 'info')
            continue

        if text == '/reset':
            messages = []
            print_status('Conversation reset', 'success')
            continue

        if text == '/exit':
            print(f'\n{Colors.YELLOW}Goodbye!{Colors.ENDC}\n')
            return

        messages.append({'role': 'user', 'content': text})

        payload = {
            'model': model,
            'messages': messages,
        }
        if not stream:
            payload['stream'] = False

        # Start loading animation
        stop_loading = threading.Event()
        loading_thread = threading.Thread(target=show_loading, args=(stop_loading,))
        loading_thread.daemon = True
        loading_thread.start()

        resp = post_chat(host, payload, stream=stream)
        if resp is None:
            stop_loading.set()
            loading_thread.join(timeout=0.5)
            messages.pop()
            continue

        if stream:
            stream_response(resp, messages, stop_loading)
        else:
            nonstream_response(resp, messages, stop_loading)
        
        # Ensure loading thread is stopped
        loading_thread.join(timeout=0.5)

def main():
    parser = argparse.ArgumentParser(description='Enhanced CLI chat client for Ollama API')
    parser.add_argument('--host', default='http://localhost/api', 
                       help='Base API host (including /api)')
    parser.add_argument('--model', default='llama3.2', 
                       help='Model name to use')
    parser.add_argument('--no-stream', action='store_true', 
                       help='Disable streaming and receive single response')
    args = parser.parse_args()

    resolved = resolve_model(args.host, args.model, interactive=True)
    model_to_use = args.model
    if resolved:
        model_to_use = resolved
    else:
        print_status(f"Model '{args.model}' not found locally", 'warning')
        choice = input(f'{Colors.GREEN}Pull it now? [y/N]: {Colors.ENDC}').strip().lower()
        if choice in ('y', 'yes'):
            ok = pull_model(args.host, args.model)
            if ok:
                model_to_use = args.model
            else:
                print_status('Pull failed; starting with requested model name (may error)', 'warning')
        else:
            print_status('Continuing without pulling; the server may reject requests', 'warning')

    try:
        interactive(args.host, model_to_use, stream=not args.no_stream)
    except Exception as e:
        print_status(f'Fatal error: {e}', 'error')
        sys.exit(1)

if __name__ == '__main__':
    main()