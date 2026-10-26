// THROWAWAY PROTOTYPE. DSH owns the loop, tools, sessions and compaction.
import { Context } from '@deepseek-ai/cordis';
import LlmRuntime, { LlmAdapter, LlmError, createUserMessage, createSystemMessage, isAgentLoopRequest } from '@deepseek-ai/dsh-llm';
import SessionStore, { SessionId } from '@deepseek-ai/dsh-session';
import SessionProjectionRegistry from '@deepseek-ai/dsh-session-projection';
import SystemPrompt from '@deepseek-ai/dsh-system-prompt';
import ToolRuntime, { defineTool } from '@deepseek-ai/dsh-tools';
import AgentRegistry from '@deepseek-ai/dsh-agent';
import AgentLoop from '@deepseek-ai/dsh-agent-loop';
import * as JsonlSessionPersistence from '@deepseek-ai/dsh-session-persistence-jsonl';
import Storage from '@deepseek-ai/dsh-storage';
import * as StorageJson from '@deepseek-ai/dsh-storage-json';
import * as StorageDomain from '@deepseek-ai/dsh-storage-domain';
import TokenMeter from '@deepseek-ai/dsh-token-meter';
import BasicCompactionEngine from '@deepseek-ai/dsh-compaction-basic';
import SessionQuery from '@deepseek-ai/dsh-session-query-sqlite';
import { z } from 'zod';
import { randomUUID } from 'node:crypto';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(process.env.PROTOTYPE_SCRATCH || './PROTOTYPE_SCRATCH_wipe_me');
const mode = 'mock'; // This first slice intentionally has no network model adapter.
const bootId = randomUUID();
const ctx = new Context();
let handle, operation = 'chat', failNext = false;
const textBlocks = text => [{ type: 'text', text }];
const message = text => createUserMessage({ content: textBlocks(text), source: { kind: 'user' } });
const now = () => new Date().toISOString();
const spec = StorageDomain.defineDomain({
  name: 'prototype_companion', version: 1,
  tables: { fish: StorageDomain.domainTable(z.object({ fish: z.object({ id: z.string() }).passthrough(), revision: z.number() }).passthrough()) },
});
class CompanionCompaction extends BasicCompactionEngine {
  async summarize(input, agent, signal) {
    const revision = read().revision;
    const result = await super.summarize({ ...input,
      messages: [createSystemMessage(activePrompt()), ...input.messages.filter(m => m.role !== 'system')],
    }, agent, signal);
    if (read().revision !== revision) throw new Error('陪伴状态已改变，拒绝提交旧版本摘要');
    return result;
  }
}
await mkdir(root, { recursive: true });
for (const plugin of [LlmRuntime, SessionStore, SessionProjectionRegistry]) await ctx.plugin(plugin);
await ctx.plugin(SystemPrompt, { includeHarnessIdentity: false, includeRuntimeContext: false });
await ctx.plugin(ToolRuntime, { mode: 'native' });
await ctx.plugin(AgentRegistry);
await ctx.plugin(JsonlSessionPersistence, { root: path.join(root, 'sessions'), compression: 'none' });
await ctx.plugin(Storage);
await ctx.plugin(StorageJson, { root: path.join(root, 'domain') });
await ctx.plugin(StorageDomain, { backend: 'json' });
await ctx.plugin(TokenMeter);
await ctx.plugin(CompanionCompaction, { auto: false, headroomTokens: 256, maxTokens: 256, retainTokens: 0 });
await ctx.plugin(SessionQuery, { path: ':memory:', openAt: 'never' });
await ctx.plugin(AgentLoop, { agents: [] });
const domain = await ctx.storageDomain.open(spec);
const table = domain.table('fish');
const read = () => table.get('one');
const initial = () => ({
  fish: { id: 'PROTOTYPE-FISH-ONE', name: '大肥鱼 · 虚构样本', persona: '温和直接的陪伴伙伴。用简短中文交流，不强制追问。', revision: 1 },
  revision: 1, memory: { id: 'sample-preference', value: '', status: 'empty', version: 0, locked: false, sourceIds: [] },
  budget: { limit: 3000, used: 0, reserved: 0, chatReserve: 300, entries: [] },
  sessionId: null, sessionEpoch: 0, appliedEpoch: 0, archive: [], revokedSources: [],
  requests: [], audit: [], lastResult: '已启动真实 DSH；模型响应和 usage 为确定性模拟。', mode,
});
if (!read()) await table.put('one', initial());
async function change(fn) {
  return table.update('one', previous => { const s = structuredClone(previous); fn(s); return s; });
}
async function note(kind, detail) {
  await change(s => { s.audit.push({ at: now(), kind, detail }); s.lastResult = typeof detail === 'string' ? detail : JSON.stringify(detail); });
}
function activePrompt() {
  const s = read();
  return '这是一次性原型的虚构相处。核心人格不得自动修改。\n'
    + JSON.stringify({ fish_id: s.fish.id, persona: s.fish.persona, persona_revision: s.fish.revision,
      state_revision: s.revision, memory_version: s.memory.version,
      allowed_memory: s.memory.status === 'active' ? s.memory.value : null,
      memory_status: s.memory.status })
    + '\n需要回看来源时只能调用 recall_allowed_source。记住明确事实时调用 remember_sample；人工纠正与遗忘优先。';
}

