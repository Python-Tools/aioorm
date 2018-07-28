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
        elif isinstance(row,Mapping):
            if not self.fieldnames:
                raise AttributeError("do not have header")
            else:
                row_ = [row.get(i,"") for i in self.fieldnames]
                row = (self.delimiter).join(row_)
        else:
            raise AttributeError("unsupport row type")
        try:
            await self.fh.write(row+os.linesep)
        except TypeError as te:
            #self.fh.write(row+os.linesep)
            pass
        except:
            raise

    async def writeheader(self,fieldnames=None):
        if fieldnames:
            self.fieldnames = list(fieldnames)
        if self.fieldnames:
            row = (self.delimiter).join(self.fieldnames)
            try:
                await self.fh.write(row+os.linesep)
            except TypeError as te:
                #self.fh.write(row+os.linesep)
                pass
            except:
                raise


async def aiodump_csv(query, file_or_name, loop= None,include_header=True, close_file=False,
             append=True, csv_writer=csv_writer):

    if isinstance(file_or_name, str):
        close_file=True
        #fh = await aiofiles.open(file_or_name, append and 'a' or 'w')
        fh = await aiofiles.open(file_or_name, 'w')
        writer = csv_writer(fh)
    else:
        fh = file_or_name
        if append:
            try:
                await fh.seek(0, 2)
            except TypeError as te:
                fh.seek(0, 2)
            except:
                raise

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
        try:
            await fh.close()
        except TypeError as te:
            fh.close()
        except:
            raise

    return fh
