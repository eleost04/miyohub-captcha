# 开发与维护规范 / Contributing

本服务采用与 [MiyoHub 维护规范](https://github.com/eleost04/miyohub/blob/main/CONTRIBUTING.md) 相同的原则。支持范围见 [ROADMAP.md](ROADMAP.md)。

## 提交与分支

- `main` 存放正式版本，`develop` 集成下一版；使用 `fix/*`、`feat/*`、`docs/*`、`release/*` 短期分支并通过 PR 审查。
- 每个独立改动使用 `git commit -S`。标题为 `fix(范围): 说明`、`feat(范围): 说明`、`docs(范围): 说明` 等 Conventional Commits；正文说明原因、变化、验证和风险。
- 不混入无关改动；不重写共享分支或已发布标签；不跳过签名和 CI。

## 版本与发布

`VERSION` 是唯一版本来源；本服务独立于主站迭代。修复递增补丁号，新增功能递增次版本；使用 `-beta.N` 和 `-rc.N` 标注验收阶段，正式版去掉预发行后缀。`0.x` 不兼容变更至少递增次版本并提供迁移说明。

当前基线为 `0.0.1`。仅主站变化时不修改本服务版本。正式标签须属于 `main`，Beta/RC 须属于 `develop`，均使用 `git tag -s`；推送后验证 GitHub 的签名状态。发布只包含本仓库核心源码，不包含模型、第三方源码快照或镜像。

Actions 可手动运行 `Verify wrapper`；恢复发布时运行 `Publish signed source release` 并指定已有签名标签。恢复仍执行全部检查，不覆盖已有 Release。

## 验证与安全

运行 `python tests/test_wrapper.py`、`bash -n scripts/prepare.sh`、`bash scripts/prepare.sh --verify`。最后一项需要已获取且获准使用的依赖；CI 不自动获取第三方模型。模型推理与 API 回归按 README 在 `--network none` 的独立容器内执行。

修改依赖必须记录固定上游版本，分别校验原始源码、补丁后源码与模型 SHA-256，并审查许可。不得为通过测试放宽域名白名单、Token 校验、并发锁、超时或隐私限制。不要拿真实验证码做自动回归，也不能从离线推理通过推断真实识别准确率。

Git 不包含 `models/`、`upstream/`、`.env`、密钥、日志、图片、缓存或备份。问题反馈只包含脱敏参数结构、版本和异常类型，不包含真实挑战或验证结果。维护文档放仓库根目录，临时 `docs/` 仍被排除。

## English summary

Use signed Conventional Commits on focused branches; review into `develop`, release stable versions from `main`. Explain why, what changed, test results and remaining risk. `VERSION` is canonical and this service is versioned independently: patch for fixes, minor for features, `-beta.N` / `-rc.N` for acceptance stages.

Verify wrapper tests, preparation scripts, checksums and network-disabled model tests. Keep upstream revisions and licensing explicit. Never commit credentials, models, vendor snapshots or challenge images, weaken safety checks, or exercise live captcha endpoints in automated tests. Releases require signed tags and passing checks; published tags are never overwritten.
