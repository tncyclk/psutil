#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Try to guess and apply appropriate labels to GitHub's issues and PRs.
"""

from __future__ import print_function
import argparse
import os
import sys
import textwrap

from github import Github

from psutil._common import hilite


ROOT_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), '..', '..'))
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')

USER = "giampaolo"
PROJECT = "psutil"

OS_LABELS = [
    "linux", "windows", "macos", "freebsd", "openbsd", "netbsd", "openbsd",
    "bsd", "sunos", "unix", "wsl", "aix", "cygwin",
]

ILLOGICAL_PAIRS = [
    ('bug', 'enhancement'),
    ('doc', 'tests'),
    ('scripts', 'doc'),
    ('scripts', 'tests'),
    ('bsd', 'freebsd'),
    ('bsd', 'openbsd'),
    ('bsd', 'netbsd'),
]

LABELS_MAP = {
    # platforms
    "linux": [
        "linux", "ubuntu", "redhat", "mint", "centos", "red hat", "archlinux",
        "debian", "alpine", "gentoo", "fedora", "slackware", "suse", "RHEL",
        "opensuse", "manylinux", "apt ", "apt-", "rpm", "yum", "kali",
        "/sys/class", "/proc/net", "/proc/disk", "/proc/smaps",
        "/proc/vmstat",
    ],
    "windows": [
        "windows", "win32", "WinError", "WindowsError", "win10", "win7",
        "win ", "mingw", "msys", "studio", "microsoft", "make.bat",
        "CloseHandle", "GetLastError", "NtQuery", "DLL", "MSVC", "TCHAR",
        "WCHAR", ".bat", "OpenProcess", "TerminateProcess", "appveyor",
    ],
    "macos": [
        "macos", "mac ", "osx", "os x", "mojave", "sierra", "capitan",
        "yosemite", "catalina", "xcode", "darwin", "dylib",
    ],
    "aix": ["aix"],
    "cygwin": ["cygwin"],
    "freebsd": ["freebsd"],
    "netbsd": ["netbsd"],
    "openbsd": ["openbsd"],
    "sunos": ["sunos", "solaris"],
    "wsl": ["wsl"],
    "unix": [
        "psposix", "_psutil_posix", "waitpid", "statvfs", "/dev/tty",
        "/dev/pts",
    ],
    "pypy": ["pypy"],
    # types
    "enhancement": ["enhancement"],
    "memleak": ["memory leak", "leaks memory", "memleak", "mem leak"],
    "api": ["idea", "proposal", "api", "feature"],
    "performance": ["performance", "speedup", "speed up", "slow", "fast"],
    "wheels": ["wheel", "wheels"],
    "scripts": [
        "example script", "examples script", "example dir", "scripts/",
    ],
    # bug
    "bug": [
        "fail", "can't execute", "can't install", "cannot execute",
        "cannot install", "install error", "crash", "critical",
    ],
    # doc
    "doc": [
        "doc ", "document ", "documentation", "readthedocs", "pythonhosted",
        "HISTORY", "README", "dev guide", "devguide", "sphinx", "docfix",
        "index.rst",
    ],
    # tests
    "tests": [
        " test ", "tests", "travis", "coverage", "cirrus", "appveyor",
        "continuous integration", "unittest", "pytest", "unit test",
    ],
    # critical errors
    "priority-high": [
        "WinError", "WindowsError", "RuntimeError", "ZeroDivisionError",
        "SystemError", "MemoryError", "core dumped",
        "segfault", "segmentation fault",
    ],
}

LABELS_MAP['scripts'].extend(
    [x for x in os.listdir(SCRIPTS_DIR) if x.endswith('.py')])


def warn(msg):
    print(hilite(">>> WARN: %s" % msg, color="red", bold=1), file=sys.stderr)


class Getter:

    def __init__(self, token):
        g = Github(token)
        self._repo = g.get_repo("%s/%s" % (USER, PROJECT))

    def _paginate(self, issues):
        tot = issues.totalCount
        for i, issue in enumerate(issues, 1):
            if i % 50 == 0:
                print("%s/%s" % (i, tot))
            yield issue

    @property
    def repo(self):
        return self._repo

    def get_issues(self, status):
        issues = self.repo.get_issues(state=status)
        print("start processing %s %r issues" % (issues.totalCount, status))
        for issue in self._paginate(issues):
            yield issue

    def get_pulls(self, status):
        prs = self.repo.get_pulls(state=status)
        print("start processing %s %r PRs" % (prs.totalCount, status))
        for pr in self._paginate(prs):
            yield pr


class Setter:

    def __init__(self, repo, do_write):
        self.repo = repo
        self.do_write = do_write
        self.avail_labels = sorted([x.name for x in self.repo.get_labels()])

    # --- utils

    def add_label(self, issue, label):
        assert label in self.avail_labels, (label, self.avail_labels)
        if not self.has_label(issue, label):
            type_ = "PR:" if self.is_pr(issue) else "issue:"
            assigned = ', '.join([x.name for x in issue.labels])
            print(textwrap.dedent("""\
                %-10s     %s: %s
                assigned:      %s
                new:           %s""" % (
                type_,
                hilite(issue.number, color='brown'),
                hilite(issue.title, color='brown'),
                assigned,
                hilite(label, 'green', bold=1),
            )))
            if self.do_write:
                issue.add_to_labels(label)

    def has_label(self, issue, label):
        assigned = [x.name for x in issue.labels]
        return label in assigned

    def has_os_label(self, issue):
        labels = set([x.name for x in issue.labels])
        for label in OS_LABELS:
            if label in labels:
                return True
        return False

    def is_pr(self, issue):
        return 'PullRequest' in issue.__module__

    def should_add(self, issue, label):
        for left, right in ILLOGICAL_PAIRS:
            if label == left and self.has_label(issue, right):
                return False
        return not self.has_label(issue, label)

    def _print_text_match(self, text, keyword):
        # print part of matched text
        text = text.lower()
        keyword = keyword.lower()
        shift = 20
        part = text.rpartition(keyword)
        ss = part[0][-shift:] + hilite(keyword, 'brown') + part[2][:shift]
        ss = ss.replace('\n', '\t')
        print("match:         %s\n" % ss.strip())

    # --- setters

    def _guess_from_text(self, issue, text):
        for label, keywords in LABELS_MAP.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    # we have a match
                    if self.should_add(issue, label):
                        yield (label, keyword)

    def guess_from_title(self, issue):
        for label, keyword in self._guess_from_text(issue, issue.title):
            self.add_label(issue, label)
            self._print_text_match(issue.title, keyword)

    def guess_from_body(self, issue):
        ls = list(self._guess_from_text(issue, issue.body))
        has_multi_os = len((set([x[0] for x in ls if x[0] in OS_LABELS]))) > 1
        for label, keyword in ls:
            if label in ('tests', 'api', 'performance'):
                continue
            if label in OS_LABELS:
                if self.has_os_label(issue) or has_multi_os:
                    continue
                if self.has_label(issue, 'scripts'):
                    continue
                self.add_label(issue, label)
                self._print_text_match(issue.body, keyword)

    # def guess_from_files(self, issue):
    #     files = sorted([x.filename for x in pr.get_files()])
    #     # pure doc change
    #     if files == ['docs/index.rst']:
    #         self.add_label(pr, 'doc')

    def logical_adjust(self, issue):
        # labels that don't make sense together
        for left, right in ILLOGICAL_PAIRS:
            if self.has_label(issue, left) and self.has_label(issue, right):
                warn("illogical pair %r + %r for #%s: %s)" % (
                    left, right, issue.number, issue.title))

        # assign generic BSD
        if not self.has_os_label(issue) and 'bsd' in issue.title.lower():
            self.add_label(issue, 'bsd')

    # def printers(self, issue)
    #     # no "enhancement" nor "bug"
    #     if 'bug' not in labels and 'enhancement' not in labels and \
    #             "doc" not in labels:
    #         if 'add support' in title or \
    #                 'refactoring' in title or \
    #                 'enhancement' in title or \
    #                 'adds support' in title:
    #             self.add_label(issue, 'enhancement')
    #         elif 'fix' in title or \
    #                 'fixes' in title or \
    #                 'is incorrect' in title or \
    #                 'is wrong' in title:
    #             self.add_label(issue, 'bug')

    #     if not self.has_os_label(issue) and not \
    #             self.has_label(issue, 'doc') and not \
    #             self.has_label(issue, 'test') and not \
    #             self.has_label(issue, 'scripts'):
    #         print(issue)

    #     not "bug" nor "enhancement"
    #     if not self.has_label(issue, 'enhancement') and not \
    #             self.has_label(issue, 'bug'):
    #         if 'support' in title and 'broken' not in title:
    #             self.add_label(issue, 'enhancement')
    #         elif 'improve' in title or 'refactor' in title:
    #             self.add_label(issue, 'enhancement')
    #         else:
    #             print(issue)


def main():
    # parser
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenfile', required=False,
                        default='~/.github.token',
                        help="a path to file contaning the GH token")
    parser.add_argument('-w', '--write', required=False, default=False,
                        action='store_true',
                        help="do the actual changes (default: dryrun)")
    parser.add_argument('-b', '--body', required=False, default=False,
                        action='store_true',
                        help="inspect text body")
    parser.add_argument('-p', '--pulls', required=False, default=False,
                        action='store_true',
                        help="only process PRs (not issues)")
    parser.add_argument('-s', '--status', required=False, default='open',
                        help="issue status (open*, close, all)")
    parser.add_argument('-n', '--number', required=False,
                        metavar='int', type=int,
                        help="only process N items instead of all")
    args = parser.parse_args()
    with open(os.path.expanduser(args.tokenfile)) as f:
        token = f.read().strip()

    # run
    getter = Getter(token)
    setter = Setter(getter.repo, args.write)
    if args.pulls:
        issues = getter.get_pulls(args.status)
    else:
        issues = getter.get_issues(args.status)
    for idx, issue in enumerate(issues, 1):
        if args.number and idx >= args.number:
            break
        setter.guess_from_title(issue)
        setter.logical_adjust(issue)
        # we want this to be the very last
        if args.body and issue.body:
            setter.guess_from_body(issue)
    print("processed %s issues" % idx)


if __name__ == '__main__':
    main()
