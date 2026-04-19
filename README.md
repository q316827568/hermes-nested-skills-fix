# Hermes WebUI Nested Skills Fix

修复 Hermes WebUI 无法显示嵌套 Skills 的问题。

## 作用与原理

### 作用

本项目解决了 Hermes WebUI 无法显示深层嵌套目录中 Skills 的问题。修复后，无论 Skills 组织在多少层深的目录中，WebUI 都能正确发现和显示它们。

**修复前：**
```
skills/
├── productivity/
│   └── markitdown/SKILL.md     ✅ 显示（2层）
└── mlops/
    ├── cloud/
    │   └── modal/SKILL.md      ❌ 不显示（4层）
    └── training/
        └── finetune/SKILL.md   ❌ 不显示（4层）
```

**修复后：**
```
所有层级的 Skills 都能正确显示 ✅
```

### 原理

#### 1. 问题根因

WebUI 后端使用**两层层级扫描**逻辑：

```javascript
// 原始代码逻辑
for (category of skillsDir) {        // 第1层：分类
    for (skill of categoryDir) {     // 第2层：Skill
        if (has_SKILL_md) add_skill();
    }
}
```

这导致 3 层以上的嵌套目录被忽略。

#### 2. 解决方案核心

将**固定层级扫描**改为**递归深度优先搜索（DFS）**：

```javascript
async function findSkillsRecursive(dir, disabledList, prefix = '') {
    for (entry of dir) {
        if (has_SKILL_md(entry)) {
            // 找到 Skill，添加到列表
            skills.push({name, fullName: prefix + entry.name});
        } else {
            // 可能是子分类，递归查找
            skills.push(...await findSkillsRecursive(entry, prefix));
        }
    }
    return skills;
}
```

#### 3. 关键实现点

| 组件 | 修改内容 | 目的 |
|------|----------|------|
| **递归扫描函数** | `findSkillsRecursive()` | 深度优先遍历所有子目录 |
| **路径前缀追踪** | `prefix` 参数 | 记录嵌套路径如 `cloud/modal` |
| **路径兼容层** | `findSkillDir()` | 支持前端请求的简化路径 |
| **SKILL.md 读取** | 自动补全路径 | 处理 `mlops/modal` → `mlops/cloud/modal` |

#### 4. 数据流

```
前端请求                    后端处理                      返回结果
─────────────────────────────────────────────────────────────────
GET /api/hermes/skills
                          findSkillsRecursive()
                          ├─ mlops/
                          │  ├─ cloud/modal/ ✅
                          │  └─ training/finetune/ ✅
                          └─ productivity/
                             └─ markitdown/ ✅
                          ───────────────────────────────►
                          [{name, fullName, description}, ...]
```

#### 5. 向后兼容

为保持前端代码不变，后端添加路径兼容层：

```javascript
// 前端请求: /api/hermes/skills/mlops/modal/SKILL.md
// 实际路径: /api/hermes/skills/mlops/cloud/modal/SKILL.md
// 兼容层自动查找并返回正确内容
```

---

## 问题描述

当 Skills 组织在多层嵌套目录中时（如 `mlops/cloud/modal/`），WebUI 只能扫描两层目录，导致深层 Skills 无法显示。

### 症状

- WebUI 显示的 Skills 数量少于预期
- 嵌套目录（3层以上）中的 Skills 不显示
- API `/api/hermes/skills` 返回不完整的 Skill 列表

### 原因

WebUI 的 `filesystem.js` 只扫描两层目录：
```
skills/<category>/<skill>/SKILL.md  ✅ 正常显示
skills/<category>/<subcategory>/<skill>/SKILL.md  ❌ 无法显示
```

## 解决方案

### 1. 添加递归扫描函数

在 `~/.hermes/node/lib/node_modules/hermes-web-ui/dist/server/routes/hermes/filesystem.js` 中添加：

