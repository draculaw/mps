#!/usr/bin/env python
#
#                              Ravenbrook
#                     <http://www.ravenbrook.com/>
#
#             BRANCH.PY -- CREATE VERSION OR TASK BRANCH
#
#             Gareth Rees, Ravenbrook Limited, 2014-03-18
#
#
# 1. INTRODUCTION
#
# This script automates the process of branching the master sources
# (or customer mainline sources) of a project. It can create a version
# branch as described in [VERSION-CREATE], or a development (task)
# branch as described in [BRANCH-MERGE].


from __future__ import unicode_literals
import argparse
from collections import deque
import datetime
import os
import re
import subprocess
import sys
import p4

if sys.version_info < (3,):
    from codecs import open

class Error(Exception): pass

DEPOT = '//info.ravenbrook.com'
PROJECT_RE = r'[a-z][a-z0-9.-]*'
PROJECT_FILESPEC_RE = r'{}/project/({})/'.format(re.escape(DEPOT), PROJECT_RE)
CUSTOMER_RE = r'[a-z][a-z0-9.-]*'
PARENT_RE = r'master|custom/({})/main'.format(CUSTOMER_RE)
PARENT_FILESPEC_RE = r'{}({})(?:/|$)'.format(PROJECT_FILESPEC_RE, PARENT_RE)
TASK_RE = r'[a-zA-Z][a-zA-Z0-9._-]*'
TASK_BRANCH_RE = r'branch/\d\d\d\d-\d\d-\d\d/{}'.format(TASK_RE)
VERSION_RE = r'\d+\.\d+'
VERSION_BRANCH_RE = (r'(?:custom/({})/)?version/({})'
                     .format(CUSTOMER_RE, VERSION_RE))
CHILD_RE = r'(?:{}|{})$'.format(TASK_BRANCH_RE, VERSION_BRANCH_RE)

TASK_BRANCH_ENTRY = '''
  <tr valign="top">
    <td><code><a href="{child}/">{child}</a></code></td>
    <td><a href="https://info.ravenbrook.com/infosys/cgi/perfbrowse.cgi?@changes+{depot}/project/{project}/{child}/...">Changes</a></td>
    <td>{description}</td>
    <td>In development (<a href="https://info.ravenbrook.com/infosys/cgi/perfbrowse.cgi?@diff2+{depot}/project/{project}/{child}/...@{base}+{depot}/project/{project}/{child}/...">diffs</a>).</td>
  </tr>

'''