// The mock has no access to business state. Its answer depends only on the actual
// DSH request. Raw requests are captured before it returns any scripted chunks.
class ScriptedProvider extends LlmAdapter {
  async resolveModel(provider, model) {
    return { provider, id: model, name: model, context: { contextWindow: 8192 }, defaultMaxTokens: 256 };
  }
  async *stream(options) {
    await change(s => { s.requests.at(-1).reachedProvider = true; });
    if (failNext) { failNext = false; throw new LlmError('模拟连接中断：没有返回 usage', 'PROTOTYPE_DISCONNECT'); }
    const last = options.messages.at(-1);
    const lastText = (last?.content || []).filter(x => x.type === 'text').map(x => x.text).join('\n');
    let tool = null, answer;
    if (options.purpose === 'compaction') {
      const all = JSON.stringify(options.messages);
      const sampleFacts = [...new Set(all.match(/(?:茉莉花茶|乌龙茶|红茶|咖啡)/g) || [])];
      answer = '模拟摘要，仅概括实际输入：' + (sampleFacts.length ? sampleFacts.join('、') : '未发现样本偏好。');
    } else if (last?.role === 'user' && lastText.startsWith('记住样本：')) {
      tool = { name: 'remember_sample', args: { value: lastText.slice(5) } };
    } else if (last?.role === 'user' && /读取旧来源|自动整理/.test(lastText)) {
      tool = { name: 'recall_allowed_source', args: {} };
    } else {
      const system = options.messages.find(m => m.role === 'system');
      const raw = (system?.content || []).filter(x => x.type === 'text').map(x => x.text).join('\n');
      const allowed = raw.match(/"allowed_memory":("(?:[^"\\]|\\.)*"|null)/)?.[1];
      answer = last?.role === 'tool' ? '模拟模型收到的工具结果：' + lastText
        : '模拟模型收到的有效记忆：' + (allowed && allowed !== 'null' ? JSON.parse(allowed) : '无') + '。';
    }
    if (tool) {
      const id = randomUUID(), args = JSON.stringify(tool.args);
      yield { type: 'block-start', index: 0, blockType: 'tool-call' };
      yield { type: 'tool-call-delta', index: 0, id, name: tool.name, argumentsDelta: args };
      yield { type: 'block-end', index: 0, block: { type: 'tool-call', id, name: tool.name, arguments: args } };
    } else {
      yield { type: 'block-start', index: 0, blockType: 'text' };
      yield { type: 'text-delta', index: 0, text: answer };
      yield { type: 'block-end', index: 0, block: { type: 'text', text: answer } };
    }
    yield { type: 'usage', usage: { inputTokens: 80, outputTokens: 20, totalTokens: 100 } };
    yield { type: 'finish', reason: { kind: tool ? 'tool-calls' : 'stop' } };
  }
}
ctx.llm.registerAdapter(['prototype'], new ScriptedProvider());

