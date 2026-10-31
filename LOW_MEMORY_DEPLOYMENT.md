# Deployment for a small-memory host

Use `deploy_app:app` for the combined website and authenticated Bolna callbacks.
It avoids a second Python process and its duplicate imports. The existing
`main:app` and `bridge_app:app` still support the split local setup.

## Start one server process

```bash
python -m uvicorn deploy_app:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
```

On Alwaysdata's **User program** site type, use the platform's assigned address
and port instead:

```bash
python -m uvicorn deploy_app:app --host "$IP" --port "$PORT" --workers 1 --no-access-log
```

Install `requirements.txt` in the host's Python environment first. Use its virtual
environment's Python executable where appropriate. Do not use `--reload`, run a
second bridge, or increase the worker count on a 256 MB account. Memory limits
cover all processes; the memory gates operate within one Python process.

## Keep configuration and data on the host

- Configure Bolna keys and callback credentials privately with environment
  variables or a private `.env` file. Never commit them.
- Set `SESSION_COOKIE_SECURE=true` on the public HTTPS site.
- Set `HAQRECORD_VOICE_PUBLIC_URL` to the combined website's public HTTPS origin.
  The callback paths remain `/bolna/tools/...`.
- Set `HAQRECORD_PUBLIC_APP_URL` to that same website origin if recipient response
  links are wanted. The full website, not a callback-only bridge, must serve them.
- Keep the SQLite database files on persistent, private writable storage. Optional
  paths are `HAQRECORD_DB_PATH` and `HAQRECORD_AUTH_DB_PATH`.
- Publish the new callback hostname and existing authentication to the Bolna agent
  using the reviewed registration/repair workflow. Merely setting an environment
  variable does not change URLs already saved in Bolna. Keep the old local bridge
  running until the remote callback update and public checks succeed.

Changing hosting address requires a real public-site check, including HTTPS
cookies, microphone permission, callback reachability, private approval, saving
and reopening a fictional case. This change does not itself deploy a website or
move existing worker databases.

## What changed

- PIN and password hashing retain their original Argon2id parameters. Expensive
  verification/hash operations now take turns rather than allocating their large
  workspaces simultaneously.
- Source processing is limited to one job at a time and shares the expensive-work
  slot with password operations. Waiting source jobs do not each load an original
  file into memory. Database transactions are kept outside that shared slot to
  avoid lock-order deadlocks.
- Large uploads and packet downloads queue before their application handlers read
  a body or build a ZIP. Cancellation and errors release their slot. Lightweight
  case reads and voice callbacks do not wait on this upload gate.
- ZIP exports spill to private temporary storage after 1 MB and stream in 64 KB
  chunks. Originals and reports remain in the packet, and temporary files close
  when the response completes.

This trades overlapping heavy work for a short wait. There is no new voice-call
attempt limit, reduced password strength, or smaller supported file-size limit.

## Measurements and verification

The original Windows probe measured approximately 314 MiB peak working set for
four simultaneous PIN verifications in the web process. After serializing that
work, the same probe measured approximately 122 MiB. This excludes the old separate
bridge; use the combined entry point to avoid that extra idle process.

Run a fresh probe on the actual host:

```bash
python profile_runtime.py
```

The probe uses fictional records in temporary databases and makes no provider
requests. It reports current and peak working set on Windows or resident memory
on Linux. The upload scenario includes an in-process test client and is not a
production load test. It does not measure arbitrary PDF decompression, every
possible case history, or the simultaneous footprint of all extraction subprocesses.

Relevant regressions:

```bash
python tests/test_memory_budget.py
python tests/test_worker_voice.py
python tests/test_case_workspace.py
python tests/test_resolution.py
python tests/test_section_voice.py
```

256 MB is a deployment target, not a proven hard ceiling for every document and
case size. Test the actual Linux account before sharing it with judges. Temporary
disk space is also needed for exports and counts against the hosting quota.
