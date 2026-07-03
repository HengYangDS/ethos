# ETHOS 质量规范决策明晰 — 相对 di-effect 的吸收/拒绝矩阵

> 状态:决策 SSOT(工作记录,`.ethos/` ignored,非 tracked truth)。
> 依据:全面研究 `~/projects/di-effect`(3 并行 Explore agent,全部落实文件)+ ETHOS `system/tao.md`。
> 目的:用**严格准则**替代此前局部片面的门禁收紧。每条 di-effect 规范走五关判定。

---

## 0. 判断准则(五把尺 — 全过才吸收)

| 准则 | 判据 | ETHOS 依据 |
| --- | --- | --- |
| **C1 道对齐** | 服务某条 First Principle(尤 #2 失败前移 / #5 派生非存储 / #6 实体需独立义务 / #8 兼容残渣是成本) | tao.md First Principles |
| **C2 普适性** | 产品化通用规律,非 di-effect 领域特异(Result/Effect 代数、DI marker) | 用户核心要求 |
| **C3 净维护** | 降低**总维护成本**,非仅增本地严格度 | tao.md #7 |
| **C4 可机验** | 门禁机械强制,非靠自觉 | ETHOS 门禁哲学 |
| **C5 SSOT/DRY** | 单一真源,不制造平行实体 | Writing Standard: Elegant |

判定符号:✅吸收 · 🔧改造后吸收 · ❌拒绝 · ⏸️暂缓(需更大重构/授权)

---

## 1. 配置与政策组织

### 1.1 config/policy 两层分离 — ✅ 吸收
- **di-effect**:`.config/lint/<domain>/` = 工具配置(HOW);`rules/lint/` = 政策 SSOT(WHAT/WHY,含 module_layout.schema.json、debt policy)。
- **五关**:C1✅(#6 各层独立义务)C2✅(通用)C3✅(改配置不碰政策,反之亦然)C4✅ C5✅(单一真源)。
- **ETHOS 现状**:`.config/checks/<tool>/` 只有工具配置;政策散在 `.ethos/rules.toml` + `system/tools.toml`。**缺口**:政策未成独立 SSOT 层。
- **落地**:确立三层——`.config/checks/<tool>/`(工具 HOW)+ `system/tools.toml`(WHY/治理注册)+ `.ethos/rules.toml`(政策阈值 WHAT)。已部分到位,补齐语义边界文档。

### 1.2 每政策文件带 `.meta.toml` 侧车(owner/doc_type/schema_ref) — 🔧 改造后吸收
- **五关**:C1✅ C2✅ C3⚠️(侧车增维护)C4✅ C5✅。
- **判断**:ETHOS 用 `system/tools.toml` 已承担 owner/why 登记,无需每文件侧车(否则违 C3 净维护 + C5 制造平行登记)。**改造**:元数据集中在 `system/tools.toml`,不散成侧车。

### 1.3 生成物与源分离(Source/Generated/Consumer 三态) — ✅ 吸收(已有)
- ETHOS `.ethos/rules.toml [artifacts] generated_outputs_tracked_truth = false` 已表达此道。对齐 di-effect `.config/README.md` 层模型。**无动作**。

---

## 2. 债务政策:ratchet 机制

### 2.1 budget-ratchet(数值预算,单调收缩)替代 per-line 抑制 — ✅ 吸收(修正我的实现)
- **di-effect**:`lint_gates.toml` 里 per-rule + per-path 数值预算(如 `SLF001 max=1286`、`core max=261`),只能降;**"Retired baselines = zero grandfathered debt"**,禁止 recreate baseline 文件、禁止 per-line 抑制骗过门禁。
- **五关**:C1✅(#2 失败前移 + #8 残渣是成本)C2✅ C3✅(债务量化在一处,非撒 `# noqa`)C4✅ C5✅。
- **ETHOS 现状 = 反模式**:我用了 `# nosec B608`(per-line 抑制)+ `.ethos/rules.toml` 里 per-file `effective_max_lines` 例外——**这正是 di-effect 退休的 grandfathering**。但我的 LOC ratchet「只降不升」的**精神**与 budget-ratchet 一致。
- **落地**:
  1. 把 per-file LOC 例外从「per-file 白名单」重构为「per-path 数值预算 + 全局趋零目标」(精神已对,形式对齐)。
  2. `# nosec` 尽量消除(已在 state.py 用白名单加固替代大部分);残留的移入「治理机器政策」而非 per-line。
  3. 确立原则文档:**禁止 recreate 抑制文件骗门禁;只能修诊断、收紧规则、或把例外移入 owning 政策**。

### 2.2 "advisory" vs "ignored-advisory" 双预算 — 🔧 改造后吸收
- di-effect 分两类:想采纳但未 select 的规则(advisory,趋零)+ 已 ignore 但追踪不增长的规则(ignored-advisory)。
- **判断**:概念优秀(区分「在采纳路上」与「已放弃但盯住」),但 ETHOS 规模小,**改造**为单一「趋零预算表」即可,双表暂过度(C3)。

---

## 3. 模块布局(你点名的重点)

### 3.1 role-based 尺寸分级 + split-by-surface 触发器 — ✅ 吸收(推翻我的 flat-400)
- **di-effect**:`module_layout.schema.json` 按 context 分级(逻辑 600/900、入口 800/1200、**cli_aggregator 2600/3200**、checker 1800/2200、测试 800/1200);切分触发器 = **公开类 >2、公开函数 >8、平铺兄弟 ≥8 → 强制子包**。soft/hard 双阈,soft 也是 error。
- **五关**:C1✅(#2 失败前移,#6 表面积=义务边界)C2✅(通用软件工程律)C3✅(按角色而非一刀切,减少无谓拆分)C4✅(schema 机验)C5✅。
- **我的错误**:flat「每文件 ≤400」把命令聚合器和逻辑模块同等对待。命令聚合器本应是「大而薄的接线表」,真正该小的是**逻辑模块**,真正的触发器是**公开表面积**不是裸行数。
- **落地(决策:role-based 分级 + 全局 hard 上限兜底)**:
  - `.ethos/rules.toml [quality.code_size]` 从单一 `default 400` 升级为分角色:
    - `surface`(命令面/aggregator):soft 800(单文件命令组目标)
    - `logic`(domain/adapters/kernel 逻辑):soft 400 / hard 600
    - `test`:soft 800 / hard 1200
    - **全局 hard 兜底 1200**(用户定,非 1400):任何文件不得超,防止 aggregator 借口无限膨胀;已有 ratchet 例外(tracked shrinking debt)可暂超,只降不升直到消解。
  - 有效行 = 纯代码行,AST 排除空行/整行与行内注释/docstring/裸字符串语句(kernel SSOT `ethos_core.measure`,已验证)。
  - 新增 split 触发器:单模块公开函数 >10 或公开类 >2 → 需拆(ETHOS 放宽 di-effect 的 8,因命令组);目录平铺 ≥8 → 子包。
  - **cli.py 重判**:它是 surface aggregator,目标不是 400,而是「命令体全下沉 domain 后自然收敛 + 公开命令函数按组拆到 surface/cli/<group>.py 各 ≤ soft 800」。当前 2985(tracked 例外)→ 分组后每文件自然 <800 < 1200 ceiling。

### 3.2 强制 section 顺序(# ==== 分区)+ AST 检查器 — ⏸️ 暂缓
- **五关**:C1✅ C2⚠️(可读性通用,但顺序细节 di-effect 特异)C3❌(需移植 ~70 文件的 bespoke AST 检查器,违净维护)C4✅ C5✅。
- **判断**:价值高但**移植成本极高**(C3 失分)。**暂缓**——ETHOS 可先靠 ruff 的 import 分组 + 人工 section 注释,不引入自建 layout 检查器引擎。未来若 ethos-quality 有余力再评估。

### 3.3 module 名字形状限制(≤42 char,≤5 token,role-suffix 词表,禁 `<concept>_<role>` 平铺) — ✅ 吸收
- 与你早先的纠偏**完全一致**(「不能靠后缀平铺,要语义子包」)。
- **五关**:C1✅(#6)C2✅ C3✅ C4🔧(需检查器或 ruff 插件;可先文档约定 + review)C5✅。
- **落地**:写入政策文档;机验用简单脚本门禁(检测 `_report.py`/`_native.py` 类平铺后缀 + 名长),不需全 AST 引擎。

---

## 4. 公开/私有 API

### 4.1 空 `__init__.py` + 禁 `__all__` + 无 re-export barrel — 🔧 改造后吸收(部分)
- **di-effect**:924/924 空 `__init__`,`__all__` 全仓禁止,可见性靠 underscore 命名 + section placement + `public_api_registry.toml`。导入具体子模块,永不过包根。
- **五关**:C1✅(#8 兼容残渣、#6)C2⚠️(激进;多数产品用 `__all__` 是正当的)C3⚠️(禁 barrel 减少 re-export churn,但强制调用方导入深路径增加冗长)C4🔧 C5✅。
- **判断**:di-effect 走极端(连 registry 都要)。ETHOS **改造吸收其精神**:
  - ✅ 采纳:不加 re-export shell/alias shim/compatibility wrapper(与 tao #8 一致);`__init__.py` 保持薄。
  - ❌ 不采纳:全仓禁 `__all__` + 强制 registry(对 ETHOS 过重,违 C2 普适性——`__all__` 是 Python 正当公共 API 声明)。
  - **落地**:政策写明「禁止 forwarding shell / alias 别名(`from x import y as main`)/ `retired_*` 包装」;`__all__` 允许但须真实反映公开面。

### 4.2 canonical 符号名是契约(禁重命名别名) — ✅ 吸收
- **五关**:全过。与 tao「删除平行实体」直通。**落地**:政策明文禁 `import y as pmap` 式语义重命名。

### 4.3 import 具体子模块、绝对导入、`force-single-line` — ✅ 吸收
- **五关**:C1✅ C2✅(通用清洁)C3✅(grep/diff 更清晰)C4✅(ruff isort 配置即可,零移植成本)C5✅。
- **落地**:`.config/checks/ruff/ruff.toml` 加 `[lint.isort] force-single-line = true` + `known-first-party` 全 ethos 包;确保 `TID`(已在 select)守绝对导入。**低风险高价值,立即落地候选**。

---

## 5. Ruff 规则姿态

### 5.1 maximalist-select(57 族)+ 外科式 ignore + inline WHY — ✅ 吸收
- **di-effect**:select 57 族,ignore 13 项每项(非显然者)带 WHY 注释,preview 规则显式 opt-in。
- **ETHOS 现状**:~19 族。**缺口大**。
- **五关**:C1✅(#2 更多失败前移)C2✅ C3⚠️(更多规则 = 更多修复,但一次性)C4✅ C5✅。
- **落地(分批,ratchet)**:向 57 族靠拢,每次加一批规则 + 修 + inline WHY。优先补:`ANN`(注解完整)、`D`+`DOC`(docstring)、`TRY`、`FBT`(布尔陷阱)、`SLF`(私有访问)、`PL`(pylint 族)、`S`(bandit 重叠可选)、`ARG`、`ERA`、`PGH`、`FURB`。ETHOS 已有 C90 复杂度。

### 5.2 复杂度多维限制(max-args/branches/returns/statements) — ✅ 吸收
- di-effect:`max-complexity=10, max-args=10, max-branches=15, max-returns=8, max-statements=60`。ETHOS 只有 `max-complexity=12`。
- **落地**:加 pylint 子表四项;complexity 12→10 收紧(ratchet)。

### 5.3 single-quote + LF + docstring-code-format — ✅ 吸收(格式 SSOT)
- **落地**:ruff format 配 `quote-style=single`(若与现状冲突则评估),`line-ending=lf`,`docstring-code-format=true`。

### 5.4 cross-tool format SSOT(format-style.toml + [principles] 层) — ⏸️ 暂缓
- 价值高(一处定义换行/列宽/列表风格,校验所有 formatter),但 ETHOS 当前 formatter 少(主要 ruff),**暂缓**至引入 markdown/yaml/toml formatter 时再建。

---

## 6. 类型系统

### 6.1 mypy/ty 姿态:注解 presence 靠 ruff ANN,类型 correctness 靠 checker — 🔧 改造后吸收
- **di-effect**:mypy **故意非严格**(16 codes disabled,所有 disallow_* off)+ ty 补充;注解**存在性**靠 ruff `ANN`。
- **ETHOS 现状**:用 ty,3 纯净包零容忍 + 其余 ratchet。
- **五关**:C1✅ C2✅ C3✅ C4✅ C5✅。
- **判断**:ETHOS 的「纯净包零容忍 + ratchet」比 di-effect 的「全局宽松」**更进取且更合道**(#2 失败前移)。**保留 ETHOS 现状**,仅**补** ruff `ANN` 族保证注解存在性(与 6.1 上半对齐)。这是 ETHOS 优于 di-effect 之处,不倒退。

### 6.2 PEP695 原生泛型(`class Foo[T]`)优先于 `from __future__ import annotations` — ❌ 拒绝(领域特异 + 违普适稳妥)
- **五关**:C2⚠️(需 py312+ 硬地板)C3❌(ETHOS 现用 `from __future__ import annotations` 遍布;强制迁移 PEP695 是大改无净收益)。
- **判断**:di-effect 有 py3.12 硬地板 + 类型密集代数库背景。ETHOS 无此需。**拒绝**——保持 `from __future__ import annotations` 惯例(已一致)。

### 6.3 集中式 TypeVar 所有权(types.py 单一 owner) — 🔧 部分吸收
- ETHOS 已有 `ethos_core`(measure 等 SSOT)。若未来引入共享 TypeVar,**采纳**集中所有权原则;当前无密集泛型,**不强制建 types.py**。

### 6.4 attrs.frozen+slots 强制、禁 dataclass — ❌ 拒绝(领域特异)
- **五关**:C2❌(di-effect 因 Result/Effect 代数需 frozen 值对象 + 性能;ETHOS 是治理 CLI,dict/dataclass 足够)C3❌(引入 attrs 依赖 + 迁移成本无净收益)。
- **判断**:纯 di-effect 领域选择。**拒绝**。

### 6.5 Result[E,T] 双通道错误政策 — ❌ 拒绝(领域特异)
- **五关**:C2❌(这是 di-effect 的**产品本身**——DI/Effect 框架的核心代数;ETHOS 是治理产品,用 EthosResult + 异常已足)。
- **判断**:ETHOS 已有 `ethos_core.result.EthosResult`,语义足够。引入 Result 代数是把别人的产品搬进来。**拒绝**。

---

## 7. 文档规范

### 7.1 module docstring 三元组(Responsibility/Usage/Boundary) — ✅ 吸收
- **di-effect**:2096 文件每个带此三元组。表达「单一职责 + 用法 + 边界」。
- **五关**:C1✅(#6 每模块单一义务,可读可恢复意图 = Writing Standard Expressive)C2✅ C3✅(轻量约定)C4🔧(docstr-coverage 可验)C5✅。
- **落地**:政策约定新模块带三元组;ETHOS 新建的 domain/adapters 模块已有职责 docstring,补齐 Usage/Boundary 格式。

### 7.2 Google docstring + 4 工具链(ruff D/DOC + pydoclint + docformatter + docstr-coverage) — 🔧 改造后吸收
- **五关**:C1✅ C2✅ C3⚠️(4 工具 = 4 依赖;ETHOS 可先用 ruff D/DOC 覆盖 80%)C4✅ C5⚠️(一域一工具原则下,ruff 已是 lint owner)。
- **落地**:先加 ruff `D`(convention=google)+ `DOC` 族(已在 5.1 批次)。pydoclint/docformatter/docstr-coverage **暂缓**,按需再加(遵一域一 blocking 工具,先让 ruff 承担)。

### 7.3 docstring coverage 门禁(95%/98% 两级) — ⏸️ 暂缓
- 价值明确但需 docstr-coverage 工具 + 达标工作量。**暂缓**至 ruff `D` 落地稳定后评估。

---

## 8. 测试规范

### 8.1 tests 顶层集中 + 镜像包名 — ⏸️ 暂缓(需单独判断)
- **di-effect**:1325 测试全在顶层 `tests/`,镜像包名,`check_test_layout` 门禁。
- **ETHOS 现状**:测试在 lane 顶层 `tests/`(已类似),但 pytest 用 lane pyproject pythonpath。
- **五关**:C1✅ C2✅ C3⚠️ C4🔧。**判断**:ETHOS 已基本是顶层 tests,**大体已对齐**;不需大动。仅在 8→2 包合并(Phase F)时一并规整。**暂缓并入 Phase F**。

### 8.2 --strict-markers + 标记体系 + 零 skip 规则 — ✅ 吸收
- **五关**:C1✅(#4 可检查性)C2✅ C3✅ C4✅ C5✅。
- **落地**:pytest 配 `--strict-markers` + 声明 marker;采纳「deselect 而非 skip」原则(默认矩阵零 skip)。低风险,立即候选。

### 8.3 coverage 95%/branch 90%(但 hosted 非门禁,await dedicated lane) — 🔧 改造后吸收
- **判断**:采纳目标值,但如 di-effect **不急于设为硬门禁**(它自己都 `--no-cov-fail`)。ETHOS 先测量报告,不阻断。**改造**:coverage 作为 informational 指标,不设 fail_under 硬门直到有专门 lane。

### 8.4 di-effect-test 提供 fixtures/law-checks — ❌ 拒绝(领域特异)
- law-checks(functor/monad 律)是 di-effect 代数产品特有。ETHOS `ethos-test` 已存在承担自己的测试工具。**拒绝** law-checks。

---

## 9. CI / 流程

### 9.1 一域一 blocking 工具(ruff 独占 lint+format,不重引 black/isort/flake8/pylint) — ✅ 吸收
- **五关**:C1✅(#7 减总维护)C2✅ C3✅ C5✅(单一 owner = SSOT)。
- **ETHOS 现状**:已是 ruff 独占。**对齐,明文化政策**。

### 9.2 两级 strict(enforced-now 门 + *-strict.toml warn-only 审计 lane) — ✅ 吸收
- **di-effect**:`ruff-strict.toml` 等 warn-only 在 scheduled/full lane,「现在强制 / 审计趋向」两级。
- **五关**:C1✅(#2 渐进前移)C2✅ C3✅(平滑收紧不破坏)C4✅ C5✅。
- **落地**:建 `.config/checks/ruff/ruff-strict.toml`(extend 主配 + 更严 select),作为 warn-only 审计层,达标后升入主门。这给「持续拔高门槛」一个**结构化机制**而非临时加规则。

### 9.3 分模式调度(local/fast/full/scheduled;bandit/pip-audit 仅 scheduled) — 🔧 改造后吸收
- **五关**:C1✅ C2✅ C3✅ C4✅。
- **落地**:ETHOS `ethos prove` 可分 fast/full;重工具(bandit 全扫)可标 scheduled。**改造**:纳入 ethos-quality gate 的 execution_mode 分级(已有 gate descriptor 基础)。

### 9.4 quality-tooling inventory(自动生成工具姿态清单,coverage_max_uncovered=0) — ✅ 吸收
- **五关**:C1✅(#4 生成面可检 drift)C2✅ C3✅ C4✅ C5✅。
- **落地**:`ethos quality` 生成门禁清单 artifact(哪些规则/族/例外),每门必登记。ETHOS 已有 gate registry,补生成投影。

---

## 10. 决策汇总表

| # | 规范 | 判定 | 优先级 |
| --- | --- | --- | --- |
| 1.1 | config/policy 两层分离 | ✅ | 高 |
| 1.2 | .meta.toml 侧车 | 🔧集中到 tools.toml | 低 |
| 2.1 | budget-ratchet 替代 per-line 抑制 | ✅ 修正实现 | 高 |
| 3.1 | role-based 尺寸+split 触发器 | ✅ 推翻 flat-400 | **最高** |
| 3.2 | 强制 section + AST 检查器 | ⏸️暂缓 | — |
| 3.3 | module 名字形状(禁后缀平铺) | ✅ | 中 |
| 4.1 | 空 __init__/禁 __all__/无 barrel | 🔧部分(禁 shell,留 __all__) | 中 |
| 4.3 | force-single-line + 绝对导入 | ✅ | **高(低风险)** |
| 5.1 | maximalist ruff select + WHY | ✅ 分批 | 高 |
| 5.2 | 复杂度多维限制 | ✅ | 中 |
| 6.1 | 注解 presence 靠 ANN | ✅补 ANN,保留 ty 现状 | 中 |
| 6.2 | PEP695 泛型 | ❌ | — |
| 6.4 | attrs.frozen 禁 dataclass | ❌ | — |
| 6.5 | Result[E,T] 双通道 | ❌ | — |
| 7.1 | module docstring 三元组 | ✅ | 中 |
| 7.2 | Google docstring + 4 工具 | 🔧先 ruff D/DOC | 中 |
| 8.2 | strict-markers + 零 skip | ✅ | 中(低风险) |
| 9.1 | 一域一 blocking 工具 | ✅已对齐 | — |
| 9.2 | 两级 strict lane | ✅ | 高 |
| 9.4 | quality inventory 生成 | ✅ | 中 |

**拒绝的(领域特异)**:PEP695 强制、attrs 强制、Result 代数、law-checks、全仓禁 __all__+registry。
**暂缓的(成本/需更大重构)**:AST layout 检查器、format-style SSOT、docstring coverage 门禁、tests 集中(并入 Phase F)。

---

## 11. 立即落地批次(低风险高价值,本会话可做)

按「先想好章法、再落地」+ ratchet:

1. **4.3 force-single-line + 绝对导入**(ruff isort 配置,零移植)
2. **3.1 role-based 尺寸分级**(改 `.ethos/rules.toml [quality.code_size]`,推翻 flat-400 — 这是最高价值)
3. **9.2 两级 strict lane**(建 ruff-strict.toml warn-only,给「持续拔高」结构化机制)
4. **8.2 strict-markers**(pytest 配置)
5. **本决策文档本身**(替代局部片面,成为质量演进 SSOT)

后续批次(需多轮 ratchet):5.1 ruff 扩族、5.2 复杂度、7.1 docstring 三元组、9.4 inventory。
需授权的破坏性:4.1 __init__ 规整、Phase F 包合并 + tests 规整。

---

## 12. 实体压缩 + 性能优化(2026-07-03,已 profile,基于道)

用户问:能否进一步压缩实体 + 性能优化。两者被同一个动作统一。

### 实体压缩(FP#6 新实体需独立义务)
- **Decision 合同已存在** = `EthosResult`(ok/state/diagnostics/next_actions/required_gaps)。专家委员会建议的 {verdict,why,next,required_gaps} 与之同构 → **合并不新增**;verdict 语义由 system/evidence_boundaries.toml 定义。
- **kernel Change/Commitment dataclass "定义未构造"** → 要么 binding(真构造),要么它们只是 spec 不该占 models 实体位。待判。
- **cli.py 薄 wrapper** → 命令体直调 _gitio/_status/_land,消中间层(进行中)。
- **8→2 包合并** = 最大实体压缩(8 部署单元→2),破坏性,独立 lane。

### 性能优化(FP#7 只在降总维护时做;已测量非臆测)
实测:`import ethos.cli` 383ms 累计,`ethos status` 端到端 53ms。热点:
- eager import 100+ 符号:跑任何命令都加载 audit(187ms)+schema(190ms)+jsonschema(125ms),即使 status 用不到。
- status 最小依赖仅 22ms,却被拖入 46ms+ 无关加载。
**结论:lazy import 是真实可测的 ~2x 常用路径提速。** 但正确形式 = 命令组拆到 surface/cli/<group>.py(每组只 import 自己依赖),而非在 75 个命令体里散插 import(那是残渣 FP#8)。

### 统一洞察
**命令组拆分同时兑现:实体压缩(surface 分文件)+ 性能(per-group lazy import)+ cli.py 收敛(→ 薄路由)。** 这是 surface 拆分的三重收益,是收敛的下一主线(多会话工程,单会话可逐组推进)。
