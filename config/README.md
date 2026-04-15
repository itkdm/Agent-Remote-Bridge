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

- [hosts.example.yaml](D:\develop\project\Agent Remote Bridge\config\hosts.example.yaml)

推荐做法：

1. 保留自己的本地 `hosts.yaml`
2. 只维护公开可分享的 `hosts.example.yaml`
3. 优先使用 `password_env` 这类环境变量引用，不要把真实密码提交到仓库
4. 不要把真实私钥路径、内网地址提交到仓库
