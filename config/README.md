# 配置说明

`config/hosts.yaml` 是本地私有配置文件。

它用于保存你自己的远程主机连接信息，例如：

- 主机 IP
- 用户名
- 认证方式
- 密码或私钥路径
- 允许访问的路径

这个文件默认不应该提交到仓库。

仓库中用于公开发布和分享的配置示例是：

- [hosts.example.yaml](./hosts.example.yaml)

推荐做法：

1. 保留自己的本地 `hosts.yaml`
2. 只维护公开可分享的 `hosts.example.yaml`
3. 长期使用优先选择 `key_path` 或 `ssh_config`
4. 如果使用 `key_path`，尽量写绝对路径，并确保私钥文件真实存在于本机
5. 如果使用 `ssh_config`，把密钥、端口、代理跳板等信息统一收进 `~/.ssh/config`
6. 如果必须使用密码，优先使用 `password_env`
7. 不要把真实密码、真实私钥路径、内网地址提交到仓库
