#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `spacetx_biohub_writer` package."""

from click.testing import CliRunner

from spacetx_biohub_writer import cli


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    assert 'Usage:' in help_result.output
