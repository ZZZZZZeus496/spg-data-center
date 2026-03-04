# -*- coding: utf-8 -*-
"""
SPG战队赛数据中心 v3.0

核心改进：
1. 侧边栏 → 电竞指挥中心风格（Logo + 折叠配置 + 深蓝金色主题）
2. 视频处理 → 全自动：抽帧 → 智能筛选结算页 → 直接出结果（不再手动选帧）
3. 结果展示 → 胜利绿/失败红背景 + MVP金色加粗 + 本周战报汇总
"""

import base64
import json
import os
import re
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from rapidfuzz import fuzz, process

# API 客户端
import dashscope
from dashscope import MultiModalConversation

# ══════════════════════════════════════════════
# 页面配置
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="SPG战队赛数据中心",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",  # 手机端默认收起侧边栏
)

# ══════════════════════════════════════════════
# 全局 CSS — 电竞科技风
# ══════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans SC', sans-serif; }

/* ===== 侧边栏 ===== */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0a1a 0%, #0d1b2a 40%, #1b2838 100%) !important;
    border-right: 1px solid rgba(245,175,25,0.15);
}
section[data-testid="stSidebar"] * {
    color: #c8d6e5 !important;
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #ffd700 !important;
    text-shadow: 0 0 12px rgba(255,215,0,0.3);
}

/* Logo 区域 */
.sidebar-logo {
    text-align: center; padding: 20px 10px 16px;
    border-bottom: 1px solid rgba(255,215,0,0.12);
    margin-bottom: 16px;
}
.sidebar-logo .logo-icon {
    font-size: 3.6rem; line-height: 1;
    filter: drop-shadow(0 0 16px rgba(255,215,0,0.5));
}
.sidebar-logo .logo-title {
    font-size: 1.35rem; font-weight: 900; margin-top: 8px;
    background: linear-gradient(90deg, #ffd700, #ffaa00, #ffd700);
    background-size: 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: goldShimmer 4s ease-in-out infinite;
    letter-spacing: 2px;
}
.sidebar-logo .logo-sub {
    font-size: 0.75rem; color: #5a6f84 !important; margin-top: 2px;
    letter-spacing: 4px;
}
@keyframes goldShimmer {
    0%,100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

/* 成员统计徽章 */
.member-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,215,0,0.08);
    border: 1px solid rgba(255,215,0,0.2);
    border-radius: 20px; padding: 4px 14px;
    font-size: 0.8rem; color: #ffd700 !important;
    margin: 4px 0 8px;
}
.member-badge .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #38ef7d; display: inline-block;
    box-shadow: 0 0 6px #38ef7d;
}