// One mandatory gate covers loop steps AND native compaction. No retry plugin is
// mounted. Each dispatch reserves 200 known mock tokens, with actual mock use 100.
ctx.on('llm/stream', async function* (options, next) {
  const id = randomUUID(), purpose = options.purpose || operation;
  const reserve = 200, isBackground = ['background', 'compaction', 'consolidate'].includes(purpose);
  let admitted = false;
  await change(s => {
    const remaining = s.budget.limit - s.budget.used - s.budget.reserved;
    const needed = reserve + (isBackground ? s.budget.chatReserve : 0);
    if (remaining < needed) {
      s.audit.push({ at: now(), kind: 'budget-denied', detail: { purpose, remaining, needed } });
      return;
    }
    admitted = true;
    s.budget.reserved += reserve;
    s.budget.entries.push({ id, purpose, reserved: reserve, status: 'pending', usage: null });
    const { signal, ...request } = options;
    s.requests.push({ id, at: now(), purpose, fishId: s.fish.id, revision: s.revision,
      sessionEpoch: s.sessionEpoch, memoryVersion: s.memory.version, nativeLoop: isAgentLoopRequest(options),
      reachedProvider: false, request: JSON.parse(JSON.stringify(request)) });
  });
  if (!admitted) throw new LlmError('产品预算不足：请求在到达 provider 前已停止', 'PROTOTYPE_BUDGET_LIMIT');
  let usage;
  try {
    for await (const chunk of next()) {
      if (chunk.type === 'usage') usage = chunk.usage;
      yield chunk;
    }
  } finally {
    await change(s => {
      const entry = s.budget.entries.find(x => x.id === id);
      if (usage && Number.isFinite(usage.inputTokens) && Number.isFinite(usage.outputTokens)) {
        const actual = usage.totalTokens ?? usage.inputTokens + usage.outputTokens;
        s.budget.reserved -= reserve;
        s.budget.used += actual;
        Object.assign(entry, { status: 'settled', usage, actual, reserved: 0 });
      } else entry.status = 'unknown-usage'; // Never silently refund an unknown request.
    });
  }
});

async function recallAllowed() {
  const s = read(), sourceId = s.memory.sourceIds[0];
  if (s.memory.status !== 'active' || !sourceId || s.revokedSources.includes(sourceId)) {
    return { allowed: false, reason: '来源已撤销或没有允许使用的记忆；原文仅供使用者回看。', value: null };
  }
  const source = s.archive.find(x => x.id === sourceId);
  if (!source || source.kind !== 'dsh-source') return { allowed: true, value: s.memory.value, source: '人工修订', version: s.memory.version };
  const native = await ctx.sessionQuery.readEvent({ sessionId: SessionId(source.sessionId), seq: source.seq, before: 0, after: 0 });
  // Return only the governed value, never an unfiltered history window.
  const latest = read();
  if (latest.memory.version !== s.memory.version || latest.revokedSources.includes(sourceId)) return { allowed: false, reason: '读取期间规则已更新', value: null };
  return { allowed: true, value: s.memory.value, version: s.memory.version, sourceEventRead: !!native.target };
}

async function commitCandidate(candidate) {
  let accepted = false;
  await change(s => {
    if (candidate.expectedVersion !== s.memory.version || s.memory.locked || s.memory.status === 'forgotten'
      || s.revokedSources.includes(candidate.source.id)) {
      s.audit.push({ at: now(), kind: 'memory-write-refused', detail: { capturedVersion: candidate.expectedVersion, currentVersion: s.memory.version } });
      return;
    }
    accepted = true;
    s.revision++;
    s.memory = { ...s.memory, value: candidate.value, status: 'active', version: s.memory.version + 1, sourceIds: [candidate.source.id] };
    if (!s.archive.some(x => x.id === candidate.source.id)) s.archive.push(candidate.source);
    s.audit.push({ at: now(), kind: 'memory-formed-by-dsh-tool', detail: { sourceId: candidate.source.id, version: s.memory.version } });
  });
  return accepted;
}

