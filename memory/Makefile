# A-MEM Makefile - Version and Release Management
# =================================================

.PHONY: help version bump-major bump-minor bump-patch prerelease release tag changelog status

help:
	@echo "A-MEM Release Management"
	@echo ""
	@echo "Commands:"
	@echo "  make status          - Show current version and git status"
	@echo "  make bump-major      - Bump MAJOR version (breaking changes)"
	@echo "  make bump-minor      - Bump MINOR version (new features)"
	@echo "  make bump-patch      - Bump PATCH version (bug fixes)"
	@echo "  make prerelease      - Create prerelease version (e.g., -alpha.1)"
	@echo "  make release         - Create release (branch, tag, changelog)"
	@echo "  make tag             - Create git tag for current version"
	@echo "  make changelog       - Generate release notes"

status:
	python3 scripts/version.py status

bump-major:
	python3 scripts/version.py bump major

bump-minor:
	python3 scripts/version.py bump minor

bump-patch:
	python3 scripts/version.py bump patch

prerelease:
	python3 scripts/version.py bump prerelease

release: status
	@echo "Creating release for version $(shell cat VERSION)..."
	python3 scripts/version.py release

tag:
	@VERSION=$$(cat VERSION); \
	echo "Creating tag v$$VERSION..."; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"

changelog:
	python3 scripts/changelog.py
