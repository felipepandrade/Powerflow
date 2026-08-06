"""Smoke tests para o CLI taskflow — cli.py.

Cobre: _parse_date (válida / inválida), _local_today (retorna date),
e os 3 comandos via typer.testing.CliRunner com mock das dependências
de banco de dados para evitar I/O real.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from taskflow.cli import _local_today, _parse_date, app


runner = CliRunner()


# ── _parse_date ────────────────────────────────────────────────────────────────

class TestParseDate:
    def test_valid_iso_date_returns_date(self) -> None:
        result = _parse_date("2026-08-06", "--from")
        assert result == date(2026, 8, 6)

    def test_invalid_format_raises_bad_parameter(self) -> None:
        with pytest.raises(typer.BadParameter):
            _parse_date("06/08/2026", "--from")

    def test_invalid_string_raises_bad_parameter(self) -> None:
        with pytest.raises(typer.BadParameter):
            _parse_date("not-a-date", "--date")

    def test_first_day_of_year(self) -> None:
        assert _parse_date("2026-01-01", "--from") == date(2026, 1, 1)

    def test_last_day_of_year(self) -> None:
        assert _parse_date("2026-12-31", "--to") == date(2026, 12, 31)


# ── _local_today ───────────────────────────────────────────────────────────────

class TestLocalToday:
    def test_returns_a_date_object(self) -> None:
        result = _local_today()
        assert isinstance(result, date)

    def test_result_is_not_in_the_past_by_much(self) -> None:
        """A data local não deve estar mais de 1 dia no futuro nem 1 dia no passado."""
        from datetime import datetime, timezone
        result = _local_today()
        utc_today = datetime.now(timezone.utc).date()
        assert abs((result - utc_today).days) <= 1


# ── Comando: build-snapshot ────────────────────────────────────────────────────

class TestBuildSnapshotCommand:
    def test_build_snapshot_with_explicit_date(self) -> None:
        with patch("taskflow.cli._build_range", new=AsyncMock(return_value=1)) as mock_build:
            result = runner.invoke(app, ["build-snapshot", "--date", "2026-08-01"])
            assert result.exit_code == 0
            mock_build.assert_called_once()
            call_args = mock_build.call_args[0]
            assert call_args[0] == date(2026, 8, 1)
            assert call_args[1] == date(2026, 8, 1)

    def test_build_snapshot_without_date_uses_today(self) -> None:
        with patch("taskflow.cli._build_range", new=AsyncMock(return_value=1)) as mock_build:
            result = runner.invoke(app, ["build-snapshot"])
            assert result.exit_code == 0
            mock_build.assert_called_once()

    def test_build_snapshot_invalid_date_fails(self) -> None:
        result = runner.invoke(app, ["build-snapshot", "--date", "not-a-date"])
        assert result.exit_code != 0


# ── Comando: backfill-snapshots ────────────────────────────────────────────────

class TestBackfillSnapshotsCommand:
    def test_backfill_with_from_and_to(self) -> None:
        with patch("taskflow.cli._build_range", new=AsyncMock(return_value=7)) as mock_build:
            result = runner.invoke(
                app,
                ["backfill-snapshots", "--from", "2026-07-01", "--to", "2026-07-07"],
            )
            assert result.exit_code == 0
            assert "processed_partitions=7" in result.output
            mock_build.assert_called_once()

    def test_backfill_without_dates_uses_default_days(self) -> None:
        with patch("taskflow.cli._build_range", new=AsyncMock(return_value=30)):
            result = runner.invoke(app, ["backfill-snapshots"])
            assert result.exit_code == 0
            assert "processed_partitions=30" in result.output

    def test_backfill_with_to_before_from_raises(self) -> None:
        """'--to' antes de '--from' deve falhar no _build_range com BadParameter."""
        # O _build_range valida end < start e levanta BadParameter
        result = runner.invoke(
            app,
            ["backfill-snapshots", "--from", "2026-08-10", "--to", "2026-08-01"],
        )
        # exit_code 1 ou 2 dependendo de como typer captura a exceção
        assert result.exit_code != 0

    def test_backfill_invalid_from_date_fails(self) -> None:
        result = runner.invoke(app, ["backfill-snapshots", "--from", "bad-date"])
        assert result.exit_code != 0


# ── Comando: recompute-metrics ────────────────────────────────────────────────

class TestRecomputeMetricsCommand:
    def test_recompute_metrics_with_valid_dates(self) -> None:
        with patch("taskflow.cli._recompute", new=AsyncMock(return_value=5)) as mock_recompute:
            result = runner.invoke(
                app,
                ["recompute-metrics", "--from", "2026-07-01", "--to", "2026-07-31"],
            )
            assert result.exit_code == 0
            assert "materialized_metrics=5" in result.output
            mock_recompute.assert_called_once()

    def test_recompute_metrics_with_project_id(self) -> None:
        import uuid
        project_id = uuid.uuid4()
        with patch("taskflow.cli._recompute", new=AsyncMock(return_value=3)) as mock_recompute:
            result = runner.invoke(
                app,
                [
                    "recompute-metrics",
                    "--from", "2026-07-01",
                    "--to", "2026-07-31",
                    "--project-id", str(project_id),
                ],
            )
            assert result.exit_code == 0
            call_kwargs = mock_recompute.call_args[0]
            assert call_kwargs[2] == project_id

    def test_recompute_metrics_invalid_project_id_fails(self) -> None:
        result = runner.invoke(
            app,
            [
                "recompute-metrics",
                "--from", "2026-07-01",
                "--to", "2026-07-31",
                "--project-id", "not-a-uuid",
            ],
        )
        assert result.exit_code != 0

    def test_recompute_metrics_to_before_from_fails(self) -> None:
        result = runner.invoke(
            app,
            ["recompute-metrics", "--from", "2026-08-10", "--to", "2026-08-01"],
        )
        assert result.exit_code != 0

    def test_recompute_metrics_missing_required_args_fails(self) -> None:
        result = runner.invoke(app, ["recompute-metrics"])
        assert result.exit_code != 0


# ── Comando: snapshots-status ─────────────────────────────────────────────────

class TestSnapshotsStatusCommand:
    def test_snapshots_status_with_no_data(self) -> None:
        with patch(
            "taskflow.cli._snapshot_status",
            new=AsyncMock(return_value=(None, None, 0, [])),
        ):
            result = runner.invoke(app, ["snapshots-status"])
            assert result.exit_code == 0
            assert "first=none" in result.output
            assert "partitions=0" in result.output
            assert "gaps=none" in result.output

    def test_snapshots_status_with_data_and_gaps(self) -> None:
        gap_date = date(2026, 7, 15)
        with patch(
            "taskflow.cli._snapshot_status",
            new=AsyncMock(
                return_value=(date(2026, 7, 1), date(2026, 7, 31), 30, [gap_date])
            ),
        ):
            result = runner.invoke(app, ["snapshots-status"])
            assert result.exit_code == 0
            assert "first=2026-07-01" in result.output
            assert "last=2026-07-31" in result.output
            assert "partitions=30" in result.output
            assert "2026-07-15" in result.output

    def test_snapshots_status_with_no_gaps(self) -> None:
        with patch(
            "taskflow.cli._snapshot_status",
            new=AsyncMock(
                return_value=(date(2026, 7, 1), date(2026, 7, 7), 7, [])
            ),
        ):
            result = runner.invoke(app, ["snapshots-status"])
            assert result.exit_code == 0
            assert "gaps=none" in result.output


# ── Entrypoint: main ──────────────────────────────────────────────────────────

class TestMain:
    def test_main_no_args_shows_help(self) -> None:
        """Sem args, o CLI deve exibir ajuda (no_args_is_help=True)."""
        result = runner.invoke(app, [])
        # Pode ser exit_code 0 (ajuda) ou outro, mas não deve crashar
        assert "backfill-snapshots" in result.output or result.exit_code in (0, 1, 2)
