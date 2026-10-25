#!/usr/bin/env python3
"""Generate offline, hand-laid-out architecture diagrams. No third-party packages."""
from pathlib import Path
from html import escape
import json

ROOT = Path(__file__).resolve().parents[1]
SHA = '22ddee3792402c3e70ec5f86a63c3e3e895a2f60'
BASE = f'https://github.com/deepseek-ai/deepseek-harness/blob/{SHA}/'
COLORS = {
 'official': ('#2563a6','#edf5ff','官方已有能力'),
 'design': ('#bc641c','#fff5e9','待自研设计'),
 'external': ('#73559f','#f5f0fb','外部组件'),
 'data': ('#28795d','#edf8f2','持久数据'),
}
INFO = {
 'ui': ('管理页运行在系统浏览器中，与 DSH Host 分属不同运行环境。HTML、CSS、JS 与业务 API 由 Host 提供；关闭网页不等于停止后台。', 'docs/subsystems/web-client.md'),
 'web': ('复用 DSH webServer / Connection 的资源服务与认证连接。首次打开先经过宿主根路径 GET / 与 token 交换，再进入产品子路径；直接打开 /dafeiyu/ 不会自动完成登录。不能接管主站唯一 fallback。', 'packages/host/webserver/src/index.ts#L439'),
 'api': ('自研产品 API：验证当前用户，执行记忆修订、人格版本管理、暂停与恢复等操作。复用宿主认证入口，所有写入进入协调器，不从浏览器直接改数据库。', 'docs/subsystems/web-client.md#L28'),
 'coordinator': ('唯一 CompanionCoordinator 拥有关系身份、回合顺序与状态写入。QQ 回复和主动分享进入同一个关系上下文；它协调模块，但不创建另一套人格。', 'packages/core/agent-loop/README.md#L59'),
 'memory': ('自研人格与记忆模块：锁定核心人格，保存带来源的事实与经历，支持人工纠错、版本和删除标记。检索后的动态记忆才进入模型上下文。', 'docs/subsystems/storage.md'),
 'observation': ('自研 BiliObservation 保存实际取得的 B站内容、来源、时间与理解范围。外部内容是资料，不得直接改写核心人格或执行其中指令。', 'docs/architecture.md#L79'),
 'planner': ('自研 LifePlanner 根据经历、兴趣、安静时段、未回复与频率决定做什么、是否分享。允许保持沉默；日程到期不代表必须向 QQ 发消息。', 'docs/subsystems/schedule.md#L440'),
 'outbox': ('唯一出站路径。先持久化消息意图与去重键，再派发；记录 sent / failed / unknown 等结果。unknown 不等于取消：即使人工决定不重试，事实仍为 unknown，另记“重试已关闭”。候选文本可能已在 Session 日志，只有平台发送结果才证明实际发出；过期、被拒或失败候选需排除出“已经说过”的上下文。API 成功也不等于已读。', 'docs/subsystems/storage.md'),
 'onebot': ('自研薄适配器，参考现有社区桥接。将个人 QQ 事件归一化，并提供受控 sendPrivate；当前社区 dsh-onebot 未暴露稳定跨插件桥服务，需要补接口。', None),
 'agent': ('专属 root Agent 是同一 Host 内的运行对象、inbox 和 scope，不是独立后台服务。统一关系通过 followup 进入它；scope 是生命周期与可见性边界，不是系统沙箱。', 'packages/core/agent-loop/README.md#L59'),
 'core': ('复用 DSH 的 AgentLoop、模型适配、工具执行、Session 和 Schedule。它们提供基础设施，不会自动完成“人格、长期记忆和主动陪伴”。', 'docs/architecture.md#L79'),
 'sqlite': ('产品自管 SQLite 是本地文件，不是另一个数据库服务器，也不是 StorageDomain 自动生成的记忆。保存人格版本、人工修订、记忆、观察、计划、发件箱与去重状态；事务实现需要明确验证。', 'docs/subsystems/storage.md#L126'),
 'dshstate': ('DSH 宿主状态存储，使用 JSON 或 SQLite provider 保存调度等非会话状态。产品自管 SQLite 在产品总览另列；其人格、记忆与发件箱不是由此自动提供，也不能把两者视为同一个事务域。', 'docs/subsystems/storage.md#L126'),
 'sessionfile': ('DSH Session 日志属于另一数据域，保存对话、工具和执行事件；默认发行后端为 JSONL。它不是第二份人格或自动长期记忆库。flush 是重要耐久边界。', 'docs/subsystems/persistence.md#L67'),
 'model': ('DeepSeek 云端模型通过 API 接收请求。AgentLoop 和产品状态留在本机/服务器 Host；调用成本、失败和模型版本要单独记录。', 'docs/architecture.md#L79'),
 'bili': ('B站是外部观察来源。具体可读内容受接口、登录与素材可用性影响；拿到标题或字幕不能声称完整观看理解视频。', None),
 'napcat': ('QQ + NapCat 独立于 DSH 进程。推荐 Linux 容器运行个人 QQ，向 OneBot 适配器提供鉴权 WebSocket；登录态和真实消息送达仍需验收。', None),
 'qq': ('用户在手机 QQ 中与普通 QQ 账号好友交互。这里不是腾讯开放平台 Bot 身份；真实私聊和主动收件需要账号验收。', None),
 'launcher': ('拟建统一入口负责版本检测、安装、启停、诊断、备份与打开管理页。它不替代账号扫码，也不拥有另一套主动消息决策。', 'README.md'),
 'profile': ('Launcher 按顺序合并 profile bundles 和 patches。产品使用专用 DSH home 下的 Web profile；bundle 是代码与配置发行形式，不是新进程。', 'docs/architecture.md#L17'),
 'loader': ('共享 profile runner / app-boot / Cordis Loader 组成 Host 插件树。这里复用 DSH 启动体系，不重新实现宿主。', 'packages/boot/app-boot/README.md#L46'),
 'registry': ('AgentRegistry 提供 create/resume 管理面；AgentLoop 注册具体 factory/driver。返回的 handle 拥有释放权。', 'packages/core/agent-loop/README.md#L59'),
 'preset': ('Preset 定义共享注册 scope 和插件树修订。Agent 保留选中的组成修订；更新 preset 不等于自动改写所有存量 Agent。', 'packages/preset/agent-preset-registry/README.md#L56'),
 'schedule': ('Schedule 持久任务到期后解析或恢复原会话 Agent，通过 followup 写入 inbox。它只唤醒，不负责发送或幂等。root Session 轮换、遗忘后，旧任务仍可能恢复旧 Session：产品必须用会话代次门禁，并删除、重建和对账旧任务，不能只换一个新会话 ID。', 'docs/subsystems/schedule.md#L440'),
 'storage': ('StorageDomain 支持 JSON/SQLite provider，保存调度等非 Session 宿主状态。产品选择自管 SQLite，单独管理人格、记忆与发件箱；不能从官方存储机制推导产品自动记忆或跨库事务保证。', 'docs/subsystems/storage.md#L126'),
 'prompt': ('每轮从稳定人格、相关记忆、Session 和可见工具组装模型上下文。inject 补上下文，不能代替 followup 唤醒。', 'docs/architecture.md#L79'),
 'llm': ('LLM adapter prepareCall 后执行模型 API 请求；流式结果可能为文本或工具调用。重试与失败必须结合宿主实际语义验证。', 'docs/architecture.md#L79'),
 'tools': ('工具注册、策略与执行器处理模型 tool calls，结果回到同一 Agent 回合。给模型工具不等于允许绕过发件箱直接向 QQ 发送。', 'docs/architecture.md#L79'),
 'session': ('Session 是追加式执行事件和上下文投影。Agent 生成的候选可能已经进入日志，但不等于 QQ 已发送；取消或失效候选必须排除在“已说过”的上下文之外。产品长期记忆由独立模块提取和维护。', 'docs/architecture.md#L122'),
 'persistence': ('SessionPersistence 管理读取、append、flush、close 和写入所有权。内存接纳一条消息不等于已达到崩溃耐久保证。', 'docs/subsystems/persistence.md#L67'),
 'gateway': ('Connection / API Gateway 处理认证请求、远程调用与事件流，Host 保持权威状态。网页或正式客户端插件都不能成为第二个后端。', 'docs/subsystems/web-client.md#L28'),
 'sendpath': ('所有聊天回复和主动分享都逐级经过 OutboxDispatcher → OneBotAdapter → NapCat → QQ。发送结果与真实发出文本回写同一关系的可见记录。', None),
 'migration': ('先停止旧调度与发送者，再做一致性备份；新端恢复时保持禁发，完成登录与上下文验收后才接管。两个本地锁无法保证跨机器单主。', None),
 'bundle': ('统一 bundle 内包含产品后端、适配模块与预构建页面。产品模块共用一个状态和协调器，禁止各自启动另一个记忆或主动发信系统。', 'docs/architecture.md#L17'),
}
DETAILS = {}
def txt(x,y,s,size=16,fill='#263644',weight=400,anchor='start'):
 return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{escape(s)}</text>'
