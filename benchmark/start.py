# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 fileencoding=utf-8
#
# Benchmark
# Copyright (c) 2017 Max Linke & Michael Gecht and contributors
# (see the file AUTHORS for the full list of names)
#
# benchmark is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# benchmark is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with benchmark.  If not, see <http://www.gnu.org/licenses/>.import os
import os
import subprocess
import sys
from glob import glob

import click
import mdsynthesis as mds

from .cli import cli
from .util import cleanup_before_restart

PATHS = os.environ['PATH'].split(':')
BATCH_SYSTEMS = {'slurm': 'sbatch', 'sge': 'qsub', 'Loadleveler': 'llsubmit'}


def get_engine_command():
    for p in PATHS:
        for b in BATCH_SYSTEMS.values():
            if glob(os.path.join(p, b)):
                return b
    raise click.UsageError(
        'Was not able to find a batch system. Are you trying to use this '
        'package on a host with a queuing system?')


@cli.command()
@click.option(
    '-d', '--directory', help='directory to search benchmarks in', default='.')
@click.option(
    '-f',
    '--force',
    'force_restart',
    help='force restart of all benchmark systems',
    is_flag=True)
def start(directory, force_restart):
    """Start benchmark simulations.

    Benchmarks are searched for recursively starting from `--directory`.

    Checks whether benchmark folders were generated beforehand, exits
    otherwise. Only runs benchmarks that were not already started. Can be
    overwritten with (--force).

    """
    bundle = mds.discover(directory)

    # Exit if no bundles were found in the current directory.
    if not bundle:
        click.echo('No benchmark systems found to run. Exiting.')
        sys.exit(0)

    grouped_bundles = bundle.categories.groupby('started')
    try:
        bundles_not_yet_started = grouped_bundles[False]
    except KeyError:
        bundles_not_yet_started = None

    if not bundles_not_yet_started and not force_restart:
        click.echo('{} All benchmark systems were already run. '
                   'You can force a restart.'.format(
                       click.style('WARNING', fg='yellow', bold=True)))
        sys.exit(0)

    # Start all benchmark simulations if a restart was requested. Otherwise
    # only start the ones that were not run yet.
    bundles_to_start = bundle
    if not force_restart:
        bundles_to_start = bundles_not_yet_started

    engine_cmd = get_engine_command()
    click.echo('Will start a total of {} benchmark systems.'.format(
        click.style(str(len(bundles_to_start)), bold=True)))

    for b in bundles_to_start:
        # Remove files generated by previous benchmark run
        if force_restart:
            cleanup_before_restart(b)

        b.categories['started'] = True
        os.chdir(b.abspath)
        subprocess.call([engine_cmd, 'bench.job'])

    click.echo(
        'Submitted all benchmarks. Once they are finish run `benchmark analyze` '
        'to get the benchmark results')
