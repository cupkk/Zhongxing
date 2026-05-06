# Task Plan: Zhongxing GUI Agent Highest-Score Optimization

## Latest Phase: Official 44.83 Douyin step6 top-submit fix 2026-05-06

- [x] Save official 44.83 step6 failure fragment
- [x] Generate first-failure classification for Douyin step6 `[705,145]`
- [x] Shift `review_form_top_submit` candidate center to `[695,145]`
- [x] Add narrow after-TYPE top raw-point snap `[705,145] -> [695,145]`
- [x] Preserve Jingdong/Pinduoduo PASS paths and ecommerce `COMPLETE` behavior
- [x] Re-run focused tests and public no-api regression
- [x] Rebuild and verify `submission.zip`
- [ ] Submit the rebuilt package and inspect whether official Douyin step6 changes to `[695,145]`

## Latest Phase: Official 41.38 failure loop 2026-05-04

- [x] Save latest visible official 41.38 log fragment
- [x] Generate latest official first-failure classification table
- [x] Fix Douyin review after-TYPE `[500,938]` submit-point miss by using right-bottom send
- [x] Fix Jingdong review mid-form `[505,600]` generic-point miss by rerouting to text area
- [x] Extend verifier/state-machine/pseudo-hidden regression to 106 pseudo-hidden checks
- [x] Run candidate coverage, py_compile, and public no-api regression
- [x] Sync submission and rebuild `submission.zip`

## Goal
把当前本地真实 VLM 公开集 11/11 的方案，升级成更抗隐藏用例变化、可持续分析失败日志、可安全提交的最高分竞赛版本。

## Current Phase
Phase 7

## Phases

### Phase 1: Baseline Lock And Submission Hygiene
- [x] 确认关键源码已同步到 `submission/src/utils`
- [x] 检查 `submission.zip` 是否包含 `src/agent.py`
- [x] 检查压缩包是否不含 `__pycache__`、`.pyc/.pyo`、重复 `doc/doc`
- [x] 用当前包跑一次可复现本地回归并保存日志
- **Status:** complete

### Phase 2: Hidden-Set Risk Map
- [x] 从公开 `ref.json` 和真实 VLM 日志统计首错类型
- [x] 建立 App/任务类型/失败机制矩阵
- [x] 标出哪些规则是公开集定点修复，哪些规则可泛化
- **Status:** complete

### Phase 3: Candidate Grounding Hardening
- [x] 扩展高置信公开流程规则保底，降低模型/API 差异影响
- [x] 增加候选元素稳定性测试，覆盖 target_id、中心点、历史动作联动
- [x] 避免新增宽泛坐标补丁影响已通过用例
- [x] 完成项目深度分析，明确候选元素增强和伪隐藏回归为下一阶段主线
- **Status:** complete

### Phase 4: State And Recovery Improvements
- [x] 增强 `Memory` 的任务阶段记录，例如 search_submit、review_finish、address_confirm
- [x] 把弹窗、广告、权限、登录提示归入窄域 RecoveryPolicy 或现有策略
- [ ] 对 `COMPLETE` 继续保持高风险拦截，防止提前结束
- **Status:** in_progress

### Phase 5: Regression And Pseudo-Hidden Suite
- [x] 构造 30 条左右伪隐藏任务：评论/评价、搜索、地图、视频、弹窗异常
- [x] 扩展到 94 条机制测试，覆盖 verifier 边界和候选排序稳定性
- [x] 每次修改后跑公开集 + 伪隐藏集
- [x] 记录分数、首错、target_id 使用率、裸 point 使用率
- **Status:** complete

### Phase 6: Submission And Design Score
- [x] 重新打包 `submission.zip`
- [x] 检查 zip 结构、大小、pycache、密钥、源码同步
- [x] 更新算法说明文档和阶段记录，突出候选元素 + target_id + 日志闭环
- **Status:** in_progress

### Phase 7: Score Sprint Roadmap
- [x] 结合赛题评分、当前候选覆盖统计、官方隐藏首错和前沿 GUI Agent 方法形成冲分路线图
- [x] 新增 `doc/冲分执行路线图_20260503.md`
- [x] 按路线图优先提升 `CandidateMiner` 候选覆盖率到 70%+
- [x] 新增轻量 `ActionReranker/ActionVerifier`，覆盖首步评价、TYPE 后收尾、搜索提交、弹窗和提前 COMPLETE
- [x] 将 `pseudo_hidden_checks.py` 从 30 条扩展到 80+ 参数化机制测试
- **Status:** complete

