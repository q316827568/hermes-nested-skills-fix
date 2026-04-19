---
name: hermes-webui-nested-skills-fix
description: 修复 Hermes WebUI 无法显示嵌套 skills 的问题。当 skills 目录结构为三层或更深时，WebUI 默认只能扫描两层，需要修改后端代码支持递归扫描和智能路径查找。
version: 1.0.0
author: hermes-agent
---

# Hermes WebUI 嵌套 Skills 显示修复

## 问题描述

Hermes WebUI 的 skills 列表 API 默认只扫描两层目录结构，无法识别嵌套的三层或更深层结构。

## 解决方案

修改文件：`~/.hermes/node/lib/node_modules/hermes-web-ui/dist/server/routes/hermes/filesystem.js`

### 关键修改点

1. **添加递归查找函数** `findSkillsRecursive()` - 递归扫描所有嵌套目录
2. **添加智能路径查找** `findSkillDir()` - 支持旧格式请求自动查找嵌套路径
3. **修改 `/api/hermes/skills` 路由** - 使用递归扫描替代两层循环
4. **修改 `/api/hermes/skills/{*path}/files` 路由** - 支持嵌套路径和旧格式兼容
5. **修改 `/api/hermes/skills/{*path}` 路由** - 支持 SKILL.md 的嵌套路径查找

## 注意事项

- 修改前备份原文件
- WebUI 包更新后需要重新应用修改
- 前端无需修改，后端自动兼容

## 详细代码

见本次会话的修改记录，或使用 `git diff` 查看变更。
