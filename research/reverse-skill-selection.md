# REA 选型与静态使用审查

调查日期：2026-10-25（Asia/Tokyo）。用户已确认所指为 REA / Reverse Engineer Anything，停止泛候选比较。本文件记录执行前的只读审查；其后主任务已安装项目内skill并运行REA，实际结果见[实验结果](rea/实验结果.md)。审查本身未执行 NapCat 或 QQ。

## 结论与正确用途

官方项目是 **[morluto/rea](https://github.com/morluto/rea)**，官方站点 **[rea.tools](https://rea.tools/)**，npm 包 **`rea-agents`**。README 明确警告不要根据同名仓库或复制 README 判断来源。

REA 的 skill 明确写：`Skip REA for ordinary source-repository architecture analysis.` 完整的 AstrBot Python 源码和 NapCat TypeScript 源码应主要用源码检索、调用链和数据流分析。

但用户已提出“用 REA 试试”，**对 NapCat 官方 release 中实际发布的 JavaScript 包做静态分析**是合理、匹配的任务：核实打包后入口、依赖、路由/IPC/API 关系，再对照开源源码。它不会自动把几个项目整合成一站式产品；整合仍要做状态归属、扩展接口和产品流程设计。

## 已核实版本与固定入口

| 项目 | 本次核实结果 |
|---|---|
| npm registry `latest` | `rea-agents@6.8.0` |
| GitHub release | [`rea-agents-6.8.0`](https://github.com/morluto/rea/releases/tag/rea-agents-6.8.0)，2026-10-25 08:36:02 UTC，非 prerelease |
| release 对应 commit | `160d821ac9a0310afcb8d1fc427862dd6508add5` |
| 查询时 main commit | `25f0f9934d226caa62fb89d68e7bacad74f4fe73`，比 release 更新，不应混用 |
| 匹配 skill 目录 | `.agents/skills/reverse-engineer-anything` |
| 匹配 SKILL.md | [固定 release 入口](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/.agents/skills/reverse-engineer-anything/SKILL.md) |
| skill 元数据版本 | `49`；同版本号的 main 文件字节已不同，所以固定 commit 比只看 version 更可靠 |
| 许可证 | [MIT，copyright morluto 2026](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/LICENSE) |
| Node 要求 | `^22.23.4 || ^24.22.1 || >=26.12.1` |

npm registry 提供的 tarball：`https://registry.npmjs.org/rea-agents/-/rea-agents-6.8.0.tgz`

Registry 完整性摘要：

```text
sha512-9QDeRnGqEDzABZyr04eLnBXBv/c6I9/TWu/6M0MD4pEfkySI/BIgwTODIbAReX3C1x6hjw9+Jlx4A2yUSPZ9ww==
sha1: 6a2cc197e4ff7f11ba937125b3ca7e4de939906a
```

本次只读取了摘要，尚未下载 tarball 做字节比对。Registry 不提供该包的 `gitHead`；release commit 来自 GitHub tag ref，不能仅凭两者版本号相同就声称已做源包逐文件一致性核验。

## Skill 内容和安装范围

固定目录只有 `SKILL.md` 和 `references/` Markdown 指南；没有独立可执行脚本。references 包括：

- `android-applications.md`
- `connection-and-recovery.md`
- `environments.md`
- `evidence-workflows.md`
- `javascript-applications.md`
- `native-and-artifacts.md`
- `runtime-observation.md`

本次重点阅读 SKILL、JavaScript、connection/recovery、安装与 CLI 文档、package.json、prepare 脚本和 JS effect 验证记录；不是对所有 REA 功能、所有依赖的完整安全审计。

只复制这个 skill 目录仅安装指令；不会注册 MCP、不会添加当前会话工具、不会安装 Hopper/Ghidra 等引擎。固定目录安装可由既有 skill-installer 使用上述 repo/ref/path 完成。可附带根目录 LICENSE 保留许可。

`rea setup` 与 skill-only 是不同动作：setup 会提出修改 agent 配置、备份和 skill 目标目录，并可选安装 Hopper。**本任务一次性 CLI 静态分析不需要 setup，不需要改 Codex MCP 配置，也不需要重启聊天。**

## 推荐首个实验

先确认使用满足版本要求的现有 Node；对实际 release ZIP 解包后的目录运行，不把单个 `.js` 文件误当 native 目标：

```bash
npx -y rea-agents@6.8.0 analyze-javascript-application /绝对路径/NapCat发布包目录 --json > /绝对路径/napcat-rea-evidence.json
```

这是官方 CLI 文档同款命令，仅把 `latest` 固定为已核发行版本。真正运行时应把中文占位路径替换为真实已获得路径。

如果发布包很大，先列清目录，然后精准选择相关文件：

```bash
npx -y rea-agents@6.8.0 analyze-javascript-application /绝对路径/NapCat发布包目录 \
  --source-path package.json --source-path 实际入口.js --json > /绝对路径/napcat-rea-evidence.json
```

`--source-path` 必须是已确认的包内相对路径；不支持 glob，依赖不会自动扩大选择范围。REA 仍对整体目录做 inventory，但只读取/分析选中的源码文件；未选择的关系保持未知。若包没有 `package.json`，不要编造文件。

完整 Evidence 可能达到数百 MB，应保存文件后读摘要，避免直接把完整图打印进聊天。创建请求 JSON：

```json
{"source":{"kind":"evidence-file","path":"/绝对路径/napcat-rea-evidence.json"},"view":{"kind":"summary"}}
```

然后调用：

```bash
npx -y rea-agents@6.8.0 inspect-analysis-view /绝对路径/view-request.json --json
```

需要分页时将 view 换为 `{"kind":"page","collection":"modules","offset":0,"limit":32}`。官方文档还支持 `trace-application-feature` 等后续路线，应基于真实返回的 module/node ID 生成请求，不猜 ID。

**资源边界：**skill 的 JS 指南说明单源静态分析默认 deadline 300000ms、old-space heap 1024MiB。`detail:summary` 只减少交付输出，不减少计算；真正缩小工作量要 `source_paths`。具体 CLI 资源 flag 需读取所安装版本的 `--help`，不要猜拼写。

## 执行、安装与网络副作用审查

| 操作 | 实际影响和边界 |
|---|---|
| 复制 skill Markdown | 写入选定 skill 目录；不会安装执行引擎或注册 MCP |
| `npx ...` | npm 可能联网下载 REA 和依赖、写 npm cache，并执行 REA；不是“完全只读文件” |
| `analyze-javascript-application` | 文档与官方 effect 记录说明不执行目标应用；会创建私有运行目录、暂存 `.source` 文件并启动 REA 自己的分析 worker |
| CLI JSON 输出 | 写用户选定 Evidence 文件；静态发现不能证明 QQ 登录、发送、重连实际成功 |
| `rea setup` | 会修改被选中的 agent 配置与 skill 目录；不在这次 CLI 实验所需范围 |
| native/runtime/browser 命令 | 部分会启动、附加或操作目标；不是本次 NapCat 静态实验的必要动作 |

package.json 没有 `preinstall/install/postinstall` 脚本；有 `prepare`（源码存在且相应开发依赖可用时处理 release-please/Husky）和 `prepublishOnly`。该判断只覆盖 REA 自身 manifest，**没有逐一审计全部 npm 依赖安装生命周期**。本次命令不需要对 NapCat 目录运行 npm install、构建、启动、扫码或加载原生 `.node` 文件。

README 声称分析在本地进行，分析结果交给当前 agent，其模型提供方有自己的数据策略；不能把“本地分析”写成“所有输出永不离开电脑”。本次检查未发现静态 JS 路线要求上传目标文件；完整依赖与所有网络路径没有在本子任务做穷举审计。

## 首个实验应交付的证据

1. NapCat 官方 release 标签、下载来源、ZIP SHA-256、解包目录和选中的文件。
2. REA `6.8.0`、Node 版本、完整命令、真实 exit code 与标准错误进度/失败记录。
3. Evidence 身份、artifact digest、模块图摘要、覆盖率与所有 unknown/limit。
4. 从 QQ 接收入口到 OneBot 事件输出、从 OneBot `send_private_msg` 到 QQ 发送层的静态证据；二者是否覆盖要由结果决定。
5. 明确本次没有运行 QQ/NapCat，也没有证明原生 Mac 账号接入。

## 主要依据

- [官方 README](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/README.md)
- [固定 SKILL](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/.agents/skills/reverse-engineer-anything/SKILL.md)
- [JavaScript skill 指南](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/.agents/skills/reverse-engineer-anything/references/javascript-applications.md)
- [CLI 与 Evidence](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/docs/cli.md)
- [JavaScript artifact reconstruction](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/docs/javascript-artifact-reconstruction.md)
- [实际副作用说明](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/docs/verification/javascript-analysis-effects-2026-10-15.md)
- [安装与配置变更](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/docs/installation.md)
- [源码 prepare 脚本](https://github.com/morluto/rea/blob/160d821ac9a0310afcb8d1fc427862dd6508add5/scripts/prepare.mjs)
