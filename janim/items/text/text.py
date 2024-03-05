from __future__ import annotations

import itertools as it
import re
from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Concatenate, Iterable, Self

import numpy as np

from janim.components.points import Cmpt_Points
from janim.constants import DEFAULT_ITEM_TO_EDGE_BUFF, ORIGIN, RIGHT, UP
from janim.items.points import Group, Points
from janim.items.vitem import VItem
from janim.logger import log
from janim.typing import JAnimColor
from janim.utils.config import Config
from janim.utils.font import Font, get_fontpath_by_name
from janim.utils.simple_functions import decode_utf8
from janim.utils.space_ops import get_norm, normalize

DEFAULT_FONT_SIZE = 24
ORIG_FONT_SIZE = 48


def get_color_value_by_key(key: str) -> JAnimColor:
    '''
    根据 ``key`` 从 ``janim.constants.colors`` 得到颜色
    '''
    import janim.constants.colors as colors
    if not hasattr(colors, key):
        raise ValueError(f'No built-in color named {key}')
    return getattr(colors, key)


type ActConverter = Callable[[str], Any]
type ActCaller = Callable[Concatenate[TextChar, ...], Any]
type Act = tuple[Iterable[ActConverter], ActCaller]
type ActName = str

type ActParams = Iterable[str]
type ActParamsStack = list[ActParams]

type ActAt = int
type ActStart = tuple[ActName, ActParams]
type ActEnd = str

available_act_map: dict[ActName, list[Act]] = defaultdict(list)


def register_acts(names: list[ActName], *acts: Act) -> None:
    '''
    用于声明可用的富文本格式
    '''
    for name in names:
        available_act_map[name].extend(acts)


register_acts(
    ['color', 'c'],
    ((get_color_value_by_key,),     lambda char, color: char.color.set(color)),
    ((float, float, float),         lambda char, r, g, b: char.color.set([r, g, b])),
    ((float, float, float, float),  lambda char, r, g, b, a: char.color.set_rgbas([r, g, b, a]))
)
register_acts(
    ['stroke_color', 'sc'],
    ((get_color_value_by_key,),     lambda char, color: char.stroke.set(color)),
    ((float, float, float),         lambda char, r, g, b: char.stroke.set([r, g, b])),
    ((float, float, float, float),  lambda char, r, g, b, a: char.stroke.set_rgbas([r, g, b, a]))
)
register_acts(
    ['fill_color', 'fc'],
    ((get_color_value_by_key,),     lambda char, color: char.fill.set(color)),
    ((float, float, float),         lambda char, r, g, b: char.fill.set([r, g, b])),
    ((float, float, float, float),  lambda char, r, g, b, a: char.fill.set_rgbas([r, g, b, a]))
)
register_acts(
    ['alpha', 'a'],
    ((float,), lambda char, a: char.color.set(alpha=a))
)
register_acts(
    ['stroke_alpha', 'sa'],
    ((float,), lambda char, a: char.stroke.set(alpha=a))
)
register_acts(
    ['fill_alpha', 'fa'],
    ((float,), lambda char, a: char.fill.set(alpha=a))
)
register_acts(
    ['stroke', 's'],
    ((float,), lambda char, radius: char.stroke.set(radius))
)
# TODO: distinct_stroke
register_acts(
    ['font_scale', 'fs'],
    ((float,), lambda char, factor: char.points.scale(factor, about_point=ORIGIN))
)


