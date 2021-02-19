#!/usr/bin/env python3

# Copyright (c) 2021, Jörn Bethune
# This source code is licensed under the BSD 3-Clause License

"""
======================================
Annovate - Annotate scientific results
======================================

We produce many files in science. Most of these files are not the final result,
but intermediate results that we generate from trying different parameters or
approaches. Sometimes we have to go back to these results and it's not always
clear which parameters where used and which input files were part of the
process. This program tries to make it convenient to log that information while
it is still recent.

Usage:

.. code-block:: shell

    annovate.py set results.csv "description=Cleaned up data" \\
                                "origin=StarGaze Lab"

    annovate.py set plot.png \\
                "description=Primary intensities with infrared correction" \\
                "origin=./run_infrared_correction -a 8.2" \\
                infra_correction=8.2

    annovate get plot.png infra_correction # get 8.2

    annovate list . # get all descriptions for the current directory

"""

from typing import Dict, List, Optional
from argparse import ArgumentParser, Namespace
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from sys import stderr, exit

META_FILE_NAME = ".annovate"

Filename = str


@dataclass
class MetaInformation:
    """
    A collection of key-value pairs that is associated with a file or directory
    at a given time.
    """
    filename: Filename
    time: datetime
    properties: dict[str, str]


@dataclass
class DatedValue:
    """
    Dataclass to store a value and a time when that value was assigned.
    """
    value: str
    time: datetime


class MetaFile:
    """
    Read and write metadata from Annovate files. Reading and creation happens
    automatically when a MetaFile object is created. Writing happens
    explicitly, when `add_information` called followed by `write`.
    """

    def __init__(self, path: Path):
        """
        Create a new MetaFile object. This will also create a meta file on disk
        if it doesn't already exist

        :param path: Path to the metadata file. All entries in the file refer
        to files in teh same directory as the medatata file
        """
        self.path = path
        data: Dict[Filename, Dict[str, DatedValue]] = {}
        if path.exists():
            current_dict = None
            file_time = None
            with open(path) as f:
                for line in f:
                    if line.startswith('@'):
                        file_key, time = line[1:].rstrip('\n').split('@')
                        current_dict = data.setdefault(file_key, {})
                        file_time = datetime.fromisoformat(time)
                    else:
                        key, value = line.rstrip('\n').split('=', maxsplit=1)
                        if current_dict is None or file_time is None:
                            raise ValueError('Meta file is not '
                                             'starting with a @')
                        else:
                            current_dict[key] = DatedValue(value, file_time)
        self.data = data
        self.new_information: List[MetaInformation] = []

    def write(self) -> None:
        """
        Write any new information to disk
        """
        if self.new_information:
            with open(self.path, 'a') as out:
                for info in self.new_information:
                    time_str = info.time.isoformat()
                    out.write(f'@{info.filename}@{time_str}\n')
                    for key, value in info.properties.items():
                        out.write(f'{key}={value}\n')
        self.new_information = []

    def add_information(self, info: MetaInformation) -> None:
        """
        Add additional metadata.

        This metadata still needs to be written to disk.

        :param info: MetaInformation about a single file
        """
        self.new_information.append(info)
        data = self.data.setdefault(info.filename, {})
        for key, value in info.properties.items():
            data[key] = DatedValue(value, info.time)

    def get(self, filename: Filename, key: str) -> Optional[DatedValue]:
        """
        Get a value from metadata, if it exists.

        :param filename: File or directory that should be queried
        :param key: Name of the parameter that should be looked up
        """
        file_data = self.data.get(filename)
        return file_data.get(key) if file_data is not None else None

    def files(self) -> List[str]:
        """
        Get a list of files for which we have metadata
        """
        return list(self.data)


def derive_meta_file_path(obj_path: Path) -> Path:
    """
    Given the path to a file or directory, return the location where its
    metadata should be stored.
    """
    path = obj_path.resolve()
    if path.is_dir():
        return path / META_FILE_NAME
    else:
        return path.parent / META_FILE_NAME


def main(args: Namespace) -> None:
    """
    Main program.

    :param args: ArgumentParser arguments.
    """
    obj = Path(args.object)
    meta_file_path = derive_meta_file_path(obj)
    if args.action == 'get':
        meta = MetaFile(meta_file_path)
        for item in args.items:
            value = meta.get(obj.name, item) or args.default
            print(value)

    elif args.action == 'set':
        meta = MetaFile(meta_file_path)
        now = datetime.now()
        properties = dict(attr_spec.split('=', maxsplit=1)
                          for attr_spec in args.items)
        meta.add_information(MetaInformation(obj.name, now, properties))
        meta.write()

    elif args.action == 'list':
        meta = MetaFile(meta_file_path)
        for file in meta.files():
            description = meta.get(file, 'description')
            if description is None:
                value = args.default
            else:
                value = description.value
            print(f'{file}\t{value}')

    else:
        stderr.write(f'Unsupported action: {args.action}\n')
        exit(2)


if __name__ == '__main__':
    parser = ArgumentParser(description='Annotate files with metadata')
    parser.add_argument('--default',
                        default='',
                        help='A default value when one is needed')
    parser.add_argument('action',
                        help='Action can be one of the following: '
                             'get, set, list')
    parser.add_argument('object',
                        help='A path to a file or directory')
    parser.add_argument('items',
                        nargs='*',
                        help='the keys or "key=value" pairs for a subcommand')
    main(parser.parse_args())
