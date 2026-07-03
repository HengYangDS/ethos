# 终态落地计划 — MECE 语义子包 + 部署边界 + LOC 硬规则

> 状态:工作记录(ignored,非 tracked truth)。分类器恢复后照此连续执行。
> 依据:用户两层边界原则 + 实测依赖图 + 实测 eff-LOC + 设计 workflow(wncl3szzw)。

## 0. 两层边界原则(用户纠偏,不可混淆)

- **包边界 = 部署单元 + 依赖方向**(少而真、无环)。包有版本/发布/CI 成本;纯内核=真包,依赖一切的垃圾场≠真边界。
- **模块边界 = 语义轴 MECE**(多而清、包内、近零成本)。沿五层内核(Tao/Contract/Method/Instrumentation/Proof),SSOT+DRY,禁后缀平铺。

## 1. 实测依据(已用 AST/grep 测得)

**依赖图(部署边界证据):**
- `ethos-core → []` 零依赖纯叶子(真内核)。仅被引用 5 次 → 大量内核语义泄漏在别处。
- `ethos-contracts → []` 也是零依赖纯叶子。
- `ethos-repository → [几乎所有]` 5193 LOC = 历史垃圾场,非内聚部署单元 → 应解散,内容按语义归位。
- `ethos → [所有]` 产品根。

**eff-LOC 巨石(AST 排 docstring):** cli.py 3224 / rules.py 1082 / context_index.py 965 / schema_validation.py 762 / openspec_native.py 688 / planner.py 671 / shadow.py 646 / coupling.py 637 / parity.py 549 / lanes.py 509 / docs_registry.py 496 / status.py 410。62 文件,16219 总 eff-LOC。

## 2. LOC 硬规则(落地地基 — 优先做,防腐化免疫系统)

**已完成(待验证):** `_effective_code_lines` 升级为 AST 精确排除 docstring(+ `import ast`)。

**待做:硬规则升级(软例外 → 硬阻断 forcing function):**
- 阈值:待定(300/400/500,依设计 workflow + 拆分后实际分布)。倾向 **400**(逼单一职责,不过碎)。
- forcing 机制:E2 的 code-size gate 从"exception 软清单"→ **pre-commit hook + prove gate 双重硬阻断**:新文件超阈值直接 land 不了。
- 例外清单:只保留"拆分进行中"的临时豁免,每个带 shrink 目标记入 evolution/ledger,不是永久。
- eff-LOC 定义:AST 排除空行 + `#`注释 + module/class/func docstring 跨行。

## 3. 包集(部署边界 — 待设计 workflow 确认,倾向)

倾向 **3 包**(比终态 8→2 多一个 test,因 test 是 dev-only 不进产品依赖链):
- `ethos-core` — 纯语义内核(零 IO/subprocess/CLI),可被独立嵌入依赖。吸收现散在 repository 的内核语义(rules 引擎、profile、action-graph)。
- `ethos` — 产品 runtime(cli 薄面 / mcp / adapters / lifecycle 编排)。
- `ethos-test` — 仅开发期,conformance/parity/fixtures,不进产品依赖。
- 待定:contracts 是否折叠进 core(若总是与 core 共部署则折叠;若被独立依赖则留 4 包)。

## 4. 包内 MECE 语义树(语义轴 — 待 workflow 细化)

沿五层内核,例:
```
ethos-core/
  contract/   schema, rule-contract, profile, protocol
  method/     workflow, guard, rule-evaluator, action-graph
  proof/      evidence, claim, chronicle, attestation
ethos/
  surface/    cli(薄命令面,委托), mcp
  adapter/    git, subprocess, openspec, shadow, status
  lifecycle/  status/plan/prove/land/publish 编排
```
cli.py 3224 → 薄命令面,75 命令委托进 lifecycle/adapter 模块;逻辑不在 cli.py 里。

## 5. 垃圾场解散(ethos-repository 5193 → 按语义归位)

rules.py→core/method;schema_validation→core/contract;parity/shadow/coupling→ethos/adapter 或 core/proof;planner→ethos/lifecycle;docs_registry→ethos/adapter。每块搬迁独立 commit + 测试零回归。

## 6. 8→2 迭代判断(待 workflow 诚实结论)

终态"8→2"的神=拆垃圾场+归位,非"数字2"。若部署现实支持 3 包(+test)或 4 包(+contracts),则**迭代终态设计**,写明为何更尊重部署现实。core+contracts 是真叶子这一实测,已支持"至少 core 独立"。

## 7. 执行顺序(低风险,保 8 phase 全绿)

1. **LOC 硬规则 forcing function**(地基,与结构无关,先做)
2. **拆 cli.py 巨石** → 薄命令面 + lifecycle/adapter 模块(最大巨石,单独验证方法)
3. **解散 repository 垃圾场** → 内容按语义归位(逐块搬,每块零回归)
4. **包集重整**(core/product/test)→ 更新 pyproject workspace 依赖
5. 每步:AST eff-LOC 达标 + pytest 零回归 + ruff 净 才提交

## 关键纪律
- 每步 stash-diff 证明零回归才提交;精确字符串 Edit(非 fuzzy);退休/大改前 tag 备份。
- pytest 用 lane pythonpath(测 lane 代码);不用 ethos CLI 二进制验证(指向主仓库)。
- parity treadmill 的 4-6 红是 pre-existing(evidence 绑会话初 HEAD 25b5be2),非回归。