class TextChar(VItem):
    '''
    字符物件，作为 :class:`TextLine` 的子物件，在创建 :class:`TextLine` 时产生
    '''
    def __init__(self, char: str, fonts: list[Font], font_size: float, **kwargs):
        super().__init__(**kwargs)
        self.char = char

        unicode = decode_utf8(char)
        font_render = self.get_font_for_render(unicode, fonts)

        outline, advance = font_render.get_glyph_data(unicode)

        font_scale_factor = font_size / ORIG_FONT_SIZE
        frame_scale_factor = Config.get.pixel_to_frame_ratio / 32
        scale_factor = font_scale_factor * frame_scale_factor

        self.points.set(outline * scale_factor)

        # 标记位置
        self.mark = Points(
            ORIGIN, RIGHT * font_scale_factor, UP * font_scale_factor,
            [advance[0] * scale_factor, advance[1] * scale_factor, 0]
        )
        Cmpt_Points.apply_points_fn.connect(
            self.points,
            lambda func, about_point: self.mark.points.apply_points_fn(func, about_point=about_point)
        )

    @staticmethod
    def get_font_for_render(unicode: str, fonts: list[Font]) -> Font:
        '''
        从字体列表中找到支持显示 ``unicode`` 的字体，如果找不到只好选用第一个
        '''
        font_render = fonts[0]
        for font in fonts:
            idx = font.face.get_char_index(unicode)
            if idx != 0:
                font_render = font
                break
        return font_render

    def get_mark_orig(self) -> np.ndarray:
        return self.mark.points._points._data[0].copy()

    def get_mark_right(self) -> np.ndarray:
        return self.mark.points._points._data[1].copy()

    def get_mark_up(self) -> np.ndarray:
        return self.mark.points._points._data[2].copy()

    def get_mark_advance(self) -> np.ndarray:
        return self.mark.points._points._data[3].copy()

    def get_advance_length(self) -> float:
        return get_norm(self.get_mark_advance() - self.get_mark_orig())

    def apply_act_list(self, act_params_map: dict[str, ActParamsStack]) -> None:
        '''
        应用富文本样式，由 :meth:`Text.apply_rich_text` 调用
        '''
        for name, params_stack in act_params_map.items():
            params = params_stack[-1]
            for converters, caller in available_act_map[name]:
                if len(converters) == len(params):
                    try:
                        caller(
                            self, *[
                                converter(param)
                                for converter, param in zip(converters, params)
                            ]
                        )
                    except Exception:
                        log.error(f'应用 {name} 时，{params} 与 {[cvt.__name__ for cvt in converters]} 不匹配')
                        raise

                    break
            else:
                txt = ','.join([
                    '[' + ','.join([cvt.__name__ for cvt in act[0]]) + ']'
                    for act in available_act_map[name]
                ])
                log.warning(f'应用 "{name}" 时，{params} 与 {txt} 没有匹配项')


class TextLine(Group[TextChar]):
    '''
    单行文字物件，作为 :class:`Text` 的子物件，在创建 :class:`Text` 时产生s
    '''
    def __init__(self, text: str, fonts: list[Font], font_size: float, char_kwargs={}, **kwargs):
        self.text = text

        super().__init__(
            *[
                TextChar(char, fonts, font_size, **char_kwargs)
                for char in text
            ],
            **kwargs
        )

        # 标记位置
        self.mark = Points(ORIGIN, RIGHT, UP)
        self.mark.points.scale(font_size / ORIG_FONT_SIZE, about_point=ORIGIN)
        Cmpt_Points.apply_points_fn.connect(
            self.points,
            lambda func, about_point: self.mark.points.apply_points_fn(func, about_point=about_point)
        )

    def get_mark_orig(self) -> np.ndarray:
        return self.mark.points._points._data[0].copy()

    def get_mark_right(self) -> np.ndarray:
        return self.mark.points._points._data[1].copy()

    def get_mark_up(self) -> np.ndarray:
        return self.mark.points._points._data[2].copy()

    def arrange_in_line(self, buff: float = 0) -> Self:
        '''
        根据 ``advance`` 的标记信息排列该行
        '''
        if len(self.children) == 0:
            return

        pos: np.ndarray = None

        def update(char: TextChar) -> None:
            nonlocal pos
            orig = char.get_mark_orig()
            advance = char.get_mark_advance()
            pos = advance if buff == 0 else advance + buff * normalize(advance - orig)

        update(self[0])
        for char in self[1:]:
            char.points.shift(pos - char.get_mark_orig())
            update(char)

        return self


