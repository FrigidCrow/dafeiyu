# DSH 普通 QQ 好友通道增量核验

日期：2026-10-26（Asia/Tokyo）。仅查阅项目作者 README、package.json、许可证与选定源码；没有安装插件、启动目标代码、登录 QQ 或发送消息。下文的“实现存在”不等于在用户 Mac、指定 DSH 版本和 QQ 账号上联调通过。

## 结论

**DSH → 社区 OneBot 插件 → NapCat → 普通 QQ 账号这条路已有实现，不必为了个人 QQ 私聊再加一层 AstrBot，也不能继续概括为“只有不支持 Mac 的旧桥接项目”。** 当前至少两份源码包含个人 QQ 私聊路由和脱离当前入站事件的出站能力。

但现成通道与统一陪伴产品仍有距离：身份和会话的统一、定时主动找主人、出站结果进入同一个对话上下文、持久发件箱、重启与失败处理，仍应由自己的陪伴插件统一管理。腾讯 `tencent-connect/dsh-qqbot` 接的是官方机器人身份，不能替代本次“普通 QQ 好友”验收。

## 三个候选的实际边界

| 候选及本次固定版本 | 已从源码核实 | 对本项目的价值与缺口 |
|---|---|---|
| [mario841859784/dsh-onebot](https://github.com/mario841859784/dsh-onebot/tree/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7)，package 0.9.6，提交时间 2026-10-24 UTC | 原生 TS/Cordis 插件；个人/群聊；每会话 Agent、映射恢复；正向/反向 WebSocket；出站实现能把 `private:<QQ>` 转成 `user_id`；BSD-3-Clause | **适合优先评估为通信底座**：模块划分较清楚，较少把陪伴人格与通道绑死。但当前没有通用 `qq_send_message` 文本工具，也没有把局部 `bridge` 暴露成稳定跨插件服务；接入统一陪伴器需要补小接口或维护薄分支，不能承诺“安装后随便调用即可”。 |
| [flyinstar/dsh-qq-bridge](https://github.com/flyinstar/dsh-qq-bridge/tree/8d52e45198365fc9e08918b3fb64f23a2d7dc5c2)，package 0.2.0，提交时间 2026-10-23 UTC | `qq_send_message` 全局工具明确接受 `private/group`，个人目标调用 `send_private_msg`；QQ 会话有持久 Session；MIT | **最直接的“后台 Agent 主动发普通 QQ 私聊”代码证据和原型候选**。同时包含自己的记忆、提醒、群聊节奏、私聊补话等产品逻辑；整套叠加容易与统一陪伴器重复。作者明确说明为个人自用，未保证开箱即用。 |
| [FablerTan/dsh-qq-relay](https://github.com/FablerTan/dsh-qq-relay/tree/26c00fa5aa4c1faa53aead87e15e0d67a6d90d37)，package 0.25.6，提交时间 2026-10-20 UTC | 自带环境与配置 UI，涵盖 Docker/Colima/NapCat；有主动 `qq_send`；但 `sendText(groupId, text)` 强制检查配置群白名单 | **可借鉴一站式安装、状态和诊断体验，不能当作当前已满足个人私聊的适配器。** 包元数据声明 MIT；本次树中未见独立 LICENSE 文件，复制前需补核实。 |

以上版本为所读仓库快照，不保证与 npm 或插件市场当前发布包相同。DSH 当前仍在预览期，必须把宿主版本、插件包和依赖锁一起验证；包的宽泛 peerDependencies 不能替代兼容性验收。

## 可定位的个人私聊与主动发送证据

### dsh-onebot：通道能力存在，但尚缺直接供独立陪伴插件调用的稳定端口

- [src/bridge.ts L601-L622](https://github.com/mario841859784/dsh-onebot/blob/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7/src/bridge.ts#L601)：入站找到对应聊天 Agent，使用 `agent.followup(...)`，并标明插件消息来源。
- [src/bridge.ts L499-L510](https://github.com/mario841859784/dsh-onebot/blob/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7/src/bridge.ts#L499)：存在不依赖本次入站事件的 `sendToChat(chatId,text)` / `sendSegments(chatId,segments)`。
- [src/outbound.ts L375-L392](https://github.com/mario841859784/dsh-onebot/blob/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7/src/outbound.ts#L375)：区分群目标和个人目标，后者设置 `params.user_id`，调用 OneBot `send_msg`，读取 `message_id`。
- [src/tools.ts L20-L37](https://github.com/mario841859784/dsh-onebot/blob/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7/src/tools.ts#L20)：`qq_napcat_api` 白名单不包含通用文本发送动作；不能假定借这个工具随意调用 `send_private_msg`。当前工具主要是媒体、合并转发和查询。
- [src/index.ts L471-L563](https://github.com/mario841859784/dsh-onebot/blob/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7/src/index.ts#L471) 与 [src/bridge.ts L1175-L1185](https://github.com/mario841859784/dsh-onebot/blob/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7/src/bridge.ts#L1175)：桥实例在插件闭包内创建，工具按 QQ Agent scope 注册。**Web 主会话或单独后台 Agent 不应被默认认为已有同样 QQ 工具。**
- [src/bridge.ts L400-L442](https://github.com/mario841859784/dsh-onebot/blob/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7/src/bridge.ts#L400)：启动恢复会话映射和超时补发跟踪，停用解除订阅并停止相关计时器。现有超时补发不是我们需要的所有自主消息的通用持久发件箱。

配置上的一个易踩坑：[README 私聊权限](https://github.com/mario841859784/dsh-onebot/blob/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7/README.md#L125) 中 `dmPolicy: open` 实际只允许管理员；必须填 `adminUsers`，否则默认无人能私聊。首版单主人非常适合这个边界，但命名不能按字面理解成全开放。

### flyinstar：确实有直接主动私聊工具，但别把“能发”当成完整陪伴循环

- [tools.js L29-L91](https://github.com/flyinstar/dsh-qq-bridge/blob/8d52e45198365fc9e08918b3fb64f23a2d7dc5c2/tools.js#L29)：`qq_send_message` 参数含 `target_type=private`、`target_id=<QQ>`；连接检查后调用 `send_private_msg`，逐段等待 API 返回。
- [index.js L1604-L1615](https://github.com/flyinstar/dsh-qq-bridge/blob/8d52e45198365fc9e08918b3fb64f23a2d7dc5c2/index.js#L1604)：可显式指定目标，也可由 QQ Agent 反查当前会话；支持给没有既有聊天记录的目标构造临时记录。工具公开描述可从 Web 主会话调用。这证明出站不要求先收到同一条消息。
- [onebot.js L675-L681](https://github.com/flyinstar/dsh-qq-bridge/blob/8d52e45198365fc9e08918b3fb64f23a2d7dc5c2/onebot.js#L675)：客户端检查 API 状态/返回码；但 `qq_send_message` 最终只回报目标和分段数，没有把各段 `message_id` 保留在工具结果中。API 成功也不等于人已读。
- [speaking-rules.js L54-L55](https://github.com/flyinstar/dsh-qq-bridge/blob/8d52e45198365fc9e08918b3fb64f23a2d7dc5c2/speaking-rules.js#L54)：现有空闲主动搭话规则明确只接受群聊。另有 [index.js L3171-L3226](https://github.com/flyinstar/dsh-qq-bridge/blob/8d52e45198365fc9e08918b3fb64f23a2d7dc5c2/index.js#L3171) 的私聊 `privateAfterthought`，是在正常答完后短暂补一句，不能等同于“隔一下午发现 B 站视频后自己来找主人”。后者需要自己的唤醒与决策层调用发送工具。
- `qq_send_message` 的发送路径只调用 `noteOwnMessage`；[index.js L2325-L2328](https://github.com/flyinstar/dsh-qq-bridge/blob/8d52e45198365fc9e08918b3fb64f23a2d7dc5c2/index.js#L2325) 只更新群聊记账。因此，**从另一 Agent 主动私聊后，不能据此声称接收方对应 QQ Session 自动记住了这句话。** 需要补同一会话事件或可检索的发送记录。
- 此发送工具所用 `resolveTarget` 没有像提醒工具那样进行可信用户目标判断。统一产品必须在自己的工具/发送端口固定主人或检查目标许可，不要把“工具接受任意 target_id”当成产品默认行为。

### FablerTan：主动工具是真实实现，但当前检查范围是群

[lib/controller/relay.js L725-L779](https://github.com/FablerTan/dsh-qq-relay/blob/26c00fa5aa4c1faa53aead87e15e0d67a6d90d37/lib/controller/relay.js#L725) 的主动文本方法接受 `groupId`，进入 `requireGroup` 检查配置群列表；因此 README 的主动推送、Colima 环境向导、作者群聊验收都不能推广成普通好友私聊已实现。

## 怎么接进一个 DSH 大肥鱼包

建议复用或薄分支改造通信层，并对统一陪伴模块只提供三个端口：`onInbound`（主人输入）、`wakeConversation`（进入同一持久会话做主动思考）、`sendPrivate`（明确目标和结果）。人格、记忆、兴趣、B 站事件、节律不应藏在通信适配器内部。

优先评估 dsh-onebot 作为较独立的通道底座；用 flyinstar 的文本私聊工具实现作为直接参考。如果更看重尽快做单人原型，也可以先用 flyinstar，但应关闭或替换与自己重复的记忆和主动模块。这个选择是静态结构判断，不是两者运行稳定性的排名。

仍需自己补的最小部分：

1. 后台观察/计划进入同一个 QQ 持久会话，明确区分用户发言和内部唤醒事件。
2. 发送前固定主人、检查安静时段和频率；持久化消息意图、去重键、状态、平台返回值。超时记为结果未知，避免自动盲目重发。
3. 成功发送后在同一会话可见的记录中写入真实发出文本，使用户回“你刚才发的视频不错”时能接上。
4. 设置 UI 只呈现一套人格、记忆和主动配置；通道页面呈现连接/登录/最近故障和发送结果。
5. 停用要取消定时器和订阅；重启恢复计划并抑制过期补发；迁移保存 DSH 会话、插件状态和会话映射，QQ 登录态需重新验证。

## Mac 与验收边界

DSH 和这些基于 Node 的通道代码没有要求把整个伴侣系统锁死在 Windows。NapCat 是另外的 QQ 运行端：可选择官方近期加入的 macOS 支持，或 Mac 上 Linux 容器中的 QQ + NapCat，后者更利于后续迁服务器。原生 Mac、Apple Silicon / Intel、具体 QQ 版本的已核实支持范围见 [astrbot-qq.md](./astrbot-qq.md)；其中 NapCat 结论与上层采用 DSH 还是 AstrBot 无关。

FablerTan 的 Colima 向导可以提供安装交互参考，不能证明其他桥已在当前 Mac 上跑通；dsh-onebot 的 macOS 字体支持也不能当作整链验收。Mac 睡眠、DSH 退出或 NapCat 离线期间都不能保证主动活动继续。

进入实现阶段的最小真实验收应是：普通 QQ 好友发一句话→同一 DSH 会话回复→没有新入站时主动私聊一次→用户续聊能接上→重启恢复→断线不重复补发→停用后不再主动发。本文尚未执行这些步骤。

许可证证据：[dsh-onebot BSD-3-Clause](https://github.com/mario841859784/dsh-onebot/blob/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7/LICENSE)、[flyinstar MIT](https://github.com/flyinstar/dsh-qq-bridge/blob/8d52e45198365fc9e08918b3fb64f23a2d7dc5c2/LICENSE)。复用时保留其许可与声明；NapCat 自身的许可证和分发条件需要独立处理，不能因桥是 MIT/BSD 就视为整个安装包同一许可。