VERSION_BRANCH_ENTRY = '''
  <tr valign="top">
    <td> <a href="{version}/">{version}</a> </td>
    <td> None. </td>
    <td> <a href="https://info.ravenbrook.com/infosys/cgi/perfbrowse.cgi?@files+{depot}/project/{project}/{parent}/...@{changelevel}">{parent}/...@{changelevel}</a> </td>
    <td>
      {description}
    </td>
    <td>
      <a href="https://info.ravenbrook.com/infosys/cgi/perfbrowse.cgi?@describe+{base}">base</a><br />
      <a href="https://info.ravenbrook.com/infosys/cgi/perfbrowse.cgi?@changes+{depot}/project/{project}/{child}/...">changelists</a>
    </td>
  </tr>

'''

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-P', '--project',
                        help='Name of the project.')
    parser.add_argument('-p', '--parent',
                        help='Name of the parent branch.')
    parser.add_argument('-C', '--changelevel', type=int,
                        help='Changelevel at which to make the branch.')
    parser.add_argument('-d', '--description',
                        help='Description of the branch (for the branch spec).')
    parser.add_argument('-y', '--yes', action='store_true',
                        help='Yes, really make the branch.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--child',
                       help='Name of the child branch.')
    group.add_argument('-v', '--version', action='store_true',
                       help='Make the next version branch.')
    group.add_argument('-t', '--task',
                       help='Name of the task branch.')
    args = parser.parse_args(argv[1:])
    args.depot = DEPOT
    args.today = datetime.date.today().strftime('%Y-%m-%d')
    fmt = lambda s: s.format_map(vars(args))

    if not args.project:
        # Deduce project from current directory.
        filespec = next(p4.run('dirs', '.'))['dir']
        m = re.match(PROJECT_FILESPEC_RE, filespec)
        if not m:
            raise Error("Can't deduce project from current directory.")
        args.project = m.group(1)
        print(fmt("project={project}"))

    if not any(p4.run('dirs', fmt('{depot}/project/{project}'))):
        raise Error(fmt("No such project: {project}"))

    if not args.parent:
        # Deduce parent branch from current directory.
        filespec = next(p4.run('dirs', '.'))['dir']
        m = re.match(PARENT_FILESPEC_RE, filespec)
        if not m:
            raise Error("Can't deduce parent branch from {}".format(filespec))
        if args.project != m.group(1):
            raise Error("Specified project={} but current directory belongs "
                        "to project={}.".format(args.project, m.group(1)))
        args.parent = m.group(2)
        print(fmt("parent={parent}"))

    m = re.match(PARENT_RE, args.parent)
    if not m:
        raise Error("Invalid parent branch: must be master or custom/*/main.")
    args.customer = m.group(1)
    if not any(p4.run('dirs', fmt('{depot}/project/{project}/{parent}'))):
        raise Error(fmt("No such branch: {parent}"))

    if not args.changelevel:
        cmd = p4.run('changes', '-m', '1', fmt('{depot}/project/{project}/{parent}/...'))
        args.changelevel = int(next(cmd)['change'])
        print(fmt("changelevel={changelevel}"))

    if args.task:
        if not re.match(TASK_RE, args.task):
            raise Error(fmt("Invalid task: {task}"))
        args.child = fmt('branch/{today}/{task}')
        print(fmt("child={child}"))
    elif args.version:
        # Deduce version number from code/version.c.
        f = fmt('{depot}/project/{project}/{parent}/code/version.c@{changelevel}')
        m = re.search(r'^#define MPS_RELEASE "release/(\d+\.\d+)\.\d+"$',
                      p4.contents(f), re.M)
        if not m:
            raise Error("Failed to extract version from {}.".format(f))
        args.version = m.group(1)
        if args.parent == 'master':
            args.child = fmt('version/{version}')
        else:
            args.child = fmt('custom/{customer}/version/{version}')
        print(fmt("child={child}"))

    m = re.match(CHILD_RE, args.child)
    if not m:
        raise Error(fmt("Invalid child: {child}"))
    if args.customer != m.group(1):
        raise Error(fmt("Customer mismatch between {parent} and {child}."))
    args.version = m.group(2)

    if not args.description:
        args.description = fmt("Branching {parent} to {child}.")
        print(fmt("description={description}"))

    # Create the branch specification
    args.branch = fmt('{project}/{child}')
    branch_spec = dict(Branch=args.branch,
                       Description=args.description,
                       View0=fmt('{depot}/project/{project}/{parent}/... '
                                 '{depot}/project/{project}/{child}/...'))
    print("view={}".format(branch_spec['View0']))
    have_branch = False
    if any(p4.run('branches', '-E', args.branch)):
        print(fmt("Branch spec {branch} already exists: skipping."))
        have_branch = True
    elif args.yes:
        print(fmt("Creating branch spec {branch}."))
        p4.run('branch', '-i').send(branch_spec).done()
        have_branch = True
    else:
        print("--yes omitted: skipping branch creation.")

    # Populate the branch
    if any(p4.run('dirs', fmt('{depot}/project/{project}/{child}'))):
        print("Child branch already populated: skipping.")
    else:
        srcs = fmt('{depot}/project/{project}/{parent}/...@{changelevel}')
        populate_args = ['populate', '-n',
                         '-b', args.branch,
                         '-d', fmt("Branching {parent} to {child}."),
                         '-s', srcs]
        if args.yes:
            print(fmt("Populating branch {branch}..."))
            populate_args.remove('-n')
            p4.do(*populate_args)
        elif have_branch:
            print("--yes omitted: populate -n ...")
            p4.do(*populate_args)
        else:
            print("--yes omitted: skipping populate.")

    # Determine the first change on the branch
    cmd = p4.run('changes', fmt('{depot}/project/{project}/{child}/...'))
    try:
        args.base = int(deque(cmd, maxlen=1).pop()['change'])
        print(fmt("base={base}"))
    except IndexError:
        args.yes = False
        args.base = args.changelevel
        print(fmt("Branch {child} not populated: using base={base}"))

    def register(filespec, search, replace):
        args.filespec = fmt(filespec)
        if p4.contents(args.filespec).find(args.child) != -1:
            print(fmt("{filespec} already updated: skipping."))
            return
        client_spec = dict(View0=fmt('{filespec} //__CLIENT__/target'))
        with p4.temp_client(client_spec) as (conn, client_root):
            filename = os.path.join(client_root, 'target')
            conn.do('sync', filename)
            conn.do('edit', filename)
            with open(filename, encoding='utf8') as f:
                text = re.sub(search, fmt(replace), f.read(), 1)
            with open(filename, 'w', encoding='utf8') as f:
                f.write(text)
            for result in conn.run('diff'):
                if 'data' in result:
                    print(result['data'])
            if args.yes:
                conn.do('submit', '-d', fmt("Registering {child}."), filename)
            else:
                print(fmt("--yes omitted: skipping submit of {filespec}"))

    # Task branches
    if not args.version:
        register('{depot}/project/{project}/branch/index.html',
                 '(?=</table>\n)', TASK_BRANCH_ENTRY)

    # Public version branches
    elif args.version and not args.customer:
        register('{depot}/project/{project}/version/index.html',
                 '(?=</table>\n)', VERSION_BRANCH_ENTRY)

        # Create git-fusion client spec
        have_git_branch = False
        args.git_client = fmt('git-fusion-{project}-version-{version}')
        if any(p4.run('clients', '-E', args.git_client)):
            print(fmt("client {git_client} already exists: skipping."))
            have_git_branch = True
        elif args.yes:
            client_spec = dict(
                Client=args.git_client,
                Description=fmt("Git-fusion client for syncing {project} "
                                "version {version}"),
                Root=fmt('/home/git-fusion/.git-fusion/views/'
                         '{project}-version-{version}/p4'),
                View0=fmt('{depot}/project/{project}/{child}/... '
                          '//{git_client}/...'))
            print(fmt("Creating client spec {git_client}"))
            p4.run('client', '-i').send(client_spec).done()
            have_git_branch = True
        else:
            print(fmt("--yes omitted: skipping {git_client}"))

        # Update table of pushes
        register('{depot}/infosys/robots/git-fusion/etc/pushes',
                 r"\n*\Z",
                 '\n{project}-version-{version}\t'
                 'git@github.com:Ravenbrook/mps-temporary.git\t'
                 '{child}\n')


if __name__ == '__main__':
    main(sys.argv)


# A. REFERENCES
#
# [BRANCH-MERGE] Gareth Rees; "Memory Pool System branching and
# merging procedures"; Ravenbrook Limited; 2014-01-09.
# <https://info.ravenbrook.com/project/mps/master/procedure/branch-merge>
#
# [VERSION-CREATE] Richard Kistruck; "Memory Pool System Version
# Create Procedure"; Ravenbrook Limited; 2008-10-29.
# <https://info.ravenbrook.com/project/mps/master/procedure/version-create>
#
#
# B. DOCUMENT HISTORY
#
# 2014-03-18 GDR Created based on [BRANCH-MERGE] and [VERSION-CREATE].
#
#
# C. COPYRIGHT AND LICENCE
#
# Copyright (c) 2014 Ravenbrook Ltd.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
# $Id$
