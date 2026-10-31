# Start the local demo

From the project terminal, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-HaqRecord.ps1
```

This starts the website on port 8000, the restricted voice callback server on port 8001, and a temporary public tunnel. It checks each connection, reuses healthy services, and avoids duplicate startup runs. Logs are stored in `.tools/`.

If a new tunnel address is required, only the local `.env` callback address is updated. The current five tool URLs are written to `VOICE_CONNECTION_URLS.txt`. You must copy changed URLs into Bolna yourself and save the agent. Optional connected tools need the same hostname. No token or Bolna setting is changed by this command.

Services run in the background after the command finishes. Run it again after restarting Windows. It checks services at startup; it is not a continuous monitor, Windows service, or cloud deployment. An already-running but unhealthy service is reported rather than killed automatically. If a tunnel hostname cannot resolve, startup attempts one Windows DNS-cache refresh; it does not change DNS-server settings.

The old `start_voice_bridge.ps1` command now delegates to this safe local startup and no longer runs the remote-agent update script.