class Text(Group[TextLine]):
    '''
    文字物件
    '''
    class Format(Enum):
        PlainText = 0
        RichText = 1

    def __init__(
        self,
        text: str,
        font: str | Iterable[str] = [],
        font_size: float = DEFAULT_FONT_SIZE,
        format: Format = Format.PlainText,
        line_kwargs: dict = {},
        stroke_alpha: float = 0,
        fill_alpha: float = 1,
        **kwargs
    ) -> None:
        # 获取字体
        if isinstance(font, str):
            font = [font]
        font.append(Config.get.font)
        fonts = [
            Font.get(get_fontpath_by_name(name))
            for name in font
        ]

        if format is not Text.Format.RichText:
            self.text = text
        else:
            # 如果是 RichText，获取属性列表
            self.text = ''
            self.act_params_list: list[tuple[ActAt, ActStart | ActEnd]] = []
            idx = 0
            iter = re.finditer(r'(<+)(/?[^<]*?)>', text)
            for match in iter:
                match: re.Match
                start, end = match.span()
                left, mid = match.group(1, 2)

                self.text += text[idx:start]
                idx = end

                left_cnt = len(left)
                self.text += '<' * (left_cnt // 2)
                if left_cnt % 2 == 0:
                    self.text += mid + '>'
                else:
                    if mid.startswith('/'):
                        self.act_params_list.append((len(self.text), mid[1:]))
                    else:
                        split = mid.split()
                        self.act_params_list.append((len(self.text), (split[0], split[1:])))

            self.text += text[idx:]

        super().__init__(
            *[
                TextLine(line_text, fonts=fonts, font_size=font_size, **line_kwargs)
                for line_text in self.text.split('\n')
            ],
            stroke_alpha=stroke_alpha,
            fill_alpha=fill_alpha,
            **kwargs
        )

        if format is Text.Format.RichText:
            self.apply_rich_text()
        for line in self.children:
            line.arrange_in_line()
        self.arrange_in_lines()
        self.astype(Points).points.to_center()

    def is_null(self) -> bool:
        return True

    def idx_to_row_col(self, idx: int) -> tuple[int, int]:
        '''
        由字符索引得到 行数、列数 索引
        '''
        for i, line in enumerate(self):
            if idx < len(line):
                return i, idx
            idx -= len(line)
        return len(self) - 1, idx

    def select_parts(self, pattern):
        '''
        根据 ``pattern`` 获得文字中的部分
        '''
        total_text: str = ''.join([line.text for line in self])
        parts = []
        for mch in re.finditer(pattern, total_text):
            l_row, l_col = self.idx_to_row_col(mch.start())
            r_row, r_col = self.idx_to_row_col(mch.end())
            if l_row == r_row:
                parts.append(self[l_row][l_col:r_col])
            else:
                parts.append(
                    Group(*it.chain(
                        self[l_row][l_col:],
                        *self[l_row + 1: r_row],
                        self[r_row][:r_col]
                    ))
                )
        return Group(*parts)

    def arrange_in_lines(self, buff: float = 0, base_buff: float = 0.85) -> Self:
        '''
        - ``buff``: 每行之间的额外间距
        - ``base_buff``: 每行之间的基本间距，默认值 `0.85` 用于将两行上下排列，如果是 `0` 则会让两行完全重合，大部分时候不需要传入该值
        '''
        if len(self.children) == 0:
            return

        pos = self.children[0].get_mark_orig()
        for line in self.children[1:]:
            vert = line.get_mark_orig() - line.get_mark_up()
            target = pos + base_buff * vert + buff * normalize(vert)
            line.points.shift(
                target - line.get_mark_orig()
            )
            pos = line.get_mark_orig()

        return self

    # TODO: word_wrap

    def apply_rich_text(self) -> None:
        '''
        应用富文本效果
        '''
        text_at = 0
        act_idx = 0
        act_params_map: defaultdict[str, ActParamsStack] = defaultdict(list)
        for line in self.children:
            for char in line.children:
                while act_idx < len(self.act_params_list):
                    next_act_at, next_act = self.act_params_list[act_idx]
                    if text_at < next_act_at:
                        break

                    if isinstance(next_act, str):   # ActEnd
                        stack = act_params_map[next_act]
                        stack.pop()
                        if not stack:
                            del act_params_map[next_act]
                    else:   # ActStart
                        name, params = next_act
                        act_params_map[name].append(params)

                    act_idx += 1

                char.apply_act_list(act_params_map)
                text_at += 1

            text_at += 1
