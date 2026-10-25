# DSH 大肥鱼可行性与生态调查

> 2026-10-26 增量：用户现在重点评估 DSH，AstrBot 保留候选。新核验已找到更多普通 QQ 私聊和主动发送实现，不能仅依据本文第9节的旧桥判断整个生态；见 [统一插件方案](DSH统一陪伴插件方案.md)、[官方能力核验](dsh-companion-check.md)、[普通 QQ 通道核验](dsh-personal-qq-check.md)。

调查日期：2026-10-25（Asia/Tokyo）。范围：DeepSeek Harness 官方文档、当前 GitHub 发布信息、社区插件 README 与选定源码。没有安装、执行或真实登录 QQ/B 站，因此下述“已核实”只代表文档/源码证据，不代表这台 Mac 上联调通过。

## 结论

**可以写一个统一的 DSH 大肥鱼插件，不需要先重写一套 AstrBot，也不需要修改 DSH 的 Agent 循环。** 当前 DSH 已具备模型调用、会话、工具注册、运行时上下文、持久化、定时唤醒、Web/桌面 UI 扩展等基础设施。适合把自己的工作集中在“同一只鱼的身份、记忆、节律、兴趣与发消息判断”上。

“一个安装包”与“单个大文件”无关。推荐一个 `dsh-dafeiyu` bundle，内部有清晰模块；QQ/B站通道使用适配器，记忆和人格只有一个权威存储与一套写入规则。现有社区插件值得借鉴或经许可复用，但同时安装多个独立记忆、人格和主动聊天插件，容易出现重复注入、并行写入和各自定时打扰。

对于用户最新明确的“自己的 Mac、像普通 QQ 好友私聊、主动来找我”，**DSH 本身不是阻碍，普通 QQ 账号在 Mac 上可靠接入才是优先验证项**。腾讯官方 Bot 路径与普通个人 QQ 好友并不等价；不能用“已经有官方 QQ 插件”替代这项验收。Mac 关机、宿主退出或系统睡眠期间也不能承诺继续主动活动。

## 十项重要发现

### 1. DSH 身份与许可证已明确

DSH 是 DeepSeek 官方开源的 DeepSeek Harness，底层使用 Cordis 的插件架构。官方站点明确提供 macOS Apple 芯片和 Windows 64 位桌面下载，亦支持 Node.js 下启动 Web 服务。官方仓库使用 MIT 许可证。

