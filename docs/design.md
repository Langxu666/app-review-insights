# App Review Insights - 设计文档

## 项目概述
App Review Insights 是一个应用商店评论分析系统，用于收集、分析和提取移动应用评论中的有价值信息。

## 技术栈
- 前端：Next.js (App Router) + TypeScript + Tailwind CSS
- 后端：FastAPI + Python 3.11+

## 目录结构
```
app-review-insights/
├── frontend/          # 前端应用
├── backend/           # 后端服务
└── docs/              # 文档
```

## 核心模块

### 1. Collector（数据收集器）
负责从各大应用商店收集评论数据。

### 2. Analyzer（分析器）
对收集到的评论进行情感分析、关键词提取和摘要生成。

### 3. Planner（规划器）
基于分析结果生成改进建议和规划。

### 4. API（接口层）
提供 RESTful API 供前端调用。