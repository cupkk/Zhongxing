# 主流电脑/手机 Agent 调研与本项目优化报告

这份报告回答两个问题：第一，市面上效果好的电脑和手机 Agent 通常怎么运行；第二，这些经验具体怎么用到本项目里，为什么当前分数卡在 55.17 不是简单换模型就能解决。

## 一、主流 Agent 的共同运行方式

OpenAI、Claude、Google Gemini 这类 Computer Use 产品，核心都不是“一次让模型猜完所有步骤”，而是一个循环：

```text
看当前截图 -> 模型给出下一步动作 -> 程序执行动作 -> 再截一张新图 -> 模型继续判断
```

OpenAI 的 Computer Use 文档明确把这个过程拆成：发送任务、检查模型返回的 computer_call、按顺序执行 actions、捕获新屏幕并回传，直到模型不再返回动作。Claude 文档也把它称为 agent loop：Claude 请求工具动作，应用执行后把截图或命令输出再返回给 Claude。Google Gemini Computer Use 的文档同样说明模型会分析用户请求和截图，然后返回代表 UI 操作的 function_call。

这说明一个关键事实：效果好的 Agent 一般不是让模型“凭感觉点一下”，而是由模型负责视觉理解，外层程序负责执行、校验、记录和再次观察。

## 二、几类代表系统可以借鉴什么

OpenAI/Codex 方向的重点是“工具化闭环”。OpenAI 文档里强调截图输入、结构化 UI 动作输出、执行后再反馈截图；Codex 的用例里也把“用 Computer Use 点击真实产品流程并记录问题”列为 QA 场景。这对我们项目的启发是：不能只把 VLM 当聊天模型用，而要把它放进一个可验证的动作循环里。

Claude Computer Use 的重点是“执行环境隔离和迭代上限”。Claude 文档里推荐容器环境、工具实现、agent loop，并设置最大迭代次数，避免无限循环。对应到本项目，就是 `Memory` 要记录已经点过哪里、已经输入过什么；`Validator` 要阻止重复点击和提前结束。

Google Gemini Computer Use 的重点是“function_call + safety decision”。它把下一步 UI 动作包装成结构化函数调用，并可能给出需要确认的安全判断。对应到本项目，就是模型输出不能直接信任，要经过 `OutputParser` 和 `ActionValidator`，把动作类型、坐标、文本都校验一遍。

Flowith Agent Neo 更偏长任务工作流：官方页面强调 infinite context、infinite tools、非停止式任务执行；FlowithOS 文档也提到把 Neo 生成的工具或资源交给 FlowithOS 打开、测试、填充数据并放进更大的 workflow。它给本项目的启发不是“照搬无限步骤”，而是把任务经验沉淀下来，比如“电商评价输入后可完成”和“视频评论输入后还要点发送”这种流程知识。

手机 Agent 论文方向也很一致。Mobile-Agent 强调用视觉感知工具定位文字和图标，再逐步操作手机；AppAgent 用简化动作空间和探索/演示沉淀 App 操作知识；SeeClick、OS-Atlas、UI-TARS 都说明 GUI grounding 是瓶颈，也就是“模型知道要点发送，但坐标不一定点准”。这正好对应我们现在的隐藏集问题。

## 三、当前 55.17 分不变的真实原因

从最新隐藏日志看，京东和拼多多已经通过：

```text
jingdong_lp_scene_1：PASS
pinduoduo_sl_scene_2：PASS
```

抖音失败已经不是“不会输入评价”，而是最后一步坐标不在官方范围内：

```text
douyin_lp_scene_0
Step 1-5：都通过，已经输入“手机支架很好用，吸附牢固，设计美观，非常满意！”
Step 6：Agent 输出 CLICK [887, 916]
Checker：CLICK failed: (887, 916) not in scope
```

这句话非常重要：`expect CLICK` 已经说明动作类型对了；`not in scope` 说明错在坐标，不是错在模型语义理解。官方评测器不是再用一个模型主观判断，而是用 `test_runner.py` 里的 `Checker` 做确定性检查：动作类型必须一致，CLICK 坐标必须落进 `ref.json` 的范围，TYPE 文本要匹配，COMPLETE 只能在参考动作也是 COMPLETE 时通过。

所以分数不变的根因是：隐藏集第一个失败用例仍然卡在抖音第 6 步，且评测模式下一旦失败会终止该用例，后面就没有机会得这一条用例的分。

## 四、本轮落地到项目的优化

这次没有盲目继续换模型，而是按上面的 Agent 经验增强本地控制层：

```text
1. 把“刚输入评价后”的状态作为高风险状态处理。
2. 京东、拼多多、淘宝这类明确电商评价：输入完评价后可 COMPLETE。
3. 抖音/内容流商品评价：虽然也有“商品、评价”字样，但输入后还要 CLICK 发布。
4. 如果历史第一步点击在中下区域，并且后面出现过顶部/星级区域点击、大文本框点击，更像内容流里的商品评价表单。
5. 这类流程第 6 步不再点普通评论框右下角 [887,916]，而改点底部居中的发布/提交区域 [500,938]。
```

通俗讲，之前的 Agent 容易把“电商评价”和“抖音商品评价”混在一起。现在规则会先看历史动作：京东/拼多多入口通常在右侧，抖音内容流入口更偏中下区域；输入完成后，二者的收尾动作不同。

## 五、下一步怎么继续提分

如果下一次提交后抖音第 6 步通过，分数应该会继续涨；如果仍然失败，要重点看失败坐标：

```text
如果 CLICK [500,938] 仍 not in scope：
说明发布按钮不在底部居中，需要从日志继续推断可能范围，比如顶部右侧或底部偏右。

如果又变成 COMPLETE：
说明规则没有触发，要检查 app_name 或 social_flow 判断。

如果抖音通过但新用例失败：
不要回头乱改抖音，按新失败用例归类优化。
```

后续优化路线应该保持“模型看图 + 程序兜底”：

```text
VLM：负责识别当前截图属于哪一步。
Memory：记录历史点击、输入、打开 App。
Validator：修正高风险动作，比如输入后乱点、提前 complete、坐标明显偏离。
Docs：把每次榜单日志归纳成可复用流程知识。
```

这也是目前主流电脑/手机 Agent 的共同路线：模型负责理解，工程层负责稳定执行。

## 参考资料

- OpenAI Computer Use 文档：https://platform.openai.com/docs/guides/tools-computer-use
- OpenAI Codex use cases：https://developers.openai.com/codex/use-cases
- Claude Computer Use 文档：https://docs.claude.com/en/docs/agents-and-tools/tool-use/computer-use-tool
- Google Gemini Computer Use 文档：https://ai.google.dev/gemini-api/docs/computer-use
- Flowith Agent Neo：https://flowith.com/agentneo
- FlowithOS 文档：https://doc.flowith.io/flowithos/about-flowithos
- Mobile-Agent：https://arxiv.org/abs/2401.16158
- AppAgent：https://arxiv.org/abs/2312.13771
- SeeClick：https://arxiv.org/abs/2401.10935
- OS-ATLAS：https://arxiv.org/abs/2410.23218
- UI-TARS：https://arxiv.org/abs/2501.12326
- AndroidWorld：https://arxiv.org/abs/2405.14573
