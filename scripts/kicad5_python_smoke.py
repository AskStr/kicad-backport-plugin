import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import legacy.kicad_backport_action as action  # noqa: E402


def main():
    launcher = os.path.join(action.plugin_root(), 'plugin', 'plugin.py')
    if not os.path.exists(launcher):
        raise RuntimeError('plugin/plugin.py was not found')
    last_error = None
    for command in action._python3_candidates():
        try:
            output = subprocess.check_output(command + [launcher, '--list-targets'])
            if not isinstance(output, str):
                output = output.decode('utf-8')
            if '10.0' in output and '7.0' in output and '5.0' in output:
                sys.stdout.write(output)
                print('kicad5 python smoke ok')
                return 0
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise RuntimeError('external Python 3 launch failed: {0}'.format(last_error))
    raise RuntimeError('external Python 3 launch failed')


if __name__ == '__main__':
    raise SystemExit(main())
