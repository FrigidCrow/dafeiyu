# 从现有 QQ → NapCat → AstrBot → DeepSeek 到一站化大肥鱼：源码映射

日期：2026-10-25（Asia/Tokyo）。分析方式：只读获取官方仓库文件并静态阅读；没有安装依赖、执行目标代码、启动 QQ、发送消息或做运行测试。此文件是实施与验收设计，不是已实现报告。

本次固定源码：AstrBot `832fc6d98ac25facd54b07424c16067435c118e6`。这是当时 master 的提交，**不宣称等同 v4.29.3 release 内容**；最终实现应选择稳定 release 并重新核对这些接口。所有源码链接固定到该提交。

## 结论与边界

直接在已有链上做 `astrbot_plugin_dafeiyu`，保留 NapCat、AstrBot 与 DeepSeek Provider。插件拥有统一的人格、记忆、生活事件、主动决策、发件箱和管理页面。最初让普通聊天继续走 AstrBot 原生 Agent 流程，利用钩子补充上下文；不先重写模型请求循环、QQ 协议、通用 Web 后台或插件市场。

插件内部按普通 Python 模块划分，不能把所有逻辑放入 main.py。建议模块名是设计提案，不是仓库现有文件：`identity`、`persona`、`memory`、`observations`、`life_loop`、`outbox`、`delivery`、`admin`。用户看到一个“大肥鱼”页面和配置入口，底层仍有协议服务、应用服务和持久化目录。

## 1. 每一环保留什么、补什么

| 环节 | 已有源码与实际行为 | 保留宿主 | 自研模块 | 不需重写 | 可验证验收 |
|---|---|---|---|---|---|
| QQ 入站与身份 | `AiocqhttpAdapter._convert_handle_message_event()` 将 self_id、sender.user_id、私聊/群聊类型、session_id、message_id 转为 AstrBotMessage；`handle_msg()` 提交事件。 | OneBot WebSocket、消息格式转换、统一事件队列。 | 主人绑定、私聊白名单、入站幂等记录。身份键用平台实例ID + bot self_id + user_id；显示名只作显示。 | QQ 登录、网络协议、图片/语音通用转换。 | 同名陌生人不能读主人记忆；非目标群消息不触发陪伴；同 message_id 重放不重复记忆或回复。 |
| 事件参与方式 | `ProcessStage.process()` 先处理插件，再决定默认 LLM 流程；`StarRequestSubStage.process()` 遇到 is_stopped 退出。 | 默认对话和工具流程。 | 确定一个插件对目标私聊具有行为决策权；初期只监听/注入。 | 整条消息 Pipeline。 | 每条用户消息最多一次正常答复；管理指令与自然聊天不会双触发。 |
| 人格与上下文 | 原生 InternalAgentSubStage 在获取会话锁并准备 ProviderRequest 后触发 `OnLLMRequestEvent`。 | Provider、会话锁、原始聊天历史。 | 人格版本、相关记忆检索、状态与来源标注。稳定设定与动态上下文分开。 | DeepSeek HTTP SDK、模型适配、token streaming。 | 重启后人格一致；动态状态不进入永久历史；没有记录时能说不知道。 |
| 生成后记忆 | `MainAgentHooks.on_agent_done()` 依次触发 OnLLMResponseEvent 与 OnAgentDoneEvent；历史写回在 InternalAgentSubStage 随后的 `_save_to_history()`。 | 原生历史保存和正常取消流程。 | 用户事实原文、模型生成候选、外部观察、实际发送记录分层；去重、冲突、修订和来源关联。 | 用聊天历史冒充全部长期记忆。 | 一次生成对应一个候选批次；模型虚构不自动变用户事实；中止或发送失败不标“已告诉主人”。 |
| 主动行动 | Context 可独立调用模型；内置 CronJobManager 有 start/shutdown/sync_from_db，但 future_task 是计划任务。 | 模型 Provider 和可用的调度基础。 | 有界生活循环：时间窗口、兴趣、事件价值、预算、冷却、未回复抑制、主人忙碌状态。单一调度所有者。 | 从零造通用任务平台。 | 无新消息仍可读取一条B站观察并决定是否分享；关闭开关后所有主动出口都停；只空转检查时不调用昂贵模型。 |
| 主动发件箱与投递 | `Context.send_message()` 路由到 `platform.send_by_session()`；OneBot 再调用 send_private_msg。Context bool 不是投递回执。 | 平台实例路由、消息链和通用 OneBot 客户端。 | 持久化 outbox、唯一 action_id、租约、尝试记录、unknown 状态与停止检查。必要时加一个薄的 OneBot 回执适配器。 | QQ 私聊发送协议；全仓 fork。 | 任务重放不产生新 action_id；崩溃/超时保持未知；重启不盲重发；真实手机消息与账本可对应。 |
| 人工记忆管理 | PluginPageService 扫描插件 views；Context.register_web_api 注册接口。 | AstrBot 登录、页面承载、bridge。 | 记忆列表、来源、编辑、锁定、归档、删除、导入导出、行为开关与状态。 | 新开一套管理站点和账号体系。 | 未登录和非授权身份不能改记忆；编辑后召回立即正确；删除后不被旧摘要/队列复活。 |
| 停止/重载/恢复 | `Star.initialize()`、`Star.terminate()` 是生命周期；PluginManager 加载 await initialize，终止 await terminate。 | 插件启停和宿主更新机制。 | 取消自己的 worker、停止取新任务、等待在途数据库事务结束、持久化运行代次/租约、重启恢复。 | 宿主进程管理器。 | 连续重载10次仍只有一个生活循环；停用后不再发消息；重启后记忆与待处理状态一致。 |
| Mac→服务器 | AstrBot 与 NapCat Docker 构建支持 amd64/arm64，数据目录可挂载。 | 容器、系统服务、现有QQ通道。 | 统一部署文件、版本清单、数据备份/恢复、只允许一处主动运行。 | 桌面专属运行时和一套服务器重制版。 | 停旧实例→备份→服务器恢复后，人工修订和删除状态保留；QQ重新认证后收发通过；不会两边同时主动。 |

