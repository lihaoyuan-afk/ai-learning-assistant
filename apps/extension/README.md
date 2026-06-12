# AgentLearn 浏览器扩展

Chrome 扩展，一键将当前网页或视频导入 AgentLearn 知识库。

## 安装（开发者模式）

1. 打开 Chrome，访问 `chrome://extensions/`
2. 开启右上角**开发者模式**
3. 点击**加载已解压的扩展程序**
4. 选择本目录（`apps/extension/`）

## 使用

1. 打开任意网页或 YouTube/B 站视频
2. 点击工具栏中的 AgentLearn 扩展图标
3. 点击**导入到知识库**
4. 等待解析完成后点击**前往查看文档**

## 设置

点击右上角 ⚙ 可配置：

- **后端 API 地址**：默认使用线上 Cloud Run 地址
  - 线上：`https://ai-learning-api-189424783668.us-central1.run.app`
  - 本地开发：`http://localhost:8000`
- **访问密码**：线上环境填 `lihaoyuan123`，本地开发留空

## 支持的内容类型

- 任意网页（正文提取，去除广告和导航）
- YouTube 视频（字幕 + 章节 + 简介）
- B 站视频（字幕 + 简介）
