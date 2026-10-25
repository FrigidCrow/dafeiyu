# NapCat v4.18.41 官方发布包：人工静态调用链

调查日期：2026-10-25。仅用本地文本检索、行号阅读、SHA-256 与 `file` 格式识别；未执行目标、加载原生模块、安装依赖、登录 QQ 或发送消息。REA 的实际运行证据由主任务单独保存，不将本文冒充 REA 输出。

## 样本身份

根目录：`/Users/frigidcrow/Documents/dafeiyu/research/artifacts/napcat-v4.18.41/extracted/`

| 文件 | SHA-256 |
|---|---|
| 官方发布 ZIP（主任务已核） | `6801f93e533846cea05f4f531874a0e84371ab2331c5585b57cd7e3b869cf96b` |
| `napcat.mjs`（本次实算） | `7c66d0239d7effe73ab6e4920eddef732a8066fb47cd19539541c72055c5f0aa` |
| `loadNapCat.js`（本次实算） | `3d272756b14175c1e603261da6d8180e69f3435cbbd73baaf0542ea52f12330f` |
| `package.json`（本次实算） | `abce2924f10c57cbd55fed0b2e59f6ffde6fd9d27b1ea7ebac26e77fa973c4c7` |

`napcat.mjs` 共 83,725 行。下文行号只对上述精确摘要样本有效。包内 `package.json` 的 version 是工作区占位 `0.0.1`，不能据此否定 release 版本；实际 bundle 第 8389 行嵌入 `4.18.41`。

## 入口与分层

- [`loadNapCat.js:3`](/Users/frigidcrow/Documents/dafeiyu/research/artifacts/napcat-v4.18.41/extracted/loadNapCat.js:3)：选择 `NAPCAT_MAIN_PATH` 或同目录 `napcat.mjs`；第 5 行动态 import。**这是执行入口，不能当无副作用库直接 import。**
- [`napcat.mjs:83720`](/Users/frigidcrow/Documents/dafeiyu/research/artifacts/napcat-v4.18.41/extracted/napcat.mjs:83720)：顶层调用 `y2e()`；该函数根据多进程/worker 配置进入主进程或 `FL()`。
- [`napcat.mjs:83304`](/Users/frigidcrow/Documents/dafeiyu/research/artifacts/napcat-v4.18.41/extracted/napcat.mjs:83304)：`FL()` 初始化路径、QQ 版本、native wrapper、登录与会话。第 83331 行使用 `NodeIQQNTWrapperEngine` / `NodeIKernelLoginService`。
- [`napcat.mjs:83406`](/Users/frigidcrow/Documents/dafeiyu/research/artifacts/napcat-v4.18.41/extracted/napcat.mjs:83406)：`InitNapCat()` 初始化 core，再 `initAdapters()`；桥接与消息业务位于登录层之上。
- [`napcat.mjs:81571`](/Users/frigidcrow/Documents/dafeiyu/research/artifacts/napcat-v4.18.41/extracted/napcat.mjs:81571)：OneBot context（发布包压缩类名 `_Ae`）聚合 `MsgApi`、action registry、networkManager。第 81590 行构造 registry 与网络管理器。

## QQ 接收 → OneBot 输出

| 顺序 | 样本行号与短语 | 静态观察 |
|---|---|---|
| 1 | 81725 `e.onRecvMsg = async (n)` | QQ 内核消息回调；只有存在活跃 adapter 时处理 |
| 2 | 81728 `this.bootTime > parseInt(r.msgTime)` | 忽略早于本次启动时间的消息；不能据此承诺离线消息全部补齐 |
| 3 | 81732 `nt.createUniqueMsgId` | 将 QQ 消息标识映射为 OneBot 使用的 ID |
| 4 | 81800 `getMsgService().addKernelMsgListener(...)` | 注册上面的接收监听器到 QQ wrapper session 的消息服务 |
| 5 | 81888 `async emitMsg(e)` | 同时处理普通消息转换与私聊/群事件 |
| 6 | 81897 `this.apis.MsgApi.parseMessageV2(...)` | 调用 OneBot 消息转换 |
| 7 | 74291 `async parseMessageV2(...)` | 补齐 UID/UIN、按私聊/群聊分派、解析消息段 |
| 8 | 74314 `initializeMessage(e)` | 生成 `self_id/user_id/message_id/message_type/sender/message`；74334 区分 `message` 与自身 `message_sent` |
| 9 | 81905 遍历 `networkManager.adapters` | 根据 adapter 的 string/array 格式和 `reportSelfMessage` 策略选事件 |
| 10 | 81917 `emitEventByNames(i)` | 按 adapter 名派发已转换事件 |
| 11 | 65272 `async emitEventByNames(e)` | 活跃 adapter 执行 `onEvent` |
| 12 | 64584 WebSocket client `onEvent(e)` | `connection.send(JSON.stringify(e))` 把 OneBot JSON 发往连接端 |

反向 WebSocket 的连接建立位于 64611 `tryConnect()`：设置 `X-Self-ID`、Bearer token、`User-Agent: OneBot/11`，连向配置 URL；64634 收到服务端请求后进入 `handleMessage`。已有重连计时逻辑，但本次没有实测其恢复效果。

因此 AstrBot 这类宿主的接入点是**已标准化的 OneBot 事件**，不用自己从 QQ 内核解析会话、图片、UID 或消息段。

## OneBot `send_private_msg` → QQ 发送

