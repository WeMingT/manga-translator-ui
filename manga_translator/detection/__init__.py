import numpy as np
from typing import List

from .default import DefaultDetector
from .dbnet_convnext import DBConvNextDetector
from .ctd import ComicTextDetector
from .craft import CRAFTDetector
from .paddle_rust import PaddleDetector
from .none import NoneDetector
from .yolo_obb import YOLOOBBDetector
from .common import CommonDetector, OfflineDetector
from ..config import Detector
from ..utils import Quadrilateral

DETECTORS = {
    Detector.default: DefaultDetector,
    Detector.dbconvnext: DBConvNextDetector,
    Detector.ctd: ComicTextDetector,
    Detector.craft: CRAFTDetector,
    Detector.paddle: PaddleDetector,
    Detector.none: NoneDetector,
}
detector_cache = {}

def get_detector(key: Detector, *args, **kwargs) -> CommonDetector:
    if key not in DETECTORS:
        raise ValueError(f'Could not find detector for: "{key}". Choose from the following: %s' % ','.join(DETECTORS))
    if not detector_cache.get(key):
        detector = DETECTORS[key]
        detector_cache[key] = detector(*args, **kwargs)
    return detector_cache[key]

async def prepare(detector_key: Detector):
    detector = get_detector(detector_key)
    if isinstance(detector, OfflineDetector):
        await detector.download()

async def dispatch(detector_key: Detector, image: np.ndarray, detect_size: int, text_threshold: float, box_threshold: float, unclip_ratio: float,
                   invert: bool, gamma_correct: bool, rotate: bool, auto_rotate: bool = False, device: str = 'cpu', verbose: bool = False,
                   use_yolo_obb: bool = False, yolo_obb_conf: float = 0.4, yolo_obb_iou: float = 0.6):
    """
    检测调度函数，支持混合检测模式
    
    Args:
        use_yolo_obb: 是否启用YOLO OBB辅助检测器
        yolo_obb_conf: YOLO OBB检测器的置信度阈值
        yolo_obb_iou: YOLO OBB检测器的IoU阈值（交叉比）
    """
    # 主检测器检测
    detector = get_detector(detector_key)
    if isinstance(detector, OfflineDetector):
        await detector.load(device)
    main_textlines, mask, raw_image = await detector.detect(image, detect_size, text_threshold, box_threshold, unclip_ratio, invert, gamma_correct, rotate, auto_rotate, verbose)
    
    # 如果不启用YOLO OBB，直接返回主检测器结果
    if not use_yolo_obb:
        return main_textlines, mask, raw_image
    
    # YOLO OBB辅助检测
    try:
        yolo_detector = get_detector_instance('yolo_obb', YOLOOBBDetector)
        await yolo_detector.load(device)
        
        # YOLO OBB检测（使用yolo_obb_conf作为text_threshold）
        yolo_textlines, _, _ = await yolo_detector.detect(
            image, detect_size, yolo_obb_conf, box_threshold, unclip_ratio,
            invert, gamma_correct, rotate, auto_rotate, verbose
        )
        
        # 智能合并：YOLO框可以替换过小的主检测器框，或添加新框
        combined_textlines = merge_detection_boxes(yolo_textlines, main_textlines)
        
        replaced_count = len(main_textlines) + len(yolo_textlines) - len(combined_textlines)
        detector.logger.info(f"混合检测: 主检测器={len(main_textlines)}, YOLO OBB={len(yolo_textlines)}, "
                           f"替换={replaced_count}, 总计={len(combined_textlines)}")
        
        return combined_textlines, mask, raw_image
    
    except Exception as e:
        detector.logger.error(f"YOLO OBB辅助检测失败: {e}")
        # 失败时返回主检测器结果
        return main_textlines, mask, raw_image


def get_detector_instance(key: str, detector_class):
    """获取或创建检测器实例（用于辅助检测器）"""
    if key not in detector_cache:
        detector_cache[key] = detector_class()
    return detector_cache[key]


