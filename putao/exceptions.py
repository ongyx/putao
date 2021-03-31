# coding: utf8


class PutaoError(Exception):
    pass


class TrackError(PutaoError):
    pass


class ProjectError(PutaoError):
    pass


class ConversionError(PutaoError):
    pass


class FrqNotFoundError(PutaoError):
    pass
