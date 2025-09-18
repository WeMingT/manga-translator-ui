import os
import re
import cv2
import numpy as np
import freetype
import functools
import logging
from pathlib import Path
from typing import Tuple, Optional, List
from hyphen import Hyphenator
from hyphen.dictools import LANGUAGES as HYPHENATOR_LANGUAGES
from langcodes import standardize_tag

from ..utils import BASE_PATH, is_punctuation, is_whitespace, imwrite_unicode

try:
    HYPHENATOR_LANGUAGES.remove('fr')
    HYPHENATOR_LANGUAGES.append('fr_FR')
except Exception:
    pass

CJK_H2V = {
    "‥": "︰",
    "—": "︱",
    "―": "|",
    "–": "︲",
    "_": "︳",
    "_": "︴",
    "(": "︵",
    ")": "︶",
    "（": "︵",
    "）": "︶",
    "{": "︷",
    "}": "︸",
    "〔": "︹",
    "〕": "︺",
    "【": "︻",
    "】": "︼",
    "《": "︽",
    "》": "︾",
    "〈": "︿",
    "〉": "﹀",
    "⟨": "︿",   
    "⟩": "﹀",   
    "⟪": "︿",   
    "⟫": "﹀",       
    "「": "﹁",
    "」": "﹂",
    "『": "﹃",
    "』": "﹄",
    "﹑": "﹅",
    "﹆": "﹆",
    "[": "﹇",
    "]": "﹈",
    "⦅": "︵",   
    "⦆": "︶",   
    "❨": "︵",          
    "❩": "︶",   
    "❪": "︷",   
    "❫": "︸",   
    "❬": "﹇",   
    "❭": "﹈",   
    "❮": "︿",   
    "❯": "﹀",    
    "﹉": "﹉",
    "﹊": "﹊",
    "﹋": "﹋",
    "﹌": "﹌",
    "﹍": "﹍",
    "﹎": "﹎",
    "﹏": "﹏",
    "…": "⋮",
    "⋯": "︙", 
    "⋰": "⋮",    
    "⋱": "⋮",           
    "\"": "﹁",   
    "\"": "﹂",   
    "'": "﹁",   
    "'": "﹂",   
    "″": "﹂",   
    "‴": "﹂",   
    "‶": "﹁",   
    "ⷷ": "﹁",   
    "~": "︴",   
    "〜": "︴",   
    "～": "︴",   
    "~": "≀",
    "〰": "︴",
    "!": "︕",    
    "?": "︖",    
    "؟": "︖",    
    "¿": "︖",    
    "¡": "︕",    
    ".": "︒",    
    "。": "︒",   
    ";": "︔",    
    "；": "︔",   
    ":": "︓",    
    "：": "︓",  
    ",": "︐",    
    "，": "︐",   
    # "､": "︐",    
    "‚": "︐",    
    "„": "︐",    
    # "、": "︑",    
    "-": "︲",    
    "−": "︲",
    "・": "·",          
}

CJK_V2H = {
    **dict(zip(CJK_H2V.items(), CJK_H2V.keys())),
}

logger = logging.getLogger(__name__)  
logger.addHandler(logging.NullHandler())  

DEFAULT_FONT = os.path.join(BASE_PATH, 'fonts', 'Arial-Unicode-Regular.ttf')
FONT = freetype.Face(Path(DEFAULT_FONT).open('rb'))  

def CJK_Compatibility_Forms_translate(cdpt: str, direction: int):
    """direction: 0 - horizontal, 1 - vertical"""
    if cdpt == 'ー' and direction == 1:
        return 'ー', 90
    if cdpt in CJK_V2H:
        if direction == 0:
            # translate
            return CJK_V2H[cdpt], 0
        else:
            return cdpt, 0
    elif cdpt in CJK_H2V:
        if direction == 1:
            # translate
            return CJK_H2V[cdpt], 0
        else:
            return cdpt, 0
    return cdpt, 0

def compact_special_symbols(text: str) -> str:
    text = text.replace('...', '…')  
    text = text.replace('..', '…')      
    # Remove half-width and full-width spaces after each punctuation mark
    pattern = r'([^WSws])[ 　]+'  
    text = re.sub(pattern, r'\1', text) 
    return text
    
