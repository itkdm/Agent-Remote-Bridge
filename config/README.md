# 配置远程主机

Agent Remote Bridge 通过 `config/hosts.yaml` 读取你要连接的远程 Linux 主机。

第一次使用时，可以从示例文件复制一份本地配置：

```powershell
Copy-Item .\config\hosts.example.yaml .\config\hosts.yaml
```

然后在 `hosts.yaml` 中填写自己的主机信息：

- `host_id`：给这台主机起一个本地使用的名称，例如 `demo-server`
- `host`：远程主机 IP 或域名
- `port`：SSH 端口，通常是 `22`
- `username`：SSH 登录用户
- `auth_mode`：认证方式，支持 `key_path`、`ssh_config`、`password`
- `default_workdir`：Agent 打开 session 后默认进入的远程目录
- `allowed_paths`：允许 Agent 读取或操作的远程路径范围
- `allow_sudo`：是否允许通过工具请求执行 sudo 命令

长期使用时，推荐优先选择 `key_path` 或 `ssh_config`，不要直接把密码写进配置文件。

如果使用 `key_path`，请填写本机私钥的绝对路径，并确认文件真实存在。例如：

```yaml
auth_mode: key_path
private_key_path: C:/Users/YOUR_USER/.ssh/id_ed25519
```

如果你已经在 `~/.ssh/config` 里维护了密钥、端口、代理跳板等信息，可以使用 `ssh_config`：

```yaml
auth_mode: ssh_config
ssh_config_host: my-server
```

如果必须使用密码，推荐把密码放在环境变量里，再通过 `password_env` 引用：

```yaml
auth_mode: password
password_env: ARB_DEMO_SERVER_PASSWORD
```

PowerShell 设置示例：

```powershell
$env:ARB_DEMO_SERVER_PASSWORD="YOUR_PASSWORD"
```

配置完成后，先运行本地校验：

```powershell
agent-remote-bridge config-validate
```

再对目标主机做 SSH 预检：

```powershell
agent-remote-bridge preflight --host-id demo-server
```

注意：`hosts.yaml` 是你的本地私有配置，可能包含真实 IP、用户名、私钥路径或密码变量名。不要把真实密码、真实私钥路径、内网地址或生产服务器信息提交到公开仓库。公开分享时请使用 [hosts.example.yaml](./hosts.example.yaml) 这样的示例配置。
