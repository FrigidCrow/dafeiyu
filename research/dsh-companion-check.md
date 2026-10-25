# DSH 一体化情感陪伴插件：官方能力增量核验

核验日期：2026-10-26（Asia/Tokyo）。本报告接续 `research/dsh.md`，只核查 DeepSeek 官方公开文档与接口语义，没有安装、执行 DSH 或任何插件。固定文档修订为 `deepseek-ai/deepseek-harness@22ddee3792402c3e70ec5f86a63c3e3e895a2f60`（提交时间 2026-10-23T11:48:59Z）；本次 GitHub releases 列表仍以 `dsh-v0.2.1-rc.3` 为最新项（2026-10-23T15:26:39Z，预发布）。固定 master 文档证据不等于该桌面发行包已运行验收。

## 判断

**可以把 DSH 作为宿主，自己写一个一体化陪伴插件；官方接口已经覆盖专属 Agent、人格注入、持久存储、管理界面挂载和定时唤醒。** 不必为这些能力重写整个 Agent 框架。但“稳定人格、可纠正记忆、主动分享、连续经历”是插件自己的产品逻辑，不能靠宿主功能自动出现。

建议一个 `dsh-dafeiyu` 安装包，内部共用一个 CompanionService，拥有唯一的身份和记忆存储；QQ/B 站只作为适配器。使用专属 root Agent/会话，不把鱼挂在临时 delegated child 上，也不把人格全局注入所有 DSH 会话。上述是基于接口的设计建议，尚未运行验证。

## 五项官方证据与工程边界

| 需求 | 官方明确提供的能力 | 插件还需负责的部分 |
|---|---|---|
| 独立人格与对话 | `ctx.agents.create/resume`；`setup(agentCtx, agent)` 在发布 Agent 前注册能力；`agent.ctx` 的提示词、工具、变量、监听只作用于这个 Agent | 保存稳定的 fishId、关系 ID、SessionId；QQ 输入和主动活动都路由到同一条身份逻辑；不能假定别的 QQ 插件创建的 Agent 自动采用自己的 preset |
| 每轮读取人格和记忆 | `systemPrompt.section` 可提供动态文本；变量每次组装解析；runtime context provider 在请求入场前刷新；Agent 作用域覆盖同名全局贡献 | 人类锁定人格、版本和记忆检索；保存后下一次请求读取新数据；被删除或纠正的事实在摘要、索引和后续重学中也要受控 |
| 人类管理界面 | `settings.section`、`settings.plugins.tab`、`settings.onboarding` 插槽；配置表单有版本、原子多项提交、冲突保留草稿 | 自己实现“人格、记忆、活动、暂停”界面；记忆列表 CRUD 与检索走自有 Host 服务；框架没有现成的人格/记忆编辑产品 |
| 持久化与可追溯记录 | JSON/SQLite 后端、schema 校验、`storageDomain`；同域写队列，持久化成功后更新内存和发变更通知 | 定义记忆语义、来源、修订、禁止重学、导出/恢复；多表业务约束与跨域事务不能自行假定；跨进程通知未实现 |
| 持续活动和主动任务 | Schedule 持久任务、冷会话恢复、向原 Session 提交 `followup`；Agent 的 `followup` 唤醒下一轮，`steer` 唤醒下一步骤 | 兴趣活动循环、安静时段、预算、判断是否值得分享、QQ 出站发件箱、确认与去重；宿主退出/Mac 睡眠时没有活动进程 |

### 1. Agent 隔离是真的，但它不是一个永久后台守护进程

官方 Agent 文档第 32–43 行允许创建/恢复 Agent；不传 `parentAgent` 才是 runtime root。第 74 行明确 `agent.ctx` 注册只影响该 Agent，并随其释放撤销。第 58 行的三个入口不可混用：`followup` 会唤醒下一轮；`steer` 会唤醒下一步；`inject` 只添加下一次可接纳步骤的模型上下文，**不会唤醒**。官方还明确 `agent/request` 已弃用，不应给新插件增加此监听。

