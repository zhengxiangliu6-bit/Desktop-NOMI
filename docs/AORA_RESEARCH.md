# Aora Bot 实际发布调研

调研日期：2026-11-11（Asia/Shanghai）。结果是本次快照，升级前重新查询，不将上游 main 等同 npm 发布版。

## 来源与版本

- [npm 元数据](https://registry.npmjs.org/@aora-bot%2freact)：`latest = 0.2.0`，peer `react >=19` / `react-dom >=19`，依赖 `@aora-bot/engine = 0.2.0`，Node `>=20`。
- 上游 HEAD：`164ffa38b3c27a8512e7c09cfceb7cf0c98f5144`；[固定版本 React README](https://github.com/sam70361/aora-bot/blob/164ffa38b3c27a8512e7c09cfceb7cf0c98f5144/packages/react/README.md)、[许可证](https://github.com/sam70361/aora-bot/blob/164ffa38b3c27a8512e7c09cfceb7cf0c98f5144/LICENSE)。
- 实际安装的 npm 包含 `LICENSE`、`dist/index.d.ts`、`dist/styles.css`；许可证为 Aora Bot License 1.1，metadata 为 `SEE LICENSE IN LICENSE`。
- tarball integrity：`sha512-PofPEn+PvUF9ugpH1qCw6zDR3/JvNb2W4mZfH3FAebJXrrSaKYZsiS53ftfR1PUdd+yILgkTDnM2uELNK0wHzw==`。未来由 package-lock 保留 registry integrity，不跳过校验。

## 安装与用法

上游示例使用 pnpm，但包是标准 npm ESM 发布；项目按用户要求选择 npm。阶段 1 已在 frontend 工程中通过 npm 安装并锁定此版本；独立添加命令为：

```bash
npm install --save-exact @aora-bot/react@0.2.0
```

React / React DOM 19 为前置依赖，engine 自动安装，无需单独添加；不存在必须安装的 `@aora-bot/core`。不需要复制上游仓库、引入 surfaces 或通过 CDN 加载。

```tsx
import { CharacterMark } from '@aora-bot/react';
import '@aora-bot/react/styles.css'; // 在应用入口导入一次

// 上游基础示例；本项目 RobotView 使用 circle / cream
<CharacterMark shape="mochi" state="happy" sizePx={96} />;
```

已核对发布包 CharacterMarkProps：支持 shape、state、emotionId、sizePx、face、styleId 等；同时给 state 与 emotionId 时 state 优先。44 个动画状态包含 idle/listening/thinking/happy/confused/humming，不含 speaking，项目 Mock speaking 在 neutral 时映射 humming，其他情绪保留对应表情；不声称精准口型。内部数字情绪协议与 AgentStateProvider 可用，但本项目先以自己的语义协议加 Adapter 隔离，不把 SDK 数据结构扩散至后端。

## 实测与限制

在 `/tmp/nomi-aora-research` 独立安装 `@aora-bot/react@0.2.0` 与 React / React DOM 19，npm 成功解析 5 个包，无项目依赖文件变更。检查 exports、CSS 路径、发布类型和许可证。

Node SSR 的 CharacterMark 只输出 `<span class="aora-mark" ...>` 容器，SVG 动画依赖客户端 effect 挂载。最初以 SSR 应包含 SVG 的探针失败；读取组件行为后改为验证正确容器属性和导出。此检查只验证包解析、服务端容器行为与静态接口，不证明浏览器动画、Vite 构建或 Windows 渲染可用。V0.1 必须浏览器挂载验证及实际构建。

## 许可与升级风险

这不是 MIT / Apache 依赖，也不能仅因源码公开称为无条件开源许可。中文协议优先：个人、教育、非营利、非营利且完全开源项目、合并计算全职/兼职/长期外包不超过 3 人的营利组织可符合免费资格；委托开发按最终拥有/运营产品方判断。其他组织上线或商用需事先商业授权；评估与内部原型例外按原文判断。

免费资格公开发布须注明 Powered by Aora Bot 并链接上游；README 已保留。不得将引擎主体单独转售、提供以角色/头像/表情为主要价值的托管服务、单售角色商品、注册角色商标、用角色设计训练生成模型或删除许可声明。将来机器人硬件分发同样需检查条款，不能假设原型许可覆盖量产。

升级时核对完整 LICENSE / LICENSE-COMMERCIAL、团队资格、API、传递依赖、动画性能和视觉回归，并更新锁文件与本记录。项目自身 LICENSE 待拥有者确定；不擅自给整个项目添加会覆盖第三方权利的许可证。React、Vite、FastAPI 等计划依赖通常为 MIT，TypeScript 为 Apache-2.0；以未来锁定版本及其传递依赖的实际许可为准，目前未完成整个应用依赖审计。

## 阶段 1 补充验证

重新查询 npm latest 仍为 0.2.0，前端 package-lock 保留发布 integrity；实际 TypeScript 验证 shape 应为 circle，dot 属于角色标识。Playwright 在 Linux 系统 Chromium 中验证真实 SVG 挂载、idle 连续帧变化和手机视口；启用 autoPause 处理 reduced-motion 与离屏暂停。Windows 实机尚未验证。完整安装无需下载或复制上游仓库。
