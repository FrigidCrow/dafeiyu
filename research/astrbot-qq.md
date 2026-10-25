# AstrBot、QQ 接入与 Mac → 服务器路线调研

调研日期：2026-10-25（Asia/Tokyo）。只读查阅官方文档、官方仓库、插件作者文档及部分源码，未安装、未登录 QQ、未实测消息收发。下文“已核实”表示文档/源码可核实，不代表用户账户运行验收。

## 结论

针对已经明确的“普通 QQ 好友身份、私聊、主动找我、先自己的 Mac、稳定后迁服务器”，优先考虑 **AstrBot + 一个自研 companion 插件 + 可替换的 OneBot 适配层**。NapCat 只承担 QQ 通道，插件统一拥有人格、记忆与行为决策；不要同时安装多个会重写提示词、抢占对话或自行定时发消息的陪伴插件。

Mac 初期推荐用 Docker 中的 Linux QQ + NapCat，与 AstrBot 一起组成可搬迁的部署。原生 Mac NapCat 已有近期支持，不能再说“不支持 Mac”；但 Docker 更符合本项目的数据隔离与后续迁移需求。这是架构判断，非本机运行验证。

QQ 官方机器人可以作为备用通道，但不等于普通 QQ 账号好友，而且主动推送的一手资料存在冲突，不能把它宣传成已保证的长期主动私聊通道，也不能沿用“全部禁止”的过时概括。

## 已核实能力与限制

| 项目 | 证据与含义 |
|---|---|
| AstrBot 版本 | GitHub latest release 为 v4.29.3，发布于 2026-10-24 15:48:37 UTC，即 2026-10-25 00:48:37 JST。主仓库许可证 AGPL-3.0。 |
| 人格 | WebUI 提供 Persona；具体会话可用自定义规则指定人格。适合存稳定角色，不等于已有长期生活史。 |
| 插件生命周期 | Python 插件继承 Star、主入口 main.py；Context 提供框架服务；停用/卸载调用 terminate。业务可拆在普通 Python 模块里，不必 fork 框架。 |
| 消息钩子 | 官方文档给出接收私聊/群聊、on_llm_request、on_llm_response、on_agent_begin/done、工具调用前后、发送前后钩子及优先级。足以实现统一上下文编排。 |
| 动态上下文 | 官方建议稳定设定进 system prompt；动态心情、时间、相关记忆进 extra_user_content_parts，临时内容用 mark_as_temp()，避免每轮变更 system prompt 和污染永久历史。不要照搬文档中具体缓存涨价倍数作为本项目实测成本。 |
| 主动发消息 | 保存 event.unified_msg_origin，后续 context.send_message(origin, chains) 可在没有当前入站事件时发送；实际能否送达由平台决定。 |
| 调度 | 内置 future_task 在 v4.14.0 引入、仍标实验性。它执行已创建的定时任务，并非持续自主观察与行动的生活循环；宿主必须运行。 |
| 人工管理页面 | 插件可提供 views/<name>/index.html，通过 AstrBotPluginView bridge 与 register_web_api 后端通信；适合记忆浏览、修订、归档、删除、溯源、导入导出。 |
| 持久化 | 每插件有独立 KV；业务文件建议 data/plugin_data/<plugin_name>/。可以把记忆数据库、状态、任务队列放独立目录。 |
| 内置知识库 | 处理上传资料的 RAG，支持嵌入/检索；不是自动生成的个人记忆，也不会把资料永久训练进模型。用户偏好、关系、事件修订仍应由 companion 记忆层管理。 |