上表最后一列都是**将来的验收**，当前没有执行。

## 2. 精确源码定位

### 入站身份与事件

- [`_convert_handle_message_event()` L198](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/sources/aiocqhttp/aiocqhttp_platform_adapter.py#L198)：L210 取机器人 self_id，L211-L214 取发送人ID和显示名，L215-L225 分私聊/群聊及会话，L228 保留原 message_id。消息不能只按昵称识别主人。
- [`create_event()` L492 与 `handle_msg()` L509](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/sources/aiocqhttp/aiocqhttp_platform_adapter.py#L492)：包装平台事件并放入宿主队列。
- [`AstrMessageEvent.unified_msg_origin` L157](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/astr_message_event.py#L157)、[`get_sender_id()` L254](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/astr_message_event.py#L254)：UMO用于路由；业务的主人ID与平台路由分开保存，迁移或换平台时显式绑定，不能靠同名合并。

### 默认增强与完全接管两种模式

- [`ProcessStage.process()` L29](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/pipeline/process_stage/stage.py#L29)：插件 handler 可以产出 ProviderRequest；也存在正常默认 Agent 分支。优先复用。
- [`StarRequestSubStage.process()` L26](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/pipeline/process_stage/method/star_request.py#L26)：按 activated_handlers 执行；L40/L86 附近检查停止，handler 完成后可能清理结果。
- [`AstrMessageEvent.stop_event()` L399](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/astr_message_event.py#L399)：明确终止后续传播。只有已决定完整接管目标消息时才用它；不得让所有非目标用户也被吞掉。
- [`Context.llm_generate()` L180](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/star/context.py#L180)：直接调用 Provider.text_chat；**不会自动执行工具调用**。
- [`Context.tool_loop_agent()` L224](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/star/context.py#L224)：可执行工具循环，但默认使用 BaseAgentRunHooks，函数本身没有原生 Pipeline 那套会话历史写回。完全接管不能假定自动继承正常聊天的 hooks、锁、历史和发送。应由封装层明确处理并回归验证。

建议第一版默认增强；完全接管仅作为以后确有需要的受控模式。主动生活循环可调用自己的小范围工具集，不应默认把所有宿主 shell/文件工具开放给B站内容驱动的行为。

### Prompt 注入与临时上下文

- [`InternalAgentSubStage.process()` L239](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/pipeline/process_stage/method/agent_sub_stages/internal.py#L239)：使用 UMO 会话锁；[`OnLLMRequestEvent` L307](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/pipeline/process_stage/method/agent_sub_stages/internal.py#L307) 是原生流程的请求改写入口。
- [`ContentPart.mark_as_temp()` L68](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/agent/message.py#L68)：标注 provider-facing 的临时内容。配合 ProviderRequest.extra_user_content_parts 放本轮相关记忆、兴趣、B站观察摘要。
- [官方钩子说明](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/docs/zh/dev/star/guides/listen-message-event.md)：稳定角色设定适合 system prompt；每轮变动内容放额外用户内容，避免破坏前缀缓存和污染历史。外部网页、字幕、评论作为不可信观察数据，不具备改变人格、主人身份或发信权限的资格。

### 记忆写入时序

- [`MainAgentHooks.on_agent_done()` L23](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/astr_agent_hooks.py#L23)：先 OnLLMResponseEvent，再 OnAgentDoneEvent。
- [`InternalAgentSubStage` L459-L467](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/pipeline/process_stage/method/agent_sub_stages/internal.py#L459) 随后保存历史；[`_save_to_history()` L504](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/pipeline/process_stage/method/agent_sub_stages/internal.py#L504) 过滤初始 system / no-save 消息并调用 conversation manager。
- [`ConversationManager.update_conversation()` L279](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/conversation_mgr.py#L279) 与 [`add_message_pair()` L357](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/conversation_mgr.py#L357)：若完全接管，需要主动理解这类接口；不能在默认模式再写一份相同对话。

建议时序：收到用户消息先保存有身份/时间/原 message_id 的事实来源；本轮完成后生成候选记忆，再做类型/来源/冲突判断；人工确认/锁定的事实优先；AI生成的第一人称故事不能自动升级成真实经历。“我看了某视频”必须有观察记录，“我告诉了主人”必须有关联发送结果。

删除需要 tombstone 或等价禁止重建规则，覆盖候选队列、向量索引、摘要、图谱、发送队列；仅删一个检索条目不足以保证以后不出现。手动修订必须更新派生索引并失效相关缓存，保留修订审计但避免把已删除敏感正文继续放在普通日志里。

## 3. 发件箱最容易被忽视的限制

[`Context.send_message()` L655](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/star/context.py#L655) 的返回注释明确是“是否找到匹配的平台”。它 await 平台 send_by_session 后返回 True；它不是 QQ 已送达、更不是用户已读。

[`AiocqhttpAdapter.send_by_session()` L109](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/sources/aiocqhttp/aiocqhttp_platform_adapter.py#L109) 以 event=None 发送，说明主动消息不依赖当前入站事件；[`AiocqhttpMessageEvent._dispatch_send()` L91](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/sources/aiocqhttp/aiocqhttp_message_event.py#L91) 调用 bot.send_private_msg / send_group_msg，但这个方法不返回 OneBot 响应体。

因此推荐内部状态至少分：`queued → leased → sending → platform_call_completed`，另有 `failed / unknown / cancelled`。如果薄适配器保留 OneBot 返回的 message_id，可另记 `platform_accepted`；真正手机展示与用户已读仍是不同证据，不自动合并。

去重键采用“行为ID + 目标身份 + 发送部分序号”，存在数据库唯一约束。生成内容与入 outbox 在同一个业务事务里；发送前再次检查主人绑定、主动开关、安静时段、冷却和有效期。网络超时可能发生在平台已接受之后，这时设 unknown，不盲目自动重发。没有平台幂等保证和可核实回执时，不能承诺严格 exactly-once。

如果要保留 OneBot ACK，不需重写协议，可通过 [`Context.get_platform_inst()` L820](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/star/context.py#L820) 和协议端 [`get_client()` L512](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/sources/aiocqhttp/aiocqhttp_platform_adapter.py#L512) 封装一个窄的发送适配器。该方案依赖具体平台类型，需要版本测试；初期仅负责主动纯文本/链接，普通聊天仍走宿主消息链。没有必要为此把整个 AstrBot fork 走。

**不要把 after_message_sent 当强送达证据。** [`RespondStage.process()` L354-L404](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/pipeline/respond/stage.py#L354) 会捕获部分发送异常并继续，而 L406 仍可能调用 OnAfterMessageSentEvent；流式分支则提前返回。它是流程钩子，不是覆盖所有路径的可靠回执。记忆和行为统计要写清使用了哪一种证据。

## 4. 一站化设置与记忆页面

- [`Context.register_web_api()` L764](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/star/context.py#L764) 注册插件后端，重复 route + methods 会替换。
- [`PluginPageService.discover_plugin_pages()` L474](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/dashboard/services/plugin_page_service.py#L474) 发现页面；[`build_security_headers()` L398](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/dashboard/services/plugin_page_service.py#L398) 与 [`resolve_plugin_page_file()` L530](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/dashboard/services/plugin_page_service.py#L530) 是页面加载边界。
- [官方 Plugin Views 合同](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/docs/zh/dev/star/guides/plugin-pages.md) 定义 `views/<name>/index.html`、`window.AstrBotPluginView` 和 `astrbot.api.web`。不要自行把内部原始框架请求对象当长期公共接口。
- [`PluginKVStoreMixin` L9](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/utils/plugin_kv_store.py#L9) 按 plugin_id 隔离简单 KV。业务记忆数据库宜放 `data/plugin_data/astrbot_plugin_dafeiyu/`，按[官方存储规范](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/docs/zh/dev/star/guides/storage.md)独立维护，不把成千条记忆塞到少量配置字段。

一个页面提供四个业务区：鱼的状态与主动开关、人格与偏好、可审查记忆、经历与发送记录。配置初次只要求主人QQ、模型、QQ通道和B站观察方式；其余有可解释默认值。高级技术日志折叠在诊断区，避免把框架配置项全部暴露成养鱼日常操作。

## 5. 停止、重启与迁移

[`Star.initialize()` / `terminate()` L141](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/star/base.py#L141) 是生命周期接口；[PluginManager.load L1422](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/star/star_manager.py#L1422) await initialize，[`_terminate_plugin()` L1932](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/star/star_manager.py#L1932) 对新式插件 await terminate。不要把清理放在已废弃的 `__del__`。

initialize 打开数据库、检查迁移、回收过期租约、恢复有界worker；terminate 设置停止标志、禁止新发件箱任务、cancel 并 await 自己创建的任务、完成或回滚事务后关闭连接。后台asyncio任务不能只create_task后丢引用。恢复时区分 queued、sending、unknown，不把崩溃前的所有任务都算成“没发”。

[`CronJobManager.start()` L116、`shutdown()` L127、`sync_from_db()` L136](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/cron/manager.py#L116) 可作已有调度能力的参考，但自研生活循环与内置future_task必须有清晰责任，不能各维护同一套发信计划。

先 Mac 稳定，再 Linux：使用同一逻辑版本与挂载布局；跨架构重建/拉镜像，不搬 Python 虚拟环境。先关闭旧实例主动权，一致性备份配置、人格、记忆、来源、派生索引版本、outbox、审计与QQ数据，校验恢复后才打开新实例。QQ/B站新环境登录必须重新确认，不能以文件存在代替有效登录。采用单写者租约或部署约束，明确只允许一处后台主动运行。

## 6. 实施顺序与具体证据

1. 先做监听插件：专用QQ好友私聊 → 主人绑定 → 确认一次消息只处理一次。保存入站ID和一条可核实回复。
2. 加人格与记忆：当前请求钩子注入 → 管理页可看/改/删 → 换话题和重启后验证召回，检查误记和删除复活。
3. 加外部观察：B站结果必须有URL、采集时间、读取层级和实际证据；观察失败不能生成“我已经看完”。
4. 加主动行为：真实观察 → 行动决策 → outbox → QQ手机收到。覆盖未回复、安静时段、断线、重复触发和发送超时。
5. 最后打包一站化入口与迁移：健康状态、备份恢复、版本固定、7天稳定性记录；Mac端模拟睡眠/重启，服务器端重新验证。

每一步都保存构建版本、事件/行为ID、输入来源、关键状态转移与实际端验收。静态阅读证明“接口存在”，单元测试证明“逻辑在模拟条件下正确”，QQ手机收发和连续运行才证明“这条鱼在目标环境能用”。

## 7. 许可证记录

AstrBot 固定提交下的 [LICENSE](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/LICENSE) 为 GNU AGPL v3。LivingMemory 与 Proactive Chat 也标 AGPL-3.0；复制其实现时应记录来源和许可证，不能把复制代码当成自行选择任意许可证的原创。通过公开 API 自己写插件与复制/修改上游代码是不同事实，需要在发布和提供他人网络使用前单独核对具体义务；这里不作法律定论。

NapCat 主仓库[LICENSE](https://github.com/NapNeko/NapCatQQ/blob/main/LICENSE) 是 Limited Redistribution License，含非商业及修改/分发限制。部署对接与打包再分发应分别核对；“一站化”可以先交付自己的插件和部署说明，不必把第三方协议端改名打包。腾讯 dsh-qqbot 的 MIT 许可证不能覆盖 NapCat 或 AstrBot。
