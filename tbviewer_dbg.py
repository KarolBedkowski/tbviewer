#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Start application in debug mode.

Copyright (c) Karol Będkowski, 2015-2020

This file is part of tbviewer
Licence: GPLv2+
"""

__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015-2020"
__version__ = "2015-05-10"

import sys
if '--profile' not in sys.argv:
    sys.argv.append('-d')


def _profile():
    """Profile app."""
    import cProfile
    print('Profiling....')
    cProfile.run('from tbviewer.main import run_viewer; run_viewer()',
                 'profile.tmp')
    import pstats
    import time
    with open('profile_result_%d.txt' % int(time.time()), 'w') as out:
        stat = pstats.Stats('profile.tmp', stream=out)
        stat.sort_stats('cumulative').print_stats('tbviewer', 50)
        out.write('\n\n----------------------------\n\n')
        stat.sort_stats('time').print_stats('tbviewer', 50)
        out.write('\n\n============================\n\n')
        stat.sort_stats('cumulative').print_stats('', 50)
        out.write('\n\n----------------------------\n\n')
        stat.sort_stats('time').print_stats('', 50)


def _memprofile():
    """Mem profile app."""
    from tbviewer import main
    main.run_viewer()
    import gc
    gc.collect()
    while gc.collect() > 0:
        print('collect')

    import objgraph
    objgraph.show_most_common_types(20)

    import pdb
    pdb.set_trace()


if __name__ == "__main__":
    if '--profile' in sys.argv:
        sys.argv.remove('--profile')
        _profile()
    elif '--memprofile' in sys.argv:
        sys.argv.remove('--memprofile')
        _memprofile()
    elif '--version' in sys.argv:
        from tbviewer import version
        print(version.INFO)
    else:
        from tbviewer import main
        main.run_viewer()