主要来源：[release](https://github.com/AstrBotDevs/AstrBot/releases/tag/v4.29.3)、[人格和会话规则](https://docs.astrbot.app/use/custom-rules.html)、[插件最小实例](https://docs.astrbot.app/dev/star/guides/simple.html)、[事件与提示词钩子](https://docs.astrbot.app/dev/star/guides/listen-message-event.html)、[主动发送](https://docs.astrbot.app/dev/star/guides/send-message.html)、[未来任务](https://docs.astrbot.app/use/proactive-agent.html)、[插件页面](https://docs.astrbot.app/dev/star/guides/plugin-pages.html)、[存储](https://docs.astrbot.app/dev/star/guides/storage.html)、[知识库](https://docs.astrbot.app/use/knowledge-base.html)。

## QQ 两条路线不能混为一谈

| | QQ 官方机器人 | 普通 QQ 账号 + NapCat |
|---|---|---|
| 身份 | QQ 开放平台创建的机器人，AppID / AppSecret / OpenID | 独立 QQ 账号，以好友身份与主人交流 |
| 接入 | AstrBot 当前推荐官方 WebSocket；可在后台扫码创建，手机 QQ 扫码聊天 | AstrBot 接入 OneBot v11 反向 WebSocket，NapCat 登录 QQ 并收发事件 |
| 主动私聊 | AstrBot 有实现，但腾讯公开文档与当前适配器证据冲突；需要目标账户核实 | OneBot 提供主动发送路径，仍受 QQ 实际登录、风控、网络状态影响 |
| 本项目适合度 | 用户接受机器人身份时的备用 | 最符合“普通 QQ 好友”需求 |
| 部署依赖 | 不必运行个人 QQ 客户端协议端 | 需要运行 QQ / NapCat，维护登录态 |

[AstrBot QQ 官方接入](https://docs.astrbot.app/platform/qqofficial/websockets.html) 明确支持私聊、群聊，并标“主动消息推送：支持”。[AstrBot OneBot 文档](https://docs.astrbot.app/platform/aiocqhttp.html) 明确说明 NapCat 是接入 QQ 的一种实现端。NapCat 的[项目说明](https://github.com/NapNeko/NapCatQQ)将其定义为基于 NTQQ 的协议端，并非腾讯官方开放接口。

### 主动推送资料冲突的准确处理

1. 腾讯官方 [bot-docs send.md](https://github.com/tencent-connect/bot-docs/blob/main/docs/develop/api-v2/server-inter/message/send-receive/send.md) 顶端仍写“2025-04-21 起不再提供主动推送”，但同页保留“每月 4 条”等旧配额。因此这些数字不能直接当作 2026 年实际配额。
2. AstrBot 官方当前文档写支持主动推送；源码也真实实现了该分支。已查看固定提交 `832fc6d98ac25facd54b07424c16067435c118e6` 的 [qqofficial_platform_adapter.py](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/sources/qqofficial/qqofficial_platform_adapter.py#L386)：私聊不强制要求缓存 msg_id；[L493-L496](https://github.com/AstrBotDevs/AstrBot/blob/832fc6d98ac25facd54b07424c16067435c118e6/astrbot/core/platform/sources/qqofficial/qqofficial_platform_adapter.py#L493) 主动移除 msg_id；代码注释也只是经验性说明，不能代替腾讯承诺。群聊另有开关和场景限制。
3. [issue #7904](https://github.com/AstrBotDevs/AstrBot/issues/7904) 记录过超过 12 小时无对话后，旧版本因缓存 msg_id 而跳过实际发送、但工具显示成功的故障。这个历史个案恰好说明验收必须看手机收到消息，不能只看日志“sent”。
4. 腾讯 [dsh-qqbot](https://github.com/tencent-connect/dsh-qqbot) 当前 package.json 版本 0.5.2、MIT，确有 QQ 私聊/群聊与扫码绑定；但[主动通知钩子请求 #16](https://github.com/tencent-connect/dsh-qqbot/issues/16) 截至查询仍 open、没有评论，报告针对 0.4.0。该 issue 只能证明存在过集成缺口，不能据此断言 0.5.2 一定不能主动。DSH 组另查当前实现。

验收建议：目标账号首次绑定后，分别验证即时回复、无新消息 2 小时后的主动消息、隔夜主动消息、重启后主动消息，并记录平台返回码及手机端实际收到时间。官方平台的权限、配额与用户客户端允许设置需以实际账户为准。

## Mac 上运行与迁服务器

### 可用路线

- **推荐候选：Docker Desktop + Linux 容器。** Docker 官方提供 Apple Silicon 与 Intel 两种 Mac 版本。NapCat-Docker 官方 README 写明 `Linux amd64 / arm64`，Dockerfile 按架构下载 Linux QQ；AstrBot 官方构建工作流也构建 `linux/amd64,linux/arm64`。这支持“同一份部署定义先 Mac、后 Linux 服务器”的技术路线，但本次没有拉镜像、登录或做端到端验证。
- **原生 Mac：现在具备候选条件。** NapCat v4.18.36/37 起近期 release 写明原生 arm64 / x64；v4.18.37 的维护者报告在 QQ 7.0.2-53644 上双架构无登录启动超过 35 秒，Packet / Napi / Native FFmpeg 初始化通过，保留腾讯原签名。报告明确未进行 QQ 登录，不能等价为连续登录与消息收发验收。当前 latest release 为 v4.18.41（2026-10-21）。
- **不要混淆 NapCatQQ 与 NapCatQQ Desktop。** 后者是 Windows 控制台，当前没有 Mac 版，不代表协议核心没有 Mac 支持。

来源：[Docker Mac](https://docs.docker.com/desktop/setup/install/mac-install/)、[NapCat Docker](https://github.com/NapNeko/NapCat-Docker/blob/main/README.md)、[Dockerfile](https://github.com/NapNeko/NapCat-Docker/blob/main/Dockerfile)、[AstrBot 镜像构建](https://github.com/AstrBotDevs/AstrBot/blob/master/.github/workflows/docker-image.yml)、[NapCat v4.18.37 验证范围](https://github.com/NapNeko/NapCatQQ/releases/tag/v4.18.37)、[NapCat 最新版](https://github.com/NapNeko/NapCatQQ/releases/tag/v4.18.41)、[Desktop 平台](https://napneko.github.io/NapCatQQ-Desktop/docs/installation/)。

### 建议的分层与搬迁范围（设计建议）

`QQ 专用账号 ↔ NapCat ↔ OneBot ↔ AstrBot ↔ companion 插件 ↔ 独立持久化数据`

人格和记忆不存放在 QQ 协议层。只把 AstrBot 事件类型、UMO 和发送接口放在薄适配器里，核心记忆/日程/兴趣模块用普通 Python 服务实现。未来换 QQ 接入或宿主时不必迁移一套人格。

固定服务版本与镜像摘要；持久化至少包含 AstrBot data、插件数据库/配置/来源证据、定时任务和发送 outbox、NapCat 配置、QQ 用户数据及 B 站浏览状态。密钥单独保存，备份不要混入可分享报告。数据库使用一致性备份，跨架构重新拉适配镜像，不复制 Mac Python 虚拟环境或原生二进制到 Linux。

迁移时先停止旧实例的发信/调度，完成一致性备份和校验，再在服务器恢复；确认记忆总量、人工修订、删除标记、任务去重键、时区都一致后才恢复主动行为。QQ 登录态和 B 站 cookie 可以备份，但换设备/IP 后可能需要重新验证或扫码，不能承诺“拷文件就永远在线”。迁移过程只允许一个实例拥有主动发送权，避免两条鱼同时发相同消息。

Mac 本机必须持续运行。睡眠、关机、Docker 退出会让行为循环暂停。Apple 官方提供接电时防止熄屏自动休眠的选项，但这不是合盖/断网/断电仍然在线的承诺。先验证唤醒后任务恢复和重复消息抑制，再决定常驻服务器。[Apple 睡眠设置](https://support.apple.com/en-bh/guide/mac-help/mchle41a6ccd/mac)

NapCat 官方[安全说明](https://napneko.github.io/other/security) 提到账号风控和掉线；它不是免风控保证。适合用专用 QQ 号、仅允许主人私聊，OneBot 和管理面板仅内部网络/本机访问。其 [LICENSE](https://github.com/NapNeko/NapCatQQ/blob/main/LICENSE) 是带非商业与修改/分发限制的自定义许可证，不能因 GitHub 可见就当作 MIT；本项目应把它当外部可替换通道，未来商业化另行评估授权。

## 现有插件值得借鉴什么

### LivingMemory 2.7.1

作者文档和 metadata.yaml 可核实长期记忆、自动总结、主动读写工具、关键词/向量/图谱混合召回、作用域隔离；管理页面支持查看来源、编辑摘要/事实、归档、删除、导入导出、召回调试。它已经覆盖用户所说的“人类可以介入管理”的相当部分，不应把现有生态描述成只有一个向量数据库。

有用参考：编辑记忆时重建派生索引；来源记录与总结分离；归档可逆、删除不可逆；跨会话隔离；临时召回上下文不写回聊天历史。局限：需要嵌入服务，不能仅靠 DeepSeek 聊天模型直接完成向量化；插件宣称与本项目召回/删除验收是两回事；它不负责完整行为循环、B 站感知和发信策略。选它作唯一记忆组件，或参考其结构自建，避免两个记忆插件双写。

来源：[仓库](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory)、[功能](https://lxfight-s-astrbot-plugins.github.io/astrbot_plugin_livingmemory/en/features)、[管理页面](https://lxfight-s-astrbot-plugins.github.io/astrbot_plugin_livingmemory/en/webui)、[注入与隔离配置](https://lxfight-s-astrbot-plugins.github.io/astrbot_plugin_livingmemory/en/configuration)。许可证 AGPL-3.0。

### Proactive Chat v1.2.6

当前 metadata 声明 AstrBot >=4.24.0，支持 aiocqhttp 与 qq_official 等平台。作者说明提供私聊/群聊主动消息、持久化调度、上下文、免打扰、未回复限制和 WebUI。可借鉴“冷却、未回复不追发、安静时段、重启恢复”的机制，不能把随机主动问候等同于有生活经历。它自己的动态情绪/人格读取/计时器若与 companion 同时拥有发送权，容易重复聊天；应由统一策略决定发不发。

来源：[仓库](https://github.com/Pancakes-Labs/astrbot_plugin_proactive_chat)、[metadata](https://github.com/Pancakes-Labs/astrbot_plugin_proactive_chat/blob/main/metadata.yaml)。许可证 AGPL-3.0。

## 单插件的可行边界与推荐验收

一个 AstrBot 插件能够承载上述陪伴业务，依据是消息钩子、模型调用、主动发送、存储与自定义页面均有公共扩展点。工程上应是“一个产品入口 + 内部分模块”，不是把上万行放在 main.py，也不是自己重写 QQ 网络协议。

建议由插件统一拥有：稳定人格版本、可修订记忆、当天经历/兴趣、主动行动决策、B 站观察结果、发送去重与节奏、管理 UI。AstrBot 负责消息和模型基础设施，NapCat 负责 QQ 通道。B 站数据源和模型供应商都是可换适配器。

最小验收闭环：QQ 私聊建立偏好 → 写入可审查记忆 → 主人更正 → B 站检索/字幕观察 → 生成有来源的个人看法 → 在合适时段主动发给主人 → 重启后仍能承接，且不重复发送。额外必须验证：删除后不从索引、摘要或排队消息复活；关闭主动开关后所有发送路径均停；QQ 断线显示真实状态；模型/网络失败不伪造已看视频或已发消息。

主任务随后只读确认本机为 Apple M4、arm64、24 GiB。尚未验证：Docker 现状、QQ 专用账号是否可用、目标 IP 登录风控、B 站 cookie 权限、实际 API 成本、持续 7 日体验、真实消息送达。这些是后续原型验收项，不是本次研究已经通过的测试。

## 针对现有 QQ → NapCat → AstrBot → DeepSeek 链的具体改造入口

用户补充截图说明已有这条链，目标是一站化。这里推荐直接保留这条链，做一个统一产品插件与部署入口，无需再造通用机器人框架。

优先采用“增强原生流程”：私聊事件收集输入，`on_llm_request` 注入稳定人格和本轮记忆，`on_agent_done` 提取候选记忆，发送后记录真实发送结果。AstrBot 继续负责模型、工具循环和正常回复。这样最大程度复用原有能力。

仅当确实需要由 companion 完整管理一轮对话时，才在匹配目标私聊的 handler 中调用 `event.stop_event()` 停止后续默认处理，再用 `context.llm_generate()` / `context.tool_loop_agent()` 和统一发送出口接管。这必须同步处理会话历史、并发锁、取消、错误与发送记录，不能只截住消息后再额外发一遍，造成双回复。定时主动行为不伪装成用户输入，由插件调度入口调用同一个策略和发送出口。

代码定位（以本次查询主分支为准，实作需固定 release 后核对）：

| 职责 | 源码路径 |
|---|---|
| QQ / OneBot 接入 | `astrbot/core/platform/sources/aiocqhttp/aiocqhttp_platform_adapter.py`、`aiocqhttp_message_event.py` |
| 插件与 Agent 流程 | `astrbot/core/pipeline/process_stage/stage.py`、`method/star_request.py`、`method/agent_request.py` |
| 模型、工具循环、发送、页面API | `astrbot/core/star/context.py`，本次源码分别约 L180、L224、L655、L764 |
| 事件钩子使用合同 | `docs/zh/dev/star/guides/listen-message-event.md` |
| 记忆管理界面 | `docs/zh/dev/star/guides/plugin-pages.md`、`astrbot/dashboard/services/plugin_page_service.py` |
| 持久化规范 | `docs/zh/dev/star/guides/storage.md` |
| 人格数据与后台 | `astrbot/core/persona_mgr.py`、`astrbot/dashboard/services/persona_service.py` |
| 未来任务 | `astrbot/core/cron/manager.py`、`astrbot/core/tools/cron_tools.py` |

“一站化”应包含：一个配置向导、一个主人身份绑定、一个记忆管理页面、一个全局主动开关、一处看到 QQ/B站/模型状态，以及一份可从 Mac 搬到服务器的数据备份；底层仍可保留 QQ 协议端与应用服务的进程边界。