class Diagram:
 def __init__(self,key,title,subtitle,height):
  self.key,self.height=key,height
  self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 {height}" role="img" aria-labelledby="{key}-title {key}-desc"><title id="{key}-title">{escape(title)}</title><desc id="{key}-desc">{escape(subtitle)}</desc><defs><marker id="{key}-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 Z" fill="#8999a6"/></marker></defs><style>text{{font-family:system-ui,-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}} .node{{cursor:pointer;outline:none}} .node:focus rect,.node:hover rect{{stroke-width:2.5}}</style><rect width="1440" height="{height}" fill="#fbfcfd"/>',txt(40,47,title,27,weight=700),txt(40,78,subtitle,15,'#637480')]
 def group(self,x,y,w,h,label,sub='',kind='official'):
  color=COLORS[kind][0]
  self.parts += [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="white" stroke="{color}" stroke-opacity=".45" stroke-dasharray="6 5"/>',txt(x+22,y+31,label,18,color,650)]
  if sub:self.parts.append(txt(x+22,y+55,sub,13,'#6c7d89'))
 def node(self,id,x,y,w,h,title,lines=(),kind='design',topic=None):
  topic=topic or id; color,bg,label=COLORS[kind]; key=f'{self.key}-{id}'
  desc,source=INFO.get(topic,('计划中的产品设计；需在实现阶段验证。',None))
  sources=[]
  if topic in ('sqlite','outbox'):sources.append(['产品架构设计（待实现）','DSH一站式大肥鱼架构设计.md'])
  if source:sources.append(['官方存储能力（背景）' if topic in ('sqlite','outbox') else '官方固定源码 / 文档',BASE+source])
  if topic in ('onebot','sendpath'):sources.append(['社区 OneBot 桥固定源码','https://github.com/mario841859784/dsh-onebot/tree/bc3aa23fcf7a11f9be7440ce2539a0a8889da3f7'])
  if topic=='napcat':sources.append(['NapCat 官方容器说明','https://github.com/NapNeko/NapCat-Docker'])
  if topic in ('migration','launcher'):sources.append(['本地部署设计底稿','evidence/deployment.md'])
  if topic in ('bili','observation'):sources.append(['本地统一方案','../research/DSH统一陪伴插件方案.md'])
  DETAILS[key]={'title':title,'kind':label,'desc':desc,'sources':sources}
  self.parts += [f'<g class="node" data-node="{key}" role="button" tabindex="0" aria-label="{escape(title)}：查看职责与边界"><title>{escape(title+" — "+desc)}</title><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{bg}" stroke="{color}" stroke-opacity=".55"/>',txt(x+16,y+23,label,10,color,650),txt(x+16,y+49,title,17,'#203341',650)]
  for i,line in enumerate(lines):self.parts.append(txt(x+16,y+72+i*20,line,13,'#536675'))
  self.parts.append('</g>')
 def edge(self,points,label='',labelpos=None,dashed=False,both=False):
  path=' '.join(f'{x},{y}' for x,y in points)
  self.parts.append(f'<polyline points="{path}" fill="none" stroke="#8999a6" stroke-width="1.6" stroke-linejoin="round" marker-end="url(#{self.key}-arrow)"'+(f' marker-start="url(#{self.key}-arrow)"' if both else '')+(' stroke-dasharray="5 5"' if dashed else '')+'/>')
  if label and labelpos:
   x,y=labelpos;w=len(label)*12+16
   self.parts.append(f'<rect x="{x-w/2}" y="{y-14}" width="{w}" height="20" rx="4" fill="#fbfcfd"/>')
   self.parts.append(txt(x,y,label,12,'#5c6e7a',anchor='middle'))
 def note(self,x,y,s,size=13):self.parts.append(txt(x,y,s,size,'#667884'))
 def finish(self):
  self.parts.append(txt(40,self.height-25,'架构设计 · 未运行验收    ｜    节点可点击查看职责与证据',12,'#7a8892'))
  self.parts.append('</svg>');return ''.join(self.parts)

# 01 — product overview
d=Diagram('product','一只鱼，一个协调中心','管理页面在浏览器；人格、记忆、活动与消息出口由同一 DSH Host 内的统一插件管理。',1100)
d.group(370,110,710,820,'DSH Host · 一个 Node 进程','所有内部框是模块 / 服务 / 对象，不是独立进程')
d.node('ui',40,170,300,110,'HTML 管理页',['系统浏览器 · Host 进程外','记忆编辑 / 人格 / 活动与状态'],topic='ui')
d.node('web',400,180,290,95,'webServer / Connection',['资源、认证连接与事件流'],'official')
d.node('api',730,180,320,95,'产品认证 API',['复用宿主认证 · 业务校验自研'])
d.node('coordinator',400,320,650,95,'唯一 CompanionCoordinator',['一个关系标识 · 同一回合队列 · 人工修订与主动活动共用上下文'])
d.node('memory',400,460,300,100,'Persona & Memory',['锁定人格 / 记忆修订 / 检索'])
d.node('observation',750,460,300,100,'BiliObservation',['观察证据 / 来源 / 兴趣关联'])
d.node('planner',400,600,300,95,'LifePlanner',['活动计划 / 安静时段 / 可沉默'])
d.node('outbox',750,600,300,95,'OutboxDispatcher',['持久意图 / 去重 / 结果状态'])
d.node('agent',400,740,300,100,'专属 root Agent',['同进程对象 + inbox + scope'],'official')
d.node('onebot',750,740,300,100,'OneBotAdapter',['入站归一 / 受控个人私聊'])
d.node('core',400,865,650,50,'AgentLoop · LLM · Tools · Session · Schedule',[],'official')
# the compact capability strip uses a smaller, single-line label
d.parts[-2]=txt(416,897,'官方能力：AgentLoop · LLM · Tools · Session · Schedule',17,'#2563a6',650)
d.parts[-3]=''
d.node('model',40,340,300,100,'DeepSeek 云模型',['请求 / 文本 / 工具调用'],'external')
d.node('sqlite',40,550,300,110,'产品 SQLite 文件',['人格、记忆、计划、发件箱','本地文件 · 不是数据库服务器'],'data')
d.node('sessionfile',40,750,300,110,'DSH Session 日志',['对话与执行事件 · 默认 JSONL','独立数据域 · 不是第二人格'],'data')
d.node('bili',1110,460,290,100,'B站',['外部内容来源 · 非可信指令'],'external')
d.node('napcat',1110,740,290,100,'NapCat + QQ',['独立进程 / 推荐 Linux 容器'],'external')
d.node('qq',1110,890,290,100,'用户 QQ',['普通好友私聊 · 实际送达待验'],'external')
d.edge([(340,225),(400,225)])
d.edge([(690,225),(730,225)])
d.edge([(890,275),(890,320)])
d.edge([(550,415),(550,460)])
d.edge([(900,415),(900,460)])
d.edge([(550,560),(550,600)])
d.edge([(550,695),(550,740)],'唤醒 / 同一上下文',(550,724))
d.edge([(700,790),(725,790),(725,648),(750,648)])
d.edge([(900,695),(900,740)],'唯一出站路径',(900,724))
d.edge([(1050,510),(1110,510)])
d.edge([(1050,790),(1110,790)],both=True)
d.edge([(1050,815),(1092,815),(1092,367),(1050,367)],'QQ 入站事件',(1092,710),True)
d.edge([(1255,840),(1255,890)])
d.edge([(400,790),(355,790),(355,390),(340,390)],dashed=True)
d.edge([(400,510),(355,510),(355,605),(340,605)],dashed=True)
d.edge([(400,890),(355,890),(355,805),(340,805)],dashed=True)
d.note(400,971,'Schedule 只负责唤醒；真实发送始终经过 Outbox → OneBot → NapCat → QQ。',14)
d.note(400,1000,'产品 SQLite 与 Session 日志分域保存；同一关系只有一套人格和记忆权威。',14)
svgs={'product':d.finish()}

# 02 — runtime
d=Diagram('runtime','DSH 底层：插件树如何成为一个运行中的 Agent','官方结构依据固定源码；橙色区域为这次产品准备增加的模块。scope 控制可见性和生命周期，不是安全沙箱。',1150)
d.node('launcher',40,110,270,100,'启动入口',['CLI / Desktop shell'],'official',topic='loader')
d.node('profile',365,110,300,100,'Profile + bundles + patches',['专用 home · 标准 Web profile'],'official')
d.node('loader',720,110,300,100,'profile runner / Cordis',['装配共享服务和插件树'],'official')
d.node('ui',1080,110,320,100,'浏览器管理页',['独立客户端运行环境'])
d.edge([(310,160),(365,160)]);d.edge([(665,160),(720,160)])
d.group(40,260,1360,690,'Host · 同一个 Node 进程','共享服务 + Preset scope + Agent scope；每个框不代表一个进程')
d.node('registry',70,340,285,95,'AgentRegistry / AgentLoop',['create / resume / handle'],'official')
d.node('preset',70,470,285,95,'Preset Registry',['定义修订 + shared scope'],'official')
d.node('schedule',70,600,285,95,'Schedule',['持久任务 · 到期 followup'],'official')
d.node('storage',70,790,285,95,'StorageDomain',['调度等非会话宿主状态'],'official')
d.group(415,340,580,385,'专属 root Agent scope','接口按 scope 可见；LLM / Tools 运行服务由 Host 共享')
d.node('agent',450,415,510,85,'root Agent：inbox → turn → step',[],'official')
d.node('prompt',450,540,230,90,'上下文组装',['人格 / 记忆 / tools'],'official')
d.node('llm',730,540,230,90,'LLM adapter',['prepareCall / 流式请求'],'official')
d.node('session',450,650,230,65,'Session',[],'official')
d.node('tools',730,650,230,65,'Tools / 策略执行',[],'official')
d.node('web',1055,340,315,95,'Web Server',['页面资源 / 认证连接'],'official')
d.node('gateway',1055,470,315,95,'Connection / API Gateway',['请求、事件、远程调用'],'official')
d.node('bundle',1055,600,315,95,'统一 Companion 插件',['API / 协调 / 人格记忆 / 出站'])
d.node('persistence',415,790,580,95,'SessionPersistence',['append / flush / close · 可替换持久后端'],'official')
d.edge([(355,387),(450,455)])
d.edge([(355,517),(415,517)],dashed=True)
d.edge([(355,647),(390,647),(390,455),(450,455)],'恢复后唤醒',(390,587))
d.edge([(565,500),(565,540)]);d.edge([(680,585),(730,585)])
d.edge([(845,630),(845,650)]);d.edge([(730,683),(680,683)],'工具结果',(705,711))
d.edge([(565,715),(565,790)])
d.edge([(1240,210),(1240,340)]);d.edge([(1212,435),(1212,470)]);d.edge([(1212,565),(1212,600)])
d.edge([(1055,647),(1015,647),(1015,455),(960,455)])
d.node('sessionfile',415,1010,300,95,'Session JSONL 文件',['对话 / 工具 / 执行日志'],'data')
d.node('model',745,1010,280,95,'外部模型 API',['Host 发起请求'],'external')
d.node('dshstate',1055,1010,315,110,'DSH 状态存储',['JSON 或 SQLite','调度与非会话宿主状态'],'data')
d.edge([(565,885),(565,1010)])
d.edge([(960,585),(1025,585),(1025,975),(885,975),(885,1010)],dashed=True)
d.edge([(355,837),(390,837),(390,930),(1212,930),(1212,1010)],dashed=True)
svgs['runtime']=d.finish()

# 03 — message and initiative flows
d=Diagram('flows','一次聊天，与一次主动分享','两种触发进入同一关系上下文；所有出站统一走发件箱。持久化日志、记忆与发送结果各有职责。',1210)
d.group(40,115,1360,450,'A · 主人发来一句话','从个人 QQ 入站；模型产出消息候选，产品完成决策后才进入发送。')
chat=[('qq',70,'普通 QQ 好友','external'),('napcat',290,'NapCat + QQ','external'),('onebot',510,'OneBotAdapter','design'),('coordinator',730,'Coordinator','design'),('agent',950,'root Agent','official'),('outbox',1170,'Outbox','design')]
for id,x,title,k in chat:d.node(id,x,220,180,100,title,[],k)
for x in [250,470,690,910,1130]:d.edge([(x,270),(x+40,270)])
d.node('sqlite',730,390,180,100,'产品 SQLite',['修订与记忆候选'],'data')
d.node('sessionfile',950,390,180,100,'Session 日志',['对话与工具事实'],'data')
d.node('sendpath',1170,390,180,100,'QQ 发送通路',['OneBot → NapCat','→ 用户 QQ'],'design')
d.edge([(820,320),(820,390)],'检索 / 写入',(820,361))
d.edge([(1040,320),(1040,390)],'flush',(1040,361))
d.edge([(1260,320),(1260,390)],'唯一发送出口',(1260,361))
d.note(70,402,'共享关系上下文',17)
d.note(70,434,'真实发出文本与发送结果回写；')
d.note(70,458,'用户续聊时能接上刚才的话。')
d.note(70,515,'超时 → unknown，不能默认已送达，也不能盲目自动重发。',14)
d.group(40,620,1360,475,'B · 没有新消息时，鱼发现值得分享的内容','Schedule 只唤醒；是否开口由协调器与 LifePlanner 决定，允许跳过分享。')
d.node('schedule',70,725,180,100,'Schedule',['到期唤醒'],'official')
d.node('agent2',510,725,180,100,'root Agent',['恢复同一 Session'],'official',topic='agent')
d.node('coordinator2',730,725,180,100,'Coordinator',['工具 / 事件进入'],topic='coordinator')
d.node('planner',950,725,180,100,'LifePlanner',['值不值得说？'])
d.node('outbox2',1170,725,180,100,'Outbox',['去重 / 安静时段'],topic='outbox')
d.edge([(250,775),(510,775)],'followup，不直接发 QQ',(380,761))
for x in [690,910,1130]:d.edge([(x,775),(x+40,775)])
d.node('bili',70,920,180,100,'B站内容',['真实取得的来源'],'external')
d.node('observation',290,920,180,100,'观察记录',['证据 / 兴趣关联'])
d.edge([(250,970),(290,970)])
d.edge([(470,970),(490,970),(490,860),(820,860),(820,825)])
d.node('sqlite2',730,920,180,100,'产品 SQLite',['新经历 / 活动状态'],'data',topic='sqlite')
d.node('sendpath2',1170,920,180,100,'QQ 发送通路',['OneBot → NapCat','→ 用户 QQ'],'design',topic='sendpath')
d.edge([(1260,825),(1260,920)])
d.edge([(1040,825),(1040,970),(910,970)],'可以只存不发',(1040,890),True)
d.note(70,1138,'日程投递、模型完成、平台 API 成功、用户已读是不同事件，不能合并成一个“完成”。',14)
svgs['flows']=d.finish()

# 04 — deployment
d=Diagram('deployment','先在 Mac 养，稳定后迁到 Linux','保留应用结构与数据协议，替换运行环境；迁移时只有一个实例拥有发送权。',1080)
d.node('launcher',450,110,540,100,'一个统一启动入口',['安装 / 启停 / 诊断 / 备份 / 打开管理页'])
d.group(40,270,640,510,'现在 · Mac（Apple Silicon）','本机 Node + DSH Web；QQ 端独立 Linux 容器')
d.group(760,270,640,510,'以后 · Linux 服务器','系统服务保持 Host 常驻；对应架构 QQ 容器')
for p,x in [('mac',70),('linux',790)]:
 d.group(x,355,580,175,'DSH Host · 一个 Node 进程')
 d.node(p+'-core',x+20,410,250,100,'DSH Web profile',['AgentLoop / 会话 / HTTP'],'official',topic='core')
 d.node(p+'-bundle',x+300,410,260,100,'统一 Companion',['同一插件包与数据 schema'],topic='bundle')
 d.node(p+'-napcat',x,585,270,125,'QQ + NapCat 容器',['独立登录态 / OneBot','amd64 或 arm64 对应镜像'],'external',topic='napcat')
 d.node(p+'-sqlite',x+310,585,270,125,'本地持久数据根',['产品 SQLite + Session 日志','配置 / 观察证据 / 版本锁'],'data',topic='sqlite')
 d.edge([(x+145,530),(x+145,585)])
 d.edge([(x+430,530),(x+430,585)],dashed=True)
d.edge([(570,210),(570,245),(360,245),(360,270)])
d.edge([(870,210),(870,245),(1080,245),(1080,270)])
d.note(70,752,'浏览器关闭：后台可继续；睡眠或退出：活动中断。')
d.note(790,752,'远程管理走认证连接；不把数据库直接暴露给网页。')
steps=[('pause','暂停并停旧端','关闭调度、发送与自动启动'),('backup','一致性备份','会话、修订、任务、去重键'),('restore','新端恢复 · 禁发','重建对应架构依赖与版本'),('verify','登录与上下文验收','凭据重绑、QQ 实际收发'),('active','新端独占发送','旧端停用后才恢复主动性')]
for i,(id,title,line) in enumerate(steps):
 x=40+i*280;d.node(id,x,860,260,110,title,[line],topic='migration')
 if i<4:d.edge([(x+260,915),(x+280,915)])
d.note(40,1014,'不是复制 node_modules 或 Mac 二进制；QQ/B站登录可能需要重新验证。两把本地锁不等于跨机单主。',14)
svgs['deployment']=d.finish()

ROOT.joinpath('diagrams').mkdir(exist_ok=True)
for name,svg in svgs.items():ROOT.joinpath('diagrams',name+'.svg').write_text(svg,encoding='utf-8')
meta={
 'product':('01 / 产品总览','让人格、记忆和主动行为只听一个协调中心。','先看橙色的唯一协调器，再沿发件箱向右看真实 QQ 出口。左侧两种数据各司其职。'),
 'runtime':('02 / DSH 底层','一个 Host，多个服务与作用域。','蓝色表示官方已有的基础能力；专属 Agent 是同进程对象。浏览器与 Host 是不同运行环境。'),
 'flows':('03 / 数据流','被动聊天与主动分享，进入同一个上下文。','上半图从 QQ 消息开始，下半图从日程或观察开始。两条路线都经过同一个发件箱。'),
 'deployment':('04 / 部署迁移','先本机验证，再让服务器持续运行。','保持插件与数据协议一致；停止旧发送者、恢复验证完成后，新机器才接管主动性。'),
}
views=''.join(f'<section class="view" id="view-{key}" {"" if key=="product" else "hidden"}>{svg}</section>' for key,svg in svgs.items())
page=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>大肥鱼 · DSH 一站式架构</title><style>
:root{--ink:#22333f;--muted:#687b87;--line:#dce5e8;--paper:#f6f8f8;--blue:#2563a6;--orange:#bc641c;--purple:#73559f;--green:#28795d}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}button,a{font:inherit}button{cursor:pointer}button:focus-visible,a:focus-visible{outline:3px solid #6ea5cf;outline-offset:4px}header{padding:32px 40px 26px;background:#fff;border-bottom:1px solid var(--line)}.eyebrow{display:flex;align-items:center;gap:12px;color:var(--muted);font-size:12px;letter-spacing:.08em}.mark{width:28px;height:28px;border-radius:9px;background:#233d4a;color:white;display:grid;place-items:center;font-size:15px;font-weight:800}.status{margin-left:auto;color:#9a5a1f;background:#fff3e4;border:1px solid #eddbc1;border-radius:20px;padding:6px 12px;letter-spacing:0}h1{margin:24px 0 9px;font-size:clamp(26px,3.2vw,42px);font-weight:650;letter-spacing:-.04em}.intro{font-size:15px;line-height:1.7;color:var(--muted);margin:0;max-width:850px}.topline{display:flex;align-items:center;gap:20px;justify-content:space-between}.actions{display:flex;gap:8px;flex-shrink:0}.btn{border:1px solid var(--line);border-radius:9px;padding:10px 14px;background:#fff;color:#344e5f;text-decoration:none;font-size:13px}.btn:hover{background:#f2f6f8}.btn.primary{background:#203c4c;border-color:#203c4c;color:white}.navwrap{padding:20px 40px 0;display:flex;align-items:center;gap:16px;flex-wrap:wrap}nav{display:flex;gap:5px;padding:5px;background:#e9eff1;border-radius:13px}nav button{border:0;border-radius:9px;padding:12px 18px;background:transparent;color:#667984;font-size:13px;font-weight:550}nav button[aria-selected=true]{background:white;color:#203c4c;box-shadow:0 2px 8px #1a354410}.legend{margin-left:auto;display:flex;gap:16px;flex-wrap:wrap;font-size:11px;color:#526774}.legend span{display:flex;align-items:center;gap:6px}.dot{display:inline-block;width:9px;height:9px;border-radius:3px}.blue{background:var(--blue)}.orange{background:var(--orange)}.purple{background:var(--purple)}.green{background:var(--green)}main{padding:24px 40px 30px}.workspace{display:grid;grid-template-columns:minmax(0,1fr) 282px;gap:20px;align-items:start}.canvas{background:white;border:1px solid var(--line);border-radius:17px;overflow:hidden;box-shadow:0 8px 30px #1e394706}.caption{padding:22px 25px 18px;border-bottom:1px solid #e5ecef;display:flex;gap:20px;align-items:flex-start}.caption h2{font-size:20px;margin:0 0 8px;font-weight:620}.caption p{font-size:13px;line-height:1.65;color:var(--muted);margin:0}.index{font-size:10px;letter-spacing:.07em;color:#8a9aa3;margin:2px 0 6px}.hint{margin-left:auto;white-space:nowrap;border:1px solid #e2eaee;border-radius:6px;padding:6px 8px;font-size:11px;color:#778b99}.viewport{overflow:auto;background:#fbfcfd}.view svg{width:100%;min-width:900px;height:auto;display:block}.view[hidden]{display:none}.detail{padding:23px 22px;background:#fff;border:1px solid var(--line);border-radius:15px;position:sticky;top:20px;min-height:325px}.detail .small{font-size:10px;letter-spacing:.08em;color:#8798a3}.detail h3{font-size:19px;line-height:1.4;margin:15px 0 11px;overflow-wrap:anywhere}.tag{display:inline-block;font-size:11px;padding:4px 8px;background:#eef3f6;border-radius:5px;color:#526b7b}.detail p{color:#617580;font-size:13px;line-height:1.9}.detail ul{padding-left:16px;line-height:1.7;font-size:12px}.detail a{color:#2d6488;text-underline-offset:3px}.boundary{margin-top:25px;padding-top:17px;border-top:1px solid #e5ecef;font-size:11px;color:#87959e;line-height:1.7}.bottom{display:flex;justify-content:space-between;gap:20px;margin-top:18px;color:#8a99a2;font-size:11px;line-height:1.7}.bottom a{color:#607d91}footer{padding:0 40px 28px;color:#81939d;font-size:11px;display:flex;justify-content:space-between}.download-links{display:flex;gap:12px;flex-wrap:wrap}.download-links a{color:#668193;text-decoration:none}@media(max-width:1100px){.workspace{grid-template-columns:minmax(0,1fr)}.detail{position:static;min-height:0}.legend{margin-left:0}.topline{align-items:flex-start}.hint{display:none}}@media(max-width:700px){header{padding:22px 20px}.topline{display:block}.actions{margin-top:18px}.navwrap{padding:16px 20px 0}nav{width:100%;overflow-x:auto}nav button{padding:10px 12px;white-space:nowrap}.legend{gap:10px}main{padding:18px 14px}.caption{padding:18px}.status{font-size:10px}.bottom{display:block}footer{padding:0 20px 24px;display:block}.download-links{margin-top:10px}}@media print{@page{size:A3 landscape;margin:10mm}header{padding:0 0 12px}h1{font-size:25px;margin:10px 0}.intro,.navwrap,.actions,.detail,.hint,.bottom,footer{display:none}.eyebrow{font-size:9px}.status{padding:3px 8px}main{padding:10px 0}.workspace{display:block}.canvas{border:0;box-shadow:none;border-radius:0}.caption{padding:0 0 8px}.caption h2{font-size:16px}.caption p{font-size:10px}.viewport{overflow:visible}.view svg{min-width:0;width:100%;max-height:230mm}.view{break-inside:avoid}}
</style></head><body><header><div class="eyebrow"><span class="mark">鱼</span><span>DAFEIYU / ARCHITECTURE</span><span class="status">架构设计 · 未运行验收</span></div><div class="topline"><div><h1>一只鱼，一个完整的世界。</h1><p class="intro">基于 DSH 的统一陪伴插件，让性格、记忆、外部观察与主动聊天共享同一条生活线。以下展示准备建设的结构，以及它所依托的已有能力。</p></div><div class="actions"><a class="btn" id="download" href="diagrams/product.svg" download="大肥鱼-product.svg">下载当前 SVG ↗</a><button class="btn primary" id="print">打印当前图</button></div></div></header><div class="navwrap"><nav role="tablist" aria-label="架构视图"><button role="tab" aria-selected="true" data-view="product">01 产品总览</button><button role="tab" aria-selected="false" data-view="runtime">02 DSH 底层</button><button role="tab" aria-selected="false" data-view="flows">03 聊天与主动</button><button role="tab" aria-selected="false" data-view="deployment">04 部署与迁移</button></nav><div class="legend" aria-label="颜色与文字图例"><span><i class="dot blue"></i>官方已有</span><span><i class="dot orange"></i>待自研</span><span><i class="dot purple"></i>外部组件</span><span><i class="dot green"></i>持久数据</span></div></div><main><div class="workspace"><div class="canvas"><div class="caption"><div><div class="index" id="view-index"></div><h2 id="view-title"></h2><p id="view-guide"></p></div><span class="hint">点击节点 · 查看边界与来源</span></div><div class="viewport">__VIEWS__</div></div><aside class="detail" aria-live="polite"><div class="small">NODE INSPECTOR / 节点说明</div><h3 id="detail-title">从唯一协调器开始</h3><span class="tag" id="detail-tag">阅读提示</span><p id="detail-desc">点击图中任一节点，查看它负责什么、哪些能力已有源码支持，以及还需要实现和验证的边界。</p><ul id="detail-sources"></ul><div class="boundary">本页是离线架构说明，不连接 QQ、B站或模型，不显示虚构运行状态。<br>官方证据固定于 2026-10-23 的源码修订。</div></aside></div><div class="bottom"><span>阅读顺序：产品边界 → 宿主机制 → 行为数据流 → 运行与迁移。</span><span>架构核验：2026-10-26 · <a href="evidence/dsh-runtime.md">DSH 证据底稿</a> · <a href="evidence/deployment.md">部署设计底稿</a></span></div></main><footer><span>一个安装入口，不等于所有组件都挤进一个进程。</span><div class="download-links"><a href="diagrams/product.svg" download>产品 SVG</a><a href="diagrams/runtime.svg" download>底层 SVG</a><a href="diagrams/flows.svg" download>数据流 SVG</a><a href="diagrams/deployment.svg" download>部署 SVG</a></div></footer><script>
const details=__DETAILS__,meta=__META__;let current='product';
function showNode(id){const d=details[id];if(!d)return;document.getElementById('detail-title').textContent=d.title;document.getElementById('detail-tag').textContent=d.kind;document.getElementById('detail-desc').textContent=d.desc;const list=document.getElementById('detail-sources');list.replaceChildren();for(const [name,url]of d.sources){const li=document.createElement('li'),a=document.createElement('a');a.textContent=name;a.href=url;a.target='_blank';a.rel='noopener noreferrer';li.append(a);list.append(li)}}
function selectView(key){if(!meta[key])return;current=key;for(const el of document.querySelectorAll('.view'))el.hidden=el.id!=='view-'+key;for(const b of document.querySelectorAll('[data-view]'))b.setAttribute('aria-selected',String(b.dataset.view===key));const [idx,title,guide]=meta[key];document.getElementById('view-index').textContent=idx;document.getElementById('view-title').textContent=title;document.getElementById('view-guide').textContent=guide;const a=document.getElementById('download');a.href='diagrams/'+key+'.svg';a.download='大肥鱼-'+key+'.svg';showNode(key+'-'+({product:'coordinator',runtime:'agent',flows:'outbox',deployment:'launcher'}[key]));}
document.addEventListener('click',e=>{const tab=e.target.closest('[data-view]');if(tab){selectView(tab.dataset.view);return}const node=e.target.closest('[data-node]');if(node)showNode(node.dataset.node)});document.addEventListener('keydown',e=>{const n=e.target.closest('[data-node]');if(n&&(e.key==='Enter'||e.key===' ')){e.preventDefault();showNode(n.dataset.node)}});document.getElementById('print').addEventListener('click',()=>window.print());selectView('product');
</script></body></html>'''
page=page.replace('__VIEWS__',views).replace('__DETAILS__',json.dumps(DETAILS,ensure_ascii=False).replace('</','<\\/')).replace('__META__',json.dumps(meta,ensure_ascii=False))
ROOT.joinpath('架构图.html').write_text(page,encoding='utf-8')
print('Generated offline HTML and 4 SVG diagrams.')
