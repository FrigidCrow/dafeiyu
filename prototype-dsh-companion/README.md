# 大肥鱼 · DSH 一次性原型

验证问题：管理页修改人格、记忆和预算，能否真正作用于同一条鱼，并在人工纠正、遗忘、新会话及重启后保持一致？

这是保留实验用的 throwaway prototype，分支为 `codex/prototype-dsh-companion`。运行真实 DSH 执行、工具、会话、存储和压缩；模型响应及 usage 来自本地确定性模拟，不调用真实模型。结论与限制见 [RESULTS.md](RESULTS.md)。

## 启动

需要 Node.js **24.9.0 或以上**。在本目录运行：

```sh
npm ci --ignore-scripts
npm run prototype
```

打开 [本机原型页](http://127.0.0.1:4317)。服务仅监听本机，默认端口 `4317`；可用 `PROTOTYPE_PORT` 改端口。无需模型密钥、QQ 登录或外部服务。

默认实验状态位于本目录的 `PROTOTYPE_SCRATCH_wipe_me/`，可用 `PROTOTYPE_SCRATCH` 指定另一个独立目录。页面“重置虚构实验”重置样本及模拟账本，但保留旧 DSH 日志；“重启运行实例”实际关闭并重新启动 DSH 子进程，从实验文件恢复。停止服务用 `Ctrl+C`。请只放虚构样本。

也可以双击 [index.html](index.html)：该模式是单文件、纯内存的操作演示，刷新即丢失，不运行 DSH、不验证磁盘恢复，也不具备在线模式的实际请求证据。

离线 reducer 已执行形成、纠正、遗忘检查；浏览器工具不允许打开 `file://`，本轮未做双击浏览器验收。在线页面与最终状态已检查，见 [界面证据](evidence/ui-check.json) 和 [截图](evidence/ui-final.jpg)。

## 怎么观察

按页面的三个演练逐步操作，或使用自由操作按钮。每一步核对当前有效状态、请求全文、工具返回、档案和拦截记录；“操作完成”不等于验收通过。

- **记忆生命周期**：形成偏好、人工纠正、压缩、遗忘、新会话和重启。纠正或遗忘会保留鱼的身份，换用新的 DSH 会话，因此短期聊天上下文会丢失。
- **预算**：尝试后台活动、聊天、缺失 usage 的失败请求及预算耗尽后的请求。被拒请求应出现在拦截记录，且没有到达模型适配器。
- **旧来源**：对比人工查看原始档案与模型受控读取，再尝试提交旧版本整理结果。原始档案仍在，不代表模型有权重新使用。

压缩需要足够长的安全范围，演练会插入明确标为虚构的长文本。空会话返回 `null`，短会话可能失败，这些都不是成功压缩。原生压缩的通用错误可能包住预算拒绝，需同时查看 `budget-denied` 记录及请求计数。

## 证据入口

- [生命周期运行记录](evidence/lifecycle.json)：23 次操作、20 次模拟 provider 请求，12 项检查为真。
- [预算运行记录](evidence/budget.json)：8 次模拟 provider 触达，已结算 700、未知用量预留 200，10 项检查为真。
- [旧任务提交记录](evidence/stale-job.json)：真实写入入口拒绝旧版本，重启后仍保持遗忘。
- [失败会话日志](evidence/failures/idle-system-edit-session.v4.jsonl)：早期直接修改空闲会话 system 事件导致恢复失败的保留反例。

依赖版本锁定在 `package-lock.json`：DSH npm 包 `0.2.1-rc.3`、Cordis `4.0.5`。这与研究文档引用的官方源码提交 `22ddee3792402c3e70ec5f86a63c3e3e895a2f60` 是两种不同证据，不宣称源码提交与运行包完全等同。

包完整性、原始 DSH 会话及关键文件散列见 [provenance.json](evidence/provenance.json) 与 [native-sessions/](evidence/native-sessions/)。`context/` 是从源工作区明确复制的交接依据快照；源工作区未提交的修改保持原状。

本轮没有验证真实模型、真实计费上限、QQ、B站或完整产品体验；不要将此页面当作正式管理后台部署。
