
from typing import Callable, Optional

from janim.constants import *
from janim.animation.animation import Animation
from janim.items.item import Item
from janim.utils.paths import straight_path, path_along_arc

class Transform(Animation):
    '''
    创建从 `item` 至 `target_item` 的插值动画

    - 改变的是 `item` 的数据，以呈现插值效果
    - `path_arc` 和 `path_arc_axis` 可以指定插值的圆弧路径的角度，若不传入则是直线
    - 也可以直接传入 `path_func` 来指定路径方法
    '''
    def __init__(
        self,
        item: Item,
        target_item: Item,
        path_arc: float = 0,
        path_arc_axis: np.ndarray = OUT,
        path_func: Optional[Callable[[np.ndarray, np.ndarray, float], np.ndarray]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.item = item
        self.target_item = target_item

        self.path_func = path_func or self.create_path_func(path_arc, path_arc_axis)

    @staticmethod
    def create_path_func(
        path_arc: float,
        path_arc_axis: np.ndarray
    ) -> Callable[[np.ndarray, np.ndarray, float], np.ndarray]:
        if path_arc == 0:
            return straight_path
        return path_along_arc(
            path_arc,
            path_arc_axis
        )

    def begin(self) -> None:
        self.target_copy = self.target_item.copy()
        self.item.align_for_transform(self.target_copy)
        self.item_copy = self.item.copy()
    
    def interpolate(self, alpha) -> None:
        for item, item1, item2 in zip(self.item.get_family(), self.item_copy.get_family(), self.target_copy.get_family()):
            item.interpolate(item1, item2, alpha, self.path_func)

    def finish(self) -> None:
        self.interpolate(1)
        