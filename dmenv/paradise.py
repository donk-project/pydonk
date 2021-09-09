import os
from pathlib import Path

if os.name == 'posix':
    PARADISE_ROOT = Path(os.path.expanduser(
        '~/ExternalRepos/third_party/Paradise/'))
else:
    PARADISE_ROOT = Path('D:/ExternalRepos/third_party/Paradise/')
