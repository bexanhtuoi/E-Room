# E-Room backend organization notes

This backend now follows a more stable project skeleton inspired by the useful parts of FlowAssist:

- `config.py` centralizes runtime settings
- `security.py` owns token helpers
- `api/dependencies.py` owns request-level helpers and boundary dependencies
- `log.py` centralizes logging setup
- `database.py` defines bootstrap and session entry points
- `server.py` is the uvicorn runner
- `main.py` wires app lifecycle + middleware + router mounting

The goal is to keep service, router, and infrastructure code from drifting into random utility files.