const setup = agentCtx => {
  agentCtx.systemPrompt.section({ name: 'prototype-companion', order: 0, complete: true, interpolate: false, text: activePrompt });
  agentCtx.tools.register(defineTool({
    name: 'remember_sample', description: '记录虚构样本的明确偏好；人工纠正或遗忘后不得自动覆盖。',
    parameters: { value: { type: 'string', required: true } },
    output: { schema: { type: 'string' }, render: (_args, value) => textBlocks(value) },
    async execute(args, exec) {
      const s = read();
      if (s.memory.locked || s.memory.status === 'forgotten') return '拒绝写入：人工纠正或遗忘优先。';
      const event = exec.agent.session.snapshotEvents().filter(x => x.type === 'user/message').at(-1);
      const id = `${exec.agent.session.id}:${event.seq}`;
      const accepted = await commitCandidate({ value: args.value, expectedVersion: s.memory.version,
        source: { id, kind: 'dsh-source', sessionId: exec.agent.session.id, seq: event.seq, value: args.value } });
      return accepted ? '已形成样本记忆，来源为实际 DSH user/message。' : '拒绝写入：状态版本或来源已经失效。';
    },
  }));
  agentCtx.tools.register(defineTool({
    name: 'recall_allowed_source', description: '按当前撤销、版本与人工锁检查旧来源。', parameters: {},
    output: { schema: { type: 'string' }, render: (_args, value) => textBlocks(value) },
    async execute() { const result = await recallAllowed(); await note('governed-recall', result); return JSON.stringify(result); },
  }));
};
const agentOptions = { provider: 'prototype', model: 'scripted-fixture', maxTokens: 256 };
async function openAgent(fresh = false) {
  if (handle) await handle.dispose();
  let id = read().sessionId;
  if (fresh || !id) {
    id = 'prototype-' + randomUUID();
    handle = await ctx.agents.create({ sessionId: SessionId(id), agentOptions, setup });
    await ctx.sessions.flush(handle.agent.session);
    await change(s => { s.sessionId = id; s.appliedEpoch = s.sessionEpoch; });
  } else handle = await ctx.agents.resume({ resumeSessionId: SessionId(id), agentOptions, setup });
  await sanitizeSurface();
}

async function sanitizeSurface() {
  const s = read();
  if (s.appliedEpoch === s.sessionEpoch) return;
  await openAgent(true);
}
await openAgent();
await note('host-started', { pid: process.pid, bootId, resumedSession: read().sessionId });

