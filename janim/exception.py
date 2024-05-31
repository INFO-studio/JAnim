import sys
from dataclasses import dataclass


_sys_excepthook = sys.excepthook


def custom_excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, ExitException):
        sys.exit(exc_value.exit_code)
    _sys_excepthook(exc_type, exc_value, exc_traceback)


sys.excepthook = custom_excepthook


EXITCODE_PYSIDE6_NOT_FOUND = 1001
'''``PySide6`` 未安装时的退出码'''
EXITCODE_MODULE_NOT_FOUND = 1002
'''使用 ``run`` 或 ``write`` 指定的文件未找到时的退出码'''
EXITCODE_NOT_FILE = 1003
'''使用 ``run`` 或 ``write`` 指定路径不是文件时的退出码'''

EXITCODE_TYPST_NOT_FOUND = 1101
'''``Typst`` 未安装时的退出码'''
EXITCODE_TYPST_COMPILE_ERROR = 1102
'''``Typst`` 编译失败时的退出码'''

EXITCODE_FFMPEG_NOT_FOUND = 2001
'''``ffmpeg`` 未安装时的退出码'''


class JAnimException(Exception): ...


@dataclass
class ExitException(JAnimException):
    '''
    当 :class:`ExitException` 未被捕获时，
    会直接以 ``exit_code`` 退出，不输出 ``traceback`` 信息
    '''
    exit_code: int


class TimelineError(JAnimException): ...
class TimelineLookupError(TimelineError): ...
class RecordFailedError(TimelineError): ...
class RecordNotFoundError(TimelineError): ...
class NotAnimationError(TimelineError): ...


class UpdaterError(JAnimException): ...


class CmptGroupLookupError(JAnimException): ...


class AnimGroupEmptyError(JAnimException): ...
class PointError(JAnimException): ...
class InvaildMatrixError(PointError): ...


class BooleanOpsError(JAnimException): ...


class AsTypeError(JAnimException): ...


class ColorNotFoundError(JAnimException): ...
class FontNotFoundError(JAnimException): ...
