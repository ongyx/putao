# coding: utf8


class PutaoError(Exception):
    pass


class LyricError(PutaoError):
    pass


class OverlapError(PutaoError):
    pass