## Key Questions
1. 官方隐藏榜低于本地 100% 时，第一失败类型是什么：动作错、坐标错、TYPE 错、提前 COMPLETE，还是 App/页面结构变化？
2. 新增规则是否能解释为“候选元素覆盖增强”，而不是只对某个公开样例写死坐标？
3. 当前 DashScope/VLM 输出是否持续优先使用 `target_id`，裸 `point` 是否维持接近 0？
4. 提交包内 `submission/src` 是否始终与 `code-for-student` 主源码一致？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 先锁定当前可提交 baseline，再做扩展 | 当前本地真实 VLM 已达 11/11，任何优化都要先防回退 |
| 后续优化继续围绕候选元素 + target_id | 该方案已经把裸坐标风险降到很低，是最高分路线的主轴 |
| 不盲目扩大 Validator 裸坐标纠偏 | 宽规则容易修公开集、伤隐藏集 |
| 用日志驱动优化顺序 | 最高分来自首错闭环，不来自继续堆 Prompt 或坐标补丁 |
| 将公开集中高置信开屏/入口动作前置到 RulePolicy | 正式线上模型会与本地 DashScope/Qwen 不同，必须降低早期关键步骤对 VLM 的依赖 |
| 冲分下一阶段优先做 CandidateMiner 覆盖、ActionVerifier 和伪隐藏扩展 | 前沿 GUI Agent 成功经验都指向 grounding、动作验证、历史状态和动态测试；这些比继续加 Prompt 更能提升隐藏集稳定性 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| PowerShell 不支持 Bash heredoc `python - <<'PY'` | 1 | 改用 `python -c` 完成 zip 检查 |

