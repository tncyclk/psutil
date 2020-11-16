#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Check for certain keywords in GitHub's issue's titles and apply the
appropriate labels.
"""

from __future__ import print_function
import argparse
import os

from github import Github


USER = "giampaolo"
PROJECT = "psutil"
OS_LABELS = ["linux", "windows", "macos", "freebsd", "openbsd", "netbsd",
             "openbsd", "sunos", "unix", "wsl", "aix", "cygwin"]
TOKEN = ""
DRYRUN = False


def add_label(issue, label):
    print("adding label %r to '#%r: %s'" % (
        label, issue.number, issue.title))
    if not DRYRUN:
        issue.add_to_labels(label)


def set_labels_from_title(issue):
    def check_for(issue, label, keywords):
        for key in keywords:
            if key in issue.title.lower():
                issue_labels = [x.name for x in issue.labels]
                if label not in issue_labels:
                    add_label(issue, label)

    # platforms
    check_for(
        issue, "linux",
        ["linux", "ubuntu", "redhat", "mint", "centos", "red hat", "archlinux",
         "debian", "alpine", "gentoo", "fedora", "slackware", "suse", "RHEL",
         "opensuse", "manylinux", "apt", "rpm", "yum", "/sys/class",
         "/sys/block", "/proc/net", "/proc/disk", "/proc/smaps"])
    check_for(
        issue, "windows",
        ["windows", "win32", "WinError", "WindowsError", "win10", "win7",
         "win", "mingw", "msys", "studio", "microsoft", "make.bat",
         "CloseHandle", "GetLastError", "NtQuery", "DLL", "MSVC", "TCHAR",
         "WCHAR", ".bat", "OpenProcess", "TerminateProcess",
         "appveyor"])
    check_for(
        issue, "macos",
        ["macos", "mac ", "osx", "os x", "mojave", "sierra", "capitan",
         "yosemite", "catalina", "xcode", "darwin"])
    check_for(issue, "aix", ["aix"])
    check_for(issue, "cygwin", ["cygwin"])
    check_for(issue, "freebsd", ["freebsd"])
    check_for(issue, "netbsd", ["netbsd"])
    check_for(issue, "openbsd", ["openbsd"])
    check_for(issue, "sunos", ["sunos", "solaris"])
    check_for(issue, "unix", ["makefile"])
    check_for(issue, "wsl", ["wsl"])
    check_for(issue, "pypy", ["pypy"])
    check_for(
        issue, "unix",
        ["psposix", "waitpid", "statvfs", "/dev/tty", "/dev/pts"])

    # types
    check_for(issue, "bug", ["bug", "raise", "exception", "traceback"])
    check_for(issue, "enhancement", ["enhancement"])
    check_for(
        issue, "memleak",
        ["memory leak", "leaks memory", "memleak", "mem leak"])

    # doc
    check_for(
        issue, "doc",
        ["doc ", "document ", "documentation", "readthedocs", "pythonhosted",
         "HISTORY.rst", "README", "dev guide", "devguide", "sphinx"])
    check_for(issue, "api", ["idea", "proposal", "api", "feature"])
    check_for(issue, "performance", ["performance", "speedup", "slow", "fast"])

    # tests
    check_for(
        issue, "tests",
        ["test", "tests", "travis", "coverage", "cirrus", "appveyor",
         "continuous integration", "unittest", "pytest"])
    check_for(issue, "wheels", ["wheel", "wheels"])

    # critical errors
    check_for(
        issue, "priority-high",
        ["WinError", "WindowsError", "RuntimeError", "segfault",
         "segmentation fault", "ZeroDivisionError", "SystemError"])


class Repository:

    def __init__(self, token):
        g = Github(token)
        self.repo = g.get_repo("%s/%s" % (USER, PROJECT))

    def _paginate(self, issues):
        tot = issues.totalCount
        for i, issue in enumerate(issues, 1):
            if i % 50 == 0:
                print("%s/%s" % (i, tot))
            yield issue

    def get_issues(self, status):
        issues = self.repo.get_issues(state=status)
        print("start processing %s %r issues" % (issues.totalCount, status))
        for issue in self._paginate(issues):
            yield issue


def main():
    global DRYRUN

    # parser
    parser = argparse.ArgumentParser(description='GitHub issue labeler')
    parser.add_argument('--tokenfile', required=False,
                        default='~/.github.token',
                        help="a path to file contaning the GH token")
    parser.add_argument('-d', '--dryrun', required=False, default=False,
                        action='store_true',
                        help="don't make actual changes")
    parser.add_argument('--status', required=False, default='open',
                        help="issue status (open, close, all)")
    args = parser.parse_args()

    # set globals
    with open(os.path.expanduser(args.tokenfile)) as f:
        token = f.read().strip()
    DRYRUN = args.dryrun

    # run
    repo = Repository(token)
    for issue in repo.get_issues(args.status):
        set_labels_from_title(issue)


if __name__ == '__main__':
    main()
