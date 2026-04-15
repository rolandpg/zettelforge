"""ZettelForge CLI entry point."""
import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        from zettelforge.demo import run_demo
        run_demo()
    elif len(sys.argv) > 1 and sys.argv[1] == "version":
        from zettelforge import __version__
        print(f"ZettelForge v{__version__}")
    else:
        print("Usage: python -m zettelforge [demo|version]")
        print("  demo     Run interactive CTI demo (ingests 5 reports, shows recall + synthesis)")
        print("  version  Show version")
        sys.exit(1)


if __name__ == "__main__":
    main()
