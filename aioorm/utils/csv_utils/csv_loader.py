import aiofiles
from io import StringIO
from peewee import *
from peewee import Database
import csv
import _csv
class Reader:

    def __init__(self,fh,delimiter=',',**kws):
        self.fh = fh
        self.delimiter = delimiter
        self.kws=dict(**kws)

    def __aiter__(self):
        return self

    async def __anext__(self):
        line = await self.fh.readline()
        if line:
            row = line.strip().split(self.delimiter)
            return row
        else:
            raise StopAsyncIteration


class Get_Reader:

    def __init__(self, file_or_name, **reader_kwargs):
        self.file_or_name=file_or_name
        self.reader_kwargs = dict(**reader_kwargs)
        self.is_file = False
        self.is_io = False
    async def __aenter__(self):

        if isinstance(self.file_or_name, str):
            self.fh = await aiofiles.open(self.file_or_name, 'r')
        elif isinstance(self.file_or_name, StringIO):
            self.fh = self.file_or_name
            self.fh.seek(0)
            self.is_io=True
        else:
            self.fh = self.file_or_name
            await self.fh.seek(0)
            self.is_file = True

        if self.is_io:
            reader = csv.reader(self.fh, **self.reader_kwargs)
        else:
            reader = Reader(self.fh, **self.reader_kwargs)
        return reader
    async def __aexit__(self, exc_type, exc, tb):
        if self.is_file:
            await self.fh.close()
        if self.is_io:
            self.fh.close()

class _CSVReader():

    def get_reader(self, file_or_name, **reader_kwargs):
        return Get_Reader(file_or_name, **reader_kwargs)

def convert_field(field_class, **field_kwargs):
    def decorator(fn):
        fn.field = lambda: field_class(**field_kwargs)
        return fn
    return decorator

class RowConverter(_CSVReader):
    """
    Simple introspection utility to convert a CSV file into a list of headers
    and column types.
    :param database: a peewee Database object.
    :param bool has_header: whether the first row of CSV is a header row.
    :param int sample_size: number of rows to introspect
    """
    date_formats = [
        '%Y-%m-%d',
        '%m/%d/%Y']

    datetime_formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f']

    def __init__(self, database, has_header=True, sample_size=10):
        self.database = database
        self.has_header = has_header
        self.sample_size = sample_size

    def matches_date(self, value, formats):
        for fmt in formats:
            try:
                datetime.datetime.strptime(value, fmt)
            except ValueError:
                pass
            else:
                return True

    @convert_field(IntegerField, default=0)
    def is_integer(self, value):
        return value.isdigit()

    @convert_field(FloatField, default=0)
    def is_float(self, value):
        try:
            float(value)
        except (ValueError, TypeError):
            pass
        else:
            return True

    @convert_field(DateTimeField, null=True)
    def is_datetime(self, value):
        return self.matches_date(value, self.datetime_formats)

    @convert_field(DateField, null=True)
    def is_date(self, value):
        return self.matches_date(value, self.date_formats)

    @convert_field(BareField, default='')
    def default(self, value):
        return True

    async def extract_rows(self, file_or_name, **reader_kwargs):
        """
        Extract `self.sample_size` rows from the CSV file and analyze their
        data-types.
        :param str file_or_name: A string filename or a file handle.
        :param reader_kwargs: Arbitrary parameters to pass to the CSV reader.
        :returns: A 2-tuple containing a list of headers and list of rows
                  read from the CSV file.
        """
        rows = []
        rows_to_read = self.sample_size
        async with self.get_reader(file_or_name, **reader_kwargs) as reader:
            if self.has_header:
                rows_to_read += 1
            for i in range(self.sample_size):
                try:
                    row = await reader.__anext__()
                except AttributeError as te:
                    row = next(reader)
                except:
                    raise
                rows.append(row)

        if self.has_header:
            header, rows = rows[0], rows[1:]
        else:
            header = ['field_%d' % i for i in range(len(rows[0]))]
        return header, rows

    def get_checks(self):
        """Return a list of functions to use when testing values."""
        return [
            self.is_date,
            self.is_datetime,
            self.is_integer,
            self.is_float,
            self.default]

    def analyze(self, rows):
        """
        Analyze the given rows and try to determine the type of value stored.
        :param list rows: A list-of-lists containing one or more rows from a
                          csv file.
        :returns: A list of peewee Field objects for each column in the CSV.
        """
        transposed = zip(*rows)
        checks = self.get_checks()
        column_types = []
        for i, column in enumerate(transposed):
            # Remove any empty values.
            col_vals = [val for val in column if val != '']
            for check in checks:
                results = set(check(val) for val in col_vals)
                if all(results):
                    column_types.append(check.field())
                    break

        return column_types


