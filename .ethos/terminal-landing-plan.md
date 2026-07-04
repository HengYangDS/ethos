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

**eff-LOC 巨石(AST 排 docstring):** cli.py 3224 / rules.py 1082 / context_index.py 965 / schema_validation.py 762 / openspec.py 688 / planner.py 671 / shadow.py 646 / coupling.py 637 / parity.py 549 / lanes.py 509 / docs_registry.py 496 / status.py 410。62 文件,16219 总 eff-LOC。

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

---

## 执行进展(2026-07,work/terminal-substrate,21 commit)

### 已落地门禁体系(6 道内生门,全 ratchet 制,配置分层 .config/checks/)
- ruff 19 规则集 + C90 圈复杂度≤12(新代码零容忍,9 函数 ratchet)
- ty 类型检查(core/quality/contracts 三纯净包零容忍;adapters/repository/ethos ratchet 基线)
- import-linter 架构门(3 契约 KEPT:core/contracts 纯叶子 + 全分层无环)
- bandit 安全门(High/Med=0,SQL 白名单加固,src assert 债务已消除)
- LOC 硬规则 400(AST 精确排 docstring,forcing function)+ measure SSOT 提升到 ethos_core
- pytest(507 绿,5 pre-existing 是 parity treadmill)
- 全部注册为 ethos_quality QualityGateDescriptor(内生于 prove 路径)

### cli.py 拆分进展(建立了 surface→domain→adapters→kernel 分层)
- ethos/adapters/git.py(git IO 原语)、config.py(rules.toml loader)
- ethos/domain/prove.py(code_size_report reducer)、status.py(纯 reducer)
- cli.py 3224 → 3143 eff-LOC(git/config/status 组已抽)

## 真实收敛路径(关键洞察 — cli.py 大头是命令体不是 helper)

cli.py 3143→400 需移出 ~2743 行。**大头是 75 个命令体,不是 44 个 helper。**
真正的"薄命令面"收敛 = 命令体业务逻辑下沉到 domain,命令只留 `bind-args → 一次 domain 调用 → _emit(json)`。

**剩余最大块(批量抽取目标,按 workflow 施工图):**
- _rule_attestation_for_evaluation(近千行,→ domain/land 规则证明)
- _campaign_closeout_report 538 + _closeout_bootstrap_package 417(→ domain/land 闭环)
- _run_inprocess_cli_gate 177 + _rule_fact_snapshot 145(→ domain/prove、domain/plan)
- audit 组(_product_repository_audit/_adopter_audit → domain/status + adapters)

**方法纪律(每步):** 逻辑移 domain/adapters,删 cli.py wrapper 并改调用点(不留委托壳,才真瘦身),每步 AST 达标 + import-linter KEPT + 零回归才提交,ratchet 逐步下调。

## 收敛机制(让门禁驱动,不依赖单会话手工)

LOC 硬规则的 ratchet 是收敛的 forcing function:cli.py 例外只能下调,永不上调。
每次抽取后 ratchet 下调锁定进展。这保证收敛单调、不回退,可跨会话持续。

---

## cli.py 收敛剧本(可无思考续跑 — 2026-07 更新,cli.py=3048)

**已完成的分层地基:** surface/cli/_base.py(app对象+resolve_root+emit+类型别名共享面)、
domain/{status,plan,prove}、adapters/{git,config}。25 commit,cli.py 3224→3048。

**关键认知:cli.py 的 helper 是密集耦合簇**(rule-fact→audit→status→git),必须**成簇下沉**,
不能单个搬(单搬会 NameError 或循环 import)。剩余最大簇:
- **rule-fact 簇**(~195行):_rule_fact_snapshot(145,依赖 _audit_for_root/_status_worktree_gaps/
  _rule_fact/_unavailable_rule_fact)+ _rule_attestation_for_evaluation(25)→ domain/plan
- **audit-status 簇**(~53行):_audit_for_root/_product_repository_audit/_adopter_audit/
  _is_product_root/_status_worktree_gaps → domain/status(注意 _adopter_audit 32行做IO,拆 adapters)
- **closeout 簇**:_campaign_closeout_report(104)+_trust_closeout_package(65)+
  _closeout_bootstrap_package(31)+_local_submit_package/_publication_readiness → domain/land
- **命令组搬 surface/cli/<group>.py**(依赖簇下沉后才干净):quality(29命令/964行,最大)、
  lane(7)、rules(6)、assistants(9)、campaign/parity(各3)... 各从 _base import app+helper。

**每簇/每组的机械步骤(严格照做,每步全绿才提交):**
1. 读簇内所有函数完整代码 + 它们的外部依赖(domain/adapters/kernel 符号)
2. 建/追加目标 domain 模块,函数改用 adapters/kernel 的公开名(非 cli 的 _wrapper)
3. cli.py 删原函数,调用点改指向新模块(或留最小委托,但优先删+改调用点)
4. `python -c import ethos.cli` (lane PYTHONPATH) 验证无 NameError/循环
5. `ruff check --fix packages/` — 修 TC002/I001/unused(每次搬完必触发,是常态不是错误)
6. 重算 cli.py eff-LOC,**下调** .ethos/rules.toml 的 cli.py ratchet 到新值
7. `pytest tests -q` 必须是 5 pre-existing(parity treadmill),`lint-imports --config
   .config/checks/import-linter/contracts.ini` 必须 3 kept,才 commit
8. 每簇一个 commit,ratchet 单调下降保证收敛不可逆

**终点判据:** cli.py ≤ 400 eff-LOC(纯 surface:每命令=bind-args→一次domain调用→emit);
或按需拆成 surface/cli/<group>.py 多文件各≤400。届时删除 cli.py 的 code_size ratchet 例外。

**pre-existing 5 红(非回归,勿追):** parity treadmill(evidence绑会话初HEAD 25b5be2)+
report_scorecard/campaign_closeout/governance_lifecycle(同源)+ rules test_valid_policy_exception
(order-dependent)。用 `--deselect` 这5个 = 507/0 全绿。