async function talk(text, purpose = 'chat') {
  await sanitizeSurface(); operation = purpose;
  const start = handle.agent.session.snapshotEvents().length;
  handle.agent.followup(message(text));
  await handle.agent.whenIdle();
  await ctx.sessions.flush(handle.agent.session);
  const events = handle.agent.session.snapshotEvents().slice(start);
  const last = events.filter(x => x.type === 'assistant/message').at(-1);
  const end = events.filter(x => x.type === 'turn/end').at(-1);
  const answer = last?.data?.message?.content?.filter(x => x.type === 'text').map(x => x.text).join('\n');
  await note('turn-completed', { purpose, sessionId: read().sessionId, answer: answer ?? null, end: end?.data ?? null, events: events.map(e => e.type) });
  await change(s => { s.lastResult = answer || 'DSH 已结束本轮：' + JSON.stringify(end?.data?.reason ?? '无回复，请检查请求账本'); });
}
async function governance(type, value) {
  await change(s => {
    s.revision++; s.sessionEpoch++; s.sessionId = null;
    s.revokedSources.push(...s.memory.sourceIds.filter(id => !s.revokedSources.includes(id)));
    if (type === 'correct') {
      const id = 'manual-' + randomUUID();
      s.archive.push({ id, kind: 'manual-correction', value });
      s.memory = { ...s.memory, value, version: s.memory.version + 1, status: 'active', locked: true, sourceIds: [id] };
    } else s.memory = { ...s.memory, value: '', version: s.memory.version + 1, status: 'forgotten', locked: true };
    s.audit.push({ at: now(), kind: type, detail: { memoryVersion: s.memory.version, revokedSourceCount: s.revokedSources.length } });
  });
  // Retire the DSH session before creating another. A crash after the domain write
  // resumes into a NEW native session, never the retired context. Same fish ID.
  await sanitizeSurface();
  await note(type, type === 'correct' ? '人工纠正生效；同一条鱼进入新 DSH 会话，原文保留。' : '已遗忘；同一条鱼进入干净的 DSH 会话，撤销旧来源，档案仍可回看。');
}
async function action(a) {
  switch (a.type) {
    case 'reset':
      if (handle) { await handle.dispose(); handle = null; }
      await table.put('one', initial()); await openAgent(true);
      await note('reset', '重置虚构样本与模拟账本；旧 DSH 日志仍保存在 scratch 中。'); break;
    case 'persona':
      if (!String(a.value || '').trim()) throw new Error('人格内容不能为空');
      await change(s => { s.fish.persona = String(a.value).slice(0, 2000); s.fish.revision++; s.revision++; });
      await note('persona', '已保存当前角色人格；下一次 DSH 请求读取最新设定。'); break;
    case 'form': await talk('记住样本：' + (a.value || '虚构样本：喜欢茉莉花茶')); break;
    case 'correct': await governance('correct', a.value || '虚构样本：喜欢乌龙茶'); break;
    case 'forget': await governance('forget'); break;
    case 'chat': await talk(String(a.message || '我们刚才聊过什么偏好？').slice(0, 5000)); break;
    case 'background': await talk('后台活动：就最近允许使用的内容做一次简短整理。', 'background'); break;
    case 'recall': await talk('读取旧来源，告诉我现在允许使用什么。', 'recall'); break;
    case 'consolidate': await talk('自动整理旧来源，检查当前允许使用的事实。', 'consolidate'); break;
    case 'fail-request': failNext = true; await talk('模拟一次缺失 usage 的请求中断。', 'failed-request'); failNext = false; break;
    case 'new-session': await openAgent(true); await note('new-session', '已创建新的真实 DSH 会话，沿用同一条鱼与当前有效状态。'); break;
    case 'compact': {
      await sanitizeSurface(); operation = 'compaction';
      const result = await ctx.compaction.compactNow(handle.agent, new AbortController().signal);
      await ctx.sessions.flush(handle.agent.session);
      await note('native-compaction', { compacted: result !== null, result }); break;
    }
    case 'budget': {
      const limit = Number(a.limit), reserve = Number(a.chatReserve ?? read().budget.chatReserve);
      if (![limit, reserve].every(n => Number.isSafeInteger(n) && n >= 0) || reserve > limit) throw new Error('预算及聊天保留须为非负整数，保留不能超过总额');
      await change(s => { s.budget.limit = limit; s.budget.chatReserve = reserve; s.revision++; });
      await note('budget', '预算已更新；每个实际请求都在模型入口检查。'); break;
    }
    case 'unsafe-replay': {
      const source = read().archive.find(x => x.kind === 'dsh-source');
      if (!source) { await note('native-history-counterexample', '先形成样本记忆，才有原生历史可读。'); break; }
      const raw = await ctx.sessionQuery.readEvent({ sessionId: SessionId(source.sessionId), seq: source.seq, before: 0, after: 0 });
      await note('native-history-counterexample', { warning: '原生历史仍能读出旧事实。仅对使用者展示，未送入模型；不加业务过滤会重新暴露。', raw }); break;
    }
    case 'stale-job': {
      const captured = structuredClone(read().memory);
      const source = structuredClone(read().archive.find(x => x.id === captured.sourceIds[0]) || { id: 'missing-source' });
      await governance('forget');
      await Promise.resolve();
      const current = read().memory;
      const refused = !await commitCandidate({ value: captured.value, expectedVersion: captured.version, source });
      await note('stale-job-commit', { capturedVersion: captured.version, currentVersion: current.version, refused,
        explanation: '模拟整理任务先读旧版本、暂停、人工遗忘，再恢复提交；提交阶段拒绝。未运行线程级并发。' }); break;
    }
    default: throw new Error('未知原型操作：' + a.type);
  }
  return snapshot();
}
async function snapshot() {
  const s = structuredClone(read());
  s.runtime = { pid: process.pid, bootId, dshVersion: '0.2.1-rc.3 (npm release)', cordisVersion: '4.0.5',
    scratchRoot: root, provider: '本地确定性模拟，无网络请求', contextWindow: 8192, providerBalance: null,
    sessionEvents: handle?.agent.session.snapshotEvents().map(e => ({ seq: e.seq, type: e.type })) || [],
    surface: handle?.agent.session.deriveMessages() || [] };
  s.budget.remaining = s.budget.limit - s.budget.used - s.budget.reserved;
  return s;
}
async function close() { if (handle) await handle.dispose(); await domain.close(); await ctx.fiber.dispose(); }
let chain = Promise.resolve();
process.on('message', msg => {
  chain = chain.then(async () => {
    try {
      if (msg.command === 'close') { await close(); process.send({ id: msg.id, result: { closed: true } }); process.exitCode = 0; process.disconnect(); return; }
      const result = msg.command === 'state' ? await snapshot() : await action(msg.action);
      process.send({ id: msg.id, result });
    } catch (error) { process.send({ id: msg.id, error: error.message, state: await snapshot() }); }
  }).catch(error => { console.error(error); process.exitCode = 1; });
});
process.send({ ready: true });
