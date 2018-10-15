#!/usr/bin/env python

# Edited by Dong Yuan Yang (dyan263)

from __future__ import with_statement

import logging

import os
import sys
import errno
import filecmp
from shutil import copyfile
import re

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn


class VersionFS(LoggingMixIn, Operations):
    def __init__(self):
        # get current working directory as place for versions tree
        self.root = os.path.join(os.getcwd(), '.versiondir')
        # check to see if the versions directory already exists
        if os.path.exists(self.root):
            print 'Version directory already exists.'
        else:
            print 'Creating version directory.'
            os.mkdir(self.root)

    # Helpers
    # =======

    def _full_path(self, partial):
        # Responsible for file names saved in .versiondir
        # Use os.listdir to find newest version
        if partial.startswith("/"):
            partial = partial[1:]
        try:
            a = int(partial[-1])
        except:
            if partial not in ["autorun.inf", ""] and partial[0] != "." and partial[-2:] != ".t":
                partial = partial + ".1"

        path = os.path.join(self.root, partial)
        return path

    def sorty(self, arr):
        def con(text): return int(text) if text.isdigit() else text

        def alphanum(key): return [con(c) for c in re.split('([0-9]+)', key)]
        return sorted(arr, key=alphanum)

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        print "access:", path, mode
        full_path = self._full_path(path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        print "chmod:", path, mode
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        print "chown:", path, uid, gid
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        print "get:", path
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                                                        'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        print "readdir:", path
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))

        unique = []
        for r in dirents:
            if r[-2:] != ".t":
                try:
                    a = int(r[-1])
                    if r[:-2] in unique:
                        pass
                    else:
                        unique.append(r[:-2])
                except:
                    unique.append(r)

        for r in unique:
            yield r

    def readlink(self, path):
        print "readlink:", path
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        print "mknod:", path, mode, dev
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        print "rmdir:", path
        full_path = self._full_path(path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
        print "mkdir:", path, mode
        return os.mkdir(self._full_path(path), mode)

    def statfs(self, path):
        print "statfs:", path
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
                                                         'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
                                                         'f_frsize', 'f_namemax'))

    def unlink(self, path):
        print "unlink:", path
        return os.unlink(self._full_path(path))

    def symlink(self, name, target):
        print "symlink:", name, target
        return os.symlink(target, self._full_path(name))

    def rename(self, old, new):
        print "rename:", old, new
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name):
        print "link:", target, name
        return os.link(self._full_path(name), self._full_path(target))

    def utimens(self, path, times=None):
        print "utimens:", path, times
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        print '** open:', path, '**'
        path = path[1:]
        temppath = path + ".t"
        dest = self._full_path(temppath)
        full_path = self._full_path(path)
        copyfile(full_path, dest)
        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
        print '** create:', path, '**'
        full_path = self._full_path(path)
        print full_path
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
        print '** read:', path, '**'
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        print '** write:', path, '**'
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        print '** truncate:', path, '**'
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        print '** flush', path, '**'
        return os.fsync(fh)

    def release(self, path, fh):
        print '** release', path, '**'
        partial = path[1:]
        full_path = self._full_path("/")

        files = os.listdir(full_path)

        versions = []
        for i in files:
            if i[:-2] == partial or i[-2:] == ".t":
                # Prev ver exists
                versions.append(i)

        versions = self.sorty(versions)
        versions.reverse()

        new_path = full_path + partial

        verVals = ["2", "3", "4", "5"]
        if len(versions) > 1:
            new = new_path + ".1"
            old = new_path + ".t"

            diff = not filecmp.cmp(new, old, shallow=False)

            if diff:
                for i in versions:

                    if i[-2:] != ".t":
                        spl = i.split(".")

                        if len(spl) == 3:
                            if spl[2] in verVals:

                                newVal = int(spl[2]) + 1

                                spl = spl[:2]
                                spl.append(str(newVal))

                                newer = ".".join(spl)

                                oldy = full_path + i
                                newly = full_path + newer
                                os.rename(oldy, newly)
                        elif len(spl) == 2:
                            if spl[1] in verVals:

                                newVal = int(spl[1]) + 1

                                spl = spl[:1]
                                spl.append(str(newVal))

                                newer = ".".join(spl)

                                oldy = full_path + i
                                newly = full_path + newer
                                os.rename(oldy, newly)
                        else:
                            print "You've entered a really messed up file name, please why are you trying to screw me over"

                newer = new_path + ".2"
                os.rename(old, newer)
            else:
                old = new_path + ".t"
                os.remove(old)
        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        print '** fsync:', path, '**'
        return self.flush(path, fh)


def main(mountpoint):
    FUSE(VersionFS(), mountpoint, nothreads=True, foreground=True)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1])
