from __future__ import annotations

import typer

from ..application.configuration_service import ConfigurationService
from ..application.installation_service import InstallationService
from ..application.services import HookOrchestrationService
from ..application.validation_service import ValidationService
from ..domain.value_objects import HookType
from ..infrastructure.config import YamlConfigLoader
from ..infrastructure.filesystem import LocalFileSystemService
from ..infrastructure.git import InMemoryGitRepository
from ..infrastructure.process import RecordingProcessExecutor


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def install(config_path: str = ".praevisio.yaml") -> None:
    fs = LocalFileSystemService()
    installer = InstallationService(fs, config_path)
    path = installer.install()
    typer.echo(f"Installed default config at {path}")


@app.command("pre-commit")
def pre_commit(config_path: str = ".praevisio.yaml") -> None:
    # Minimal local run: load config, create simple git + executor, and run.
    fs = LocalFileSystemService()
    loader = YamlConfigLoader()
    config = ConfigurationService(loader, fs, config_path).load()
    ValidationService().validate(config)
    # NOTE: replace InMemoryGitRepository with a real Git adapter later.
    git = InMemoryGitRepository(staged_files=[])
    executor = RecordingProcessExecutor(default_exit_code=0)
    results = HookOrchestrationService(git, executor).run_hooks(HookType.PRE_COMMIT, config)
    skipped = [r for r in results if r.skipped]
    typer.echo(f"Ran {len(results)} hooks, skipped {len(skipped)}")


def main() -> None:
    app()