class Loader(_CSVReader):
    """
    Load the contents of a CSV file into a database and return a model class
    suitable for working with the CSV data.
    :param db_or_model: a peewee Database instance or a Model class.
    :param file_or_name: the filename of the CSV file *or* a file handle.
    :param list fields: A list of peewee Field() instances appropriate to
        the values in the CSV file.
    :param list field_names: A list of names to use for the fields.
    :param bool has_header: Whether the first row of the CSV file is a header.
    :param int sample_size: Number of rows to introspect if fields are not
        defined.
    :param converter: A RowConverter instance to use.
    :param str db_table: Name of table to store data in (if not specified, the
        table name will be derived from the CSV filename).
    :param reader_kwargs: Arbitrary arguments to pass to the CSV reader.
    """
    def __init__(self, db_or_model, file_or_name, fields=None,
                 field_names=None, has_header=True, sample_size=10,
                 converter=None, db_table=None, pk_in_csv=False,
                 **reader_kwargs):
        self.file_or_name = file_or_name
        self.fields = fields
        self.field_names = field_names
        self.has_header = has_header
        self.sample_size = sample_size
        self.converter = converter
        self.reader_kwargs = reader_kwargs

        if isinstance(file_or_name, str):
            self.filename = file_or_name
        elif isinstance(file_or_name, StringIO):
            self.filename = 'data.csv'
        else:
            self.filename = file_or_name._file.name

        if isinstance(db_or_model, Database):
            self.database = db_or_model
            self.model = None
            self.db_table = (
                db_table or
                os.path.splitext(os.path.basename(self.filename))[0])
        else:
            self.model = db_or_model
            self.database = self.model._meta.database
            self.db_table = self.model._meta.db_table
            self.fields = self.model._meta.sorted_fields
            self.field_names = self.model._meta.sorted_field_names
            # If using an auto-incrementing primary key, ignore it unless we
            # are told the primary key is included in the CSV.
            if self.model._meta.auto_increment and not pk_in_csv:
                self.fields = self.fields[1:]
                self.field_names = self.field_names[1:]

    def clean_field_name(self, s):
        return re.sub('[^a-z0-9]+', '_', s.lower())

    def get_converter(self):
        return self.converter or RowConverter(
            self.database,
            has_header=self.has_header,
            sample_size=self.sample_size)

    def analyze_csv(self):
        converter = self.get_converter()
        header, rows = converter.extract_rows(
            self.file_or_name,
            **self.reader_kwargs)
        if rows:
            self.fields = converter.analyze(rows)
        else:
            self.fields = [converter.default.field() for _ in header]
        if not self.field_names:
            self.field_names = [self.clean_field_name(col) for col in  header]

    def get_model_class(self, field_names, fields):
        if self.model:
            return self.model
        attrs = dict(zip(field_names, fields))
        if 'id' not in attrs:
            attrs['_auto_pk'] = PrimaryKeyField()
        elif isinstance(attrs['id'], IntegerField):
            attrs['id'] = PrimaryKeyField()
        klass = type(self.db_table.title(), (Model,), attrs)
        klass._meta.database = self.database
        klass._meta.db_table = self.db_table
        return klass

    async def load(self):
        if not self.fields:
            self.analyze_csv()
        if not self.field_names and not self.has_header:
            self.field_names = [
                'field_%d' % i for i in range(len(self.fields))]

        #reader_obj = self.get_reader(self.file_or_name, **self.reader_kwargs)
        async with self.get_reader(self.file_or_name, **self.reader_kwargs) as reader:
            if not self.field_names:
                try:
                    row = await reader.__anext__()
                except AttributeError as te:
                    row = next(reader)
                except:
                    raise
                self.field_names = [self.clean_field_name(col) for col in row]
            elif self.has_header:
                try:
                    row = await reader.__anext__()
                except AttributeError as te:
                    row = next(reader)
                except:
                    raise


            ModelClass = self.get_model_class(self.field_names, self.fields)

            #with self.database.transaction():
            await ModelClass.create_table(True)
            inserts = []
            if isinstance(reader,Reader):
                async for row in reader:
                    if not row:
                        continue
                    insert = {}
                    for field_name, value in zip(self.field_names, row):
                        if value:
                            insert[field_name] = value
                    if insert:
                        inserts.append(insert)
            else:
                for row in reader:
                    if not row:
                        continue
                    insert = {}
                    for field_name, value in zip(self.field_names, row):
                        if value:
                            insert[field_name] = value
                    if insert:
                        inserts.append(insert)
            await ModelClass.insert_many(inserts).execute()

        return ModelClass

async def aioload_csv(db_or_model, file_or_name, fields=None, field_names=None,
             has_header=True, sample_size=10, converter=None,
             db_table=None, pk_in_csv=False, **reader_kwargs):
    loader = Loader(
        db_or_model=db_or_model,
        file_or_name=file_or_name,
        fields=fields,
        field_names=field_names,
        has_header=has_header,
        sample_size=sample_size,
        converter=converter,
        db_table=db_table,
        pk_in_csv=pk_in_csv,
        **reader_kwargs)
    return await loader.load()

aioload_csv.__doc__ = Loader.__doc__
