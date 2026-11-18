# 分支与提交规范

## 分支

- `main`：只放打了 tag 的稳定版本（如 v0.1、v0.2），不直接在上面开发
- `dev`：日常集成分支，功能完成后合并到这里
- `feature/xxx`：功能分支，从 `dev` 拉出，完成后合回 `dev`，例如 `feature/whisper-asr`

## 工作流程

1. 切到 `dev` 并拉取最新：`git checkout dev` → `git pull`
2. 拉出功能分支：`git checkout -b feature/xxx`
3. 开发，小步提交，每次 commit 只做一件事
4. 完成后合回 `dev`，推送
5. 一个版本全部完成后，把 `dev` 合并到 `main`，并打 tag

## Commit 规范

格式：`前缀: 简短说明`

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 只改文档
- `refactor:` 重构，不改变功能
- `chore:` 杂项配置，如 LFS、目录结构