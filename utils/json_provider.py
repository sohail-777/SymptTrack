from decimal import Decimal
from datetime import date, datetime
from flask.json.provider import DefaultJSONProvider


class SymptTrackJSONProvider(DefaultJSONProvider):
    """
    MySQL connector returns Decimal for DECIMAL/NUMERIC columns and
    date/datetime objects for DATE/DATETIME columns. Flask's default
    JSON encoder can't serialize these out of the box, so we teach it how,
    application-wide, instead of remembering to cast every single field.
    """

    @staticmethod
    def default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return DefaultJSONProvider.default(obj)
