# DSH 原生记忆、上下文压缩与 Token 能力核验

核验日期：2026-10-26（Asia/Tokyo）。只读官方文档与源码，未安装、启动或使用 DSH；没有模型调用、用户密钥或运行兼容性实测。

源码基线：`deepseek-ai/deepseek-harness@22ddee3792402c3e70ec5f86a63c3e3e895a2f60`，提交时间 2026-10-23T11:48:59Z。查询到的最新 release 为 [dsh-v0.2.1-rc.3](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.1-rc.3)，发布时间 2026-10-23T15:26:39Z，标记 prerelease。以下固定提交源码与文档用于静态判断，不能据此声称已验证发布包在用户 Mac 上的行为。仓库仍是 developer preview，应固定依赖版本验证升级。

## 1. 结论：保留 Harness，仅补陪伴记忆业务

DSH 已经具备持久会话、上下文测量、自动压缩、工具输出裁剪/落盘、历史读取与可选全文检索、MCP 接入和通用持久化接口。没有理由重新写 Agent 循环、会话事件日志、压缩事务或整套 Token 测量。当前官方发行组合**没有默认安装记忆服务器**；官方提供的独立长期记忆路径是可选第三方 memory MCP，并不自带适合情感陪伴的“事实版本、人工锁定、冲突裁决、来源撤销和遗忘”完整业务。见[官方 memory MCP 指南 L5–31](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/user/guide/mcp-memory.md#L5-L31)、[默认组合 L149–161](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/bundle/base/cordis.patch.yml#L149-L161)。

最重要的区分：

| 层次 | DSH 当前原生能力 | 对陪伴产品的意义 |
|---|---|---|
| 会话原始证据 | 追加式 Session 事件日志、恢复与读取 | 保留发生过什么；不是自动筛选好的个人长期记忆 |
| 当前工作上下文 | 最近消息＋压缩摘要＋当前提示与工具 | 维持本次聊天连续性；摘要可能丢细节或继承旧结论 |
| 跨会话查历史 | sessionQuery、可选 SQLite FTS5、会话引用快照 | 按需读历史；不自动等同事实抽取、语义记忆或遗忘 |
| 陪伴长期记忆 | 可接外部 memory MCP；可用通用 StorageDomain 存业务记录 | 人格、人际关系、可编辑事实、版本、锁定、撤销仍需插件定义 |

依据：[Session L12](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/core/session/README.md#L12)、[压缩 L82–84](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/README.md#L82-L84)、[查询 API](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session-query/session-query/README.md#L28-L51)、[MCP 示例边界](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/user/guide/mcp-memory.md#L46-L55)。

**推荐方向（设计建议，非已实现）：** DSH 管运行、会话与上下文；陪伴插件管理一个独立的“有效记忆视图”，按当前话题从中选少量记录，借 DSH 原有提示/工具扩展送入模型。需要考证时再用受过滤的 sessionQuery 回查来源；不要把全部聊天和全部事实每轮重复塞进 system prompt。

## 2. 官方目前如何提供长期记忆

### 2.1 官方有接入指南，没有默认 memory server

最新官方指南给了三套默认关闭的互操作示例：Memorix 1.3.0、MCP Reference Memory 2026.7.4、Engram v1.20.0，且明确这不代表背书、推荐、合作或持续支持。DSH 的通用 MCP 客户端负责启动 stdio 子进程或连接已运行的 HTTP 服务、发现并暴露工具；不负责安装服务、初始化数据库、选择 embedding/模型、云账号或迁移第三方数据。[指南 L5–21](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/user/guide/mcp-memory.md#L5-L21)

该指南直接说明发行组合不包含 memory server。其可选指令仅提醒模型需要记忆时写入、相关时检索，并不替换 DSH 的 system-prompt persona。[默认关闭 L25–33](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/user/guide/mcp-memory.md#L25-L33)、[提示边界 L66–72](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/user/guide/mcp-memory.md#L66-L72)

在本次查阅的当前服务、包目录及默认组合中，未发现一个已随发行配置启用、专门承诺个人事实更新/人工锁定/遗忘的通用原生 memory 服务。这是有范围的代码检查结论，不能扩大为“DSH 没有记忆能力”。

### 2.2 最轻量官方示例也不自动解决陪伴记忆

官方对 MCP Reference Memory 的说明：JSONL 知识图谱，实体/关系/观察/搜索/读取工具，无需 embedding 或模型；搜索是忽略大小写的子串匹配，没有自动摘要、冲突处理和遗忘策略。即便接入成功，人工锁定、事实更新优先级、误记修正、过期和来源删除仍不能视为已解决。[指南 L46–55](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/user/guide/mcp-memory.md#L46-L55)

官方验证要求跨两个新会话进行“写入 → 召回 → 实际使用”，不是在同一会话复述。这可直接继承为后续验收的一项。[指南 L74–82](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/user/guide/mcp-memory.md#L74-L82)

## 3. 原生 Session 的“存”和“清理”

默认 base 挂载 JSONL Session 后端。当前后端默认使用带校验的 Zstandard 帧保存追加式事件；可以在新根目录选 `compression: none`。压缩编码是磁盘存储压缩，与模型上下文摘要是两件事。历史格式迁移创建新的代文件并保留旧代；已提交事件不被改写。[后端说明 L12、48、57–87](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session/session-persistence-jsonl/README.md#L12-L87)

**没有自动会话日志清理或删除 API。** 官方明确日志一直累积到外部移除。不能把 UI 归档、上下文 compact、FTS 索引重建当成擦除原始会话。运行时外部删文件也不是已验证安全的清理方案；需要先验证 live handle、恢复和索引协调。[限制 L164–169](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session/session-persistence-jsonl/README.md#L164-L169)

生命周期清理应分开：

| 对象 | 原生实际语义 | 插件清理时的注意点 |
|---|---|---|
| 模型当前上下文 | compact 替换可见范围，原事件留日志 | 节省 Token，不是物理删除 |
| Session JSONL 与旧代 | 保留完整事件与历史格式代 | 需独立保留期限/导出/删除流程；当前 seam 无删除 API |
| sessionQuery SQLite | 可重建的派生索引 | 删索引不删来源；下一次检索可重建 |
| Spill 工具输出/引用文件 | 完整长输出外置文件；默认有清理政策 | 不能当永久长期记忆；失效后引用可能打不开 |
| 人格/事实/关系记录 | 通用业务存储可提供 CRUD | 删除事实不会自动改写 Session 摘要、引用快照或备份 |

依据：[压缩原件保留](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction/README.md#L95-L97)、[检索索引派生与更新](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session-query/session-query-sqlite/README.md#L87-L104)、[Spill 存储及清理](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/spill/spill-local/README.md#L32-L59)。

Spill-local 默认使用私有的进程级临时目录；`cleanupPeriodDays` 默认 30，可配置 0 关闭；只有启动时一次尽力清理，不是长期运行中的定时清扫。因此外置结果的目录、保留期和失效提示应明确配置，不能只展示“已经记住”。[Spill-local L32–59、L126](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/spill/spill-local/README.md#L32-L59)

## 4. DSH 已有的省 Token 链路

### 4.1 不调用模型的削减

1. **Spill policy：** 太长的工具结果保存全文，模型先看头尾与读取地址；默认 base 的 `maxInlineTokens` 为 12,500。它减少立即进入上下文的体积，不等于总结或永久记忆。失败时保留原结果，不伪造成功。[策略](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/spill/spill-policy/README.md#L28-L65)、[base L408–413](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/bundle/base/cordis.patch.yml#L408-L413)
2. **工具结果裁剪：** 在压缩压力触发时裁剪合格文本的中段，默认阈值 8,192 字符、头 4,096、尾 1,024；不是每条输出都会裁剪，也不是按语义挑重点。原件仍保留在日志。[规则](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-tool-result-pruner/README.md#L40-L60)
3. **图像卸载：** 特定压缩失败路径可把旧图像替换为可重新读取的引用，减少视觉上下文；不会删除原附件。[图像卸载](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-image-offload/README.md#L38-L84)

B 站读取工具适合先返回“标题、来源、简短摘要、可追溯地址”，按需读详细内容；这一业务裁剪可与原生 Spill 配合，不需要另做 Harness。

### 4.2 原生摘要压缩

默认 base 已挂载 `token-meter`、`compaction-basic` 和人工 `/compact`。自动压缩会在模型请求前测量压力，先做裁剪，再用额外模型调用概括旧的安全范围，保留最近原文；遇模型确认为上下文超限时，还有有界的压缩恢复路径。[base L348–357](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/bundle/base/cordis.patch.yml#L348-L357)、[自动流程 L119–135](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/README.md#L119-L135)

阈值不能只说“80% 自动压缩”。当前公式为：

```text
W = 模型上下文窗口
O = 此次请求有效输出上限（预留，不是已花掉的 Token）
B = headroomTokens，默认 65,536
触发阈值 = floor(min(W × 0.8, W − O − B))
最近原文默认保留 = 16% × (W − O)
```

可按 provider/model 覆盖阈值、余量、保留量和摘要模型；小窗口必须调整默认余量，满足 `W−O−B>0`，否则不能假设开箱配置可用。`maxTokens` 默认跟随 headroom，是摘要输出上限，不代表每次必消耗 65,536。[配置与公式 L62–80](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/README.md#L62-L80)

摘要会减少后续输入 Token，却要支付一次额外摘要调用，并从替换位置失去相应前缀缓存。压缩得越频繁不一定越便宜。原生正文也说明一个不可拆分的大块仍可能超限。[Token/缓存影响 L184–190](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/README.md#L184-L190)

### 4.3 情感陪伴最值得适配的原生点：摘要模板

**新发现：默认摘要模板明显服务于编程。** 源码要求 coding assistant、英文工程语言，并固定技术概念、文件代码、错误修复、待办等章节；其中虽包含用户偏好与纠正，却不能据此证明长期陪伴的情绪转折、关系变化、共享经历会被合适保留。[模板源码 L32–71](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/src/summarizer.ts#L32-L71)

**不必为此重写压缩器。** 当前 `BasicCompactionEngine` 明确将受保护的 `summarize()` 作为唯一子类定制钩子，而回放、持久替换和统一 Token 测量策略保留。可先评估默认模板；必要时在陪伴 profile 中使用只定制摘要表达的派生后端，继承范围选取、锁、事务、恢复与预算行为。没有发现可直接在配置中填写自定义摘要 prompt 的字段，因此“改一项配置即可换模板”不应当成已支持。[扩展点 L104–113](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/src/index.ts#L104-L113)、[方法 L270–279](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/src/index.ts#L270-L279)

该方案是源码支持下的可行设计推断，尚未验证包导出、实例替换和发布包兼容性。摘要也仍是有损的当前工作上下文，不应承担唯一长期事实数据库。

## 5. 已有跨会话历史能力，不必重造聊天记录搜索

`ctx.sessionQuery` 已提供 list/read/filter/trace/search 等接口；纯读取与字面过滤不要求开启全文索引。其 SQLite 实现提供 FTS5 派生索引。**包自身 `openAt` 默认 startup，但官方 base 明确覆盖为 `never`、path 为 `:memory:`**：开箱全文搜索关闭，精确读取和追溯仍可用；Web 搜索默认只匹配标题和工作区名。[查询 API](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session-query/session-query/README.md#L28-L51)、[包配置](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session-query/session-query-sqlite/README.md#L43-L53)、[base 精确配置](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/bundle/base/cordis.patch.yml#L149-L161)

开启全文查询后：

- 默认搜索 `current`、`shadowed`、`log-only` 全部事件；应按用途明确过滤。
- 是 unicode61 的字面词/短语检索，排序由匹配跨度等确定，不能称为 embedding 语义召回，也不能未经测评保证中文口语效果。
- FTS 索引是可丢弃派生数据；会在后续搜索协调来源改变和删除。
- service 本身是可信上下文的能力，不自动提供陪伴对象、事实版本或撤销语义。

依据：[搜索默认条件 L57–67](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session-query/session-query-sqlite/README.md#L57-L67)、[索引生命周期 L87–104](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session-query/session-query-sqlite/README.md#L87-L104)、[调用方边界 L143](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session-query/session-query-sqlite/README.md#L143)。

另有实验性 `tool-session-query`，提供五个模型工具（会话搜索、事件搜索、两种追溯、精读事件），需显式启用，工具 schema 本身每次请求也占 Token。其跨会话边界采用相同 cwd 等条件，不是用户关系记忆的授权/版本边界；精读结果需配合通用 Spill。可以复用其底层，但不应将原始工具无条件暴露成“查回一切”。[实验工具 L12、47–57](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/experimental/tool-session-query/README.md#L47-L57)

原生 `session-reference` 则把明确提及的其他会话转为有界、标记不可信的快照；**快照不是活链接**，来源更正不会自动修改已经插入目标会话的内容。它适合“参考那次聊天”，不适合作为唯一可更新事实源。[引用 Token 与限制 L115–137](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/context/session-reference/README.md#L115-L137)

## 6. 人工修改/删除会不会被旧摘要“复活”

**会存在这种路径；这是由数据结构推得的风险，不是本次运行复现。** 原生 compact 不删除原文；原生查询默认包含被压缩的历史；引用快照不会同步来源修改；默认摘要模板又会把 prior checkpoint 的仍有效信息合入新摘要。“事实库删了一条”无法自动处理这些独立副本。[原文保留](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction/README.md#L95-L97)、[默认搜索](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session-query/session-query-sqlite/README.md#L59)、[快照不联动](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/context/session-reference/README.md#L136)、[摘要合并规则](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/src/summarizer.ts#L63-L71)

需要区分三种产品操作：

1. **修订：** 旧偏好/旧事实失效，新版本成为当前值；保留变更轨迹但模型召回只能使用当前有效版本。
2. **遗忘：** 不再用于对话、摘要和回忆；应保存最小撤销标记，阻止后来从旧聊天或 B 站资料重新抽取。
3. **物理擦除：** 清掉原始日志、摘要副本、引用、Spill、索引、导出和备份；目前 DSH Session seam 无现成“一键彻底擦除”接口，范围与执行顺序要专门验证。

这些是插件应实现的业务语义，不是声称原生已有。较小实现至少需要：稳定 memory ID、版本、有效状态、来源 Session/seq、人工锁、撤销记录；所有模型可见的召回路径先过当前有效性检查。单纯追加“用户纠正了”提示，或者只加 `surface=current`，都不能证明旧摘要中的值已消失。

对“当前会话已带有旧摘要”的更正，需要明确新事实优先级，并验证是否通过原生可见表面/提示更新接口更新上下文，或切换到带新事实的会话；不能承诺仅改数据库 UI 就即时覆盖模型已看过的内容。

## 7. 通用存储可复用，但没有完整记忆数据库语义

`StorageDomain` 提供校验、内存状态、单域串行变更和持久化、put/update/delete/deleteMany；可接 JSON 或 SQLite。它不自动注入模型上下文，因此适合放插件自己的事实、设置和撤销状态。[StorageDomain 运行契约](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/storage/storage-domain/README.md#L73-L90)

需要纠正“有 SQLite 就有完整事务层”的误读：

- Domain 无跨表事务、二级索引或多段键；
- 无自动数据迁移，已存版本不同会拒绝打开；
- 变更通知限同一进程；
- SQLite 后端按记录存 JSON，单条与规定批量删除具原子性，不等于任意跨业务表事务；
- JSON 单文档与多文档模式的崩溃语义不同，多文件批删存在断电后恢复旧文档等限制。

依据：[Domain 限制 L144–148](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/storage/storage-domain/README.md#L144-L148)、[SQLite 原子边界](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/storage/storage-sqlite/README.md#L57-L72)、[JSON 落盘与限制](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/storage/storage-json/README.md#L72-L74)、[JSON 批删限制 L143](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/storage/storage-json/README.md#L143)。

**设计判断：** 如果将“当前事实＋版本＋锁＋撤销”组织为同一个可原子更新的业务聚合，原生 Domain 可能足够；若来源级撤销必须同时更新多张关系表、搜索索引及版本，需单独设计事务/重建策略或使用插件自有数据库。先验证所需一致性，不应为了“继承 Harness”而误用不具备的事务能力，也不应默认把所有存储重新实现。

小量稳定的人工规则还可复用 `agent-instructions` 读取的用户/项目 AGENTS 等文件，但它不是持续文件监听，也不会默认把任意 MEMORY.md 自动当长期记忆；外部修改通常要等结构化文件访问、恢复等时机刷新。它不适合承诺 UI 修改立刻生效的事实库。[行为 L30–38](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/context/agent-instructions/README.md#L30-L38)、[更新限制 L222–228](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/context/agent-instructions/README.md#L222-L228)

## 8. Token 统计与剩余上下文：能复用什么，不能误报什么

DSH 已有统一 `ctx.tokenMeter`：模型容量由适配器提供；`measure()` 测量当前请求压力；`contextPressure` 投影携带最新 provider prompt 用量、预计下次 prompt 大小和窗口；`contextBreakdown` 分系统/工具/消息；`tokenUsage` 给输入、输出、cache read/write 等统计。[API 与投影 L28–55](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/llm/token-meter/README.md#L28-L55)

展示时至少分清：

| 指标 | 可用信息 | 正确表达 |
|---|---|---|
| 上一次实际 prompt | provider usage | 已报告值；没有就未知 |
| 下一次预计 prompt | projectedTokens/measure | 估算，会随上下文变化 |
| 窗口余额 | 窗口 − 预计 prompt | 仅供参考；还需预留输出和压缩余量 |
| 系统/工具/消息构成 | heuristic breakdown | 近似构成，不要求加总等于 provider 账单 |
| 总成本 | 各模型调用实际 usage × 对应价格 | 需含摘要等辅助调用，不能只读一次会话投影 |

文本回退估计约四字符一 Token，官方承认中文与 JSON schema 可能明显低估；工具、模型、请求配置变化会使 provider anchor 不可复用。system prompt 改写后，`projectedTokens` 的该替换增量可能直到下一次 usage 才体现，`measure()` 和构成会即时重算。因此 UI 必须标估算/时间点，不能把未知显示成 0。[估计限制 L143–159](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/llm/token-meter/README.md#L143-L159)

**新发现：原生 `tokenUsage` 投影不能直接当“这条鱼全部开销”。** 源码只累计 `assistant/message` / `assistant/attempt`；而摘要调用 usage 保存在 `compaction/summary` 上，随后插入的是 user 替换消息，所以该投影不累计这笔摘要调用。压缩调用本身使用原生 `ctx.llm.stream()` 并带 `purpose: compaction`；插件可复用该记录补充总账，不需要另写模型调用层。[usageOf L82–85](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/llm/token-meter/src/usage-projection.ts#L82-L85)、[投影过滤 L111–124](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/llm/token-meter/src/usage-projection.ts#L111-L124)、[摘要 usage 记录 L491–508](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/src/region.ts#L491-L508)、[原生摘要调用](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/compaction/compaction-basic/README.md#L129)。

后续陪伴插件若增加记忆抽取、重排、整理等模型调用，应单独记录用途和 usage；这一点是业务成本账本补充，不是替代 DSH Token 测量。尚未核验每个潜在辅助功能的全部计费路径，不能笼统声称全部都遗漏或全部都已计入。

## 9. 官方公开规划：只能说“提案”，不能说“即将上线”

官方仓库保留一份 **Status: proposed** 的“Recallable compaction”说明，提出把旧历史变成冻结索引检查点，另有可变工作状态，再增加 history_read/history_search 读取被摘要遮住的原文；设想中的包名为 `dsh-tool-recall` 和 `dsh-compact-recallable`。[状态 L1–3](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/.agents/notes/proposed/feature/2026-07-06-recallable-compaction.md#L1-L3)、[方案 L19–57](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/.agents/notes/proposed/feature/2026-07-06-recallable-compaction.md#L19-L57)

本次固定版本包目录与 base 仍是 basic 路线，未见上述两个提案包；“跨会话召回、语义搜索 fallback”等也被列为需独立证据的后续项。未找到可据此承诺的发布日期、稳定 API 或情感陪伴长期记忆路线图。[后续边界 L66–77](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/.agents/notes/proposed/feature/2026-07-06-recallable-compaction.md#L66-L77)

特别注意：该提案背景中“没有工具读回被遮住历史”的历史表述，不能直接当当前代码事实；当前版本已存在通用 sessionQuery 与实验查询工具。**尚未落地的是该提案的特定检查点/召回组合，不是所有历史读取能力。**

## 10. 应交给技术探针的未知，不需要让用户替工程实现做选择

1. 固定发布包是否导出并支持继承 `BasicCompactionEngine`，如何在专用陪伴 profile 替换该 provider；验证不丢原生范围、锁、恢复和预算能力。
2. 中文长聊压力测量误差、默认摘要对关系事件与人类纠正的保真度；比较原生模板与仅覆盖 summarize 的模板。
3. “修改/锁定/撤销 → 当前会话 → 压缩 → 新会话 → 重启”链路，验证旧摘要、FTS 和引用不会重新提取失效事实。
4. Domain 单业务聚合是否满足版本＋锁＋来源撤销的一致性；若不满足，比较自有 SQLite 的小范围事务层，而不是重写整个 Harness。
5. Native session-query 的中文口语召回、跨会话过滤与返回 Token 上限；先验证字面检索基线，再决定是否需要额外向量库。
6. 汇总普通回复＋失败重试＋compaction/summary＋插件记忆抽取的实际 usage，与 provider 账单比对，分清 cache 桶。
7. 日志、历史代、Spill、引用和派生索引的保留/物理清理演练；验证删除时 live handles 和重启恢复，不直接删用户原数据。
8. 新会话召回验收沿用官方三步法，并额外测试“人类修订后的值”和“已撤销的来源”。

这些属于可验证的工程未知。此报告没有把静态支持、文档示例、拟议功能或设计建议当成运行通过。
