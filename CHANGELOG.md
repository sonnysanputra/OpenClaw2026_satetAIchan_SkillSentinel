# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

## [0.1.0-foundations] — Phase 0 close

### Added
- Project skeleton: `pyproject.toml`, `src/` layout, tests, CI workflow.
- Core Pydantic schemas: `SkillBundle`, `Finding`, `RiskReport`, `ScanRequest`.
- Stub orchestrator wiring five empty specialist agents end-to-end.
- CLI skeleton (`skillsentinel scan|verdict|gateway|doctor|config|logs|models`).
- Build provenance system (public vs. internal build mode).
- Pre-commit hooks (ruff format/check, mypy).
- GitHub Actions CI (lint, type-check, test, smoke build).
- Design documents under `docs/`.

## [0.0.1-design]

### Added
- Architecture design, test plan, OpenClaw integration spec, complete to-do list.
