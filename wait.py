'''
Watches for changes and executes commands in response to changes.
'''
import os
import time
import fnmatch
import subprocess
import shlex
from collections import namedtuple
from timeit import default_timer as timer

import click
from colorama import init
from colorama import Fore
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

CODE_MODIFIED = 'M'
CODE_RENAMED = 'R'
CODE_DELETED = 'D'

def _color_code(code: str) -> str:
    if code == CODE_MODIFIED:
        return Fore.GREEN
    if code == CODE_RENAMED:
        return Fore.YELLOW
    if code == CODE_DELETED:
        return Fore.RED
    return ''


# Change to the file system
Change = namedtuple('Change', ['code', 'path'])


# A collection of files that changed.
CHANGES = set()


def _print_fs_change(code: str, path: str) -> None:
    print(f'{_color_code(code)}{code}{Fore.RESET} {os.path.relpath(path)}')


class Handler(FileSystemEventHandler):
    '''File System Event Handler class.'''

    def __init__(self, patterns: str, excludes: str) -> None:
        self.patterns = patterns.split(',') if patterns else []
        self.excludes = excludes.split(',') if excludes else []

    @staticmethod
    def _matches(glob, path) -> bool:
        return fnmatch.fnmatchcase(path, glob)

    def _should_process(self, event: FileSystemEvent) -> bool:
        if event.is_directory:
            return False
        for exclude in self.excludes:
            if Handler._matches(exclude, event.src_path):
                return False
        for pattern in self.patterns:
            if Handler._matches(pattern, event.src_path):
                return True
        return False

    def on_moved(self, event: FileSystemEvent):
        if self._should_process(event):
            CHANGES.add(Change('R', event.src_path))

    def on_deleted(self, event: FileSystemEvent):
        if self._should_process(event):
            CHANGES.add(Change('D', event.src_path))

    def on_modified(self, event):
        if self._should_process(event):
            CHANGES.add(Change('M', event.src_path))

def _run_command(command: str) -> None:
    args = shlex.split(command)
    print(f"Running: {command}")
    start = timer()
    result = subprocess.run(args, capture_output=True)
    color = Fore.RED if result.returncode else Fore.GREEN
    end = timer()
    print(f'Elapsed Time: {int(end - start)} seconds.  '
          f'Exit Code: {color}{result.returncode}{Fore.RESET}')
    if result.stdout:
        print(result.stdout.decode("utf-8"))
    if result.stderr:
        print(f'{Fore.RED}{result.stderr.decode("utf-8")}{Fore.RESET}')


@click.command()
@click.option('--pattern', help='glob for files to watch')
@click.option('--exclude', default=None, help='glob for files to ignore')
@click.option('--command', help='command to run')
def wait(pattern: str, exclude: str, command):
    ''' Program entry point'''
    observer = Observer()
    observer.schedule(Handler(pattern, exclude), ".", recursive=True)
    observer.start()
    print('waiting...')
    global CHANGES  # pylint: disable=W0603
    try:
        while True:
            time.sleep(1)
            if CHANGES:
                for change in sorted(CHANGES, key=lambda x: x.path):
                    _print_fs_change(change.code, change.path)
                _run_command(command)
                CHANGES.clear()
                print('waiting...')
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    init()
    wait()  # pylint: disable=E1120
