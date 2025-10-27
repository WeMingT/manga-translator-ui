"""
YSGYOLO 模型检测可视化工具 - 使用 Ultralytics YOLO
支持 .pt 格式模型，基于用户提供的代码改造
"""
import cv2
import numpy as np
import torch
from ultralytics import YOLO
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import os


class YSGYOLOUltralyticsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YSGYOLO 文本检测可视化工具 (Ultralytics)")
        self.root.geometry("1200x850")
        
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
        
        # 第一行：文件操作
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="图片路径:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.path_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="浏览", command=self.browse_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="检测", command=self.detect_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="保存结果", command=self.save_result).pack(side=tk.LEFT, padx=5)
        
        # 第二行：检测参数
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=2)
        
        # 置信度阈值
        ttk.Label(row2, text="置信度:").pack(side=tk.LEFT, padx=5)
        self.conf_var = tk.DoubleVar(value=0.5)
        conf_scale = ttk.Scale(row2, from_=0.1, to=0.9, variable=self.conf_var, 
                              orient=tk.HORIZONTAL, length=120)
        conf_scale.pack(side=tk.LEFT, padx=5)
        self.conf_label = ttk.Label(row2, text="0.50")
        self.conf_label.pack(side=tk.LEFT, padx=5)
        self.conf_var.trace('w', self.update_conf_label)
        
        # IOU 阈值
        ttk.Label(row2, text="IOU:").pack(side=tk.LEFT, padx=5)
        self.iou_var = tk.DoubleVar(value=0.5)
        iou_scale = ttk.Scale(row2, from_=0.1, to=0.9, variable=self.iou_var, 
                             orient=tk.HORIZONTAL, length=120)
        iou_scale.pack(side=tk.LEFT, padx=5)
        self.iou_label = ttk.Label(row2, text="0.50")
        self.iou_label.pack(side=tk.LEFT, padx=5)
        self.iou_var.trace('w', self.update_iou_label)
        
        # 图片尺寸
        ttk.Label(row2, text="尺寸:").pack(side=tk.LEFT, padx=5)
        self.size_var = tk.StringVar(value="640")
        size_combo = ttk.Combobox(row2, textvariable=self.size_var, 
                                 values=["320", "416", "512", "640", "800", "1024"], width=8)
        size_combo.pack(side=tk.LEFT, padx=5)
        
        # 第三行：边界框扩展参数
        row3 = ttk.Frame(control_frame)
        row3.pack(fill=tk.X, pady=2)
        
        ttk.Label(row3, text="边框扩展 (像素):").pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row3, text="上:").pack(side=tk.LEFT, padx=2)
        self.expand_top = tk.IntVar(value=0)
        ttk.Spinbox(row3, from_=0, to=50, textvariable=self.expand_top, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(row3, text="下:").pack(side=tk.LEFT, padx=2)
        self.expand_bottom = tk.IntVar(value=0)
        ttk.Spinbox(row3, from_=0, to=50, textvariable=self.expand_bottom, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(row3, text="左:").pack(side=tk.LEFT, padx=2)
        self.expand_left = tk.IntVar(value=0)
        ttk.Spinbox(row3, from_=0, to=50, textvariable=self.expand_left, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(row3, text="右:").pack(side=tk.LEFT, padx=2)
        self.expand_right = tk.IntVar(value=0)
        ttk.Spinbox(row3, from_=0, to=50, textvariable=self.expand_right, width=5).pack(side=tk.LEFT, padx=2)
        
        # 保存标签选项
        self.save_labels_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="保存 YOLO 标签", variable=self.save_labels_var).pack(side=tk.LEFT, padx=10)
        
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
    
    def check_gpu(self):
        """检查 GPU 可用性"""
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024
            return True, f"{gpu_name} ({total_memory:.0f}MB)"
        return False, "CPU"
    
    def load_model(self):
        """加载 YOLO 模型"""
        try:
            self.status_var.set("正在加载模型...")
            self.root.update()
            
            # 检测设备
            use_gpu, device_info = self.check_gpu()
            self.device = "cuda" if use_gpu else "cpu"
            
            # 加载 YOLO 模型
            self.model = YOLO(self.model_path, task='detect')
            
            self.status_var.set(f"模型已加载 (使用 {device_info})")
            
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
            img_size = int(self.size_var.get())
            
            # 清理 GPU 缓存
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            # 保存临时文件（用于 YOLO 推理）
            temp_path = "temp_detect_image.jpg"
            cv2.imwrite(temp_path, self.current_image)
            
            # YOLO 推理
            results = self.model.predict(
                source=temp_path,
                save=False,
                show=False,
                device=self.device,
                verbose=False,
                conf=conf_threshold,
                iou=iou_threshold,
                imgsz=img_size
            )
            
            # 删除临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            result = results[0]
            
            # 检查是否有检测结果
            if result.boxes is None or len(result.boxes) == 0:
                self.root.after(0, messagebox.showinfo, "提示", "未检测到任何文本区域")
                self.status_var.set("未检测到文本区域")
                # 使用原图作为结果
                self.result_image = self.current_image.copy()
                self.root.after(0, self.display_image, self.result_image, self.result_canvas)
                return
            
            # 获取边框扩展参数
            expand_values = (
                self.expand_top.get(),
                self.expand_bottom.get(),
                self.expand_left.get(),
                self.expand_right.get()
            )
            
            # 处理结果
            boxes_data = []
            img_h, img_w = self.current_image.shape[:2]
            
            for box in result.boxes:
                cls = int(box.cls[0])
                bbox = box.xywhn[0].tolist()  # [x_center, y_center, width, height] 归一化
                conf = float(box.conf[0])
                
                # 应用边框扩展
                adjusted_bbox = self.adjust_bbox(
                    bbox, expand_values, img_w, img_h
                )
                
                boxes_data.append({
                    'class': cls,
                    'bbox_norm': adjusted_bbox,
                    'conf': conf,
                    'class_name': self.model.names[cls] if hasattr(self.model, 'names') else str(cls)
                })
            
            # 保存标签文件（如果启用）
            if self.save_labels_var.get() and self.current_image_path:
                self.save_yolo_labels(boxes_data)
            
            # 绘制结果
            self.result_image = self.draw_boxes_custom(
                self.current_image.copy(), boxes_data, img_w, img_h
            )
            
            # 显示结果
            self.root.after(0, self.display_image, self.result_image, self.result_canvas)
            
            # 更新结果文本
            result_text = f"检测到 {len(boxes_data)} 个文本区域\n"
            for i, box_data in enumerate(boxes_data):
                bbox = box_data['bbox_norm']
                x_center, y_center, width, height = bbox
                x1 = int((x_center - width / 2) * img_w)
                y1 = int((y_center - height / 2) * img_h)
                x2 = int((x_center + width / 2) * img_w)
                y2 = int((y_center + height / 2) * img_h)
                w, h = x2 - x1, y2 - y1
                result_text += f"  区域 {i+1}: {box_data['class_name']} 位置=({x1},{y1},{x2},{y2}) 大小={w}x{h} 置信度={box_data['conf']:.3f}\n"
            
            self.root.after(0, self.update_result_text, result_text)
            self.status_var.set(f"检测完成 - 找到 {len(boxes_data)} 个文本区域")
            
        except Exception as e:
            self.root.after(0, messagebox.showerror, "错误", f"检测失败: {e}")
            self.status_var.set("检测失败")
            import traceback
            traceback.print_exc()
    
    def adjust_bbox(self, bbox, expand_values, img_width, img_height):
        """调整边界框（应用扩展）"""
        x_center, y_center, width, height = bbox
        top, bottom, left, right = expand_values
        
        # 转换扩展像素为归一化值
        expand_top = top / img_height
        expand_bottom = bottom / img_height
        expand_left = left / img_width
        expand_right = right / img_width
        
        # 应用扩展
        new_width = min(1.0, max(0, width + expand_left + expand_right))
        new_height = min(1.0, max(0, height + expand_top + expand_bottom))
        
        # 调整中心点
        x_center = max(new_width / 2, min(1 - new_width / 2, 
                                         x_center + (expand_right - expand_left) / 2))
        y_center = max(new_height / 2, min(1 - new_height / 2, 
                                           y_center + (expand_bottom - expand_top) / 2))
        
        return [x_center, y_center, new_width, new_height]
    
    def save_yolo_labels(self, boxes_data):
        """保存 YOLO 格式标签文件"""
        if not self.current_image_path:
            return
        
        # 创建标签目录
        label_dir = os.path.join(os.path.dirname(self.current_image_path), "biaoqianTXT")
        os.makedirs(label_dir, exist_ok=True)
        
        # 保存标签
        image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        label_path = os.path.join(label_dir, f"{image_name}.txt")
        
        with open(label_path, 'w') as f:
            for box_data in boxes_data:
                bbox = box_data['bbox_norm']
                f.write(f"{box_data['class']} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")
        
        print(f"标签已保存: {label_path}")
    
    def draw_boxes_custom(self, img, boxes_data, img_w, img_h):
        """绘制检测框"""
        colors = [
            (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255), (128, 255, 0), (255, 128, 0)
        ]
        
        for i, box_data in enumerate(boxes_data):
            bbox = box_data['bbox_norm']
            x_center, y_center, width, height = bbox
            
            # 转换为像素坐标
            x1 = int((x_center - width / 2) * img_w)
            y1 = int((y_center - height / 2) * img_h)
            x2 = int((x_center + width / 2) * img_w)
            y2 = int((y_center + height / 2) * img_h)
            
            color = colors[box_data['class'] % len(colors)]
            
            # 绘制矩形框
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
            
            # 半透明填充
            overlay = img.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
            
            # 标签
            label = f"#{i+1} {box_data['class_name']} {box_data['conf']:.2f}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            
            (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            cv2.rectangle(img, (x1, y1 - label_h - 10), (x1 + label_w + 10, y1), color, -1)
            cv2.putText(img, label, (x1 + 5, y1 - 5), font, font_scale, (255, 255, 255), thickness)
            
            # 中心点
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            cv2.circle(img, (center_x, center_y), 5, color, -1)
        
        return img
    
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


def main():
    root = tk.Tk()
    app = YSGYOLOUltralyticsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

