# B站感知与模型成本：专项研究

截至 2026-10-25（Asia/Tokyo）。本轮阅读作者仓库与选定源码，没有登录B站、发评论或执行插件。建议与源码事实分开记录。

## 主要发现

1. **已有“刷B站的鱼”实现可研究。** [dsh-bili-whale](https://github.com/Alterssss/dsh-bili-whale) 当前 package 0.4.6，将作息调度、视频资料、日记、分享与监听组合起来；[dsh-bili-pond](https://github.com/YOYOLnFu/dsh-bili-pond) 文档版本1.3.12，偏每日筛选、报告、记忆和管理面板。这说明产品流程能做，不证明复制安装即兼容或真实平台永远可用。
2. **看视频必须注明观察范围。** 字幕可以支持讨论台词；抽帧可以支持有限画面观察；标题、简介、封面只能支持有限判断。抽几帧不等于观看完整视频；ASR/OCR也会错。评论是别人的观点，不是视频内容本身。建议记录 transcript / sampled_frames / metadata_only / failed，并在分享语气中体现。
3. **源码与宣传存在具体差异。** 固定提交 `8b0009f8ce2ebdc421afcb2e727b19ac18912ec6` 的 [traffic.mjs](https://github.com/Alterssss/dsh-bili-whale/blob/8b0009f8ce2ebdc421afcb2e727b19ac18912ec6/tools/lib/traffic.mjs) 默认间隔1500ms且可读risk配置；README另有一段仍称600ms写死。自己的实现应以固定源码和测试为准，不照抄宣传默认值。[debrief.mjs](https://github.com/Alterssss/dsh-bili-whale/blob/8b0009f8ce2ebdc421afcb2e727b19ac18912ec6/tools/commands/debrief.mjs) 确有字幕、评论与抽帧路径，并对某些失败降级；这只是获取路径存在，不能证明一定“真看懂”。
4. **只读适配器可借鉴。** [moxingovo/dsh-bilibili](https://github.com/moxingovo/dsh-bilibili/blob/main/README.zh.md) 提供搜索、元数据、字幕、播放地址和帧工具，使用结构化错误；源码已查 [provider.ts](https://github.com/moxingovo/dsh-bilibili/blob/42cd1c9e7d975fc46cf62bd86024a134c37501d7/src/provider.ts)。它访问B站服务器并不等于平台授权的开放API；README也明确它是非官方社区插件。其兼容性列的是DSH 0.1.7等旧线，不能推定0.2.1兼容。
5. **旧SDK的维护状态已经变化。** [Nemo2011/bilibili-api](https://github.com/Nemo2011/bilibili-api) 在2026-07-06归档，当前README写停止维护及永久关停。旧教程、仍可安装的PyPI版本或fork不能证明上游持续维护。这里只报告仓库状态，不采纳其中法律函件的指控为独立法律结论。
6. **浏览器读取是另一种可替换实现。** 可以在用户明确登录的独立浏览器状态中读取正常可见页面，但仍受页面变化、登录过期及平台限制影响，不能承诺比API永远稳定或自动获得平台许可。[Playwright官方](https://playwright.dev/docs/auth) 支持保存登录状态，并说明该文件包含敏感认证信息。验证码/拒绝访问时暂停并交回用户，不把失败记成无内容。

## 适合本项目的第一版

围绕“QQ好友”设计：B站用于产生经历，QQ用于和用户分享。第一版只做低频读取和给主人私聊分享；公开评论、点赞、投币、私信其他人均不属于用户当前要求。

建议循环：每天1–2次候选发现 → 根据鱼自己的兴趣和用户近期话题筛选 → 对最多2条获取正文/字幕及必要画面 → 保存来源证据 → 形成个人看法 → 判断是否值得打扰 → QQ发送并记录回执。次数是产品初值，不是平台认可配额。

每条观察至少保存 BV/cid、URL、标题、作者、获取时间、观察模式、覆盖时间段、原始资料引用、摘要、感想、置信与失败状态。原始视频事实和鱼的感想分开；看见某观点不代表采纳，不自动把它升级成用户偏好。

读取范围、调度预算与发送权限由程序控制。网页、字幕、评论都是外部材料，不得改变主人身份、工具权限、人格锁定或长期记忆规则。发送采用去重键和状态机，未知结果先核查，不自动重复发。

## 当前DeepSeek模型与成本

[官方价格页](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) 显示当前 `deepseek-flash` 对应 DeepSeek-V4.1-Flash-1017；[图像文档](https://api-docs.deepseek.com/zh-cn/guides/vision/) 明确可接收图片。因此现在不能沿用“DeepSeek不看图”的旧结论。是否能理解抽帧仍取决于适配器真正传入图片及上下文覆盖。

价格快照：Flash每百万token，空闲时输入未命中1元、命中0.02元、输出4元；高峰分别2、0.04、8元。按实际缓存、思考输出和图片token计量。

**算术例子而非实测报价：** 若每天总计20万未缓存输入、2万输出，全按空闲价为0.28元/天、8.4元/30天；全按高峰价为0.56元/天、16.8元/30天。若反思、浏览、长历史令用量放大10倍，价格也近似放大10倍。未含嵌入、语音识别、服务器和额外搜索。

同页列Search/Fetch各5元/1000成功请求；说明Harness等通过Server端工具调用的部分将于北京时间2026-11-01 00:00起计费（日本时间同日01:00）。因此要统计真实usage、失败重试和后台消费，不能凭聊天条数报价。先给日预算、达到后暂停浏览，保留用户聊天额度。

## 本次证据边界

已查固定文件：whale package.json、debrief.mjs、traffic.mjs；moxing provider.ts；三项目README和官方模型文档。未完成全仓安全审计，未做DSH兼容测试、B站登录访问或连续7日观察。下一阶段需要用少量用户选定视频验证正文获取、失败分类和分享质量。