def merge_detection_boxes(yolo_boxes: List[Quadrilateral], main_boxes: List[Quadrilateral]) -> List[Quadrilateral]:
    """
    合并主检测器和YOLO检测器的框，智能替换逻辑：
    1. 如果YOLO框与主检测器框重叠
    2. 且YOLO框完全包含主检测器框
    3. 且YOLO框面积 >= 主检测器框面积 * 2
    4. 则删除主检测器框，使用YOLO框替代
    5. 其他情况：删除重叠的YOLO框，保留主检测器框
    6. 不重叠的YOLO框直接添加
    
    Args:
        yolo_boxes: YOLO OBB检测器的检测框
        main_boxes: 主检测器的检测框
    
    Returns:
        合并后的检测框列表
    """
    if len(main_boxes) == 0:
        return yolo_boxes
    
    if len(yolo_boxes) == 0:
        return main_boxes
    
    # 标记要移除的主检测器框索引
    main_boxes_to_remove = set()
    # 标记要移除的YOLO框索引
    yolo_boxes_to_remove = set()
    # 要添加的YOLO框（用于替换）
    yolo_boxes_to_add_set = set()  # 使用set避免重复
    
    for yolo_idx, yolo_box in enumerate(yolo_boxes):
        # 计算YOLO框的AABB和面积
        yolo_min_x = np.min(yolo_box.pts[:, 0])
        yolo_max_x = np.max(yolo_box.pts[:, 0])
        yolo_min_y = np.min(yolo_box.pts[:, 1])
        yolo_max_y = np.max(yolo_box.pts[:, 1])
        yolo_area = (yolo_max_x - yolo_min_x) * (yolo_max_y - yolo_min_y)
        
        # 检查这个YOLO框是否满足任何替换条件
        can_replace = False
        has_overlap_without_replace = False
        
        for main_idx, main_box in enumerate(main_boxes):
            # 计算主检测器框的AABB和面积
            main_min_x = np.min(main_box.pts[:, 0])
            main_max_x = np.max(main_box.pts[:, 0])
            main_min_y = np.min(main_box.pts[:, 1])
            main_max_y = np.max(main_box.pts[:, 1])
            main_area = (main_max_x - main_min_x) * (main_max_y - main_min_y)
            
            # 检查是否有重叠
            if not (yolo_max_x < main_min_x or yolo_min_x > main_max_x or
                    yolo_max_y < main_min_y or yolo_min_y > main_max_y):
                # 有重叠，检查YOLO框是否完全包含主检测器框
                contains = (yolo_min_x <= main_min_x and yolo_max_x >= main_max_x and
                           yolo_min_y <= main_min_y and yolo_max_y >= main_max_y)
                
                # 检查面积条件
                area_ratio = yolo_area / main_area if main_area > 0 else 0
                
                if contains and area_ratio >= 2.0:
                    # 满足替换条件：删除主检测器框，使用YOLO框
                    main_boxes_to_remove.add(main_idx)
                    can_replace = True
                else:
                    # 不满足替换条件但有重叠
                    has_overlap_without_replace = True
        
        # 决定这个YOLO框的命运
        if can_replace:
            # 至少替换了一个主检测器框，保留这个YOLO框
            yolo_boxes_to_add_set.add(yolo_idx)
        elif has_overlap_without_replace:
            # 有重叠但不满足替换条件，删除这个YOLO框
            yolo_boxes_to_remove.add(yolo_idx)
        # else: 没有重叠，会在后面作为新框添加
    
    # 构建最终结果
    result = []
    
    # 添加未被移除的主检测器框
    for idx, main_box in enumerate(main_boxes):
        if idx not in main_boxes_to_remove:
            result.append(main_box)
    
    # 添加YOLO框（替换的 + 不重叠的新框）
    for idx, yolo_box in enumerate(yolo_boxes):
        # 如果不在删除列表中，就添加（包括替换框和新框）
        if idx not in yolo_boxes_to_remove:
            result.append(yolo_box)
    
    return result

async def unload(detector_key: Detector):
    detector_cache.pop(detector_key, None)
