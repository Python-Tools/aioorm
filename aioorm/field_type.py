from aioorm.abcs.field_type import FieldType

class Int(FieldType):
    mysql = "INTEGER"
    pg = "INTEGER"

class BigInt(FieldType):
    mysql = "BIGINT"
    pg = "BIGINT"

class SmallInt(FieldType):
    mysql = "SMALLINT"
    pg = "BIGINT"

class Json(FieldType):
    pass

class Array(FieldType):
    pass

class Bool(FieldType):
    pass

class Char(FieldType):
    pass

class 