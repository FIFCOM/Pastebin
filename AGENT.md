# Material Bin 版本管理

本文是维护者和自动化 agent 的版本操作规范。仓库内产品版本只接受
`MAJOR.MINOR.PATCH`，当前基线版本为 `1.0.0`，唯一来源是根目录的
`VERSION` 文件。

## 版本规则

- 常规提交由 Git hook 自动将 `PATCH` 加一，例如 `1.0.0 -> 1.0.1`。
- `MAJOR` 或 `MINOR` 只能人工提升，提升时 `PATCH` 必须归零。
- 不要人工修改单个版本字段。`.githooks/versioning.py` 会同步所有受管文件。
- 不要使用 `git commit --no-verify` 绕过 hook。GitHub Actions 会拒绝版本不一致或
  版本跃迁非法的提交。
- 正式版本 tag 必须是 `vX.Y.Z`，并与提交中的 `VERSION` 完全一致。
- 本地 `.env` 不受 hook 管理。若其中设置了 `VERSION`，它会覆盖仓库版本；除非
  确实需要运行时覆盖，否则应删除该项。

## 启用 Git hook

每次克隆仓库后执行一次：

```bash
./.githooks/install.sh
```

确认配置：

```bash
git config --get core.hooksPath
# 预期输出：.githooks
```

Git 不会自动启用仓库中受版本控制的 hook，因此这一步不能省略。hook 只在本地
Git 命令中运行；GitHub 网页创建的提交和 merge commit 不会运行 hook。最终的
`master` 提交应在已启用 hook 的本地仓库中创建，否则容器工作流会校验失败。

## 常规提交

按正常流程提交，不要手工改版本：

```bash
git add <files>
git commit -m "fix: describe the change"
```

`pre-commit` 会计算下一个 patch 版本、同步并暂存以下字段：

```bash
python3 .githooks/versioning.py paths
```

提交前若这些受管文件含有未暂存修改，hook 会停止，防止意外暂存其他改动。先将
相关修改暂存或恢复，再重新提交。

修改最近一次提交且不希望产生新版本时，显式保留版本：

```bash
MATERIALBIN_KEEP_VERSION=1 git commit --amend
```

## 人工提升较大版本

提升 minor 或 major 时，先选择目标版本。必须大于当前版本且 patch 为 `0`。

```bash
# 例如：1.4.7 -> 1.5.0
python3 .githooks/versioning.py set 1.5.0

# 或者：1.5.9 -> 2.0.0
python3 .githooks/versioning.py set 2.0.0
```

检查并暂存全部受管版本文件：

```bash
python3 .githooks/versioning.py check
git add -- $(python3 .githooks/versioning.py paths)
git commit -m "chore: release 1.5.0"
```

hook 会识别合法的人工 major/minor 提升并保留目标版本，不会再将它改成 patch
版本。将提交推送到 `master` 并确认容器工作流通过后，创建正式发布 tag：

```bash
git push origin master
git tag -a v1.5.0 -m "Release v1.5.0"
git push origin v1.5.0
```

`master` push 会发布精确版本、`sha-*` 和 `edge` 镜像标签。正式 tag 会额外发布
`MAJOR.MINOR` 和 `latest`；例如 `v1.5.0` 会发布 `1.5.0`、`1.5`、`latest`
和对应的 `sha-*`。

## 校验和恢复

检查所有版本字段是否一致：

```bash
python3 .githooks/versioning.py check
```

如果字段被单独修改，以 `VERSION` 为准重新同步：

```bash
python3 .githooks/versioning.py set "$(python3 .githooks/versioning.py current)"
```

不要移动或复用已经推送的版本 tag。错误 tag 尚未推送时可以本地删除后重新创建；
已经发布的版本应通过新的 patch 版本修正。
