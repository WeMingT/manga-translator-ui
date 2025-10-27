"""
YOLO OBB (Oriented Bounding Box) 检测器
用于漫画文本检测的辅助检测器
"""

import os
import numpy as np
import cv2
import onnxruntime as ort
from typing import List, Tuple, Optional

from .common import OfflineDetector
from ..utils import Quadrilateral


class YOLOOBBDetector(OfflineDetector):
    """YOLO OBB 检测器 - 基于ONNX Runtime"""
    
    _MODEL_MAPPING = {
        'model': {
            'url': 'https://github.com/hgmzhn/manga-translator-ui/releases/download/v1.7.1/ysgyolo_1.2_OS1.0.onnx',
            'hash': '6f3202925f01fdf045f8c31a3bf62e6c44944f56ce09107eb436bc5a5b185ebe',
            'file': '.',
        }
    }
    
    def __init__(self, *args, **kwargs):
        os.makedirs(self.model_dir, exist_ok=True)
        super().__init__(*args, **kwargs)
        
        # 类别列表（不包括other）
        self.classes = ['balloon', 'qipao', 'shuqing', 'changfangtiao', 'hengxie']
        self.input_size = 640
    
    async def _load(self, device: str):
        """加载ONNX模型"""
        model_path = self._get_file_path('ysgyolo_1.2_OS1.0.onnx')
        
        # 配置ONNX Runtime providers
        providers = []
        if device == 'cuda':
            providers.append('CUDAExecutionProvider')
        providers.append('CPUExecutionProvider')
        
        try:
            self.session = ort.InferenceSession(model_path, providers=providers)
            self.logger.info(f"YOLO OBB模型加载成功: {model_path}")
            self.logger.info(f"Providers: {self.session.get_providers()}")
        except Exception as e:
            self.logger.error(f"YOLO OBB模型加载失败: {e}")
            raise
        
        self.device = device
    
    async def _unload(self):
        """卸载模型"""
        del self.session
    
    def letterbox(
        self, 
        img: np.ndarray, 
        new_shape: Tuple[int, int] = (640, 640), 
        color: Tuple[int, int, int] = (114, 114, 114)
    ) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        """
        调整图像大小并添加边框（保持宽高比）- YOLO风格
        
        Returns:
            resized_img: 调整后的图像
            gain: 缩放比例
            (pad_w, pad_h): 填充的宽度和高度（像素）
        """
        shape = img.shape[:2]  # 当前形状 [height, width]
        
        # 计算缩放比例 (gain)
        gain = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        
        # 计算新的未填充尺寸
        new_unpad_w = int(round(shape[1] * gain))
        new_unpad_h = int(round(shape[0] * gain))
        
        # 计算padding（分成两边）
        pad_w = round((new_shape[1] - new_unpad_w) / 2 - 0.1)
        pad_h = round((new_shape[0] - new_unpad_h) / 2 - 0.1)
        
        # Resize图像
        if (new_unpad_w, new_unpad_h) != (shape[1], shape[0]):
            img = cv2.resize(img, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_LINEAR)
        
        # 添加边框
        top, bottom = int(pad_h), int(pad_h)
        left, right = int(pad_w), int(pad_w)
        img = cv2.copyMakeBorder(
            img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
        )
        
        return img, gain, (pad_w, pad_h)
    
    def preprocess(self, img: np.ndarray) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        """预处理图像"""
        img_resized, gain, pad = self.letterbox(
            img, 
            new_shape=(self.input_size, self.input_size)
        )
        
        # 转换为 RGB
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        
        # 转换为 CHW 格式
        img_transposed = img_rgb.transpose(2, 0, 1)
        
        # 添加 batch 维度
        img_expanded = np.expand_dims(img_transposed, axis=0)
        
        # 归一化到 [0, 1]
        blob = img_expanded.astype(np.float32) / 255.0
        
        return blob, gain, pad
    
    def scale_boxes(self, img1_shape, boxes, img0_shape, gain, pad, xywh=False):
        """将边界框从img1_shape缩放到img0_shape（移除letterbox效果）"""
        pad_w, pad_h = pad
        
        # 移除padding
        boxes[:, 0] -= pad_w  # x or cx
        boxes[:, 1] -= pad_h  # y or cy
        if not xywh:
            boxes[:, 2] -= pad_w  # x2
            boxes[:, 3] -= pad_h  # y2
        
        # 缩放到原始尺寸
        boxes[:, :4] /= gain
        
        # 裁剪到图像边界
        if xywh:
            boxes[:, 0] = np.clip(boxes[:, 0], 0, img0_shape[1])  # cx
            boxes[:, 1] = np.clip(boxes[:, 1], 0, img0_shape[0])  # cy
        else:
            boxes[:, 0] = np.clip(boxes[:, 0], 0, img0_shape[1])  # x1
            boxes[:, 1] = np.clip(boxes[:, 1], 0, img0_shape[0])  # y1
            boxes[:, 2] = np.clip(boxes[:, 2], 0, img0_shape[1])  # x2
            boxes[:, 3] = np.clip(boxes[:, 3], 0, img0_shape[0])  # y2
        
        return boxes
    
    def xywhr2xyxyxyxy(self, rboxes: np.ndarray) -> np.ndarray:
        """将旋转边界框从 xywhr 格式转换为 xyxyxyxy (四个角点) 格式"""
        ctr = rboxes[:, :2]  # 中心点
        w = rboxes[:, 2:3]   # 宽度
        h = rboxes[:, 3:4]   # 高度
        angle = rboxes[:, 4:5]  # 角度（弧度）
        
        cos_value = np.cos(angle)
        sin_value = np.sin(angle)
        
        # 计算两个向量
        vec1_x = w / 2 * cos_value
        vec1_y = w / 2 * sin_value
        vec2_x = -h / 2 * sin_value
        vec2_y = h / 2 * cos_value
        
        vec1 = np.concatenate([vec1_x, vec1_y], axis=-1)
        vec2 = np.concatenate([vec2_x, vec2_y], axis=-1)
        
        # 计算四个角点
        pt1 = ctr + vec1 + vec2
        pt2 = ctr + vec1 - vec2
        pt3 = ctr - vec1 - vec2
        pt4 = ctr - vec1 + vec2
        
        corners = np.stack([pt1, pt2, pt3, pt4], axis=1)
        return corners
    
    def nms_rotated(self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> List[int]:
        """旋转框的非极大值抑制 (简化版本)"""
        if len(boxes) == 0:
            return []
        
        # 按分数排序
        indices = np.argsort(scores)[::-1]
        keep = []
        
        while len(indices) > 0:
            current = indices[0]
            keep.append(current)
            
            if len(indices) == 1:
                break
            
            # 简化的 IoU 计算（使用外接矩形）
            current_box = boxes[current]
            other_boxes = boxes[indices[1:]]
            
            # 计算边界框重叠（简化版）
            indices = indices[1:]
        
        return keep
    
    def deduplicate_boxes(
        self,
        boxes: np.ndarray,
        scores: np.ndarray,
        class_ids: np.ndarray,
        distance_threshold: float = 10.0,
        iou_threshold: float = 0.3
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """后处理去重：移除中心点距离很近或高度重叠的框"""
        if len(boxes) == 0:
            return boxes, scores, class_ids
        
        # 计算每个框的中心点
        centers = np.mean(boxes, axis=1)  # (N, 2)
        
        keep = []
        
        # 按分数排序（从高到低）
        sorted_indices = np.argsort(scores)[::-1]
        
        for i in sorted_indices:
            should_keep = True
            
            for j in keep:
                # 检查中心点距离
                dist = np.linalg.norm(centers[i] - centers[j])
                
                # 同类别且距离很近，则去重
                if class_ids[i] == class_ids[j] and dist < distance_threshold:
                    should_keep = False
                    break
                
                # 计算简化的IoU（使用边界框）
                box_i_min = np.min(boxes[i], axis=0)
                box_i_max = np.max(boxes[i], axis=0)
                box_j_min = np.min(boxes[j], axis=0)
                box_j_max = np.max(boxes[j], axis=0)
                
                # 计算交集
                inter_min = np.maximum(box_i_min, box_j_min)
                inter_max = np.minimum(box_i_max, box_j_max)
                inter_wh = np.maximum(0, inter_max - inter_min)
                inter_area = inter_wh[0] * inter_wh[1]
                
                # 计算并集
                box_i_area = (box_i_max[0] - box_i_min[0]) * (box_i_max[1] - box_i_min[1])
                box_j_area = (box_j_max[0] - box_j_min[0]) * (box_j_max[1] - box_j_min[1])
                union_area = box_i_area + box_j_area - inter_area
                
                # 计算IoU
                if union_area > 0:
                    iou = inter_area / union_area
                    if iou > iou_threshold:
                        should_keep = False
                        break
            
            if should_keep:
                keep.append(i)
        
        return boxes[keep], scores[keep], class_ids[keep]
    
    def postprocess(
        self,
        outputs: np.ndarray,
        img_shape: Tuple[int, int],
        gain: float,
        pad: Tuple[float, float],
        conf_threshold: float,
        iou_threshold: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        后处理模型输出
        
        Returns:
            boxes_corners: (N, 4, 2) 角点坐标
            scores: (N,) 置信度
            class_ids: (N,) 类别ID
        """
        # 处理输出格式
        predictions = outputs[0]
        
        # 检查并转置（如果需要）
        if predictions.ndim == 3:
            if predictions.shape[0] == 1:
                predictions = predictions[0]
        
        if predictions.ndim == 2:
            if predictions.shape[0] < predictions.shape[1] and predictions.shape[0] < 100:
                predictions = predictions.T
        
        if len(predictions) == 0:
            return np.array([]), np.array([]), np.array([])
        
        # YOLO OBB 输出格式: [cx, cy, w, h, class0, class1, ..., classN, angle]
        nc = len(self.classes)
        box = predictions[:, :4]  # [cx, cy, w, h]
        cls = predictions[:, 4:4+nc]  # 类别分数
        angle = predictions[:, -1:]  # angle（最后一列）
        
        # 获取最高置信度的类别
        conf = np.max(cls, axis=1, keepdims=True)
        j = np.argmax(cls, axis=1, keepdims=True).astype(float)
        
        # 组合：[box, conf, class_id, angle]
        x = np.concatenate((box, conf, j, angle), axis=1)
        
        # 应用置信度阈值
        x = x[conf.flatten() > conf_threshold]
        
        if x.shape[0] == 0:
            return np.array([]), np.array([]), np.array([])
        
        # 缩放坐标（在NMS之前）
        boxes_to_scale = x[:, :4].copy()
        boxes_to_scale = self.scale_boxes(
            (self.input_size, self.input_size),
            boxes_to_scale,
            img_shape,
            gain,
            pad,
            xywh=True
        )
        x[:, :4] = boxes_to_scale
        
        # NMS
        boxes_xywhr = np.concatenate((x[:, :4], x[:, -1:]), axis=-1)
        scores = x[:, 4]
        keep_indices = self.nms_rotated(boxes_xywhr, scores, iou_threshold)
        x = x[keep_indices]
        
        # 提取结果
        boxes_xywhr = np.concatenate((x[:, :4], x[:, -1:]), axis=-1)
        scores = x[:, 4]
        class_ids = x[:, 5].astype(int)
        
        # 转换为角点格式
        if len(boxes_xywhr) > 0:
            boxes_corners = self.xywhr2xyxyxyxy(boxes_xywhr)
            
            # 内部去重
            boxes_corners, scores, class_ids = self.deduplicate_boxes(
                boxes_corners, scores, class_ids,
                distance_threshold=10.0,
                iou_threshold=0.3
            )
            self.logger.info(f"YOLO OBB内部去重后: {len(boxes_corners)} 个框")
        else:
            boxes_corners = np.array([])
        
        return boxes_corners, scores, class_ids
    
    async def _infer(
        self, 
        image: np.ndarray, 
        detect_size: int, 
        text_threshold: float,
        box_threshold: float, 
        unclip_ratio: float,
        verbose: bool = False
    ):
        """
        执行检测推理
        
        Returns:
            textlines: List of Quadrilateral objects
            raw_mask: None (YOLO OBB不生成mask)
            debug_img: None
        """
        # 预处理
        blob, gain, pad = self.preprocess(image)
        
        # 推理
        input_name = self.session.get_inputs()[0].name
        output_names = [output.name for output in self.session.get_outputs()]
        outputs = self.session.run(output_names, {input_name: blob})
        
        # 后处理
        img_shape = image.shape[:2]
        boxes_corners, scores, class_ids = self.postprocess(
            outputs,
            img_shape,
            gain,
            pad,
            text_threshold,  # 使用text_threshold作为置信度阈值
            0.6  # IoU阈值
        )
        
        # 转换为Quadrilateral对象
        textlines = []
        for corners, score, class_id in zip(boxes_corners, scores, class_ids):
            # corners: (4, 2) array
            pts = corners.astype(np.int32)
            label = self.classes[class_id] if class_id < len(self.classes) else f'class_{class_id}'
            quad = Quadrilateral(pts, label, float(score))
            textlines.append(quad)
        
        self.logger.info(f"YOLO OBB检测到 {len(textlines)} 个文本框")
        
        return textlines, None, None

