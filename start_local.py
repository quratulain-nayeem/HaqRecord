"""Start local HaqRecord services. Never writes to the Bolna API."""
import json
import re
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.tools'
PYTHON = ROOT / '.venv-native/Scripts/python.exe'
CLOUDFLARED = RUNTIME / 'cloudflared.exe'
URL_PATTERN = r'https://[a-z0-9-]+\.trycloudflare\.com'
CHILDREN = []
DNS_RETRIED = set()


def healthy(address):
    try:
        r = httpx.get(address.rstrip('/') + '/health', timeout=4)
        return r.status_code == 200 and r.json().get('status') == 'ok'
    except (httpx.HTTPError, ValueError):
        return False


def public_healthy(address):
    if healthy(address):
        return True
    host = address.split('://', 1)[-1].split('/', 1)[0]
    try:
        socket.getaddrinfo(host, 443)
    except socket.gaierror:
        if host not in DNS_RETRIED:
            DNS_RETRIED.add(host)
            # A newly issued quick-tunnel hostname can be negatively cached by
            # Windows before its DNS record appears. Do not change DNS servers.
            print('Refreshing the cached lookup for the public connection...', flush=True)
            subprocess.run(['powershell.exe', '-NoProfile', '-Command', 'Clear-DnsClientCache'],
                           capture_output=True, timeout=10,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            return healthy(address)
    return False


def launch(name, args):
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    err = RUNTIME / f'{name}-{stamp}.stderr.log'
    with (RUNTIME / f'{name}-{stamp}.stdout.log').open('ab') as out, err.open('ab') as stderr:
        child = subprocess.Popen(args, cwd=ROOT, stdout=out, stderr=stderr,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
    CHILDREN.append(child)
    return child, err


def server(port, app, name):
    address = f'http://127.0.0.1:{port}'
    if healthy(address):
        if port == 8000:
            status = httpx.get(address + '/voice/status', timeout=20).json()
            if status.get('mode') != 'backend_intake':
                raise RuntimeError('Port 8000 is running a different app.')
        print(f'{name}: already running.', flush=True)
        return
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'Port {port} is occupied but unhealthy. No process was stopped.')
    child, log = launch(name, [str(PYTHON), '-m', 'uvicorn', app, '--host',
                              '127.0.0.1', '--port', str(port), '--reload',
                              '--timeout-graceful-shutdown', '5', '--no-access-log'])
    for _ in range(30):
        if healthy(address):
            print(f'{name}: started and checked.', flush=True)
            return
        if child.poll() is not None:
            break
        time.sleep(.5)
    raise RuntimeError(f'{name} did not start. See {log}')


def public_connection(old):
    if old and public_healthy(old):
        print('Reused the existing public address.', flush=True)
        return old
    # Do not create a second tunnel if this project's existing process is unhealthy.
    command = "Get-CimInstance Win32_Process -Filter \"Name='cloudflared.exe'\" | Select-Object ExecutablePath,CommandLine | ConvertTo-Json -Compress"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
                            capture_output=True, text=True, check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    processes = json.loads(result.stdout or '[]')
    if isinstance(processes, dict):
        processes = [processes]
    running = any(str(p.get('ExecutablePath', '')).lower() == str(CLOUDFLARED).lower()
                  and '127.0.0.1:8001' in (p.get('CommandLine') or '') for p in processes)
    if running:
        for log in sorted(RUNTIME.glob('tunnel*.stderr.log'), key=lambda p: p.stat().st_mtime, reverse=True):
            urls = re.findall(URL_PATTERN, log.read_text(encoding='utf-8', errors='replace'))
            if urls and public_healthy(urls[-1]):
                return urls[-1]
        raise RuntimeError('An existing tunnel is running but unreachable. Check its logs/internet connection; no duplicate was started.')
    print('Opening a temporary public voice connection...', flush=True)
    child, log = launch('tunnel-startup', [str(CLOUDFLARED), 'tunnel', '--url',
                                         'http://127.0.0.1:8001', '--no-autoupdate'])
    for _ in range(45):
        if child.poll() is not None:
            break
        urls = re.findall(URL_PATTERN, log.read_text(encoding='utf-8', errors='replace'))
        if urls and public_healthy(urls[-1]):
            return urls[-1]
        time.sleep(.75)
    raise RuntimeError(f'The public connection did not become healthy. See {log}')


def main():
    for path in (PYTHON, CLOUDFLARED, ROOT / '.env'):
        if not path.exists():
            raise RuntimeError(f'Missing required file: {path}')
    server(8000, 'main:app', 'website')
    server(8001, 'bridge_app:app', 'voice-callback')
    old = dotenv_values(ROOT / '.env').get('HAQRECORD_VOICE_PUBLIC_URL')
    public = public_connection(old)
    if old != public:
        set_key(str(ROOT / '.env'), 'HAQRECORD_VOICE_PUBLIC_URL', public)
        print('Updated only the local callback address. Bolna has not been changed.', flush=True)
    from voice_agent_guard import TOOLS
    paths = TOOLS
    lines = [f'Current public voice address: {public}', '',
             'Use these URLs in the corresponding Bolna tools. Keep existing tokens. Save agent after editing.']
    lines += [f'{name}: {public}/bolna/tools/{path}' for name, path in paths.items()]
    lines += ['', 'If optional tools are connected, update their hostname to this same address too.',
              'This startup never changes the remote Bolna agent.']
    instructions = ROOT / 'VOICE_CONNECTION_URLS.txt'
    instructions.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Public connection checked: {public}', flush=True)
    status = httpx.get('http://127.0.0.1:8000/voice/status', timeout=20).json()
    if status.get('ready') and status.get('backend_connected'):
        print('Voice connection ready.', flush=True)
    else:
        print('Local services are healthy. Bolna still needs matching tool URLs or a successful configuration check.', flush=True)
    print(f'Tool URL instructions: {instructions}\nOpen http://127.0.0.1:8000/voice and refresh.\n'
          'Services run in the background. After restarting Windows, run this command again.\n'
          'This is local development, not permanent cloud hosting.', flush=True)


if __name__ == '__main__':
    # One starter at a time, including simultaneous double clicks.
    import msvcrt
    with (RUNTIME / 'startup.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise SystemExit('HaqRecord startup is already in progress.')
        try:
            main()
        except Exception as error:
            raise SystemExit(f'Startup incomplete: {error}\nCheck .tools logs. Existing services were not stopped.')
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