| 顺序 | 样本行号与短语 | 静态观察 |
|---|---|---|
| 1 | 33146 `SendPrivateMsg: "send_private_msg"` | OneBot action 名常量 |
| 2 | 64650 WebSocket client `handleMessage(e)` | 解析 `action/params/echo`；64659 按 `actions.get(n.action)` 分派 |
| 3 | 64664 `i.websocketHandle(...)` | 进入统一 action 包装器；结果通过 echo 回传 |
| 4 | 81363 `new I1e(t,e)`；81476 `mAe` | 私聊发送 handler 注册进入 action map |
| 5 | 33391 `async websocketHandle(...)` | 执行 `check` 和 `_handle`，返回 OneBot 成功或错误结构 |
| 6 | 75636 `class I1e extends Dy` | 私聊 handler；75649 强制 `message_type="private"`，75652 调用 `base_handle(..., la.Private)` |
| 7 | 74761 `async base_handle(...)` | 通用发送链；74763 用 `J2()` 定位 peer，74767 解析 OneBot 消息内容 |
| 8 | 74702 `J2(...)` | UIN/UID 与好友/临时会话/群信息转换；不需要新建一套身份寻址 |
| 9 | 74791 `createSendElements(i,r)` | 将 OneBot message segments 转为 QQ raw elements |
| 10 | 74792 `sendMsgWithOb11UniqueId(...)` | 调用桥接消息 API，并向调用方返回 `message_id` |
| 11 | 74406 `async sendMsgWithOb11UniqueId` | 检查空消息、计算超时，74431 调 `core.apis.MsgApi.sendMsg`，成功后产生 OneBot ID |
| 12 | 10800 `async sendMsg(...)` | 核心 QQ 发送；10808 目标 `NodeIKernelMsgService/sendMsg` |
| 13 | 26527 `callNormalEventV2(...)` | 调用原生服务并等待匹配 listener；26551 执行 `createEventFunction(e)(...r)` |
| 14 | 26478 `createEventFunction(e)` | 将 `NodeIKernelMsgService/sendMsg` 映射到 `WrapperSession.getMsgService().sendMsg` |
| 15 | 10809 `NodeIKernelMsgListener/onMsgInfoListUpdate` | 成功判定等待同一生成标识且 `KSEND_STATUS_SUCCESS`，不是发起调用即认定发送成功 |

这条 action 输入例子仅需要目标 `user_id` 和 `message`，不是要求附上近期一条来信的 `msg_id`。**可以推断它在桥接接口层支持主动发送形态**；但是否能在特定账号、客户端版本、风控状态下发送成功仍要登录后验证，不能由静态链推出无限制主动消息能力。

普通 WebSocket server 路径在 65219 `handleMessage`，同样分派 action registry。可复用现成宿主的一条正确接入路径，无需同时启用全部 HTTP/WebSocket 方案。

## 外部模块与操作系统边界

- JS 文件开头静态依赖主要为 Node built-ins，外部 JS 包为第 43 行 `express`、第 48 行 `ws`，以及第 52 行同目录 `conout-wiJ7YKRd.js`。`package.json` 也声明 express/ws；该发布 bundle 已内嵌许多其他实现，不能只根据两个依赖推断整个项目只有两项依赖。
- 第 32887 行 `vse()` 寻找 QQ 的 `wrapper.node`；第 32878 行 `process.dlopen` 才加载它。**真正的 QQ 服务跨入原生模块边界，静态 JS 本身不等于独立 QQ 协议实现。**
- 第 32893 行包含 macOS `../Resources/app/wrapper.node` 路径；第 32817 行处理 `QQ Helper` → 主 `QQ` 路径。
- 第 82577 / 82732 行原生组件平台列表含 `darwin.x64` 与 `darwin.arm64`；本发布包实际携带：
  - `native/packet/MoeHoo.darwin.arm64.node`
  - `native/napi2native/napi2native.darwin.arm64.node`
  - 对应 darwin.x64 文件和 `ffmpegAddon.darwin.*.node`
- 本次只读 `file` 检查前两个 arm64 文件，均显示 `Mach-O 64-bit dynamically linked shared library arm64`。这比“代码里出现 darwin 字样”更强，但依然不是加载/登录/收发验证。
- 第 33494 行给出 Mac 默认状态目录 `~/Library/Application Support/QQ/NapCat`。一站式产品应显式管理配置路径与生命周期，不应混淆人格数据库和 QQ 客户端状态。
- 目录中存在 Windows launcher；本次限定调查未核到完整 Mac launcher/安装步骤。不因已有 Mac 原生部件就宣称一键安装已经成立。

## 对一站式大肥鱼设计的意义

**无需修改 QQ 协议层。** 保留 NapCat 作为可替换的收发进程，把 AstrBot 或独立宿主作为消息与模型运行层，再让一个统一大肥鱼模块负责人格、记忆、主动活动和管理界面。用户只看到一个产品入口；内部进程分层保留，便于更新和排错。

统一产品需要补齐的主要是：首次配置与登录状态展示、宿主/桥接健康检查、通道凭据、重连状态、发送结果追踪，以及人格/记忆/活动规则的唯一存储。不能把 NapCat 自带 `send_private_msg` 当作完整“活人感”；“什么时候找用户、说什么、从何种真实经历而来、是否打扰、怎么记住后续回应”在上层实现。

验收时应单独测试：普通好友来信→OneBot事件→人格回复→发送成功；无来信条件下主动发送；断开桥接后重连；宿主重启后的消息去重；Mac 睡眠恢复。当前笔记只证明可定位静态调用链和发布部件存在。