不要把会话永远保持运行当作“长期记忆”。长期状态应与 Agent 实例生命周期分离；恢复会话时重新挂载动态贡献。Agent 释放与“清空全部持久历史”不是同一个概念。来源：[Agent 官方文档，第 28–80 行](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/core/agent/README.md#L28-L80)。

### 2. 人格可限定作用范围，但 `complete` 是整段替换

官方系统提示文档第 56 行：一个 `complete: true` section 会成为完整系统提示；同一有效组成中有多个 complete section 会导致组装失败。因此不能随意叠装多个“人格接管”插件。完整替换还意味着要主动评估保留哪些宿主行为指导，而不只是往原提示末尾追加一段人设。

第 68–74 行说明变化中的事实应放入 context provider，注册的 context 在请求入场前重新读取，变量每次组装解析。第 179 行明确没有给终端用户提供现成的 prompt 编辑 API。建议核心人格用 Agent 作用域 section，相关记忆/情绪/近期活动用动态上下文；管理页更新权威存储后，使下一次模型请求读取新版本。已经发给模型的请求不会因修改数据库自动改写，这个边界需在 UI 说明并验收。来源：[System Prompt 官方文档](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/core/system-prompt/README.md)。

补充：修改 preset 定义与修改人格数据不是同一种刷新。官方 preset registry 文档说明现存 Agent 保留其组成修订，新 Agent 才使用当前定义；重启后按保存的 preset ID 使用当前定义，旧实现不会永久保留。服务提供方及消费者还必须位于同一个 `cordis:group` 隔离域，不能以为 entry-local 隔离自动穿透到 `agent.ctx`。普通人格数据更新应经过动态读取机制，无需反复修改 preset 或重建所有 Agent。来源：[Preset Registry 官方文档](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/preset/agent-preset-registry/README.md#understand-the-implementation)。

### 3. 定时器可以恢复原会话，却不是可靠外发系统

Schedule 第 442–446 行说明：Host 启动读取持久任务；通过 `schedule/resolve-agent` 激活原会话，冷会话由嵌入方/Session Controller 恢复；提交 followup 并确认 Session 刷盘后记投递凭据。它**不等待模型完成，不打断当前回合**。

Session 刷盘与任务记录写入并非跨存储原子操作，崩溃窗口可能重复投递；该组件没有模型结果确认、执行取消或外部通知渠道。第 470–471 行还明确：delegation depth 大于零的 child Session 创建任务会被拒绝为 `subagent_session`，因为未来投递不可达。

因此陪伴体应是可恢复的 root 会话；任务循环记录活动 ID，发送经持久 outbox，只有收到实际通道结果才写“已发送”。不能将 schedule receipt 呈现为“鱼已经看了 B 站/已经给你发 QQ”。macOS 睡眠和 DSH 退出期间停止执行是进程运行条件下的推论；不能靠插件承诺全天在线。来源：[Schedule 官方语义，第 440–480 行](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/subsystems/schedule.md#L440-L480)。

### 4. 管理页可以正式挂载，无需靠改宿主前端实现

官方 ui-settings 第 34 行提供配置编辑快照和版本检查；第 44 行给出 `settings.section` 等标准插槽。适合承载名称、人格、活动节律等参数。它自身不渲染界面，也没有把任意记忆表自动变成 CRUD 页。

建议提供单一“养鱼”管理入口，记忆页经自己的 Host 接口读写 `storageDomain`，支持查看来源、纠正、锁定、删除及生效状态。配置项与大量记忆记录不必塞到同一配置文档里。客户端挂载与 Host 服务都需要编入插件 bundle，并确认目标 DSH release 实际提供这些依赖。来源：[UI Settings 官方文档，第 28–48 行](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/client/ui-settings/README.md#L28-L48)。

### 5. 存储能保障单域写入秩序，不能替代记忆治理

Storage 第 126 行明确同域写队列的顺序是“后端确认→内存更新→变更事件”，`update` 提供队列位置上的原子读改写。返回值是存储对象本身，不应原地修改，必须通过写接口。第 130 行同名 domain 重复打开会失败，因此一套权威服务比多个各自打开相同域的记忆模块更稳妥。

第 153 行的 `domain/changed` 只是进程内通知，提交后监听失败不会回滚写入。它并不保证删除一条事实后历史会话/摘要/备份同步遗忘。插件要明确定义“删除”“归档”“禁止再学回”的不同效果。来源：[Storage 官方文档，第 126–153 行](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/subsystems/storage.md#L126-L153)。

## 最小可验收闭环（建议，尚未执行）

1. 专属鱼 Agent 收到 QQ 输入；其他 DSH 会话的人格不改变。
2. 一条用户事实写入自己的记忆域；管理页可见其来源和版本。
3. 人类在当前会话存活时纠正该事实，下一次回复使用新版本；删除后不会立即从旧摘要重建。
4. 一个持久任务在允许的时段恢复原会话，读一次 B 站实际资料，保存带来源的经历，再决定是否分享。
5. QQ 通道发送成功/失败均有真实记录；在“已入队、模型未结束、发送后确认前”三个位置重启，不重复分享同一条活动。
6. 宿主退出或 Mac 睡眠显示离线/暂停；恢复后补做活动有预算，不集中轰炸消息。

## 尚不能宣称已验证

- 当前 DSH 桌面包与新插件的 API/依赖装配、UI 运行、重启恢复。
- 普通 QQ 好友身份在这台 Mac 上的真实接收与主动发送；官方 QQ Bot 不能替代此验收。
- 人格稳定性、多日成本与打扰体验；这些需要对话评估和实际使用，不由接口存在直接推出。
- B 站数据成功获取及内容理解质量；看到了标题/简介不能冒充看懂完整视频。

结论的证据强度是“官方文档明确支持所需扩展结构，工程方案可行”，不是“已经运行完成的一体化养鱼产品”。