def rotate_image(image, angle):
    if angle == 0:
        return image, (0, 0)
    image_exp = np.zeros((round(image.shape[0] * 1.5), round(image.shape[1] * 1.5), image.shape[2]), dtype = np.uint8)
    diff_i = (image_exp.shape[0] - image.shape[0]) // 2
    diff_j = (image_exp.shape[1] - image.shape[1]) // 2
    image_exp[diff_i:diff_i+image.shape[0], diff_j:diff_j+image.shape[1]] = image
    # from https://stackoverflow.com/questions/9041681/opencv-python-rotate-image-by-x-degrees-around-specific-point
    image_center = tuple(np.array(image_exp.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    result = cv2.warpAffine(image_exp, rot_mat, image_exp.shape[1::-1], flags=cv2.INTER_LINEAR)
    if angle == 90:
        return result, (0, 0)
    return result, (diff_i, diff_j)

def add_color(bw_char_map, color, stroke_char_map, stroke_color):
    if bw_char_map.size == 0:
        fg = np.zeros((bw_char_map.shape[0], bw_char_map.shape[1], 4), dtype = np.uint8)
        return fg
    
    if stroke_color is None :
        x, y, w, h = cv2.boundingRect(bw_char_map)
    else :
        x, y, w, h = cv2.boundingRect(stroke_char_map)

    fg = np.zeros((h, w, 4), dtype = np.uint8)
    fg[:,:,0] = color[0]
    fg[:,:,1] = color[1]
    fg[:,:,2] = color[2]
    fg[:,:,3] = bw_char_map[y:y+h, x:x+w]

    if stroke_color is None :
        stroke_color = color
    bg = np.zeros((stroke_char_map.shape[0], stroke_char_map.shape[1], 4), dtype = np.uint8)
    bg[:,:,0] = stroke_color[0]
    bg[:,:,1] = stroke_color[1]
    bg[:,:,2] = stroke_color[2]
    bg[:,:,3] = stroke_char_map

    fg_alpha = fg[:, :, 3] / 255.0
    bg_alpha = 1.0 - fg_alpha
    bg[y:y+h, x:x+w, :] = (fg_alpha[:, :, np.newaxis] * fg[:, :, :] + bg_alpha[:, :, np.newaxis] * bg[y:y+h, x:x+w, :])

    return bg

FALLBACK_FONTS = [
    os.path.join(BASE_PATH, 'fonts/Arial-Unicode-Regular.ttf'),
    os.path.join(BASE_PATH, 'fonts/msyh.ttc'),
    os.path.join(BASE_PATH, 'fonts/msgothic.ttc'),
]
FONT_SELECTION: List[freetype.Face] = []
font_cache = {}
def get_cached_font(path: str) -> freetype.Face:
    path = path.replace('\\', '/')
    if not font_cache.get(path):
        font_cache[path] = freetype.Face(Path(path).open('rb'))
    return font_cache[path]

def update_font_selection():
    global FONT_SELECTION
    FONT_SELECTION = []
    if FONT:
        FONT_SELECTION.append(FONT)
    for font_path in FALLBACK_FONTS:
        try:
            face = get_cached_font(font_path)
            if face and face not in FONT_SELECTION:
                FONT_SELECTION.append(face)
        except Exception as e:
            logger.error(f"Failed to load fallback font: {font_path} - {e}")


def set_font(path: str):
    global FONT
    if not path or not os.path.exists(path):
        if path:
            logger.error(f'Could not load font: {path}')
        try:
            FONT = freetype.Face(Path(DEFAULT_FONT).open('rb'))
        except (freetype.ft_errors.FT_Exception, FileNotFoundError):
            logger.critical("Default font could not be loaded. Please check your installation.")
            FONT = None
        update_font_selection()
        get_char_glyph.cache_clear()
        return

    try:
        FONT = freetype.Face(Path(path).open('rb'))
    except (freetype.ft_errors.FT_Exception, FileNotFoundError):
        logger.error(f'Could not load font: {path}')
        try:
            FONT = freetype.Face(Path(DEFAULT_FONT).open('rb'))
        except (freetype.ft_errors.FT_Exception, FileNotFoundError):
            logger.critical("Default font could not be loaded. Please check your installation.")
            FONT = None
    update_font_selection()
    get_char_glyph.cache_clear()

class namespace:
    pass

class Glyph:
    def __init__(self, glyph):
        self.bitmap = namespace()
        self.bitmap.buffer = glyph.bitmap.buffer
        self.bitmap.rows = glyph.bitmap.rows
        self.bitmap.width = glyph.bitmap.width
        self.advance = namespace()
        self.advance.x = glyph.advance.x
        self.advance.y = glyph.advance.y
        self.bitmap_left = glyph.bitmap_left
        self.bitmap_top = glyph.bitmap_top
        self.metrics = namespace()
        self.metrics.vertBearingX = glyph.metrics.vertBearingX
        self.metrics.vertBearingY = glyph.metrics.vertBearingY
        self.metrics.horiBearingX = glyph.metrics.horiBearingX
        self.metrics.horiBearingY = glyph.metrics.horiBearingY
        self.metrics.horiAdvance = glyph.metrics.horiAdvance
        self.metrics.vertAdvance = glyph.metrics.vertAdvance

@functools.lru_cache(maxsize = 1024, typed = True)
def get_char_glyph(cdpt: str, font_size: int, direction: int) -> Glyph:
    global FONT_SELECTION
    for i, face in enumerate(FONT_SELECTION):
        char_index = face.get_char_index(cdpt)
        if char_index == 0 and i != len(FONT_SELECTION) - 1:
            # Log fallback only on the primary font for clarity
            if i == 0:
                try:
                    font_name = face.family_name.decode('utf-8') if face.family_name else 'Unknown'
                    logger.info(f"Character '{cdpt}' not found in primary font '{font_name}'. Trying fallbacks.")
                except Exception:
                    pass # Avoid logging errors within logging
            continue
        
        if direction == 0:
            face.set_pixel_sizes(0, font_size)
        elif direction == 1:
            face.set_pixel_sizes(font_size, 0)
        face.load_char(cdpt)
        return Glyph(face.glyph)

#@functools.lru_cache(maxsize = 1024, typed = True)
def get_char_border(cdpt: str, font_size: int, direction: int):
    global FONT_SELECTION
    for i, face in enumerate(FONT_SELECTION):
        if face.get_char_index(cdpt) == 0 and i != len(FONT_SELECTION) - 1:
            continue
        if direction == 0:
            face.set_pixel_sizes(0, font_size)
        elif direction == 1:
            face.set_pixel_sizes(font_size, 0)
        face.load_char(cdpt, freetype.FT_LOAD_DEFAULT | freetype.FT_LOAD_NO_BITMAP)
        slot_border = face.glyph
        return slot_border.get_glyph()

def calc_vertical(font_size: int, text: str, max_height: int):
    logger.debug(f"[布局调试-垂直] 开始垂直布局计算")
    logger.debug(f"[布局调试-垂直] 字体大小: {font_size}, 最大高度: {max_height}")
    logger.debug(f"[布局调试-垂直] 输入文本: '{text}' (长度: {len(text)})")

    line_text_list = []
    line_height_list = []

    line_str = ""
    line_height = 0
    line_width_left = 0
    line_width_right = 0
    for i, cdpt in enumerate(text):
        logger.debug(f"[布局调试-垂直] 处理字符 {i+1}/{len(text)}: '{cdpt}'")

        if line_height == 0 and cdpt == ' ':
            logger.debug(f"[布局调试-垂直] 跳过行首空格")
            continue

        cdpt, rot_degree = CJK_Compatibility_Forms_translate(cdpt, 1)
        ckpt = get_char_glyph(cdpt, font_size, 1)
        bitmap = ckpt.bitmap

        if bitmap.rows * bitmap.width == 0 or len(bitmap.buffer) != bitmap.rows * bitmap.width:
            char_offset_y = ckpt.metrics.vertBearingY >> 6
        else:
            char_offset_y = ckpt.metrics.vertAdvance >> 6

        char_width = bitmap.width
        char_bearing_x = ckpt.metrics.vertBearingX >> 6

        logger.debug(f"[布局调试-垂直] 字符'{cdpt}' - 高度偏移: {char_offset_y}, 宽度: {char_width}, 水平偏移: {char_bearing_x}")

        if line_height + char_offset_y > max_height:
            logger.debug(f"[布局调试-垂直] 超出高度限制: {line_height + char_offset_y} > {max_height}")
            line_text_list.append(line_str)
            line_height_list.append(line_height)
            logger.debug(f"[布局调试-垂直] 完成一列: '{line_str}', 高度: {line_height}")

            line_str = ""
            line_height = 0
            line_width_left = 0
            line_width_right = 0

        line_height += char_offset_y
        line_str += cdpt
        line_width_left = max(line_width_left, abs(char_bearing_x))
        line_width_right = max(line_width_right, char_width - abs(char_bearing_x))

        logger.debug(f"[布局调试-垂直] 当前列状态 - 文本: '{line_str}', 高度: {line_height}, 左宽: {line_width_left}, 右宽: {line_width_right}")

    line_text_list.append(line_str)
    line_height_list.append(line_height)
    logger.debug(f"[布局调试-垂直] 最后一列: '{line_str}', 高度: {line_height}")

    logger.debug(f"[布局调试-垂直] 完成垂直布局计算，总列数: {len(line_text_list)}")
    for i, (text, height) in enumerate(zip(line_text_list, line_height_list)):
        logger.debug(f"[布局调试-垂直] 最终第{i+1}列: '{text}', 高度: {height}")

    return line_text_list, line_height_list

def put_char_vertical(font_size: int, cdpt: str, pen_l: Tuple[int, int], canvas_text: np.ndarray, canvas_border: np.ndarray, border_size: int):  
    pen = pen_l.copy()  
    is_pun = is_punctuation(cdpt)  
    cdpt, rot_degree = CJK_Compatibility_Forms_translate(cdpt, 1)  
    slot = get_char_glyph(cdpt, font_size, 1)  
    bitmap = slot.bitmap
    char_bitmap_rows = bitmap.rows  
    char_bitmap_width = bitmap.width  
    if char_bitmap_rows * char_bitmap_width == 0 or len(bitmap.buffer) != char_bitmap_rows * char_bitmap_width:  
        if hasattr(slot, 'metrics') and hasattr(slot.metrics, 'vertAdvance') and slot.metrics.vertAdvance:  
             char_offset_y = slot.metrics.vertAdvance >> 6  
        elif hasattr(slot, 'advance') and slot.advance.y:  
             char_offset_y = slot.advance.y >> 6  
        elif hasattr(slot, 'metrics') and hasattr(slot.metrics, 'vertBearingY'):  
             char_offset_y = slot.metrics.vertBearingY >> 6  
        else:  
             char_offset_y = font_size  
        return char_offset_y  
    char_offset_y = slot.metrics.vertAdvance >> 6  
    bitmap_char = np.array(bitmap.buffer, dtype=np.uint8).reshape((char_bitmap_rows, char_bitmap_width))  
    char_place_x = pen[0] + (slot.metrics.vertBearingX >> 6)  
    char_place_y = pen[1] + (slot.metrics.vertBearingY >> 6)   
    paste_y_start = max(0, char_place_y)  
    paste_x_start = max(0, char_place_x)  
    paste_y_end = min(canvas_text.shape[0], char_place_y + char_bitmap_rows)  
    paste_x_end = min(canvas_text.shape[1], char_place_x + char_bitmap_width)  
    if paste_y_start >= paste_y_end or paste_x_start >= paste_x_end:  
        logger.warning(f"Char '{cdpt}' is completely outside the canvas or on the boundary, skipped. Position: x={char_place_x}, y={char_place_y}, Canvas size: {canvas_text.shape}")      
    else:       
        bitmap_char_slice = bitmap_char[paste_y_start-char_place_y : paste_y_end-char_place_y,   
                                        paste_x_start-char_place_x : paste_x_end-char_place_x]
        if bitmap_char_slice.size > 0:       
            canvas_text[paste_y_start:paste_y_end, paste_x_start:paste_x_end] = bitmap_char_slice        
    if border_size > 0:  
        glyph_border = get_char_border(cdpt, font_size, 1)  
        stroker = freetype.Stroker()  
        stroke_radius = 64 * max(int(0.07 * font_size), 1)
        stroker.set(stroke_radius, freetype.FT_STROKER_LINEJOIN_ROUND, freetype.FT_STROKER_LINECAP_ROUND, 0)  
        glyph_border.stroke(stroker, destroy=True)  
        blyph = glyph_border.to_bitmap(freetype.FT_RENDER_MODE_NORMAL, freetype.Vector(0, 0), True)  
        bitmap_b = blyph.bitmap
        border_bitmap_rows = bitmap_b.rows  
        border_bitmap_width = bitmap_b.width  
        if border_bitmap_rows * border_bitmap_width > 0 and len(bitmap_b.buffer) == border_bitmap_rows * border_bitmap_width:  
            bitmap_border = np.array(bitmap_b.buffer, dtype=np.uint8).reshape((border_bitmap_rows, border_bitmap_width))  
            char_center_offset_x = char_bitmap_width / 2.0  
            char_center_offset_y = char_bitmap_rows / 2.0  
            border_center_offset_x = border_bitmap_width / 2.0  
            border_center_offset_y = border_bitmap_rows / 2.0  
            char_center_on_canvas_x = char_place_x + char_center_offset_x  
            char_center_on_canvas_y = char_place_y + char_center_offset_y  
            pen_border_x_float = char_center_on_canvas_x - border_center_offset_x  
            pen_border_y_float = char_center_on_canvas_y - border_center_offset_y  
            pen_border_x = int(round(pen_border_x_float))  
            pen_border_y = int(round(pen_border_y_float))  
            pen_border = (max(0, pen_border_x), max(0, pen_border_y))  
            paste_border_y_start = pen_border[1]  
            paste_border_x_start = pen_border[0]  
            paste_border_y_end = min(canvas_border.shape[0], pen_border[1] + border_bitmap_rows)  
            paste_border_x_end = min(canvas_border.shape[1], pen_border[0] + border_bitmap_width)  
            if paste_border_y_start >= paste_border_y_end or paste_border_x_start >= paste_border_x_end:  
                logger.warning(f"The border of char '{cdpt}' is completely outside the canvas or on the boundary, skipped. Position: x={pen_border[0]}, y={pen_border[1]}, Canvas size: {canvas_border.shape}")  
            else:        
                bitmap_border_slice = bitmap_border[0 : paste_border_y_end-paste_border_y_start,   
                                                    0 : paste_border_x_end-paste_border_x_start]
                if bitmap_border_slice.size > 0:
                    target_slice = canvas_border[paste_border_y_start:paste_border_y_end,   
                                                 paste_border_x_start:paste_border_x_end]  
                    if target_slice.shape == bitmap_border_slice.shape:  
                        canvas_border[paste_border_y_start:paste_border_y_end,   
                                      paste_border_x_start:paste_border_x_end] = cv2.add(target_slice, bitmap_border_slice)  
                    else:  
                        logger.warning(f"Shape mismatch: target={{target_slice.shape}}, source={{bitmap_border_slice.shape}}")  
    return char_offset_y  

def put_text_vertical(font_size: int, text: str, h: int, alignment: str, fg: Tuple[int, int, int], bg: Optional[Tuple[int, int, int]], line_spacing: int):
    logger.debug(f"[文本渲染调试-垂直] 开始垂直文本渲染")
    logger.debug(f"[文本渲染调试-垂直] 输入参数 - 字体大小: {font_size}, 文本: '{text}'")
    logger.debug(f"[文本渲染调试-垂直] 高度限制: {h}, 对齐: {alignment}, 行间距: {line_spacing}")
    logger.debug(f"[文本渲染调试-垂直] 前景色: RGB{fg}, 背景色: RGB{bg}")

    text = compact_special_symbols(text)
    if not text :
        logger.debug(f"[文本渲染调试-垂直] 文本为空，返回")
        return

    bg_size = int(max(font_size * 0.07, 1)) if bg is not None else 0
    spacing_x = int(font_size * (line_spacing or 0.2))
    logger.debug(f"[文本渲染调试-垂直] 边框大小: {bg_size}, 水平间距: {spacing_x}")

    num_char_y = h // font_size
    num_char_x = len(text) // num_char_y + 1
    logger.debug(f"[文本渲染调试-垂直] 估算 - 垂直字符数: {num_char_y}, 水平列数: {num_char_x}")

    canvas_x = font_size * num_char_x + spacing_x * (num_char_x - 1) + (font_size + bg_size) * 2
    canvas_y = font_size * num_char_y + (font_size + bg_size) * 2
    logger.debug(f"[文本渲染调试-垂直] 初始画布尺寸: {canvas_x} x {canvas_y}")

    line_text_list, line_height_list = calc_vertical(font_size, text, h)
    logger.debug(f"[文本渲染调试-垂直] 计算结果 - 列数: {len(line_text_list)}")
    for i, (line_text, line_height) in enumerate(zip(line_text_list, line_height_list)):
        logger.debug(f"[文本渲染调试-垂直] 第{i+1}列: '{line_text}', 高度: {line_height}")

    canvas_text = np.zeros((canvas_y, canvas_x), dtype=np.uint8)
    canvas_border = canvas_text.copy()
    pen_orig = [canvas_text.shape[1] - (font_size + bg_size), font_size + bg_size]
    logger.debug(f"[文本渲染调试-垂直] 初始笔位: {pen_orig}")

    for line_idx, (line_text, line_height) in enumerate(zip(line_text_list, line_height_list)):
        pen_line = pen_orig.copy()
        logger.debug(f"[文本渲染调试-垂直] 处理第{line_idx+1}列，初始笔位: {pen_line}")

        if alignment == 'center':
            pen_line[1] += (max(line_height_list) - line_height) // 2
            logger.debug(f"[文本渲染调试-垂直] 居中对齐，调整后笔位: {pen_line}")
        elif alignment == 'right':
            pen_line[1] += max(line_height_list) - line_height
            logger.debug(f"[文本渲染调试-垂直] 右对齐（底部），调整后笔位: {pen_line}")

        for char_idx, c in enumerate(line_text):
            offset_y = put_char_vertical(font_size, c, pen_line, canvas_text, canvas_border, border_size=bg_size)
            pen_line[1] += offset_y
            logger.debug(f"[文本渲染调试-垂直] 字符'{c}'渲染完成，偏移: {offset_y}, 新笔位: {pen_line}")
        pen_orig[0] -= spacing_x + font_size
        logger.debug(f"[文本渲染调试-垂直] 第{line_idx+1}列完成，下一列笔位X: {pen_orig[0]}")

    canvas_border = np.clip(canvas_border, 0, 255)
    line_box = add_color(canvas_text, fg, canvas_border, bg)
    combined_canvas = cv2.add(canvas_text, canvas_border)
    x, y, w, h = cv2.boundingRect(combined_canvas)
    logger.debug(f"[文本渲染调试-垂直] 最终裁剪区域: x={x}, y={y}, w={w}, h={h}")
    result = line_box[y:y+h, x:x+w]
    logger.debug(f"[文本渲染调试-垂直] 垂直文本渲染完成，最终尺寸: {result.shape}")
    return result

def select_hyphenator(lang: str):
    lang = standardize_tag(lang)
    if lang not in HYPHENATOR_LANGUAGES:
        for avail_lang in reversed(HYPHENATOR_LANGUAGES):
            if avail_lang.startswith(lang):
                lang = avail_lang
                break
        else:
            return None
    try:
        return Hyphenator(lang)
    except Exception:
        return None

def get_char_offset_x(font_size: int, cdpt: str):
    if cdpt == '＿':
        # Return the width of a full-width space for the placeholder
        return get_char_offset_x(font_size, '　')

    c, rot_degree = CJK_Compatibility_Forms_translate(cdpt, 0)
    glyph = get_char_glyph(c, font_size, 0)
    bitmap = glyph.bitmap
    if bitmap.rows * bitmap.width == 0 or len(bitmap.buffer) != bitmap.rows * bitmap.width:
        char_offset_x = glyph.advance.x >> 6
    else:
        char_offset_x = glyph.metrics.horiAdvance >> 6
    return char_offset_x

def get_string_width(font_size: int, text: str):
    return sum([get_char_offset_x(font_size, c) for c in text])

def calc_horizontal_cjk(font_size: int, text: str, max_width: int) -> Tuple[List[str], List[int]]:
    """
    Line breaking logic for CJK languages with punctuation rules.
    Handles forced newlines (\n) and invisible placeholders (＿).
    """
    logger.debug(f"[布局调试-CJK水平] 开始CJK水平布局计算")
    logger.debug(f"[布局调试-CJK水平] 字体大小: {font_size}, 最大宽度: {max_width}")
    logger.debug(f"[布局调试-CJK水平] 输入文本: '{text}'")

    lines = []
    no_start_chars = "》，。．」』】）！；：？"
    no_end_chars = "《「『【（"
    logger.debug(f"[布局调试-CJK水平] 行首禁则字符: '{no_start_chars}'")
    logger.debug(f"[布局调试-CJK水平] 行尾禁则字符: '{no_end_chars}'")

    paragraphs = text.split('\n')
    logger.debug(f"[布局调试-CJK水平] 分割为 {len(paragraphs)} 个段落")

    for para_idx, paragraph in enumerate(paragraphs):
        logger.debug(f"[布局调试-CJK水平] 处理段落 {para_idx+1}: '{paragraph}'")
        if not paragraph:
            lines.append(("", 0))
            logger.debug(f"[布局调试-CJK水平] 空段落，添加空行")
            continue

        current_line = ""
        current_width = 0
        for char_idx, char in enumerate(paragraph):
            char_width = get_char_offset_x(font_size, char)
            logger.debug(f"[布局调试-CJK水平] 字符'{char}' 宽度: {char_width}")

            if current_width + char_width > max_width and current_line:
                logger.debug(f"[布局调试-CJK水平] 超出宽度限制: {current_width + char_width} > {max_width}")
                if current_line and current_line[-1] in no_end_chars:
                    last_char = current_line[-1]
                    current_line = current_line[:-1]
                    lines.append((current_line, get_string_width(font_size, current_line)))
                    current_line = last_char + char
                    logger.debug(f"[布局调试-CJK水平] 行尾禁则处理，移动字符'{last_char}'到下一行")
                else:
                    lines.append((current_line, current_width))
                    current_line = char
                    logger.debug(f"[布局调试-CJK水平] 换行，当前行: '{lines[-1][0]}'")
                current_width = get_string_width(font_size, current_line)
            elif not current_line and char in no_start_chars:
                logger.debug(f"[布局调试-CJK水平] 行首禁则字符'{char}'")
                if lines:
                    prev_line_text, prev_line_width = lines[-1]
                    lines[-1] = (prev_line_text + char, prev_line_width + char_width)
                    logger.debug(f"[布局调试-CJK水平] 添加到上一行: '{lines[-1][0]}'")
                else:
                    current_line += char
                    current_width += char_width
                    logger.debug(f"[布局调试-CJK水平] 第一行，强制添加")
            else:
                current_line += char
                current_width += char_width
                logger.debug(f"[布局调试-CJK水平] 正常添加字符，当前行: '{current_line}', 宽度: {current_width}")

        if current_line:
            lines.append((current_line, current_width))
            logger.debug(f"[布局调试-CJK水平] 段落结束，最后一行: '{current_line}', 宽度: {current_width}")

    line_text_list = [line[0] for line in lines]
    line_width_list = [line[1] for line in lines]

    logger.debug(f"[布局调试-CJK水平] 完成布局计算，总行数: {len(line_text_list)}")
    for i, (text, width) in enumerate(zip(line_text_list, line_width_list)):
        logger.debug(f"[布局调试-CJK水平] 最终第{i+1}行: '{text}', 宽度: {width}")

    return line_text_list, line_width_list

def calc_horizontal(font_size: int, text: str, max_width: int, max_height: int, language: str = 'en_US', hyphenate: bool = True) -> Tuple[List[str], List[int]]:
    logger.debug(f"[布局调试-标准水平] 开始标准水平布局计算")
    logger.debug(f"[布局调试-标准水平] 字体大小: {font_size}, 最大宽度: {max_width}, 最大高度: {max_height}")
    logger.debug(f"[布局调试-标准水平] 语言: {language}, 连字符: {hyphenate}")
    logger.debug(f"[布局调试-标准水平] 输入文本: '{text}'")

    max_width = max(max_width, 2 * font_size)
    logger.debug(f"[布局调试-标准水平] 调整后最大宽度: {max_width}")

    whitespace_offset_x = get_char_offset_x(font_size, ' ')
    hyphen_offset_x = get_char_offset_x(font_size, '-')
    logger.debug(f"[布局调试-标准水平] 空格宽度: {whitespace_offset_x}, 连字符宽度: {hyphen_offset_x}")

    words = re.split(r'\s+', text)
    logger.debug(f"[布局调试-标准水平] 分割为 {len(words)} 个单词: {words}")

    word_widths = []
    for i, word in enumerate(words):
        width = get_string_width(font_size, word)
        word_widths.append(width)
        logger.debug(f"[布局调试-标准水平] 单词 {i+1} '{word}' 宽度: {width}")

    while True:
        max_lines = max_height // font_size + 1
        expected_size = sum(word_widths) + max((len(word_widths) - 1) * whitespace_offset_x - (max_lines - 1) * hyphen_offset_x, 0)
        max_size = max_width * max_lines
        logger.debug(f"[布局调试-标准水平] 预估计算 - 最大行数: {max_lines}, 期望尺寸: {expected_size}, 最大尺寸: {max_size}")

        if max_size < expected_size:
            multiplier = np.sqrt(expected_size / max_size)
            max_width *= max(multiplier, 1.05)
            max_height *= multiplier
            logger.debug(f"[布局调试-标准水平] 调整尺寸 - 倍数: {multiplier:.3f}, 新宽度: {max_width:.1f}, 新高度: {max_height:.1f}")
        else:
            break

    syllables = []
    hyphenator = select_hyphenator(language)
    logger.debug(f"[布局调试-标准水平] 连字符处理器: {'已找到' if hyphenator else '未找到'}")

    for i, word in enumerate(words):
        new_syls = []
        if hyphenator and len(word) <= 100:
            try:
                new_syls = hyphenator.syllables(word)
                logger.debug(f"[布局调试-标准水平] 单词'{word}'音节分割: {new_syls}")
            except Exception as e:
                logger.debug(f"[布局调试-标准水平] 单词'{word}'音节分割失败: {e}")
                new_syls = []

        if len(new_syls) == 0:
            if len(word) <= 3:
                new_syls = [word]
            else:
                new_syls = list(word)
            logger.debug(f"[布局调试-标准水平] 单词'{word}'使用默认分割: {new_syls}")

        normalized_syls = []
        for syl in new_syls:
            syl_width = get_string_width(font_size, syl)
            if syl_width > max_width:
                normalized_syls.extend(list(syl))
                logger.debug(f"[布局调试-标准水平] 音节'{syl}'过长，按字符拆分")
            else:
                normalized_syls.append(syl)
        syllables.append(normalized_syls)
        logger.debug(f"[布局调试-标准水平] 单词'{word}'最终音节: {normalized_syls}")

    line_words_list = []
    line_width_list = []
    hyphenation_idx_list = []
    line_words = []
    line_width = 0
    hyphenation_idx = 0

    def break_line():
        nonlocal line_words, line_width, hyphenation_idx
        line_words_list.append(line_words)
        line_width_list.append(line_width)
        hyphenation_idx_list.append(hyphenation_idx)
        logger.debug(f"[布局调试-标准水平] 换行 - 当前行单词: {line_words}, 宽度: {line_width}, 连字符索引: {hyphenation_idx}")
        line_words = []
        line_width = 0
        hyphenation_idx = 0

    def get_present_syllables_range(line_idx, word_pos):
        while word_pos < 0:
            word_pos += len(line_words_list[line_idx])
        word_idx = line_words_list[line_idx][word_pos]
        syl_start_idx = 0
        syl_end_idx = len(syllables[word_idx])
        if line_idx > 0 and word_pos == 0 and line_words_list[line_idx - 1][-1] == word_idx:
            syl_start_idx = hyphenation_idx_list[line_idx - 1]
        if line_idx < len(line_words_list) - 1 and word_pos == len(line_words_list[line_idx]) - 1 and line_words_list[line_idx + 1][0] == word_idx:
            syl_end_idx = hyphenation_idx_list[line_idx]
        return syl_start_idx, syl_end_idx

    def get_present_syllables(line_idx, word_pos):
        syl_start_idx, syl_end_idx = get_present_syllables_range(line_idx, word_pos)
        return syllables[line_words_list[line_idx][word_pos]][syl_start_idx:syl_end_idx]

    i = 0
    while True:
        if i >= len(words):
            if line_width > 0:
                break_line()
            break

        current_width = whitespace_offset_x if line_width > 0 else 0
        logger.debug(f"[布局调试-标准水平] 处理单词 {i+1}/{len(words)}: '{words[i]}', 当前行宽: {line_width}, 需要空格: {current_width}")

        if line_width + current_width + word_widths[i] <= max_width + hyphen_offset_x:
            line_words.append(i)
            line_width += current_width + word_widths[i]
            logger.debug(f"[布局调试-标准水平] 单词'{words[i]}'加入当前行，新行宽: {line_width}")
            i += 1
        elif word_widths[i] > max_width:
            logger.debug(f"[布局调试-标准水平] 单词'{words[i]}'过长，需要分割")
            j = 0
            hyphenation_idx = 0
            while j < len(syllables[i]):
                syl = syllables[i][j]
                syl_width = get_string_width(font_size, syl)
                logger.debug(f"[布局调试-标准水平] 检查音节'{syl}', 宽度: {syl_width}")

                if line_width + current_width + syl_width <= max_width:
                    current_width += syl_width
                    j += 1
                    hyphenation_idx = j
                    logger.debug(f"[布局调试-标准水平] 音节'{syl}'可以放入，累计宽度: {current_width}")
                else:
                    if hyphenation_idx > 0:
                        line_words.append(i)
                        line_width += current_width
                        logger.debug(f"[布局调试-标准水平] 部分单词加入行，连字符索引: {hyphenation_idx}")
                    current_width = 0
                    break_line()
            line_words.append(i)
            line_width += current_width
            logger.debug(f"[布局调试-标准水平] 单词'{words[i]}'处理完成")
            i += 1
        else:
            logger.debug(f"[布局调试-标准水平] 单词'{words[i]}'无法放入当前行，换行")
            break_line()

    logger.debug(f"[布局调试-标准水平] 初始布局完成，共 {len(line_words_list)} 行")

    # 连字符优化阶段
    if hyphenate and len(line_words_list) > max_lines:
        logger.debug(f"[布局调试-标准水平] 开始连字符优化，当前行数 {len(line_words_list)} > 最大行数 {max_lines}")
        line_idx = 0
        while line_idx < len(line_words_list) - 1:
            line_words1 = line_words_list[line_idx]
            line_words2 = line_words_list[line_idx + 1]
            left_space = max_width - line_width_list[line_idx]
            logger.debug(f"[布局调试-标准水平-优化] 处理行{line_idx+1}和{line_idx+2}，剩余空间: {left_space}")
            first_word = True
            while len(line_words2) != 0:
                word_idx = line_words2[0]
                logger.debug(f"[布局调试-标准水平-优化] 检查单词索引 {word_idx}: '{words[word_idx]}'")
                if first_word and word_idx == line_words1[-1]:
                    syl_start_idx = hyphenation_idx_list[line_idx]
                    if line_idx < len(line_width_list) - 2 and word_idx == line_words_list[line_idx + 2][0]:
                        syl_end_idx = hyphenation_idx_list[line_idx + 1]
                    else:
                        syl_end_idx = len(syllables[word_idx])
                    logger.debug(f"[布局调试-标准水平-优化] 继续单词，音节范围: {syl_start_idx}-{syl_end_idx}")
                else:
                    left_space -= whitespace_offset_x
                    syl_start_idx = 0
                    syl_end_idx = len(syllables[word_idx]) if len(line_words2) > 1 else hyphenation_idx_list[line_idx + 1]
                    logger.debug(f"[布局调试-标准水平-优化] 新单词，音节范围: {syl_start_idx}-{syl_end_idx}，扣除空格后剩余: {left_space}")
                first_word = False
                current_width = 0
                for i in range(syl_start_idx, syl_end_idx):
                    syl = syllables[word_idx][i]
                    syl_width = get_string_width(font_size, syl)
                    logger.debug(f"[布局调试-标准水平-优化] 音节'{syl}'宽度: {syl_width}")
                    if left_space > current_width + syl_width:
                        current_width += syl_width
                        logger.debug(f"[布局调试-标准水平-优化] 音节可放入，累计宽度: {current_width}")
                    else:
                        if current_width > 0:
                            left_space -= current_width
                            line_width_list[line_idx] = max_width - left_space
                            hyphenation_idx_list[line_idx] = i
                            line_words1.append(word_idx)
                            logger.debug(f"[布局调试-标准水平-优化] 部分单词移动到上一行，连字符索引: {i}")
                        break
                else:
                    left_space -= current_width
                    line_width_list[line_idx] = max_width - left_space
                    line_words1.append(word_idx)
                    line_words2.pop(0)
                    logger.debug(f"[布局调试-标准水平-优化] 整个单词移动到上一行")
                    continue
                break
            if len(line_words2) == 0:
                line_words_list.pop(line_idx + 1)
                line_width_list.pop(line_idx + 1)
                hyphenation_idx_list.pop(line_idx)
                logger.debug(f"[布局调试-标准水平-优化] 第{line_idx+2}行为空，已删除")
            else:
                line_idx += 1

    # 行合并优化阶段
    logger.debug(f"[布局调试-标准水平] 开始行合并优化")
    line_idx = 0
    while line_idx < len(line_words_list) - 1:
        line_words1 = line_words_list[line_idx]
        line_words2 = line_words_list[line_idx + 1]
        merged_word_idx = -1
        logger.debug(f"[布局调试-标准水平-合并] 检查行{line_idx+1}和{line_idx+2}的合并可能性")
        if line_words1[-1] == line_words2[0]:
            word1_text = ''.join(get_present_syllables(line_idx, -1))
            word2_text = ''.join(get_present_syllables(line_idx + 1, 0))
            word1_width = get_string_width(font_size, word1_text)
            word2_width = get_string_width(font_size, word2_text)
            logger.debug(f"[布局调试-标准水平-合并] 跨行单词分析: '{word1_text}'({word1_width}) + '{word2_text}'({word2_width})")
            if len(word2_text) == 1 or word2_width < font_size:
                merged_word_idx = line_words1[-1]
                line_words2.pop(0)
                line_width_list[line_idx] += word2_width
                line_width_list[line_idx + 1] -= word2_width + whitespace_offset_x
                logger.debug(f"[布局调试-标准水平-合并] 第二部分'{word2_text}'太短，合并到上一行")
            elif len(word1_text) == 1 or word1_width < font_size:
                merged_word_idx = line_words1[-1]
                line_words1.pop(-1)
                line_width_list[line_idx] -= word1_width + whitespace_offset_x
                line_width_list[line_idx + 1] += word1_width
                logger.debug(f"[布局调试-标准水平-合并] 第一部分'{word1_text}'太短，移动到下一行")
        if len(line_words1) == 0:
            line_words_list.pop(line_idx)
            line_width_list.pop(line_idx)
            hyphenation_idx_list.pop(line_idx)
            logger.debug(f"[布局调试-标准水平-合并] 第{line_idx+1}行为空，已删除")
        elif len(line_words2) == 0:
            line_words_list.pop(line_idx + 1)
            line_width_list.pop(line_idx + 1)
            hyphenation_idx_list.pop(line_idx)
            logger.debug(f"[布局调试-标准水平-合并] 第{line_idx+2}行为空，已删除")
        elif line_idx >= len(line_words_list) - 1 or line_words_list[line_idx + 1] != merged_word_idx:
            line_idx += 1

    use_hyphen_chars = hyphenate and hyphenator and max_width > 1.5 * font_size and len(words) > 1
    logger.debug(f"[布局调试-标准水平] 使用连字符字符: {use_hyphen_chars}")

    line_text_list = []
    for i, line in enumerate(line_words_list):
        line_text = ''
        for j, word_idx in enumerate(line):
            syl_start_idx, syl_end_idx = get_present_syllables_range(i, j)
            current_syllables = syllables[word_idx][syl_start_idx:syl_end_idx]
            line_text += ''.join(current_syllables)
            if len(line_text) == 0:
                continue
            if j == 0 and i > 0 and line_text_list[-1][-1] == '-' and line_text[0] == '-':
                line_text = line_text[1:]
                line_width_list[i] -= hyphen_offset_x
            if j < len(line) - 1 and len(line_text) > 0:
                line_text += ' '
            elif use_hyphen_chars and syl_end_idx != len(syllables[word_idx]) and len(words[word_idx]) > 3 and line_text[-1] != '-' and not (syl_end_idx < len(syllables[word_idx]) and not re.search(r'\w', syllables[word_idx][syl_end_idx][0])):
                line_text += '-'
                line_width_list[i] += hyphen_offset_x
        line_width_list[i] = get_string_width(font_size, line_text)
        line_text_list.append(line_text)
        logger.debug(f"[布局调试-标准水平] 最终第{i+1}行: '{line_text}', 宽度: {line_width_list[i]}")

    logger.debug(f"[布局调试-标准水平] 完成标准水平布局计算，总行数: {len(line_text_list)}")
    return line_text_list, line_width_list

def put_char_horizontal(font_size: int, cdpt: str, pen_l: Tuple[int, int], canvas_text: np.ndarray, canvas_border: np.ndarray, border_size: int):
    if cdpt == '＿':
        # For the placeholder, just advance the pen and do nothing else.
        return get_char_offset_x(font_size, '＿')

    pen = list(pen_l)
    cdpt, rot_degree = CJK_Compatibility_Forms_translate(cdpt, 0)
    slot = get_char_glyph(cdpt, font_size, 0)
    bitmap = slot.bitmap
    
    if hasattr(slot, 'metrics') and hasattr(slot.metrics, 'horiAdvance') and slot.metrics.horiAdvance:
        char_offset_x = slot.metrics.horiAdvance >> 6
    elif hasattr(slot, 'advance') and slot.advance.x:
        char_offset_x = slot.advance.x >> 6
    elif bitmap.width > 0 and hasattr(slot, 'bitmap_left'):
         char_offset_x = slot.bitmap_left + bitmap.width
    else:
         char_offset_x = font_size // 2
    if bitmap.rows * bitmap.width == 0 or len(bitmap.buffer) != bitmap.rows * bitmap.width:
        return char_offset_x
    bitmap_char = np.array(bitmap.buffer, dtype=np.uint8).reshape((bitmap.rows, bitmap.width))
    char_place_x = pen[0] + slot.bitmap_left
    char_place_y = pen[1] - slot.bitmap_top
    paste_y_start = max(0, char_place_y)
    paste_x_start = max(0, char_place_x)
    paste_y_end = min(canvas_text.shape[0], char_place_y + bitmap.rows)
    paste_x_end = min(canvas_text.shape[1], char_place_x + bitmap.width)
    bitmap_slice_y_start = paste_y_start - char_place_y
    bitmap_slice_x_start = paste_x_start - char_place_x
    bitmap_slice_y_end = bitmap_slice_y_start + (paste_y_end - paste_y_start)
    bitmap_slice_x_end = bitmap_slice_x_start + (paste_x_end - paste_x_start)
    bitmap_char_slice = bitmap_char[
        bitmap_slice_y_start:bitmap_slice_y_end,
        bitmap_slice_x_start:bitmap_slice_x_end
    ]
    if (bitmap_char_slice.size > 0 and 
        bitmap_char_slice.shape == (paste_y_end - paste_y_start,
                                   paste_x_end - paste_x_start)):
        canvas_text[paste_y_start:paste_y_end, 
                    paste_x_start:paste_x_end] = bitmap_char_slice
    if border_size > 0:
        glyph_border = get_char_border(cdpt, font_size, 0)
        stroker = freetype.Stroker()
        stroke_radius = 64 * max(int(0.07 * font_size), 1)
        stroker.set(stroke_radius, 
                   freetype.FT_STROKER_LINEJOIN_ROUND,
                   freetype.FT_STROKER_LINECAP_ROUND,
                   0)
        glyph_border.stroke(stroker, destroy=True)
        blyph = glyph_border.to_bitmap(freetype.FT_RENDER_MODE_NORMAL, 
                                      freetype.Vector(0, 0), True)
        bitmap_b = blyph.bitmap
        border_bitmap_rows = bitmap_b.rows
        border_bitmap_width = bitmap_b.width
        if (border_bitmap_rows * border_bitmap_width > 0 and 
            len(bitmap_b.buffer) == border_bitmap_rows * border_bitmap_width):
            bitmap_border = np.array(bitmap_b.buffer, dtype=np.uint8
                                   ).reshape((border_bitmap_rows, border_bitmap_width))
            char_bitmap_rows = bitmap.rows
            char_bitmap_width = bitmap.width
            char_center_offset_x = char_bitmap_width / 2.0
            char_center_offset_y = char_bitmap_rows / 2.0
            border_center_offset_x = border_bitmap_width / 2.0
            border_center_offset_y = border_bitmap_rows / 2.0
            char_center_on_canvas_x = char_place_x + char_center_offset_x
            char_center_on_canvas_y = char_place_y + char_center_offset_y
            pen_border_x_float = char_center_on_canvas_x - border_center_offset_x
            pen_border_y_float = char_center_on_canvas_y - border_center_offset_y
            pen_border_x = int(round(pen_border_x_float))
            pen_border_y = int(round(pen_border_y_float))
            paste_border_y_start = max(0, pen_border_y)
            paste_border_x_start = max(0, pen_border_x)
            paste_border_y_end = min(canvas_border.shape[0], pen_border_y + border_bitmap_rows)
            paste_border_x_end = min(canvas_border.shape[1], pen_border_x + border_bitmap_width)
            border_slice_y_start = paste_border_y_start - pen_border_y
            border_slice_x_start = paste_border_x_start - pen_border_x
            border_slice_y_end = border_slice_y_start + (paste_border_y_end - paste_border_y_start)
            border_slice_x_end = border_slice_x_start + (paste_border_x_end - paste_border_x_start)
            bitmap_border_slice = bitmap_border[
                border_slice_y_start:border_slice_y_end,
                border_slice_x_start:border_slice_x_end
            ]
            if (bitmap_border_slice.size > 0 and 
                bitmap_border_slice.shape == (paste_border_y_end - paste_border_y_start,
                                            paste_border_x_end - paste_border_x_start)):
                target_slice = canvas_border[
                    paste_border_y_start:paste_border_y_end,
                    paste_border_x_start:paste_border_x_end
                ]
                if target_slice.shape == bitmap_border_slice.shape:
                    canvas_border[paste_border_y_start:paste_border_y_end,
                                paste_border_x_start:paste_border_x_end] = cv2.add(
                        target_slice, bitmap_border_slice)
                else:
                    print(f"[Error] Shape mismatch during border paste: "
                         f"target={{target_slice.shape}}, source={{bitmap_border_slice.shape}}")
    return char_offset_x

def is_cjk_lang(lang: str):
    lang = lang.lower()
    # Check for common language codes for Chinese, Japanese, Korean
    return lang in ['chs', 'cht', 'jpn', 'kor', 'zh', 'ja', 'ko']

def put_text_horizontal(font_size: int, text: str, width: int, height: int, alignment: str,
                        reversed_direction: bool, fg: Tuple[int, int, int], bg: Tuple[int, int, int],
                        lang: str = 'en_US', hyphenate: bool = True, line_spacing: int = 0, config=None):
    logger.debug(f"[文本渲染调试-水平] 开始水平文本渲染")
    logger.debug(f"[文本渲染调试-水平] 输入参数 - 字体大小: {font_size}, 文本: '{text}'")
    logger.debug(f"[文本渲染调试-水平] 渲染区域 - 宽度: {width}, 高度: {height}")
    logger.debug(f"[文本渲染调试-水平] 对齐: {alignment}, 反向: {reversed_direction}")
    logger.debug(f"[文本渲染调试-水平] 语言: {lang}, 连字符: {hyphenate}, 行间距: {line_spacing}")
    logger.debug(f"[文本渲染调试-水平] 前景色: RGB{fg}, 背景色: RGB{bg}")

    text = compact_special_symbols(text)
    if not text :
        logger.debug(f"[文本渲染调试-水平] 文本为空，返回")
        return

    layout_mode = 'default'
    if config:
        layout_mode = config.render.layout_mode
        logger.debug(f"[文本渲染调试-水平] 当前排版模式: {layout_mode}")
        # Check for no-wrap condition and handle AI line breaks
        if layout_mode == 'smart_scaling' and config.render.disable_auto_wrap:
            width = 99999
            # Use a case-insensitive regex to handle variations like [br], [ BR ], etc.
            text = re.sub(r'\s*\[BR\]\s*', '\n', text, flags=re.IGNORECASE)
            logger.debug(f"[文本渲染调试-水平-smart_scaling] 禁用自动换行，宽度设为无限: {width}")
            logger.debug(f"[文本渲染调试-水平-smart_scaling] 处理AI换行符后文本: '{text}'")

    bg_size = int(max(font_size * 0.07, 1)) if bg is not None else 0
    spacing_y = int(font_size * (line_spacing or 0.01))
    logger.debug(f"[文本渲染调试-水平] 边框大小: {bg_size}, 垂直间距: {spacing_y}")

    if layout_mode == 'smart_scaling' and is_cjk_lang(lang):
        logger.debug(f"[文本渲染调试-水平] 使用CJK布局算法")
        line_text_list, line_width_list = calc_horizontal_cjk(font_size, text, width)
    else:
        logger.debug(f"[文本渲染调试-水平] 使用标准布局算法")
        line_text_list, line_width_list = calc_horizontal(font_size, text, width, height, lang, hyphenate)

    logger.debug(f"[文本渲染调试-水平] 计算结果 - 行数: {len(line_text_list)}")
    for i, (line_text, line_width) in enumerate(zip(line_text_list, line_width_list)):
        logger.debug(f"[文本渲染调试-水平] 第{i+1}行: '{line_text}', 宽度: {line_width}")

    canvas_w = max(line_width_list) + (font_size + bg_size) * 2
    canvas_h = font_size * len(line_width_list) + spacing_y * (len(line_width_list) - 1) + (font_size + bg_size) * 2
    logger.debug(f"[文本渲染调试-水平] 画布尺寸: {canvas_w} x {canvas_h}")

    canvas_text = np.zeros((canvas_h, canvas_w), dtype=np.uint8)
    canvas_border = canvas_text.copy()
    pen_orig = [font_size + bg_size, font_size + bg_size]
    if reversed_direction:
        pen_orig[0] = canvas_w - bg_size - 10
        logger.debug(f"[文本渲染调试-水平] 反向文本，调整起始笔位: {pen_orig}")
    logger.debug(f"[文本渲染调试-水平] 初始笔位: {pen_orig}")

    for line_idx, (line_text, line_width) in enumerate(zip(line_text_list, line_width_list)):
        pen_line = pen_orig.copy()
        logger.debug(f"[文本渲染调试-水平] 处理第{line_idx+1}行，初始笔位: {pen_line}")

        if alignment == 'center':
            pen_line[0] += (max(line_width_list) - line_width) // 2 * (-1 if reversed_direction else 1)
            logger.debug(f"[文本渲染调试-水平] 居中对齐，调整后笔位: {pen_line}")
        elif alignment == 'right' and not reversed_direction:
            pen_line[0] += max(line_width_list) - line_width
            logger.debug(f"[文本渲染调试-水平] 右对齐，调整后笔位: {pen_line}")
        elif alignment == 'left' and reversed_direction:
            pen_line[0] -= max(line_width_list) - line_width
            pen_line[0] = max(line_width, pen_line[0])
            logger.debug(f"[文本渲染调试-水平] 反向左对齐，调整后笔位: {pen_line}")

        for char_idx, c in enumerate(line_text):
            if reversed_direction:
                cdpt, rot_degree = CJK_Compatibility_Forms_translate(c, 0)
                glyph = get_char_glyph(cdpt, font_size, 0)
                offset_x = glyph.metrics.horiAdvance >> 6
                pen_line[0] -= offset_x
                logger.debug(f"[文本渲染调试-水平] 反向字符'{c}'，预调整笔位: {pen_line}")
            offset_x = put_char_horizontal(font_size, c, pen_line, canvas_text, canvas_border, border_size=bg_size)
            if not reversed_direction:
                pen_line[0] += offset_x
            logger.debug(f"[文本渲染调试-水平] 字符'{c}'渲染完成，偏移: {offset_x}, 新笔位: {pen_line}")
        pen_orig[1] += spacing_y + font_size
        logger.debug(f"[文本渲染调试-水平] 第{line_idx+1}行完成，下一行笔位Y: {pen_orig[1]}")

    canvas_border = np.clip(canvas_border, 0, 255)
    line_box = add_color(canvas_text, fg, canvas_border, bg)
    combined_canvas = cv2.add(canvas_text, canvas_border)
    x, y, w, h = cv2.boundingRect(combined_canvas)
    logger.debug(f"[文本渲染调试-水平] 最终裁剪区域: x={x}, y={y}, w={w}, h={h}")
    result = line_box[y:y+h, x:x+w]
    logger.debug(f"[文本渲染调试-水平] 水平文本渲染完成，最终尺寸: {result.shape}")
    return result

def test():
    canvas = put_text_horizontal(64, 1.0, '因为不同‼ [这"真的是普]通的》肉！那个“姑娘”的恶作剧！是吗？咲夜⁉', 400, (0, 0, 0), (255, 128, 128))
    imwrite_unicode('text_render_combined.png', canvas)

if __name__ == '__main__':
    test()