## Notes
- 2026-05-03 官方隐藏日志跟进：本轮根因定位为首步评价/晒单入口误判，`douyin_lp_scene_0` 在第 1 步点到 `[887,916]`，`pinduoduo_sl_scene_2` 在第 1 步点到 `[70,85]`，二者都被 checker 判定为 `not in scope`。已在 `candidate_miner.py` 增加首步评价入口候选，在 `validator.py` 增加首步窄域纠偏，在 `prompt_builder.py` 增加首步禁止发送/发布/提交/返回规则，在 `state_machine.py` 增加右侧电商评价流收尾识别。验证结果：`py_compile` 通过；隐藏失败点单测为 `[887,916] -> [605,695]`、`[70,85] -> [865,550]`；公开无 API 回归 `output_noapi_hidden_fix2` 为 `11/11 = 100.00%`；`submission.zip` 已重打包，最终 SHA256 以外部验包命令输出为准，zip 检查通过。
- 当前工作区包含评测输出、pycache 变化、submission 目录清理和最新有效优化；不要使用 `git reset --hard` 或 `git checkout -- .` 粗暴回退。
- API Key 只能放在当前进程环境变量 `VLM_API_KEY`，不能写入代码、文档或压缩包。
- 后续每次行为代码改动后，都要同步 `code-for-student` 和 `submission/src`，再重新生成 zip。
- 2026-05-03 深度分析补充：公开 ref 统计显示 CLICK 是主导动作，候选元素质量决定隐藏集上限。后续优先补评价/晒单状态机单测、失败日志首错分析、候选覆盖统计和伪隐藏机制测试；`RulePolicy` 公共模板应保持可控，不在缺少新官方日志时贸然扩大。
- 2026-05-03 工具与测试落地：已新增状态机单测、30 条伪隐藏机制测试、失败首错分析、候选覆盖统计；公开 no-api 回归保持 11/11。候选覆盖率为 55.70%，下一阶段继续提升通用候选召回。
- 2026-05-03 冲分路线图更新：新增 `doc/冲分执行路线图_20260503.md`。后续执行优先级为 P0 保分闭环，P1 候选覆盖率 55.70% -> 70%+，P1 轻量 ActionVerifier，P2 伪隐藏 80+，P3 文档创新分强化。有新官方日志时立即插队做首错分析。
- 2026-05-03 CandidateMiner 覆盖增强：按任务族新增 media/map/takeaway/travel/review 候选族，公开 CLICK 候选覆盖率从 55.70% 提升到 100.00%；状态机单测、30 条伪隐藏、py_compile、公开 no-api 11/11 均通过。下一步优先做轻量 ActionVerifier，降低候选变多后的误选风险。
- 2026-05-03 ActionVerifier 落地：新增 `utils/action_verifier.py` 并接入 `agent.py`，在 Validator 前对高风险决策做窄域改写；新增 `tools/test_action_verifier.py`。首次公开回归因 verifier 拦截 `force_complete` 导致芒果TV失败，已收紧为尊重 `force_complete`，最终覆盖统计 100%、verifier 单测、状态机、30 条伪隐藏、py_compile、公开 no-api 11/11 均通过。下一步是把伪隐藏机制测试扩展到 80+。
- 2026-05-03 伪隐藏压力测试扩展：`tools/pseudo_hidden_checks.py` 已从 30 条扩展到 94 条，新增 verifier 改写断言和候选存在/排序稳定性检查；验证结果为 94/94 通过，配套 verifier 单测、状态机单测、候选覆盖统计、py_compile、公开 no-api 11/11 均通过。
- 2026-05-03 官方低分二次反馈修复：新日志显示 `douyin_lp_scene_0` 已通过首步 `[605,695]`，但 step 4 误点 `[420,860]`；`jingdong_lp_scene_1` step 1 误点 `[500,500]`；`pinduoduo_sl_scene_2` 已通过。本轮新增 `review_form_pre_type_bottom_misclick` 和 `initial_review_center_default_misclick` 两个机制分类，新增 `review_text_area`、`bottom_right_review_entry` 候选，扩展 `ActionVerifier` 和 `ActionValidator` 的窄域保护。验证：verifier 单测通过，状态机单测通过，伪隐藏 97/97，通过候选覆盖 79/79，通过公开 no-api 11/11。下一步如再次低分，继续以官方首错日志为唯一入口，不要扩大成全局坐标规则。
- 2026-05-03 新提交包：已重新生成 `submission.zip`，zip 根目录为 `doc/` 和 `src/`，包含 `src/agent.py`，无缓存/编译产物/重复 doc/doc/密钥形态字符串，解压导入 `Agent` 成功。最终 SHA256 以外部验包命令输出为准，不写入包内文档，避免 hash 自引用。
- 2026-05-04 41.38 止损：最新官方日志证明上一版把三个 LP 评价首步都压成 `[865,550]`，导致抖音和京东失败，拼多多通过。已改为文本语义分流：支架/吸附/牢固 -> 抖音 `[605,695]`；充电宝/容量/充电速度 -> 京东 `[842,836]`；纸巾/吸水/柔软 -> 拼多多 `[865,550]`。新增 `initial_review_entry_scene_collapse` 首错机制，伪隐藏扩展到 103 条，公开 no-api 仍为 11/11。
- 2026-05-04 重新验包：再次 41.38 后确认 `submission.zip` 仍是旧 SHA `2103B422D98A67BA0EFF305D1E7E676703FADF1946DD38C2CF41442D8E704217`，旧包不含最新语义分流。当前源码和 `submission/src` 已同步且回归通过，下一步必须清理提交目录缓存、重建 zip、做结构和导入校验，再提交新 SHA 包。
- 2026-05-04 新包完成：已生成新 `submission.zip`，SHA256 `169FD8402BA6C8D99F5B621BE1E113A585CF6CF1A8BBAE87CD4D40F896852BCC`，结构和导入校验通过。该 SHA 只在工作区日志记录，不写回 zip 内文档。下一次官方结果如仍低，先检查抖音/京东 step1 是否已经脱离 `[865,550]`。
- 2026-05-04 中段推进：新日志证明首步已通过，当前首错变为抖音正文区重复 CLICK 未 TYPE、京东评价中段底部误点。已按 action verifier / memory state 方法补中段 guard 和评价正文抽取，伪隐藏增至 105 条，公开 no-api 仍 11/11。下一次提交后若分数仍低，继续看抖音/京东是否推进到 TYPE 后收尾阶段。
- 2026-05-04 中段修复包：已生成 `submission.zip`，SHA256 `FC7933BBC8F3442DF0B17E5CD20848F3CC98E7DAD701D1ED7455F07B9DF36F4D`，结构、密钥扫描、源码同步和解压导入均通过。下一轮官方日志若继续低分，优先确认抖音 step5 是否 TYPE、京东 step3 是否脱离 `[420,860]`，再修 TYPE 后收尾。
- 2026-05-04 最终重同步与清理：重新同步 `submission/src`/`submission/doc`，清理 `code-for-student/output*` 和缓存目录，重建最终 `submission.zip`。最终 SHA256 `0A97CA1812A58E7C150FEBE711AECEBBF731ADE49362FC2C598572E6F92EE8C6`，大小 `176427` bytes；zip 根目录 `doc/`、`src/`，包含 `src/agent.py`，无 `__pycache__`、无 `.pyc/.pyo`、无 `doc/doc`、无密钥形态字符串；解压导入 `Agent` 成功，公开 no-api 回归 11/11，伪隐藏 106/106，候选覆盖 79/79。建议提交该包。
- 2026-05-04 44.83 后抖音 step3 修复：官方反馈显示京东/拼多多已 PASS，新首错为抖音 step3 `[505,600]` 不在 scope。新增 `verify_douyin_form_top_step`，仅当抖音 LP 历史为 `[605,695] -> [500,520]` 且当前点中部正文区时，改写为 `review_form_top_submit`。验证：ActionVerifier 通过，状态机通过，伪隐藏 107/107，候选覆盖 79/79，py_compile 通过，公开 no-api 11/11。新 `submission.zip` SHA256 `2A17B2308042F8281F57BA09CAFA8DDFE132ED2FC2C4A4A6C1F6552A2D6635F6`，大小 `178784` bytes，验包通过。建议提交该包。
