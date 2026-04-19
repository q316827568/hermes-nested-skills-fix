---
name: webui-nested-skills-fix
description: Fix WebUI to display nested skills by modifying backend routes for recursive scanning and path compatibility
version: 1.0.0
author: hermes
---

# WebUI Nested Skills Fix

When WebUI doesn't display nested skills (skills organized in subdirectories like `mlops/cloud/modal/`), the backend routes need modification.

## Problem Symptoms

- WebUI shows fewer skills than expected
- Skills in nested directories (3+ levels deep) don't appear
- API `/api/hermes/skills` returns incomplete skill lists

## Root Cause

WebUI's `filesystem.js` only scans two directory levels:
```
skills/<category>/<skill>/SKILL.md  ✅ Works
skills/<category>/<subcategory>/<skill>/SKILL.md  ❌ Missed
```

## Solution

### 1. Add Recursive Skill Discovery Function

Add to `~/.hermes/node/lib/node_modules/hermes-web-ui/dist/server/routes/hermes/filesystem.js`:

```javascript
// Helper: Recursively find all skills in a directory (supports nested categories)
async function findSkillsRecursive(dir, disabledList, prefix = '') {
    const skills = [];
    let entries;
    try {
        entries = await (0, promises_1.readdir)(dir, { withFileTypes: true });
    }
    catch {
        return skills;
    }
    for (const entry of entries) {
        if (!entry.isDirectory() || entry.name.startsWith('.'))
            continue;
        const subDir = (0, path_1.join)(dir, entry.name);
        const skillPath = prefix ? `${prefix}/${entry.name}` : entry.name;
        // Check if this directory is a skill (has SKILL.md)
        const skillMd = await safeReadFile((0, path_1.join)(subDir, 'SKILL.md'));
        if (skillMd) {
            // This is a skill directory
            skills.push({
                name: entry.name,
                fullName: skillPath, // full path like "cloud/modal"
                description: extractDescription(skillMd),
                enabled: !disabledList.includes(entry.name),
            });
        }
        else {
            // This might be a sub-category, recurse into it
            const nested = await findSkillsRecursive(subDir, disabledList, skillPath);
            skills.push(...nested);
        }
    }
    return skills;
}
```

### 2. Modify Skills List Route

Replace the `/api/hermes/skills` route to use recursive discovery:

```javascript
exports.fsRoutes.get('/api/hermes/skills', async (ctx) => {
    const skillsDir = (0, path_1.join)(hermesDir(), 'skills');
    // ... config reading ...
    for (const entry of entries) {
        // ... category setup ...
        // Use recursive discovery instead of flat scan
        const skills = await findSkillsRecursive(catDir, disabledList, '');
        // ... rest of route ...
    }
});
```

### 3. Add Nested Path Lookup for Files Route

The frontend may request `mlops/modal/files` but the actual path is `mlops/cloud/modal/`. Add lookup helper:

```javascript
async function findSkillDir(skillsDir, category, skillName) {
    // First try direct path: category/skillName
    const directPath = (0, path_1.join)(skillsDir, category, skillName);
    const directMd = await safeReadFile((0, path_1.join)(directPath, 'SKILL.md'));
    if (directMd) return directPath;
    
    // Search recursively under category for nested skill
    const catDir = (0, path_1.join)(skillsDir, category);
    return await findSkillDirRecursive(catDir, skillName);
}

async function findSkillDirRecursive(dir, skillName) {
    // Recursively search for skill directory by name
    // Returns full path when found, null otherwise
}
```

### 4. Update Files Route for Compatibility

```javascript
exports.fsRoutes.get('/api/hermes/skills/{*path}/files', async (ctx) => {
    // Check if direct path exists
    // If not, try nested lookup for category/skillName format
    // Return files list
});
```

### 5. Update SKILL.md Read Route

The frontend requests SKILL.md content via `/api/hermes/skills/${category}/${skill}` (NOT `/SKILL.md` suffix!). Must handle both formats:

```javascript
exports.fsRoutes.get('/api/hermes/skills/{*path}', async (ctx) => {
    let content = await safeReadFile(fullPath);
    
    if (content === null) {
        // Case 1: path ends with /SKILL.md
        if (filePath.endsWith('/SKILL.md')) {
            // Try nested lookup
        }
        // Case 2: path is category/skillName (no file extension) - auto append SKILL.md
        else if (!filePath.includes('.')) {
            const parts = filePath.split('/');
            if (parts.length >= 2) {
                let skillDir = (0, path_1.join)(skillsDir, filePath);
                let mdPath = (0, path_1.join)(skillDir, 'SKILL.md');
                content = await safeReadFile(mdPath);
                // If not found, try nested lookup
                if (content === null && parts.length === 2) {
                    const found = await findSkillDir(skillsDir, parts[0], parts[1]);
                    if (found) {
                        content = await safeReadFile((0, path_1.join)(found, 'SKILL.md'));
                    }
                }
            }
        }
    }
});
```

## Testing

```bash
# Test nested skill discovery
curl -s "http://localhost:8648/api/hermes/skills?token=YOUR_TOKEN" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(len([c for c in d['categories'] if c['name']=='mlops'][0]['skills']))"

# Test backward compatibility
curl -s "http://localhost:8648/api/hermes/skills/mlops/modal/SKILL.md?token=YOUR_TOKEN"
curl -s "http://localhost:8648/api/hermes/skills/mlops/modal/files?token=YOUR_TOKEN"
```

## Verification

After changes, nested skills should appear in WebUI:
- `mlops` should show all subcategory skills (models/*, training/*, inference/*)
- `academic-research-skills` should show deep-research, academic-paper, etc.

## Key Files

- `~/.hermes/node/lib/node_modules/hermes-web-ui/dist/server/routes/hermes/filesystem.js`

## Notes

- Backup the original file before modification
- Restart WebUI after changes: `pkill -f "node.*hermes-web-ui"; cd ~/.hermes/node/lib/node_modules/hermes-web-ui && node dist/server/index.js &`
- Frontend code doesn't need modification - backend handles compatibility