```javascript
// 递归查找所有 Skills
async function findSkillsRecursive(dir, disabledList, prefix = '') {
    const skills = [];
    let entries;
    try {
        entries = await (0, promises_1.readdir)(dir, { withFileTypes: true });
    } catch {
        return skills;
    }
    for (const entry of entries) {
        if (!entry.isDirectory() || entry.name.startsWith('.')) continue;
        const subDir = (0, path_1.join)(dir, entry.name);
        const skillPath = prefix ? `${prefix}/${entry.name}` : entry.name;
        
        const skillMd = await safeReadFile((0, path_1.join)(subDir, 'SKILL.md'));
        if (skillMd) {
            skills.push({
                name: entry.name,
                fullName: skillPath,
                description: extractDescription(skillMd),
                enabled: !disabledList.includes(entry.name),
            });
        } else {
            const nested = await findSkillsRecursive(subDir, disabledList, skillPath);
            skills.push(...nested);
        }
    }
    return skills;
}
```

### 2. 修改 Skills 列表路由

将 `/api/hermes/skills` 路由改为使用递归扫描。

### 3. 添加嵌套路径查找

前端可能请求 `mlops/modal/files` 但实际路径是 `mlops/cloud/modal/`，需要添加查找辅助函数。

详细实现见 `SKILL.md`。

## 定时维护任务

### Cron 配置

```bash
# Skills 维护任务 - 每天 00:30 执行
30 0 * * * HERMES_HOME=/home/reload/.hermes /home/reload/.hermes/scripts/skills_daily_maintenance.sh
```

### 维护脚本

`skills_daily_maintenance.sh`:
```bash
#!/bin/bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT="$HERMES_HOME/hermes-agent"
LOG_FILE="$HERMES_HOME/logs/skills_maintenance.log"

mkdir -p "$(dirname "$LOG_FILE")"
source "$HERMES_AGENT/venv/bin/activate"

echo "=== $(date) ===" >> "$LOG_FILE"
python3 "$HERMES_AGENT/tools/skills_maintenance.py" all >> "$LOG_FILE" 2>&1

# 清理旧日志（保留 30 天）
find "$(dirname "$LOG_FILE")" -name "*.log" -mtime +30 -delete 2>/dev/null
```

### 维护任务内容

Python 维护脚本 (`skills_maintenance.py`) 执行：

1. **更新 Hot Skills** - 根据使用频率更新热门 Skills 列表
2. **清理过期缓存** - 清理超过 24 小时的缓存文件
3. **生成使用报告** - 生成 30 天内的 Skills 使用统计
4. **同步到 GitHub** - 可选的远程同步

## 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 完整的修复方案文档 |
| `SKILL_v1.md` | 初始版本（简化版） |
| `scripts/skills_daily_maintenance.sh` | 定时维护脚本 |
| `scripts/skills_maintenance.py` | Python 维护任务 |

## 测试验证

```bash
# 测试嵌套 Skills 发现
curl -s "http://localhost:8648/api/hermes/skills?token=YOUR_TOKEN" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(len([c for c in d['categories'] if c['name']=='mlops'][0]['skills']))"

# 测试向后兼容
curl -s "http://localhost:8648/api/hermes/skills/mlops/modal/SKILL.md?token=YOUR_TOKEN"
curl -s "http://localhost:8648/api/hermes/skills/mlops/modal/files?token=YOUR_TOKEN"
```

## 验证结果

修复后：
- `mlops` 分类应显示所有子分类 Skills（models/*, training/*, inference/*）
- `academic-research-skills` 应显示 deep-research, academic-paper 等

## 注意事项

1. 修改前备份原文件
2. 修改后重启 WebUI：`pkill -f "node.*hermes-web-ui"; cd ~/.hermes/node/lib/node_modules/hermes-web-ui && node dist/server/index.js &`
3. 前端代码无需修改 - 后端处理兼容性

## 相关链接

- [Hermes Agent](https://github.com/q316827568/hermes-agent)
- [问题反馈](https://github.com/q316827568/hermes-nested-skills-fix/issues)
