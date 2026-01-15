# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-01-15

### Added
- Comprehensive NumPy-style docstrings for all public methods in `metrics.py`
- Complete API reference documentation in `docs/api.md`
- 5-minute Quick Start Guide in `docs/quickstart.md`
- HTML API documentation generation script
- Enhanced input validation for metric IDs with JSON compatibility checks
- Maximum limits for metric counts (100 total, 20 mandatory)
- Better error messages with actionable context
- Development roadmap in `docs/roadmap.md`
- Sprint planning system in `PLAN.md`

### Changed
- Improved validation messages for better developer experience
- Updated error handling to provide more context

### Fixed
- Python version inconsistencies - aligned all configs to support Python 3.10-3.13
- Removed Python 3.14 from supported versions as Pydantic doesn't support it yet
- Docker image build tools configuration
- Report formatting issues

### Documentation
- Added comprehensive docstrings following NumPy style guide
- Created Quick Start Guide for new users
- Added complete API reference documentation
- Fixed typos throughout the codebase
- Added clear installation and usage instructions

## [0.1.1] - 2025-12-16

### Added
- Expanded test coverage for all core functionality
- Testing infrastructure with pytest and tox
- Multi-version testing support (Python 3.10-3.13)
- Integration with Docker for isolated testing

### Changed
- Improved test organization and structure

## [0.1.0] - 2025-12-14

### Added
- Initial release of teval framework
- Core `EvaluationRubric` class for defining evaluation criteria
- `MetricDefinition` for individual metric specifications
- Two-tier metric system (mandatory and cumulative)
- LLM integration methods:
  - `to_prompt_text()` for generating evaluation prompts
  - `to_json_schema()` for structured LLM outputs
  - `to_pydantic_model()` for type-safe validation
  - `validate_result()` for checking evaluation results
- Helper functions for Pydantic model generation
- Model alignment validation features
- Comprehensive unit tests
- Apache 2.0 License

### Features
- Binary Yes/No evaluation system
- Mandatory metrics that all must pass
- Cumulative metrics with threshold-based scoring
- JSON Schema generation compatible with OpenAPI/Swagger
- Dynamic Pydantic model creation
- Full type safety and IDE support
- Minimal dependencies (only Pydantic 2.9.0+)

[0.1.2]: https://github.com/tvaroska/teval/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/tvaroska/teval/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/tvaroska/teval/releases/tag/v0.1.0