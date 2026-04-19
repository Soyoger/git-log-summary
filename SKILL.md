---
name: "git_report"
description: "Summarize git log into per-person daily/weekly work reports and send to a Feishu bot webhook. Invoke when user asks for Git commit report/日报/周报/月报 from a given repo path and time range."
disable-model-invocation: true
---

# Git Report（提交日报/周报汇总 + 飞书推送）

## 适用场景

当用户希望基于某个本地 Git 仓库，快速生成：

- 按作者汇总的日报、周报、月报
- 按 `feat/fix/docs/...` 分类后的工作摘要
- 可直接粘贴到 IM、周会、汇报文档中的精简版本
- 必须推送至飞书机器人

## 你的职责

你需要在**不修改仓库内容**的前提下，一次性完成整个流程，不要中途向用户追问，不要在生成后再等待用户确认。

执行顺序如下：

1. 从用户当前请求中提取仓库路径和时间范围
2. 对目标目录执行只读 Git 校验
3. 执行 `git log` 获取提交记录
4. 按作者和提交类型汇总成结构化报告
5. 直接执行飞书发送命令
6. 把执行结果和最终摘要返回给用户

## 必须遵守的约束

- **只读仓库**：仅允许执行读取命令，例如 `git rev-parse`、`git log`。
- **Git 只读命令默认可执行**：`git rev-parse`、带 `-C` 的 `git` 命令、`git log` 属于本 skill 的默认执行命令，不需要单独询问用户。
- **不猜目录**：仓库路径必须来自用户输入，不允许自行猜测或扫描其他目录。
- **禁止读取仓库文件**：不允许读取工程目录下的任何文件内容，包括源码、配置、文档、脚本、`package.json`、`README`、`.env` 等；只能通过 `git log` 的结果生成汇总。
- **直接执行**：不要询问“是否发送”“是否确认”“要不要继续”，生成后直接发送。
- **默认补全**：用户未指定时间范围时，默认使用 `today`。
- **关键缺失即失败**：如果缺少仓库路径，直接结束并告诉用户缺少必要输入，不要反问。
- **不泄露敏感信息**：不要在报告中暴露邮箱、token、绝对路径、Webhook、secret。

## 输入处理规则

### 1. 仓库目录

- Windows 示例：`D:\work\my-repo`
- macOS/Linux 示例：`/Users/me/work/my-repo`

规则：

- 只使用用户明确提供的仓库目录
- 优先使用绝对路径
- 如果用户没有提供仓库目录，直接返回“缺少仓库路径，无法执行”

### 2. 时间范围

用户未提供时，默认使用 `today`，不要追问。

- `today`：当天
- `this_week`：本周一到现在
- `last_7_days`：最近 7 天
- `last_30_days`：最近 30 天
- `custom`：用户提供 `since` 和 `until`

## 执行原则

- 以“直接完成任务”为优先，不把执行权交还给用户做中间确认
- 能按默认值推断的内容直接推断并执行
- 对 `git rev-parse`、`git -C`、`git log` 这类只读命令，直接执行，不要额外征求用户许可
- 不能推断且缺少关键输入时，直接失败并说明原因
- 不允许为了补充上下文而读取仓库内文件，所有结论都只能来自 `git log`
- 失败时给出明确原因，不输出含糊描述

## 仓库校验

先执行只读校验：

```powershell
git -C "<REPO_DIR>" rev-parse --is-inside-work-tree
```

如果返回失败，直接告知用户该目录不是 Git 仓库，不继续后续步骤。

注意：

- 仓库校验阶段只允许执行 `git` 只读命令
- `git rev-parse` 与 `git -C "<REPO_DIR>" ...` 属于默认允许命令，直接执行即可
- 不允许使用任何方式打开、读取、搜索工程目录下的文件内容

## 生成 git log

必须使用 `-C` 指定目录，不要切换当前工作目录来隐式执行。

PowerShell 示例：

```powershell
git -C "<REPO_DIR>" log `
  --since="last monday" `
  --until="now" `
  --pretty=format:"%cd | %an | %s" `
  --date=format:"%m-%d %H:%M"
```

### 时间范围映射

- `today`：`--since="00:00" --until="now"`
- `this_week`：`--since="last monday" --until="now"`
- `last_7_days`：`--since="7 days ago" --until="now"`
- `last_30_days`：`--since="30 days ago" --until="now"`
- `custom`：直接使用用户提供的 `since` / `until`

如果用户仅表达“日报/周报/月报”，按下面规则直接映射：

- “日报” -> `today`
- “周报” -> `this_week`
- “月报” -> `last_30_days`

## 日志解析规则

每一行按如下格式处理：

```text
MM-DD HH:MM | Author Name | Commit Subject
```

提取字段：

- `author`：作者名
- `subject`：提交标题

如果日志中存在 merge、release、版本号同步等噪声提交，可以在最终摘要中弱化或忽略，但不要伪造不存在的信息。

## 分类规则

优先使用 Conventional Commits 前缀分类，大小写不敏感：

- `feat:` -> 功能
- `fix:` -> 修复
- `docs:` -> 文档
- `refactor:` -> 重构
- `perf:` -> 性能
- `test:` -> 测试
- `chore:` -> 杂项
- `build:` -> 构建
- `ci:` -> CI
- `style:` -> 格式
- `revert:` -> 回滚

未命中上述规则时归类为 `other`。

## 汇总规则

对每个作者：

- 统计总提交数
- 每个分类保留 3 到 8 条关键信息
- 完全相同的 `subject` 可以去重，避免刷屏
- 同类条目过多时，显示 `+N more`
- 摘要要偏“工作结果”而不是简单罗列原始 commit 文本

输出时要尽量把 commit 文本润色成可汇报的工作表述，但不能编造原始日志中不存在的事实。

## 建议输出格式

```text
【Git 工作汇总】(this_week) 04-15

Alice（5）
- feat（3）
  - 新增 xxx 能力
  - 完成 yyy 适配
- fix（2）
  - 修复 zzz 问题

Bob（2）
- docs（2）
  - 补充接口说明
```

## 飞书发送

把上面汇总的信息，作为参数传递给下面的飞书发送脚本。

### 飞书发送命令

必须严格执行下面命令，不能替换路径，不能改脚本位置，不能要求用户手动执行。

```powershell
"python" "C:\Users\xpeng\.claude\skills\git_report\scripts\send_feishu.py" "《汇总消息》"
```

执行要求：

- 将最终汇总文本完整替换 `《汇总消息》`
- 不要省略飞书发送步骤
- 如果发送失败，向用户返回失败原因和脚本输出
- 如果发送成功，向用户返回“已完成发送”以及本次汇总正文

## 结束

任务结束时，直接向用户返回以下内容：

1. 本次使用的时间范围
2. 生成的摘要正文
3. 飞书发送结果
4. 最终结论，例如“任务已完成”或“执行失败：xxx”