/* ===== 主区域 Hero ===== */
.hero-banner {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    border-radius: 20px;
    padding: 44px 32px 36px;
    text-align: center;
    margin-bottom: 32px;
    border: 1px solid rgba(255,215,0,0.08);
    box-shadow: 0 12px 40px rgba(0,0,0,0.35);
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(ellipse at 30% 20%, rgba(255,215,0,0.06) 0%, transparent 60%),
                radial-gradient(ellipse at 70% 80%, rgba(241,39,17,0.04) 0%, transparent 60%);
}
.hero-banner h1 {
    position: relative; margin: 0;
    font-size: 2.6rem; font-weight: 900; letter-spacing: 3px;
    background: linear-gradient(90deg, #ffd700, #ff6b35, #ffd700);
    background-size: 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: goldShimmer 3s ease-in-out infinite;
}
.hero-banner .sub { position: relative; color: #8899aa; margin-top: 10px; font-size: 1.05rem; }
.hero-banner .flow {
    position: relative;
    display: flex; justify-content: center; gap: 8px; margin-top: 24px;
    flex-wrap: wrap; align-items: center;
}
.hero-banner .flow-step {
    display: flex; align-items: center; gap: 6px;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px; padding: 6px 16px;
    color: rgba(255,255,255,0.7); font-size: 0.88rem;
}
.hero-banner .flow-step .n {
    width: 22px; height: 22px; border-radius: 50%;
    background: linear-gradient(135deg, #ffd700, #ff6b35);
    color: #fff; font-weight: 700; font-size: 0.72rem;
    display: inline-flex; align-items: center; justify-content: center;
}
.hero-banner .flow-arrow { color: rgba(255,215,0,0.4); font-size: 1.1rem; }

/* ===== 空状态 ===== */
.empty-state {
    text-align: center; padding: 80px 20px;
    background: linear-gradient(180deg, rgba(48,43,99,0.08) 0%, transparent 100%);
    border-radius: 20px;
    border: 2px dashed rgba(255,215,0,0.15);
}
.empty-state .icon { font-size: 4rem; margin-bottom: 12px; opacity: 0.7; }
.empty-state .main-text { font-size: 1.15rem; color: #555; font-weight: 500; }
.empty-state .sub-text { font-size: 0.85rem; color: #999; margin-top: 6px; }

/* ===== 统计卡片 ===== */
.stats-grid { display: flex; gap: 16px; margin: 20px 0 28px; flex-wrap: wrap; }
.s-card {
    flex: 1; min-width: 150px; border-radius: 16px; padding: 24px 16px;
    text-align: center; color: #fff; position: relative; overflow: hidden;
    box-shadow: 0 6px 24px rgba(0,0,0,0.18);
}
.s-card::after {
    content: ''; position: absolute; top: -30px; right: -30px;
    width: 80px; height: 80px; border-radius: 50%;
    background: rgba(255,255,255,0.08);
}
.s-card.c-total  { background: linear-gradient(135deg, #667eea, #764ba2); }
.s-card.c-win    { background: linear-gradient(135deg, #11998e, #38ef7d); }
.s-card.c-lose   { background: linear-gradient(135deg, #eb3349, #f45c43); }
.s-card.c-rate   { background: linear-gradient(135deg, #f7971e, #ffd200); color: #333; }
.s-card .val  { font-size: 2.4rem; font-weight: 900; margin: 0; position: relative; z-index: 1; }
.s-card .desc { font-size: 0.85rem; opacity: 0.85; margin-top: 4px; position: relative; z-index: 1; }

/* ===== 战报表格 ===== */
.report-header {
    display: flex; align-items: center; gap: 12px;
    margin: 8px 0 16px; padding-bottom: 12px;
    border-bottom: 2px solid rgba(255,215,0,0.2);
}
.report-header h2 {
    margin: 0; font-size: 1.5rem; font-weight: 700;
    background: linear-gradient(90deg, #302b63, #667eea);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.report-header .rh-icon { font-size: 1.8rem; }

/* 处理进度区 */
.processing-box {
    background: linear-gradient(135deg, rgba(15,12,41,0.04), rgba(48,43,99,0.06));
    border-radius: 16px; padding: 24px;
    border: 1px solid rgba(102,126,234,0.12);
    margin: 16px 0;
}

/* ===== 移动端适配 ===== */

/* 确保 viewport 正确缩放 */
@viewport { width: device-width; }

/* 手机竖屏 (宽度 < 768px) */
@media screen and (max-width: 768px) {
    /* 主区域减少内边距 */
    .block-container { padding: 0.5rem 1rem !important; }

    /* Hero Banner 缩小 */
    .hero-banner {
        padding: 24px 16px 20px;
        border-radius: 12px;
        margin-bottom: 16px;
    }
    .hero-banner h1 {
        font-size: 1.4rem !important;
        letter-spacing: 1px;
    }
    .hero-banner .sub { font-size: 0.85rem; margin-top: 6px; }
    .hero-banner .flow { gap: 4px; margin-top: 14px; }
    .hero-banner .flow-step {
        padding: 4px 10px;
        font-size: 0.72rem;
    }
    .hero-banner .flow-step .n {
        width: 18px; height: 18px;
        font-size: 0.6rem;
    }
    .hero-banner .flow-arrow { font-size: 0.8rem; }

    /* 统计卡片：2列网格 */
    .stats-grid {
        display: grid !important;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin: 12px 0 16px;
    }
    .s-card {
        min-width: unset !important;
        padding: 16px 10px;
        border-radius: 12px;
    }
    .s-card .val { font-size: 1.6rem; }
    .s-card .desc { font-size: 0.72rem; }

    /* 空状态 */
    .empty-state { padding: 40px 16px; }
    .empty-state .icon { font-size: 2.8rem; }
    .empty-state .main-text { font-size: 0.95rem; }
    .empty-state .sub-text { font-size: 0.75rem; }

    /* 战报标题 */
    .report-header { margin: 4px 0 10px; }
    .report-header h2 { font-size: 1.1rem; }
    .report-header .rh-icon { font-size: 1.3rem; }

    /* 侧边栏 Logo 缩小 */
    .sidebar-logo { padding: 12px 8px 10px; }
    .sidebar-logo .logo-icon { font-size: 2.4rem; }
    .sidebar-logo .logo-title { font-size: 1rem; }

    /* 成员徽章 */
    .member-badge { font-size: 0.7rem; padding: 3px 10px; }

    /* 表格横向可滚动 */
    .stDataFrame, [data-testid="stDataFrame"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }
    .stDataFrame table {
        font-size: 0.75rem !important;
        min-width: 600px;
    }

    /* 按钮自适应 */
    .stButton > button {
        font-size: 0.85rem !important;
        padding: 8px 16px !important;
    }

    /* 文件上传区 */
    [data-testid="stFileUploader"] {
        padding: 8px !important;
    }
    [data-testid="stFileUploader"] p {
        font-size: 0.8rem !important;
    }
}

/* 超小屏幕 (宽度 < 480px) */
@media screen and (max-width: 480px) {
    .hero-banner h1 { font-size: 1.15rem !important; }
    .hero-banner .flow-step { font-size: 0.65rem; padding: 3px 8px; }
    .stats-grid { gap: 6px; }
    .s-card .val { font-size: 1.3rem; }
    .s-card { padding: 12px 8px; }
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════

def encode_bytes_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")

def get_mime(name: str) -> str:
    ext = Path(name).suffix.lower()
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/png")

def parse_json_robust(raw: str) -> dict:
    for fn in [
        lambda t: json.loads(t),
        lambda t: json.loads(re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", t, re.DOTALL).group(1).strip()),
        lambda t: json.loads(re.search(r"\{.*\}", t, re.DOTALL).group(0)),
    ]:
        try:
            return fn(raw)
        except Exception:
            continue
    raise ValueError(f"无法解析 JSON：{raw[:200]}...")


def try_load_env_key(key_name: str = "GEMINI_API_KEY") -> str:
    """尝试从 .env 文件或环境变量读取 API Key。"""
    env_path = Path(".env")
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key_name:
                    v = v.strip().strip('"').strip("'")
                    if v and not v.startswith("xxxx"):
                        return v
        except Exception:
            pass
    return os.environ.get(key_name, "")


# ══════════════════════════════════════════════
# 视频处理 — 全自动抽帧 + 智能筛选
# ══════════════════════════════════════════════

def extract_video_frames(video_bytes: bytes, max_frames: int = 120) -> list[np.ndarray]:
    """从视频按每秒 1 帧抽取，确保不遗漏任何结算页。"""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name
    frames = []
    try:
        cap = cv2.VideoCapture(tmp_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if total <= 0 or fps <= 0:
            return frames
        # 每秒抽 1 帧（确保密度足够），但不超过 max_frames
        step = max(1, int(fps))  # 按 FPS 每秒取 1 帧
        indices = list(range(0, total, step))
        if len(indices) > max_frames:
            # 如果超出上限，均匀采样
            ratio = len(indices) / max_frames
            indices = [indices[int(i * ratio)] for i in range(max_frames)]
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if ok:
                frames.append(frame)
        cap.release()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return frames


def is_settlement_screen(frame: np.ndarray) -> bool:
    """
    判断一帧是否为王者荣耀比赛结算详情页（10人数据页）。

    核心特征：
    - 左蓝右红双色调（我方/敌方）
    - 上方有 "胜利"/"失败" + 比分
    - 中间有 10 行选手数据（KDA、评分等）
    - 整体偏暗，边缘密度适中

    需要排除：游戏大厅、战队首页、比赛列表等非结算页
    """
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = gray.mean()

    # ── 1. 基础排除 ──
    if brightness < 20 or brightness > 140:
        return False

    # ── 2. 左蓝右红检测 ──
    y1, y2 = h // 5, 4 * h // 5
    left_half = frame[y1:y2, :w // 2]
    right_half = frame[y1:y2, w // 2:]

    left_hsv = cv2.cvtColor(left_half, cv2.COLOR_BGR2HSV)
    right_hsv = cv2.cvtColor(right_half, cv2.COLOR_BGR2HSV)

    lsat = left_hsv[:, :, 1] > 30
    rsat = right_hsv[:, :, 1] > 30
    if lsat.sum() < 100 or rsat.sum() < 100:
        return False

    lhue = left_hsv[:, :, 0]
    rhue = right_hsv[:, :, 0]

    lblue = ((lhue > 85) & (lhue < 135) & lsat).sum() / max(lsat.sum(), 1)
    rred = (((rhue < 18) | (rhue > 155)) & rsat).sum() / max(rsat.sum(), 1)

    if not (lblue > 0.15 and rred > 0.08):
        return False

    # ── 3. 边缘密度：结算页有 KDA 文字但不会太密集 ──
    edges = cv2.Canny(gray, 50, 150)
    ledge = edges[y1:y2, :w // 2].mean() / 255.0
    redge = edges[y1:y2, w // 2:].mean() / 255.0
    if ledge < 0.03 or redge < 0.03:
        return False

    # ── 4. 排除游戏大厅/战队首页 ──
    # 大厅底部 brightness ~73-76，战队页 ~76，结算页底部 ~45-46
    bottom_region = gray[3 * h // 4:, :]
    bottom_brightness = bottom_region.mean()
    if bottom_brightness > 60:
        return False

    # 额外检查：整体亮度。结算页 ~65-67，大厅 ~87
    if brightness > 80:
        return False

    # ── 5. 结算页中间区域有水平排列的选手行 ──
    # 检查中间区域的水平边缘（选手行之间的分隔线）
    mid_region = gray[h // 6: 5 * h // 6, w // 8: 7 * w // 8]
    # Sobel 水平边缘
    sobelx = cv2.Sobel(mid_region, cv2.CV_64F, 0, 1, ksize=3)
    horiz_edges = np.abs(sobelx).mean()
    # 结算页有明显的水平行结构
    if horiz_edges < 5:
        return False

    return True


def _content_region(frame: np.ndarray) -> np.ndarray:
    """提取结算页中心内容区域（玩家名字+KDA所在区域），用于去重比较。"""
    h, w = frame.shape[:2]
    # 中心区域：去掉顶部标题栏和底部按钮栏，聚焦选手数据区
    region = frame[h // 6: 5 * h // 6, w // 10: 9 * w // 10]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (200, 120))


def filter_settlement_frames(frames: list[np.ndarray]) -> list[np.ndarray]:
    """从抽取的帧中筛选出结算页面，并智能去重。"""
    results = []
    for frame in frames:
        if is_settlement_screen(frame):
            results.append(frame)

    if len(results) <= 1:
        return results

    # 去重：比较中心内容区域（选手名字/KDA），而不是全帧
    # 全帧比较会因为蓝红背景色相同而误判为重复
    deduped = [results[0]]
    for i in range(1, len(results)):
        is_duplicate = False
        curr_content = _content_region(results[i])
        # 与所有已保留的帧比较（不只是前一帧）
        for kept in deduped:
            prev_content = _content_region(kept)
            diff = cv2.absdiff(prev_content, curr_content).mean()
            if diff < 8:  # 内容区域差异小于 8 → 同一场比赛
                is_duplicate = True
                break
        if not is_duplicate:
            deduped.append(results[i])

    return deduped


def frame_to_png_bytes(frame: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", frame)
    return buf.tobytes() if ok else b""


# ══════════════════════════════════════════════
# GPT-4o-mini Vision API
# ══════════════════════════════════════════════

VISION_PROMPT = """这是一张王者荣耀战队赛的结算截图。请仔细分析图片，提取以下信息并严格以 JSON 格式返回。

**极其重要 — 区分玩家ID和英雄名**：
- 截图中每个选手位置有两行文字：上面一行是【玩家游戏ID】，下面一行是【使用的英雄名】
- 我需要的是【玩家游戏ID】，绝对不要返回英雄名！
- 英雄名举例（这些是英雄不是玩家，绝对不要返回）：亚瑟、妲己、后羿、鲁班、安琪拉、吕布、关羽、赵云、韩信、李白、露娜、公孙离、马可波罗、瑶、蔡文姬、鬼谷子、张飞、小乔、大乔、王昭君、诸葛亮、司马懿、花木兰、芈月、夏侯惇、澜、云缨、不知火舞、李信、孙膑、明世隐、女娲、嫦娥、西施、元歌、百里守约、百里玄策、虞姬、黄忠、狄仁杰、孙尚香、伽罗、蒙犽、戈娅、海月、暃、盾山、猪八戒、刘邦、白起、廉颇、项羽、铠、曹操、橘右京、宫本武藏、哪吒、杨戬、老夫子、狂铁、苏烈、梦奇、阿古朵、姜子牙、干将莫邪、周瑜、墨子、高渐离、扁鹊、张良、钟馗、上官婉儿、沈梦溪、米莱狄、弈星、刘禅、太乙真人、牛魔、东皇太一、盘古、镜、阿轲、兰陵王、娜可露露、裴擒虎、李元芳、刘备、曜、马超、典韦、程咬金、达摩
- 玩家游戏ID举例：SPG.嘎嘎、SPG.zeus、专注ω、清心凝薇、Hide on brush 等
- 玩家ID通常包含：SPG前缀、丶丨★ω℃等特殊符号、英文名、数字等

**截图说明**：
- 截图分为左右两半：左侧是一支队伍，右侧是另一支队伍
- **请同时提取左右两侧的完整数据**，不要预先判断哪侧是我方
- 请根据界面中的蓝方/红方标识（颜色、边框、文字等）判断左右两侧各是蓝方还是红方
- **分路必须严格按该侧在截图中的行顺序确定**，不要根据英雄类型推断！
- 每侧从上到下共5行，固定对应：第1行=对抗路，第2行=中路，第3行=发育路，第4行=打野，第5行=游走

请提取以下信息（左右两侧都要返回）：

1. **左侧队伍**：阵营（蓝方/红方）、比赛结果（胜利/失败）、5名选手（游戏ID、分路、评分、奖牌）、MVP（若在本侧则填，否则 null）
2. **右侧队伍**：同上
3. **比赛日期**：格式 YYYY/M/D（如 2026/2/6），没有则返回 null

注意事项：
- 再次强调：返回的必须是玩家游戏ID，不是英雄名称！
- 评分是数字（如 10.4、7.9、5.6）
- 分路位置如果无法确定请填 "未知"
- 只返回 JSON，不要有其他文字说明

返回格式：
{
    "比赛日期": "2026/2/6",
    "左侧队伍": {
        "阵营": "蓝方",
        "比赛结果": "失败",
        "选手": [
            {"游戏ID": "xxx", "分路": "对抗路", "评分": 5.6, "奖牌": "金牌"},
            {"游戏ID": "yyy", "分路": "中路", "评分": 6.3, "奖牌": null},
            {"游戏ID": "zzz", "分路": "发育路", "评分": 9.1, "奖牌": "银牌"},
            {"游戏ID": "aaa", "分路": "打野", "评分": 8.0, "奖牌": null},
            {"游戏ID": "bbb", "分路": "游走", "评分": 7.7, "奖牌": "铜牌"}
        ],
        "MVP": null
    },
    "右侧队伍": {
        "阵营": "红方",
        "比赛结果": "胜利",
        "选手": [...],
        "MVP": {"游戏ID": "SPG.xxx", "评分": 10.4}
    }
}"""


import time as _time
from concurrent.futures import ThreadPoolExecutor, as_completed


def call_vision_qwen(img_bytes: bytes, mime: str, api_key: str) -> dict:
    """
    使用阿里云百炼 Qwen-VL-Max 识别截图。
    通过 DashScope MultiModalConversation 接口调用。
    """
    dashscope.api_key = api_key
    b64 = encode_bytes_b64(img_bytes)
    data_url = f"data:{mime};base64,{b64}"

    messages = [
        {
            "role": "user",
            "content": [
                {"image": data_url},
                {"text": VISION_PROMPT},
            ],
        }
    ]

    resp = MultiModalConversation.call(
        model="qwen-vl-max",
        messages=messages,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Qwen-VL-Max 调用失败 [{resp.status_code}]: "
            f"{resp.message if hasattr(resp, 'message') else resp}"
        )

    # 提取返回文本
    content = resp.output.choices[0].message.content
    if isinstance(content, list):
        text = content[0].get("text", "")
    elif isinstance(content, str):
        text = content
    else:
        text = str(content)

    return parse_json_robust(text.strip())


def call_vision_qwen_with_retry(img_bytes: bytes, mime: str, api_key: str,
                                 max_retries: int = 3) -> dict:
    """带自动重试的 Qwen-VL-Max 调用（处理限流等临时错误）。"""
    last_err = None
    for attempt in range(max_retries):
        try:
            return call_vision_qwen(img_bytes, mime, api_key)
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "throttl" in err_str or "rate" in err_str or "429" in str(e) or "limit" in err_str:
                wait = 10 * (attempt + 1)
                _time.sleep(wait)
                continue
            else:
                raise
    raise last_err


def call_vision(img_bytes: bytes, mime: str, api_key, engine: str = "qwen") -> dict:
    """统一调用入口。"""
    if isinstance(api_key, list):
        api_key = api_key[0]
    return call_vision_qwen_with_retry(img_bytes, mime, api_key)


# ══════════════════════════════════════════════
# 队员匹配
# ══════════════════════════════════════════════

def build_matcher_json(path: str = "members.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    members = data.get("队员列表", [])
    team_name = data.get("战队名", "SPG")
    id2n, ids = {}, []
    for m in members:
        real = m["真实名字"]
        for gid in m["游戏ID"]:
            id2n[gid] = real
            ids.append(gid)
        # 真实名字、昵称也可匹配，便于 OCR 返回这些变体时对上
        if real:
            id2n[real] = real
            ids.append(real)
        nick = m.get("昵称", "").strip()
        if nick and nick != real:
            id2n[nick] = real
            ids.append(nick)
    return id2n, ids, len(members), team_name


def build_matcher_text(text: str):
    id2n, ids = {}, []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, part = line.split("=", 1)
        name = name.strip()
        for gid in (x.strip() for x in part.split(",") if x.strip()):
            id2n[gid] = name
            ids.append(gid)
    return id2n, ids, len(set(id2n.values()))


# ── 王者荣耀英雄名黑名单（防止 AI 返回英雄名代替玩家ID） ──
HERO_NAMES = {
    # 战士/对抗路
    "吕布", "关羽", "赵云", "花木兰", "芈月", "夏侯惇", "曹操", "典韦", "程咬金", "达摩",
    "老夫子", "哪吒", "杨戬", "铠", "狂铁", "苏烈", "盘古", "马超", "曜", "蒙恬",
    "橘右京", "宫本武藏", "李信", "亚瑟", "刘备", "司空震", "暃",
    # 打野/刺客
    "韩信", "李白", "露娜", "澜", "阿轲", "兰陵王", "百里玄策", "裴擒虎", "娜可露露",
    "李元芳", "赵怀真", "镜", "云中君", "司马懿", "元歌", "上官婉儿", "青莲",
    # 法师/中路
    "妲己", "王昭君", "诸葛亮", "安琪拉", "小乔", "大乔", "嫦娥", "西施", "女娲",
    "干将莫邪", "千将莫邪", "甄姬", "武则天", "张良", "周瑜", "墨子", "高渐离", "扁鹊",
    "姜子牙", "钟馗", "沈梦溪", "米莱狄", "弈星", "杨玉环", "不知火舞", "海月", "金蝉",
    # 射手/发育路
    "后羿", "鲁班", "鲁班七号", "马可波罗", "公孙离", "孙尚香", "虞姬", "黄忠", "狄仁杰",
    "伽罗", "蒙犽", "百里守约", "李元芳", "艾琳", "戈娅", "莱西奥",
    # 辅助/游走
    "蔡文姬", "鬼谷子", "张飞", "瑶", "孙膑", "明世隐", "牛魔", "东皇太一", "刘禅",
    "太乙真人", "庄周", "盾山", "大司命", "桑启", "猪八戒",
    # 坦克
    "白起", "廉颇", "项羽", "刘邦", "梦奇", "阿古朵", "朵莉亚",
    # 其他 / 容易混淆的
    "云缨", "敖隐", "赤兰", "姬小满", "亚连", "徕佬", "芷", "婵", "千",
}


def _is_hero_name(name: str) -> bool:
    """检查一个字符串是否是英雄名（精确或模糊匹配）。"""
    s = name.strip()
    if s in HERO_NAMES:
        return True
    # 处理 AI 可能加的前后缀，如 "公孙离（射手）" 或 "(MVP)公孙离"
    for h in HERO_NAMES:
        if len(h) >= 2 and h in s and len(s) <= len(h) + 6:
            return True
    return False


# 尾随/首尾符号（OCR/识别可能产生变体的符号，统一去除后再匹配）
_NORM_SYMBOLS = frozenset("♡♥♂♀★☆♦♣♠°·˚^~`｀〃々〆〇〓〤〥〦〧〨〩〪〭〮〯〫〬")


def _normalize_for_match(s: str) -> str:
    """去除首尾易变符号，便于将「朝暮予你♡」「朝暮予你♂」等统一为同一人。"""
    if not s:
        return ""
    s = s.strip()
    while s and s[0] in _NORM_SYMBOLS:
        s = s[1:]
    while s and s[-1] in _NORM_SYMBOLS:
        s = s[:-1]
    return s.strip()


def match_id(gid: str, id2n: dict, ids: list, thr: int = 60) -> str:
    """
    将游戏ID模糊匹配为战队成员真名。
    符号变体（如 朝暮予你♡/朝暮予你♂）统一为同一人；能对上选手表则直接对应。
    """
    if not gid or not gid.strip():
        return ""
    gid = gid.strip()
    if _is_hero_name(gid):
        return ""
    # 1. 精确匹配
    if gid in id2n:
        return id2n[gid]
    # 2. 规范化后精确匹配：去首尾符号后与选手表中的 ID 一致则视为同一人
    gid_norm = _normalize_for_match(gid)
    if gid_norm:
        for known_id, real_name in id2n.items():
            if _normalize_for_match(known_id) == gid_norm:
                return real_name
    if not ids:
        return gid
    # 3.  fuzzy 匹配：放宽阈值，优先 token_set_ratio 处理符号差异
    r = process.extractOne(gid, ids, scorer=fuzz.token_set_ratio, score_cutoff=max(45, thr - 10))
    if r:
        return id2n[r[0]]
    # 4. 用规范化后的名字再试一次 fuzzy
    if gid_norm:
        r2 = process.extractOne(gid_norm, ids, scorer=fuzz.token_set_ratio, score_cutoff=50)
        if r2:
            return id2n[r2[0]]
    return gid


# ══════════════════════════════════════════════
# 数据处理 & 导出
# ══════════════════════════════════════════════

# 与截图行顺序一致：第1行对抗路、第2行中路、第3行射手、第4行打野、第5行辅助
LANE_ORDER = ["对抗路", "中路", "发育路", "打野", "游走"]
LANE_ALIASES = {
    "上单": "对抗路", "边路": "对抗路", "上路": "对抗路", "战士": "对抗路",
    "野区": "打野", "打野": "打野",
    "中路": "中路", "中单": "中路", "法师": "中路",
    "发育路": "发育路", "射手": "发育路", "下路": "发育路", "ADC": "发育路",
    "游走": "游走", "辅助": "游走", "辅": "游走",
}


def normalize_lane(lane: str) -> str:
    """将各种分路名称统一为标准5路。"""
    lane = lane.strip()
    if lane in LANE_ORDER:
        return lane
    return LANE_ALIASES.get(lane, "未知")


def _count_roster_matches(players: list, id2n: dict, ids: list, thr: int) -> int:
    """统计该侧有多少选手能匹配到队员名单。"""
    known_names = set(id2n.values())
    count = 0
    for p in players[:5]:
        gid = (p.get("游戏ID") or p) if isinstance(p, dict) else str(p)
        if not gid:
            continue
        matched = match_id(gid, id2n, ids, thr)
        if matched in known_names:
            count += 1
    return count


def result_to_row(res: dict, id2n: dict, ids: list, thr: int, src: str) -> dict | None:
    """将 API 返回结果转换为表格行。根据队员名单匹配确定我方，不依赖胜利/失败。"""
    if res.get("error"):
        return None

    # 新格式：左右两侧都有，根据队员名单匹配确定我方
    left = res.get("左侧队伍") or {}
    right = res.get("右侧队伍") or {}

    if left and right:
        left_players = left.get("选手") or []
        right_players = right.get("选手") or []
        left_cnt = _count_roster_matches(left_players, id2n, ids, thr)
        right_cnt = _count_roster_matches(right_players, id2n, ids, thr)
        # 匹配数多的一侧为我方；若相等则取左侧（或可改为取胜利方，但用户要求不依赖胜负）
        if right_cnt > left_cnt:
            side = right
        else:
            side = left
        players = side.get("选手") or []
        camp = side.get("阵营") or "未知"
        result = side.get("比赛结果") or "未知"
        mvp_raw = side.get("MVP")
    else:
        # 兼容旧格式：直接返回 选手
        players = res.get("选手") or res.get("我方队员") or []
        camp = res.get("本方阵营") or "未知"
        result = res.get("比赛结果", "未知")
        mvp_raw = res.get("MVP")

    # 兼容旧格式（纯 ID 列表）
    if players and isinstance(players[0], str):
        names = [match_id(g, id2n, ids, thr) for g in players[:5]]
        names += [""] * (5 - len(names))
        mvp_name = ""
        mvp_score = ""
        if isinstance(mvp_raw, dict):
            mvp_name = match_id(mvp_raw.get("游戏ID", ""), id2n, ids, thr)
            mvp_score = mvp_raw.get("评分", "")
        elif isinstance(mvp_raw, str) and mvp_raw:
            mvp_name = match_id(mvp_raw, id2n, ids, thr)
        return {
            "日期": res.get("比赛日期") or "未知",
            "本方阵营": camp,
            "对抗路选手": names[0], "中路选手": names[1], "发育路选手": names[2],
            "打野选手": names[3], "游走选手": names[4],
            "胜负情况": result,
            "MVP": f"{mvp_name} {mvp_score}".strip() if mvp_name else "",
            "备注": "",
        }

    # 新格式：含分路/评分/奖牌的选手列表
    lane_map = {}
    for p in players[:5]:
        gid = p.get("游戏ID", "")
        spg_name = match_id(gid, id2n, ids, thr)
        lane = normalize_lane(p.get("分路", "未知"))
        score = p.get("评分", "")
        medal = p.get("奖牌") or ""
        lane_map[lane] = {"name": spg_name, "score": score, "medal": medal}

    unassigned = []
    assigned_lanes = set()
    for p in players[:5]:
        lane = normalize_lane(p.get("分路", "未知"))
        if lane == "未知" or lane in assigned_lanes:
            gid = p.get("游戏ID", "")
            spg_name = match_id(gid, id2n, ids, thr)
            unassigned.append({"name": spg_name, "score": p.get("评分", ""), "medal": p.get("奖牌") or ""})
        else:
            assigned_lanes.add(lane)

    for lane in LANE_ORDER:
        if lane not in lane_map and unassigned:
            lane_map[lane] = unassigned.pop(0)

    mvp_name, mvp_score = "", ""
    if isinstance(mvp_raw, dict):
        mvp_name = match_id(mvp_raw.get("游戏ID", ""), id2n, ids, thr)
        mvp_score = mvp_raw.get("评分", "")
    elif isinstance(mvp_raw, str) and mvp_raw:
        mvp_name = match_id(mvp_raw, id2n, ids, thr)

    medal_notes = []
    for l in LANE_ORDER:
        info = lane_map.get(l, {})
        m = info.get("medal", "")
        if m:
            medal_notes.append(f"{info.get('name', '')}({m})")

    row = {
        "日期": res.get("比赛日期") or "未知",
        "本方阵营": camp,
    }
    for lane in LANE_ORDER:
        info = lane_map.get(lane, {})
        row[f"{lane}选手"] = info.get("name", "")
    row["胜负情况"] = result
    row["MVP"] = f"{mvp_name} {mvp_score}".strip() if mvp_name else ""
    row["备注"] = "、".join(medal_notes) if medal_notes else ""

    row["_mvp_name"] = mvp_name
    row["_mvp_score"] = float(mvp_score) if mvp_score and str(mvp_score).replace(".", "").isdigit() else 0.0
    row["_player_medals"] = {
        lane_map.get(l, {}).get("name", ""): lane_map.get(l, {}).get("medal", "")
        for l in LANE_ORDER if lane_map.get(l, {}).get("name", "")
    }
    return row


def df_to_excel(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="战队赛统计")
        ws = w.sheets["战队赛统计"]
        for ci, col in enumerate(df.columns, 1):
            ml = max(df[col].astype(str).map(len).max(), len(col))
            ws.column_dimensions[ws.cell(1, ci).column_letter].width = min(ml * 2 + 4, 40)
    return buf.getvalue()


def default_member_text() -> str:
    p = Path("members.json")
    if p.exists():
        try:
            data = json.load(open(p, "r", encoding="utf-8"))
            lines = [f"{m['真实名字']}={', '.join(m['游戏ID'])}"
                     for m in data.get("队员列表", [])[:15]]
            lines.append("# ...完整名单请选择「members.json」模式")
            return "\n".join(lines)
        except Exception:
            pass
    return ("# 格式：标准名=游戏ID1, 游戏ID2\n"
            "花瓶崽=雾, SPG.花瓶崽\n小鱼=小鱼寓言, SPG.小鱼\n"
            "橙子=皓月当空, SPG.橙子\n陈情=陈情情情情, SPG陈情")


# ══════════════════════════════════════════════
#  主界面
# ══════════════════════════════════════════════

def main():
    # ──────── 侧边栏：战队指挥中心 ────────
    with st.sidebar:
        # Logo 区域
        st.markdown("""
        <div class="sidebar-logo">
            <div class="logo-icon">🏆</div>
            <div class="logo-title">SPG 战队赛数据中心</div>
            <div class="logo-sub">ESPORTS DATA CENTER</div>
        </div>
        """, unsafe_allow_html=True)

        # ─── API 引擎（从 Streamlit Secrets 读取密钥） ───
        engine_id = "qwen"
        try:
            api_key = st.secrets["DASHSCOPE_API_KEY"]
        except (KeyError, FileNotFoundError):
            api_key = ""
        if not api_key:
            st.error("⚠️ 未配置 DASHSCOPE_API_KEY")
            with st.expander("📖 如何配置密钥？", expanded=True):
                st.markdown("""
**线上部署（Streamlit Cloud）：**
1. 打开 [share.streamlit.io](https://share.streamlit.io) → **Your apps**
2. 点击你的应用 → **Settings** → **Secrets**
3. 输入：
   ```
   DASHSCOPE_API_KEY = "sk-你的阿里云百炼密钥"
   ```
4. 保存后点击 **Reboot app**

**本地运行：** 在 `.streamlit/secrets.toml` 中写入上述内容。

📄 详细步骤见项目根目录 `部署与密钥配置.md`
                """)
            st.stop()
        st.markdown(
            '<div class="member-badge"><span class="dot"></span>AI 引擎：Qwen-VL-Max ✅ (百炼平台)</div>',
            unsafe_allow_html=True)

        # ─── 战队名册 ───
        st.markdown("### 📋 战队名册管理")

        has_json = Path("members.json").exists()
        source = st.radio("数据来源",
                          ["📁 members.json", "📝 手动编辑"],
                          index=0 if has_json else 1,
                          label_visibility="collapsed")

        if source.startswith("📁"):
            if has_json:
                id2n, all_ids, n_mem, team_name = build_matcher_json()
                st.markdown(
                    f'<div class="member-badge"><span class="dot"></span>'
                    f'当前已加载：{n_mem} 名队员 · {len(all_ids)} 个游戏ID</div>',
                    unsafe_allow_html=True)
            else:
                st.error("❌ 未找到 members.json")
                id2n, all_ids = {}, []
        else:
            txt = st.text_area("队员配置", value=default_member_text(), height=250,
                               help="格式：标准名=游戏ID1, 游戏ID2")
            id2n, all_ids, n_txt = build_matcher_text(txt)
            st.markdown(
                f'<div class="member-badge"><span class="dot"></span>'
                f'当前已加载：{n_txt} 名队员</div>',
                unsafe_allow_html=True)

        # ─── 高级设置（折叠） ───
        with st.expander("⚙️ 高级算法设置", expanded=False):
            threshold = st.slider("模糊匹配灵敏度", 30, 100, 60, 5,
                                  help="越低越宽松（容忍 OCR 误差），60 为推荐值")
            max_frames = st.slider("视频抽帧密度", 60, 300, 120, 10,
                                   help="每个视频最多抽取的帧数（按每秒1帧计算），120帧≈2分钟视频")
            st.caption("默认参数适合大多数场景，通常无需调整")

        # ─── GitHub 与页面 ───
        st.markdown("### 🔄 仓库与页面")
        st.markdown("[GitHub 仓库](https://github.com/ZZZZZZeus496/spg-data-center)")
        st.markdown("**应用页面**：")
        streamlit_app_url = "https://spg-data-center-zzzzzzeus496.streamlit.app"
        st.markdown(f"[{streamlit_app_url}]({streamlit_app_url})")
        st.caption("若未部署，请将本仓库导入 [Streamlit Cloud](https://share.streamlit.io) 获取页面网址")

    # ──────── Hero Banner ────────
    streamlit_app_url = "https://spg-data-center-zzzzzzeus496.streamlit.app"
    st.markdown(f"""
    <div class="hero-banner">
        <h1>SPG 战队赛 · 数据中心</h1>
        <p class="sub">上传截图或比赛录屏，AI 全自动生成周报</p>
        <div class="flow">
            <div class="flow-step"><span class="n">1</span>上传素材</div>
            <span class="flow-arrow">→</span>
            <div class="flow-step"><span class="n">2</span>AI 智能识别</div>
            <span class="flow-arrow">→</span>
            <div class="flow-step"><span class="n">3</span>一键导出</div>
        </div>
        <p class="sub" style="margin-top:16px; font-size:0.85rem;">
            🌐 应用页面：<a href="{streamlit_app_url}" target="_blank" style="color:#ffd700;">{streamlit_app_url}</a>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ──────── 上传区域 ────────
    uploaded = st.file_uploader(
        "拖拽截图或录屏到此处",
        type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "avi"],
        accept_multiple_files=True,
    )

    if not uploaded:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📸  🎬</div>
            <p class="main-text">将结算截图或比赛录屏拖拽到上方</p>
            <p class="sub-text">支持 JPG · PNG · MP4 · MOV 格式，可一次上传多个文件</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── 分类文件 ──
    IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
    VID_EXT = {".mp4", ".mov", ".avi"}
    imgs, vids = [], []
    for f in uploaded:
        ext = Path(f.name).suffix.lower()
        if ext in IMG_EXT:
            imgs.append(f)
        elif ext in VID_EXT:
            vids.append(f)

    # ── 自动处理视频 → 提取结算帧 ──
    auto_frames: list[tuple[bytes, str]] = []
    if vids:
        st.markdown("---")
        for vf in vids:
            st.markdown(f"**🎬 处理视频：{vf.name}**")
            prog_extract = st.progress(0, text=f"正在从 {vf.name} 抽取画面帧...")
            raw_frames = extract_video_frames(vf.getvalue(), max_frames=max_frames)
            prog_extract.progress(0.5, text=f"已抽取 {len(raw_frames)} 帧，正在智能筛选结算画面...")

            settlement = filter_settlement_frames(raw_frames)
            prog_extract.progress(1.0,
                text=f"✅ {vf.name}：抽取 {len(raw_frames)} 帧 → 识别到 {len(settlement)} 个结算画面")

            if settlement:
                # 小尺寸预览
                prev_cols = st.columns(min(len(settlement), 6))
                for i, frame in enumerate(settlement[:6]):
                    with prev_cols[i]:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        st.image(rgb, caption=f"结算 #{i+1}", use_container_width=True)
                if len(settlement) > 6:
                    st.caption(f"... 共 {len(settlement)} 个结算画面")

                for i, frame in enumerate(settlement):
                    auto_frames.append(
                        (frame_to_png_bytes(frame), f"{vf.name}·结算{i+1}"))
            else:
                st.warning(f"⚠️ 未在 {vf.name} 中检测到结算画面，请确认视频内容")

    # ── 图片预览 ──
    if imgs:
        st.markdown("---")
        st.markdown(f"**🖼️ 已上传 {len(imgs)} 张截图**")
        n_show = min(len(imgs), 6)
        cols = st.columns(n_show)
        for i in range(n_show):
            with cols[i]:
                st.image(imgs[i], caption=imgs[i].name, use_container_width=True)
        if len(imgs) > 6:
            st.caption(f"... 还有 {len(imgs) - 6} 张")

    # ── 开始分析 ──
    total_count = len(imgs) + len(auto_frames)
    st.markdown("---")

    if total_count == 0:
        st.info("未检测到有效的结算画面，请尝试上传截图或确认视频中包含结算画面。")
        return

    can_go = bool(id2n) and total_count > 0
    if not id2n:
        st.warning("⚠️ 请在侧边栏配置队员名单")

    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        engine_label = "Qwen-VL-Max"
        go = st.button(f"🚀 开始 {engine_label} 分析（共 {total_count} 张结算画面）",
                       type="primary", disabled=not can_go, use_container_width=True)

    if go:
        do_analysis(imgs, auto_frames, api_key, id2n, all_ids, threshold, engine_id)

    if "result_df" in st.session_state and st.session_state.result_df is not None:
        show_report(st.session_state.result_df)


# ══════════════════════════════════════════════
# 分析流程
# ══════════════════════════════════════════════

def do_analysis(imgs, auto_frames, api_key, id2n, all_ids, thr, engine="qwen"):
    tasks = []
    for f in imgs:
        tasks.append((f.getvalue(), get_mime(f.name), f.name))
    for png_bytes, name in auto_frames:
        tasks.append((png_bytes, "image/png", name))

    total = len(tasks)
    rows, errors = [], []
    engine_label = "Qwen-VL-Max"
    prog = st.progress(0, text=f"🤖 {engine_label} 正在并发分析 {total} 个结算画面...")

    # ── 并发分析：最多 8 路并行，加速处理 ──
    MAX_WORKERS = min(8, total)
    completed_count = 0
    # 用字典保持原始顺序
    results_map = {}  # idx -> (row, error)

    def _analyze_one(idx, bts, mime, name):
        """单张图片分析（在子线程中执行）"""
        try:
            res = call_vision(bts, mime, api_key, engine=engine)
            row = result_to_row(res, id2n, all_ids, thr, name)
            if row:
                return idx, row, None
            else:
                return idx, None, f"{name}：结果为空"
        except Exception as e:
            return idx, None, f"{name}：{e}"

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_analyze_one, i, bts, mime, name): i
            for i, (bts, mime, name) in enumerate(tasks)
        }
        for future in as_completed(futures):
            completed_count += 1
            prog.progress(
                completed_count / total,
                text=f"🤖 {engine_label} 并发分析中... ({completed_count}/{total})"
            )
            idx, row, err = future.result()
            results_map[idx] = (row, err)

    # 按原始顺序收集结果
    for idx in sorted(results_map.keys()):
        row, err = results_map[idx]
        if row:
            rows.append(row)
        if err:
            errors.append(err)

    prog.progress(1.0, text=f"✅ 分析完成！成功 {len(rows)} 场，失败 {len(errors)} 场")

    if errors:
        with st.expander(f"⚠️ {len(errors)} 个画面分析失败（点击展开）", expanded=False):
            for e in errors:
                st.error(e)

    if rows:
        df = pd.DataFrame(rows)
        # 显示列（腾讯文档格式）
        display_cols = ["日期", "本方阵营", "对抗路选手", "中路选手", "发育路选手",
                        "打野选手", "游走选手", "胜负情况", "MVP", "备注"]
        display_cols = [c for c in display_cols if c in df.columns]
        st.session_state.result_df = df
        st.session_state.display_cols = display_cols
    else:
        st.error("❌ 未生成有效数据，请检查图片内容或 API Key")
        st.session_state.result_df = None


# ══════════════════════════════════════════════
# 结果展示：本周战报汇总
# ══════════════════════════════════════════════

def show_report(df: pd.DataFrame):
    st.markdown("---")

    # ── 标题 ──
    st.markdown("""
    <div class="report-header">
        <span class="rh-icon">📊</span>
        <h2>本周战报汇总</h2>
    </div>
    """, unsafe_allow_html=True)

    # ── 统计卡片 ──
    total = len(df)
    result_col = "胜负情况" if "胜负情况" in df.columns else "比赛结果"
    wins = int((df[result_col] == "胜利").sum()) if result_col in df.columns else 0
    losses = int((df[result_col] == "失败").sum()) if result_col in df.columns else 0
    rate = f"{wins / total * 100:.1f}%" if total > 0 else "0%"

    st.markdown(f"""
    <div class="stats-grid">
        <div class="s-card c-total"><p class="val">{total}</p><p class="desc">总场次</p></div>
        <div class="s-card c-win"><p class="val">{wins}</p><p class="desc">胜利</p></div>
        <div class="s-card c-lose"><p class="val">{losses}</p><p class="desc">失败</p></div>
        <div class="s-card c-rate"><p class="val">{rate}</p><p class="desc">胜率</p></div>
    </div>
    """, unsafe_allow_html=True)

    # ── 只展示腾讯文档格式列 ──
    display_cols = st.session_state.get("display_cols", [c for c in df.columns if not c.startswith("_")])
    show_df = df[display_cols].copy()

    # ── 表格样式 ──
    def style_result(val):
        if val == "胜利":
            return "background-color: rgba(56,239,125,0.22); color: #0d9e4f; font-weight: 700"
        if val == "失败":
            return "background-color: rgba(244,92,67,0.18); color: #d32f2f; font-weight: 700"
        return ""

    def style_mvp_col(val):
        if val and str(val).strip():
            return "color: #b8860b; font-weight: 900"
        return ""

    def style_medal_col(val):
        """备注列中的奖牌颜色"""
        s = str(val) if val else ""
        if "顶级" in s:
            return "background-color: rgba(255,215,0,0.30); font-weight: 700"
        if "金牌" in s:
            return "background-color: rgba(255,215,0,0.18)"
        if "银牌" in s:
            return "background-color: rgba(192,192,192,0.20)"
        if "铜牌" in s:
            return "background-color: rgba(205,127,50,0.15)"
        return ""

    styled = show_df.style

    if result_col in show_df.columns:
        styled = styled.map(style_result, subset=[result_col])
    if "MVP" in show_df.columns:
        styled = styled.map(style_mvp_col, subset=["MVP"])
    if "备注" in show_df.columns:
        styled = styled.map(style_medal_col, subset=["备注"])

    styled = (
        styled
        .set_properties(**{"text-align": "center"})
        .set_table_styles([
            {"selector": "thead th", "props": [
                ("background-color", "#1a1a2e"), ("color", "#ffd700"),
                ("font-weight", "700"), ("text-align", "center"),
                ("padding", "12px 14px"), ("font-size", "0.9rem"),
                ("border-bottom", "2px solid rgba(255,215,0,0.3)"),
            ]},
            {"selector": "tbody tr:nth-child(even)", "props": [
                ("background-color", "#f8f8fc")]},
            {"selector": "tbody tr:nth-child(odd)", "props": [
                ("background-color", "#ffffff")]},
            {"selector": "tbody td", "props": [
                ("padding", "10px 12px"), ("font-size", "0.88rem")]},
        ])
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── 结算胜场表：仅统计「胜利+MVP」场次，每场 +1 结算胜场 ──
    result_col = "胜负情况" if "胜负情况" in df.columns else "比赛结果"
    if "_mvp_name" in df.columns and result_col in df.columns:
        win_mvp = df[
            (df[result_col] == "胜利") &
            (df["_mvp_name"].str.strip() != "")
        ][["_mvp_name"]].copy()
        if not win_mvp.empty:
            st.markdown("")
            st.markdown("### 🏆 本周结算胜场表（胜利+MVP 场次）")
            win_rank = (
                win_mvp.groupby("_mvp_name").size()
                .reset_index(name="结算胜场")
                .sort_values("结算胜场", ascending=False)
                .reset_index(drop=True)
            )
            win_rank.columns = ["选手", "结算胜场"]
            win_rank.index = range(1, len(win_rank) + 1)
            win_rank.index.name = "排名"

            def style_win_rank(row):
                idx = row.name
                if idx == 1:
                    return ["background-color: rgba(255,215,0,0.25); font-weight:900"] * len(row)
                if idx == 2:
                    return ["background-color: rgba(192,192,192,0.20); font-weight:700"] * len(row)
                if idx == 3:
                    return ["background-color: rgba(205,127,50,0.15); font-weight:600"] * len(row)
                return [""] * len(row)

            win_styled = (
                win_rank.style
                .apply(style_win_rank, axis=1)
                .set_properties(**{"text-align": "center"})
                .set_table_styles([
                    {"selector": "thead th", "props": [
                        ("background-color", "#1a1a2e"), ("color", "#ffd700"),
                        ("font-weight", "700"), ("text-align", "center"), ("padding", "10px"),
                    ]},
                ])
            )
            st.dataframe(win_styled, use_container_width=True)
            st.caption("结算规则：每场胜利且获 MVP，结算胜场 +1。")

    # ── MVP 评分排行榜（按评分总和排名） ──
    if "_mvp_name" in df.columns and "_mvp_score" in df.columns:
        mvp_data = df[df["_mvp_name"].str.strip() != ""][["_mvp_name", "_mvp_score"]].copy()
        if not mvp_data.empty:
            st.markdown("")
            st.markdown("### 🏅 周 MVP 排行榜（按评分）")

            # 按选手汇总：MVP次数 + 总评分
            ranking = (
                mvp_data.groupby("_mvp_name")
                .agg(MVP次数=("_mvp_name", "count"), 总评分=("_mvp_score", "sum"))
                .sort_values("总评分", ascending=False)
                .reset_index()
            )
            ranking.columns = ["选手", "MVP次数", "总评分"]
            ranking["总评分"] = ranking["总评分"].round(1)
            ranking.index = range(1, len(ranking) + 1)
            ranking.index.name = "排名"

            # 标注前三名
            def style_rank(row):
                idx = row.name
                if idx == 1:
                    return ["background-color: rgba(255,215,0,0.25); font-weight:900"] * len(row)
                if idx == 2:
                    return ["background-color: rgba(192,192,192,0.20); font-weight:700"] * len(row)
                if idx == 3:
                    return ["background-color: rgba(205,127,50,0.15); font-weight:600"] * len(row)
                return [""] * len(row)

            rank_styled = (
                ranking.style
                .apply(style_rank, axis=1)
                .set_properties(**{"text-align": "center"})
                .set_table_styles([
                    {"selector": "thead th", "props": [
                        ("background-color", "#1a1a2e"), ("color", "#ffd700"),
                        ("font-weight", "700"), ("text-align", "center"), ("padding", "10px"),
                    ]},
                ])
            )
            st.dataframe(rank_styled, use_container_width=True)

            st.caption("排名规则：MVP 次数相同时，按评分总和排序。第1名为周 MVP 状元，第2名为榜眼，第3名为探花。")

    # ── 下载 ──
    st.markdown("---")
    st.markdown("### 📥 导出报表")

    # 导出时只包含腾讯文档列
    export_df = df[display_cols].copy()

    _, dl_col, _ = st.columns([1, 2, 1])
    with dl_col:
        st.download_button(
            "⬇️  下载 战队赛统计.xlsx",
            data=df_to_excel(export_df),
            file_name="战队赛统计.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    # ── 同步到 GitHub ──
    st.markdown("")
    st.markdown("### 🔄 同步选手信息到 GitHub")
    repo_url = "https://github.com/ZZZZZZeus496/spg-data-center"
    st.markdown(f"**仓库地址**：[{repo_url}]({repo_url})")
    st.markdown("")
    if st.button("📤 推送 members.json 到 GitHub", type="secondary", use_container_width=True):
        try:
            root = Path(__file__).resolve().parent
            subprocess.run(["git", "add", "members.json"], cwd=root, capture_output=True, text=True, timeout=10)
            r2 = subprocess.run(
                ["git", "commit", "-m", "更新队员名单"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            r3 = subprocess.run(["git", "push", "origin", "master"], cwd=root, capture_output=True, text=True, timeout=30)
            if r3.returncode == 0:
                st.success("✅ 已成功推送到 GitHub！")
                st.markdown(f"**members.json 直链**：[{repo_url}/blob/master/members.json]({repo_url}/blob/master/members.json)")
            else:
                st.warning("推送可能失败或无新改动，请检查 Git 配置。")
                if r2.returncode != 0 and "nothing to commit" in (r2.stdout or r2.stderr or ""):
                    st.info("当前无文件变更，无需提交。")
        except subprocess.TimeoutExpired:
            st.error("操作超时，请手动推送。")
        except FileNotFoundError:
            st.error("未检测到 Git，请先安装 Git 并配置。")
        except Exception as e:
            st.error(f"同步失败：{e}")


# ══════════════════════════════════════════════
main()
