#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Check that all backup are performed
"""

import os
from UserList import UserList
import datetime
import sys
import logging

logger = logging.getLogger('check_backup')

class BackupFile(object):
    """
    A single backup file.

    :param hostname: host name of the backuped host
    :type hostname: basestring
    :param name: name of the backuped component
    :type name: basestring
    :param date: when the backup happened
    :type date: :class:`datetime.datetime`
    :param compression: which compression type
    :type compression: basestring
    """

    format_type = {
        #'postgresql': 'sql'
        'pip': 'virtualenv',
        'sql': 'postgresql'
    }

    def __init__(self, hostname, name, type_name, date, compression='.gz'):
        self.hostname = hostname
        self.name = name
        self.type_name = type_name
        self.date = date
        self.compression = compression

    @property
    def filename(self):
        """
        return filename of this backup
        """
        return '-'.join((
            self.hostname, self.name, self.type_name,
            self.date.strftime("%Y-%m-%d-%H_%M_%S"),
            #self.format_type[self.type], self.compression
            self.type_name, self.compression
        ))

    def __repr__(self):
        return self.filename

    @classmethod
    def from_filename(cls, filename):
        """
        return an instance based on the original filename of the backup
        :param filename: relative filename
        :type filename: string
        :return: instance
        :rtype: :class:`BackupFile`
        """
        prefix, type_name, compression = filename.split('.')
        items = prefix.split('-')
        format_str = cls.format_type[type_name]
        if format_str not in items:
            msg = "invalid extension (%s) and type in %s" % (compression,
                                                             filename)
            logger.warning(msg)
            raise ValueError(msg)
        hostname = '-'.join(items[0:items.index(format) - 1])
        name = items[items.index(format) - 1]
        date_string = '-'.join(items[items.index(format) + 1:])
        return cls(hostname, name, type,
                   datetime.datetime.strptime(date_string, '%Y-%m-%d-%H_%M_%S'),
                   compression)

class BackupDirectory(UserList):
    """
    List of all backup in a directory

    :param dirname: root directory
    :type dirname: string
    """

    def __init__(self, dirname):
        self.dirname = dirname
        data = []
        for filename in os.listdir(self.dirname):
            absolute_filename = os.path.join(self.dirname, filename)
            if os.path.isfile(absolute_filename):
                try:
                    data.append(BackupFile.from_filename(filename))
                except (ValueError, KeyError):
                    logger.debug("Can't handle %s", absolute_filename)
            else:
                logger.debug("%s isn't a file", absolute_filename)
        UserList.__init__(self, data)

def main():
    """
    main loop
    """
    now = datetime.datetime.now()
    max_time = datetime.timedelta(hours=36)
    hosts = {}
    backup = BackupDirectory('/var/lib/backup')
    for file_obj in backup:
        try:
            host = hosts[file_obj.hostname]
        except KeyError:
            host = hosts[file_obj.hostname] = {}
        try:
            name = host[file_obj.name]
        except KeyError:
            name = host[file_obj.name] = {}
        try:
            type_obj = name[file_obj.type_name]
        except KeyError:
            type_obj = name[file_obj.type_name] = {}
        type_obj[file_obj.date] = file_obj

    number_backups = 0
    missing_backup = []
    for host in hosts:
        for name in hosts[host]:
            for type_name in hosts[host][name]:
                logger.debug("Process %s - %s type %s", host, name, type_name)
                dates = hosts[host][name][type_name].keys()
                dates.sort()
                latest = hosts[host][name][type_name][dates[-1]]
                logger.debug("Latest backup %s: %s", latest, latest.date.isoformat())
                if now - latest.date > max_time:
                    logger.debug("Expired backup %s", latest)
                    missing_backup.append('-'.join((host, type_name)))
                else:
                    logger.debug("Good backup %s", latest)
                    number_backups += 1

    if not missing_backup:
        print 'BACKUP OK - no missing backup|backups={0}'.format(
            number_backups)
        sys.exit(0)
    else:
        print 'BACKUP WARNING - {0} missing backup|backups={1}'.format(
            len(missing_backup), number_backups)
        sys.exit(1)

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR, stream=sys.stdout)
    main()
