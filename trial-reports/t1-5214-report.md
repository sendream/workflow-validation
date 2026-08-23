# Black 试运行 T1：issue #5214

## 结论

T1 已完成，工作流侧按 **fast path** 执行；提交前的 G19 影响核对将改动定性为 **standard / file-linked**，没有升级到 complex/high。理由是生产修复只有一个默认字段初始化，影响面局限于 `Leaf` 构造不变量，且可由精确 RED/GREEN、相邻回归和全套件闭合；不需要三文件或 Role Reviewer。

instrumented 候选提交为 `965abad19646ab0a00d0051c23c25c3160972ce6`。bare 对照提交为 `3b6961072bda97854da05b4a4a1e5e9a3f7b8c3e`，只作为 patch/stat 归档，不推送。

## 基线与约束

- Black 基线：`8947c48ef2077c3a301b03c1e814dc2e3f78436e`。
- instrumented 父提交：`868d4ef`，包含已复验的 full overlay 与 T0；T1 自身是一条独立提交。
- 测试统一使用 `env -u NO_COLOR`。
- 补丁锁定前只读取 [issue #5214](https://github.com/psf/black/issues/5214) 及其评论；未读取 #5215/#5221 的 PR 页面、diff 或提交。
- 未推 psf/black、未建 PR、未留言。
- 源工作流仓始终保持 `fe560cd5`，未修改。

## 复现事实与 RED

issue 中维护者确认的输入在当前试验基线已经能完成 `black.format_str`；因此不能把当前 main 描述为仍然端到端崩溃。原因是基线中已有相邻 fmt-skip 修复改变了路径，但 `Leaf` 声明不变量仍然缺失。

instrumented 测试保留维护者确认输入中的 `ExtractorLoggingConfig` 形式，经 `black.lib2to3_parse` 枚举真实 leaves，并要求每个 `leaf.bracket_depth` 为整数；同时再运行 `format_str`。修复前精确 RED：

```text
AttributeError: 'Leaf' object has no attribute 'bracket_depth'
```

这证明被钉住的是 issue 的底层对象不变量，而不是制造一个已经不成立的端到端崩溃叙述。

## 修复与验证

生产修复仅在 `src/blib2to3/pytree.py::Leaf.__init__` 增加：

```python
self.bracket_depth = 0
```

验证结果：

- focused RED：1 failed / 166 deselected，错误为上述 `AttributeError`。
- focused GREEN：1 passed / 166 deselected。
- 相邻 `fmtskip_after_bracket_with_comment`：1 passed / 235 deselected。
- agent 全套件：482 passed / 3 skipped。
- root 独立全套件：482 passed / 3 skipped；13.31 秒（当时与 smoke 并行）。
- 含试验报告提交的候选 revision 全套件重复通过：482 passed / 3 skipped。
- root 独立 smoke：通过；6.03 秒。
- 修改文件 Black 格式检查：通过。
- `git diff --check`：通过。
- T1 commit diff：2 文件，+27/−0。
- 工作树：干净。

## 工作流侧执行数据

| 指标 | instrumented full overlay | bare 对照 |
|---|---:|---:|
| Codex turns | 4（3 次平台误拦截 + 1 次完成） | 2（设计确认 + 实施） |
| Codex wall time | 1097.53 s（18m17.53s） | 415.87 s（6m55.87s） |
| 已观测 input tokens | 1,288,191（仅完成 turn） | 2,071,721 |
| 已观测 cached input | 1,240,576 | 1,972,736 |
| 已观测 non-cached input | 47,615 | 98,985 |
| 已观测 output tokens | 14,310 | 16,302 |
| 已观测 reasoning output | 8,731 | 7,456 |
| cached input 比例 | 96.30% | 95.22% |
| 机械委派 | 0 | 0 |
| 三文件真实消费 | 无；仅存在 seed README | 无 overlay |
| guard/monitor 提醒或阻断 | 0 / 0 | 不适用 |
| T1 diff | 2 files, +27/−0 | 2 files, +25/−0 |
| 返工 | Git 身份 1 次；平台误拦截 3 turns | 设计批准多 1 turn；Black 格式 1 次；Git 身份 1 次 |

instrumented 的三个失败 turn 由运行服务的错误 cybersecurity 分类导致，JSONL 只记录失败，不发出 usage；因此 1,288,191 是**可核验下限，不是完整 token 总量**。两侧 token 不作总成本胜负结论。wall time 则完整计入失败 turn，不能从 instrumented 数字中剔除。

## bare 对照

bare 会话未看到 overlay、instrumented 分支或上游 PR。它独立得到同一生产修复，测试路径稍不同：

- 从维护者输入走 `parse → normalize_fmt_off`，筛选真实 `STANDALONE_COMMENT`；
- 断言生成叶 `bracket_depth == 0`；
- focused：2 passed；
- agent 与 root 独立 full：482 passed / 3 skipped；
- root 独立 full 用时 5.80 秒；
- 首次 Black check 要求三引号机械格式调整，调整后重跑 focused/full；
- 提交后工作树干净。

对照 patch 和统计随本报告归档；对照分支不推送。

## 补丁锁定后的上游比较

锁定本地补丁后才读取 [PR #5215](https://github.com/psf/black/pull/5215) 与 [PR #5221](https://github.com/psf/black/pull/5221)：

- 两个上游候选的生产修复均是给 `Leaf.__init__` 增加 `self.bracket_depth = 0`，与本地生产结论一致；初始化语句位置不同但语义相同。
- #5215 另加 CHANGES 条目和直接构造 `Leaf` 的较短单元测试，覆盖 `bracket_depth` 与 `opening_bracket` 默认值。
- #5221 只含生产一行，没有回归测试。
- instrumented 测试更贴近维护者输入与 parser 公共路径，但比 #5215 测试长；T1 任务卡未要求 CHANGES，因此本地未加 CHANGES。

## 真实机制观察

### 1. G20 linked-worktree 假阳性

instrumented 工作区是 linked worktree，`.git` 为指向 common git dir 的文件。overlay validator 的 `--require-local-exclude` 固定检查当前 root 下的 `.git/info/exclude`，因而报：

```text
local workflow overlay ignore patterns incomplete
```

实际 exclude 位于主 worktree 的 common git dir；随后用 `git check-ignore --no-index` 独立核对 17 类 overlay 路径，全部被正确忽略，普通 staged checker 也通过。这是一次可复现的验证器误报；未修改工作流绕过，应带回源仓裁决。

### 2. guard / monitor

- 编辑目标不是敏感路径，P1 无提醒或阻断。
- 无 review-only/plan-only/revoked 明确信号，P4 未激活。
- trajectory 状态最终 `event_seq=0`、两个 signal 的 `warnings=0`；没有同命令三连败或单文件五连编辑。
- 本任务未产生足以证明 P2 有效或误报的数据。

### 3. 三文件与分流

任务被自主判定为 bounded fast/file-linked；没有创建 active task 三文件，也没有读取三文件正文。这个行为与 fast-path 预期一致，不把“未使用三文件”误写成失败。

## 产物

- instrumented code commit：`965abad19646ab0a00d0051c23c25c3160972ce6`
- bare control commit：`3b6961072bda97854da05b4a4a1e5e9a3f7b8c3e`
- control patch：`trial-reports/t1-5214-control.patch`
- control stats：`trial-reports/t1-5214-control-stats.txt`
- 原始 JSONL/time/stderr 保留在仓外 `~/trials/black-run-1/reports/`，不提交。
