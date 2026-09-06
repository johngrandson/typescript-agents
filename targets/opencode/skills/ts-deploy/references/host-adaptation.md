# Deployment host adaptation

Docker/Compose are the current deployment contract. No host-specific platform configuration is assumed. A requested host must support the built image, persistent storage, env
validation, health and graceful shutdown requirements.

Map migrations to a one-off pre-consumer step and preserve API/worker storage compatibility. Validate the concrete config in a disposable deployment before publishing. Do not copy
obsolete platform defaults or recommend weakening TLS.

## Starter evidence

Read `Dockerfile` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.
