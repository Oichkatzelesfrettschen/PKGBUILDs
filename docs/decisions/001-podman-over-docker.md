# ADR 001: Use Podman instead of Docker for sonarqube-server

## Status: Accepted

## Context

The sonarqube-server package needs a container runtime to run the SonarQube
image. Two options are available on Arch Linux: Docker and Podman.

The PKGBUILD originally declared `depends=('podman')` but the service file,
setup script, and configuration all used `docker` CLI commands, creating an
inconsistency that prevented the package from working as-installed.

## Decision

Use Podman throughout: service file, setup script, and documentation.

## Rationale

- **Rootless by default**: Podman runs containers as the invoking user without
  a privileged daemon. SonarQube runs as a systemd user service, which aligns
  naturally with Podman's rootless model.
- **No daemon required**: Docker requires `dockerd` running as root. Podman
  has no daemon, reducing the system-level footprint.
- **Drop-in compatible**: Podman is CLI-compatible with Docker for all
  operations used here (pull, run, rm, stop, logs).
- **Arch Linux default**: Podman is the preferred container runtime in the
  Arch ecosystem for rootless use.

## Consequences

- All `docker` calls in sonarqube-server files replaced with `podman`.
- `After=docker.service` removed from service file (no daemon dependency).
- Users who prefer Docker can alias `podman` to `docker` or edit the files.
