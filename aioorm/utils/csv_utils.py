from functools import partial
from collections import Collection, Mapping
import asyncio
import aiofiles
import os
from peewee import Func
from peewee import Field

class csv_writer:

    def __init__(self,fh,fieldnames=None,delimiter=','):
        self.fh = fh
        self.delimiter = delimiter
        if fieldnames:
            self.fieldnames = list(fieldnames)
        else:
            self.fieldnames = None

    async def writerow(self,row):
        if isinstance(row,Collection):
            row = (self.delimiter).join([str(i) for i in row])
            await self.fh.write(row+os.linesep)

        if isinstance(row,Mapping):
            if not self.fieldnames:
                raise AttributeError("do not have header")
            else:
                row_ = [row.get(i,"") for i in self.fieldnames]
                row = (self.delimiter).join(row_)
                await self.fh.write(row+os.linesep)

    async def writeheader(self,fieldnames=None):
        if fieldnames:
            self.fieldnames = list(fieldnames)
        if self.fieldnames:
            row = (self.delimiter).join(self.fieldnames)
            await self.fh.write(row+os.linesep)


async def aiodump_csv(query, file_or_name, loop= None,include_header=True, close_file=True,
             append=True, csv_writer=csv_writer):

    if isinstance(file_or_name, str):
        fh = await aiofiles.open(file_or_name, append and 'a' or 'w')
        writer = csv_writer(fh)
    else:
        fh = file_or_name
        if append:
            await fh.seek(0, 2)
        writer = csv_writer(fh)

    if include_header:
        header = []
        for idx, node in enumerate(query._select):
            if node._alias:
                header.append(node._alias)
            elif isinstance(node, (Field, Func)):
                header.append(node.name)
            else:
                header.append('col_%s' % idx)
        await writer.writeheader(header)

    for row in (await query.tuples()):

        await writer.writerow(row)

    if close_file:
        await fh.close()

    return fh
