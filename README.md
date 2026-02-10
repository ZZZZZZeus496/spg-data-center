# 王者荣耀战队赛 - 周报自动化工具

自动识别王者荣耀战队赛结算截图，提取比赛数据，生成 Excel 周报。

## 功能

- **截图识别**：使用 GPT-4o-mini Vision API 自动识别结算截图中的比赛信息
- **队员匹配**：通过模糊匹配将游戏 ID 映射到队员真实名字（支持一人多 ID）
- **周报导出**：自动生成包含比赛结果、队员、MVP 等信息的 Excel 周报

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env` 并填入你的 OpenAI API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```
OPENAI_API_KEY=sk-你的API密钥
```

### 3. 配置队员信息

编辑 `members.json`，填入你的战队队员信息：

```json
{
    "队员列表": [
        {
            "真实名字": "张三",
            "游戏ID": ["张三的ID1", "张三的ID2"]
        }
    ]
}
```

每个队员可以有多个游戏 ID，系统会自动处理模糊匹配。

### 4. 放入截图

将战队赛结算截图放入 `images/` 文件夹（支持 PNG、JPG、JPEG、WebP、BMP 格式）。

### 5. 运行

```bash
python main.py
```

也可以指定图片文件夹：

```bash
python main.py 我的截图文件夹
```

运行后会在当前目录生成 `weekly_report.xlsx`。

## 项目结构

```
├── main.py                 # 主流程脚本
├── member_matcher.py       # 队员模糊匹配模块
├── screenshot_analyzer.py  # 截图识别模块（GPT-4o-mini Vision）
├── members.json            # 队员名字与游戏 ID 映射
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── images/                 # 放置战队赛截图
└── weekly_report.xlsx      # 生成的周报（运行后产生）
```

## 输出格式

生成的 Excel 文件包含以下列：

| 日期 | 比赛结果 | 队员1 | 队员2 | 队员3 | 队员4 | 队员5 | MVP得主 | 金牌 | 银牌 | 来源图片 |
|------|---------|-------|-------|-------|-------|-------|--------|------|------|---------|

## 注意事项

- 需要有效的 OpenAI API Key（支持 GPT-4o-mini 模型）
- 截图质量越高，识别结果越准确
- 模糊匹配阈值默认为 60 分，可在代码中调整
- 每次调用 API 会消耗 Token，建议批量处理以节省费用
