"""
YSGYOLO PyTorch 模型检测可视化工具 - 带 GUI 界面
支持加载 .pt 格式的 YOLOv5 模型
"""
import cv2
import numpy as np
import torch
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import os
import sys

# 添加项目路径以导入必要的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manga_translator.detection.ctd_utils.yolov5.yolo import load_yolov5


class YSGYOLOPyTorchDetectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YSGYOLO PyTorch 模型检测可视化工具")
        self.root.geometry("1200x800")
        
        # 模型路径
        self.model_path = r"C:\Users\徐浩文\manga-image-translator\manga-translator-ui-package\models\detection\ysgyolo_1.2_OS1.0.pt"
        self.model = None
        self.device = None
        self.current_image = None
        self.current_image_path = None
        self.result_image = None
        
        # 创建界面
        self.create_widgets()
        
        # 加载模型
        self.load_model()
    
    def create_widgets(self):
        """创建界面组件"""
        # 顶部控制面板
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        # 文件选择
        ttk.Label(control_frame, text="图片路径:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.path_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="浏览", command=self.browse_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="检测", command=self.detect_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="保存结果", command=self.save_result).pack(side=tk.LEFT, padx=5)
        
        # 参数设置面板
        param_frame = ttk.Frame(self.root, padding=10)
        param_frame.pack(side=tk.TOP, fill=tk.X)
        
        # 置信度阈值
        ttk.Label(param_frame, text="置信度阈值:").pack(side=tk.LEFT, padx=5)
        self.conf_var = tk.DoubleVar(value=0.4)
        conf_scale = ttk.Scale(param_frame, from_=0.1, to=0.9, variable=self.conf_var, 
                              orient=tk.HORIZONTAL, length=150)
        conf_scale.pack(side=tk.LEFT, padx=5)
        self.conf_label = ttk.Label(param_frame, text="0.40")
        self.conf_label.pack(side=tk.LEFT, padx=5)
        self.conf_var.trace('w', self.update_conf_label)
        
        # NMS 阈值
        ttk.Label(param_frame, text="NMS阈值:").pack(side=tk.LEFT, padx=5)
        self.iou_var = tk.DoubleVar(value=0.45)
        iou_scale = ttk.Scale(param_frame, from_=0.1, to=0.9, variable=self.iou_var, 
                             orient=tk.HORIZONTAL, length=150)
        iou_scale.pack(side=tk.LEFT, padx=5)
        self.iou_label = ttk.Label(param_frame, text="0.45")
        self.iou_label.pack(side=tk.LEFT, padx=5)
        self.iou_var.trace('w', self.update_iou_label)
        
        # 输入尺寸
        ttk.Label(param_frame, text="输入尺寸:").pack(side=tk.LEFT, padx=5)
        self.size_var = tk.StringVar(value="640")
        size_combo = ttk.Combobox(param_frame, textvariable=self.size_var, 
                                 values=["320", "416", "512", "640", "800", "1024"], width=10)
        size_combo.pack(side=tk.LEFT, padx=5)
        
        # 图片显示区域
        display_frame = ttk.Frame(self.root)
        display_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 原图显示
        left_frame = ttk.LabelFrame(display_frame, text="原图", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.original_canvas = tk.Canvas(left_frame, bg='gray')
        self.original_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 结果显示
        right_frame = ttk.LabelFrame(display_frame, text="检测结果", padding=10)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.result_canvas = tk.Canvas(right_frame, bg='gray')
        self.result_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=5)
        
        # 检测结果文本
        self.result_text = tk.Text(status_frame, height=5, wrap=tk.WORD)
        self.result_text.pack(fill=tk.X, padx=5, pady=5)
    
    def update_conf_label(self, *args):
        self.conf_label.config(text=f"{self.conf_var.get():.2f}")
    
    def update_iou_label(self, *args):
        self.iou_label.config(text=f"{self.iou_var.get():.2f}")
    
    def load_model(self):
        """加载 PyTorch 模型"""
        try:
            self.status_var.set("正在加载模型...")
            self.root.update()
            
            # 检测可用设备
            if torch.cuda.is_available():
                self.device = 'cuda'
                device_name = "CUDA"
            else:
                self.device = 'cpu'
                device_name = "CPU"
            
            # 加载 YOLOv5 模型
            self.model = load_yolov5(self.model_path, map_location=self.device, fuse=True)
            self.model.eval()
            self.model.to(self.device)
            
            self.status_var.set(f"模型已加载 (使用 {device_name})")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载模型失败: {e}")
            self.status_var.set("模型加载失败")
            import traceback
            traceback.print_exc()
    
    def browse_image(self):
        """浏览选择图片"""
        filename = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp"),
                ("所有文件", "*.*")
            ]
        )
        if filename:
            self.path_var.set(filename)
            self.load_image(filename)
    
    def load_image(self, path):
        """加载并显示图片（支持中文路径）"""
        try:
            # 使用 numpy 读取以支持中文路径
            with open(path, 'rb') as f:
                image_data = f.read()
            image_array = np.frombuffer(image_data, dtype=np.uint8)
            self.current_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if self.current_image is None:
                messagebox.showerror("错误", f"无法读取图片: {path}")
                return
            
            self.current_image_path = path
            self.display_image(self.current_image, self.original_canvas)
            self.status_var.set(f"已加载图片: {os.path.basename(path)} ({self.current_image.shape[1]}x{self.current_image.shape[0]})")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图片失败: {e}")
    
    def display_image(self, cv_image, canvas):
        """在 Canvas 上显示图片"""
        # 转换为 RGB
        image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        
        # 调整大小以适应 Canvas
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 500
            canvas_height = 500
        
        h, w = image_rgb.shape[:2]
        scale = min(canvas_width / w, canvas_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        image_resized = cv2.resize(image_rgb, (new_w, new_h))
        
        # 转换为 PIL Image
        pil_image = Image.fromarray(image_resized)
        photo = ImageTk.PhotoImage(pil_image)
        
        # 显示在 Canvas 中央
        canvas.delete("all")
        x = (canvas_width - new_w) // 2
        y = (canvas_height - new_h) // 2
        canvas.create_image(x, y, anchor=tk.NW, image=photo)
        canvas.image = photo  # 保持引用
    
    def detect_image(self):
        """检测图片"""
        if self.current_image is None:
            messagebox.showwarning("警告", "请先加载图片")
            return
        
        if self.model is None:
            messagebox.showerror("错误", "模型未加载")
            return
        
        # 在线程中运行检测以避免界面冻结
        thread = threading.Thread(target=self._detect_thread)
        thread.daemon = True
        thread.start()
    
    def _detect_thread(self):
        """检测线程"""
        try:
            self.status_var.set("正在检测...")
            self.root.update()
            
            # 获取参数
            conf_threshold = self.conf_var.get()
            iou_threshold = self.iou_var.get()
            input_size = int(self.size_var.get())
            
            # 预处理
            img_resized, ratio, (dw, dh) = self.letterbox(
                self.current_image, new_shape=(input_size, input_size)
            )
            
            # 转换为 PyTorch 张量
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            img_tensor = torch.from_numpy(img_rgb).permute(2, 0, 1).float()
            img_tensor = img_tensor.unsqueeze(0) / 255.0  # [1, 3, H, W]
            img_tensor = img_tensor.to(self.device)
            
            # 推理
            with torch.no_grad():
                outputs = self.model(img_tensor)
            
            # 处理输出
            # YOLOv5 输出格式: (predictions, features)
            if isinstance(outputs, tuple):
                predictions = outputs[0]
            else:
                predictions = outputs
            
            # 转换为 numpy
            predictions = predictions.cpu().numpy()
            
            # 后处理
            boxes, scores, class_ids = self.process_output(
                predictions, conf_threshold, iou_threshold
            )
            
            # 转换坐标到原图
            img_h, img_w = self.current_image.shape[:2]
            if len(boxes) > 0:
                boxes[:, [0, 2]] -= dw
                boxes[:, [1, 3]] -= dh
                boxes[:, [0, 2]] /= ratio[0]
                boxes[:, [1, 3]] /= ratio[1]
                boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, img_w)
                boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, img_h)
            
            # 绘制结果
            self.result_image = self.draw_boxes(
                self.current_image.copy(), boxes, scores, class_ids
            )
            
            # 显示结果
            self.root.after(0, self.display_image, self.result_image, self.result_canvas)
            
            # 更新结果文本
            result_text = f"检测到 {len(boxes)} 个文本区域\n"
            for i, (box, score, class_id) in enumerate(zip(boxes, scores, class_ids)):
                x1, y1, x2, y2 = box.astype(int)
                w, h = x2 - x1, y2 - y1
                result_text += f"  区域 {i+1}: 位置=({x1},{y1},{x2},{y2}) 大小={w}x{h} 置信度={score:.3f}\n"
            
            self.root.after(0, self.update_result_text, result_text)
            self.status_var.set(f"检测完成 - 找到 {len(boxes)} 个文本区域")
            
        except Exception as e:
            self.root.after(0, messagebox.showerror, "错误", f"检测失败: {e}")
            self.status_var.set("检测失败")
            import traceback
            traceback.print_exc()
    
    def update_result_text(self, text):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, text)
    
    def save_result(self):
        """保存结果图片（支持中文路径）"""
        if self.result_image is None:
            messagebox.showwarning("警告", "没有检测结果可保存")
            return
        
        filename = filedialog.asksaveasfilename(
            title="保存结果",
            defaultextension=".jpg",
            filetypes=[
                ("JPEG", "*.jpg"),
                ("PNG", "*.png"),
                ("所有文件", "*.*")
            ]
        )
        
        if filename:
            try:
                # 使用 cv2.imencode 支持中文路径
                ext = os.path.splitext(filename)[1]
                if ext.lower() == '.png':
                    encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
                    _, encoded_img = cv2.imencode('.png', self.result_image, encode_param)
                else:
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
                    _, encoded_img = cv2.imencode('.jpg', self.result_image, encode_param)
                
                with open(filename, 'wb') as f:
                    f.write(encoded_img)
                
                messagebox.showinfo("成功", f"结果已保存到:\n{filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
    
    @staticmethod
    def letterbox(im, new_shape=(640, 640), color=(114, 114, 114)):
        """调整图片大小并添加边框"""
        shape = im.shape[:2]
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)
        
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        ratio = r, r
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
        dw /= 2
        dh /= 2
        
        if shape[::-1] != new_unpad:
            im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
        
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        return im, ratio, (dw, dh)
    
    @staticmethod
    def xywh2xyxy(x):
        """转换边界框格式"""
        y = np.copy(x)
        y[..., 0] = x[..., 0] - x[..., 2] / 2
        y[..., 1] = x[..., 1] - x[..., 3] / 2
        y[..., 2] = x[..., 0] + x[..., 2] / 2
        y[..., 3] = x[..., 1] + x[..., 3] / 2
        return y
    
    @staticmethod
    def nms(boxes, scores, iou_threshold=0.45):
        """非极大值抑制"""
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]
        
        return keep
    
    def process_output(self, output, conf_threshold=0.4, iou_threshold=0.45):
        """处理 YOLO 输出"""
        predictions = output[0]
        obj_conf = predictions[:, 4]
        mask = obj_conf > conf_threshold
        predictions = predictions[mask]
        
        if len(predictions) == 0:
            return np.array([]), np.array([]), np.array([])
        
        boxes = predictions[:, :4]
        scores = predictions[:, 4]
        
        if predictions.shape[1] > 5:
            class_scores = predictions[:, 5:]
            class_ids = np.argmax(class_scores, axis=1)
            class_conf = np.max(class_scores, axis=1)
            scores = scores * class_conf
        else:
            class_ids = np.zeros(len(scores), dtype=np.int32)
        
        boxes = self.xywh2xyxy(boxes)
        indices = self.nms(boxes, scores, iou_threshold)
        
        return boxes[indices], scores[indices], class_ids[indices]
    
    @staticmethod
    def draw_boxes(img, boxes, scores, class_ids):
        """在图片上绘制检测框"""
        colors = [
            (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255), (128, 255, 0), (255, 128, 0)
        ]
        
        for i, (box, score, class_id) in enumerate(zip(boxes, scores, class_ids)):
            x1, y1, x2, y2 = box.astype(int)
            color = colors[int(class_id) % len(colors)]
            
            # 绘制矩形框（加粗）
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
            
            # 绘制半透明填充
            overlay = img.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
            
            # 添加文本标签
            label = f"#{i+1} {score:.2f}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            
            (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # 标签背景
            cv2.rectangle(img, (x1, y1 - label_h - 10), (x1 + label_w + 10, y1), color, -1)
            # 标签文字
            cv2.putText(img, label, (x1 + 5, y1 - 5), font, font_scale, (255, 255, 255), thickness)
            
            # 绘制中心点
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            cv2.circle(img, (center_x, center_y), 5, color, -1)
        
        return img


def main():
    root = tk.Tk()
    app = YSGYOLOPyTorchDetectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