- [官方主页](https://www.deepseek.com/harness/)
- [官方仓库 README](https://github.com/deepseek-ai/deepseek-harness/blob/master/README.md)
- [LICENSE](https://github.com/deepseek-ai/deepseek-harness/blob/master/LICENSE)

### 2. 当前处于快速变化的预览期，版本绑定是实际开发工作

GitHub releases 接口本次返回最新发布为 `dsh-v0.2.1-rc.3`，发布时间 `2026-10-23T15:26:39Z`，`prerelease=true`。官方 README 明确预告破坏兼容性的变更。不能把社区插件名相同视为版本兼容。

已见实际兼容差异：

- `zangxx66/dsh-prompt-setting` 当前仓库 `0.2.5` 要求 DSH `>=0.2.1-0 <0.3.0-0`；README 同时写 npm latest 仍为 `0.2.2`，说明仓库版本、已发布包版本可能不同。
- `LittleBlackTong/dsh-plugin-memory` 当前仓库 `0.10.0`；README 说明其新消息格式需要 DSH 会话格式 v4（0.1.7+），0.8.0 及以前的插件消息包装在新格式中会被拒绝。
- `qwert702/dsh-memory` 仍使用官方已标记弃用的同步 `Session.snapshotEvents()`，README 明说未来需要迁移到新查询服务。

建议固定一个验证过的宿主 release 与完整依赖锁，升级时用短验收回归；不要在养鱼主环境自动追逐所有插件 main 分支。

- [DSH 最新发布](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.1-rc.3)
- [人格插件 package.json](https://github.com/zangxx66/dsh-prompt-setting/blob/main/packages/dsh-prompt-setting/package.json)
- [memory 格式边界](https://github.com/LittleBlackTong/dsh-plugin-memory#installation)
- [memory 兼容性说明](https://github.com/qwert702/dsh-memory/blob/main/README.zh.md)

### 3. 自写统一插件具有官方扩展点，通常不必 fork 宿主

官方教程展示 TypeScript 模块的 `apply(ctx)`、`inject` 依赖声明与自动资源清理。官方架构映射给出了下列扩展位置：

| 需要的能力 | 官方接口/机制 | 对鱼的作用 |
|---|---|---|
| 对话和续跑 | `ctx.agents`，Agent inbox/follow-up | QQ 输入和定时唤醒进入同一处理流程 |
| 提供外部动作 | `ctx.tools.register` | 读视频、检索经历、草拟消息等受控工具 |
| 注入相关记忆 | `agent.inject()`，system prompt 组装扩展点 | 让已验证记忆在需要时进入上下文 |
| 观察已完成对话 | `session/event` | 从持久会话事实提取候选记忆 |
| 运行任务 | `ctx.jobs` | 查看、取消和跟踪后台任务 |
| 保存产品状态 | `ctx.storageDomain` | 人格版本、记忆、兴趣、计划、待发消息 |
| 管理 UI | 客户端插件、设置/会话视图扩展 | 人类编辑、批准、纠正与追溯 |

这些是可用结构，不等于“人格”“成长”已经由宿主实现。行为逻辑仍需要自己的插件设计。

- [第一个插件](https://deepseek-harness.github.io/deepseek-harness/develop/basic/)
- [官方架构映射](https://deepseek-harness.github.io/deepseek-harness/reference/)
- [打包与安装插件](https://deepseek-harness.github.io/deepseek-harness/develop/basic/publish)

### 4. 存储与记忆是两层，DSH 提供前者但不会自动完成后者

官方存储子系统可用可读 JSON 或 SQLite，`storageDomain` 提供有 schema 的记录及变更通知。它保存的是非会话应用状态；**存储不会自动变成模型可见记忆**，检索、筛选、冲突处理、注入仍要插件负责。

这很适合统一插件拥有自己的状态域。无需为了一个私人伙伴先引入独立向量数据库。首版用明确的结构化事实、来源和全文检索更便于人工纠错；语义检索可在记忆数量增长后增加。

- [Storage 官方说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/storage/README.md)
- [storageDomain](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/storage/storage-domain/README.md)

### 5. 官方定时功能足够唤醒，但不是持续生命，也不是 QQ 推送

官方 Schedule 支持一次、间隔、每日、每周、cron，持久保存任务并在运行时恢复原会话、加入 follow-up。文档明确：

- 宿主关闭后调度停止，重启后补逾期一次性提醒或重复任务最近错过的一次。
- 发送记录表示输入已持久写入会话 inbox，不表示模型完成工作。
- 不保证恰好投递一次；部分崩溃窗口可能重复投递。
- 它本身不是外部通知渠道。

因此主动聊天还要有“决定是否值得打扰→进入发件箱→通道发送→记录真实结果”的独立流程；给每次活动/消息一个幂等键，恢复时检查重复。Mac 睡眠的运行边界是正常进程运行条件，应明确告诉用户。

- [Schedule 官方文档](https://deepseek-harness.github.io/deepseek-harness/guide/schedule)

### 6. 人格编辑插件已经存在，但它主要解决 prompt 管理

`zangxx66/dsh-prompt-setting` 支持查看组装后的 system prompt、全局与工作区自定义内容、预设库、历史 diff 和备份恢复。其当前设计把用户部分追加为独立段，内置段以只读方式呈现。

可借鉴其“看见最终注入内容”和版本回滚设计。仅编辑 prompt 不会自动产生长期经历、稳定兴趣、主动行为和变化约束。鱼的人格应拆成“人类锁定的核心人格”和“可解释变化的兴趣/状态”，后者不能随一次外部文章任意覆盖前者。

- [项目中文说明](https://github.com/zangxx66/dsh-prompt-setting/blob/main/README_zh.md)

### 7. 可管理记忆已有实现，但不同插件的数据语义差异很大

`qwert702/dsh-memory` 的 README 与选定源码相互对应：项目+全局 JSON 存储；客户端可增删改、置顶、归档、链接、撤销整理、导入导出；自动提取在 turn/end 后执行；自动注入 Top-K 记忆。源码 `lib/client.js` 包含实际 `/api/dsh-memory/add/update/remove/undo` 调用，`lib/store.js` 包含 remove 和 snapshot/restore 方法，说明不是只有 UI 宣传。

但这是工作区/全局记忆，不天然等于“每个 QQ 用户、每段关系的隔离”；真正删除也不能只看一条记录消失，历史会话、摘要、索引、备份仍可能重建旧信息，需要自己的删除与禁止重学策略。

`LittleBlackTong/dsh-plugin-memory` 采用 Markdown+Git、`SOUL.md`、原始资料、索引和时间线；迁移与人工审阅直观。注意其设置页的健康仪表盘/关系图是只读，不能把“存在图谱”说成全面编辑器；默认 `activeSessionOnly=true` 且 `deferUntilUserSpeaks=true`，与无人主动活动的专用鱼会话有行为冲突，整合时必须明确调整。

- [qwert 项目说明](https://github.com/qwert702/dsh-memory/blob/main/README.zh.md)
- [客户端 CRUD 源码](https://github.com/qwert702/dsh-memory/blob/main/lib/client.js)
- [持久存储源码](https://github.com/qwert702/dsh-memory/blob/main/lib/store.js)
- [SOUL 记忆插件](https://github.com/LittleBlackTong/dsh-plugin-memory)
- [SOUL 插件入口源码](https://github.com/LittleBlackTong/dsh-plugin-memory/blob/main/lib/index.js)

### 8. 腾讯已有 DSH QQ 插件，但不能自动满足普通好友形态

`tencent-connect/dsh-qqbot` 当前 package.json 为 `0.5.2`、MIT。它接 QQ Bot WebSocket、为每个私聊/群建独立 Agent，映射使用确定性 SessionId 并可持久恢复；提供 QQ 侧问答、审批和文件发送。桌面/Web 支持应用内扫码绑定，CLI 有终端扫码流程。

其 README 和源码说明这是 QQ Bot 通道，不是登录普通个人 QQ 账号。还需注意作者兼容性声明只列实测 DSH CLI `0.1.0-rc.8` 与 Desktop `0.2.0-rc.2`，不能自动推断最新 DSH 的每条路径已验证。

源码 `src/transport/msgid-cache.ts` 明确是被动回复目标缓存，群缓存 TTL 5 分钟、私聊 TTL 30 分钟。这是实现中的缓存参数，**不能当作腾讯全部主动消息政策的完整说明**；也足以证明“代码有出站发送”不等于“任意时刻主动找人”。真正的主动权限应由 QQ 平台当前文档与所选账号能力核查。

- [腾讯插件](https://github.com/tencent-connect/dsh-qqbot)
- [版本与作者兼容性声明](https://github.com/tencent-connect/dsh-qqbot/blob/main/package.json)
- [被动回复缓存源码](https://github.com/tencent-connect/dsh-qqbot/blob/main/src/transport/msgid-cache.ts)

### 9. 普通 QQ 的社区桥接存在，但本次未证明 Mac 开箱可用

`TomoyoNatsume/dsh-qq-bridge` 声称支持 NapCat/OneBot 和官方 QQ Bot 两路径、一次性 timer、memo、Web 会话完成通知。它当前 README 的安装要求是 Linux/WSL2；自动安装向导不支持原生 Windows，也未给出已验证的原生 Mac 路径。不能因插件是 JS 就认定底层 QQ 桥在 Mac 可用。

其“零安全风险”是项目营销表述，不能采信为实证。普通账号桥接实际需要独立核查客户端版本、操作系统/架构、重连、封禁和掉线边界。

- [QQ bridge README](https://github.com/TomoyoNatsume/dsh-qq-bridge/blob/main/README.md)

### 10. B 站养鱼插件接近目标，但作者也明确没有普适运行证明

`Alterssss/dsh-bili-whale` 当前 README 为 `0.4.6`，2026-10-25 增补扫码。它描述偏好、作息、两本日记、阅读与分享预算、沉默后降低分享，且每 60 秒由宿主 tick，通过 `sessionController.prompt` 唤醒。这个产品思路值得研究。

作者同页明确：项目起源于一个人的 Windows+DSH+微信工作流；自带测试验证逻辑，**不验证真实 DSH 版本兼容性或 B 站接口可用性**。它要求的 `sessionController/webServer/connection` 依赖与 CLI 执行能力也需要按宿主版本验收。不能直接把宣传中的“真看懂”和“自己生活”当作已运行的端到端能力。

- [B 站养鱼项目](https://github.com/Alterssss/dsh-bili-whale)
- [当前 README 完整边界](https://github.com/Alterssss/dsh-bili-whale/blob/main/README.md)

## 推荐的统一插件边界（架构建议，不是已有功能声明）

同一个 `dsh-dafeiyu` 安装包内部至少分为：

1. `identity`：核心人格版本、人类锁定项、语言示例、稳定价值与边界。
2. `memory`：经历/事实/关系/偏好四类记录，来源、可信度、有效时间、修订与删除状态。
3. `life`：兴趣、当前活动、计划、未完成话题、安静时段、活动预算和打扰预算。
4. `perception`：只把实际获得的标题、字幕、帧与评论作为观察证据；外部文字不允许改人设或下达主指令。
5. `conversation`：把 QQ 输入和自发活动放进同一个状态机；忙时可中断/排队，防止同时生成互相矛盾的回复。
6. `outbox`：去重、过期、重试、频率限制和发送确认；通道失败不写“已经联系你”。
7. `admin`：人格、记忆、活动记录、消息草稿、暂停与导出。
8. `adapters`：QQ 与 B 站。适配器只做收发/读取，不拥有第二套人格和关系记忆。

最值得先验收的纵切：用户在 QQ 提到一个兴趣→入库为有来源的候选→管理页可纠正→鱼在指定窗口独立读取 1 个 B 站视频的实际资料→形成有来源的经历→判断值得分享→在普通 QQ 好友通道主动发出→重启后不重复发→用户能追问它具体看到了什么。

应把普通 QQ/Mac 通道验证放在大量人格 UI 开发之前。若这一环不可用，需让用户在保持 Mac 主机的同时接受独立桥接运行环境，或改成官方 Bot 身份；不能默默更换用户想要的产品形态。

## 尚未验证的项目

- 常开/睡眠策略，以及普通 QQ 账号桥的本机可用性。机器硬件后来已只读确认为 Apple M4、arm64、24 GiB 内存，详见正式研究报告。
- 官方 QQ Bot 账号当前的主动发送权限与审核限制；本报告没有登录账号核查。
- DSH `0.2.1-rc.3` 与上述各插件组合的真实运行结果。
- B 站 Cookie/字幕/视觉链路在该账号和网络下的成功率。
- 记忆纠错后旧摘要、原始会话和备份是否会重新注入旧事实。
- 多日运行的成本、打扰频率、人格稳定性与用户主观活人感。

因此现阶段可以给出“技术路线可行、核心扩展点有证据、若干生态实现可借鉴”，不能给出“装这些就一定能养成”的承诺。
