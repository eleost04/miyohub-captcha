# 功能与限制 / Capability board

基线版本：`0.0.1`。本服务独立于主站版本迭代。**已实现**表示代码及离线回归具备，不代表对所有真实验证码有效。

| ID | 能力 | 状态 | 验收 / 限制 |
| --- | --- | --- | --- |
| CAP-01 | `/pass_nine`、`/pass_uni` 兼容接口 | 已实现 | 校验参数与有效响应；返回失败不能伪装为成功 |
| CAP-02 | CPU 模型推理和健康检查 | 已实现 | 五个模型全部加载；真实 CPU 推理在禁网容器回归 |
| CAP-03 | Token、并发、超时及域名限制 | 已实现 | 包含鉴权失败、超时、429 和错误脱敏测试 |
| CAP-04 | 固定源码、模型及三组 SHA-256 | 已实现 | 不覆盖已有不匹配文件；不包含训练脚本或图像归档 |
| CAP-05 | 真实上游识别与账号接受结果 | 待验收 | 需账号所有者明确授权，低频测试；不承诺通过率 |
| CAP-06 | Geetest 4 自动识别 | 未实现 | 主站应让用户手动验证；不得把 V4 参数交给 V3 接口 |
| CAP-07 | 多 worker / GPU | 不在当前范围 | 共享文件及资源预算不支持简单增加 worker |
| CAP-08 | arm64 运行 | 待验收 | 当前仅验证 Linux/amd64；不将交叉构建写成硬件通过 |
| CAP-09 | 容器镜像分发 | 尚未启用 | 必须先明确第三方代码和模型的许可与分发范围 |

每条变更需包含相应测试、说明和 GPG 签名提交；详见 [CONTRIBUTING.md](CONTRIBUTING.md)。上游参考 [test_nine](https://github.com/luguoyixiazi/test_nine) 与 [验证码讨论](https://github.com/Womsxd/MihoyoBBSTools/issues/198)，许可由各项目自身声明。

## English summary

Implemented: the compatible HTTP API, five CPU models, health checks, token/timeout/concurrency controls, redacted errors and checksum-pinned preparation. Still requiring live acceptance: recognition accuracy and upstream verification. Not implemented: automated Geetest 4 solving, multi-worker/GPU support, or automatic image publication. Arm64 has not been hardware-tested.
