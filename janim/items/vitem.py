from __future__ import annotations
from typing import Iterable, Optional
import numpy as np

from janim.constants import *
from janim.items.item import Item
from janim.utils.iterables import resize_with_interpolation
from janim.shaders.render import VItemRenderer
from janim.utils.math_functions import cross, get_norm

class VItem(Item):
    tolerance_for_point_equality = 1e-8

    def __init__(
        self,
        stroke_width: Optional[float | Iterable[float]] = 0.1,
        joint_type: str = 'auto',
        fill_color: Optional[JAnimColor | Iterable[float]] = None,
        fill_opacity = 0.0,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        # self.fill_color = fill_color # TODO: 实现 fill_color 和 fill_opacity
        # self.fill_opacity = fill_opacity

        # 轮廓线粗细
        self.stroke_width = np.array([0.1], dtype=np.float32)   # stroke_width 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_stroke_width = True

        # TODO: triangulation
        # TODO: 精细化边界框
        
        # 默认值
        self.set_stroke_width(stroke_width)

    def points_changed(self) -> None:
        super().points_changed()
        self.needs_new_stroke_width = True
    
    def create_renderer(self) -> VItemRenderer:
        return VItemRenderer()
    
    def set_stroke_width(self, stroke_width: float | Iterable[float]):
        if not isinstance(stroke_width, Iterable):
            stroke_width = [stroke_width]
        stroke_width = resize_with_interpolation(np.array(stroke_width), max(1, self.points_count()))
        if len(stroke_width) == len(self.stroke_width):
            self.stroke_width[:] = stroke_width
        else:
            self.stroke_width = stroke_width.astype(np.float32)
        return self
    
    def get_stroke_width(self) -> np.ndarray:
        if self.needs_new_stroke_width:
            self.set_stroke_width(self.stroke_width)
            self.needs_new_stroke_width = False
        return self.stroke_width

